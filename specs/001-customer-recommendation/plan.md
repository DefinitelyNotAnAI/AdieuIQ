# Implementation Plan: Customer Recommendation Engine

**Branch**: `001-customer-recommendation` | **Date**: 2026-01-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-customer-recommendation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build an Azure-native web application that delivers personalized adoption and upsell recommendations to customer support agents in real-time. The system integrates Fabric IQ for semantic intelligence, Foundry IQ for knowledge retrieval, and Azure AI Foundry SDK for multi-agent orchestration. A Power BI dashboard provides Customer Success Managers with adoption metrics and upsell pipeline visibility. Technical approach uses Python backend with FastAPI for API services, React frontend for agent interface, Azure AI Foundry SDK for orchestration, and Power BI Embedded for dashboards.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript 5.x + React 18 (frontend)  
**Primary Dependencies**: FastAPI, Azure AI Foundry SDK, azure-identity, azure-keyvault-secrets, OpenTelemetry SDK, React, @azure/msal-browser  
**Storage**: OneLake (primary data lake via Fabric IQ), Azure Cosmos DB (recommendation cache and history), Azure Redis Cache (session and performance optimization)  
**Testing**: pytest + pytest-asyncio (backend), Jest + React Testing Library (frontend), Playwright (E2E), Locust (load testing)  
**Target Platform**: Azure App Service (Linux containers), Azure Container Apps (for agent orchestration service)  
**Project Type**: Web application (separate backend API + frontend SPA)  
**Performance Goals**: <2s p95 recommendation generation, 100+ concurrent users, <5s dashboard load  
**Constraints**: <200ms p95 API response (excluding AI calls), <10s real-time data ingestion lag, 99.9% uptime  
**Scale/Scope**: 100-500 concurrent support agents, 50K+ customers, 10K+ daily recommendation generations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ I. Azure-Native Architecture
- ✅ Using Azure App Service and Azure Container Apps for hosting
- ✅ Azure AI Foundry SDK for multi-agent orchestration
- ✅ Fabric IQ integration for semantic intelligence
- ✅ Foundry IQ integration for knowledge retrieval
- ✅ Azure OpenAI Service for LLM inference
- ✅ Fabric Real-Time Intelligence for event streaming
- ✅ OneLake for unified data storage

**Status**: PASSED - All components use Azure-native services per constitutional requirements.

### ✅ II. Security & Identity (NON-NEGOTIABLE)
- ✅ Azure Managed Identity for all service-to-service auth (App Service ↔ Fabric IQ, Foundry IQ, OpenAI, Key Vault)
- ✅ Azure Key Vault for storing API keys, connection strings
- ✅ No hardcoded credentials (enforced via pre-commit hooks)
- ✅ RBAC configured for support agent, customer success manager, administrator roles
- ✅ Azure Defender for Cloud enabled for security posture monitoring

**Status**: PASSED - Security architecture follows zero-trust principles with Managed Identity and Key Vault.

### ✅ III. Compliance & Responsible AI (NON-NEGOTIABLE)
- ✅ Microsoft Purview integration for data governance and audit trails
- ✅ Azure AI Content Safety applied to all AI-generated recommendation text
- ✅ Data classification and sensitivity labeling via Purview
- ✅ Audit trail for all customer data access and recommendations
- ✅ Human-in-the-loop: support agents review recommendations before delivery
- ✅ AI model behavior documented in quickstart.md (Phase 1 deliverable)

**Status**: PASSED - Compliance architecture meets governance and responsible AI requirements.

### ✅ IV. Observability & Monitoring
- ✅ Azure Application Insights enabled for backend, frontend, and orchestration service
- ✅ OpenTelemetry instrumentation for distributed tracing across components
- ✅ Structured logging with correlation IDs for request tracing
- ✅ AI agent decisions logged with reasoning chains and data sources
- ✅ Alerts configured for: recommendation latency >2s, orchestration failures, service health
- ✅ Key metrics tracked: acceptance rate, response latency, orchestration success rate

**Status**: PASSED - Comprehensive observability meets production readiness standards.

