# Data Pipeline: Cosmos DB → Fabric Real-Time Intelligence

**Purpose**: Stream recommendation events, acceptance rates, and customer health scores from Cosmos DB to Fabric for Power BI dashboards  
**Latency Requirement**: <10 seconds (FR-012)  
**Technology**: Azure Data Factory, Cosmos DB Change Feed, Fabric Eventstream

## Architecture

```
┌──────────────┐   Change    ┌─────────────┐   Eventstream   ┌──────────────────────┐   Direct    ┌──────────┐
│  Cosmos DB   │──── Feed ───▶│  Azure      │────────────────▶│ Fabric Real-Time     │─── Query ───▶│ Power BI │
│  (Cache)     │              │  Function   │                 │ Intelligence (KQL)   │              │ Service  │
└──────────────┘              └─────────────┘                 └──────────────────────┘              └──────────┘
   ^                                                                    │
   │ Writes                                                             ▼
   │                                                             ┌──────────────┐
┌──────────────┐                                                │  OneLake     │
│  Backend     │                                                │  (Storage)   │
│  API         │                                                └──────────────┘
└──────────────┘
```

## Data Sources

### Cosmos DB Collections

**Collection 1: recommendations**
- **Purpose**: Cache of generated recommendations for customer profile page
- **TTL**: 12 months (per recommendation_service.py)
- **Change Feed**: Enabled (track inserts, updates)
- **Partition Key**: `customer_id`
- **Throughput**: 4000 RU/s (autoscale)

**Collection 2: customers**
- **Purpose**: Customer profile metadata
- **TTL**: None (permanent storage)
- **Change Feed**: Enabled (track updates to account_manager_email, product_tier)
- **Partition Key**: `customer_id`
- **Throughput**: 1000 RU/s (manual)

**Collection 3: usage_data**
- **Purpose**: Feature usage metrics
- **TTL**: 90 days
- **Change Feed**: Enabled (track usage_count, last_used_at updates)
- **Partition Key**: `customer_id`
- **Throughput**: 2000 RU/s (autoscale)

**Collection 4: interaction_events**
- **Purpose**: Customer support interactions
- **TTL**: 12 months
- **Change Feed**: Enabled (track new interactions, sentiment_score updates)
- **Partition Key**: `customer_id`
- **Throughput**: 2000 RU/s (autoscale)

## Fabric Destination

### Fabric Real-Time Intelligence (KQL Database)

**Workspace**: #{FABRIC_WORKSPACE_ID}#  
**KQL Database**: `adieuiq-rtdb`  
**Ingestion Method**: Eventstream (via Azure Event Hubs-compatible endpoint)

**Tables**:
1. `recommendations` (target for Cosmos DB recommendations collection)
2. `customers` (target for Cosmos DB customers collection)
3. `usage_data` (target for Cosmos DB usage_data collection)
4. `interaction_events` (target for Cosmos DB interaction_events collection)

## Pipeline Components

### Component 1: Azure Function (Change Feed Processor)

**Function Name**: `CosmosToFabricProcessor`  
**Runtime**: Python 3.11  
**Trigger**: Cosmos DB Change Feed  
**Hosting**: Consumption Plan (serverless)  
**Managed Identity**: Enabled (for Fabric authentication)

