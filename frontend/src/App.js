// src/App.js

import React, { useState, useEffect } from "react";
import "./App.css";
import { FileSpreadsheet, Search, AlertCircle } from "lucide-react";

const API_BASE_URL = "http://localhost:8000";

function App() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false); // search loading
  const [error, setError] = useState(null);
  const [showContext, setShowContext] = useState(false);

  const [filesToUpload, setFilesToUpload] = useState([]);
  const [indexing, setIndexing] = useState(false);
  const [indexReady, setIndexReady] = useState(false);
  const [indexMessage, setIndexMessage] = useState(
    "Please upload spreadsheets to start."
  );
  const [indexedConcepts, setIndexedConcepts] = useState(0);

  // 🔹 Track currently stored workbook(s) on backend
  const [uploadedFiles, setUploadedFiles] = useState([]);

  // 🔹 Default examples (fallback when nothing indexed yet)
  const [exampleQueries, setExampleQueries] = useState([
    "Who is the best performer in the East region?",
    "What is the Total Revenue for Year 1?",
    "What is the Net Profit for Year 3?",
    "Which region has the highest churn?",
    "Show me the top 3 customers by revenue.",
  ]);

  // --- Backend helpers ---

  const fetchFiles = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/files`);
      if (!res.ok) return;
      const data = await res.json();
      setUploadedFiles(Array.isArray(data.files) ? data.files : []);
    } catch (e) {
      console.error("Failed to fetch file list:", e);
      setUploadedFiles([]);
    }
  };

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/status`);
      if (!res.ok) return;
      const data = await res.json();
      const count = data.indexed_concepts || 0;
      setIndexedConcepts(count);

      if (count > 0) {
        setIndexReady(true);
        setIndexMessage(`Index ready with ${count} concepts.`);
      } else {
        setIndexReady(false);
        setIndexMessage("No data indexed yet. Please upload spreadsheets.");
      }

      // 🔹 If backend returns example_queries in /status, update them
      if (Array.isArray(data.example_queries) && data.example_queries.length) {
        setExampleQueries(data.example_queries);
      }

      // Keep file list in sync
      fetchFiles();
    } catch (e) {
      console.error(e);
      setIndexMessage("Unable to fetch index status.");
      setUploadedFiles([]);
    }
  };

  useEffect(() => {
    // On mount, clear any previous dataset/index and then check status
    const init = async () => {
      try {
        await fetch(`${API_BASE_URL}/reset`, {
          method: "POST",
        });
      } catch (e) {
        console.error("Failed to reset backend state:", e);
      } finally {
        fetchStatus();
      }
    };

    init();
  }, []);

  // --- Upload & Index ---

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files || []);
    setFilesToUpload(files);
  };

  const handleUploadAndIndex = async () => {
    if (!filesToUpload.length) {
      setError("Please select at least one Excel file (.xlsx).");
      return;
    }
    setError(null);
    setResult(null);
    setIndexing(true);
    setIndexReady(false);
    setIndexMessage("Uploading files and indexing. Please wait...");

    try {
      const formData = new FormData();
      filesToUpload.forEach((file) => {
        formData.append("files", file);
      });

      const res = await fetch(`${API_BASE_URL}/index`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        // Try to parse JSON error first, then fall back to raw text
        let message = "Indexing failed.";
        try {
          const errData = await res.json();
          message = errData.detail || errData.message || message;
        } catch {
          const text = await res.text();
          if (text) message = text;
        }
        throw new Error(message);
      }

      const data = await res.json();

      if (data.status === "success" && data.indexed_concepts > 0) {
        setIndexedConcepts(data.indexed_concepts);
        setIndexReady(true);
        setIndexMessage(
          data.message ||
            `Indexing complete. Indexed ${data.indexed_concepts} concepts.`
        );

        // 🔹 Update curated example queries from backend if present
        if (
          Array.isArray(data.example_queries) &&
          data.example_queries.length > 0
        ) {
          setExampleQueries(data.example_queries);
        }

        // 🔹 Refresh file list after successful indexing
        fetchFiles();

        // (Optional) Clear local selection after upload
        // setFilesToUpload([]);
      } else {
        setIndexReady(false);
        setIndexMessage(
          data.message || "Indexing did not produce any indexed concepts."
        );
        setUploadedFiles([]);
      }
    } catch (err) {
      console.error(err);
      setError(
        err.message || "An unexpected error occurred during indexing."
      );
      setIndexReady(false);
      setIndexMessage("Indexing failed.");
      setUploadedFiles([]);
    } finally {
      setIndexing(false);
    }
  };

  // --- Search ---

  const handleSearch = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (!query.trim()) return;

    if (!indexReady) {
      setError("Index is not ready yet. Please upload and index spreadsheets.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${API_BASE_URL}/search`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: query }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to fetch search result.");
      }

      const data = await response.json();
      setResult(data);
      setShowContext(true);
    } catch (err) {
      console.error(err);
      setError(err.message || "An unexpected error occurred during search.");
    } finally {
      setLoading(false);
    }
  };

  // Simple Markdown renderer
  const renderMarkdown = (markdownText) => {
    if (!markdownText) return null;

    let html = markdownText.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    const lines = html.split("\n");
    let inList = false;
    let finalHtml = "";

    lines.forEach((line) => {
      if (line.trim().startsWith("*")) {
        if (!inList) {
          finalHtml += "<ul>";
          inList = true;
        }
        finalHtml += line.trim().replace(/^\* /, "<li>") + "</li>";
      } else {
        if (inList) {
          finalHtml += "</ul>";
          inList = false;
        }
        if (line.trim() !== "") {
          finalHtml += `<p>${line}</p>`;
        }
      }
    });

    if (inList) {
      finalHtml += "</ul>";
    }

    return <div dangerouslySetInnerHTML={{ __html: finalHtml }} />;
  };

  // --- JSX ---

  return (
    <div className="App app-root">
      <div className="app-shell">
        {/* HEADER CARD */}
        <header className="header-card">
          <div className="header-icon">
            <FileSpreadsheet className="header-icon-svg" />
          </div>
          <div className="header-text">
            <h1 className="app-title">SemantiSheet AI Search</h1>
            <p className="app-subtitle">No formulas. No queries. Just ask.</p>
            <div className="tech-pill-row">
              <span className="tech-pill">
                Backend: FastAPI + Gemini + ChromaDB
              </span>
              <span className="tech-pill">Frontend: React</span>
            </div>
          </div>
        </header>

        <main className="content-area">
          {/* UPLOAD & INDEX CARD */}
          <section className="search-card" style={{ marginBottom: "1rem" }}>
            <h2 style={{ marginBottom: "0.5rem" }}>
              1. Upload spreadsheets &amp; build index
            </h2>
            <p style={{ marginBottom: "0.75rem", fontSize: "0.9rem" }}>
              Select one or more Excel files (.xlsx). We&apos;ll index them and
              then enable semantic search.
            </p>

            <div className="upload-container">
              {/* CUSTOM FILE INPUT */}
              <div className="file-input-wrapper">
                <label className="custom-file-btn" htmlFor="file-upload">
                  {filesToUpload.length
                    ? `${filesToUpload.length} file(s) selected`
                    : "Choose Files"}
                </label>
                <input
                  id="file-upload"
                  type="file"
                  multiple
                  accept=".xlsx,.xls"
                  onChange={handleFileChange}
                />
              </div>

              <button
                type="button"
                onClick={handleUploadAndIndex}
                className="btn btn-secondary"
                disabled={indexing || !filesToUpload.length}
              >
                {indexing ? "Indexing..." : "Upload & Index"}
              </button>
            </div>

            {/* 🔹 Preview selected file names BEFORE upload */}
            {filesToUpload.length > 0 && (
              <div className="selected-files">
                <p className="selected-files-title">Selected file(s):</p>
                <ul className="selected-files-list">
                  {filesToUpload.map((file, idx) => (
                    <li key={idx}>{file.name}</li>
                  ))}
                </ul>
              </div>
            )}

            <div
              className="status-card status-info"
              style={{ marginTop: "0.75rem" }}
            >
              {indexReady ? <>✅ {indexMessage}</> : <>ℹ️ {indexMessage}</>}
            </div>
          </section>

          {/* SEARCH CARD */}
          <section className="search-card">
            <div className="mode-header">
              <h2 style={{ marginBottom: "0.5rem" }}>
                2. Ask a question on your sheets
              </h2>
            </div>

            <form onSubmit={handleSearch} className="search-form-row">
              <div className="search-input-wrapper">
                <Search className="search-input-icon" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Try one of the suggested questions below…"
                  disabled={loading || !indexReady}
                  className="search-input"
                />
              </div>
              <button
                type="submit"
                disabled={loading || !indexReady}
                className="btn btn-primary"
              >
                {loading ? "Searching..." : "Search Data"}
              </button>
            </form>

            {/* Example Queries (dynamic) */}
            <div className="examples-section">
              <p className="examples-label">Try these example queries:</p>
              <div className="examples-chips">
                {exampleQueries.map((ex, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="chip"
                    onClick={() => {
                      setQuery(ex);
                      if (indexReady && !loading) {
                        handleSearch({ preventDefault: () => {} });
                      }
                    }}
                    disabled={loading || !indexReady}
                  >
                    {ex}
                  </button>
                ))}
              </div>
            </div>

            {/* STATUS / ERROR */}
            {loading && (
              <div className="status-card status-info">
                🔍 Searching and synthesizing answer...
              </div>
            )}

            {error && (
              <div className="status-card status-error">
                <AlertCircle className="status-icon" />
                <span>Error: {error}</span>
              </div>
            )}

            {!indexReady && !indexing && (
              <div className="status-card status-warning">
                ⚠️ Index is not ready. Please upload and index spreadsheets
                before searching.
              </div>
            )}
          </section>

          {/* SEARCH RESULT */}
          {result && (
            <section className="result-card">
              <div className="result-header">
                <h2 className="result-title">✅ Search Result</h2>
                <span className="result-query-pill">
                  Query: <em>{result.query}</em>
                </span>
              </div>

              <div className="synthesis-block">
                {renderMarkdown(result.result)}
              </div>

              <button
                type="button"
                onClick={() => setShowContext(!showContext)}
                className="btn btn-secondary context-toggle-btn"
              >
                {showContext
                  ? "Hide Retrieved Context (Source Data)"
                  : "Show Retrieved Context (Source Data)"}
              </button>

              {showContext && (
                <div className="context-section">
                  <h3 className="context-title">
                    Context Snippets Used for Synthesis
                  </h3>
                  <p className="context-subtitle">
                    These {result.context.length} snippets were retrieved from
                    ChromaDB and passed to the Gemini model:
                  </p>

                  <div className="context-table-container">
                    <table className="context-table">
                      <thead>
                        <tr>
                          <th>SHEET</th>
                          <th>METRIC</th>
                          <th>CONTEXT SNIPPET</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.context.map((item, index) => (
                          <tr key={index}>
                            <td>{item.sheet}</td>
                            <td>{item.metric}</td>
                            <td>{item.snippet}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </section>
          )}

          {/* EMPTY STATE (when nothing yet) */}
          {!loading && !result && !error && uploadedFiles.length === 0 && (
            <section className="empty-state-card">
              <Search className="empty-state-icon" />
              <h3>Start by uploading spreadsheets, then ask a question</h3>
              <p>
                For example:{" "}
                <em>“Who is the best performer in the East region?”</em>
              </p>
            </section>
          )}

          {/* INFO FOOTER */}
          <section className="info-footer">
            <h3>How this semantic search works</h3>
            <div className="info-grid">
              <div className="info-item">
                <h4>1. Embed your query</h4>
                <p>
                  Your natural language question is converted into a vector
                  using Google Gemini embeddings.
                </p>
              </div>
              <div className="info-item">
                <h4>2. Retrieve relevant snippets</h4>
                <p>
                  ChromaDB finds the most relevant spreadsheet rows and metrics
                  based on semantic similarity.
                </p>
              </div>
              <div className="info-item">
                <h4>3. Synthesize an answer</h4>
                <p>
                  Gemini analyzes the retrieved context to generate a clear,
                  structured answer.
                </p>
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

export default App;
