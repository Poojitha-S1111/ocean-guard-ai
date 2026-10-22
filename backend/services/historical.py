import json
import math
from datetime import datetime
from fastapi import HTTPException
from app.database import get_db
from app.schemas import SpillHistoryResponse, HistoricalIncidentItem

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great-circle distance between two GPS coordinates in kilometers.
    """
    R = 6371.0 # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)

def analyze_spill_history(spill_id: str) -> SpillHistoryResponse:
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Fetch current spill
        cursor.execute("""
            SELECT id, name, latitude, longitude, detection_time, area_sq_km,
                   classification, confidence_score, status, notes
            FROM spill_detections
            WHERE id = ?;
        """, (spill_id,))
        spill = cursor.fetchone()
        if not spill:
            raise HTTPException(status_code=404, detail=f"Spill '{spill_id}' not found.")
        
        spill_lat = spill["latitude"]
        spill_lon = spill["longitude"]
        
        # 2. Fetch all historical incidents
        cursor.execute("""
            SELECT id, incident_date, latitude, longitude, spill_type, volume_m3,
                   source_description, responsible_vessel, verified, similarity_notes
            FROM historical_incidents;
        """)
        historical_rows = cursor.fetchall()
        
        nearby_incidents = []
        verified_count_nearby = 0
        
        for h in historical_rows:
            dist = haversine_distance_km(spill_lat, spill_lon, h["latitude"], h["longitude"])
            
            # Compute heuristic similarity score (0.0 to 1.0)
            # Higher if closer in distance and similar classification
            dist_factor = max(0.0, 1.0 - (dist / 60.0)) # decays to 0 at 60 km
            
            is_both_hydrocarbon = ("Oil" in h["spill_type"] or "Fuel" in h["spill_type"] or "Bilge" in h["spill_type"]) and (spill["classification"] == "likely_oil_spill")
            is_both_natural = ("Natural" in h["spill_type"] or "Biogenic" in h["spill_type"]) and (spill["classification"] == "natural_lookalike")
            
            type_factor = 0.9 if (is_both_hydrocarbon or is_both_natural) else 0.4
            similarity = round(0.6 * dist_factor + 0.4 * type_factor, 2)
            
            if dist <= 30.0 and h["verified"] == 1:
                verified_count_nearby += 1
                
            nearby_incidents.append(HistoricalIncidentItem(
                id=h["id"],
                incident_date=h["incident_date"],
                latitude=h["latitude"],
                longitude=h["longitude"],
                distance_km=dist,
                spill_type=h["spill_type"],
                volume_m3=h["volume_m3"],
                source_description=h["source_description"],
                responsible_vessel=h["responsible_vessel"],
                verified=bool(h["verified"]),
                similarity_score=similarity,
                similarity_notes=h["similarity_notes"]
            ))
            
        # Sort by distance
        nearby_incidents = sorted(nearby_incidents, key=lambda x: x.distance_km)
        
        # Risk assessment
        if verified_count_nearby >= 2:
            risk_level = f"High Chronic Risk Corridor: {verified_count_nearby} verified illegal discharges previously recorded within 30 km in this shipping corridor."
        elif verified_count_nearby == 1:
            risk_level = "Moderate Recurrence Risk: 1 verified prior discharge on file within 30 km."
        else:
            risk_level = "Low Historical Recurrence: No recent verified spills on record within immediate 30 km radius."
            
        # Timeline events
        timeline = [
            {
                "timestamp": spill["detection_time"],
                "event": "Current SAR Satellite Acquisition",
                "details": f"Sentinel-1 SAR observation captured dark patch '{spill['name']}' ({spill['area_sq_km']} km2, confidence {int(spill['confidence_score']*100)}%).",
                "badge": "SAR Detection"
            }
        ]
        
        for inc in nearby_incidents[:3]:
            timeline.append({
                "timestamp": inc.incident_date,
                "event": f"Historical Event: {inc.spill_type}",
                "details": f"{inc.source_description} ({inc.distance_km} km away, similarity: {int(inc.similarity_score * 100)}%).",
                "badge": "Historical Record"
            })
            
        timeline = sorted(timeline, key=lambda x: x["timestamp"], reverse=True)
        
        return SpillHistoryResponse(
            spill_id=spill["id"],
            spill_name=spill["name"],
            spill_location={"latitude": spill_lat, "longitude": spill_lon},
            spill_time=spill["detection_time"],
            nearby_historical_incidents=nearby_incidents,
            local_repeat_offense_risk=risk_level,
            timeline_events=timeline
        )
