# backend/app/api/main.py

import time  # New import for logging duration
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import shutil
import os
from google import genai
from typing import List, Dict, Any

from app.core.config import DATA_DIR, GENERATIVE_MODEL, GEMINI_API_KEY
from app.services.ingestion import StreamingSheetParser
from app.services.embedding import embedding_service
from app.services.vector_db import vector_db

# --- Config ---
# Initialize the new Google GenAI client
client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI(title="SemantiSheet Local RAG")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---
class SearchRequest(BaseModel):
    query: str

class SearchResult(BaseModel):
    query: str
    result: str
    context: List[Dict[str, Any]]

# --- Global State for Progress ---
indexing_state = {
    "is_indexing": False,
    "total_indexed": 0,
    "current_file": "",
    "status_message": "Idle"
}

def clear_index(reset_data_dir: bool = True):
    global indexing_state
    # 1. Reset the indexing state tracking
    indexing_state = {
        "is_indexing": False,
        "total_indexed": 0,
        "current_file": "",
        "status_message": "Idle"
    }
    
    # 2. Drop the ChromaDB collection
    vector_db.reset_collection()
    
    # 3. Wipe the data directory physically
    if reset_data_dir and DATA_DIR.exists():
        for f in DATA_DIR.glob("*"):
            try:
                if f.is_file(): f.unlink()
            except Exception as e:
                print(f"⚠️ Cleanup error: {e}")

# --- Background Task Logic ---
def process_files_background(filepaths: List[str]):
    global indexing_state
    indexing_state["is_indexing"] = True
    indexing_state["total_indexed"] = 0
    
    start_time_total = time.time() # Track total process time
    vector_db.reset_collection()
    
    BATCH_SIZE = 500 
    
    try:
        for fp in filepaths:
            filename = os.path.basename(fp)
            indexing_state["current_file"] = filename
            indexing_state["status_message"] = f"Parsing {filename}..."
            
            print(f"\n🚀 Starting Indexing: {filename}")
            parser = StreamingSheetParser(fp)
            
            batch_docs, batch_metas, batch_ids = [], [], []
            
            # 1. Parse Data
            parse_start = time.time()
            for row in parser.process_generator():
                if row is None: continue
                
                batch_docs.append(row.semantic_text)
                batch_metas.append(row.to_metadata())
                
                safe_sheet = str(row.sheet_name).replace(" ", "_")
                batch_ids.append(f"{filename}_{safe_sheet}_{row.row_index}")
                
                # 2. Process Batch (Embedding + DB)
                if len(batch_docs) >= BATCH_SIZE:
                    batch_start = time.time()
                    
                    # Log embedding time
                    emb_start = time.time()
                    embeddings = embedding_service.generate_batch(batch_docs)
                    emb_end = time.time()
                    
                    # Log DB insertion time
                    db_start = time.time()
                    vector_db.add_batch(batch_docs, batch_metas, batch_ids, embeddings)
                    db_end = time.time()
                    
                    batch_duration = time.time() - batch_start
                    indexing_state["total_indexed"] += len(batch_docs)
                    
                    print(f"   ✅ Batch Processed: {len(batch_docs)} rows in {batch_duration:.2f}s "
                          f"(Emb: {emb_end-emb_start:.2f}s | DB: {db_end-db_start:.2f}s)")
                    
                    batch_docs, batch_metas, batch_ids = [], [], []

            # 3. Handle remaining rows
            if batch_docs:
                final_emb_start = time.time()
                embeddings = embedding_service.generate_batch(batch_docs)
                vector_db.add_batch(batch_docs, batch_metas, batch_ids, embeddings)
                indexing_state["total_indexed"] += len(batch_docs)
                print(f"   ✨ Final Batch for {filename}: {len(batch_docs)} rows in {time.time()-final_emb_start:.2f}s")

        total_duration = time.time() - start_time_total
        print(f"\n🎉 INDEXING COMPLETE")
        print(f"🏁 Total Rows: {indexing_state['total_indexed']}")
        print(f"⏱️  Total Time: {total_duration:.2f} seconds")
        print(f"📊 Avg Speed: {indexing_state['total_indexed'] / total_duration:.2f} rows/sec")
        
        indexing_state["status_message"] = f"Complete! {indexing_state['total_indexed']} rows in {total_duration:.1f}s"
        
    except Exception as e:
        print(f"❌ Indexing Error: {e}")
        indexing_state["status_message"] = f"Error: {str(e)}"
    finally:
        indexing_state["is_indexing"] = False

