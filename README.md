# CampusHire Advisor

> AI-powered campus placement prediction and coaching tool for engineering students.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat&logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-3178C6?style=flat&logo=typescript)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat&logo=python)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What is CampusHire Advisor?

Campus placement cells in Indian engineering colleges rely almost exclusively on CGPA to evaluate student employability — missing high-signal indicators like competitive programming ratings, GitHub activity, resume quality, and project experience.

**CampusHire Advisor** combines all these signals into a single calibrated **placement probability (0–100%)** along with a **Placement Matrix Score** based on the RBU CDPC rubric, transparent SHAP-based explanations, ATS resume scoring, and a **What-If Simulator** so students know exactly what to improve before placement season.

---

## Features

| Feature | Description |
|---|---|
| **Placement Probability** | ML model outputs a 0–100% probability with confidence band |
| **Placement Matrix Score** | Deterministic RBU CDPC rubric score across 8 categories (/100) |
| **Resume ATS Scoring** | PDF parsing + keyword gap analysis |
| **SHAP Explainability** | Top feature contributions driving your score |
| **Action Plan Engine** | 2–3 prioritized, time-bound recommendations |
| **What-If Simulator** | Change any input and instantly see the delta in probability |
| **Extra Scorer** | Bonus adjustments for international internships, LORs, hackathons |

---

## Tech Stack

### Backend
- **FastAPI** — REST API with async support
- **SQLAlchemy** — ORM with PostgreSQL
- **Pydantic v2** — Schema validation
- **pdfplumber / PyPDF2** — Resume text extraction
- **XGBoost + Sentence-BERT** — ML prediction model
- **Google Gemini** — AI-powered action generation (with heuristic fallback)

### Frontend
- **React 18 + TypeScript** — UI
- **Vite** — Build tool
- **TanStack Query** — Server state management
- **React Router v6** — Client-side routing
- **Tailwind CSS** — Styling

### Deployment
- **Render** — Backend hosting
- **Vercel** — Frontend hosting
- **PostgreSQL** — Database (Render managed)

---

## Project Structure

```
placment-prediction-model/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── main.py          # API router (whatif before analysis!)
│   │   │   ├── deps.py          # Auth + DB dependencies
│   │   │   └── routes/
│   │   │       ├── analysis.py  # POST /analyse, GET /analyse/:id
│   │   │       └── whatif.py    # POST /analyse/whatif
│   │   ├── core/
│   │   │   └── config.py        # Settings (env vars)
│   │   ├── db/
│   │   │   ├── database.py      # SQLAlchemy engine
│   │   │   └── models.py        # StudentProfile, Submission
│   │   ├── engine/
│   │   │   ├── scorer.py        # MatrixScorer (deterministic RBU rubric)
│   │   │   ├── parser.py        # ResumeParser (ATS + skill extraction)
│   │   │   └── ml.py            # ML predictor (XGBoost + Gemini)
│   │   ├── schemas/
│   │   │   ├── profile.py       # Pydantic models
│   │   │   └── user.py
│   │   └── main.py              # FastAPI app + CORS
│   ├── ml/
│   │   └── extra_scorer.py      # Bonus probability adjustment
│   └── requirements.txt
│
└── campushire-advisor/          # React frontend
    ├── src/
    │   ├── hooks/
    │   │   └── useAnalysis.ts   # All API calls + data transforms
    │   ├── pages/
    │   │   ├── WhatIf.tsx       # What-If Simulator
    │   │   └── ...
    │   └── ...
    ├── vercel.json              # Vercel SPA routing config
    └── package.json
```

---

## Local Development Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL (or use the Render free tier)

---

### 1. Clone the repository

```bash
git clone https://github.com/<owner>/placment-prediction-model.git
cd placment-prediction-model
```

---

### 2. Backend setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file inside `backend/`:

```env
PROJECT_NAME=CampusHire Advisor
API_V1_STR=/api/v1
DATABASE_URL=postgresql://user:password@localhost:5432/campushire
SECRET_KEY=your-secret-key-here
FRONTEND_URL=http://localhost:5173
ENVIRONMENT=development

# Optional — for Gemini AI actions
GEMINI_API_KEY=your-gemini-api-key
```

