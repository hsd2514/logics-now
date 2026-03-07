---
name: FreightIQ Full Build
overview: "Build FreightIQ - a complete AI Document Intelligence prototype for LR-POD-Invoice matching. FastAPI backend with SQLite/SQLAlchemy, React (JS) frontend with shadcn/ui + Tailwind, Vercel AI SDK integration. Features 6-stage AI pipeline and 5 novel differentiators: Explainable AI heatmaps, Natural Language Query, AI Audit Trail, Predictive Alerts, and Document Chat."
todos: []
isProject: false
---

# FreightIQ - AI Document Intelligence (Full Build Plan)

## Tech Stack


| Layer    | Technology                                  |
| -------- | ------------------------------------------- |
| Frontend | React (JS) + shadcn/ui + Tailwind CSS       |
| Backend  | FastAPI (Python)                            |
| Database | SQLite + SQLAlchemy (PostgreSQL ready)      |
| AI/LLM   | Vercel AI SDK (frontend) + OpenAI (backend) |
| OCR      | Tesseract + pytesseract                     |
| ML       | scikit-learn for anomaly detection          |
| Realtime | FastAPI WebSocket                           |


## Architecture

```mermaid
flowchart TB
    subgraph frontend [React + shadcn/ui]
        Upload[Document Upload]
        Dashboard[Matching Dashboard]
        FraudPanel[Fraud Alerts]
        ReviewQueue[Review Queue]
        DocChat[Document Chat AI]
        NLQuery[Natural Language Query]
        Heatmap[Explainability Heatmaps]
    end
    
    subgraph backend [FastAPI Backend]
        API[REST API]
        AIRoutes[AI Streaming Routes]
        Pipeline[6-Stage Pipeline]
        WS[WebSocket Handler]
    end
    
    subgraph ml [ML/AI Layer]
        OCR[Tesseract OCR]
        NER[Entity Extraction]
        Match[Triplet Matcher]
        Fraud[Anomaly Detector]
        LLM[OpenAI LLM]
    end
    
    subgraph data [Data Layer]
        SQLite[(SQLite)]
        FileStore[(File Storage)]
    end
    
    frontend --> API
    frontend --> AIRoutes
    API --> Pipeline
    Pipeline --> ml
    Pipeline --> SQLite
    WS --> frontend
```



## 5 Novel Features (Key Differentiators)

### 1. Explainable AI - Attention Heatmaps

Visual overlay on documents showing WHY they matched. Green regions = high match, Yellow = partial, Red = mismatch. Stores attention weights in `attention_map` JSON field.

### 2. Natural Language Query

Finance teams ask: "Show invoices from ABC Transport above 50k last week" - AI converts to database filters. Uses OpenAI to parse intent and generate query parameters.

### 3. AI-Generated Audit Trail

Every match decision gets auto-generated compliance explanation stored in `ai_explanation` field. Example: "LR #123 matched with POD #123 and Invoice #123. Shipment ID exact match. Amount variance 0.3% within 2% tolerance."

### 4. Predictive Alerts

Learn vendor behavior patterns (avg amount, frequency, routes). Alert when new invoice deviates significantly - catches fraud BEFORE it happens. Stores patterns in `VendorProfile` model.

### 5. Document Chat

Ask questions about any uploaded document using conversational AI with streaming responses. "What is the total amount?" "Is delivery date before invoice date?"

## Project Structure

