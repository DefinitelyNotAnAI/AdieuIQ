# Tasks: Customer Recommendation Engine

**Input**: Design documents from `specs/001-customer-recommendation/`  
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Test tasks included per constitutional requirement (minimum 80% coverage). Tests are marked with [TEST] and should be implemented alongside corresponding feature tasks to support continuous validation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `- [ ] [ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/`, `dashboard/`, `infrastructure/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project directory structure per plan.md (backend/, frontend/, dashboard/, infrastructure/)
- [X] T002 Initialize Python backend project with requirements.txt (FastAPI, Azure AI Foundry SDK, azure-identity, azure-keyvault-secrets, OpenTelemetry SDK, pytest)
- [X] T003 [P] Initialize TypeScript frontend project with package.json (React 18, TypeScript 5.x, @azure/msal-browser, @testing-library/react)
- [X] T004 [P] Configure ESLint and Prettier for frontend in frontend/.eslintrc.json and frontend/.prettierrc
- [X] T005 [P] Configure Black and Flake8 for backend in backend/pyproject.toml
- [X] T006 Create .gitignore for Python, Node.js, and Azure artifacts

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T007 Setup Azure infrastructure with Bicep in infrastructure/bicep/main.bicep (Resource Group, Key Vault, App Service, Container Apps, Cosmos DB, Redis Cache, Application Insights)
- [ ] T008 [P] Configure Azure Managed Identity for App Service and Container Apps in infrastructure/bicep/app-service.bicep and infrastructure/bicep/container-apps.bicep
- [ ] T009 [P] Create Azure Key Vault configuration in infrastructure/bicep/key-vault.bicep with secrets for Fabric IQ, Foundry IQ, OpenAI endpoints
- [ ] T010 Configure Application Insights and OpenTelemetry in infrastructure/bicep/monitoring.bicep
- [ ] T011 Implement core configuration management in backend/src/core/config.py (load from environment variables and Key Vault)
- [ ] T012 [P] Implement Azure AD authentication helper in backend/src/core/auth.py (Managed Identity credential, JWT token validation)
- [ ] T013 [P] Implement observability setup in backend/src/core/observability.py (OpenTelemetry tracer, Application Insights exporter, correlation ID middleware)
- [ ] T014 Create FastAPI application entry point in backend/src/main.py with CORS, authentication middleware, and health check endpoint
- [ ] T015 [P] Create MSAL authentication service in frontend/src/services/auth-service.ts (PublicClientApplication, token acquisition)
- [ ] T016 [P] Create API client service in frontend/src/services/api-client.ts (HTTP client with token injection and error handling)
- [ ] T017 Setup Cosmos DB database and containers in infrastructure/bicep/main.bicep (customers, recommendations, interaction-events collections)
- [ ] T018 [P] Setup Redis Cache configuration in infrastructure/bicep/main.bicep (Standard tier, 1GB)
- [ ] T019 Create deployment script in infrastructure/scripts/deploy.sh (deploy Bicep templates, configure RBAC, seed test data)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Customer Lookup and Recommendation Generation (Priority: P1) 🎯 MVP

**Goal**: Enable support agents to search for customers and receive AI-generated recommendations within 2 seconds

**Independent Test**: Search for test customer, verify profile loads with usage data and sentiment, confirm 2-5 adoption + 1-3 upsell recommendations generated within 2s

### Backend Implementation for User Story 1

- [X] T020 [P] [US1] Create Customer model in backend/src/models/customer.py (Pydantic model with UUID, company_name, industry_segment, product_tier, validation rules per data-model.md)
- [X] T021 [P] [US1] Create UsageData model in backend/src/models/usage_data.py (customer_id FK, feature_name, usage_count, intensity_score enum)
- [X] T022 [P] [US1] Create InteractionEvent model in backend/src/models/interaction_event.py (event_type enum, sentiment_score float validation, resolution_status enum)
- [X] T023 [P] [US1] Create Recommendation model in backend/src/models/recommendation.py (recommendation_type enum, confidence_score float, reasoning_chain JSON, state transitions per data-model.md)
- [X] T024 [P] [US1] Create AgentContribution model in backend/src/models/agent_contribution.py (agent_type enum, execution_time_ms tracking)
- [X] T025 [US1] Implement Fabric IQ client in backend/src/services/fabric_client.py (query usage trends, semantic layer integration, mock mode for local dev per quickstart.md)
- [X] T026 [US1] Implement Foundry IQ client in backend/src/services/foundry_client.py (knowledge base search, RAG retrieval, mock mode for local dev)
- [X] T027 [US1] Implement Content Safety service in backend/src/services/content_safety.py (Azure AI Content Safety client, text validation per FR-019)
- [X] T028 [US1] Implement Retrieval Agent in backend/src/services/orchestration/retrieval_agent.py (query Fabric IQ and Foundry IQ in parallel, return usage_data + knowledge_articles + confidence score)
- [X] T029 [P] [US1] Implement Sentiment Analysis Agent in backend/src/services/orchestration/sentiment_agent.py (analyze interaction history, calculate sentiment score and factors)
- [X] T030 [US1] Implement Reasoning Agent in backend/src/services/orchestration/reasoning_agent.py (combine retrieval + sentiment, generate candidate recommendations, apply sentiment-aware filtering per FR-015)
- [X] T031 [US1] Implement Validation Agent in backend/src/services/orchestration/validation_agent.py (check duplicates per FR-014, apply Content Safety filters, constitutional compliance checks)
- [X] T032 [US1] Implement multi-agent orchestrator in backend/src/services/orchestration/orchestrator.py (Azure AI Foundry SDK, parallel execution for T028+T029, sequential for T030+T031, log reasoning chains per FR-010)
- [X] T033 [US1] Implement Recommendation Service in backend/src/services/recommendation_service.py (orchestrate agents, cache results in Cosmos DB, handle graceful degradation per FR-017)
- [X] T034 [US1] Implement Customer Service in backend/src/services/customer_service.py (search with fuzzy matching per FR-001, retrieve profile from Cosmos DB, aggregate usage from Fabric IQ, calculate sentiment indicators)
- [X] T035 [US1] Create customer search endpoint in backend/src/api/customers.py GET /customers/search (fuzzy matching, pagination, RBAC check)
- [X] T036 [US1] Create customer profile endpoint in backend/src/api/customers.py GET /customers/{customer_id}/profile (return CustomerProfile composite per contracts/openapi.yaml)
- [X] T037 [US1] Create recommendation generation endpoint in backend/src/api/recommendations.py POST /customers/{customer_id}/recommendations (trigger orchestration, return adoption + upsell recommendations, track generation_time_ms)
- [X] T038 [US1] Create recommendation outcome update endpoint in backend/src/api/recommendations.py PUT /recommendations/{recommendation_id}/outcome (update status to Delivered/Accepted/Declined, audit trail)
- [X] T038a [US1] Implement recommendation acceptance tracking in backend/src/api/recommendations.py (POST /recommendations/{recommendation_id}/acceptance with agent_confirmed boolean, timestamp, optional feedback text; track acceptance rate for SC-002 accuracy measurement; store in Cosmos DB for analytics per FR-020 audit trail)
- [X] T038b [P] [US1] Add acceptance confirmation UI in frontend/src/components/RecommendationDetail/RecommendationDetail.tsx (add "Mark as Delivered" button, confirmation modal with optional feedback field, optimistic UI update, error handling)

### Frontend Implementation for User Story 1

- [X] T039 [P] [US1] Create CustomerSearch component in frontend/src/components/CustomerSearch/CustomerSearch.tsx (search input with fuzzy matching, result list, click to select customer)
- [X] T040 [P] [US1] Create CustomerProfile component in frontend/src/components/CustomerProfile/CustomerProfile.tsx (display company info, product tier, usage summary, sentiment indicators)
- [X] T041 [P] [US1] Create RecommendationList component in frontend/src/components/RecommendationList/RecommendationList.tsx (adoption + upsell sections, confidence scores, accept/decline actions)
- [X] T042 [P] [US1] Create RecommendationDetail component in frontend/src/components/RecommendationDetail/RecommendationDetail.tsx (show recommendation text, supporting context, usage data, sentiment analysis, knowledge base references)
- [X] T043 [US1] Create AgentDashboard page in frontend/src/pages/AgentDashboard.tsx (integrate CustomerSearch component, authentication check)
- [X] T044 [US1] Create CustomerDetail page in frontend/src/pages/CustomerDetail.tsx (integrate CustomerProfile, RecommendationList, RecommendationDetail components, fetch data from API)
- [X] T045 [US1] Implement App routing in frontend/src/App.tsx (MsalProvider wrapper, protected routes for AgentDashboard and CustomerDetail, RBAC enforcement)
- [X] T046 [US1] Add error handling and loading states in frontend/src/services/api-client.ts (handle 401, 404, 500 errors, display user-friendly messages)

**Checkpoint**: User Story 1 complete - support agents can search customers and view recommendations (core MVP functional)

---

## Phase 4: User Story 2 - Real-Time Dashboard for Customer Success Managers (Priority: P2)

**Goal**: Provide Customer Success Managers with real-time adoption metrics and upsell opportunities

**Independent Test**: Load Power BI dashboard, verify adoption metrics and upsell pipeline display within 5s, confirm data refreshes within 10s of new events

- [ ] T047 [P] [US2] Create Fabric Real-Time Intelligence connection configuration in dashboard/datasets/fabric-connection.json (OneLake endpoint, authentication via Managed Identity)
- [ ] T048 [US2] Design Power BI adoption metrics report in dashboard/reports/adoption-metrics.pbix (feature usage %, low-adoption alerts, customer segmentation by adoption level, Direct Query mode to Fabric per research.md Decision 5)
- [ ] T049 [US2] Design Power BI upsell pipeline report in dashboard/reports/upsell-pipeline.pbix (prioritized customer list with upsell potential, estimated revenue impact, recommendation confidence scores)
- [ ] T050 [US2] Configure Power BI row-level security in dashboard/reports/adoption-metrics.pbix (Azure AD groups for Customer Success Manager role)
- [ ] T051 [US2] Deploy Power BI reports to Power BI Service workspace (configure refresh schedule, enable embedding if needed for future)
- [ ] T052 [US2] Create data pipeline from Cosmos DB to Fabric Real-Time Intelligence (recommendation events, acceptance rates, customer health scores, max 10s lag per FR-012)
- [ ] T053 [US2] Add dashboard access link to AgentDashboard page in frontend/src/pages/AgentDashboard.tsx (conditionally show for Customer Success Manager role only)

**Checkpoint**: User Story 2 complete - managers can monitor adoption trends and identify upsell opportunities

---

## Phase 5: User Story 3 - Historical Interaction Context Retrieval (Priority: P3)

**Goal**: Enable support agents to view customer interaction history and past recommendations

**Independent Test**: View customer with 100+ interactions, verify timeline loads within 3s, confirm past recommendations show outcomes (accepted/declined/pending)

- [ ] T054 [P] [US3] Create historical interaction query in backend/src/services/customer_service.py (retrieve past 12 months of InteractionEvents from Cosmos DB, sort chronologically)
- [ ] T055 [P] [US3] Create past recommendations query in backend/src/services/recommendation_service.py (retrieve past 12 months of Recommendations with outcomes, filter by customer_id)
- [ ] T056 [US3] Create customer history endpoint in backend/src/api/history.py GET /customers/{customer_id}/history (return interactions + past_recommendations per contracts/openapi.yaml, support months query param)
- [ ] T057 [US3] Update Reasoning Agent in backend/src/services/orchestration/reasoning_agent.py (check for previously declined recommendations per FR-014, flag duplicates or provide re-suggesting reasoning)
- [ ] T058 [P] [US3] Create HistoryTimeline component in frontend/src/components/HistoryTimeline/HistoryTimeline.tsx (chronological display of tickets/chats/calls, recommendation events, outcome status badges)
- [ ] T059 [US3] Update CustomerDetail page in frontend/src/pages/CustomerDetail.tsx (add history tab, lazy load timeline when tab is clicked per quickstart.md optimization tip)

**Checkpoint**: User Story 3 complete - agents can view historical context to improve recommendation quality

---

## Phase 6: User Story 4 - Multi-Agent Orchestration with Explainability (Priority: P3)

**Goal**: Provide transparency into AI reasoning chain for trust and debugging

**Independent Test**: Generate recommendation, click "Show reasoning", verify explainability panel shows all agent contributions (Retrieval, Sentiment, Reasoning, Validation) with data sources and confidence scores

- [ ] T060 [P] [US4] Create explainability endpoint in backend/src/api/recommendations.py GET /recommendations/{recommendation_id}/explainability (return recommendation + agent_contributions per contracts/openapi.yaml)
- [ ] T061 [US4] Update orchestrator in backend/src/services/orchestration/orchestrator.py (_log_agent_contributions method to store AgentContribution records in Cosmos DB with input_data, output_result, confidence_score, execution_time_ms)
- [ ] T062 [P] [US4] Create ExplainabilityPanel component in frontend/src/components/ExplainabilityPanel/ExplainabilityPanel.tsx (agent breakdown with icons for each agent type, collapsible sections for input/output, data source references with timestamps, confidence score visualizations)
- [ ] T063 [US4] Update RecommendationDetail component in frontend/src/components/RecommendationDetail/RecommendationDetail.tsx (add "Show reasoning" button, modal/drawer to display ExplainabilityPanel)

**Checkpoint**: User Story 4 complete - explainability enables trust and troubleshooting

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Production readiness, performance optimization, and final polish

- [ ] T064 [P] Add Redis caching for customer profile lookups in backend/src/services/customer_service.py (5-minute TTL per quickstart.md optimization tip)
- [ ] T065 [P] Add Redis caching for Fabric IQ queries in backend/src/services/fabric_client.py (cache usage trends with 1-hour TTL)
- [ ] T066 [P] Implement circuit breaker pattern for Fabric IQ and Foundry IQ clients in backend/src/services/fabric_client.py and backend/src/services/foundry_client.py (graceful degradation per FR-017)
- [ ] T067 [P] Configure alerts in infrastructure/bicep/monitoring.bicep (recommendation latency >2s, orchestration failures, service health degradation)
- [ ] T068 [P] Implement Purview integration for audit trails in backend/src/services/customer_service.py and backend/src/services/recommendation_service.py (log customer data access and recommendation deliveries per FR-020)
- [ ] T069 Add API response compression in backend/src/main.py (gzip middleware for responses >1KB)
- [ ] T070 [P] Optimize frontend bundle size (code splitting, lazy loading routes, tree shaking in frontend/package.json build config)
- [ ] T071 [P] Add loading skeletons and optimistic UI updates in frontend/src/components/ (improve perceived performance)
- [ ] T072 Create end-to-end test suite in frontend/tests/e2e/ using Playwright (test US1: search + profile + recommendations, test US3: history tab, test US4: explainability panel)
- [ ] T073 [P] Create load test suite using Locust in backend/tests/load/ (test 100+ concurrent agents, verify <2s p95 latency per SC-003)
- [ ] T074 Run security scan with Azure Defender for Cloud (verify no hardcoded secrets, validate Managed Identity usage, check for vulnerabilities)
- [ ] T075 Create deployment documentation in infrastructure/README.md (prerequisites, deployment steps, RBAC configuration, troubleshooting)
- [ ] T076 Create user guide documentation in docs/USER_GUIDE.md (support agent workflows, manager dashboard usage, explainability interpretation)

**Checkpoint**: Production-ready application with all user stories complete

---

## Phase 8: Testing & Quality Assurance (Constitutional Requirement)

**Purpose**: Achieve 80%+ code coverage per Constitution Principle VI and validate all functional requirements

**⚠️ CONSTITUTIONAL MANDATE**: Minimum 80% coverage required before production deployment

### Backend Unit Tests (Target: 80%+ coverage)

- [ ] T077 [P] [TEST] Create unit tests for Customer model in backend/tests/unit/models/test_customer.py (validation rules, UUID generation, field constraints per data-model.md)
- [ ] T078 [P] [TEST] Create unit tests for Recommendation model in backend/tests/unit/models/test_recommendation.py (state transitions, confidence score validation, reasoning chain structure)
- [ ] T079 [P] [TEST] Create unit tests for Fabric IQ client in backend/tests/unit/services/test_fabric_client.py (mock API responses, error handling, cache behavior per T025)
- [ ] T080 [P] [TEST] Create unit tests for Foundry IQ client in backend/tests/unit/services/test_foundry_client.py (mock knowledge retrieval, RAG pattern validation per T026)
- [ ] T081 [TEST] Create unit tests for Retrieval Agent in backend/tests/unit/orchestration/test_retrieval_agent.py (parallel execution, data source merging, confidence scoring per T028)
- [ ] T082 [P] [TEST] Create unit tests for Sentiment Agent in backend/tests/unit/orchestration/test_sentiment_agent.py (sentiment calculation, factor analysis per T029)
- [ ] T083 [TEST] Create unit tests for Reasoning Agent in backend/tests/unit/orchestration/test_reasoning_agent.py (recommendation generation, sentiment filtering per FR-015, duplicate detection per FR-014)
- [ ] T084 [TEST] Create unit tests for Validation Agent in backend/tests/unit/orchestration/test_validation_agent.py (Content Safety integration per T031, constitutional compliance checks)

### Backend Integration Tests

- [ ] T085 [TEST] Create integration tests for multi-agent orchestration in backend/tests/integration/test_orchestration_workflow.py (end-to-end agent flow per T032, verify Retrieval || Sentiment → Reasoning → Validation sequence, validate reasoning chain logging per FR-010)
- [ ] T086 [TEST] Create integration tests for recommendation service in backend/tests/integration/test_recommendation_service.py (Cosmos DB caching per T033, graceful degradation per FR-017, verify 2s latency requirement per FR-005)
- [ ] T087 [TEST] Create integration tests for customer service in backend/tests/integration/test_customer_service.py (fuzzy search per FR-001, profile aggregation, Fabric IQ integration)

### Backend Contract Tests

- [ ] T088 [P] [TEST] Create API contract tests in backend/tests/contract/test_customer_api.py (GET /customers/search, GET /customers/{id}/profile per contracts/openapi.yaml, validate response schemas)
- [ ] T089 [P] [TEST] Create API contract tests in backend/tests/contract/test_recommendation_api.py (POST /customers/{id}/recommendations, PUT /recommendations/{id}/outcome, GET /recommendations/{id}/explainability per contracts/openapi.yaml)
- [ ] T090 [P] [TEST] Create API contract tests in backend/tests/contract/test_history_api.py (GET /customers/{id}/history per contracts/openapi.yaml, validate timeline structure)

### Frontend Unit Tests

- [ ] T091 [P] [TEST] Create component tests for CustomerSearch in frontend/tests/unit/components/test_CustomerSearch.test.tsx (search input handling, fuzzy matching display, result selection per T039)
- [ ] T092 [P] [TEST] Create component tests for CustomerProfile in frontend/tests/unit/components/test_CustomerProfile.test.tsx (data display, sentiment indicators per T040)
- [ ] T093 [P] [TEST] Create component tests for RecommendationList in frontend/tests/unit/components/test_RecommendationList.test.tsx (adoption/upsell sections, confidence scores, accept/decline actions per T041)
- [ ] T094 [P] [TEST] Create component tests for ExplainabilityPanel in frontend/tests/unit/components/test_ExplainabilityPanel.test.tsx (agent breakdown, data source references per T062)

### Coverage Validation

- [ ] T095 [TEST] Configure coverage reporting in backend/pyproject.toml (pytest-cov, 80% threshold, exclude migrations and generated code)
- [ ] T096 [TEST] Configure coverage reporting in frontend/package.json (Jest coverage, 80% threshold for components and services)
- [ ] T097 [TEST] Run full test suite and generate coverage report (verify 80%+ coverage achieved, identify gaps, document any justified exclusions)

**Checkpoint**: All tests passing, 80%+ coverage achieved, ready for production deployment

---

## Dependencies & Execution Plan

### Story Completion Order (Blocking Dependencies)

```
Phase 1 (Setup) → Phase 2 (Foundational) → [Phase 3 (US1) ✅ MUST COMPLETE FIRST]
                                           ↓
                                  Phase 4 (US2) - depends on T033 (recommendation service exists)
                                           ↓
                                  Phase 5 (US3) - depends on T033, T036 (profile endpoint exists)
                                           ↓
                                  Phase 6 (US4) - depends on T037 (recommendation generation exists)
                                           ↓
                                  Phase 7 (Polish) - depends on all user stories complete
