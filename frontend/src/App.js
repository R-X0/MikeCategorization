import React from 'react';
import FileUpload from './components/FileUpload';
import TransactionsTable from './components/TransactionsTable';
import ExportData from './components/ExportData';
import './App.css';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>Automated Transaction Processing Platform</h1>
      </header>
      <main>
        <section id="upload-section" className="section">
          <h2>Upload Files</h2>
          <FileUpload />
        </section>
        <section id="transactions-section" className="section">
          <h2>Processed Transactions</h2>
          <TransactionsTable />
        </section>
        <section id="export-section" className="section">
          <h2>Export Data</h2>
          <ExportData />
        </section>
      </main>
      <footer>
        <p>&copy; 2025 Your Company Name. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default App;
