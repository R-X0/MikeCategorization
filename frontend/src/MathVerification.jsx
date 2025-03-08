import React, { useState } from "react";

const MathVerification = ({ verificationData }) => {
  const [showAllDiscrepancies, setShowAllDiscrepancies] = useState(false);
  
  if (!verificationData) {
    return null;
  }

  const { mathVerified, discrepancies = [], summary } = verificationData;
  
  // Group discrepancies by significance
  const highSignificance = discrepancies.filter(d => d.significance === "High");
  const mediumSignificance = discrepancies.filter(d => d.significance === "Medium");
  const lowSignificance = discrepancies.filter(d => d.significance === "Low" || !d.significance);
  
  // Determine which discrepancies to show based on the toggle state
  const visibleDiscrepancies = showAllDiscrepancies 
    ? discrepancies 
    : [...highSignificance, ...mediumSignificance.slice(0, 3)];

  // Calculate if we're hiding any discrepancies
  const hiddenCount = discrepancies.length - visibleDiscrepancies.length;

  return (
    <div className="math-verification">
      <h3 className="section-title">Math Verification</h3>
      
      <div className={`verification-status ${mathVerified ? 'verified' : 'issues'}`}>
        <div className="status-icon">
          {mathVerified ? (
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          )}
        </div>
        <div className="status-message">
          <strong>{mathVerified ? "Calculations Verified" : "Calculation Issues Detected"}</strong>
          <p>{summary}</p>
        </div>
      </div>
      
      {visibleDiscrepancies.length > 0 && (
        <div className="discrepancies-container">
          <div className="discrepancies-header">
            <h4>
              Discrepancies Found
              {highSignificance.length > 0 && (
                <span className="high-significance-badge">
                  {highSignificance.length} High Significance
                </span>
              )}
            </h4>
            
            {discrepancies.length > 3 && (
              <button 
                className="toggle-discrepancies-btn"
                onClick={() => setShowAllDiscrepancies(!showAllDiscrepancies)}
              >
                {showAllDiscrepancies ? "Show Important Only" : `Show All (${discrepancies.length})`}
              </button>
            )}
          </div>
          
          <table className="discrepancies-table">
            <thead>
              <tr>
                <th>Significance</th>
                <th>Type</th>
                <th>Location</th>
                <th>Expected</th>
                <th>Document Value</th>
                <th>Correction</th>
              </tr>
            </thead>
            <tbody>
              {visibleDiscrepancies.map((discrepancy, index) => (
                <tr key={index} className={`significance-${discrepancy.significance || 'low'}`}>
                  <td className={`significance-cell ${discrepancy.significance || 'low'}`}>
                    {discrepancy.significance || 'Low'}
                  </td>
                  <td>{discrepancy.type}</td>
                  <td>{discrepancy.location}</td>
                  <td className="numeric">{typeof discrepancy.expected === 'number' ? 
                       discrepancy.expected.toFixed(2) : discrepancy.expected}</td>
                  <td className="numeric error-value">{typeof discrepancy.actual === 'number' ? 
                       discrepancy.actual.toFixed(2) : discrepancy.actual}</td>
                  <td className="numeric correction-value">{typeof discrepancy.correction === 'number' ? 
                       discrepancy.correction.toFixed(2) : discrepancy.correction}</td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {hiddenCount > 0 && !showAllDiscrepancies && (
            <div className="hidden-discrepancies-notice">
              {hiddenCount} less significant {hiddenCount === 1 ? 'issue' : 'issues'} hidden. 
              <button 
                className="show-all-link"
                onClick={() => setShowAllDiscrepancies(true)}
              >
                Show all
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default MathVerification;