import React, { useState } from "react";
import "./App.css";

const PDFProcessor = () => {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");
  const [downloadUrl, setDownloadUrl] = useState("");
  const [loading, setLoading] = useState(false);

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
      const data = await res.json();
      console.log("Response:", data.response);
      
      // Use the response as plain text.
      const text = data.response;
      const blob = new Blob([text], { type: "text/plain" });
      const url = window.URL.createObjectURL(blob);
      setDownloadUrl(url);
      setMessage("Finished processing");
    } catch (error) {
      console.error("Processing error:", error);
      setMessage("An error occurred: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <div className="card">
        <h1>Gemini PDF Processor</h1>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="pdfFile">File (PDF or Image):</label>
            <input
              type="file"
              id="pdfFile"
              accept="application/pdf, image/*"
              onChange={(e) => setFile(e.target.files[0])}
              className="form-control-file"
              required
            />
          </div>
          <button type="submit" className="btn">
            {loading ? "Processing..." : "Submit"}
          </button>
        </form>
        {message && (
          <div className="response">
            <h2>{message}</h2>
          </div>
        )}
        {downloadUrl && (
          <div className="download">
            <a href={downloadUrl} download="document_data.txt" className="btn">
              Download Text Document
            </a>
          </div>
        )}
      </div>
    </div>
  );
};

export default PDFProcessor;