```

### Parallel Execution Opportunities

**Phase 1 (Setup)**: T003, T004, T005 can run in parallel (frontend + backend init separate)

**Phase 2 (Foundational)**:
- T008 + T009 + T010 (Bicep files different resources)
- T012 + T013 + T015 + T016 (auth + observability + frontend services independent)
- T017 + T018 (Cosmos DB + Redis separate resources)

**Phase 3 (User Story 1)**:
- T020-T024 (models in separate files)
- T029 || T028 (sentiment agent || retrieval agent - parallel execution by design)
- T039-T042 (React components in separate files)

**Phase 4 (User Story 2)**:
- T047 + T048 + T049 (Power BI reports can be designed in parallel)

**Phase 5 (User Story 3)**:
- T054 + T055 (queries independent)
- T058 (component) || T056 (endpoint) if component uses mocked data initially

**Phase 6 (User Story 4)**:
- T060 + T062 (endpoint + component can be developed with contracts first)

**Phase 7 (Polish)**:
- T064-T068 (caching, circuit breakers, alerts, Purview - all independent)
- T070 + T071 (frontend optimizations)
- T072 + T073 (E2E + load tests)

### MVP Scope (Suggested for First Release)

**Minimum Viable Product = User Story 1 Only**

Tasks T001-T048 constitute a complete, independently valuable MVP:
- Support agents can search for customers ✅
- View customer profile with usage and sentiment ✅
- Receive AI-generated recommendations (adoption + upsell) ✅
- See recommendation context and reasoning ✅
- Track recommendation acceptance for accuracy measurement (SC-002) ✅
- All constitutional requirements met (Managed Identity, Content Safety, Observability, etc.) ✅

**Total MVP Tasks**: 48 feature tasks + unit/integration/contract tests from Phase 8  
**Estimated MVP Completion**: Can be delivered incrementally as Phase 1 → Phase 2 → Phase 3 + Phase 8 tests

**Post-MVP Increments**:
- Increment 1 (US2): Add dashboard for managers (7 tasks, T047-T053)
- Increment 2 (US3): Add historical context (6 tasks, T054-T059)
- Increment 3 (US4): Add explainability (4 tasks, T060-T063)
- Increment 4: Polish & production hardening (13 tasks, T064-T076)

---

## Task Summary

**Total Tasks**: 97 tasks (76 feature tasks + 21 test tasks)  
**By User Story**:
- Setup: 6 tasks
- Foundational: 13 tasks (blocking all user stories)
- User Story 1 (P1): 29 tasks (MVP - MUST COMPLETE FIRST, includes acceptance tracking for SC-002)
- User Story 2 (P2): 7 tasks
- User Story 3 (P3): 6 tasks
- User Story 4 (P3): 4 tasks
- Polish: 13 tasks
- Testing: 21 tasks (constitutional requirement, 80%+ coverage)

**Parallel Opportunities**: 29 tasks marked with [P] can run in parallel with others in same phase

**Constitutional Compliance**:
- ✅ All tasks follow Managed Identity + Key Vault pattern (T008, T009, T012)
- ✅ Content Safety integration (T027, T031)
- ✅ OpenTelemetry observability (T013, T032)
- ✅ Azure AI Foundry SDK orchestration (T032)
- ✅ RAG with Fabric IQ + Foundry IQ (T025, T026, T028)
- ✅ Purview audit trails (T068)

**Format Validation**: ✅ ALL 97 tasks follow strict checklist format:
- Checkbox: `- [ ]`
- Task ID: Sequential T001-T097
- [P] marker: Present for parallelizable tasks
- [Story] label: Present for all user story tasks (US1, US2, US3, US4)
- [TEST] marker: Present for all test tasks (T077-T097)
- File paths: Included in all implementation task descriptions
