/**
 * CustomerProfile Component (T040)
 * 
 * Display company info, product tier, usage summary, sentiment indicators.
 * Shows comprehensive customer data from CustomerProfile API.
 */

import React from 'react';
import './CustomerProfile.css';

interface Customer {
  account_id: string;
  company_name: string;
  industry_segment: string;
  product_tier: string;
  subscription_start_date: string;
  current_products: string[];
  contact_email?: string;
  contact_phone?: string;
}

interface UsageSummary {
  total_features_available: number;
  high_usage_features: string[];
  medium_usage_features: string[];
  low_usage_features: string[];
  unused_features: string[];
  adoption_rate: number;
  last_updated: string;
}

interface SentimentIndicators {
  overall_sentiment_score: number;
  sentiment_trend: string;
  recent_issues_count: number;
  unresolved_issues_count: number;
  interaction_count: number;
  last_updated: string;
}

interface CustomerProfileProps {
  customer: Customer;
  usageSummary: UsageSummary | null;
  sentimentIndicators: SentimentIndicators | null;
}

export const CustomerProfile: React.FC<CustomerProfileProps> = ({
  customer,
  usageSummary,
  sentimentIndicators,
}) => {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const getSentimentClass = (score: number) => {
    if (score >= 0.5) return 'positive';
    if (score >= 0) return 'neutral';
    return 'negative';
  };

  const getSentimentEmoji = (score: number) => {
    if (score >= 0.5) return '😊';
    if (score >= 0) return '😐';
    return '😟';
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'improving':
        return '📈';
      case 'declining':
        return '📉';
      default:
        return '➡️';
    }
  };

  return (
    <div className="customer-profile">
      {/* Basic Info Section */}
      <div className="profile-section info-section">
        <h2 className="section-title">Customer Information</h2>
        <div className="info-grid">
          <div className="info-item">
            <span className="info-label">Company Name</span>
            <span className="info-value company-name">{customer.company_name}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Industry</span>
            <span className="info-value">{customer.industry_segment}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Product Tier</span>
            <span className={`info-value tier-badge tier-${customer.product_tier.toLowerCase()}`}>
              {customer.product_tier}
            </span>
          </div>
          <div className="info-item">
            <span className="info-label">Customer Since</span>
            <span className="info-value">{formatDate(customer.subscription_start_date)}</span>
          </div>
          {customer.contact_email && (
            <div className="info-item">
              <span className="info-label">Contact Email</span>
              <span className="info-value">{customer.contact_email}</span>
            </div>
          )}
          {customer.contact_phone && (
            <div className="info-item">
              <span className="info-label">Contact Phone</span>
              <span className="info-value">{customer.contact_phone}</span>
            </div>
          )}
        </div>
        <div className="info-item full-width">
          <span className="info-label">Current Products ({customer.current_products.length})</span>
          <div className="products-list">
            {customer.current_products.map((product, index) => (
              <span key={index} className="product-badge">
                {product}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Usage Summary Section */}
      {usageSummary && (
        <div className="profile-section usage-section">
          <h2 className="section-title">Feature Usage Summary</h2>
          <div className="adoption-meter">
            <div className="meter-label">
              <span>Adoption Rate</span>
              <span className="meter-value">{(usageSummary.adoption_rate * 100).toFixed(1)}%</span>
            </div>
            <div className="meter-bar">
              <div
                className="meter-fill"
                style={{ width: `${usageSummary.adoption_rate * 100}%` }}
              />
            </div>
          </div>

          <div className="usage-grid">
            {usageSummary.high_usage_features.length > 0 && (
              <div className="usage-category high-usage">
                <h3 className="usage-category-title">
                  <span className="usage-icon">🔥</span>
                  High Usage
                </h3>
                <ul className="feature-list">
                  {usageSummary.high_usage_features.map((feature, index) => (
                    <li key={index} className="feature-item">
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {usageSummary.medium_usage_features.length > 0 && (
              <div className="usage-category medium-usage">
                <h3 className="usage-category-title">
                  <span className="usage-icon">📊</span>
                  Medium Usage
                </h3>
                <ul className="feature-list">
                  {usageSummary.medium_usage_features.map((feature, index) => (
                    <li key={index} className="feature-item">
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {usageSummary.low_usage_features.length > 0 && (
              <div className="usage-category low-usage">
                <h3 className="usage-category-title">
                  <span className="usage-icon">📉</span>
                  Low Usage
                </h3>
                <ul className="feature-list">
                  {usageSummary.low_usage_features.map((feature, index) => (
                    <li key={index} className="feature-item">
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {usageSummary.unused_features.length > 0 && (
              <div className="usage-category unused">
                <h3 className="usage-category-title">
                  <span className="usage-icon">💤</span>
                  Not Used
                </h3>
                <ul className="feature-list">
                  {usageSummary.unused_features.map((feature, index) => (
                    <li key={index} className="feature-item">
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="section-footer">
            <span className="last-updated">Last updated: {formatDate(usageSummary.last_updated)}</span>
          </div>
        </div>
      )}

      {/* Sentiment Indicators Section */}
      {sentimentIndicators && (
        <div className="profile-section sentiment-section">
          <h2 className="section-title">Customer Sentiment</h2>
          
          <div className="sentiment-overview">
            <div className="sentiment-score">
              <span className="sentiment-emoji">
                {getSentimentEmoji(sentimentIndicators.overall_sentiment_score)}
              </span>
              <div className="sentiment-details">
                <span className={`sentiment-value ${getSentimentClass(sentimentIndicators.overall_sentiment_score)}`}>
                  {sentimentIndicators.overall_sentiment_score.toFixed(2)}
                </span>
                <span className="sentiment-label">Overall Score</span>
              </div>
            </div>

            <div className="sentiment-trend">
              <span className="trend-icon">{getTrendIcon(sentimentIndicators.sentiment_trend)}</span>
              <div className="trend-details">
                <span className="trend-value">{sentimentIndicators.sentiment_trend}</span>
                <span className="trend-label">Trend</span>
              </div>
            </div>
          </div>

          <div className="sentiment-stats">
            <div className="stat-item">
              <span className="stat-value">{sentimentIndicators.interaction_count}</span>
              <span className="stat-label">Total Interactions</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{sentimentIndicators.recent_issues_count}</span>
              <span className="stat-label">Recent Issues</span>
            </div>
            <div className="stat-item">
              <span className={`stat-value ${sentimentIndicators.unresolved_issues_count > 0 ? 'warning' : ''}`}>
                {sentimentIndicators.unresolved_issues_count}
              </span>
              <span className="stat-label">Unresolved Issues</span>
            </div>
          </div>

          <div className="section-footer">
            <span className="last-updated">Last updated: {formatDate(sentimentIndicators.last_updated)}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default CustomerProfile;