Run the backend:

```bash
uvicorn app.main:app --reload --port 8000
```

API docs available at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 3. Frontend setup

```bash
cd campushire-advisor

# Install dependencies
npm install
```

Create a `.env` file inside `campushire-advisor/`:

```env
VITE_API_URL=http://localhost:8000/api/v1
```

Run the frontend:

```bash
npm run dev
```

Frontend available at: [http://localhost:5173](http://localhost:5173)

---

## API Reference

### Core Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/analyse` | Submit profile + resume for full analysis |
| `GET` | `/api/v1/analyse/{id}` | Fetch saved analysis result |
| `POST` | `/api/v1/analyse/whatif` | Stateless what-if simulation |

### POST `/api/v1/analyse`

Accepts `multipart/form-data`:
- `profile` — stringified JSON (see `ProfileSubmissionRequest` schema)
- `resume` — PDF file (max 5 MB)

Returns `AnalysisResponse` with probability, matrix score, ATS score, SHAP contributions, and action items.

### POST `/api/v1/analyse/whatif`

Accepts JSON body:
```json
{
  "profile": { "lc_total_solved": 300 },
  "experience": { "hackathon_first": 1 },
  "ats_score": 85.0,
  "base_profile": { "academic": {}, "coding": {}, "experience": {} }
}
```

Returns the same `AnalysisResponse` shape. **Nothing is written to the database.**

---

## Placement Matrix Score

Based on the **RBU CDPC rubric** for IT industry placements:

| Category | Max Score |
|---|---|
| 10th Percentage | 5 |
| 12th Percentage | 5 |
| CGPA | 5 |
| GitHub Profile | 15 |
| Coding Platforms (LC + HR) | 20 |
| Internship Experience | 10 |
| Skillset & Certifications | 15 |
| Projects | 15 |
| Hackathons & Competitions | 10 |
| **Total** | **100** |

---

## Deployment

### Backend → Render

1. Push your code to GitHub.
2. Go to [render.com](https://render.com) → **New Web Service** → connect your repo.
3. Set **Root Directory** to `backend`.
4. Set **Build Command**: `pip install -r requirements.txt`
5. Set **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Set **Health Check Path**: `/health`
7. Add environment variables in the Render dashboard:
   - `DATABASE_URL`
   - `SECRET_KEY`
   - `FRONTEND_URL` → your Vercel URL
   - `GEMINI_API_KEY` (if using AI actions)
   - `ENVIRONMENT=production`

### Frontend → Vercel

1. Go to [vercel.com](https://vercel.com) → **New Project** → import your repo.
2. Set **Root Directory** to `campushire-advisor`.
3. Set **Framework Preset** to `Vite`.
4. Add environment variable:
   - `VITE_API_URL` → your Render backend URL e.g. `https://campushire-backend.onrender.com/api/v1`
5. Click **Deploy**.

The `vercel.json` in the frontend root handles SPA routing automatically.

---

## Environment Variables Reference

### Backend (`backend/.env`)

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `SECRET_KEY` | ✅ | JWT signing secret |
| `PROJECT_NAME` | ✅ | App name shown in API docs |
| `API_V1_STR` | ✅ | API prefix e.g. `/api/v1` |
| `FRONTEND_URL` | ✅ | Allowed CORS origin |
| `ENVIRONMENT` | ✅ | `development` or `production` |
| `GEMINI_API_KEY` | ⬜ | Google Gemini API key for AI actions |

### Frontend (`campushire-advisor/.env`)

| Variable | Required | Description |
|---|---|---|
| `VITE_API_URL` | ✅ | Full backend API base URL |

---

## Contributing

Please read the [Contributing Guide](#contributing-guide) below before opening a PR.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgements

- RBU Career Development & Placement Cell for the placement matrix rubric
- [FastAPI](https://fastapi.tiangolo.com) and [TanStack Query](https://tanstack.com/query) communities
