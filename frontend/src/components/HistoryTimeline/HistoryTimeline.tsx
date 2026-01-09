/**
 * HistoryTimeline Component (T058)
 * 
 * Chronological display of tickets/chats/calls, recommendation events, outcome status badges.
 * Shows historical interaction context per FR-013.
 */

import React, { useState } from 'react';
import './HistoryTimeline.css';

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

interface HistoryTimelineProps {
  interactions: InteractionEvent[];
  pastRecommendations: PastRecommendation[];
  isLoading?: boolean;
}

type TimelineEvent = {
  type: 'interaction' | 'recommendation';
  timestamp: string;
  data: InteractionEvent | PastRecommendation;
};

export const HistoryTimeline: React.FC<HistoryTimelineProps> = ({
  interactions,
  pastRecommendations,
  isLoading = false,
}) => {
  const [filterType, setFilterType] = useState<'all' | 'interactions' | 'recommendations'>('all');

  // Merge and sort events by timestamp
  const getTimelineEvents = (): TimelineEvent[] => {
    const interactionEvents: TimelineEvent[] = interactions.map(i => ({
      type: 'interaction' as const,
      timestamp: i.timestamp,
      data: i,
    }));

    const recommendationEvents: TimelineEvent[] = pastRecommendations.map(r => ({
      type: 'recommendation' as const,
      timestamp: r.generation_timestamp,
      data: r,
    }));

    const allEvents = [...interactionEvents, ...recommendationEvents];
    
    // Sort by timestamp descending (most recent first)
    allEvents.sort((a, b) => {
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    });

    // Apply filter
    if (filterType === 'interactions') {
      return allEvents.filter(e => e.type === 'interaction');
    } else if (filterType === 'recommendations') {
      return allEvents.filter(e => e.type === 'recommendation');
    }

    return allEvents;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getEventTypeIcon = (eventType: string) => {
    switch (eventType) {
      case 'SupportTicket':
        return '🎫';
      case 'PhoneCall':
        return '📞';
      case 'ChatInteraction':
        return '💬';
      default:
        return '📄';
    }
  };

  const getSentimentClass = (score: number) => {
    if (score >= 0.5) return 'positive';
    if (score >= 0) return 'neutral';
    return 'negative';
  };

  const getOutcomeClass = (outcome: string) => {
    switch (outcome) {
      case 'Accepted':
        return 'accepted';
      case 'Declined':
        return 'declined';
      case 'Delivered':
        return 'delivered';
      case 'Pending':
        return 'pending';
      default:
        return 'unknown';
    }
  };

  const getOutcomeIcon = (outcome: string) => {
    switch (outcome) {
      case 'Accepted':
        return '✅';
      case 'Declined':
        return '❌';
      case 'Delivered':
        return '📤';
      case 'Pending':
        return '⏳';
      default:
        return '❓';
    }
  };

  const timelineEvents = getTimelineEvents();

  if (isLoading) {
    return (
      <div className="history-timeline loading">
        <div className="loading-spinner"></div>
        <p>Loading history...</p>
      </div>
    );
  }

  if (timelineEvents.length === 0) {
    return (
      <div className="history-timeline empty">
        <p className="empty-message">No historical data available for this customer.</p>
      </div>
    );
  }

  return (
    <div className="history-timeline">
      {/* Filter Controls */}
      <div className="timeline-filters">
        <button
          className={`filter-btn ${filterType === 'all' ? 'active' : ''}`}
          onClick={() => setFilterType('all')}
        >
          All Events ({interactions.length + pastRecommendations.length})
        </button>
        <button
          className={`filter-btn ${filterType === 'interactions' ? 'active' : ''}`}
          onClick={() => setFilterType('interactions')}
        >
          Interactions ({interactions.length})
        </button>
        <button
          className={`filter-btn ${filterType === 'recommendations' ? 'active' : ''}`}
          onClick={() => setFilterType('recommendations')}
        >
          Recommendations ({pastRecommendations.length})
        </button>
      </div>

      {/* Timeline */}
      <div className="timeline-container">
        {timelineEvents.map((event, index) => (
          <div key={`${event.type}-${index}`} className={`timeline-event ${event.type}`}>
            <div className="event-marker"></div>
            <div className="event-content">
              <div className="event-header">
                <span className="event-date">
                  {formatDate(event.timestamp)} at {formatTime(event.timestamp)}
                </span>
              </div>

              {event.type === 'interaction' && (
                <InteractionCard interaction={event.data as InteractionEvent} />
              )}

              {event.type === 'recommendation' && (
                <RecommendationCard recommendation={event.data as PastRecommendation} />
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  function InteractionCard({ interaction }: { interaction: InteractionEvent }) {
    return (
      <div className="event-card interaction-card">
        <div className="card-header">
          <span className="event-type-icon">{getEventTypeIcon(interaction.event_type)}</span>
          <span className="event-type-label">{interaction.event_type}</span>
          <span className={`resolution-badge ${interaction.resolution_status.toLowerCase()}`}>
            {interaction.resolution_status}
          </span>
        </div>
        <p className="event-description">{interaction.description}</p>
        <div className="event-footer">
          <span className={`sentiment-indicator ${getSentimentClass(interaction.sentiment_score)}`}>
            Sentiment: {(interaction.sentiment_score * 100).toFixed(0)}%
          </span>
          {interaction.tags.length > 0 && (
            <div className="event-tags">
              {interaction.tags.map(tag => (
                <span key={tag} className="tag">{tag}</span>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  function RecommendationCard({ recommendation }: { recommendation: PastRecommendation }) {
    return (
      <div className="event-card recommendation-card">
        <div className="card-header">
          <span className="event-type-icon">💡</span>
          <span className="event-type-label">
            {recommendation.recommendation_type} Recommendation
          </span>
          <span className={`outcome-badge ${getOutcomeClass(recommendation.outcome_status)}`}>
            {getOutcomeIcon(recommendation.outcome_status)} {recommendation.outcome_status}
          </span>
        </div>
        <p className="event-description">{recommendation.recommendation_text}</p>
        <div className="event-footer">
          <span className="confidence-score">
            Confidence: {(recommendation.confidence_score * 100).toFixed(0)}%
          </span>
          {recommendation.delivered_by_agent_id && (
            <span className="agent-info">
              Agent: {recommendation.delivered_by_agent_id}
            </span>
          )}
          {recommendation.outcome_timestamp && (
            <span className="outcome-date">
              Outcome: {formatDate(recommendation.outcome_timestamp)}
            </span>
          )}
        </div>
      </div>
    );
  }
};
