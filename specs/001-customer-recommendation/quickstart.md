# Quickstart Guide: Customer Recommendation Engine

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)  
**Audience**: Developers implementing this feature  
**Purpose**: Accelerate development with architecture overview and key patterns

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│  CustomerSearch → CustomerProfile → RecommendationList           │
│                   HistoryTimeline   ExplainabilityPanel          │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS + Azure AD JWT
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend API (FastAPI)                         │
│  /customers/search  /customers/{id}/profile                      │
│  /customers/{id}/recommendations  /customers/{id}/history        │
└───────────┬─────────────────┬─────────────────┬─────────────────┘
            │                 │                 │
            ▼                 ▼                 ▼
┌─────────────────┐  ┌───────────────┐  ┌─────────────────┐
│  Fabric IQ      │  │  Foundry IQ   │  │  Azure OpenAI   │
│  (Usage Data)   │  │  (Knowledge)  │  │  (LLM)          │
└─────────────────┘  └───────────────┘  └─────────────────┘
            │                 │                 │
            └─────────────────┴─────────────────┘
                            │
                            ▼
            ┌───────────────────────────────────┐
            │  Azure AI Foundry SDK             │
            │  Multi-Agent Orchestration        │
            │  ┌──────────┐  ┌──────────┐      │
            │  │Retrieval │  │Sentiment │      │
            │  │  Agent   │  │  Agent   │      │
            │  └──────────┘  └──────────┘      │
            │  ┌──────────┐  ┌──────────┐      │
            │  │Reasoning │  │Validation│      │
            │  │  Agent   │  │  Agent   │      │
            │  └──────────┘  └──────────┘      │
            └───────────────────────────────────┘
                            │
                            ▼
            ┌───────────────────────────────────┐
            │  Storage Layer                    │
            │  • OneLake (via Fabric IQ)        │
            │  • Cosmos DB (cache + history)    │
            │  • Redis (session + perf)         │
            └───────────────────────────────────┘
```

## Key Implementation Patterns

### 1. Multi-Agent Orchestration (Constitutional Requirement)

**Pattern**: Sequential + Parallel Execution via Azure AI Foundry SDK

```python
# backend/src/services/orchestration/orchestrator.py
from azure.ai.foundry import AgentOrchestrator, Agent

class RecommendationOrchestrator:
    def __init__(self):
        self.orchestrator = AgentOrchestrator(
            credential=ManagedIdentityCredential()  # Constitutional: Managed Identity
        )
        
    async def generate_recommendations(self, customer_id: str) -> dict:
        # Phase 1: Parallel execution (Retrieval + Sentiment)
        retrieval_task = self.retrieval_agent.run(customer_id)
        sentiment_task = self.sentiment_agent.run(customer_id)
        
        retrieval_result, sentiment_result = await asyncio.gather(
            retrieval_task, sentiment_task
        )
        
        # Phase 2: Sequential (Reasoning uses Phase 1 outputs)
        reasoning_result = await self.reasoning_agent.run(
            retrieval=retrieval_result,
            sentiment=sentiment_result
        )
        
        # Phase 3: Sequential (Validation uses Reasoning output)
        validated_result = await self.validation_agent.run(
            recommendations=reasoning_result,
            customer_id=customer_id
        )
        
        # Log reasoning chain for explainability (FR-016)
        await self._log_agent_contributions(validated_result)
        
        return validated_result
```

**Why This Pattern**:
- Constitutional requirement: "Use Azure AI Foundry SDK for ALL agent orchestration"
- Parallel execution optimizes latency (FR-005: <2s p95)
- Sequential dependencies ensure data flow correctness

---

### 2. Retrieval-Augmented Generation (RAG)

**Pattern**: Ground recommendations in Fabric IQ + Foundry IQ data

```python
# backend/src/services/orchestration/retrieval_agent.py
class RetrievalAgent(Agent):
    async def run(self, customer_id: str) -> dict:
        # Query Fabric IQ for usage trends
        usage_data = await self.fabric_client.get_usage_trends(
            customer_id=customer_id,
            days=90  # FR-002: past 90 days
        )
        
        # Query Foundry IQ for relevant knowledge
        knowledge = await self.foundry_client.search_knowledge(
            query=self._build_search_query(usage_data),
            top_k=10
        )
        
        return {
            "usage_data": usage_data,
            "knowledge_articles": knowledge,
            "confidence": self._calculate_confidence(usage_data, knowledge)
        }
