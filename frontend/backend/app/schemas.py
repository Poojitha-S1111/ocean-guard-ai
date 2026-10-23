from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class PatchFeature(BaseModel):
    patch_id: int
    area_pixels: float
    perimeter_pixels: float
    elongation: float
    compactness: float
    mean_intensity: float
    surrounding_contrast: float
    texture_homogeneity: float
    texture_contrast: float
    texture_energy: float
    bounding_box: List[int] # [min_r, min_c, max_r, max_c]
    polygon_coords: List[List[float]] # [[lat, lon], ...]
    area_sq_km: Optional[float] = None
    perimeter_km: Optional[float] = None
    classification: Optional[str] = None
    confidence_score: Optional[float] = None

class DetectionResponse(BaseModel):
    detection_id: str
    image_name: str
    original_image_url: str
    overlay_image_url: str
    patch_count: int
    patches: List[PatchFeature]
    center_lat: float
    center_lon: float
    processing_time_ms: float
    disclaimer: str = "Decision-support tool. Rankings and detections are investigative leads, not proof of responsibility. Human verification required."

class ValidationRequest(BaseModel):
    patch_id: int
    features: Dict[str, float]

class ValidationResponse(BaseModel):
    patch_id: int
    classification: str # "likely_oil_spill" or "natural_lookalike"
    confidence_score: float # 0.0 to 1.0
    probabilities: Dict[str, float]
    feature_importance: Dict[str, float]
    investigative_notes: str
    disclaimer: str = "Decision-support tool. Human verification required."

class DriftRequest(BaseModel):
    spill_id: Optional[str] = None
    latitude: float
    longitude: float
    observation_time: str # ISO format
    backtrack_hours: float = 12.0
    wind_speed_knots: float = 15.0
    wind_direction_deg: float = 230.0 # direction wind blows FROM (meteorological)
    current_speed_knots: float = 0.8
    current_direction_deg: float = 70.0 # direction current flows TO (oceanographic)
    uncertainty_growth_rate_km_per_hr: float = 0.4 # expands search area with backtrack duration

class DriftPoint(BaseModel):
    hours_back: float
    timestamp: str
    latitude: float
    longitude: float
    uncertainty_radius_km: float

class DriftResponse(BaseModel):
    spill_latitude: float
    spill_longitude: float
    observation_time: str
    backtrack_hours: float
    net_drift_speed_knots: float
    net_drift_direction_deg: float
    drift_path: List[DriftPoint]
    source_region_center: Dict[str, float] # {lat, lon}
    source_region_radius_km: float
    estimated_release_window: Dict[str, str] # {earliest, latest}
    geojson: Dict[str, Any]
    formula_used: str = "Net Drift = Ocean Current + ~3% Wind Speed (standard backtracking model)"
    disclaimer: str = "Decision-support tool. Source region is an estimated investigative search area subject to wind and current variance."

class VesselWeightConfig(BaseModel):
    timing: float = 0.25
    proximity: float = 0.25
    trajectory: float = 0.25
    drift_consistency: float = 0.25

class VesselRankingRequest(BaseModel):
    spill_id: Optional[str] = None
    source_lat: float
    source_lon: float
    source_radius_km: float
    release_window_start: str
    release_window_end: str
    drift_path_points: Optional[List[Dict[str, float]]] = None
    weights: Optional[VesselWeightConfig] = None

class CandidateVesselScore(BaseModel):
    mmsi: int
    name: str
    vessel_type: str
    flag: str
    length: Optional[float] = None
    draft: Optional[float] = None
    destination: Optional[str] = None
    overall_score: float # 0.0 to 1.0
    sub_scores: Dict[str, float] # timing, proximity, trajectory, drift_consistency
    min_distance_to_source_km: float
    closest_approach_time: str
    candidate_assessment: str
    track_coordinates: List[List[float]] # [[lat, lon], ...]
    is_high_interest: bool

class VesselRankingResponse(BaseModel):
    spill_id: Optional[str]
    ranked_candidate_vessels: List[CandidateVesselScore]
    weights_applied: Dict[str, float]
    total_vessels_evaluated: int
    disclaimer: str = "Decision-support tool. Vessel rankings are investigative leads, not proof of responsibility. Human verification required."

class HistoricalIncidentItem(BaseModel):
    id: str
    incident_date: str
    latitude: float
    longitude: float
    distance_km: float
    spill_type: str
    volume_m3: Optional[float]
    source_description: str
    responsible_vessel: Optional[str]
    verified: bool
    similarity_score: float
    similarity_notes: str

class SpillHistoryResponse(BaseModel):
    spill_id: str
    spill_name: str
    spill_location: Dict[str, float]
    spill_time: str
    nearby_historical_incidents: List[HistoricalIncidentItem]
    local_repeat_offense_risk: str
    timeline_events: List[Dict[str, Any]]
