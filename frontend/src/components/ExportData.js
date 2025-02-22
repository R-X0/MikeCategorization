import React, { useState } from 'react';

function ExportData() {
  const [format, setFormat] = useState("csv");
  const [exportData, setExportData] = useState("");
  const [loading, setLoading] = useState(false);

  const handleExport = () => {
    setLoading(true);
    fetch(`/api/export?format=${format}`)
      .then((res) => res.json())
      .then((data) => {
        setExportData(data.export_data);
        setLoading(false);
      })
      .catch((error) => {
        console.error("Export error:", error);
        setExportData("Error during export.");
        setLoading(false);
      });
  };

  return (
    <div className="export-data">
      <div className="export-controls">
        <select value={format} onChange={(e) => setFormat(e.target.value)}>
          <option value="csv">CSV</option>
          <option value="json">JSON</option>
          <option value="xml">XML</option>
          <option value="qbo">QBO</option>
        </select>
        <button onClick={handleExport}>Export</button>
      </div>
      {loading ? (
        <p>Exporting data...</p>
      ) : (
        <pre className="export-output">{exportData}</pre>
      )}
    </div>
  );
}

export default ExportData;