```

**Why This Pattern**:
- Constitutional requirement: "Ground all recommendations in Foundry IQ and Fabric IQ"
- Prevents hallucinations (FR-009)
- Enables explainability with data source references

---

### 3. Content Safety Integration

**Pattern**: Filter all AI-generated text before returning to client

```python
# backend/src/services/content_safety.py
from azure.ai.contentsafety import ContentSafetyClient

class ContentSafetyService:
    def __init__(self):
        self.client = ContentSafetyClient(
            endpoint=os.getenv("CONTENT_SAFETY_ENDPOINT"),
            credential=ManagedIdentityCredential()  # Constitutional: Managed Identity
        )
    
    async def validate_recommendation_text(self, text: str) -> bool:
        result = await self.client.analyze_text(text)
        
        # Block if any category exceeds threshold
        if any(score > 0.5 for score in result.severity_scores.values()):
            logger.warning(f"Content Safety blocked text: {result}")
            return False
            
        return True
```

**Why This Pattern**:
- Constitutional requirement: "Apply Azure AI Content Safety filters to ALL AI-generated content" (FR-019)
- Prevents harmful content in customer-facing recommendations

---

### 4. Observability with OpenTelemetry

**Pattern**: Instrument all critical paths with spans

```python
# backend/src/core/observability.py
from opentelemetry import trace
from opentelemetry.exporter.azuremonitor import AzureMonitorTraceExporter

tracer = trace.get_tracer(__name__)

# Usage in orchestrator
async def generate_recommendations(self, customer_id: str) -> dict:
    with tracer.start_as_current_span("generate_recommendations") as span:
        span.set_attribute("customer_id", customer_id)
        
        with tracer.start_as_current_span("retrieval_agent"):
            retrieval_result = await self.retrieval_agent.run(customer_id)
            span.set_attribute("retrieval.confidence", retrieval_result["confidence"])
        
        with tracer.start_as_current_span("reasoning_agent"):
            reasoning_result = await self.reasoning_agent.run(retrieval_result)
            span.set_attribute("reasoning.candidate_count", len(reasoning_result))
        
        # Spans auto-exported to Application Insights
        return validated_result
```

**Why This Pattern**:
- Constitutional requirement: "Implement OpenTelemetry instrumentation for distributed tracing"
- Enables debugging of agent orchestration failures
- Supports performance optimization (FR-005: <2s latency)

---

### 5. Azure AD Authentication (Frontend)

**Pattern**: MSAL React for token acquisition

```typescript
// frontend/src/services/auth-service.ts
import { PublicClientApplication } from '@azure/msal-browser';

const msalConfig = {
  auth: {
    clientId: process.env.REACT_APP_CLIENT_ID,
    authority: `https://login.microsoftonline.com/${process.env.REACT_APP_TENANT_ID}`,
    redirectUri: window.location.origin,
  },
};

export const msalInstance = new PublicClientApplication(msalConfig);

// API client with token injection
export async function callBackendAPI(endpoint: string, method: string = 'GET') {
  const account = msalInstance.getAllAccounts()[0];
  const tokenResponse = await msalInstance.acquireTokenSilent({
    account,
    scopes: ['api://adieuiq/Customers.Read'],
  });
  
  return fetch(`${API_BASE_URL}${endpoint}`, {
    method,
    headers: {
      'Authorization': `Bearer ${tokenResponse.accessToken}`,
      'Content-Type': 'application/json',
    },
  });
}
```

**Why This Pattern**:
- Constitutional requirement: Managed Identity for services, Azure AD for user auth
- Provides per-user audit trails (FR-020)

---

## Development Workflow

### Step 1: Environment Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install

# Infrastructure (Azure resources)
cd infrastructure/bicep
az login
az deployment sub create --location eastus --template-file main.bicep
```

### Step 2: Local Development with Mocks

Mock Fabric IQ and Foundry IQ during local development:

