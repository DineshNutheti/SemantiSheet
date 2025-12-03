# **SemantiSheet AI Search**

*Ask business questions to Excel — no formulas, just natural language.*

---

##  **What is SemantiSheet?**

**SemantiSheet AI Search** lets you upload Excel spreadsheets and **query them using plain English**, powered by:

| Component             | Purpose                         |
| --------------------- | ------------------------------- |
| **FastAPI**           | Backend API                     |
| **React**             | Frontend UI                     |
| **ChromaDB**          | Vector search engine            |
| **Google Gemini API** | Embeddings + AI reasoning       |
| **OpenPyXL / Pandas** | Spreadsheet parsing & ingestion |

You can ask questions like:

* What is the total revenue for Year 2?
* Who is the best performer in the East region?
* Which region has the highest churn?
* Show me the profit comparison year-wise.

No cell references. No formulas. Just questions.

---

## 📂 **Project Structure**

```
SemantiSheet/
│── backend/
    ├── api
    │   └── main.py            # FastAPI server
    ├── chroma_db              # Store vector embeddings
    ├── data                   # Store excel files temporarily
    └── utils
        ├── index_data.py
        └── ingestion.py
│── frontend/
│   ├── src/
│   │   ├── App.js             # Main React UI
│   │   ├── App.css            # Styling
│   ├── package.json
│── README.md
│── .env.example
```

---

## 🧠 **How It Works**

```
User Query
   ↓
Gemini Embedding API → Vector
   ↓
ChromaDB → Top relevant Excel cells
   ↓
Gemini LLM → Structured answer
   ↓
Shown in React frontend
```

---

## ⚙️ **Installation Guide (FULL STEPS)**

### **1. Create a Python Environment**

```bash
# Windows
python -m venv venv

# Linux/Mac
python3 -m venv venv
```

### **2. Activate the Environment**

**Windows**

```bash
cd backend
venv\Scripts\activate
```

**Linux/Mac**

```bash
cd backend
source venv/bin/activate
```

---

### **3. Install Dependencies**

```bash
pip install -r requirements.txt
```

---

### **4. Set API Key**

Create `.env` file inside **backend/** and add:

```
GEMINI_API_KEY=your_api_key_here
```

---

### **5. Run Backend (FastAPI)**

```bash
uvicorn main:app --reload
```

API Runs at ➜ `http://localhost:8000`

---

### **6. Frontend Setup (React)**

```bash
cd frontend
npm install
npm start
```

Runs at ➜ `http://localhost:3000`

---

### **7. (Optional) Manual Data Ingestion**

*If file upload is not used from frontend:*

```bash
python src/ingestion.py
python index_data.py
```

---

## 📌 **API Endpoints**

| Endpoint            | Method | Description                         |
| ------------------- | ------ | ----------------------------------- |
| `/index`            | POST   | Upload & index spreadsheets         |
| `/search`           | POST   | Ask a question about sheets         |
| `/files`            | GET    | List uploaded files                 |
| `/files/{filename}` | GET    | Download the updated Excel          |

---

## 🔍 **Example Query (POST /search)**

```json
{
  "query": "What is the total revenue of Year 1?"
}
```

---

## 📤 **Example Response**

```json
{
  "query": "What is the total revenue of Year 1?",
  "result": "**Revenue in Year 1: 350000** from sheet 'Dashboard'.",
  "context": [
    {
      "sheet": "Dashboard",
      "metric": "Total Revenue Yr1",
      "snippet": "350000"
    }
  ]
}
```

---

## 📈 **Tech Stack**

| Layer               | Technology Used                    |
| ------------------- | ---------------------------------- |
| Frontend            | React                              |
| Backend             | FastAPI                            |
| Vector DB           | ChromaDB                           |
| Embeddings          | Google Gemini                      |
| Spreadsheet Parsing | pandas, OpenPyXL                   |
| Deployment          | Works on Localhost                 |    

---

## 🧠 **Future Enhancements**

* Google Sheets API Integration
* Domain-specific business templates
* Sheet summarization & insights
* SaaS login + multi-user dashboard
* Full financial modeling support

---

## 📜 **License**

MIT License — free for commercial and research use.

---