**Function Code** (`function_app.py`):
```python
import azure.functions as func
import logging
import json
from azure.identity import DefaultAzureCredential
from azure.eventhub import EventHubProducerClient, EventData
import os

app = func.FunctionApp()

# Environment variables
EVENT_HUB_NAMESPACE = os.environ["FABRIC_EVENTHUB_NAMESPACE"]
EVENT_HUB_NAME = os.environ["FABRIC_EVENTHUB_NAME"]

# Initialize Event Hub client with Managed Identity
credential = DefaultAzureCredential()
producer_client = EventHubProducerClient(
    fully_qualified_namespace=f"{EVENT_HUB_NAMESPACE}.servicebus.windows.net",
    eventhub_name=EVENT_HUB_NAME,
    credential=credential
)

@app.cosmos_db_trigger(
    arg_name="documents",
    database_name="adieuiq",
    collection_name="recommendations",
    connection_string_setting="COSMOS_DB_CONNECTION",
    lease_collection_name="leases",
    create_lease_collection_if_not_exists=True
)
def recommendations_change_feed(documents: func.DocumentList) -> None:
    """Process Cosmos DB changes for recommendations collection."""
    if documents:
        logging.info(f"Processing {len(documents)} recommendation change(s)")
        
        events = []
        for doc in documents:
            # Transform Cosmos DB document to Fabric schema
            event_data = {
                "recommendation_id": doc.get("id"),
                "customer_id": doc.get("customer_id"),
                "recommendation_type": doc.get("recommendation_type"),
                "recommended_products": doc.get("recommended_products", []),
                "reasoning": doc.get("reasoning"),
                "confidence_score": doc.get("confidence_score"),
                "generated_at": doc.get("generated_at"),
                "delivered_at": doc.get("delivered_at"),
                "outcome_status": doc.get("outcome_status"),
                "estimated_revenue_impact": doc.get("estimated_revenue_impact", 0),
                "_ts": doc.get("_ts")  # Cosmos DB timestamp for deduplication
            }
            
            events.append(EventData(json.dumps(event_data)))
        
        # Send batch to Event Hub (Fabric Eventstream)
        with producer_client:
            event_batch = producer_client.create_batch()
            for event in events:
                event_batch.add(event)
            producer_client.send_batch(event_batch)
        
        logging.info(f"Sent {len(events)} events to Fabric Eventstream")

@app.cosmos_db_trigger(
    arg_name="documents",
    database_name="adieuiq",
    collection_name="customers",
    connection_string_setting="COSMOS_DB_CONNECTION",
    lease_collection_name="leases",
    create_lease_collection_if_not_exists=True
)
def customers_change_feed(documents: func.DocumentList) -> None:
    """Process Cosmos DB changes for customers collection."""
    if documents:
        logging.info(f"Processing {len(documents)} customer change(s)")
        
        events = []
        for doc in documents:
            event_data = {
                "customer_id": doc.get("id"),
                "company_name": doc.get("company_name"),
                "industry_segment": doc.get("industry_segment"),
                "product_tier": doc.get("product_tier"),
                "current_products": doc.get("current_products", []),
                "contact_email": doc.get("contact_email"),
                "account_manager_email": doc.get("account_manager_email"),
                "_ts": doc.get("_ts")
            }
            events.append(EventData(json.dumps(event_data)))
        
        with producer_client:
            event_batch = producer_client.create_batch()
            for event in events:
                event_batch.add(event)
            producer_client.send_batch(event_batch)
        
        logging.info(f"Sent {len(events)} customer events to Fabric Eventstream")

@app.cosmos_db_trigger(
    arg_name="documents",
    database_name="adieuiq",
    collection_name="usage_data",
    connection_string_setting="COSMOS_DB_CONNECTION",
    lease_collection_name="leases",
    create_lease_collection_if_not_exists=True
)
def usage_data_change_feed(documents: func.DocumentList) -> None:
    """Process Cosmos DB changes for usage_data collection."""
    if documents:
        logging.info(f"Processing {len(documents)} usage data change(s)")
        
        events = []
        for doc in documents:
            event_data = {
                "customer_id": doc.get("customer_id"),
                "feature_name": doc.get("feature_name"),
                "usage_count": doc.get("usage_count"),
                "intensity_score": doc.get("intensity_score"),
                "last_used_at": doc.get("last_used_at"),
                "timestamp": doc.get("timestamp"),
                "_ts": doc.get("_ts")
            }
            events.append(EventData(json.dumps(event_data)))
        
        with producer_client:
            event_batch = producer_client.create_batch()
            for event in events:
                event_batch.add(event)
            producer_client.send_batch(event_batch)
        
        logging.info(f"Sent {len(events)} usage data events to Fabric Eventstream")

@app.cosmos_db_trigger(
    arg_name="documents",
    database_name="adieuiq",
    collection_name="interaction_events",
    connection_string_setting="COSMOS_DB_CONNECTION",
    lease_collection_name="leases",
    create_lease_collection_if_not_exists=True
)
def interaction_events_change_feed(documents: func.DocumentList) -> None:
    """Process Cosmos DB changes for interaction_events collection."""
    if documents:
        logging.info(f"Processing {len(documents)} interaction event change(s)")
        
        events = []
        for doc in documents:
            event_data = {
                "interaction_id": doc.get("id"),
                "customer_id": doc.get("customer_id"),
                "event_type": doc.get("event_type"),
                "summary": doc.get("summary"),
                "sentiment_score": doc.get("sentiment_score"),
                "resolution_status": doc.get("resolution_status"),
                "occurred_at": doc.get("occurred_at"),
                "_ts": doc.get("_ts")
            }
            events.append(EventData(json.dumps(event_data)))
        
        with producer_client:
            event_batch = producer_client.create_batch()
            for event in events:
                event_batch.add(event)
            producer_client.send_batch(event_batch)
        
        logging.info(f"Sent {len(events)} interaction events to Fabric Eventstream")
```

