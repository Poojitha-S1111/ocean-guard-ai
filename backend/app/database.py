import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).resolve().parent.parent / "oceanguard.db"

def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def get_db():
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Spills table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS spill_detections (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            detection_time TEXT NOT NULL,
            area_sq_km REAL NOT NULL,
            perimeter_km REAL NOT NULL,
            classification TEXT NOT NULL,
            confidence_score REAL NOT NULL,
            source_image_name TEXT,
            image_path TEXT,
            overlay_image_path TEXT,
            polygon_geojson TEXT,
            features_json TEXT,
            wind_speed_knots REAL DEFAULT 12.0,
            wind_direction_deg REAL DEFAULT 225.0,
            current_speed_knots REAL DEFAULT 0.8,
            current_direction_deg REAL DEFAULT 65.0,
            status TEXT DEFAULT 'investigating',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 2. Historical incidents table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS historical_incidents (
            id TEXT PRIMARY KEY,
            incident_date TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            spill_type TEXT NOT NULL,
            volume_m3 REAL,
            source_description TEXT,
            responsible_vessel TEXT,
            verified INTEGER DEFAULT 1,
            similarity_notes TEXT
        );
        """)

        # 3. AIS Vessels table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ais_vessels (
            mmsi INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            vessel_type TEXT NOT NULL,
            flag TEXT,
            imo INTEGER,
            length REAL,
            draft REAL,
            destination TEXT
        );
        """)

        # 4. AIS Track points table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ais_track_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mmsi INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            speed_knots REAL NOT NULL,
            course_deg REAL NOT NULL,
            status TEXT,
            FOREIGN KEY (mmsi) REFERENCES ais_vessels (mmsi)
        );
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_track_mmsi_time ON ais_track_points(mmsi, timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_spills_time ON spill_detections(detection_time);")