# --- Endpoints ---

@app.post("/index")
async def index_data(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    # 1. Clear old data ONLY when a new upload starts
    clear_index(reset_data_dir=True)
    
    # 2. Save new files
    saved_paths = []
    for upload in files:
        dest = DATA_DIR / upload.filename
        with open(dest, "wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)
        saved_paths.append(str(dest))

    # 3. Trigger background indexing
    background_tasks.add_task(process_files_background, saved_paths)
    return {"status": "started"}

@app.get("/status")
def get_status():
    """Returns current indexing status and example queries."""
    # Always fetch the live count from the vector database
    count = vector_db.count() 
    
    # If the background task isn't running, provide examples from the existing index
    examples = []
    if not indexing_state["is_indexing"] and count > 0:
        examples = vector_db.get_example_queries()
    
    return {
        "status": "indexing" if indexing_state["is_indexing"] else "ok",
        "indexed_concepts": count,
        "message": indexing_state["status_message"],
        "example_queries": examples
    }

@app.post("/search", response_model=SearchResult)
def search_data(request: SearchRequest):
    if vector_db.count() == 0:
         raise HTTPException(status_code=503, detail="Index empty.")
    
    start_time = time.time()
    
    # 1. Embed Query locally
    emb_start = time.time()
    q_embedding = embedding_service.generate_batch([request.query])[0]
    emb_end = time.time()
    
    # 2. Retrieve snippets from local vector DB
    ret_start = time.time()
    results = vector_db.search(q_embedding)
    docs = results['documents'][0]
    metas = results['metadatas'][0]
    ret_end = time.time()
    
    # 3. Synthesize (Modern Gemini SDK)
    syn_start = time.time()
    context_str = "\n".join([f"- {d}" for d in docs])
    
    system_instruction = (
        "You are a spreadsheet analysis expert. Answer the user query based ONLY on the "
        "provided snippets. If you cannot find the answer, say so. Group answers by sheet."
    )
    
    user_prompt = f"Query: {request.query}\n\nContext Snippets:\n{context_str}"
    
    try:
        response = client.models.generate_content(
            model=GENERATIVE_MODEL,
            contents=user_prompt,
            config={'system_instruction': system_instruction}
        )
        final_text = response.text
    except Exception as e:
        print(f"❌ Gemini Synthesis Error: {e}")
        final_text = "Error generating response from Gemini."
    syn_end = time.time()
    
    total_latency = time.time() - start_time
    print(f"\n🔍 Search Completed in {total_latency:.2f}s")
    print(f"   ├─ Embedding: {emb_end-emb_start:.2f}s")
    print(f"   ├─ Retrieval: {ret_end-ret_start:.2f}s")
    print(f"   └─ Synthesis: {syn_end-syn_start:.2f}s")
    
    return SearchResult(
        query=request.query, 
        result=final_text, 
        context=[{"sheet": m.get("sheet"), "metric": m.get("header"), "snippet": d} for m, d in zip(metas, docs)]
    )

@app.post("/reset")
def reset_all():
    clear_index(reset_data_dir=True)
    return {"status": "reset", "indexed_concepts": 0}

@app.get("/files")
def list_files():
    if not os.path.exists(DATA_DIR):
        return {"files": []}
    files = [{"name": f, "size_bytes": os.path.getsize(DATA_DIR / f)} for f in os.listdir(DATA_DIR)]
    return {"files": files}

@app.get("/files/{filename}")
def download_file(filename: str):
    target = DATA_DIR / filename
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(path=target, filename=filename)