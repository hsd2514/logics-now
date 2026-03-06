# FreightIQ - AI Document Intelligence

**AI-powered LR-POD-Invoice Matching System for Logistics**

Team: Up Up & Debug | LogisticsNow LoRRI AI Hackathon 2026

## Overview

FreightIQ is an intelligent document processing system that automates the matching of Lorry Receipts (LR), Proof of Delivery (POD), and Invoices in logistics operations. It uses a 6-stage AI pipeline with 5 novel features that differentiate it from traditional solutions.

## Key Features

### 6-Stage AI Pipeline
1. **Preprocessing** - Image enhancement, deskew, denoise
2. **OCR** - Text extraction with spatial coordinates
3. **NER** - Entity extraction (Shipment ID, Amount, Date, etc.)
4. **Matching** - Triplet matching with confidence scoring
5. **Validation** - Rule-based validation
6. **Fraud Detection** - Anomaly detection

### 5 Novel Features
1. **Explainable AI Heatmaps** - Visual overlay showing WHY documents matched
2. **Natural Language Query** - Ask "Show invoices above 50k from last week"
3. **AI Audit Trail** - Auto-generated compliance explanations
4. **Predictive Alerts** - Detect fraud BEFORE it happens
5. **Document Chat** - Ask questions about any document

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React + shadcn/ui + Tailwind CSS |
| Backend | FastAPI (Python) |
| Database | SQLite + SQLAlchemy (PostgreSQL ready) |
| AI/LLM | OpenAI + Vercel AI SDK |
| OCR | Tesseract |
| ML | scikit-learn |

## Project Structure

```
freightiq/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI entry
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── routes/           # API endpoints
│   │   ├── pipeline/         # 6-stage pipeline
│   │   ├── ai/               # AI features
│   │   └── services/         # Business logic
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── hooks/            # Custom hooks
│   │   └── services/         # API client
│   └── package.json
├── sample_data/
│   └── generator.py          # Document generator
└── README.md
```

## Quick Start

### Backend

```bash
cd backend

# Install dependencies with uv
uv sync

# Set environment variables
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# Run server
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### Generate Sample Data

```bash
cd sample_data
python generator.py
```

## API Endpoints

### Documents
- `POST /api/documents/upload` - Upload document
- `GET /api/documents` - List documents
- `GET /api/documents/{id}` - Get document

### Triplets
- `POST /api/triplets/match` - Run matching
- `GET /api/triplets` - List triplets
- `POST /api/triplets/{id}/approve` - Approve
- `POST /api/triplets/{id}/reject` - Reject

### Fraud
- `GET /api/fraud/alerts` - List alerts
- `GET /api/fraud/predictions` - Predictive alerts

### AI (Novel Features)
- `POST /api/ai/chat` - Document chat (streaming)
- `POST /api/ai/query` - Natural language query
- `GET /api/ai/audit/{triplet_id}` - AI audit trail

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │ Upload  │ │Dashboard│ │  Fraud  │ │  Chat   │       │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘       │
└───────┼───────────┼───────────┼───────────┼────────────┘
        │           │           │           │
        ▼           ▼           ▼           ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │              6-Stage Pipeline                    │   │
│  │  Preprocess → OCR → NER → Match → Validate → FD │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │              AI Features                         │   │
│  │  Chat │ NL Query │ Audit Trail │ Predictive     │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│                   SQLite Database                        │
│  Documents │ Triplets │ FraudAlerts │ VendorProfiles    │
└─────────────────────────────────────────────────────────┘
```

## Confidence Score Formula

```
C = 0.35 × MatchScore + 0.20 × OCRacc + 0.25 × NERconf + 0.20 × RulePass
```

## Success Metrics

| Metric | Target |
|--------|--------|
| OCR accuracy (typed) | >95% |
| Entity extraction F1 | >0.90 |
| Triplet matching | >90% |
| Fraud detection precision | >85% |
| Processing time/triplet | <30s |

## PostgreSQL Migration

Change one line in `backend/app/database.py`:

```python
# From SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./freightiq.db"

# To PostgreSQL
SQLALCHEMY_DATABASE_URL = "postgresql://user:pass@host/freightiq"
```

## License

MIT License - Team Up Up & Debug

## Demo

[Video link to be added]
