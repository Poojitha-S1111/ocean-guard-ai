import os
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.database import get_db, init_db
from app.schemas import (
    DetectionResponse, ValidationRequest, ValidationResponse,
    DriftRequest, DriftResponse, VesselRankingRequest, VesselRankingResponse,
    SpillHistoryResponse
)

# Base Paths
BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
SAMPLE_IMAGES_DIR = BACKEND_DIR / "data" / "sample_images"

app = FastAPI(
    title="OceanGuard AI – Marine Pollution Monitoring & Investigation System",
    description="Full-stack AI/ML prototype for SAR oil spill detection, drift backtracking, and candidate vessel ranking. Decision-support tool.",
    version="1.0.0"
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure sample images directory exists
SAMPLE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Mount sample images
app.mount("/data/sample_images", StaticFiles(directory=str(SAMPLE_IMAGES_DIR)), name="sample_images")

# On startup, ensure database is initialized
@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "OceanGuard AI API",
        "system_notice": "Decision-support tool. Vessel rankings are investigative leads, not proof of responsibility."
    }

# -------------------------------------------------------------
# Endpoints: Spills Listing & Details
# -------------------------------------------------------------
@app.get("/api/spills")
def get_spills():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, latitude, longitude, detection_time, area_sq_km, perimeter_km,
                   classification, confidence_score, source_image_name, image_path,
                   overlay_image_path, polygon_geojson, features_json, wind_speed_knots,
                   wind_direction_deg, current_speed_knots, current_direction_deg,
                   status, notes, created_at
            FROM spill_detections
            ORDER BY detection_time DESC;
        """)
        rows = cursor.fetchall()
        spills = []
        for r in rows:
            item = dict(r)
            if item.get("polygon_geojson"):
                try:
                    item["polygon_geojson"] = json.loads(item["polygon_geojson"])
                except Exception:
                    pass
            if item.get("features_json"):
                try:
                    item["features_json"] = json.loads(item["features_json"])
                except Exception:
                    pass
            spills.append(item)
        return spills

@app.get("/api/spills/{spill_id}")
def get_spill(spill_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, latitude, longitude, detection_time, area_sq_km, perimeter_km,
                   classification, confidence_score, source_image_name, image_path,
                   overlay_image_path, polygon_geojson, features_json, wind_speed_knots,
                   wind_direction_deg, current_speed_knots, current_direction_deg,
                   status, notes, created_at
            FROM spill_detections
            WHERE id = ?;
        """, (spill_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Spill detection '{spill_id}' not found.")
        
        item = dict(row)
        if item.get("polygon_geojson"):
            try:
                item["polygon_geojson"] = json.loads(item["polygon_geojson"])
            except Exception:
                pass
        if item.get("features_json"):
            try:
                item["features_json"] = json.loads(item["features_json"])
            except Exception:
                pass
        return item

@app.get("/api/spills/{spill_id}/history")
def get_spill_history(spill_id: str):
    # Delegate to historical analysis service
    from services.historical import analyze_spill_history
    return analyze_spill_history(spill_id)

# -------------------------------------------------------------
# Module 1 & 2: Detection and Validation Endpoints
# -------------------------------------------------------------
@app.post("/api/detect", response_model=DetectionResponse)
async def detect_spills(
    file: UploadFile = File(...),
    reference_lat: float = Form(50.450),
    reference_lon: float = Form(0.650)
):
    from services.detection import process_sar_image
    contents = await file.read()
    return process_sar_image(contents, file.filename, reference_lat, reference_lon)

@app.post("/api/validate", response_model=ValidationResponse)
def validate_patch(request: ValidationRequest):
    from services.validation import validate_patch_features
    return validate_patch_features(request.patch_id, request.features)

# -------------------------------------------------------------
# Module 4 & 5: Drift Estimation & Vessel Ranking
# -------------------------------------------------------------
@app.post("/api/drift", response_model=DriftResponse)
def estimate_drift(request: DriftRequest):
    from services.drift import compute_drift_backtrack
    return compute_drift_backtrack(request)

@app.post("/api/rank-vessels", response_model=VesselRankingResponse)
def rank_vessels(request: VesselRankingRequest):
    from services.vessel_ranking import rank_candidate_vessels
    return rank_candidate_vessels(request)

# -------------------------------------------------------------
# Static Frontend Serving
# -------------------------------------------------------------
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend_static")

    @app.get("/")
    def serve_index():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "OceanGuard AI Backend Active. Frontend index.html will be generated in Step 5."}
