import React, { useState } from "react";
import "./App.css";

const VendorResearch = ({ vendorName, jsonData }) => {
  const [vendorInfo, setVendorInfo] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [financialCategorization, setFinancialCategorization] = useState(null);
  const [debugInfo, setDebugInfo] = useState("");

  // Helper function to extract JSON from markdown code blocks
  const extractJsonFromMarkdown = (text) => {
    // Check if the text contains markdown code blocks with JSON
    const jsonCodeBlockRegex = /```(?:json)?\s*([\s\S]*?)```/;
    const match = text.match(jsonCodeBlockRegex);
    
    if (match && match[1]) {
      return match[1].trim();
    }
    
    return text;
  };

  const researchVendor = async () => {
    if (!vendorName) return;
    
    setLoading(true);
    setError("");
    setFinancialCategorization(null);
    setDebugInfo("");
    
    try {
      console.log("Sending request to research vendor:", vendorName);
      
      const response = await fetch("http://localhost:8000/research-vendor", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ vendor_name: vendorName }),
      });
      
      console.log("Received response:", response);
      
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      
      // Get the response data
      const data = await response.json();
      console.log("Response data:", data);
      
      if (data.error) {
        setError(data.error);
        return;
      }
      
      if (!data.response) {
        setError("Invalid response from server");
        setDebugInfo(JSON.stringify(data, null, 2));
        return;
      }
      
      // Extract JSON if it's wrapped in markdown code blocks
      const cleanedJsonText = extractJsonFromMarkdown(data.response);
      console.log("Cleaned JSON text:", cleanedJsonText);
      
      // Now try to parse the cleaned text as JSON
      try {
        const parsedData = JSON.parse(cleanedJsonText);
        console.log("Parsed vendor data:", parsedData);
        
        // Set vendor information
        setVendorInfo(parsedData.vendorInfo || "");
        
        // Set financial categorization if available
        if (parsedData.financialCategorization) {
          setFinancialCategorization(parsedData.financialCategorization);
        } else {
          console.warn("No financial categorization in response");
        }
      } catch (parseError) {
        console.error("Error parsing JSON from Gemini:", parseError);
        setError("Failed to parse vendor information. The response was not valid JSON.");
        setDebugInfo(data.response);
        
        // Attempt to display in a more readable format
        setVendorInfo("Could not extract structured information for this vendor.");
      }
    } catch (err) {
      console.error("Error in vendor research:", err);
      setError(`Failed to research vendor: ${err.message}`);
      setDebugInfo(err.toString());
    } finally {
      setLoading(false);
    }
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
          {debugInfo && (
            <div className="debug-info">
              <details>
                <summary>Debug Information</summary>
                <pre>{debugInfo}</pre>
              </details>
            </div>
          )}
        </div>
      )}
      
      {vendorInfo && (
        <div className="vendor-info">
          <h4>About this Vendor</h4>
          <p>{vendorInfo}</p>
          
          {/* Financial Categorization Section */}
          {financialCategorization && (
            <div className="financial-categorization">
              <h4>Financial Categorization</h4>
              <div className="categorization-card">
                <div className="categorization-header">
                  <span 
                    className="category-tag"
                    data-type={financialCategorization.ledgerEntryType.split(' ')[0]}
                  >
                    {financialCategorization.ledgerEntryType}
                  </span>
                  <span className="category-name">{financialCategorization.mostLikelyAnswer}</span>
                </div>
                <div className="categorization-details">
                  <p><strong>Category:</strong> {financialCategorization.category}</p>
                  <p><strong>Subcategory:</strong> {financialCategorization.subcategory}</p>
                  <p><strong>Description:</strong> {financialCategorization.description}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default VendorResearch;