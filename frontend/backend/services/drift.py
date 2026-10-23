import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from app.schemas import DriftRequest, DriftResponse, DriftPoint

def meteorological_to_vector_knots(speed_knots: float, from_deg: float) -> Tuple[float, float]:
    """
    Converts meteorological wind (direction blowing FROM) to (u_east, v_north) components.
    Wind blows towards (from_deg + 180) % 360.
    """
    to_rad = math.radians((from_deg + 180.0) % 360.0)
    u_east = speed_knots * math.sin(to_rad)
    v_north = speed_knots * math.cos(to_rad)
    return u_east, v_north

def oceanographic_to_vector_knots(speed_knots: float, towards_deg: float) -> Tuple[float, float]:
    """
    Converts ocean current (direction flowing TOWARDS) to (u_east, v_north) components.
    """
    to_rad = math.radians(towards_deg % 360.0)
    u_east = speed_knots * math.sin(to_rad)
    v_north = speed_knots * math.cos(to_rad)
    return u_east, v_north

def create_circle_polygon(center_lat: float, center_lon: float, radius_km: float, num_points: int = 32) -> List[List[float]]:
    coords = []
    for i in range(num_points):
        angle = 2.0 * math.pi * i / num_points
        d_north_km = radius_km * math.cos(angle)
        d_east_km = radius_km * math.sin(angle)
        
        lat = center_lat + (d_north_km / 111.139)
        lon = center_lon + (d_east_km / (111.139 * math.cos(math.radians(center_lat))))
        coords.append([round(lon, 5), round(lat, 5)]) # GeoJSON standard is [lon, lat]
    coords.append(coords[0]) # close polygon
    return coords

def compute_drift_backtrack(req: DriftRequest) -> DriftResponse:
    # 1. Parse observation time
    obs_time_clean = req.observation_time.replace("Z", "+00:00")
    try:
        obs_dt = datetime.fromisoformat(obs_time_clean)
    except Exception:
        obs_dt = datetime.utcnow()
        
    # 2. Decompose wind & current
    u_wind, v_wind = meteorological_to_vector_knots(req.wind_speed_knots, req.wind_direction_deg)
    u_curr, v_curr = oceanographic_to_vector_knots(req.current_speed_knots, req.current_direction_deg)
    
    # 3. Standard Drift Approximation: Drift = Current + ~3% Wind
    wind_factor = 0.03
    u_drift = u_curr + (wind_factor * u_wind)
    v_drift = v_curr + (wind_factor * v_wind)
    
    net_speed_knots = math.sqrt(u_drift ** 2 + v_drift ** 2)
    net_dir_rad = math.atan2(u_drift, v_drift)
    net_direction_deg = (math.degrees(net_dir_rad) + 360.0) % 360.0
    
    # Speed in km/h (1 knot = 1.852 km/h)
    u_drift_kmh = u_drift * 1.852
    v_drift_kmh = v_drift * 1.852
    
    # 4. Backtrack trajectory
    # For backtracking, velocity is reversed (-u, -v)
    drift_points: List[DriftPoint] = []
    
    # Initial point (T = 0)
    current_lat = req.latitude
    current_lon = req.longitude
    init_radius_km = 0.6
    
    drift_points.append(DriftPoint(
        hours_back=0.0,
        timestamp=obs_dt.isoformat().replace("+00:00", "Z"),
        latitude=round(current_lat, 5),
        longitude=round(current_lon, 5),
        uncertainty_radius_km=round(init_radius_km, 2)
    ))
    
    total_hours = int(req.backtrack_hours)
    step_hours = 1.0
    
    # GeoJSON coordinates for drift path LineString ([lon, lat])
    linestring_coords = [[round(current_lon, 5), round(current_lat, 5)]]
    
    km_per_deg_lat = 111.139
    
    for h in range(1, total_hours + 1):
        dt_step = obs_dt - timedelta(hours=h)
        
        # Step backwards
        delta_north_km = -v_drift_kmh * step_hours
        delta_east_km = -u_drift_kmh * step_hours
        
        current_lat += (delta_north_km / km_per_deg_lat)
        current_lon += (delta_east_km / (km_per_deg_lat * math.cos(math.radians(current_lat))))
        
        # Uncertainty grows over backtrack time
        uncert_radius = init_radius_km + (h * req.uncertainty_growth_rate_km_per_hr)
        
        drift_points.append(DriftPoint(
            hours_back=float(h),
            timestamp=dt_step.isoformat().replace("+00:00", "Z"),
            latitude=round(current_lat, 5),
            longitude=round(current_lon, 5),
            uncertainty_radius_km=round(uncert_radius, 2)
        ))
        
        linestring_coords.append([round(current_lon, 5), round(current_lat, 5)])

    # Source region is centered at the maximum backtrack point
    source_center = {"latitude": round(current_lat, 5), "longitude": round(current_lon, 5)}
    source_radius = round(drift_points[-1].uncertainty_radius_km, 2)
    source_polygon_coords = create_circle_polygon(current_lat, current_lon, source_radius)
    
    # Release window: typically estimated between (backtrack_hours * 0.5) to (backtrack_hours * 1.0)
    release_earliest = (obs_dt - timedelta(hours=total_hours)).isoformat().replace("+00:00", "Z")
    release_latest = (obs_dt - timedelta(hours=max(1, total_hours // 2))).isoformat().replace("+00:00", "Z")
    
    # Build complete GeoJSON FeatureCollection
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "Drift Backtrack Path",
                    "type": "drift_path",
                    "net_speed_knots": round(net_speed_knots, 2),
                    "net_direction_deg": round(net_direction_deg, 1)
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": linestring_coords
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "name": "Estimated Source Region",
                    "type": "source_region",
                    "radius_km": source_radius,
                    "release_window": f"{release_earliest} to {release_latest}"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [source_polygon_coords]
                }
            }
        ]
    }
    
    # Add waypoint points
    for pt in drift_points:
        geojson["features"].append({
            "type": "Feature",
            "properties": {
                "name": f"Backtrack T-{int(pt.hours_back)}h",
                "type": "drift_waypoint",
                "hours_back": pt.hours_back,
                "timestamp": pt.timestamp,
                "uncertainty_km": pt.uncertainty_radius_km
            },
            "geometry": {
                "type": "Point",
                "coordinates": [pt.longitude, pt.latitude]
            }
        })

    return DriftResponse(
        spill_latitude=req.latitude,
        spill_longitude=req.longitude,
        observation_time=req.observation_time,
        backtrack_hours=req.backtrack_hours,
        net_drift_speed_knots=round(net_speed_knots, 2),
        net_drift_direction_deg=round(net_direction_deg, 1),
        drift_path=drift_points,
        source_region_center=source_center,
        source_region_radius_km=source_radius,
        estimated_release_window={
            "earliest": release_earliest,
            "latest": release_latest
        },
        geojson=geojson
    )
