<!--
  ============================================================================
  SYNC IMPACT REPORT - Constitution Amendment
  ============================================================================
  Version Change: Initial → 1.0.0
  Amendment Type: MAJOR (Initial ratification)
  Date: 2026-01-08
  
  Modified Principles:
  - ✅ NEW: I. Azure-Native Architecture
  - ✅ NEW: II. Security & Identity
  - ✅ NEW: III. Compliance & Responsible AI
  - ✅ NEW: IV. Observability & Monitoring
  - ✅ NEW: V. AI/ML Best Practices
  - ✅ NEW: VI. Spec-Driven Development (NON-NEGOTIABLE)
  
  New Sections:
  - ✅ Technology Stack Requirements
  - ✅ Quality & Performance Standards
  - ✅ Governance
  
  Template Alignment Status:
  - ✅ plan-template.md: Constitution Check section compatible
  - ✅ spec-template.md: Functional requirements align with principles
  - ✅ tasks-template.md: Task categorization supports principle-driven work
  
  Follow-up Actions:
  - None - all placeholders resolved
  ============================================================================
-->

# AdieuIQ Constitution

**Purpose**: Establish mandatory architectural and operational principles for building an Azure-native solution leveraging **Fabric IQ** and **Foundry IQ** to deliver personalized adoption and upsell recommendations for customer support personas.

## Core Principles

### I. Azure-Native Architecture

All components MUST use Azure-native services and follow Azure Well-Architected Framework principles.

**Requirements**:
- Host all compute, storage, and AI workloads on Azure
- Use Azure AI Foundry SDK for multi-agent orchestration
- Leverage Fabric IQ for semantic modeling and real-time operational intelligence
- Integrate Foundry IQ for enterprise-grade knowledge retrieval and grounding
- Use Azure OpenAI Service for reasoning and natural language generation
- Implement Fabric Real-Time Intelligence for streaming data ingestion
- Store unified data in OneLake for Fabric integration

**Rationale**: Azure-native architecture ensures seamless integration with Microsoft Fabric IQ and Foundry IQ, optimizes for Azure AI capabilities, and aligns with enterprise governance and compliance requirements.

### II. Security & Identity (NON-NEGOTIABLE)

All authentication and authorization MUST follow zero-trust security principles.

**Requirements**:
- Use Managed Identity for ALL service-to-service authentication
- Store ALL secrets, connection strings, and API keys in Azure Key Vault
- Never hardcode credentials in source code or configuration files
- Implement Role-Based Access Control (RBAC) for all Azure resources
- Enable Azure Defender for Cloud for security posture management
- Encrypt data at rest and in transit using Azure-managed encryption

**Rationale**: Managed Identity eliminates credential management risks; Key Vault provides centralized secret management with audit trails; zero-trust principles are mandatory for enterprise customer data handling.

### III. Compliance & Responsible AI (NON-NEGOTIABLE)

All data handling and AI operations MUST comply with governance and responsible AI standards.

**Requirements**:
- Integrate Microsoft Purview for data governance, lineage, and cataloging
- Apply Azure AI Content Safety filters to ALL AI-generated content
- Implement data classification and sensitivity labeling
- Maintain audit trails for all data access and AI model invocations
- Document AI model behavior, limitations, and failure modes
- Implement human-in-the-loop oversight for high-impact recommendations

**Rationale**: Purview ensures compliance with data residency and privacy regulations; Content Safety prevents generation of harmful content; responsible AI practices build trust with customers and support personas.

### IV. Observability & Monitoring

All services MUST implement comprehensive observability for production readiness.

**Requirements**:
- Enable Azure Application Insights for all application components
- Implement OpenTelemetry instrumentation for distributed tracing
- Log all AI agent decisions with reasoning context (for explainability)
- Configure alerts for service health, performance degradation, and anomalies
- Track key metrics: recommendation acceptance rate, response latency, agent orchestration success rate
- Implement structured logging with correlation IDs for request tracing

**Rationale**: Observability enables rapid incident response, performance optimization, and continuous improvement of AI recommendations; OpenTelemetry provides vendor-neutral instrumentation; Application Insights integrates with Azure ecosystem.

### V. AI/ML Best Practices

All AI agent implementations MUST follow orchestration and grounding best practices.

