/**
 * CustomerSearch Component (T039)
 * 
 * Search input with fuzzy matching, result list, click to select customer.
 * Implements FR-001: Fuzzy search on company name.
 */

import React, { useState, useCallback } from 'react';
import { api, getErrorMessage } from '../../services/api-client';
import './CustomerSearch.css';

interface CustomerSearchResult {
  account_id: string;
  company_name: string;
  industry_segment: string;
  product_tier: string;
  subscription_start_date: string;
  current_products: string[];
  contact_email?: string;
  match_score: number;
}

interface CustomerSearchProps {
  onSelectCustomer: (customerId: string) => void;
}

export const CustomerSearch: React.FC<CustomerSearchProps> = ({ onSelectCustomer }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<CustomerSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) {
      setError('Please enter a search term');
      return;
    }

    setLoading(true);
    setError(null);
    setSearched(true);

    try {
      const response = await api.get<CustomerSearchResult[]>(
        `/customers/search?query=${encodeURIComponent(query)}&limit=20&min_score=60`
      );
      setResults(response.data);
    } catch (err) {
      setError(getErrorMessage(err));
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [query]);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleSelectCustomer = (customerId: string) => {
    onSelectCustomer(customerId);
  };

  return (
    <div className="customer-search">
      <div className="search-input-container">
        <input
          type="text"
          className="search-input"
          placeholder="Search by company name..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={loading}
        />
        <button
          className="search-button"
          onClick={handleSearch}
          disabled={loading || !query.trim()}
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>

      {error && (
        <div className="search-error" role="alert">
          <span className="error-icon">⚠️</span>
          {error}
        </div>
      )}

      {searched && !loading && results.length === 0 && !error && (
        <div className="search-no-results">
          <span className="no-results-icon">🔍</span>
          <p>No customers found matching "{query}"</p>
          <p className="no-results-hint">Try a different search term or check the spelling</p>
        </div>
      )}

      {results.length > 0 && (
        <div className="search-results">
          <div className="results-header">
            <span className="results-count">{results.length} customers found</span>
          </div>
          <ul className="results-list">
            {results.map((customer) => (
              <li
                key={customer.account_id}
                className="result-item"
                onClick={() => handleSelectCustomer(customer.account_id)}
                role="button"
                tabIndex={0}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    handleSelectCustomer(customer.account_id);
                  }
                }}
              >
                <div className="result-item-header">
                  <h3 className="company-name">{customer.company_name}</h3>
                  <span className="match-score" title="Match score">
                    {customer.match_score}% match
                  </span>
                </div>
                <div className="result-item-details">
                  <span className="industry-segment" title="Industry">
                    {customer.industry_segment}
                  </span>
                  <span className="separator">•</span>
                  <span className="product-tier" title="Tier">
                    {customer.product_tier}
                  </span>
                  <span className="separator">•</span>
                  <span className="products-count" title="Products">
                    {customer.current_products.length} products
                  </span>
                </div>
                {customer.contact_email && (
                  <div className="result-item-contact">
                    <span className="contact-email">{customer.contact_email}</span>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default CustomerSearch;