**Function Configuration** (`host.json`):
```json
{
  "version": "2.0",
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "maxTelemetryItemsPerSecond": 20
      }
    }
  },
  "extensions": {
    "cosmosDB": {
      "maxItemsPerInvocation": 100,
      "preferredLocations": ["East US", "West US"],
      "connectionMode": "Direct"
    }
  }
}
```

**Function Settings** (`local.settings.json` for local dev):
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "COSMOS_DB_CONNECTION": "#{COSMOS_DB_CONNECTION_STRING}#",
    "FABRIC_EVENTHUB_NAMESPACE": "#{FABRIC_EVENTHUB_NAMESPACE}#",
    "FABRIC_EVENTHUB_NAME": "adieuiq-ingest",
    "AZURE_TENANT_ID": "#{AZURE_TENANT_ID}#",
    "AZURE_CLIENT_ID": "#{MANAGED_IDENTITY_CLIENT_ID}#"
  }
}
```

### Component 2: Fabric Eventstream

**Eventstream Name**: `adieuiq-ingest`  
**Source**: Azure Event Hubs (Azure Function output)  
**Destination**: Fabric Real-Time Intelligence KQL database (`adieuiq-rtdb`)

**Eventstream Configuration**:
1. **Source Settings**:
   - Event Hub namespace: #{FABRIC_EVENTHUB_NAMESPACE}#
   - Event Hub name: `adieuiq-ingest`
   - Consumer group: `$Default`
   - Authentication: Managed Identity

2. **Transformation** (optional):
   - Parse JSON payload
   - Add ingestion timestamp: `ingestion_time = now()`
   - Remove `_ts` field (Cosmos DB internal timestamp)

3. **Destination Settings**:
   - KQL database: `adieuiq-rtdb`
   - Table mapping:
     - Events with `recommendation_id` → `recommendations` table
     - Events with `customer_id` (no recommendation_id) → `customers` table
     - Events with `feature_name` → `usage_data` table
     - Events with `interaction_id` → `interaction_events` table
   - Ingestion batching: 1000 events or 5 seconds (whichever comes first)
   - Error policy: Skip invalid rows, log to diagnostic logs

### Component 3: Fabric Real-Time Intelligence (KQL Tables)

**Table Creation Scripts** (run in KQL database):

```kql
// Create recommendations table
.create table recommendations (
    recommendation_id: string,
    customer_id: string,
    recommendation_type: string,
    recommended_products: dynamic,
    reasoning: string,
    confidence_score: decimal,
    generated_at: datetime,
    delivered_at: datetime,
    outcome_status: string,
    estimated_revenue_impact: decimal,
    ingestion_time: datetime
)

// Create customers table
.create table customers (
    customer_id: string,
    company_name: string,
    industry_segment: string,
    product_tier: string,
    current_products: dynamic,
    contact_email: string,
    account_manager_email: string,
    ingestion_time: datetime
)

// Create usage_data table
.create table usage_data (
    customer_id: string,
    feature_name: string,
    usage_count: long,
    intensity_score: string,
    last_used_at: datetime,
    timestamp: datetime,
    ingestion_time: datetime
)

