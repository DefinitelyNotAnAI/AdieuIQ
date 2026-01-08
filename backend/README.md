# Customer Recommendation Engine - Backend

Azure-native Python backend for customer recommendation system.

## Requirements

- Python 3.11+
- Azure subscription with access to:
  - Azure AI Foundry SDK
  - Fabric IQ
  - Foundry IQ
  - Azure OpenAI Service
  - Azure Cosmos DB
  - Azure Redis Cache
  - Azure Key Vault

## Installation

```bash
pip install -r requirements.txt
```

## Running Locally

```bash
# Configure environment
cp .env.example .env
# Edit .env with your Azure credentials

# Run development server
python -m uvicorn src.main:app --reload --port 8000
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test types
pytest tests/unit/
pytest tests/integration/
pytest tests/contract/
```

## Project Structure

```
backend/
├── src/
│   ├── models/          # Pydantic data models
│   ├── services/        # Business logic and external integrations
│   ├── api/             # FastAPI endpoints
│   ├── core/            # Configuration, auth, observability
│   └── main.py          # Application entry point
└── tests/               # Test suites
```
