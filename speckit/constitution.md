### Purpose

Establish mandatory architectural and operational principles for
building an Azure-native solution leveraging **Fabric IQ** and **Foundry
IQ** to deliver personalized adoption and upsell recommendations for
customer support personas.

### Principles

- **Security**

  - Use Managed Identity for all service-to-service authentication.

  - Store secrets in Azure Key Vault.

- **Compliance**

  - Integrate Microsoft Purview for data governance.

  - Apply Content Safety for responsible AI.

- **Observability**

  - Enable Application Insights and OpenTelemetry for monitoring.

- **AI/ML Best Practices**

  - Use Azure AI Foundry SDK for agent orchestration.

  - Implement multi-agent workflows with clear role definitions.

- **Spec-Driven Development**

  - All implementation must follow this specification and GitHub SpecKit
    workflow.
