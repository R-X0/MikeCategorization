// File: TransactionsTable.js
import React, { useState, useEffect } from 'react';

function TransactionsTable() {
  const [transactions, setTransactions] = useState([]);

  const loadTransactions = () => {
    fetch("/api/transactions")
      .then((res) => res.json())
      .then((data) => {
        setTransactions(data.transactions);
      })
      .catch((error) => {
        console.error("Error loading transactions:", error);
      });
  };

  useEffect(() => {
    loadTransactions();
  }, []);

  return (
    <section>
      <h2>Processed Transactions</h2>
      <button onClick={loadTransactions}>Refresh Transactions</button>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Date</th>
            <th>Amount</th>
            <th>Description</th>
            <th>Account Code</th>
            <th>Category</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((tx) => (
            <tr key={tx.transaction_id}>
              <td>{tx.transaction_id}</td>
              <td>{tx.transaction_date}</td>
              <td>{tx.amount}</td>
              <td>{tx.description}</td>
              <td>{tx.account_code}</td>
              <td>{tx.category}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export default TransactionsTable;
