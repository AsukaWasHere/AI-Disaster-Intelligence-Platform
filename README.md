# AI Disaster Intelligence Platform

> A production-ready machine learning system for analyzing, predicting, and
> visualizing natural disaster risk from the NOAA Storm Events dataset.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Overview

This platform ingests NOAA Storm Events data and delivers a unified AI pipeline
covering disaster type classification, damage estimation, composite risk scoring,
NLP-powered narrative insights, and interactive geospatial visualization.

It is designed for emergency management analysts, climate researchers, and
data engineers who need a reliable, extensible decision-support system.

## Features

- **Multi-class classification** — predicts disaster type (EVENT_TYPE) using
  Random Forest and XGBoost with class-imbalance handling
- **Damage regression** — estimates total damage in USD with log-transformed
  XGBoost and baseline linear model
- **Composite risk score** — weighted formula combining damage, deaths,
  injuries, and magnitude into a 0–100 risk index
- **NLP narrative analysis** — extracts keywords and semantic embeddings from
  NOAA event/episode narratives using spaCy and sentence-transformers
- **Geospatial visualization** — interactive risk heatmaps and event
  clustering via Folium and Plotly
- **REST API** — FastAPI backend with Pydantic validation and auto-generated
  OpenAPI documentation
- **Interactive dashboard** — Streamlit UI for live inference and data
  exploration
- **Fully containerized** — Docker + docker-compose for one-command deployment

## Architecture
```
NOAA Data → Feature Engineering → ML Models (Classification / Regression / NLP)
         → Risk Scorer → FastAPI → Streamlit Dashboard + Folium Maps
```

See `docs/architecture.md` for the full system diagram.

## Tech Stack

| Layer | Technology |
|---|---|
| ML | scikit-learn, XGBoost, PyTorch |
| NLP | spaCy, sentence-transformers |
| API | FastAPI, Pydantic, Uvicorn |
| Dashboard | Streamlit, Plotly, Folium |
| Database | PostgreSQL, SQLAlchemy, Alembic |
| Deployment | Docker, docker-compose |

## Setup

### Prerequisites

- Python 3.11+
- Docker and docker-compose
- PostgreSQL 15+ (or use the bundled Docker service)

### Local Development
```bash
# 1. Clone the repository
git clone https://github.com/your-org/ai-disaster-intelligence.git
cd ai-disaster-intelligence

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download spaCy model
python -m spacy download en_core_web_sm

# 5. Configure environment variables
cp .env.example .env
# Edit .env with your DB credentials

# 6. Run database migrations
alembic upgrade head

# 7. Run data pipeline
python -m src.data.loader
python -m src.features.builder

# 8. Train models
python -m src.models.classification.random_forest
python -m src.models.regression.xgboost_reg

# 9. Start the API
uvicorn src.api.main:app --reload --port 8000

# 10. Start the dashboard (new terminal)
streamlit run dashboard/app.py
```

### Docker Deployment
```bash
docker-compose up --build
```

Services will be available at:
- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:8501
- pgAdmin: http://localhost:5050

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/predict/type` | POST | Predict disaster event type |
| `/predict/damage` | POST | Estimate total damage in USD |
| `/risk/score` | POST | Compute composite risk score |
| `/insights/narrative` | POST | Extract NLP keywords from narrative |
| `/health` | GET | Service health check |

Full reference: `docs/api_reference.md` or `/docs` (Swagger UI).

## Screenshots

> _Dashboard overview — coming soon_

> _Geospatial risk heatmap — coming soon_

> _Classification results by event type — coming soon_

## Project Structure
```
ai-disaster-intelligence/
├── src/              # All application source code
├── dashboard/        # Streamlit pages and components
├── configs/          # YAML configuration
├── data/             # Raw and processed datasets
├── tests/            # Unit and integration tests
├── deployment/       # Dockerfile and docker-compose
└── docs/             # Architecture and API docs
```

## Running Tests
```bash
pytest tests/ -v --tb=short
```

## Future Scope

- **Time-series forecasting** — predict disaster frequency by region using
  LSTM or Prophet on historical monthly event counts
- **Automated alerts** — webhook integration to notify emergency services
  when risk score exceeds a configurable threshold
- **Fine-tuned BERT** — domain-adapted NER on NOAA narratives for extracting
  structured damage assertions from free text
- **PostGIS integration** — native geospatial queries for administrative
  boundary intersection and county-level risk aggregation
- **MLflow experiment tracking** — log all training runs, metrics, and
  artifacts to a centralized MLflow server
- **CI/CD pipeline** — GitHub Actions workflow for lint, test, build, and
  deploy on every merge to main

## License

MIT License. See `LICENSE` for details.

## Contributing

Pull requests are welcome. Please read `CONTRIBUTING.md` and ensure all tests
pass before submitting.