<!--
  ============================================================================
  NOTE: This is a simplified working copy of the constitution.
  The authoritative constitution template is maintained at:
  .specify/memory/constitution.md
  
  Version: 1.0.0 | Last Updated: 2026-01-08
  ============================================================================
-->

### Purpose

Establish mandatory architectural and operational principles for building an Azure-native solution leveraging **Fabric IQ** and **Foundry IQ** to deliver personalized adoption and upsell recommendations for customer support personas.

### Principles

**I. Azure-Native Architecture**
- MUST use Azure-native services and follow Azure Well-Architected Framework
- Host all compute, storage, and AI workloads on Azure
- Use Azure AI Foundry SDK for multi-agent orchestration
- Leverage Fabric IQ for semantic modeling and real-time operational intelligence
- Integrate Foundry IQ for enterprise-grade knowledge retrieval

**II. Security & Identity (NON-NEGOTIABLE)**
- Use Managed Identity for ALL service-to-service authentication
- Store ALL secrets in Azure Key Vault
- Never hardcode credentials
- Implement RBAC for all Azure resources
- Enable Azure Defender for Cloud

**III. Compliance & Responsible AI (NON-NEGOTIABLE)**
- Integrate Microsoft Purview for data governance
- Apply Azure AI Content Safety to ALL AI-generated content
- Implement data classification and sensitivity labeling
- Maintain audit trails for data access and AI invocations
- Implement human-in-the-loop oversight for high-impact recommendations

**IV. Observability & Monitoring**
- Enable Application Insights for all components
- Implement OpenTelemetry instrumentation for distributed tracing
- Log all AI agent decisions with reasoning context
- Configure alerts for service health and performance degradation

**V. AI/ML Best Practices**
- Use Azure AI Foundry SDK for agent orchestration (do not custom-build)
- Implement multi-agent workflows with explicit role definitions
- Ground all recommendations in Foundry IQ and Fabric IQ
- Implement retrieval-augmented generation (RAG) patterns
- Version all prompts and agent configurations in source control

**VI. Spec-Driven Development (NON-NEGOTIABLE)**
- All implementation must follow GitHub SpecKit workflow
- Maintain specifications in `.specify/` directory
- Generate plan.md BEFORE implementation
- Verify constitution compliance at each phase gate

### Quality Standards

**Performance Requirements**:
- Recommendation latency: < 2 seconds p95
- Dashboard refresh: < 5 seconds
- Real-time ingestion lag: < 10 seconds

**Testing Requirements**:
- Unit tests (80%+ coverage)
- Integration tests for agent workflows
- Contract tests for API boundaries
- End-to-end testing before release

**Governance**: This constitution supersedes all other practices. Changes require explicit justification and version increment following semantic versioning.

**Version**: 1.0.0 | **Ratified**: 2026-01-08 | **Last Amended**: 2026-01-08
