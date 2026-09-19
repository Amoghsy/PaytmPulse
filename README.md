# Paytm Pulse — Phase 1: Project Foundation

> **Real-Time AI Business Partner for Every Merchant**

Paytm Pulse is an AI-powered intelligence and action engine built for merchants. System vision architecture: **UNDERSTAND → DETECT → PREDICT → ACT → MEASURE**.

---

## 1. System Architecture

Phase 1 establishes the core infrastructure and service communication stack:

```text
React (Vite Dashboard)
   │
   ▼
FastAPI Backend
   │
   ├── PostgreSQL (Database)
   │
   └── Redis (Caching & Real-Time State)

n8n Workflow Engine (Event Orchestration)
```

---

## 2. Prerequisites

Ensure you have the following installed on your local machine:

* **Docker & Docker Compose** (Docker Desktop recommended)
* **Python** 3.11 or higher
* **Node.js** 18 or higher (npm v9+)
* **Git**

---

## 3. Project Structure

```text
paytm-pulse/
│
├── backend/                  # FastAPI Application
│   ├── app/
│   │   ├── api/             # API Routers & Health Endpoints
│   │   ├── database/        # PostgreSQL SQLAlchemy connection & sessions
│   │   ├── services/        # Redis service & ping client
│   │   ├── models/          # Database ORM models (Placeholder for Phase 2+)
│   │   ├── schemas/         # Pydantic Schemas (Placeholder for Phase 2+)
│   │   ├── __init__.py
│   │   └── main.py          # FastAPI app entrypoint, CORS, Logging
│   ├── requirements.txt     # Python Dependencies
│   └── Dockerfile           # Backend Container Definition
│
├── frontend/                 # React + Vite Application
│   ├── src/
│   │   ├── services/
│   │   │   └── api.js       # Backend API client using VITE_API_BASE_URL
│   │   ├── App.jsx          # System Status Dashboard Component
│   │   ├── App.css          # Styled UI Components
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile           # Frontend Container Definition
│
├── n8n/                      # n8n Workflow Data Directory (Persisted)
│   └── .gitkeep
│
├── docker-compose.yml        # Full Stack Docker Compose Orchestration
├── .env.example              # Environment Variable Template
├── .gitignore                # Git Ignore Rules
├── README.md                 # Project Documentation
└── LICENSE                   # MIT License
```

---

## 4. Service URLs

Once the stack is running, access services at the following local URLs:

| Service | URL | Description |
| :--- | :--- | :--- |
| **React Frontend** | `http://localhost:5173` | Status Dashboard UI |
| **FastAPI Backend** | `http://localhost:8000` | Backend Base API |
| **Swagger API Docs** | `http://localhost:8000/docs` | Interactive OpenAPI Documentation |
| **ReDoc API Docs** | `http://localhost:8000/redoc` | Alternative API Documentation |
| **n8n Engine** | `http://localhost:5678` | Workflow & Webhook Automation Interface |
| **PostgreSQL** | `localhost:5432` | Database Service (`paytm_pulse`) |
| **Redis** | `localhost:6379` | In-Memory Cache Service |

---

## 5. Running the Project

### Option A: Using Docker Compose (Recommended)

Start all services (PostgreSQL, Redis, n8n, Backend, Frontend) in detached mode:

```bash
docker compose up -d
```

Check running container logs:

```bash
docker compose logs -f
```

Stop all services:

```bash
docker compose down
```

---

### Option B: Running Locally (Development Mode)

#### Step 1: Start Databases & n8n via Docker

```bash
docker compose up -d postgres redis n8n
```

#### Step 2: Start FastAPI Backend

```bash
cd backend

# Create & activate Python virtual environment
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run FastAPI with live reload
uvicorn app.main:app --reload --port 8000
```

#### Step 3: Start React Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```

---

## 6. Health & Verification Endpoints

Verify backend connectivity using `curl` or opening in browser:

* **Root Status Endpoint**
  ```bash
  curl http://localhost:8000/
  ```
  Expected Response:
  ```json
  {
    "application": "Paytm Pulse",
    "message": "Real-Time AI Business Partner for Every Merchant",
    "status": "running"
  }
  ```

* **General Health Endpoint**
  ```bash
  curl http://localhost:8000/health
  ```
  Expected Response:
  ```json
  {
    "status": "healthy"
  }
  ```

* **PostgreSQL Health Endpoint** (Executes `SELECT 1`)
  ```bash
  curl http://localhost:8000/health/database
  ```
  Expected Response:
  ```json
  {
    "service": "postgresql",
    "status": "healthy"
  }
  ```

