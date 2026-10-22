# OceanGuard AI – Marine Pollution Monitoring & Investigation System

> **Decision-Support Notice**: OceanGuard AI is strictly an investigative decision-support tool. Candidate vessel rankings and hydrodynamic backtrack trajectories represent spatial and temporal correlations, **not proof of responsibility**. Human analyst verification and environmental ground-truthing are required.

---

## 🌊 Overview

**OceanGuard AI** is a full-stack AI/ML prototype designed for coastal maritime authorities, environmental protection agencies, and port state control inspectors. It detects suspected hydrocarbon slicks in Synthetic Aperture Radar (SAR) satellite imagery, performs hydrodynamic drift backtracking, and investigates candidate vessel traffic to provide actionable investigative leads.

### Key Capabilities
- **SAR Satellite Anomaly Detection**: Ingests high-resolution SAR rasters, removes speckle noise via adaptive Lee filtering, normalizes backscatter, and extracts dark capillary damping boundaries.
- **ML Saliency & Look-alike Classification**: Extracts 9 morphology and Gray-Level Co-occurrence Matrix (GLCM) texture features and evaluates a calibrated Random Forest classifier to distinguish mineral oil slicks from natural biogenic look-alikes.
- **Hydrodynamic Drift Backtracking**: Inverts the empirical marine drift equation ($\vec{V}_{\text{drift}} = \vec{V}_{\text{current}} + 0.03 \times \vec{V}_{\text{wind}}$) hour-by-hour to reconstruct the past drift trajectory and an expanding uncertainty source region.
- **Multivariate Candidate Vessel Ranking**: Fuses Automatic Identification System (AIS) tracks to evaluate candidate vessels across four sub-scores: **Timing**, **Proximity**, **Trajectory**, and **Drift-path consistency**.
- **Interactive Operations Console**: Dark navy/ocean-teal single-page dashboard featuring Leaflet.js geospatial mapping, AIS time-scrubbing slider, SAR upload and analysis, and historical recurring risk logs.

---

## 📁 System Architecture & Directory Structure

```text
oceanguard-ai/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI application & REST routing
│   │   ├── database.py           # SQLite connection pool & table schemas
│   │   └── schemas.py            # Pydantic v2 validation contracts
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── train.py              # ML training script, evaluation & joblib export
│   │   ├── classifier.py         # Model loading & inference
│   │   ├── oil_spill_classifier.joblib  # Trained Random Forest artifact
│   │   └── README.md             # Dataset swap instructions & feature guide
│   ├── services/
│   │   ├── __init__.py
│   │   ├── detection.py          # SAR noise filtering, morphology & patch extraction
│   │   ├── validation.py         # ML feature classification & probabilistic scoring
│   │   ├── drift.py              # Vector decomposition & trajectory backtracking
│   │   ├── vessel_ranking.py     # 4-factor candidate vessel multivariate ranking
│   │   └── historical.py         # Haversine distance & chronic recurrence analysis
│   ├── data/
│   │   ├── sample_images/        # Calibrated sample SAR acquisitions & overlays
│   │   └── sample_ais_tracks.json # Exported sample AIS telemetry
│   ├── generate_sample_sars.py  # Synthetic SAR imagery generator
│   ├── requirements.txt          # Python runtime dependencies
│   ├── seed.py                   # SQLite database seeder
│   └── test_api.py               # Automated backend verification test suite
├── frontend/
│   ├── index.html                # Single-page operations console & product landing
│   ├── style.css                 # Dark navy/ocean-teal responsive styles
│   └── app.js                    # Leaflet map, API integration & animation slider
└── README.md                     # Documentation & setup guide
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+ or Python 3.11 (tested on Python 3.11.9)
- Web browser (Chrome, Edge, Firefox)

### 2. Install Dependencies
Open a terminal in the project directory:
```bash
cd backend
pip install -r requirements.txt
```

### 3. Initialize & Seed Database
Populate SQLite with sample spill detections, historical incidents, and 24-hour AIS candidate tracks:
```bash
python seed.py
```
*(Creates `backend/oceanguard.db` and loads 4 demonstration spills, 5 historical cases, and 10 candidate vessels with 240 AIS tracking points).*

### 4. Train the ML Classifier (Optional / Pre-trained)
To re-train the Random Forest model and print test performance metrics:
```bash
python ml/train.py
```
*(Prints accuracy, precision, recall, confusion matrix, and feature importances, saving the model bundle to `backend/ml/oil_spill_classifier.joblib`).*

### 5. Launch the Full-Stack Application
Start the FastAPI server via Uvicorn:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 6. Open the Dashboard
Open your web browser and navigate to:
```
http://127.0.0.1:8000
```
- Interactive map loads with active spill polygons, drift path, source uncertainty buffer, and candidate vessel tracks.
- Click any spill in the left sidebar to view forensic details, hydrodynamic vectors, candidate vessel rankings, and historical records.
- Click **"Upload SAR Image"** to run the live computer vision pipeline on a new image.
- Use the **AIS Temporal Scrubbing Slider** to step forward or backward in time or press **Play** to animate transits.

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health status and decision-support operational notice |
| `GET` | `/api/spills` | Retrieve all recorded spill detections with GeoJSON polygons |
| `GET` | `/api/spills/{id}` | Retrieve specific spill detection with full evidence |
| `GET` | `/api/spills/{id}/history` | Correlate spill with SQLite historical incident records |
| `POST` | `/api/detect` | Process uploaded SAR image (speckle filter, adaptive thresholding, contours) |
| `POST` | `/api/validate` | Classify extracted patch features via scikit-learn model |
| `POST` | `/api/drift` | Compute hydrodynamic backtracking path and source uncertainty region |
| `POST` | `/api/rank-vessels` | Rank candidate vessels across 4 weighted sub-scores |

---

## 🔬 Machine Learning & Forensic Features

During SAR patch segmentation, 9 physical features are extracted:
1. `area_pixels`: Spatial scale of the detected feature.
2. `perimeter_pixels`: Interface length with open sea.
3. `elongation`: Major-to-minor axis ratio. (Underway vessels typically leave linear trails with elongation > 2.5).
4. `compactness`: Isoperimetric quotient ($4\pi A / P^2$).
5. `mean_intensity`: Average backscatter return (hydrocarbons strongly dampen capillary waves).
6. `surrounding_contrast`: Ocean buffer intensity minus patch intensity (steep contrast indicates mineral oil).
7. `texture_homogeneity`: GLCM uniformity.
8. `texture_contrast`: Local GLCM texture roughness.
9. `texture_energy`: Angular second moment.

To swap in real Sentinel-1 SAR or NOAA CleanSea datasets, see instructions in [`backend/ml/README.md`](file:///backend/ml/README.md).

---

## 🛡️ Responsible AI & Decision-Support Guidelines

1. **Investigative Leads Only**: Rankings prioritize vessels for inspection. They do not constitute legal proof of fault.
2. **Neutral Nomenclature**: The system uses **"candidate vessel"**, never "culprit" or "violator".
3. **Explicit Uncertainty**: All estimated release windows, backtracking horizons, and source region radii explicitly display confidence bounds ($\pm \text{km}$).