// Create interaction_events table
.create table interaction_events (
    interaction_id: string,
    customer_id: string,
    event_type: string,
    summary: string,
    sentiment_score: decimal,
    resolution_status: string,
    occurred_at: datetime,
    ingestion_time: datetime
)

// Create indexes for query performance
.alter table customers policy partitioning ```
{
  "PartitionKeys": [
    {
      "ColumnName": "customer_id",
      "Kind": "Hash",
      "Properties": {
        "Function": "XxHash64",
        "MaxPartitionCount": 256
      }
    }
  ]
}
```

.alter table recommendations policy partitioning ```
{
  "PartitionKeys": [
    {
      "ColumnName": "customer_id",
      "Kind": "Hash",
      "Properties": {
        "Function": "XxHash64",
        "MaxPartitionCount": 256
      }
    }
  ]
}
```

// Create update policy for deduplication (last write wins)
.create-or-alter function RecommendationsDedup() {
    recommendations
    | summarize arg_max(ingestion_time, *) by recommendation_id
}

.alter table recommendations policy update 
@'[{"IsEnabled": true, "Source": "recommendations_raw", "Query": "RecommendationsDedup()", "IsTransactional": false}]'
```

## Deployment Steps

### Step 1: Enable Cosmos DB Change Feed

1. Open Azure Portal: https://portal.azure.com
2. Navigate to Cosmos DB account: `adieuiq-cosmos`
3. Go to **Data Explorer** → Select database `adieuiq`
4. For each collection (recommendations, customers, usage_data, interaction_events):
   - Click **Settings** → **Change Feed**
   - Enable: **On**
   - Retention: 24 hours (sufficient for Azure Function processing)
5. Click **Save**

### Step 2: Create Fabric Eventstream

1. Open Fabric portal: https://fabric.microsoft.com
2. Navigate to workspace: #{FABRIC_WORKSPACE_ID}#
3. Click **+ New** → **Eventstream**
4. Name: `adieuiq-ingest`
5. Add source: **Azure Event Hubs**
   - Event Hub namespace: #{FABRIC_EVENTHUB_NAMESPACE}# (create if needed)
   - Event Hub name: `adieuiq-ingest` (create if needed)
   - Consumer group: `$Default`
   - Authentication: **Managed Identity** (grant "Azure Event Hubs Data Receiver" role)
6. Add destination: **KQL Database**
   - Database: `adieuiq-rtdb`
   - Table: `recommendations` (create mapping for each table)
7. Click **Publish**

### Step 3: Deploy Azure Function

1. Open VS Code → Navigate to `dashboard/pipelines/function/`
2. Install Azure Functions extension: `Ctrl+Shift+X` → Search "Azure Functions"
3. Sign in to Azure: `Ctrl+Shift+P` → "Azure: Sign In"
4. Create Function App:
   - `Ctrl+Shift+P` → "Azure Functions: Create Function App in Azure"
   - Name: `adieuiq-cosmos-processor`
   - Runtime: Python 3.11
   - Region: East US (same as Cosmos DB for low latency)
   - Hosting: Consumption Plan
5. Enable Managed Identity:
   - Azure Portal → Function App → **Identity**
   - System-assigned: **On** → Save
   - Note the Object ID for role assignments
6. Deploy function:
   - `Ctrl+Shift+P` → "Azure Functions: Deploy to Function App"
   - Select: `adieuiq-cosmos-processor`
   - Wait for deployment completion
7. Configure app settings:
   - Azure Portal → Function App → **Configuration**
   - Add settings from `local.settings.json` (replace placeholders)
   - **COSMOS_DB_CONNECTION**: Connection string from Cosmos DB (Keys blade)
   - **FABRIC_EVENTHUB_NAMESPACE**: Event Hub namespace name
   - Click **Save** → Restart function app

### Step 4: Grant Permissions

**Managed Identity Permissions**:
1. **Event Hub** (for Azure Function):
   - Azure Portal → Event Hub namespace
   - **Access control (IAM)** → **Add role assignment**
   - Role: `Azure Event Hubs Data Sender`
   - Assign to: Managed Identity → `adieuiq-cosmos-processor`
   
2. **Fabric Workspace** (for Eventstream):
   - Fabric portal → Workspace → **Manage access**
   - Add: Managed Identity → `adieuiq-cosmos-processor`
   - Role: `Contributor`

### Step 5: Validate Pipeline

1. **Trigger test event**:
   - Use backend API to create a test recommendation:
     ```bash
     curl -X POST https://#{BACKEND_API_URL}#/api/customers/test-customer-123/recommendations \
       -H "Authorization: Bearer #{TEST_JWT_TOKEN}#" \
       -H "Content-Type: application/json"
     ```

2. **Monitor Azure Function**:
   - Azure Portal → Function App → **Monitor** → **Logs**
   - Verify log: "Processing 1 recommendation change(s)"
   - Verify log: "Sent 1 events to Fabric Eventstream"

3. **Verify Fabric ingestion**:
   - Fabric portal → KQL database `adieuiq-rtdb`
   - Run query:
     ```kql
     recommendations
     | where ingestion_time > ago(5m)
     | order by ingestion_time desc
     | take 10
     ```
   - Verify test recommendation appears

4. **Check Power BI**:
   - Power BI Service → Open `upsell-pipeline` report
   - Verify new recommendation appears in "Top 10 Upsell Opportunities" table
   - Measure refresh lag: Should be <10 seconds (FR-012)

## Monitoring & Alerting

### Application Insights Integration

**Function App Logging**:
- Automatically enabled (Function App → Application Insights)
- Query:
  ```kusto
  traces
  | where operation_Name startswith "recommendations_change_feed"
  | project timestamp, message, severityLevel
  | order by timestamp desc
  ```

**Fabric Eventstream Monitoring**:
- Fabric portal → Eventstream → **Monitoring**
- Metrics: Ingestion rate, error rate, latency
- Alert on: Error rate >1%, Latency >10 seconds

### Alerts Configuration

**Alert 1: High Change Feed Lag**
- Resource: Azure Function
- Metric: `CosmosDB-ChangeFeedProcessorLag`
- Condition: >100 events for 5 minutes
- Action: Email IT Admin, create ServiceNow incident

**Alert 2: Fabric Ingestion Failures**
- Resource: Fabric Eventstream
- Metric: `FailedEvents`
- Condition: >10 failures in 5 minutes
- Action: Email Data Engineering team

## Performance Optimization

1. **Batching**: Azure Function processes up to 100 documents per invocation
2. **Parallelism**: Change feed lease collection enables multiple function instances
3. **Indexing**: Fabric KQL tables partitioned by `customer_id` for fast lookups
4. **Deduplication**: Update policy in Fabric removes duplicate events (last write wins)
5. **Connection Pooling**: Event Hub producer client reused across invocations

**Expected Latency**:
- Cosmos DB write → Change Feed: <1 second
- Change Feed → Azure Function: <2 seconds
- Azure Function → Event Hub: <1 second
- Event Hub → Fabric KQL: <5 seconds
- **Total**: <10 seconds (meets FR-012)

## Troubleshooting

### Issue: High change feed lag (>100 events)

**Cause**: Function App throttled by Consumption Plan limits  
**Resolution**: Upgrade to Premium Plan (dedicated instances) or increase `maxItemsPerInvocation` in host.json

### Issue: Events not appearing in Fabric

**Cause**: Event Hub authentication failure  
**Resolution**: Verify Managed Identity has "Azure Event Hubs Data Sender" role on Event Hub namespace

### Issue: Duplicate recommendations in Power BI

**Cause**: Deduplication policy not applied  
**Resolution**: Run KQL update policy creation script (see Component 3 above)

## Future Enhancements

1. **Dead Letter Queue**: Route failed events to Azure Storage for manual reprocessing
2. **Schema Validation**: Add JSON schema validation in Azure Function before sending to Event Hub
3. **Data Quality Metrics**: Track null fields, outliers in Fabric KQL (e.g., confidence_score >1.0)
4. **Historical Backfill**: One-time pipeline to backfill existing Cosmos DB data into Fabric (Azure Data Factory)