```
freightiq/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── config.py               # Environment settings
│   │   ├── database.py             # SQLAlchemy setup
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── document.py         # Document model
│   │   │   ├── triplet.py          # Triplet model
│   │   │   ├── fraud_alert.py      # FraudAlert model
│   │   │   ├── vendor_profile.py   # VendorProfile model
│   │   │   └── audit_log.py        # AuditLog model
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── document.py         # Pydantic schemas
│   │   │   ├── triplet.py
│   │   │   └── fraud.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── documents.py        # Upload, CRUD
│   │   │   ├── triplets.py         # Matching results
│   │   │   ├── review.py           # Human review queue
│   │   │   ├── fraud.py            # Fraud alerts
│   │   │   ├── ai.py               # AI streaming (chat, query)
│   │   │   └── stats.py            # Dashboard stats
│   │   ├── pipeline/
│   │   │   ├── __init__.py
│   │   │   ├── preprocessor.py     # Stage 1: Image enhancement
│   │   │   ├── ocr_engine.py       # Stage 2: Tesseract OCR
│   │   │   ├── entity_extractor.py # Stage 3: NER extraction
│   │   │   ├── triplet_matcher.py  # Stage 4: Matching logic
│   │   │   ├── validator.py        # Stage 5: Rule validation
│   │   │   └── fraud_detector.py   # Stage 6: Anomaly detection
│   │   ├── ai/
│   │   │   ├── __init__.py
│   │   │   ├── embeddings.py       # Document embeddings
│   │   │   ├── nl_query.py         # NL to filter conversion
│   │   │   ├── audit_generator.py  # AI audit trail generation
│   │   │   ├── doc_chat.py         # Document Q&A
│   │   │   └── vendor_patterns.py  # Predictive pattern learning
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── document_service.py
│   │   │   ├── matching_service.py
│   │   │   └── websocket_manager.py
│   │   └── utils/
│   │       └── helpers.py
│   ├── uploads/                    # Uploaded document files
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Main app component
│   │   ├── main.jsx                # Entry point
│   │   ├── index.css               # Tailwind imports
│   │   ├── lib/
│   │   │   └── utils.js            # cn() helper for shadcn
│   │   ├── components/
│   │   │   ├── ui/                 # shadcn components
│   │   │   │   ├── button.jsx
│   │   │   │   ├── card.jsx
│   │   │   │   ├── input.jsx
│   │   │   │   ├── badge.jsx
│   │   │   │   ├── dialog.jsx
│   │   │   │   ├── table.jsx
│   │   │   │   ├── tabs.jsx
│   │   │   │   ├── progress.jsx
│   │   │   │   ├── alert.jsx
│   │   │   │   └── scroll-area.jsx
│   │   │   ├── DocumentUpload.jsx
│   │   │   ├── MatchingDashboard.jsx
│   │   │   ├── TripletCard.jsx
│   │   │   ├── FraudAlertPanel.jsx
│   │   │   ├── ReviewQueue.jsx
│   │   │   ├── AttentionHeatmap.jsx    # Novel feature
│   │   │   ├── NLQueryBar.jsx          # Novel feature
│   │   │   ├── AuditTrail.jsx          # Novel feature
│   │   │   ├── PredictiveAlerts.jsx    # Novel feature
│   │   │   ├── DocumentChat.jsx        # Novel feature
│   │   │   └── StatsCards.jsx
│   │   ├── hooks/
│   │   │   ├── useWebSocket.js
│   │   │   ├── useDocuments.js
│   │   │   └── useTriplets.js
│   │   └── services/
│   │       └── api.js              # Axios API client
│   ├── components.json             # shadcn config
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
├── sample_data/
│   ├── generator.py                # Synthetic document generator
│   └── templates/
│       ├── lr_template.html
│       ├── pod_template.html
│       └── invoice_template.html
├── docker-compose.yml
└── README.md
```

## Database Models (SQLAlchemy)

### Document

- id, type (LR/POD/INVOICE), file_name, file_path
- uploaded_at, ocr_text, entities (JSON), embedding (JSON)
- confidence, status

### Triplet

- id, lr_id, pod_id, invoice_id
- match_score, confidence, status
- ai_explanation (Novel: AI audit)
- attention_map (Novel: Heatmap data)
- created_at, reviewed_at, reviewed_by

### FraudAlert

- id, triplet_id, risk_score
- alert_type (DUPLICATE, AMOUNT_ANOMALY, PREDICTED)
- details (JSON), status, created_at

### VendorProfile

- id, vendor_name, avg_amount, std_deviation
- avg_frequency, route_patterns (JSON)
- risk_score, last_updated

### AuditLog

- id, triplet_id, action
- ai_generated (Novel: AI explanation)
- user_id, timestamp

## API Endpoints

### Documents

- `POST /api/documents/upload` - Upload single document
- `POST /api/documents/batch` - Batch upload
- `GET /api/documents` - List all documents
- `GET /api/documents/{id}` - Get document with entities

### Triplets

- `GET /api/triplets` - List matched triplets
- `GET /api/triplets/{id}` - Get triplet with attention map
- `POST /api/triplets/{id}/approve` - Human approve
- `POST /api/triplets/{id}/reject` - Human reject

### Fraud

- `GET /api/fraud/alerts` - All fraud alerts
- `GET /api/fraud/predictions` - Predictive alerts (Novel)
- `POST /api/fraud/alerts/{id}/dismiss` - Dismiss alert

### AI (Streaming SSE)

