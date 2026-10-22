import math
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.database import get_db
from app.schemas import (
    VesselRankingRequest, VesselRankingResponse,
    CandidateVesselScore, VesselWeightConfig
)
from services.historical import haversine_distance_km

def parse_iso(ts_str: str) -> datetime:
    clean = ts_str.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(clean)
    except Exception:
        return datetime.utcnow()

def min_distance_to_linestring_km(point_lat: float, point_lon: float, line_points: List[Dict[str, float]]) -> float:
    """
    Computes minimum haversine distance from a point to a list of lat/lon waypoints.
    """
    if not line_points:
        return 999.0
    min_dist = 9999.0
    for wp in line_points:
        w_lat = wp.get("latitude", wp.get("lat", 0.0))
        w_lon = wp.get("longitude", wp.get("lon", 0.0))
        d = haversine_distance_km(point_lat, point_lon, w_lat, w_lon)
        if d < min_dist:
            min_dist = d
    return min_dist

def rank_candidate_vessels(req: VesselRankingRequest) -> VesselRankingResponse:
    # 1. Weights
    w_cfg = req.weights or VesselWeightConfig()
    total_w = w_cfg.timing + w_cfg.proximity + w_cfg.trajectory + w_cfg.drift_consistency
    if total_w <= 0:
        total_w = 1.0
    w_time = w_cfg.timing / total_w
    w_prox = w_cfg.proximity / total_w
    w_traj = w_cfg.trajectory / total_w
    w_drift = w_cfg.drift_consistency / total_w
    
    # 2. Parse release window
    win_start = parse_iso(req.release_window_start)
    win_end = parse_iso(req.release_window_end)
    if win_start > win_end:
        win_start, win_end = win_end, win_start
    win_mid = win_start + (win_end - win_start) / 2
    
    # 3. Fetch vessels and their track points from SQLite
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT mmsi, name, vessel_type, flag, imo, length, draft, destination FROM ais_vessels;")
        vessel_rows = cursor.fetchall()
        
        candidates: List[CandidateVesselScore] = []
        
        for v in vessel_rows:
            mmsi = v["mmsi"]
            
            cursor.execute("""
                SELECT timestamp, latitude, longitude, speed_knots, course_deg, status
                FROM ais_track_points
                WHERE mmsi = ?
                ORDER BY timestamp ASC;
            """, (mmsi,))
            track_points = cursor.fetchall()
            
            if not track_points:
                continue
                
            track_coords = []
            min_dist_to_source = 9999.0
            closest_pt_time = track_points[0]["timestamp"]
            points_inside_source = 0
            min_dist_to_drift_line = 9999.0
            
            for pt in track_points:
                lat, lon = pt["latitude"], pt["longitude"]
                track_coords.append([lat, lon])
                
                # Distance to estimated source region center
                d_source = haversine_distance_km(lat, lon, req.source_lat, req.source_lon)
                if d_source < min_dist_to_source:
                    min_dist_to_source = d_source
                    closest_pt_time = pt["timestamp"]
                    
                if d_source <= req.source_radius_km:
                    points_inside_source += 1
                    
                # Distance to drift path if provided
                if req.drift_path_points:
                    d_drift = min_distance_to_linestring_km(lat, lon, req.drift_path_points)
                    if d_drift < min_dist_to_drift_line:
                        min_dist_to_drift_line = d_drift

            # ---------------------------------------------------------
            # Sub-score 1: Timing (0.0 to 1.0)
            # ---------------------------------------------------------
            t_closest = parse_iso(closest_pt_time)
            if win_start <= t_closest <= win_end:
                timing_score = 1.0
            else:
                # Time difference in hours to nearest window edge
                diff_sec = min(abs((t_closest - win_start).total_seconds()), abs((t_closest - win_end).total_seconds()))
                diff_hours = diff_sec / 3600.0
                timing_score = max(0.0, math.exp(-diff_hours / 4.0)) # exponential decay over 4-8 hrs
                
            # ---------------------------------------------------------
            # Sub-score 2: Proximity (0.0 to 1.0)
            # ---------------------------------------------------------
            if min_dist_to_source <= req.source_radius_km:
                proximity_score = 1.0
            else:
                excess_km = min_dist_to_source - req.source_radius_km
                proximity_score = max(0.0, 1.0 - (excess_km / 22.0)) # decays to 0 at 22km beyond source
                
            # ---------------------------------------------------------
            # Sub-score 3: Trajectory (0.0 to 1.0)
            # ---------------------------------------------------------
            # Does the vessel transit directly across or through the source zone?
            if points_inside_source >= 1:
                trajectory_score = min(1.0, 0.85 + (points_inside_source * 0.05))
            else:
                # Passes near the boundary
                trajectory_score = max(0.0, 0.70 - (min_dist_to_source / 30.0))
                
            # ---------------------------------------------------------
            # Sub-score 4: Drift-path consistency (0.0 to 1.0)
            # ---------------------------------------------------------
            if req.drift_path_points and min_dist_to_drift_line < 900:
                drift_score = max(0.0, 1.0 - (min_dist_to_drift_line / 18.0))
            else:
                # Fallback to proximity correlation
                drift_score = proximity_score * 0.85

            # Combined weighted score
            overall = (
                w_time * timing_score +
                w_prox * proximity_score +
                w_traj * trajectory_score +
                w_drift * drift_score
            )
            overall = round(min(1.0, max(0.0, overall)), 3)
            
            # Plain language explanation
            assessments = []
            if overall >= 0.75:
                assessments.append(f"High-interest candidate lead ({int(overall*100)}%).")
                assessments.append(f"Vessel passed within {min_dist_to_source:.1f} km of source center at {closest_pt_time[11:16]} UTC, directly matching the estimated release window.")
                assessments.append("Track path closely aligns with the backtracked drift vector.")
            elif overall >= 0.50:
                assessments.append(f"Moderate investigative interest ({int(overall*100)}%).")
                assessments.append(f"Closest approach was {min_dist_to_source:.1f} km at {closest_pt_time[11:16]} UTC.")
                if timing_score > 0.7:
                    assessments.append("Timing matches the release window, but vessel passed slightly peripheral to the primary source radius.")
                else:
                    assessments.append("Spatial route is in the corridor, but timing exhibits a slight offset from the estimated release window.")
            else:
                assessments.append(f"Low correlation lead ({int(overall*100)}%).")
                assessments.append(f"Closest approach was {min_dist_to_source:.1f} km outside source region; temporal or geographic alignment is weak.")

            candidate = CandidateVesselScore(
                mmsi=mmsi,
                name=v["name"],
                vessel_type=v["vessel_type"],
                flag=v["flag"] or "Unknown",
                length=v["length"],
                draft=v["draft"],
                destination=v["destination"],
                overall_score=overall,
                sub_scores={
                    "timing": round(timing_score, 2),
                    "proximity": round(proximity_score, 2),
                    "trajectory": round(trajectory_score, 2),
                    "drift_consistency": round(drift_score, 2)
                },
                min_distance_to_source_km=round(min_dist_to_source, 1),
                closest_approach_time=closest_pt_time,
                candidate_assessment=" ".join(assessments),
                track_coordinates=track_coords,
                is_high_interest=(overall >= 0.70)
            )
            candidates.append(candidate)

    # Sort candidates by overall score descending
    candidates = sorted(candidates, key=lambda c: c.overall_score, reverse=True)
    
    return VesselRankingResponse(
        spill_id=req.spill_id,
        ranked_candidate_vessels=candidates,
        weights_applied={
            "timing": round(w_time, 2),
            "proximity": round(w_prox, 2),
            "trajectory": round(w_traj, 2),
            "drift_consistency": round(w_drift, 2)
        },
        total_vessels_evaluated=len(candidates)
    )
