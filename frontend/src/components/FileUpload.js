import React, { useState } from 'react';

function FileUpload() {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadStatus, setUploadStatus] = useState("");

  const handleFiles = (files) => {
    setSelectedFiles([...files]);
  };

  const onDrop = (event) => {
    event.preventDefault();
    event.stopPropagation();
    const files = event.dataTransfer.files;
    if (files && files.length > 0) {
      handleFiles(files);
    }
  };

  const onDragOver = (event) => {
    event.preventDefault();
    event.stopPropagation();
  };

  const handleFileInputChange = (event) => {
    handleFiles(event.target.files);
  };

  const handleUpload = () => {
    if (selectedFiles.length === 0) {
      setUploadStatus("Please select at least one file.");
      return;
    }
    setUploadStatus("Uploading...");
    const formData = new FormData();
    Array.from(selectedFiles).forEach((file) => {
      formData.append('files', file);
    });
    fetch("/api/upload", {
      method: "POST",
      body: formData
    })
      .then(response => response.json())
      .then(data => {
        setUploadStatus("Upload successful!");
        // Optionally trigger a refresh of transactions here.
      })
      .catch(error => {
        console.error("Upload error:", error);
        setUploadStatus("Error during file upload.");
      });
  };

  return (
    <div className="file-upload">
      <div 
        className="dropzone"
        onDrop={onDrop}
        onDragOver={onDragOver}
      >
        <p>Drag &amp; drop files here, or click to select files.</p>
        <input type="file" multiple onChange={handleFileInputChange} />
      </div>
      {selectedFiles.length > 0 && (
        <div className="file-list">
          <h3>Selected Files:</h3>
          <ul>
            {Array.from(selectedFiles).map((file, index) => (
              <li key={index}>{file.name}</li>
            ))}
          </ul>
          <button onClick={handleUpload}>Upload Files</button>
        </div>
      )}
      {uploadStatus && <p className="upload-status">{uploadStatus}</p>}
    </div>
  );
}

export default FileUpload;
