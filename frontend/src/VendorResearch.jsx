// Create this file as frontend/src/VendorResearch.jsx
import React, { useState } from "react";
import "./App.css";

const VendorResearch = ({ vendorName, jsonData }) => {
  const [vendorInfo, setVendorInfo] = useState("");
  const [searchSuggestionsHtml, setSearchSuggestionsHtml] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const researchVendor = async () => {
    if (!vendorName) return;
    
    setLoading(true);
    setError("");
    
    try {
      const response = await fetch("http://localhost:8000/research-vendor", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ vendor_name: vendorName }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.error) {
        setError(data.error);
      } else {
        setVendorInfo(data.vendorInfo);
        setSearchSuggestionsHtml(data.searchSuggestionsHtml);
      }
    } catch (err) {
      setError(`Failed to research vendor: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Function to safely render HTML provided by the API (search suggestions)
  const renderSearchSuggestions = () => {
    if (!searchSuggestionsHtml) return null;
    
    return (
      <div 
        className="search-suggestions-container"
        dangerouslySetInnerHTML={{ __html: searchSuggestionsHtml }}
      />
    );
  };

  return (
    <div className="vendor-research">
      <h3 className="section-title">Vendor Information</h3>
      
      <div className="vendor-details">
        <p>
          <strong>Vendor Name:</strong> {vendorName || "Not available"}
        </p>
        
        {jsonData && jsonData.partyInformation && jsonData.partyInformation.vendor && (
          <>
            <p>
              <strong>Address:</strong> {jsonData.partyInformation.vendor.address || "Not available"}
            </p>
            <p>
              <strong>Contact:</strong> {jsonData.partyInformation.vendor.contact || "Not available"}
            </p>
            <p>
              <strong>Tax ID:</strong> {jsonData.partyInformation.vendor.taxID || "Not available"}
            </p>
          </>
        )}
      </div>
      
      <button 
        onClick={researchVendor} 
        className="btn research-btn"
        disabled={loading || !vendorName}
      >
        {loading ? (
          <span className="spinner-button">
            <svg className="spinner-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="2" x2="12" y2="6" />
              <line x1="12" y1="18" x2="12" y2="22" />
              <line x1="4.93" y1="4.93" x2="7.76" y2="7.76" />
              <line x1="16.24" y1="16.24" x2="19.07" y2="19.07" />
              <line x1="2" y1="12" x2="6" y2="12" />
              <line x1="18" y1="12" x2="22" y2="12" />
              <line x1="4.93" y1="19.07" x2="7.76" y2="16.24" />
              <line x1="16.24" y1="7.76" x2="19.07" y2="4.93" />
            </svg>
            Researching...
          </span>
        ) : (
          <>
            <svg className="btn-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            Research Vendor
          </>
        )}
      </button>
      
      {error && (
        <div className="error-message">
          {error}
        </div>
      )}
      
      {vendorInfo && (
        <div className="vendor-info">
          <h4>About this Vendor</h4>
          <p>{vendorInfo}</p>
          
          {/* Render Google Search Suggestions */}
          {renderSearchSuggestions()}
        </div>
      )}
    </div>
  );
};

export default VendorResearch;