**Requirements**:
- Use Azure AI Foundry SDK for ALL agent orchestration (do not custom-build orchestrators)
- Implement multi-agent workflows with explicit role definitions (e.g., retrieval agent, reasoning agent, validation agent)
- Ground all recommendations in Foundry IQ knowledge base and Fabric IQ semantic context
- Implement retrieval-augmented generation (RAG) patterns for factual accuracy
- Version all prompts and agent configurations in source control
- Establish evaluation metrics for agent performance (accuracy, hallucination rate, latency)

**Rationale**: Azure AI Foundry SDK provides battle-tested orchestration patterns; multi-agent workflows enable specialization and improve reliability; grounding in Fabric IQ and Foundry IQ prevents hallucinations and ensures recommendations are data-driven.

### VI. Spec-Driven Development (NON-NEGOTIABLE)

All implementation work MUST follow the GitHub SpecKit workflow and constitution principles.

**Requirements**:
- Maintain specification documents in `.specify/` directory
- Update constitution.md for architectural decisions and principle changes
- Generate plan.md BEFORE implementation begins
- Create spec.md with user stories and acceptance criteria
- Derive tasks.md from approved specifications
- Verify constitution compliance at each phase gate
- Document all deviations from planned architecture with justification

**Rationale**: Spec-driven development ensures alignment between business requirements and implementation; constitution compliance prevents architectural drift; structured planning reduces rework and improves code quality.

## Technology Stack Requirements

**Infrastructure**:
- Azure AI Foundry (agent orchestration)
- Azure OpenAI Service (GPT-4 or later)
- Microsoft Fabric (Fabric IQ semantic layer, Real-Time Intelligence, OneLake)
- Azure AI Foundry IQ (knowledge retrieval and grounding)
- Azure Key Vault (secret management)
- Azure Managed Identity (authentication)

**Data & Analytics**:
- Fabric Real-Time Intelligence (event streaming)
- OneLake (unified data storage)
- Fabric IQ Semantic Layer (semantic modeling)
- Power BI (visualization and dashboards)

**Governance & Security**:
- Microsoft Purview (data governance)
- Azure AI Content Safety (responsible AI)
- Azure Defender for Cloud (security posture)

**Observability**:
- Azure Application Insights (APM)
- OpenTelemetry (distributed tracing)

**Development Workflow**:
- GitHub (source control)
- GitHub Copilot + SpecKit (AI-assisted implementation)

## Quality & Performance Standards

**Performance Requirements**:
- Recommendation generation latency: < 2 seconds p95
- Dashboard refresh latency: < 5 seconds
- Real-time data ingestion lag: < 10 seconds
- Agent orchestration timeout: 30 seconds maximum

**Reliability Requirements**:
- Service availability: 99.9% SLA target
- Graceful degradation when AI services unavailable
- Implement circuit breakers for external service calls
- Retry policies with exponential backoff for transient failures

**Testing Requirements**:
- Unit tests for all business logic (minimum 80% coverage)
- Integration tests for agent orchestration workflows
- Contract tests for API boundaries
- Load tests for Power BI dashboard under concurrent user load
- End-to-end testing of demo scenarios before release

## Governance

This constitution supersedes all other development practices and architectural decisions. All implementation work, code reviews, and architectural designs MUST comply with these principles.

**Amendment Process**:
- Constitution changes require explicit justification and approval
- Version increments follow semantic versioning (MAJOR.MINOR.PATCH)
- MAJOR: Backward-incompatible principle changes or removals
- MINOR: New principles or materially expanded guidance
- PATCH: Clarifications, wording fixes, non-semantic refinements
- All amendments MUST include migration plan for existing code

**Compliance Verification**:
- Every specification (spec.md) MUST include constitution check section
- Every implementation plan (plan.md) MUST verify principle alignment
- Code reviews MUST verify compliance with security, observability, and AI principles
- Deviations MUST be documented with explicit justification in complexity tracking section

**Runtime Development Guidance**:
- Consult `.specify/templates/commands/*.md` for workflow execution
- Reference `.github/prompts/speckit.*.prompt.md` for command-specific guidance
- Use `README.md` and `speckit/` artifacts for project context

**Version**: 1.0.0 | **Ratified**: 2026-01-08 | **Last Amended**: 2026-01-08