- `POST /api/ai/chat` - Document chat (Novel)
- `POST /api/ai/query` - NL query to filters (Novel)
- `GET /api/ai/audit/{triplet_id}` - Generate audit trail (Novel)

### Realtime

- `WS /ws/processing` - Real-time processing updates

### Stats

- `GET /api/stats` - Dashboard metrics

## 6-Stage Pipeline Implementation

### Stage 1: Preprocessor (`preprocessor.py`)

- Load image, grayscale conversion
- Adaptive thresholding (CLAHE)
- Deskew using Hough transform
- Denoise with fastNlMeansDenoising
- Return enhanced image + quality score

### Stage 2: OCR Engine (`ocr_engine.py`)

- Use pytesseract.image_to_data()
- Extract text with x, y, width, height coordinates
- Calculate confidence scores per text block
- Return structured TextBlock objects

### Stage 3: Entity Extractor (`entity_extractor.py`)

- Extract: SHIPMENT_ID, AMOUNT, DATE, PARTY_NAME, ADDRESS, VEHICLE_NO
- Use regex patterns + positional context
- Return entities with confidence scores

### Stage 4: Triplet Matcher (`triplet_matcher.py`)

- Compute document embeddings from entities
- Match LR-POD-Invoice by similarity + field matching
- Calculate attention weights for explainability
- Return match score and confidence

### Stage 5: Validator (`validator.py`)

- Amount tolerance: abs(Invoice - LR) less than 2%
- Date sequence: LR_date <= POD_date <= Invoice_date
- ID exact match validation
- Party name fuzzy match (greater than 85% similarity)

### Stage 6: Fraud Detector (`fraud_detector.py`)

- Isolation Forest on [amount, frequency, route_deviation]
- Check for duplicates (same invoice number)
- Compare against vendor profile for anomalies
- Return fraud_risk score and alert_type

## Confidence Score Formula

```
C = 0.35 * MatchScore + 0.20 * OCRacc + 0.25 * NERconf + 0.20 * RulePass
```

## Key Dependencies

### Backend (requirements.txt)

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
aiosqlite==0.19.0
python-multipart==0.0.6
pytesseract==0.3.10
opencv-python==4.9.0.80
pillow==10.2.0
numpy==1.26.3
scikit-learn==1.4.0
openai==1.10.0
python-dotenv==1.0.0
websockets==12.0
pydantic==2.5.3
pydantic-settings==2.1.0
jinja2==3.1.3
weasyprint==60.2
```

### Frontend (package.json)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "ai": "^3.0.0",
    "lucide-react": "^0.312.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0",
    "class-variance-authority": "^0.7.0",
    "react-dropzone": "^14.2.3",
    "axios": "^1.6.5"
  }
}
```

## PostgreSQL Migration

Change one line in `backend/app/database.py`:

```python
# SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./freightiq.db"
# PostgreSQL
SQLALCHEMY_DATABASE_URL = "postgresql://user:pass@host/freightiq"
```

## Implementation Phases (24hr)

### Phase 1: Setup (0-3 hrs)

- FastAPI project structure with all folders
- React + Vite + Tailwind + shadcn/ui setup
- SQLAlchemy models and database init
- Basic health check endpoints

### Phase 2: Core Pipeline (3-10 hrs)

- Document upload with file storage
- Image preprocessing with OpenCV
- OCR extraction with pytesseract
- Entity extraction with regex patterns
- Triplet matching with scoring
- Rule validation engine
- Basic anomaly detection

### Phase 3: AI Features (10-16 hrs)

- OpenAI integration
- Document Chat with SSE streaming
- NL Query to filter conversion
- AI Audit Trail generation
- Attention weights for heatmaps
- Vendor pattern learning

### Phase 4: Frontend (16-21 hrs)

- Dashboard layout with shadcn
- Document upload with dropzone
- Triplet cards with confidence bars
- Fraud alert panel
- Review queue with actions
- Attention heatmap overlay
- NL Query bar
- Document chat sidebar
- WebSocket real-time updates

### Phase 5: Demo (21-24 hrs)

- Generate 50+ sample triplets
- Include 5 fraud test cases
- Test full pipeline
- Create README with diagrams

## Success Criteria


| Metric                    | Target  |
| ------------------------- | ------- |
| OCR accuracy (typed)      | >95%    |
| Entity extraction F1      | >0.90   |
| Triplet matching          | >90%    |
| Fraud detection precision | >85%    |
| Processing time/triplet   | <30s    |
| All 5 novel features      | Working |