* **Redis Health Endpoint** (Executes Redis `PING`)
  ```bash
  curl http://localhost:8000/health/redis
  ```
  Expected Response:
  ```json
  {
    "service": "redis",
    "status": "healthy"
  }
  ```

---

## 7. Phase 5: Google ADK + Gemini Business Intelligence Agent

Paytm Pulse incorporates an intelligent AI business reasoning agent powered by **Google ADK & Gemini** to diagnose merchant trends, investigate anomalies, and produce structured, non-executing business recommendations.

```text
Live Transaction (Phase 3 Event)
               │
               ▼
   Phase 4 ML Intelligence Tools
  ┌───────────────────────────────┐
  │ • Sales Analyzer              │
  │ • Anomaly Detector            │
  │ • Demand Forecaster (Ridge)   │
  │ • Stockout Predictor          │
  │ • Customer RFM Segmentation   │
  │ • Opportunity Scanner         │
  └──────────────┬────────────────┘
                 │ (Controlled Structured Outputs)
                 ▼
    Google Gemini Reasoning Agent
     (Prompt & Context Injection)
                 │
                 ▼
  Structured Business Recommendation
        (AgentAnalysis Schema)
                 │
                 ▼
    [Phase 6 Action Engine]
```

### Controlled Agent Tools

The agent interacts exclusively with controlled, deterministic Python tools rather than querying raw database tables directly:

| Tool | Purpose | Source |
| :--- | :--- | :--- |
| `get_sales_analysis(merchant_id)` | Multi-horizon sales, growth %, AOV, top/slow products | Phase 4 Sales Analyzer |
| `detect_anomalies(merchant_id, product_id)` | IsolationForest anomaly detection & baseline checks | Phase 4 Anomaly Detector |
| `forecast_demand(merchant_id, product_id, horizon)` | Next 1h/6h/24h demand predictions | Phase 4 Ridge Regression |
| `predict_stockout(merchant_id, product_id)` | Real-time stock runway and stockout hazard | Phase 4 Stockout Predictor |
| `get_all_stockout_risks(merchant_id)` | Catalog-wide urgent restocking rankings | Phase 4 Stockout Predictor |
| `get_customer_intelligence(merchant_id)` | RFM clusters, churn risk, high-value customer lists | Phase 4 Customer RFM |
| `detect_opportunities(merchant_id)` | RESTOCK, DEMAND_GROWTH, WINBACK, CROSS_SELL | Phase 4 Opportunity Detector |
| `get_business_event(event_id)` | Phase 3 real-time trigger payload & severity | Phase 3 Event Table |

---

### Agent API Endpoints

#### 1. Real-Time Business Event Analysis
```http
POST /api/v1/agent/analyze-event
Content-Type: application/json

{
  "event_id": "ev_demand_spike_001"
}
```
**Response (`AgentAnalysis`):**
```json
{
  "event_id": "ev_demand_spike_001",
  "merchant_id": "m_agent_001",
  "summary": "Cold Drinks 750ml demand is significantly above its normal baseline level.",
  "detected_issue": "Demand surge and potential inventory shortage for Cold Drinks 750ml",
  "evidence": [
    "Observed recent demand (8.0) is 60.0% above baseline (5.0)",
    "Forecast demand is 12.0 units over horizon next_hour",
    "Current stock is 18 units with estimated runway of 2.4 hours"
  ],
  "impact": {
    "type": "POTENTIAL_REVENUE_LOSS",
    "estimated_value": 1350.0,
    "currency": "INR"
  },
  "urgency": "HIGH",
  "confidence": 0.88,
  "recommendation": "Consider restocking Cold Drinks 750ml before current inventory runs out to capture ongoing surge.",
  "supporting_data": { ... },
  "suggested_action_type": "RESTOCK"
}
```

#### 2. Merchant General Health Diagnosis
```http
POST /api/v1/agent/analyze-merchant
Content-Type: application/json

{
  "merchant_id": "m_agent_001"
}
```

#### 3. Conversational Merchant Chat
```http
POST /api/v1/agent/chat
Content-Type: application/json

{
  "merchant_id": "m_agent_001",
  "message": "Which products may run out soon?"
}
```
**Response (`ChatResponse`):**
```json
{
  "merchant_id": "m_agent_001",
  "response": "Attention needed: 'Cold Drinks 750ml' has only 18 units remaining. At current demand velocity, it is projected to run out in approximately 2.4 hours.",
  "supporting_data": {
    "at_risk_products": [ ... ]
  },
  "suggested_action": "RESTOCK"
}
```

---

## 8. Phase 6: Next Best Action & Decision Engine

