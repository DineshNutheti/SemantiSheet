// src/App.js

import React, { useState, useEffect } from "react";
import "./App.css";
import { FileSpreadsheet, Search, AlertCircle } from "lucide-react";

const API_BASE_URL = "http://localhost:8000";

function App() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false); 
  const [error, setError] = useState(null);
  const [showContext, setShowContext] = useState(false);

  const [filesToUpload, setFilesToUpload] = useState([]);
  const [indexing, setIndexing] = useState(false);
  const [indexReady, setIndexReady] = useState(false);
  const [indexMessage, setIndexMessage] = useState(
    "Please upload spreadsheets to start."
  );
  const [indexedConcepts, setIndexedConcepts] = useState(0);
  const [uploadedFiles, setUploadedFiles] = useState([]);

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

      // Change: UI unlocks if status is 'ok' and count > 0
      if (data.status === "ok" && count > 0) {
        setIndexReady(true);
        setIndexMessage(data.message || `Index ready with ${count} concepts.`);
        setIndexing(false); // Stop indexing spinner if polling found it's done
      } else if (data.status === "indexing") {
        setIndexReady(false);
        setIndexing(true);
        setIndexMessage(data.message || `Indexing in progress... (${count} rows so far)`);
      } else {
        setIndexReady(false);
        setIndexMessage("No data indexed yet. Please upload spreadsheets.");
      }

      if (Array.isArray(data.example_queries) && data.example_queries.length) {
        setExampleQueries(data.example_queries);
      }

      fetchFiles();
      return data.status; // Return status for polling logic
    } catch (e) {
      console.error("Status check failed:", e);
      setIndexMessage("Unable to fetch index status.");
    }
  };

  useEffect(() => {
    // BUG FIX: Removed the /reset call so data persists on refresh
    fetchStatus();
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
    setIndexMessage("Uploading files and starting indexing...");

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
        throw new Error("Failed to start indexing.");
      }

      // NEW: Auto-Polling Logic
      // Check status every 2 seconds until status is "ok"
      const pollInterval = setInterval(async () => {
        const currentStatus = await fetchStatus();
        if (currentStatus === "ok") {
          clearInterval(pollInterval); // Stop polling when finished
        }
      }, 2000);

    } catch (err) {
      console.error(err);
      setError(err.message || "An unexpected error occurred.");
      setIndexing(false);
    }
  };

  // --- Search ---

  const handleSearch = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${API_BASE_URL}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Search failed.");
      }

      const data = await response.json();
      setResult(data);
      setShowContext(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const renderMarkdown = (markdownText) => {
    if (!markdownText) return null;
    let html = markdownText.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    const lines = html.split("\n");
    let inList = false;
    let finalHtml = "";

    lines.forEach((line) => {
      if (line.trim().startsWith("*")) {
        if (!inList) { finalHtml += "<ul>"; inList = true; }
        finalHtml += line.trim().replace(/^\* /, "<li>") + "</li>";
      } else {
        if (inList) { finalHtml += "</ul>"; inList = false; }
        if (line.trim() !== "") finalHtml += `<p>${line}</p>`;
      }
    });
    if (inList) finalHtml += "</ul>";
    return <div dangerouslySetInnerHTML={{ __html: finalHtml }} />;
  };

  return (
    <div className="App app-root">
      <div className="app-shell">
        <header className="header-card">
          <div className="header-icon">
            <FileSpreadsheet className="header-icon-svg" />
          </div>
          <div className="header-text">
            <h1 className="app-title">SemantiSheet AI Search</h1>
            <p className="app-subtitle">Local RAG: Million-row capable spreadsheet search.</p>
            <div className="tech-pill-row">
              <span className="tech-pill">FastAPI + BGE-Small + Gemini</span>
              <span className="tech-pill">React</span>
            </div>
          </div>
        </header>

        <main className="content-area">
          <section className="search-card" style={{ marginBottom: "1rem" }}>
            <h2>1. Upload &amp; Index</h2>
            <div className="upload-container">
              <div className="file-input-wrapper">
                <label className="custom-file-btn" htmlFor="file-upload">
                  {filesToUpload.length ? `${filesToUpload.length} file(s) selected` : "Choose Files"}
                </label>
                <input id="file-upload" type="file" multiple accept=".xlsx,.xls" onChange={handleFileChange} />
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
            {filesToUpload.length > 0 && (
              <div className="selected-files">
                <ul className="selected-files-list">
                  {filesToUpload.map((file, idx) => <li key={idx}>{file.name}</li>)}
                </ul>
              </div>
            )}
            <div className={`status-card ${indexReady ? 'status-info' : 'status-warning'}`} style={{ marginTop: "0.75rem" }}>
              {indexReady ? "✅ " : "ℹ️ "}{indexMessage}
            </div>
          </section>

          <section className="search-card">
            <h2>2. Ask Questions</h2>
            <form onSubmit={handleSearch} className="search-form-row">
              <div className="search-input-wrapper">
                <Search className="search-input-icon" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Ask about sales, profit, or trends..."
                  disabled={loading || !indexReady}
                  className="search-input"
                />
              </div>
              <button type="submit" disabled={loading || !indexReady} className="btn btn-primary">
                {loading ? "Searching..." : "Search"}
              </button>
            </form>

            <div className="examples-section">
              <div className="examples-chips">
                {exampleQueries.map((ex, idx) => (
                  <button key={idx} type="button" className="chip" onClick={() => setQuery(ex)} disabled={loading || !indexReady}>
                    {ex}
                  </button>
                ))}
              </div>
            </div>

            {error && <div className="status-card status-error"><AlertCircle className="status-icon" />{error}</div>}
          </section>

          {result && (
            <section className="result-card">
              <div className="result-header">
                <h2 className="result-title">Answer</h2>
              </div>
              <div className="synthesis-block">{renderMarkdown(result.result)}</div>
              <button type="button" onClick={() => setShowContext(!showContext)} className="btn btn-secondary context-toggle-btn">
                {showContext ? "Hide Context" : "Show Context"}
              </button>
              {showContext && (
                <div className="context-section">
                  <div className="context-table-container">
                    <table className="context-table">
                      <thead><tr><th>SHEET</th><th>METRIC</th><th>SNIPPET</th></tr></thead>
                      <tbody>
                        {result.context.map((item, i) => (
                          <tr key={i}><td>{item.sheet}</td><td>{item.metric}</td><td>{item.snippet}</td></tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </section>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;