import React, { useState } from "react";
import "./App.css";

const PDFProcessor = () => {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");
  const [downloadUrl, setDownloadUrl] = useState("");
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      alert("Please select a file.");
      return;
    }
    setLoading(true);
    setMessage("");
    setDownloadUrl("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/process-pdf", {
        method: "POST",
        body: formData,
      });
      
      if (!res.ok) {
        throw new Error(`Server responded with status: ${res.status}`);
      }
      
      const data = await res.json();
      console.log("Response:", data.response);
      
      // Use the response as plain text
      const text = data.response;
      const blob = new Blob([text], { type: "text/plain" });
      const url = window.URL.createObjectURL(blob);
      setDownloadUrl(url);
      setMessage("Document processed successfully!");
    } catch (error) {
      console.error("Processing error:", error);
      setMessage("An error occurred: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
              <polyline points="14 2 14 8 20 8" />
              <path d="M8 13h2" />
              <path d="M8 17h2" />
              <path d="M14 13h2" />
              <path d="M14 17h2" />
            </svg>
            <span>DocuExtract</span>
          </div>
        </div>
      </header>

      <div className="container">
        <div className="card">
          <div className="section-title">Document Processing</div>
          <h1>Extract Structured Data from Documents</h1>
          <p className="description">
            Upload a PDF or image to extract structured information using advanced AI processing.
          </p>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="pdfFile" className="form-label">Upload Document</label>
              <div className="file-input-container">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
                <div className="file-input-text">
                  <div className="file-input-title">Choose a file or drag and drop</div>
                  <div className="file-input-description">PDF, JPG, PNG (max. 10MB)</div>
                </div>
                <input
                  type="file"
                  id="pdfFile"
                  accept="application/pdf, image/*"
                  className="file-input"
                  onChange={handleFileChange}
                  required
                />
              </div>
              {file && (
                <div className="file-name">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                    <polyline points="22 4 12 14.01 9 11.01" />
                  </svg>
                  {file.name}
                </div>
              )}
            </div>

            <button type="submit" className="btn" disabled={loading || !file}>
              {loading ? (
                <>
                  <svg className="btn-icon animate-spin" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="12" y1="2" x2="12" y2="6" />
                    <line x1="12" y1="18" x2="12" y2="22" />
                    <line x1="4.93" y1="4.93" x2="7.76" y2="7.76" />
                    <line x1="16.24" y1="16.24" x2="19.07" y2="19.07" />
                    <line x1="2" y1="12" x2="6" y2="12" />
                    <line x1="18" y1="12" x2="22" y2="12" />
                    <line x1="4.93" y1="19.07" x2="7.76" y2="16.24" />
                    <line x1="16.24" y1="7.76" x2="19.07" y2="4.93" />
                  </svg>
                  Processing...
                </>
              ) : (
                <>
                  <svg className="btn-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                    <polyline points="23 3 12 14 9 11" />
                  </svg>
                  Extract Data
                </>
              )}
            </button>
          </form>

          {loading && (
            <div className="loading-indicator">
              <div className="spinner"></div>
            </div>
          )}

          {(message || downloadUrl) && (
            <div className="result-container">
              {message && (
                <div className="result-message">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                    <polyline points="22 4 12 14.01 9 11.01" />
                  </svg>
                  {message}
                </div>
              )}

              {downloadUrl && (
                <a href={downloadUrl} download="document_data.json" className="download-btn">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                  Download Structured Data
                </a>
              )}
            </div>
          )}
        </div>
      </div>

      <footer className="footer">
        <p>© {new Date().getFullYear()} DocuExtract. All rights reserved.</p>
      </footer>
    </div>
  );
};

export default PDFProcessor;