The **Next Best Action (NBA) & Decision Engine** takes the business intelligence and AI reasoning and converts them into **concrete, prioritized, merchant-approvable actions** with machine-readable parameters and estimated financial impact.

```text
               TRANSACTION (Phase 3)
                        ↓
             ML INTELLIGENCE (Phase 4)
                        ↓
            AI REASONING AGENT (Phase 5)
                        ↓
             DECISION ENGINE (Phase 6)
  ┌───────────────────────────────────────────┐
  │ 1. Candidate Action Generation            │
  │ 2. Machine-Readable Parameter Computation │
  │ 3. Impact Estimation (Protected / Incr.)  │
  │ 4. Constraint Validation & Conflict Rules │
  │ 5. Composite Scoring & Prioritization     │
  │ 6. Deduplication & DB Persistence         │
  └─────────────────────┬─────────────────────┘
                        ↓
             NEXT BEST ACTION (NBA)
               (Status: PENDING)
                        ↓
         MERCHANT REVIEW & APPROVAL
         (Approve / Reject via Dashboard)
                        ↓
          [Phase 8 Action Execution]
```

### Supported Action Types

| Action Type | Category | Primary Trigger | Target Outcome |
| :--- | :--- | :--- | :--- |
| `RESTOCK_PRODUCT` | Inventory | `DEMAND_SPIKE`, `STOCKOUT_RISK` | Protect sales from inventory depletion |
| `RUN_PROMOTION` | Sales | `SALES_DECLINE`, `DEMAND_SPIKE` | Stimulate store footfall & volume |
| `CUSTOMER_WINBACK` | Customer | `CUSTOMER_RISK`, `INACTIVITY` | Recover at-risk regular customer revenue |
| `CREATE_BUNDLE` | Growth | `CROSS_SELL`, `OPPORTUNITY` | Expand basket size with product pairs |
| `MONITOR_TREND` | Operational | Steady state / baseline signals | Continuous tracking with low friction |
| `FINANCIAL_PRODUCT` | Advisory | Capital / margin recommendations | Working capital advisory (Non-executing) |

---

### Decision Engine API Endpoints

#### 1. Generate Next Best Action
```http
POST /api/v1/decisions/generate
Content-Type: application/json

{
  "merchant_id": "m_agent_001",
  "event_id": "ev_demand_spike_001"
}
```
**Response (`DecisionResponse`):**
```json
{
  "merchant_id": "m_agent_001",
  "event_id": "ev_demand_spike_001",
  "next_best_action": {
    "id": "rec_001",
    "merchant_id": "m_agent_001",
    "event_id": "ev_demand_spike_001",
    "action_type": "RESTOCK_PRODUCT",
    "title": "Restock Cold Drink 750ml",
    "description": "Order 76 units of Cold Drink 750ml to fulfill surging customer demand.",
    "reason": "Demand is surging and existing inventory of 8 units may deplete within ~2-3 hours.",
    "priority": "HIGH",
    "urgency": "HIGH",
    "confidence": 0.91,
    "estimated_impact": {
      "type": "REVENUE_PROTECTED",
      "value": 1350.0,
      "currency": "INR"
    },
    "parameters": {
      "product_id": "p_cold_drinks",
      "quantity": 76,
      "supplier": "Delhi Beverage Co"
    },
    "requires_approval": true,
    "status": "PENDING_APPROVAL"
  },
  "alternative_actions": [ ... ],
  "total_candidates": 3,
  "created_at": "2026-09-18T00:15:00Z"
}
```

#### 2. List Pending Actions Awaiting Merchant Approval
```http
GET /api/v1/decisions/{merchant_id}/pending
```

#### 3. Approve Action
```http
POST /api/v1/decisions/{decision_id}/approve
```
*Transitions status: `PENDING` ➔ `APPROVED` (sets `approved_at` timestamp without premature external execution).*

#### 4. Reject Action
```http
POST /api/v1/decisions/{decision_id}/reject
```
*Transitions status: `PENDING` ➔ `REJECTED`.*

---

## 9. Configuration & Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `GOOGLE_API_KEY` | *(empty)* | Google AI Studio Gemini API Key |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model name |
| `REDIS_HOST` | `localhost` | Redis caching server hostname |
| `REDIS_PORT` | `6379` | Redis caching server port |
| `DATABASE_URL` | *(postgres)* | SQLAlchemy PostgreSQL database connection string |

---

## 10. Next Phase Roadmap

* **Phase 7**: Multichannel Merchant Communication (WhatsApp Interactive Flows / Sarvam AI Multilingual Voice)
* **Phase 8**: Closed-Loop Action Execution, Supplier Webhooks & ROI Outcome Tracking
