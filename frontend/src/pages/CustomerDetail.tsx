/**
 * CustomerDetail Page (T044 + T059)
 * 
 * Integrates CustomerProfile, RecommendationList, RecommendationDetail, and HistoryTimeline components.
 * Fetches data from API and manages state for customer detail view.
 * 
 * T059: Add history tab with lazy loading when tab is clicked per quickstart.md optimization tip.
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { CustomerProfile } from '../components/CustomerProfile/CustomerProfile';
import { HistoryTimeline } from '../components/HistoryTimeline/HistoryTimeline';
import { api } from '../services/api-client';
import './CustomerDetail.css';

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

interface CustomerProfileData {
  customer: Customer;
  usage_summary: UsageSummary;
  sentiment_indicators: SentimentIndicators;
}

interface InteractionEvent {
  event_id: string;
  customer_id: string;
  event_type: 'SupportTicket' | 'PhoneCall' | 'ChatInteraction';
  timestamp: string;
  description: string;
  sentiment_score: number;
  resolution_status: 'Pending' | 'Resolved' | 'Escalated';
  tags: string[];
}

interface PastRecommendation {
  recommendation_id: string;
  customer_id: string;
  recommendation_type: 'Adoption' | 'Upsell';
  recommendation_text: string;
  confidence_score: number;
  reasoning_chain: Record<string, any>;
  generation_timestamp: string;
  outcome_status: 'Pending' | 'Delivered' | 'Accepted' | 'Declined';
  delivered_by_agent_id?: string;
  outcome_timestamp?: string;
}

interface CustomerHistory {
  interactions: InteractionEvent[];
  past_recommendations: PastRecommendation[];
}

type TabType = 'profile' | 'recommendations' | 'history';

export const CustomerDetail: React.FC = () => {
  const { customerId } = useParams<{ customerId: string }>();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<TabType>('profile');
  const [profile, setProfile] = useState<CustomerProfileData | null>(null);
  const [history, setHistory] = useState<CustomerHistory | null>(null);
  const [isLoadingProfile, setIsLoadingProfile] = useState(true);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch customer profile on mount
  useEffect(() => {
    if (!customerId) {
      setError('Customer ID is required');
      setIsLoadingProfile(false);
      return;
    }

    fetchCustomerProfile();
  }, [customerId]);

  // Lazy load history when history tab is clicked (per quickstart.md optimization)
  useEffect(() => {
    if (activeTab === 'history' && !history && customerId) {
      fetchCustomerHistory();
    }
  }, [activeTab]);

  const fetchCustomerProfile = async () => {
    if (!customerId) return;

    try {
      setIsLoadingProfile(true);
      setError(null);

      const response = await api.get<CustomerProfileData>(`/customers/${customerId}/profile`);
      setProfile(response.data);
    } catch (err: any) {
      console.error('Failed to fetch customer profile:', err);
      setError(err.response?.data?.detail || 'Failed to load customer profile');
    } finally {
      setIsLoadingProfile(false);
    }
  };

  const fetchCustomerHistory = async () => {
    if (!customerId) return;

    try {
      setIsLoadingHistory(true);
      setError(null);

      const response = await api.get<CustomerHistory>(
        `/customers/${customerId}/history`,
        { params: { months: 12 } }
      );
      setHistory(response.data);
    } catch (err: any) {
      console.error('Failed to fetch customer history:', err);
      setError(err.response?.data?.detail || 'Failed to load customer history');
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const handleBack = () => {
    navigate(-1);
  };

  if (error) {
    return (
      <div className="customer-detail error">
        <div className="error-container">
          <h2>Error</h2>
          <p>{error}</p>
          <button onClick={handleBack} className="back-button">
            Go Back
          </button>
        </div>
      </div>
    );
  }

  if (isLoadingProfile) {
    return (
      <div className="customer-detail loading">
        <div className="loading-spinner"></div>
        <p>Loading customer details...</p>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="customer-detail empty">
        <p>Customer not found</p>
        <button onClick={handleBack} className="back-button">
          Go Back
        </button>
      </div>
    );
  }

  return (
    <div className="customer-detail">
      {/* Header */}
      <div className="detail-header">
        <button onClick={handleBack} className="back-button">
          ← Back
        </button>
        <h1 className="customer-name">{profile.customer.company_name}</h1>
      </div>

      {/* Tabs */}
      <div className="detail-tabs">
        <button
          className={`tab-button ${activeTab === 'profile' ? 'active' : ''}`}
          onClick={() => setActiveTab('profile')}
        >
          Profile
        </button>
        <button
          className={`tab-button ${activeTab === 'recommendations' ? 'active' : ''}`}
          onClick={() => setActiveTab('recommendations')}
        >
          Recommendations
        </button>
        <button
          className={`tab-button ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          History
        </button>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'profile' && (
          <CustomerProfile
            customer={profile.customer}
            usageSummary={profile.usage_summary}
            sentimentIndicators={profile.sentiment_indicators}
          />
        )}

        {activeTab === 'recommendations' && (
          <div className="recommendations-tab">
            <p className="placeholder-text">
              Recommendations feature coming soon. This will display adoption and upsell recommendations
              generated for this customer.
            </p>
          </div>
        )}

        {activeTab === 'history' && (
          <div className="history-tab">
            {isLoadingHistory ? (
              <div className="loading-container">
                <div className="loading-spinner"></div>
                <p>Loading history...</p>
              </div>
            ) : history ? (
              <HistoryTimeline
                interactions={history.interactions}
                pastRecommendations={history.past_recommendations}
              />
            ) : (
              <p className="placeholder-text">No history available</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default CustomerDetail;
