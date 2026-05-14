# Market Rent Engine

Transparent industrial market rent estimation engine built for the Reml Insights engineering case study.

Spent 55 minutes. Most time went into ingest logic, auditability, and debugging local environment setup.

The system ingests noisy industrial lease comparable data, cleans and normalizes the dataset, applies deterministic market adjustments, and produces an auditable rent estimate with confidence scoring and a transparent waterfall.

---

# Features

- Lease comp ingestion and normalization
- Monthly-to-annual rent normalization
- Duplicate comp detection and deduplication
- Off-market comp filtering
- Confidence scoring for each comp
- Transparent adjustment waterfall
- FastAPI estimation endpoint
- Streamlit frontend UI
- Used vs dropped comparable audit trail
- Basic automated tests

---

# Architecture

## Backend

### `ingest.py`

Responsible for:
- loading lease comps
- cleaning malformed records
- normalizing monthly rents
- dropping unusable comps
- deduplicating transactions
- assigning confidence scores

### `estimate.py`

Implements:
- time adjustment
- vintage adjustment
- size adjustment
- clear height adjustment
- weighted blending
- confidence-weighted market rent estimate
- audit waterfall generation

### `main.py`

FastAPI application exposing:

```txt
POST /api/v1/market-rent/estimate
```

The backend validates inputs, runs ingest + estimate logic, and returns structured JSON responses.

---

# Frontend

### `streamlit_app.py`

The Streamlit frontend automatically calls the FastAPI backend and renders:

- estimated market rent
- rent range
- confidence score
- adjustment waterfall
- used comparable leases
- dropped comparable leases

---

# Run Instructions

## 1. Activate virtual environment

Open PowerShell and run:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
```

---

## 2. Run FastAPI backend

Start the backend API server:

```powershell
python -m uvicorn app.main:app --reload
```

Once running, open:

```txt
http://127.0.0.1:8000/docs
```

This opens the FastAPI Swagger UI.

To manually test the API:

1. Expand:

```txt
POST /api/v1/market-rent/estimate
```

2. Click:

```txt
Try it out
```

3. Paste the target asset JSON:

```json
{
  "address": "4150 S 51st Ave, Phoenix, AZ 85043",
  "submarket": "Sky Harbor",
  "total_sf": 145000,
  "year_built": 2008,
  "clear_height_ft": 32,
  "as_of": "2025-09-30"
}
```

4. Click:

```txt
Execute
```

The API will return:
- point estimate
- confidence score
- adjustment waterfall
- used comparable leases
- dropped comparable leases

---

## 3. Run Streamlit frontend

Open a second PowerShell terminal and run:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
streamlit run streamlit_app.py
```

The Streamlit frontend automatically calls the FastAPI backend and displays:
- estimated market rent
- confidence score
- adjustment waterfall
- used comparable leases
- dropped comparable leases

---

## 4. Run tests

From the `backend` directory:

```powershell
pytest
```

Expected output:

```txt
2 passed
```

---

# Target Asset

The target warehouse being valued:

```json
{
  "address": "4150 S 51st Ave, Phoenix, AZ 85043",
  "submarket": "Sky Harbor",
  "total_sf": 145000,
  "year_built": 2008,
  "clear_height_ft": 32,
  "as_of": "2025-09-30"
}
```

The system compares each lease comp individually against this target building and adjusts the comp rents to become “target-equivalent” rents before blending them into the final estimate.

---

# Data Quality Handling

The ingest layer intentionally handles noisy CRE data issues:

- undisclosed / missing rents
- monthly vs annual rent normalization
- duplicate lease transactions
- off-market comps
- incomplete building attributes

Dropped comps are preserved with explicit reasons so the system remains auditable rather than silently discarding data.

---

# Waterfall Logic

The estimate waterfall shows how raw market comps evolve into the final target rent estimate:

```txt
Base weighted rent
→ Time adjustment
→ Vintage adjustment
→ Size adjustment
→ Clear height adjustment
→ Final estimate
```

Each step includes:
- before value
- after value
- delta
- rationale

This allows reviewers to reconstruct the estimate top-to-bottom.

---

# Key Assumptions

- Market rents grow at a flat 3% annually.
- Sky Harbor is the primary target submarket.
- Tolleson and Southwest Phoenix are treated as adjacent submarkets with reduced confidence.
- Larger industrial leases generally achieve lower rents per square foot.
- Monthly rent quotes are normalized to annual rents when identified in notes.
- Confidence scores reflect source reliability, market relevance, and data quality.

---

# Design Philosophy

This implementation prioritizes:

- auditability
- transparency
- deterministic logic
- data trust

over predictive complexity.

The assignment emphasized explainability and reviewer trust, so the estimate engine was intentionally implemented as a transparent rules-based adjustment model rather than a black-box predictive model.
