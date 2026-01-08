### Architecture

#### Data Flow

+----------------------------------------------------------------------+
| 1 Sample Data Services → Fabric Real-Time Intelligence → OneLake →   |
| Fabric IQ Semantic Layer → Foundry IQ Knowledge Base → AI Agents →   |
| Power BI Dashboard                                                   |
|                                                                      |
| 2                                                                    |
+======================================================================+

#### Integration Points

- **Azure OpenAI**: Reasoning and natural language generation.

- **Purview**: Governance and compliance.

- **Defender for Cloud**: Security posture management.

#### High-Level Diagram

*(Include in repo as architecture.png)*

### Demo Scenario

1.  **Sample Data Services** stream synthetic customer interaction and
    usage data into Fabric Real-Time Intelligence.

2.  **Fabric Real-Time Intelligence** processes and routes data to
    OneLake for unified storage.

3.  **Fabric IQ provides semantic context** (feature usage trends,
    sentiment analysis).

4.  **Foundry IQ retrieves historical knowledge** for grounding.

5.  **AI agent recommends upsell offer** and adoption tips in real-time.

6.  **Dashboard updates dynamically** with recommendation outcomes.

### Recommendation for Sample Data Services

- **Service A (Support Interaction Simulator)**:

  - Generates synthetic support tickets and chat logs with randomized
    customer issues.

  - Streams data into Fabric Real-Time Intelligence using Eventstream.

  - Tags data with customer ID and sentiment score for semantic
    enrichment.

- **Service B (Usage Telemetry Simulator)**:

  - Produces feature usage metrics, adoption rates, and session
    durations.

  - Streams telemetry events into Fabric Real-Time Intelligence.

  - Includes metadata for product tier and subscription status for
    upsell logic.

Both services should:

- Use **Azure Functions** or **Container Apps** for lightweight
  deployment.

- Implement **Eventstream connectors** for Fabric ingestion.

- Support **configurable frequency and payload size** for demo
  flexibility.
