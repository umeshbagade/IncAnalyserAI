# IncAnalyserAI

**AI-powered Production Incident Root Cause Analysis Platform**

A full-stack application for analysing production incidents with a multi-stage investigation pipeline: **Saturn → DataHub → Ingestion**.

![Dashboard Preview](https://img.shields.io/badge/Status-Active-success)
![Next.js](https://img.shields.io/badge/Next.js-15-black)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue)

---

## 📋 Prerequisites

- **Node.js** v18+ (recommended: v22.17.1)
- **Python** 3.10+
- **npm** or **yarn**

---

## 🚀 Setup Instructions (Fresh Clone)

Follow these steps to set up the project on a new machine after cloning:

### 1. Clone the Repository

```bash
git clone <repo-url>
cd IncAnalyserAI
```

### 2. Backend Setup (FastAPI)

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate   # On macOS/Linux
# OR
venv\Scripts\activate      # On Windows

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup (Next.js)

```bash
cd frontend

# Install Node.js dependencies
npm install
```

### 4. Run the Application

You need **two terminal windows** running simultaneously.

#### Terminal 1 — Start Backend Server

```bash
cd backend
source venv/bin/activate   # macOS/Linux
# OR venv\Scripts\activate  # Windows
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend is now running at **http://localhost:8000**

- API Docs (Swagger): http://localhost:8000/docs
- Health Check: http://localhost:8000/health

#### Terminal 2 — Start Frontend Server

```bash
cd frontend
npm run dev
```

The frontend is now running at **http://localhost:3000**

---

## 🎯 Usage

### Landing Page
Open **http://localhost:3000** — Browse all incidents, search by ID, or click "New Investigation".

### Investigation Dashboard
Navigate to an incident (e.g. **http://localhost:3000/inc/INC-2026-07-20-001**) to see:

| Panel | Content |
|-------|---------|
| **Header** | INC ID, Flow name, Severity badge, Elapsed timer, Escalate/Settings |
| **Left (30%)** | Original incident text, Triage summary, Extracted entities, Timeline of events |
| **Bottom-Left** | Root Cause Analysis (RCA) with confidence bar, Causal chain, Best-Next-Action buttons |
| **Center (45%)** | Flow DAG (Saturn → DataHub → Ingestion) — click nodes to see evidence + live SSE event stream |
| **Right (25%)** | Context-sensitive Evidence & Citations per selected step — tool calls, runbook links, similar past incidents, feedback |

### Analysis Flow Order
1. **Saturn** — Report-level checks (dashboards, counts, aggregations)
2. **DataHub** — Data layer inspection (Oracle, Hive, data dumps)
3. **Ingestion** — Pipeline ingestion checks (feeds, loaders, transforms)

---

## 📁 Project Structure

```
IncAnalyserAI/
├── backend/                      # FastAPI Backend
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py               # All REST APIs + SSE streaming
│   ├── requirements.txt          # Python dependencies
│   └── venv/                     # Python virtual environment (gitignored)
├── frontend/                     # Next.js 15 Frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── globals.css       # Dark theme + custom utilities
│   │   │   ├── layout.tsx        # Root layout
│   │   │   ├── page.tsx          # Landing page (incident list)
│   │   │   └── inc/[id]/page.tsx # Incident detail + analysis dashboard
│   │   ├── components/
│   │   │   ├── Header.tsx        # Top bar
│   │   │   ├── IncidentPanel.tsx # Left panel
│   │   │   ├── RCAPanel.tsx      # Bottom-left panel
│   │   │   ├── FlowDAG.tsx       # Center DAG visualization
│   │   │   ├── LiveEventStream.tsx # SSE event stream
│   │   │   └── EvidencePanel.tsx # Right panel
│   │   └── lib/api.ts            # API client (proxies to backend via Next.js rewrites)
│   │   └── types.ts              # TypeScript interfaces
│   ├── package.json
│   ├── tsconfig.json
│   └── tailwind.config.js
└── .gitignore
```

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Service info |
| `GET` | `/health` | Health check |
| `GET` | `/incidents` | List all incidents |
| `POST` | `/incidents` | Start investigation → returns `run_id` |
| `GET` | `/incidents/{run_id}` | Get investigation state |
| `GET` | `/incidents/{run_id}/stream` | SSE event stream (2s per step) |
| `POST` | `/incidents/{run_id}/feedback` | Mark step useful/wrong |
| `POST` | `/incidents/{run_id}/approve` | Approve remediation |
| `GET` | `/knowledge/flows/{id}` | Flow DAG definitions |

---

## 🛠 Tech Stack

- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS, Lucide Icons
- **Backend**: FastAPI, Python 3.10+, Uvicorn, SSE streaming
- **Design**: Dark theme, Responsive layout, Real-time event streaming

---

## 📄 License

N A

