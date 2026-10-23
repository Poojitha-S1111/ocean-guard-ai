import json
import math
from datetime import datetime, timedelta
from app.database import get_db, init_db

def create_spill_polygon(center_lat, center_lon, radius_km, num_points=16, elongation=1.8, angle_deg=45.0):
    """
    Creates a realistic organic-looking spill polygon (GeoJSON coordinates).
    """
    angle_rad = math.radians(angle_deg)
    coords = []
    for i in range(num_points):
        theta = 2.0 * math.pi * i / num_points
        # introduce slight organic variation
        r = radius_km * (1.0 + 0.18 * math.sin(3 * theta) - 0.12 * math.cos(2 * theta))
        # stretch along major axis
        x = r * math.cos(theta) * elongation
        y = r * math.sin(theta)
        
        # rotate
        rot_x = x * math.cos(angle_rad) - y * math.sin(angle_rad)
        rot_y = x * math.sin(angle_rad) + y * math.cos(angle_rad)
        
        # convert km offset to lat/lon (1 deg lat approx 111 km, 1 deg lon approx 111 * cos(lat) km)
        dlat = rot_y / 111.0
        dlon = rot_x / (111.0 * math.cos(math.radians(center_lat)))
        coords.append([round(center_lat + dlat, 5), round(center_lon + dlon, 5)])
    
    # close the ring
    coords.append(coords[0])
    return coords

