from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_endpoints():
    print("Testing OceanGuard AI API Endpoints...")
    
    # 1. Health check
    r1 = client.get("/api/health")
    assert r1.status_code == 200, f"Health failed: {r1.text}"
    print("[PASS] 1. Health Check:", r1.json()["status"])

    # 2. Spills list
    r2 = client.get("/api/spills")
    assert r2.status_code == 200
    spills = r2.json()
    assert len(spills) >= 4
    first_id = spills[0]["id"]
    print(f"[PASS] 2. Spills List ({len(spills)} detections loaded, latest: {first_id})")

    # 3. Spill History
    r3 = client.get(f"/api/spills/{first_id}/history")
    assert r3.status_code == 200
    hist = r3.json()
    assert len(hist["nearby_historical_incidents"]) > 0
    print(f"[PASS] 3. Spill History: {len(hist['nearby_historical_incidents'])} nearby historical incidents, risk='{hist['local_repeat_offense_risk'][:30]}...'")

    # 4. Drift Estimation
    drift_payload = {
        "latitude": 50.450,
        "longitude": 0.650,
        "observation_time": "2026-10-22T08:30:00Z",
        "backtrack_hours": 10.0,
        "wind_speed_knots": 14.5,
        "wind_direction_deg": 220.0,
        "current_speed_knots": 0.9,
        "current_direction_deg": 65.0
    }
    r4 = client.post("/api/drift", json=drift_payload)
    assert r4.status_code == 200
    drift_data = r4.json()
    print(f"[PASS] 4. Drift Estimation: Net speed={drift_data['net_drift_speed_knots']} kts, Backtrack Points={len(drift_data['drift_path'])}, Source Radius={drift_data['source_region_radius_km']} km")

    # 5. Vessel Ranking
    vessel_payload = {
        "spill_id": first_id,
        "source_lat": drift_data["source_region_center"]["latitude"],
        "source_lon": drift_data["source_region_center"]["longitude"],
        "source_radius_km": drift_data["source_region_radius_km"],
        "release_window_start": drift_data["estimated_release_window"]["earliest"],
        "release_window_end": drift_data["estimated_release_window"]["latest"],
        "drift_path_points": [{"latitude": p["latitude"], "longitude": p["longitude"]} for p in drift_data["drift_path"]],
        "weights": {"timing": 0.25, "proximity": 0.25, "trajectory": 0.25, "drift_consistency": 0.25}
    }
    r5 = client.post("/api/rank-vessels", json=vessel_payload)
    assert r5.status_code == 200
    v_data = r5.json()
    top_vessel = v_data["ranked_candidate_vessels"][0]
    print(f"[PASS] 5. Candidate Vessel Ranking: Evaluated {v_data['total_vessels_evaluated']} vessels. Top candidate: '{top_vessel['name']}' ({top_vessel['vessel_type']}) with score {top_vessel['overall_score']:.2f}")

    # 6. Feature Validation
    val_payload = {
        "patch_id": 1,
        "features": {
            "area_pixels": 4500,
            "perimeter_pixels": 820,
            "elongation": 3.1,
            "compactness": 0.35,
            "mean_intensity": 36.0,
            "surrounding_contrast": 72.0,
            "texture_homogeneity": 0.81,
            "texture_contrast": 16.0,
            "texture_energy": 0.34
        }
    }
    r6 = client.post("/api/validate", json=val_payload)
    assert r6.status_code == 200
    val_res = r6.json()
    print(f"[PASS] 6. Feature Validation: Classified as '{val_res['classification']}' (Confidence: {val_res['confidence_score']*100:.1f}%)")

    print("\nALL 6 BACKEND MODULE TEST SUITES PASSED PERFECTLY!\n")

if __name__ == "__main__":
    test_endpoints()