```python
# backend/src/services/fabric_client.py
class FabricIQClient:
    def __init__(self):
        if os.getenv("ENV") == "local":
            self.use_mock = True
        else:
            self.use_mock = False
            self.credential = ManagedIdentityCredential()
    
    async def get_usage_trends(self, customer_id: str, days: int):
        if self.use_mock:
            return self._get_mock_usage_data()
        else:
            return await self._query_fabric_iq(customer_id, days)
```

### Step 3: Test-Driven Development

**Required by Constitution**: TDD for agent orchestration

```python
# backend/tests/integration/test_orchestration.py
@pytest.mark.asyncio
async def test_recommendation_generation_success():
    # Arrange
    orchestrator = RecommendationOrchestrator()
    customer_id = "test-customer-123"
    
    # Act
    result = await orchestrator.generate_recommendations(customer_id)
    
    # Assert
    assert 2 <= len(result["adoption_recommendations"]) <= 5  # FR-003
    assert 1 <= len(result["upsell_recommendations"]) <= 3   # FR-004
    assert result["generation_time_ms"] < 2000  # FR-005: <2s
    assert all(r["confidence_score"] > 0.5 for r in result["adoption_recommendations"])
```

### Step 4: Deploy to Azure

```bash
# Build and push containers
docker build -t adieuiq-backend:latest backend/
az acr login --name adieuiqregistry
docker tag adieuiq-backend:latest adieuiqregistry.azurecr.io/backend:latest
docker push adieuiqregistry.azurecr.io/backend:latest

# Deploy via Bicep
az deployment group create \
  --resource-group adieuiq-rg \
  --template-file infrastructure/bicep/main.bicep
```

---

## Performance Optimization Tips

### 1. Cache Frequently Accessed Data

```python
# Use Redis for customer profile caching
@cache(ttl=300)  # 5-minute TTL
async def get_customer_profile(customer_id: str):
    return await cosmos_db.query(customer_id)
```

### 2. Parallel API Calls

```python
# Don't do this (sequential):
usage = await fabric_client.get_usage(customer_id)
knowledge = await foundry_client.search(query)

# Do this (parallel):
usage, knowledge = await asyncio.gather(
    fabric_client.get_usage(customer_id),
    foundry_client.search(query)
)
```

### 3. Lazy Load Historical Data

```typescript
// Frontend: Load history tab only when clicked
const HistoryTab = () => {
  const [history, setHistory] = useState(null);
  
  useEffect(() => {
    if (tabActive) {  // Only load when tab is active
      fetchHistory(customerId).then(setHistory);
    }
  }, [tabActive]);
};
```

---

## Constitutional Compliance Checklist

Before merging code, verify:

- [ ] ✅ Managed Identity used for all Azure service auth (no hardcoded secrets)
- [ ] ✅ Azure AI Foundry SDK used for agent orchestration (no custom orchestrators)
- [ ] ✅ Content Safety filters applied to all AI-generated text
- [ ] ✅ OpenTelemetry spans created for agent execution
- [ ] ✅ Application Insights logs include correlation IDs
- [ ] ✅ Purview integration enabled for audit trails
- [ ] ✅ RBAC configured for support agent / customer success manager roles
- [ ] ✅ RAG patterns ground recommendations in Fabric IQ + Foundry IQ
- [ ] ✅ Unit tests + integration tests + contract tests passing
- [ ] ✅ Performance: <2s p95 recommendation latency

---

## Common Pitfalls

1. **Hardcoding API keys**: Constitutional violation. Always use Managed Identity + Key Vault.
2. **Custom orchestration logic**: Constitutional violation. Use Azure AI Foundry SDK patterns.
3. **Skipping Content Safety**: Constitutional violation (FR-019). Filter all AI text.
4. **Missing correlation IDs**: Violates observability principles. Use OpenTelemetry context propagation.
5. **Synchronous API calls**: Breaks <2s latency requirement. Use async/await + parallel execution.

---

## References

- [Azure AI Foundry SDK Documentation](https://learn.microsoft.com/azure/ai-foundry/)
- [Fabric IQ API Reference](https://learn.microsoft.com/fabric/)
- [Foundry IQ Knowledge Retrieval](https://learn.microsoft.com/azure/ai-foundry/foundry-iq)
- [OpenTelemetry Python SDK](https://opentelemetry.io/docs/languages/python/)
- [MSAL React Documentation](https://github.com/AzureAD/microsoft-authentication-library-for-js/tree/dev/lib/msal-react)