def seed_database():
    print("Initializing OceanGuard AI SQLite database...")
    init_db()

    with get_db() as conn:
        cursor = conn.cursor()

        # Clear existing tables for a clean seed
        cursor.execute("DELETE FROM spill_detections;")
        cursor.execute("DELETE FROM historical_incidents;")
        cursor.execute("DELETE FROM ais_vessels;")
        cursor.execute("DELETE FROM ais_track_points;")

        # -------------------------------------------------------------
        # 1. Spill Detections (Sample data for demonstration)
        # -------------------------------------------------------------
        spills = [
            {
                "id": "SPILL-2026-081",
                "name": "Dover Strait West Slick [Sample Demo]",
                "latitude": 50.450,
                "longitude": 0.650,
                "detection_time": "2026-10-22T08:30:00Z",
                "area_sq_km": 14.2,
                "perimeter_km": 26.8,
                "classification": "likely_oil_spill",
                "confidence_score": 0.92,
                "source_image_name": "sar_dover_pass_081.png",
                "image_path": "/data/sample_images/sar_dover_pass_081.png",
                "overlay_image_path": "/data/sample_images/sar_dover_pass_081_overlay.png",
                "polygon_geojson": json.dumps({
                    "type": "Polygon",
                    "coordinates": [create_spill_polygon(50.450, 0.650, 1.4, elongation=2.2, angle_deg=55.0)]
                }),
                "features_json": json.dumps({
                    "area_pixels": 4520,
                    "perimeter_pixels": 820,
                    "elongation": 2.45,
                    "compactness": 0.38,
                    "mean_intensity": 38.2,
                    "surrounding_contrast": 68.4,
                    "texture_homogeneity": 0.78,
                    "texture_contrast": 18.2,
                    "texture_energy": 0.31
                }),
                "wind_speed_knots": 14.5,
                "wind_direction_deg": 220.0,
                "current_speed_knots": 0.9,
                "current_direction_deg": 65.0,
                "status": "investigating",
                "notes": "Sample data for demonstration. Dark patch exhibiting high damping ratio and sharp edge gradients typical of heavy fuel/crude slick."
            },
            {
                "id": "SPILL-2026-082",
                "name": "Calais Approach Elongated Discharge [Sample Demo]",
                "latitude": 50.720,
                "longitude": 1.450,
                "detection_time": "2026-10-22T12:15:00Z",
                "area_sq_km": 8.7,
                "perimeter_km": 19.4,
                "classification": "likely_oil_spill",
                "confidence_score": 0.88,
                "source_image_name": "sar_calais_pass_082.png",
                "image_path": "/data/sample_images/sar_calais_pass_082.png",
                "overlay_image_path": "/data/sample_images/sar_calais_pass_082_overlay.png",
                "polygon_geojson": json.dumps({
                    "type": "Polygon",
                    "coordinates": [create_spill_polygon(50.720, 1.450, 1.0, elongation=3.1, angle_deg=35.0)]
                }),
                "features_json": json.dumps({
                    "area_pixels": 2980,
                    "perimeter_pixels": 610,
                    "elongation": 3.12,
                    "compactness": 0.29,
                    "mean_intensity": 42.1,
                    "surrounding_contrast": 61.5,
                    "texture_homogeneity": 0.72,
                    "texture_contrast": 22.0,
                    "texture_energy": 0.28
                }),
                "wind_speed_knots": 12.0,
                "wind_direction_deg": 210.0,
                "current_speed_knots": 1.1,
                "current_direction_deg": 70.0,
                "status": "investigating",
                "notes": "Sample data for demonstration. Linear trail aligned with outbound traffic separation lane."
            },
            {
                "id": "SPILL-2026-083",
                "name": "Beachy Head Low-Wind Lookalike [Sample Demo]",
                "latitude": 50.380,
                "longitude": 0.220,
                "detection_time": "2026-10-21T18:40:00Z",
                "area_sq_km": 22.4,
                "perimeter_km": 48.0,
                "classification": "natural_lookalike",
                "confidence_score": 0.84,
                "source_image_name": "sar_beachy_head_083.png",
                "image_path": "/data/sample_images/sar_beachy_head_083.png",
                "overlay_image_path": "/data/sample_images/sar_beachy_head_083_overlay.png",
                "polygon_geojson": json.dumps({
                    "type": "Polygon",
                    "coordinates": [create_spill_polygon(50.380, 0.220, 2.1, elongation=1.3, angle_deg=10.0)]
                }),
                "features_json": json.dumps({
                    "area_pixels": 7820,
                    "perimeter_pixels": 1420,
                    "elongation": 1.25,
                    "compactness": 0.49,
                    "mean_intensity": 55.4,
                    "surrounding_contrast": 24.1,
                    "texture_homogeneity": 0.52,
                    "texture_contrast": 39.5,
                    "texture_energy": 0.16
                }),
                "wind_speed_knots": 3.8,
                "wind_direction_deg": 180.0,
                "current_speed_knots": 0.4,
                "current_direction_deg": 85.0,
                "status": "archived",
                "notes": "Sample data for demonstration. Low wind calm zone / natural biogenic surfactants. Low backscatter contrast."
            },
            {
                "id": "SPILL-2026-084",
                "name": "Wight Passage Feathered Slick [Sample Demo]",
                "latitude": 50.510,
                "longitude": -0.450,
                "detection_time": "2026-10-20T14:10:00Z",
                "area_sq_km": 5.3,
                "perimeter_km": 14.1,
                "classification": "likely_oil_spill",
                "confidence_score": 0.79,
                "source_image_name": "sar_wight_pass_084.png",
                "image_path": "/data/sample_images/sar_wight_pass_084.png",
                "overlay_image_path": "/data/sample_images/sar_wight_pass_084_overlay.png",
                "polygon_geojson": json.dumps({
                    "type": "Polygon",
                    "coordinates": [create_spill_polygon(50.510, -0.450, 0.8, elongation=2.6, angle_deg=60.0)]
                }),
                "features_json": json.dumps({
                    "area_pixels": 1840,
                    "perimeter_pixels": 450,
                    "elongation": 2.58,
                    "compactness": 0.33,
                    "mean_intensity": 41.5,
                    "surrounding_contrast": 58.0,
                    "texture_homogeneity": 0.71,
                    "texture_contrast": 24.3,
                    "texture_energy": 0.27
                }),
                "wind_speed_knots": 16.0,
                "wind_direction_deg": 240.0,
                "current_speed_knots": 0.7,
                "current_direction_deg": 60.0,
                "status": "verified",
                "notes": "Sample data for demonstration. Moderate weathering, confirmed bilge residue from coastal patrol."
            }
        ]

        for s in spills:
            cursor.execute("""
            INSERT INTO spill_detections (
                id, name, latitude, longitude, detection_time, area_sq_km, perimeter_km,
                classification, confidence_score, source_image_name, image_path,
                overlay_image_path, polygon_geojson, features_json, wind_speed_knots,
                wind_direction_deg, current_speed_knots, current_direction_deg, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                s["id"], s["name"], s["latitude"], s["longitude"], s["detection_time"],
                s["area_sq_km"], s["perimeter_km"], s["classification"], s["confidence_score"],
                s["source_image_name"], s["image_path"], s["overlay_image_path"],
                s["polygon_geojson"], s["features_json"], s["wind_speed_knots"],
                s["wind_direction_deg"], s["current_speed_knots"], s["current_direction_deg"],
                s["status"], s["notes"]
            ))

        # -------------------------------------------------------------
        # 2. Historical Incidents (Sample data for demonstration)
        # -------------------------------------------------------------
        historical = [
            ("HIST-2025-014", "2025-11-12T04:20:00Z", 50.480, 0.720, "Crude Oil", 35.0, "Tanker tank cleaning wash off Dover lanes", "MT Nordic Trader", 1, "High geographic correlation with SPILL-2026-081. Identical outbound shipping route."),
            ("HIST-2025-042", "2025-08-04T16:10:00Z", 50.390, 0.310, "Biogenic Sheen", 0.0, "Summer diatomaceous algal bloom recorded by aerial patrol", "N/A - Natural Phenomenon", 0, "Look-alike event in low wind zone (sub-3 knots), dampening micro-capillary waves."),
            ("HIST-2024-089", "2024-12-19T21:45:00Z", 50.740, 1.480, "Heavy Fuel Oil", 120.0, "Bunkering hose leakage off Cap Gris-Nez", "MV Atlantic Pioneer", 1, "Very similar spectral damping characteristics and contrast to SPILL-2026-082."),
            ("HIST-2024-031", "2024-05-15T09:00:00Z", 50.530, 0.580, "Bilge Discharge", 18.0, "Illegal night-time oily water separator bypass", "MV Baltic Trader", 1, "Persistent streak pattern detected in ERS-2 historical archives near Varne Sand."),
            ("HIST-2023-112", "2023-09-28T14:30:00Z", 50.620, 1.150, "Natural Look-alike", 0.0, "Freshwater internal tidal boundary slick", "N/A - Oceanographic Internal Wave", 0, "Distinct banded structure caused by tidal current shear rather than hydrocarbons.")
        ]
        cursor.executemany("""
        INSERT INTO historical_incidents (
            id, incident_date, latitude, longitude, spill_type, volume_m3,
            source_description, responsible_vessel, verified, similarity_notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, historical)

        # -------------------------------------------------------------
        # 3. AIS Vessels (Sample data for demonstration)
        # -------------------------------------------------------------
        vessels = [
            (219012345, "NORDIC MARINER", "Crude Oil Tanker", "Marshall Islands", 9781234, 274.0, 15.2, "Rotterdam"),
            (311000456, "CHEM PATRIOT", "Chemical Tanker", "Liberia", 9654321, 183.0, 11.0, "Antwerp"),
            (244123000, "ATLANTIC STAR", "Container Ship", "Netherlands", 9812456, 366.0, 14.5, "Hamburg"),
            (257991200, "BALTIC EXPLORER", "Bulk Carrier", "Norway", 9543120, 225.0, 12.8, "Dunkirk"),
            (356881000, "PACIFIC HORIZON", "Crude Oil Tanker", "Panama", 9487612, 330.0, 17.1, "Le Havre"),
            (636018900, "SEAWIND LEADER", "General Cargo", "Cyprus", 9387451, 140.0, 7.8, "Southampton"),
            (228990100, "CHANNEL EXPRESS", "Ro-Ro Ferry", "France", 9245123, 198.0, 6.5, "Dover"),
            (477123900, "OCEAN TITAN", "Product Tanker", "Hong Kong", 9723410, 210.0, 12.0, "Immingham"),
            (235112000, "NEPTUNE SHIELD", "Offshore Support", "United Kingdom", 9601122, 85.0, 5.5, "Portsmouth"),
            (211889000, "NORTH SEA PIONEER", "Fishing Vessel", "Germany", 8901234, 48.0, 4.2, "Brest")
        ]
        cursor.executemany("""
        INSERT INTO ais_vessels (mmsi, name, vessel_type, flag, imo, length, draft, destination)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, vessels)

        # -------------------------------------------------------------
        # 4. AIS Track Points (Sample data for demonstration)
        # Generated around SPILL-2026-081 (observed 2026-10-22T08:30:00Z at 50.450, 0.650)
        # Net drift with wind ~14.5kt @ 220, current 0.9kt @ 65 gives net drift ~0.8 kt towards ENE (approx 70 deg).
        # Backtracking 6-12 hours places estimated release area near (50.36 to 50.40, 0.40 to 0.52)
        # -------------------------------------------------------------
        base_time = datetime.fromisoformat("2026-10-22T08:30:00")
        
        # Track profiles
        # Vessel 1: NORDIC MARINER - passes straight through release area at approx T-8 hrs (00:30 UTC)
        # MMSI 219012345: outbound lane heading approx 065 deg, speed 12.5 kts
        points_data = []
        for step in range(-16, 8): # from T-16h to T+7h
            t = base_time + timedelta(hours=step)
            t_str = t.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # Nordic Mariner (prime candidate lead)
            # at step = -8 (00:30), lat=50.375, lon=0.485 (right inside backtracked source circle)
            lat_nm = 50.375 + (step + 8) * 0.052
            lon_nm = 0.485 + (step + 8) * 0.115
            points_data.append((219012345, t_str, round(lat_nm, 5), round(lon_nm, 5), 12.5, 65.0, "Underway Using Engine"))

            # Chem Patriot (secondary candidate: crosses 4.5 km south at T-6h)
            lat_cp = 50.320 + (step + 6) * 0.048
            lon_cp = 0.440 + (step + 6) * 0.110
            points_data.append((311000456, t_str, round(lat_cp, 5), round(lon_cp, 5), 11.2, 62.0, "Underway Using Engine"))

            # Atlantic Star (container ship - inbound opposing lane, 12 km north at T-9h)
            lat_as = 50.560 - (step + 9) * 0.060
            lon_as = 0.720 - (step + 9) * 0.125
            points_data.append((244123000, t_str, round(lat_as, 5), round(lon_as, 5), 18.4, 245.0, "Underway Using Engine"))

            # Baltic Explorer (bulk carrier - crossed area 14 hours prior, before estimated window)
            lat_be = 50.380 + (step + 14) * 0.045
            lon_be = 0.510 + (step + 14) * 0.095
            points_data.append((257991200, t_str, round(lat_be, 5), round(lon_be, 5), 10.8, 64.0, "Underway Using Engine"))

            # Pacific Horizon (tanker - passed 28 km offshore south)
            lat_ph = 50.180 + (step + 7) * 0.050
            lon_ph = 0.400 + (step + 7) * 0.120
            points_data.append((356881000, t_str, round(lat_ph, 5), round(lon_ph, 5), 13.0, 68.0, "Underway Using Engine"))

            # Seawind Leader (general cargo - coastal route near English coast)
            lat_sl = 50.620 + (step + 8) * 0.040
            lon_sl = 0.350 + (step + 8) * 0.100
            points_data.append((636018900, t_str, round(lat_sl, 5), round(lon_sl, 5), 9.5, 70.0, "Underway Using Engine"))

            # Channel Express (ferry crossing Dover-Calais transverse)
            ferry_cycle = (step % 4) / 4.0
            lat_ce = 50.850 - ferry_cycle * 0.25
            lon_ce = 1.300 + ferry_cycle * 0.40
            points_data.append((228990100, t_str, round(lat_ce, 5), round(lon_ce, 5), 21.0, 135.0, "Underway Using Engine"))

            # Ocean Titan (product tanker - entered channel much later at T-2h)
            lat_ot = 50.360 + (step + 2) * 0.054
            lon_ot = 0.470 + (step + 2) * 0.118
            points_data.append((477123900, t_str, round(lat_ot, 5), round(lon_ot, 5), 14.1, 66.0, "Underway Using Engine"))

            # Neptune Shield (support tug - stationary near coast)
            points_data.append((235112000, t_str, 50.680 + (step * 0.001), 0.220 + (step * 0.001), 1.2, 180.0, "Engaged in Towing"))

            # North Sea Pioneer (fishing vessel - zig-zag pattern outside shipping lane)
            lat_f = 50.280 + math.sin(step * 0.8) * 0.08
            lon_f = 0.620 + math.cos(step * 0.8) * 0.08
            points_data.append((211889000, t_str, round(lat_f, 5), round(lon_f, 5), 4.5, 45.0, "Engaged in Fishing"))

        cursor.executemany("""
        INSERT INTO ais_track_points (mmsi, timestamp, latitude, longitude, speed_knots, course_deg, status)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, points_data)

    print(f"Database seeded successfully with {len(spills)} sample spills, {len(historical)} historical incidents, {len(vessels)} vessels, and {len(points_data)} AIS track points.")

if __name__ == "__main__":
    seed_database()
