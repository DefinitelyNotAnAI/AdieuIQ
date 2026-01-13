import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import CustomerDetail from './pages/CustomerDetail';
import DashboardPage from './pages/DashboardPage';
import contosoLogo from './assets/contoso-logo.png';
import './App.css';

/**
 * Main application component with routing
 */
const App: React.FC = () => {
  return (
    <Router>
      <div className="app">
        <header className="app-header">
          <img src={contosoLogo} alt="Contoso Resorts" className="app-header-logo" />
          <div className="app-header-content">
            <h1>Contoso Resorts</h1>
            <p>Guest Experience Intelligence Platform</p>
          </div>
        </header>
        <main className="app-main">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/customer/:customerId" element={<CustomerDetail />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
};

export default App;

