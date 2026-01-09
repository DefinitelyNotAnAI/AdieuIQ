import React, { useState } from 'react';
import './ExplainabilityPanel.css';

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

interface ExplainabilityPanelProps {
  recommendationId: string;
  agentContributions: AgentContribution[];
  onClose?: () => void;
}

const ExplainabilityPanel: React.FC<ExplainabilityPanelProps> = ({
  recommendationId,
  agentContributions,
  onClose,
}) => {
  // Track which agent sections are expanded
  const [expandedAgents, setExpandedAgents] = useState<Set<string>>(
    new Set(['Retrieval']) // Expand Retrieval by default
  );

  // Toggle agent section expansion
  const toggleAgent = (agentType: string) => {
    const newExpanded = new Set(expandedAgents);
    if (newExpanded.has(agentType)) {
      newExpanded.delete(agentType);
    } else {
      newExpanded.add(agentType);
    }
    setExpandedAgents(newExpanded);
  };

  // Get agent icon based on type
  const getAgentIcon = (agentType: string): string => {
    switch (agentType) {
      case 'Retrieval':
        return '🔍'; // Magnifying glass for data retrieval
      case 'Sentiment':
        return '💭'; // Thought bubble for sentiment analysis
      case 'Reasoning':
        return '🧠'; // Brain for reasoning logic
      case 'Validation':
        return '✅'; // Check mark for validation
      default:
        return '🤖'; // Robot for generic agent
    }
  };

  // Get agent color based on type
  const getAgentColor = (agentType: string): string => {
    switch (agentType) {
      case 'Retrieval':
        return '#1976d2'; // Blue
      case 'Sentiment':
        return '#9c27b0'; // Purple
      case 'Reasoning':
        return '#ff9800'; // Orange
      case 'Validation':
        return '#4caf50'; // Green
      default:
        return '#757575'; // Gray
    }
  };

  // Format confidence score as percentage
  const formatConfidence = (score: number): string => {
    return `${(score * 100).toFixed(1)}%`;
  };

  // Get confidence badge class based on score
  const getConfidenceBadgeClass = (score: number): string => {
    if (score >= 0.8) return 'confidence-high';
    if (score >= 0.5) return 'confidence-medium';
    return 'confidence-low';
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

  // Format execution time
  const formatExecutionTime = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  // Render JSON data in a readable format
  const renderJsonData = (data: Record<string, any>, prefix: string = '') => {
    return (
      <div className="json-data">
        {Object.entries(data).map(([key, value]) => (
          <div key={`${prefix}-${key}`} className="json-entry">
            <span className="json-key">{key}:</span>{' '}
            <span className="json-value">
              {typeof value === 'object' && value !== null
                ? JSON.stringify(value, null, 2)
                : String(value)}
            </span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="explainability-panel">
      <div className="panel-header">
        <h2>Recommendation Reasoning Chain</h2>
        {onClose && (
          <button className="close-button" onClick={onClose} aria-label="Close">
            ×
          </button>
        )}
      </div>

      <div className="panel-description">
        <p>
          This recommendation was generated through a multi-agent AI system. Each agent
          contributes specialized analysis to ensure accurate, relevant, and safe recommendations.
        </p>
      </div>

      <div className="agents-container">
        {agentContributions.map((contribution) => {
          const isExpanded = expandedAgents.has(contribution.agent_type);
          const agentIcon = getAgentIcon(contribution.agent_type);
          const agentColor = getAgentColor(contribution.agent_type);

          return (
            <div
              key={contribution.contribution_id}
              className={`agent-card ${isExpanded ? 'expanded' : 'collapsed'}`}
              style={{ borderLeftColor: agentColor }}
            >
              <div
                className="agent-header"
                onClick={() => toggleAgent(contribution.agent_type)}
                role="button"
                tabIndex={0}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    toggleAgent(contribution.agent_type);
                  }
                }}
              >
                <div className="agent-title">
                  <span className="agent-icon" role="img" aria-label={contribution.agent_type}>
                    {agentIcon}
                  </span>
                  <span className="agent-name">{contribution.agent_type} Agent</span>
                  <span className={`confidence-badge ${getConfidenceBadgeClass(contribution.confidence_score)}`}>
                    {formatConfidence(contribution.confidence_score)}
                  </span>
                </div>
                <span className="expand-icon">{isExpanded ? '▼' : '▶'}</span>
              </div>

              {isExpanded && (
                <div className="agent-details">
                  <div className="agent-metadata">
                    <span className="metadata-item">
                      ⏱️ {formatExecutionTime(contribution.execution_time_ms)}
                    </span>
                    <span className="metadata-item">
                      📅 {formatTimestamp(contribution.created_at)}
                    </span>
                  </div>

                  <div className="agent-section">
                    <h4 className="section-title">Input Data</h4>
                    {renderJsonData(contribution.input_data, 'input')}
                  </div>

                  <div className="agent-section">
                    <h4 className="section-title">Output Result</h4>
                    {renderJsonData(contribution.output_result, 'output')}
                  </div>

                  {/* Special handling for data sources (Retrieval Agent) */}
                  {contribution.agent_type === 'Retrieval' && contribution.output_result.data_sources && (
                    <div className="agent-section">
                      <h4 className="section-title">Data Sources</h4>
                      <div className="data-sources">
                        {contribution.output_result.data_sources.map((source: any, idx: number) => (
                          <div key={idx} className="data-source-item">
                            <span className="source-icon">📄</span>
                            <div className="source-details">
                              <div className="source-title">{source.title || 'Untitled'}</div>
                              {source.timestamp && (
                                <div className="source-timestamp">
                                  {formatTimestamp(source.timestamp)}
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="panel-footer">
        <p className="footer-note">
          <strong>Note:</strong> Agent contributions are stored for audit and transparency purposes
          in compliance with AI governance policies.
        </p>
      </div>
    </div>
  );
};

export default ExplainabilityPanel;