### ✅ V. AI/ML Best Practices
- ✅ Azure AI Foundry SDK for agent orchestration (not custom-built)
- ✅ Multi-agent workflow: retrieval agent, sentiment analysis agent, reasoning agent, validation agent
- ✅ Grounding in Foundry IQ knowledge base and Fabric IQ semantic context
- ✅ RAG (Retrieval-Augmented Generation) patterns implemented
- ✅ Prompts and agent configurations versioned in source control
- ✅ Evaluation metrics defined: accuracy, hallucination rate, latency

**Status**: PASSED - AI architecture follows Azure AI Foundry SDK best practices with proper grounding.

### ✅ VI. Spec-Driven Development (NON-NEGOTIABLE)
- ✅ Specification maintained in `.specify/` directory structure
- ✅ This plan.md generated before implementation
- ✅ spec.md with user stories and acceptance criteria completed
- ✅ Constitution compliance verified at this phase gate
- ✅ Will generate tasks.md from approved specifications (Phase 2)

**Status**: PASSED - Following GitHub SpecKit workflow as mandated.

### Overall Constitution Status: ✅ ALL GATES PASSED

No violations detected. Architecture fully complies with all constitutional principles. Ready to proceed to Phase 0 (Research).

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/              # Entity models (Customer, UsageData, Recommendation, etc.)
│   ├── services/
│   │   ├── fabric_client.py      # Fabric IQ integration
│   │   ├── foundry_client.py     # Foundry IQ integration
│   │   ├── orchestration/        # Azure AI Foundry SDK agents
│   │   │   ├── retrieval_agent.py
│   │   │   ├── sentiment_agent.py
│   │   │   ├── reasoning_agent.py
│   │   │   └── validation_agent.py
│   │   ├── recommendation_service.py
│   │   └── customer_service.py
│   ├── api/
│   │   ├── customers.py          # Customer search & profile endpoints
│   │   ├── recommendations.py    # Recommendation generation endpoints
│   │   └── history.py            # Historical interaction endpoints
│   ├── core/
│   │   ├── config.py             # Configuration management
│   │   ├── auth.py               # Azure AD / Managed Identity
│   │   └── observability.py     # OpenTelemetry setup
│   └── main.py                   # FastAPI application entry
└── tests/
    ├── contract/                 # API contract tests
    ├── integration/              # Agent orchestration tests
    └── unit/                     # Business logic unit tests

frontend/
├── src/
│   ├── components/
│   │   ├── CustomerSearch/
│   │   ├── CustomerProfile/
│   │   ├── RecommendationList/
│   │   ├── RecommendationDetail/
│   │   ├── HistoryTimeline/
│   │   └── ExplainabilityPanel/
│   ├── pages/
│   │   ├── AgentDashboard.tsx   # Support agent main interface
│   │   └── CustomerDetail.tsx   # Customer profile page
│   ├── services/
│   │   ├── api-client.ts        # Backend API integration
│   │   └── auth-service.ts      # MSAL authentication
│   └── App.tsx
└── tests/
    ├── unit/                     # Component unit tests
    └── e2e/                      # Playwright E2E tests

dashboard/
├── reports/
│   ├── adoption-metrics.pbix    # Power BI adoption dashboard
│   └── upsell-pipeline.pbix     # Power BI upsell dashboard
└── datasets/
    └── fabric-connection.json   # Fabric Real-Time Intelligence connection

infrastructure/
├── bicep/                       # Azure infrastructure as code
│   ├── main.bicep
│   ├── app-service.bicep
│   ├── container-apps.bicep
│   ├── key-vault.bicep
│   └── monitoring.bicep
└── scripts/
    └── deploy.sh                # Deployment automation
```

**Structure Decision**: Web application structure selected (Option 2) because:
- Frontend (React SPA) + Backend (FastAPI) separation enables independent scaling
- Support agent interface requires rich client-side interactions (search, recommendation display, history timeline)
- Power BI dashboard deployed separately via Power BI Service (not embedded in main app for MVP)
- Agent orchestration runs in backend as part of recommendation service
- Infrastructure-as-code in separate directory for deployment automation

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
