# Research: Customer Recommendation Engine

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)  
**Phase**: 0 (Pre-Design Research)  
**Purpose**: Resolve technical unknowns and establish implementation patterns

## Decision Log

### Decision 1: Backend Framework

**Choice**: FastAPI (Python 3.11+)

**Rationale**:
- Native async/await support for concurrent AI agent orchestration
- Automatic OpenAPI documentation generation (supports contract-first development)
- Built-in dependency injection simplifies Azure SDK integration
- Strong typing with Pydantic models aligns with data validation requirements
- Mature ecosystem for Azure integrations (azure-identity, OpenTelemetry)

**Alternatives Considered**:
- **Flask**: Rejected due to lack of native async support; would require complex threading for agent orchestration
- **Django**: Rejected as overly heavy for API-only service; ORM unnecessary given OneLake + Cosmos DB usage
- **.NET (ASP.NET Core)**: Viable but rejected due to team Python expertise and Azure AI Foundry SDK Python SDK maturity

### Decision 2: Frontend Framework

**Choice**: React 18 with TypeScript

**Rationale**:
- Component reusability for CustomerProfile, RecommendationList, HistoryTimeline
- Strong TypeScript support ensures type safety for API contracts
- Large ecosystem for UI components (Material-UI, Ant Design) accelerates development
- MSAL React library provides seamless Azure AD authentication
- Developer tooling (React DevTools, TypeScript compiler) improves productivity

**Alternatives Considered**:
- **Angular**: Rejected due to steeper learning curve and heavier framework overhead
- **Vue.js**: Rejected due to smaller Azure integration ecosystem
- **Blazor WebAssembly**: Rejected to maintain consistency with Python backend

### Decision 3: Multi-Agent Orchestration Architecture

**Choice**: Azure AI Foundry SDK with Sequential + Parallel Agent Patterns

**Rationale**:
- Constitutional requirement: "Use Azure AI Foundry SDK for ALL agent orchestration (do not custom-build)"
- SDK provides built-in patterns: ReAct (reasoning + action), Sequential chains, Parallel execution
- Explicit agent roles improve explainability (required by FR-016)
- Built-in retry logic and error handling for resilient orchestration

**Pattern Design**:
```
1. Retrieval Agent (parallel with Sentiment Agent)
   → Queries Foundry IQ for relevant knowledge
   → Queries Fabric IQ for usage trends

2. Sentiment Analysis Agent (parallel with Retrieval Agent)
   → Analyzes customer interaction history sentiment
   → Provides sentiment score and factors

3. Reasoning Agent (sequential, after 1+2 complete)
   → Combines retrieval results + sentiment
   → Generates candidate recommendations
   → Applies business rules (e.g., sentiment-aware filtering per FR-015)

4. Validation Agent (sequential, after 3)
   → Checks for duplicate recommendations (FR-014)
   → Applies Content Safety filters (FR-019)
   → Validates against constitutional compliance rules
```

**Alternatives Considered**:
- **LangChain**: Rejected due to constitutional requirement for Azure AI Foundry SDK
- **Custom orchestrator**: Explicitly forbidden by Constitution Principle V

### Decision 4: Data Storage Strategy

**Choice**: Hybrid - OneLake (primary) + Cosmos DB (cache/operational) + Redis (session)

**Rationale**:
- **OneLake**: Constitutional requirement for unified Fabric integration; stores raw customer data, usage telemetry
- **Cosmos DB**: Low-latency cache for recommendation history (FR-013: 3s load for 100 interactions); supports change feed for real-time updates
- **Redis**: Session caching and API response caching to meet <200ms p95 constraint

**Data Flow**:
- Raw data ingested to OneLake via Fabric Real-Time Intelligence
- Fabric IQ semantic layer provides aggregated views (no direct OneLake queries from backend)
- Recommendation results cached in Cosmos DB for historical timeline
- Redis caches frequent customer profile lookups

**Alternatives Considered**:
- **SQL Database (Azure SQL)**: Rejected; OneLake + Fabric IQ already provide semantic layer
- **PostgreSQL**: Rejected for same reason
- **Cosmos DB only**: Insufficient for real-time analytics required by dashboard (P2)

### Decision 5: Power BI Dashboard Deployment

**Choice**: Power BI Service (workspace deployment) with Direct Query to Fabric

**Rationale**:
- Direct Query mode ensures <10s refresh lag requirement (FR-012)
- Fabric Real-Time Intelligence → OneLake → Power BI provides native integration
- Power BI Pro licenses sufficient for <500 users (Customer Success Manager persona)
- Row-level security via Azure AD groups for data isolation

**Alternatives Considered**:
- **Power BI Embedded**: Rejected for MVP to reduce frontend complexity; revisit for P2+ if embedding required
- **Tableau**: Rejected; lacks native Fabric integration
- **Custom dashboard**: Rejected; violates best practice of leveraging Power BI for analytics

### Decision 6: Authentication & Authorization

**Choice**: Azure AD (Entra ID) with MSAL + RBAC

**Rationale**:
- Constitutional requirement: Managed Identity for service-to-service, RBAC for users
- MSAL browser library provides token acquisition with automatic renewal
- Backend validates JWT tokens using Azure AD public keys
- RBAC roles: `SupportAgent`, `CustomerSuccessManager`, `Administrator`

**Token Flow**:
```
Frontend (MSAL) → Azure AD → JWT token → Backend API (validates) → Managed Identity → Azure services
```

**Alternatives Considered**:
- **Custom auth**: Explicitly forbidden by constitutional principles
- **API keys**: Rejected; does not support per-user audit trails required by Purview

### Decision 7: Observability Implementation

**Choice**: OpenTelemetry SDK + Azure Application Insights

**Rationale**:
- OpenTelemetry provides vendor-neutral instrumentation (constitutional requirement)
- Application Insights as exporter provides Azure-native integration
- Distributed tracing via W3C Trace Context headers for request correlation
- Structured logging with correlation IDs enables debugging agent orchestration

**Instrumentation Points**:
- HTTP requests (FastAPI middleware)
- AI agent execution (custom spans for each agent in orchestration)
- Database queries (Cosmos DB SDK hooks)
- External API calls (Fabric IQ, Foundry IQ, OpenAI)

**Alternatives Considered**:
- **Application Insights SDK only**: Rejected; lacks vendor neutrality required by constitution
- **Prometheus + Grafana**: Rejected; adds operational complexity, Application Insights preferred for Azure

### Decision 8: Testing Strategy

**Choice**: Layered testing with TDD for agent orchestration

**Rationale**:
- Constitutional requirement for TDD on critical paths
- Contract tests validate API boundaries (align with OpenAPI spec)
- Integration tests for agent orchestration ensure multi-agent workflows function correctly
- E2E tests verify user stories (Playwright for cross-browser testing)
- Load tests ensure 100+ concurrent user support (Locust)

**Test Pyramid**:
```
        E2E Tests (Playwright) - 10%
       ────────────────────────
      Integration Tests - 30%
     (Agent orchestration, API)
    ────────────────────────────
   Unit Tests (pytest) - 60%
  (Business logic, models)
```

**Alternatives Considered**:
- **Manual testing only**: Rejected; violates constitutional quality standards
- **Selenium for E2E**: Rejected; Playwright provides better async handling and faster execution

## Unresolved Questions

None - all technical context clarified. Ready to proceed to Phase 1 (Design).
