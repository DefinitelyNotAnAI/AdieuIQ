# Customer Recommendation Engine - User Guide

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Support Agent Workflows](#support-agent-workflows)
4. [Understanding Recommendations](#understanding-recommendations)
5. [Explainability Features](#explainability-features)
6. [Manager Dashboard](#manager-dashboard)
7. [Best Practices](#best-practices)
8. [FAQ](#faq)

---

## Overview

The Customer Recommendation Engine is an AI-powered tool that helps support agents provide personalized recommendations to customers. It analyzes customer usage patterns, sentiment, and historical interactions to suggest:

- **Adoption Recommendations**: Features or capabilities the customer isn't using but would benefit from
- **Upsell Recommendations**: Premium features or tier upgrades that align with customer needs

### Key Benefits

- ✅ **Personalized**: Recommendations tailored to each customer's usage patterns
- ✅ **Explainable**: See the reasoning behind every recommendation
- ✅ **Contextual**: Considers customer sentiment and interaction history
- ✅ **Actionable**: Direct insights that support agents can act on immediately

---

## Getting Started

### Accessing the Application

1. Navigate to the application URL: `https://your-app-url.azurecontainerapps.io`
2. Sign in with your Microsoft account
3. Grant necessary permissions when prompted

### Required Permissions

You need one or more of these roles:
- **Support Agent**: Can search customers and view recommendations
- **Support Manager**: Can access dashboard and analytics
- **Admin**: Full access including system configuration

---

## Support Agent Workflows

### Workflow 1: Find and View Customer Profile

#### Step 1: Search for Customer

1. Click on the **Search Bar** at the top of the page
2. Start typing the customer's company name
3. See fuzzy-matched results appear instantly
4. Click on the correct customer from the list

**Pro Tip**: The search uses fuzzy matching, so you don't need to type the exact name. "Acme" will match "ACME Corporation", "Acme Inc.", etc.

#### Step 2: Review Customer Profile

The customer profile shows:

- **Company Information**:
  - Company name
  - Industry
  - Contract tier (Free, Standard, Premium)
  - Account representative

- **Usage Summary**:
  - Features currently in use
  - Usage intensity (High, Medium, Low, None)
  - Usage trends over the past 90 days

- **Sentiment Indicators**:
  - Overall sentiment score (-1.0 to +1.0)
  - Recent sentiment trend
  - Key sentiment factors (issues, praise, concerns)

**Example Profile**:
```
Customer: Contoso Manufacturing
Industry: Manufacturing
Tier: Standard
Account Rep: Jane Smith

Usage Summary (Last 90 Days):
  ✓ Dashboard Analytics - HIGH (142 uses)
  ✓ API Integration - MEDIUM (87 uses)
  ✓ Data Export - LOW (12 uses)
  ✗ Advanced Reporting - NONE
  ✓ Custom Workflows - MEDIUM (34 uses)

Sentiment: +0.62 (Positive) ↗️
  Key Factors:
    • Praised dashboard ease of use
    • Requested better export options
    • No critical issues reported
```

---

### Workflow 2: Generate and Review Recommendations

#### Step 1: Generate Recommendations

1. On the customer profile page, click **"Generate Recommendations"**
2. Wait 2-3 seconds while AI analyzes the customer
3. See recommendations appear grouped by type

#### Step 2: Review Adoption Recommendations

Adoption recommendations suggest features the customer isn't using:

**Example**:
```
💡 Adoption Recommendation

Feature: Advanced Reporting
Confidence: 85%

Why This Recommendation:
"Customer has high usage of Dashboard Analytics but hasn't 
enabled Advanced Reporting. This feature would provide deeper 
insights into supply chain bottlenecks. Customers who activate 
this feature report 40% faster decision-making."

Reasoning Chain:
  🔍 Retrieval: High Dashboard Analytics usage (142 uses/90d)
  💭 Sentiment: Positive sentiment, no blockers identified
  🧠 Reasoning: Advanced Reporting complements current usage
  ✅ Validation: Passed content safety, no duplicates
```

**What to Do**:
- **Accept**: Customer is interested → Track the outcome
- **Decline**: Not relevant right now → System learns from feedback
- **Explain**: Need more details → Click "Show Reasoning" (see below)

#### Step 3: Review Upsell Recommendations

Upsell recommendations suggest premium features or tier upgrades:

**Example**:
```
💰 Upsell Recommendation

Feature: Custom Workflow Premium Pack
Confidence: 78%

Why This Recommendation:
"Customer actively uses Custom Workflows (34 uses) and would 
benefit from premium workflow templates, advanced automation, 
and priority support. Average ROI for similar customers: 3.2x."

Reasoning Chain:
  🔍 Retrieval: Active Custom Workflows usage
  💭 Sentiment: Positive, ready for expansion
  🧠 Reasoning: Matches usage patterns of premium users
  ✅ Validation: No recent declines for similar offers
```

---

### Workflow 3: Understanding Explainability

#### Why Explainability Matters

Every recommendation comes with **complete transparency** about how it was generated. This helps you:
- Build trust with customers
- Address concerns proactively
- Understand why certain recommendations are made
- Learn how the AI evaluates customers

#### How to View Explainability

1. Find a recommendation you want to understand
2. Click **"🔍 Show Reasoning"** button
3. See the multi-agent breakdown

#### Understanding the Agent Breakdown

The AI uses 4 specialized agents:

**1. 🔍 Retrieval Agent**
- **What it does**: Fetches customer data from multiple sources
- **Shows you**:
  - Usage data from past 90 days
  - Knowledge articles retrieved
  - Interaction history
  - Data source timestamps

**Example**:
```
Input Data:
  • customer_id: 550e8400-e29b-41d4-a716-446655440001
  • days: 90
  
Output Result:
  • Data Sources:
    - Dashboard Analytics: 142 uses (HIGH intensity)
    - API Integration: 87 uses (MEDIUM intensity)
  • Knowledge Articles:
    - "Advanced Reporting Best Practices" (relevance: 0.92)
    - "Workflow Optimization Guide" (relevance: 0.85)
  
Confidence: 90%
Execution Time: 234ms
```

**2. 💭 Sentiment Agent**
- **What it does**: Analyzes customer sentiment from interactions
- **Shows you**:
  - Sentiment score (-1.0 to +1.0)
  - Positive/negative factors identified
  - Readiness for new features

**Example**:
```
Input Data:
  • interaction_history: [12 events, 90 days]
  
Output Result:
  • Sentiment Score: +0.62 (Positive)
  • Factors:
    + Praised dashboard UX
    + Satisfied with API performance
    - Requested better export options
  • Readiness: HIGH (positive + no blockers)
  
Confidence: 85%
Execution Time: 156ms
```

**3. 🧠 Reasoning Agent**
- **What it does**: Generates recommendation candidates
- **Shows you**:
  - Features considered
  - Filtering logic applied
  - Duplicate detection results

**Example**:
```
Input Data:
  • usage_data: [5 features tracked]
  • sentiment: +0.62
  • past_recommendations: [3 previous]
  
Output Result:
  • Candidates Generated:
    1. Advanced Reporting (score: 0.85)
    2. Custom Workflows Premium (score: 0.78)
    3. Data Export Pro (score: 0.54)
  • Duplicates Filtered:
    - Advanced Reporting declined <90 days ago ❌
  • Final Recommendations: 2
  
Confidence: 82%
Execution Time: 423ms
```

**4. ✅ Validation Agent**
- **What it does**: Validates recommendations for safety and compliance
- **Shows you**:
  - Content safety checks
  - Business rule validation
  - Confidence threshold filtering

**Example**:
```
Input Data:
  • recommendations: [2 candidates]
  
Output Result:
  • Content Safety: PASSED (all)
  • Business Rules: PASSED
    ✓ Confidence > 0.5
    ✓ No blacklisted features
    ✓ Customer tier eligible
  • Final Count: 2 approved
  
Confidence: 95%
Execution Time: 89ms
```

---

### Workflow 4: Track Recommendation Outcomes

#### Why Track Outcomes?

Tracking helps the AI learn and improve:
- **Accepted**: Customer adopted the recommendation → Positive signal
- **Declined**: Not interested right now → Learn customer preferences
- **Pending**: Still considering → No signal yet

#### How to Track

1. After discussing recommendation with customer, record the outcome:
   - Click **"✓ Accept"** if customer is interested
   - Click **"✗ Decline"** if not relevant
2. The system automatically updates and learns from your input
3. Future recommendations will be better tailored

**Important**: Always record outcomes to help the system learn!

---

### Workflow 5: View Historical Context

#### Accessing History

1. Open customer profile
2. Click the **"History"** tab
3. See chronological timeline of:
   - Past recommendations (with outcomes)
   - Customer interactions
   - Feature adoption events

#### Using History

- **Before generating new recommendations**: Check what was previously suggested
- **During customer conversations**: Reference past interactions
- **After outcomes**: Understand recommendation patterns

**Example Timeline**:
```
📅 March 15, 2025
  Recommendation: Advanced Reporting
  Outcome: ✓ ACCEPTED
  
📅 March 10, 2025
  Interaction: Support ticket #12345
  Topic: Export feature request
  Sentiment: Neutral
  
📅 February 28, 2025
  Recommendation: Data Export Pro
  Outcome: ✗ DECLINED
  Reason: Budget constraints
  
📅 February 15, 2025
  Feature Adopted: API Integration
  Usage Since: 87 API calls
```

---

## Manager Dashboard

### Accessing the Dashboard

1. Navigate to **"Dashboard"** in the top menu (Manager role required)
2. See overview metrics and analytics

### Key Metrics

**Adoption Metrics**:
- Total recommendations generated
- Acceptance rate by feature
- Time-to-adoption after recommendation
- Feature usage after adoption

**Upsell Pipeline**:
- Upsell opportunities identified
- Conversion rate by tier
- Revenue potential (estimated)
- Win/loss analysis

**Agent Performance** (if applicable):
- Recommendations per agent
- Acceptance rate by agent
- Average response time

### Using Dashboard Insights

1. **Identify High-Performing Features**:
   - Which features have highest acceptance rates?
   - Focus training on these for quick wins

2. **Spot Trends**:
   - Are certain industries more receptive?
   - What's the best time to make recommendations?

3. **Optimize Messaging**:
   - Review declined recommendations
   - Refine pitch based on patterns

---

## Best Practices

### ✅ Do's

1. **Review customer profile before generating recommendations**
   - Understand their usage patterns
   - Check sentiment indicators
   - Review recent interactions

2. **Use explainability to build trust**
   - Show customers the data behind recommendations
   - Address concerns proactively
   - Build credibility with transparency

3. **Always track outcomes**
   - Accept/Decline buttons help the AI learn
   - More data = better future recommendations

4. **Consider timing**
   - Don't recommend if customer just declined similar feature
   - Wait for positive sentiment before upsell

5. **Personalize your pitch**
   - Use customer's usage data in conversation
   - Reference specific pain points from sentiment analysis
   - Connect recommendation to their goals

### ❌ Don'ts

1. **Don't ignore sentiment indicators**
   - Negative sentiment = wrong time for recommendations
   - Address concerns first, then recommend

2. **Don't over-recommend**
   - Quality over quantity
   - 2-3 strong recommendations > 10 mediocre ones

3. **Don't skip explainability**
   - Always understand why before pitching
   - If you don't understand, customer won't either

4. **Don't pressure customers**
   - Recommendations are suggestions, not mandates
   - Respect "Decline" decisions

5. **Don't forget to follow up**
   - Track adoption after acceptance
   - Check if customer needs help implementing

---

## FAQ

### Q: How are recommendations generated?

**A**: Recommendations use a multi-agent AI system that:
1. Retrieves customer usage data and knowledge articles
2. Analyzes sentiment from interactions
3. Generates candidates based on patterns
4. Validates for safety and compliance

### Q: Why don't I see recommendations for some customers?

**A**: Possible reasons:
- Customer is new (less than 30 days of data)
- All features already adopted
- Recent negative sentiment (system waits for positive trend)
- Technical issues retrieving data

### Q: Can I override recommendations?

**A**: You can decline recommendations you don't agree with. The system will learn from your feedback and adjust future recommendations.

### Q: How accurate are recommendations?

**A**: Confidence scores indicate likelihood of success:
- **80-100%**: High confidence, strong pattern match
- **50-79%**: Medium confidence, worth discussing
- **Below 50%**: Low confidence, filtered out

Acceptance rates vary by feature but typically range from 40-70%.

### Q: What if a customer asks how their data is used?

**A**: Refer them to the explainability view. It shows:
- Exact data sources used
- How sentiment was calculated
- Why recommendation was made
- All processing is logged for audit

### Q: Can I see recommendations I made yesterday?

**A**: Yes! Use the History tab on the customer profile. All recommendations are stored with timestamps and outcomes.

### Q: What happens if I accidentally click the wrong outcome?

**A**: Contact your manager or admin to update the record. Outcomes can be corrected within 24 hours.

### Q: Why did the system recommend the same feature twice?

**A**: The system filters duplicates based on:
- Accepted recommendations: Not suggested again for 30 days
- Declined recommendations: Not suggested again for 90 days
- Pending recommendations: Can be re-suggested after 14 days

If you see a duplicate, it may be a different variation or package of the feature.

---

## Getting Help

### Support Contacts

- **Technical Issues**: support@company.com
- **Training Questions**: training@company.com
- **Feature Requests**: product@company.com

### Training Resources

- **Video Tutorials**: [Link to training portal]
- **Live Training Sessions**: [Schedule link]
- **Knowledge Base**: [Link to internal KB]

---

## Glossary

**Adoption Recommendation**: Suggestion to activate a feature the customer isn't using

**Agent Contribution**: The output from one of the 4 AI agents (Retrieval, Sentiment, Reasoning, Validation)

**Circuit Breaker**: Safety mechanism that prevents system overload when external services fail

**Confidence Score**: Percentage (0-100%) indicating likelihood of recommendation success

**Fuzzy Matching**: Search algorithm that finds approximate matches (e.g., "Acme" matches "ACME Corp")

**Graceful Degradation**: System continues working with reduced functionality when services fail

**Intensity Score**: Usage frequency classification (NONE, LOW, MEDIUM, HIGH)

**RAG (Retrieval-Augmented Generation)**: AI pattern that grounds recommendations in real data

**Sentiment Indicator**: Measure of customer satisfaction (-1.0 to +1.0)

**Upsell Recommendation**: Suggestion to upgrade tier or add premium features

---

**Version**: 1.0  
**Last Updated**: January 2026  
**Document Owner**: Product Team
