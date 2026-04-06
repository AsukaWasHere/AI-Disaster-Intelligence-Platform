# 🛰️ AI Disaster Intelligence Platform

An end-to-end machine learning system for real-time disaster prediction, damage estimation, and risk scoring — powered by a FastAPI backend and a React dashboard.

---

## Overview

The AI Disaster Intelligence Platform ingests geospatial and environmental parameters to classify disaster types, estimate economic damage, and compute actionable risk scores. Results are surfaced through a live React dashboard with geospatial visualization and neural insight feeds.

---

## Features

- 🔍 **Disaster Classification** — Multi-class prediction of disaster type (earthquake, wildfire, hurricane, flood, etc.) using Random Forest and XGBoost
- 💰 **Damage Estimation** — Regression model to forecast economic impact in USD
- 📊 **Risk Scoring** — Composite risk score derived from classification confidence, magnitude, and location
- 🗺️ **Geospatial Dashboard** — Live React UI with interactive maps, layer toggles, and regional analysis
- 🧠 **NLP Pipeline** — Keyword extraction and narrative summarization from free-text scenario descriptions
- ⚡ **REST API** — FastAPI backend with typed schemas, modular routes, and model inference endpoints
- 🔄 **Real-time Insights** — Aggregated event stats, average damage, and high-risk state identification

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend API** | FastAPI, Uvicorn |
| **ML Models** | scikit-learn, XGBoost |
| **NLP** | Custom keyword extractor + summarizer |
| **Data Processing** | Pandas, NumPy |
| **Frontend** | React 18, Vite, Tailwind CSS |
| **Config** | YAML-based config system |
| **Serialization** | Pydantic schemas |

---

## Project Structure

```
ai-disaster-intelligence-platform/
├── requirements.txt
├── train_all.py                    # Unified model training entry point
├── configs/
│   └── config.yaml                 # Centralized config (paths, hyperparams)
├── data/
│   └── processed/
│       └── feature_columns.json    # Feature schema for inference
├── models/
│   ├── classification/
│   │   └── random_forest.pkl       # Trained classifier
│   └── regression/
│       └── xgboost_regressor.pkl   # Trained damage regressor
├── scripts/
│   └── train_classifier.py
├── src/
│   ├── api/
│   │   ├── main.py                 # FastAPI app + CORS
│   │   ├── schemas.py              # Pydantic request/response models
│   │   ├── dependencies.py         # Shared DI (model loading)
│   │   └── routes/
│   │       ├── predict.py          # POST /predict
│   │       ├── insights.py         # GET /insights
│   │       └── risk.py             # Risk score logic
│   ├── data/
│   │   ├── data_loader.py
│   │   ├── data_cleaning.py
│   │   └── pipeline.py
│   ├── features/
│   │   └── feature_engineering.py
│   ├── models/
│   │   ├── classification/         # RF + XGBoost classifiers + evaluators
│   │   ├── regression/             # Linear + XGBoost regressors + evaluators
│   │   └── nlp/                    # Keyword extraction, summarization
│   └── utils/
│       ├── config.py
│       ├── risk.py
│       ├── logger.py
│       ├── exceptions.py
│       └── merge_features.py
├── dashboard/                      # Legacy Streamlit dashboard (preserved)
│   ├── app.py
│   └── pages/
└── sentinel/                       # React frontend
    ├── index.html
    ├── vite.config.js
    ├── tailwind.config.js
    └── src/
        ├── App.jsx
        ├── services/
        │   └── api.js              # Centralized API layer
        ├── components/
        │   ├── Sidebar.jsx
        │   ├── Topbar.jsx
        │   ├── LoadingSpinner.jsx
        │   └── ErrorBanner.jsx
        └── pages/
            ├── OverviewPage.jsx
            ├── PredictionsPage.jsx
            ├── GeospatialPage.jsx
            └── InsightsPage.jsx
```

---

## Installation

### Prerequisites

- Python 3.9+
- Node.js 18+

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/your-username/ai-disaster-intelligence-platform.git
cd ai-disaster-intelligence-platform

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Train models (if not using pre-trained .pkl files)
python train_all.py

# Start the API server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at `http://127.0.0.1:8000`  
Interactive docs at `http://127.0.0.1:8000/docs`

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

Dashboard will be available at `http://localhost:5173`

---

## API Reference

### `POST /predict`

Run disaster risk prediction for a given location and scenario.

**Request**

```json
{
  "lat": 35.6895,
  "lon": 139.6917,
  "month": 9,
  "magnitude": 7.2,
  "narrative": "Heavy rainfall preceding seismic activity in coastal zone."
}
```

**Response**

```json
{
  "event_type": "Earthquake",
  "top_predictions": [
    { "label": "Earthquake", "probability": 0.87 },
    { "label": "Tsunami Inundation", "probability": 0.62 },
    { "label": "Landslide", "probability": 0.41 }
  ],
  "damage_usd": 14200000000,
  "risk_score": 88,
  "explanation": "Seismic indicators and coastal proximity suggest high-impact primary event with secondary cascade risk.",
  "keywords": ["seismic", "coastal", "high-magnitude", "secondary-risk"]
}
```

---

### `GET /insights`

Retrieve aggregated platform statistics.

**Response**

```json
{
  "total_events": 1284,
  "avg_damage_usd": 4200000,
  "avg_risk_score": 78.4,
  "high_risk_states": ["California, USA", "Florida, USA", "Kanto, Japan"]
}
```

---

## Use Cases

- **Emergency management agencies** — Rapid pre-event risk triage and resource allocation
- **Insurance & reinsurance** — AI-assisted damage estimation before field assessments
- **Infrastructure planning** — Long-term geospatial risk profiling for construction and policy
- **Research institutions** — Reproducible ML pipeline for disaster science experiments
- **Government dashboards** — Real-time situational awareness across regions

---

## Future Improvements

- [ ] Real-time data ingestion from USGS, NOAA, and Copernicus APIs
- [ ] Temporal forecasting with LSTM/Transformer models
- [ ] User authentication and role-based access control
- [ ] Exportable PDF incident reports from the dashboard
- [ ] WebSocket support for live event streaming
- [ ] Multi-language NLP pipeline for international incident narratives
- [ ] Docker + Docker Compose for one-command deployment
- [ ] CI/CD pipeline with automated model retraining on new data

---

## License

This project is licensed under the [MIT License](LICENSE).

```
MIT License — free to use, modify, and distribute with attribution.
```

---

<p align="center">Built with FastAPI · scikit-learn · XGBoost · React · Tailwind CSS</p>