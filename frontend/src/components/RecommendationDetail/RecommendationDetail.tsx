import React, { useState } from 'react';
import ExplainabilityPanel from '../ExplainabilityPanel/ExplainabilityPanel';
import { getExplainability } from '../../services/api-client';
import './RecommendationDetail.css';

// Recommendation structure from OpenAPI spec
interface Recommendation {
  recommendation_id: string;
  customer_id: string;
  recommendation_type: 'Adoption' | 'Upsell';
  text_description: string;
  confidence_score: number;
  reasoning_chain: {
    retrieval: string;
    sentiment: string;
    reasoning: string;
  };
  generation_timestamp: string;
  outcome_status?: 'Pending' | 'Accepted' | 'Declined';
}

// Agent contribution structure from OpenAPI spec
interface AgentContribution {
  contribution_id: string;
  agent_type: 'Retrieval' | 'Sentiment' | 'Reasoning' | 'Validation';
  input_data: Record<string, any>;
  output_result: Record<string, any>;
  confidence_score: number;
  execution_time_ms: number;
  created_at: string;
}

interface RecommendationDetailProps {
  recommendation: Recommendation;
  onOutcomeUpdate?: (recommendationId: string, outcome: 'Accepted' | 'Declined') => void;
}

const RecommendationDetail: React.FC<RecommendationDetailProps> = ({
  recommendation,
  onOutcomeUpdate,
}) => {
  const [showExplainability, setShowExplainability] = useState(false);
  const [agentContributions, setAgentContributions] = useState<AgentContribution[]>([]);
  const [isLoadingExplainability, setIsLoadingExplainability] = useState(false);
  const [explainabilityError, setExplainabilityError] = useState<string | null>(null);

  // Fetch explainability data when "Show reasoning" is clicked
  const handleShowReasoning = async () => {
    if (showExplainability) {
      // If already shown, just close it
      setShowExplainability(false);
      return;
    }

    // Fetch agent contributions
    setIsLoadingExplainability(true);
    setExplainabilityError(null);

    try {
      const result = await getExplainability(recommendation.recommendation_id);
      setAgentContributions(result.agent_contributions);
      setShowExplainability(true);
    } catch (error) {
      console.error('Failed to fetch explainability:', error);
      setExplainabilityError('Failed to load reasoning details. Please try again.');
    } finally {
      setIsLoadingExplainability(false);
    }
  };

  // Handle outcome button clicks
  const handleOutcome = (outcome: 'Accepted' | 'Declined') => {
    if (onOutcomeUpdate) {
      onOutcomeUpdate(recommendation.recommendation_id, outcome);
    }
  };

  // Format timestamp
  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Get confidence badge class
  const getConfidenceBadgeClass = (score: number): string => {
    if (score >= 0.8) return 'confidence-high';
    if (score >= 0.5) return 'confidence-medium';
    return 'confidence-low';
  };

  // Get outcome badge class
  const getOutcomeBadgeClass = (outcome?: string): string => {
    switch (outcome) {
      case 'Accepted':
        return 'outcome-accepted';
      case 'Declined':
        return 'outcome-declined';
      case 'Pending':
      default:
        return 'outcome-pending';
    }
  };

  return (
    <div className="recommendation-detail">
      <div className="detail-card">
        {/* Header */}
        <div className="detail-header">
          <div className="header-left">
            <span className={`type-badge ${recommendation.recommendation_type.toLowerCase()}`}>
              {recommendation.recommendation_type}
            </span>
            <span className={`outcome-badge ${getOutcomeBadgeClass(recommendation.outcome_status)}`}>
              {recommendation.outcome_status || 'Pending'}
            </span>
          </div>
          <div className="header-right">
            <span className={`confidence-badge ${getConfidenceBadgeClass(recommendation.confidence_score)}`}>
              Confidence: {(recommendation.confidence_score * 100).toFixed(1)}%
            </span>
          </div>
        </div>

        {/* Description */}
        <div className="detail-body">
          <h3 className="recommendation-title">Recommendation</h3>
          <p className="recommendation-text">{recommendation.text_description}</p>

          {/* Reasoning Chain Summary */}
          <div className="reasoning-summary">
            <h4 className="summary-title">Quick Reasoning Summary</h4>
            <div className="summary-grid">
              <div className="summary-item">
                <span className="summary-label">🔍 Retrieval:</span>
                <span className="summary-value">{recommendation.reasoning_chain.retrieval}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">💭 Sentiment:</span>
                <span className="summary-value">{recommendation.reasoning_chain.sentiment}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">🧠 Reasoning:</span>
                <span className="summary-value">{recommendation.reasoning_chain.reasoning}</span>
              </div>
            </div>
          </div>

          {/* Metadata */}
          <div className="detail-metadata">
            <span className="metadata-item">
              📅 Generated: {formatTimestamp(recommendation.generation_timestamp)}
            </span>
            <span className="metadata-item">
              🆔 ID: {recommendation.recommendation_id.substring(0, 8)}...
            </span>
          </div>
        </div>

        {/* Actions */}
        <div className="detail-actions">
          <button
            className="btn-reasoning"
            onClick={handleShowReasoning}
            disabled={isLoadingExplainability}
          >
            {isLoadingExplainability ? (
              <>
                <span className="spinner"></span>
                Loading...
              </>
            ) : showExplainability ? (
              'Hide Reasoning'
            ) : (
              '🔍 Show Reasoning'
            )}
          </button>

          {recommendation.outcome_status === 'Pending' && (
            <div className="outcome-buttons">
              <button
                className="btn-accept"
                onClick={() => handleOutcome('Accepted')}
              >
                ✓ Accept
              </button>
              <button
                className="btn-decline"
                onClick={() => handleOutcome('Declined')}
              >
                ✗ Decline
              </button>
            </div>
          )}
        </div>

        {/* Error Message */}
        {explainabilityError && (
          <div className="error-message">
            <span className="error-icon">⚠️</span>
            {explainabilityError}
          </div>
        )}
      </div>

      {/* Explainability Modal/Drawer */}
      {showExplainability && agentContributions.length > 0 && (
        <div className="explainability-modal">
          <div className="modal-overlay" onClick={() => setShowExplainability(false)} />
          <div className="modal-content">
            <ExplainabilityPanel
              recommendationId={recommendation.recommendation_id}
              agentContributions={agentContributions}
              onClose={() => setShowExplainability(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default RecommendationDetail;
