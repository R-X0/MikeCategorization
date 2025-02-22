import React, { useState } from "react";
import "./App.css";

const PDFProcessor = () => {
  const [prompt, setPrompt] = useState("");
  const [file, setFile] = useState(null);
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      alert("Please select a PDF file.");
      return;
    }
    setLoading(true);
    const formData = new FormData();
    formData.append("prompt", prompt);
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/process-pdf", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      // data.response now contains just the text response from Claude
      setResult(data.response || "No response received.");
    } catch (error) {
      console.error("Error:", error);
      setResult("An error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <div className="card">
        <h1>Claude PDF Processor</h1>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="prompt">Prompt:</label>
            <input
              type="text"
              id="prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Enter your question..."
              className="form-control"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="pdfFile">PDF File:</label>
            <input
              type="file"
              id="pdfFile"
              accept="application/pdf"
              onChange={(e) => setFile(e.target.files[0])}
              className="form-control-file"
              required
            />
          </div>
          <button type="submit" className="btn">
            {loading ? "Processing..." : "Submit"}
          </button>
        </form>
        {result && (
          <div className="response">
            <h2>Response from Claude:</h2>
            <p>{result}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default PDFProcessor;
