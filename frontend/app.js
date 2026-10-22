// OceanGuard AI – Marine Pollution Monitoring & Investigation System
// Frontend Client Application

const API_BASE = window.location.origin;

// State
let allSpills = [];
let currentSpill = null;
let currentDriftData = null;
let currentVesselData = null;
let currentHistoryData = null;
let highlightedMmsi = null;

// Map & Layers
let map = null;
let spillLayerGroup = null;
let driftLayerGroup = null;
let sourceLayerGroup = null;
let vesselLayerGroup = null;

// Time Slider & Animation
let animationInterval = null;
let isPlaying = false;
let currentSliderStep = 0; // T-0 is 0

// Initialize upon DOM load
document.addEventListener("DOMContentLoaded", () => {
  initMap();
  initTabs();
  initTimeSlider();
  initUploadModal();
  initEventListeners();
  loadSpillDetections();
});

// -----------------------------------------------------------------
// 1. Map Initialization
// -----------------------------------------------------------------
function initMap() {
  // Center near Dover Strait / English Channel
  map = L.map("leaflet-map", {
    zoomControl: true,
    attributionControl: true
  }).setView([50.50, 0.70], 10);

  // High-tech dark CartoDB basemap
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    subdomains: "abcd",
    maxZoom: 18
  }).addTo(map);

  // Initialize Layer Groups
  spillLayerGroup = L.layerGroup().addTo(map);
  driftLayerGroup = L.layerGroup().addTo(map);
  sourceLayerGroup = L.layerGroup().addTo(map);
  vesselLayerGroup = L.layerGroup().addTo(map);

  // Layer Visibility Toggles
  document.getElementById("chk-layer-spills").addEventListener("change", (e) => {
    e.target.checked ? map.addLayer(spillLayerGroup) : map.removeLayer(spillLayerGroup);
  });
  document.getElementById("chk-layer-drift").addEventListener("change", (e) => {
    e.target.checked ? map.addLayer(driftLayerGroup) : map.removeLayer(driftLayerGroup);
  });
  document.getElementById("chk-layer-source").addEventListener("change", (e) => {
    e.target.checked ? map.addLayer(sourceLayerGroup) : map.removeLayer(sourceLayerGroup);
  });
  document.getElementById("chk-layer-vessels").addEventListener("change", (e) => {
    e.target.checked ? map.addLayer(vesselLayerGroup) : map.removeLayer(vesselLayerGroup);
  });
}

// -----------------------------------------------------------------
// 2. Load Spill Detections from API
// -----------------------------------------------------------------
async function loadSpillDetections(selectId = null) {
  const container = document.getElementById("spill-list-container");
  container.innerHTML = `<div class="loading-state">Loading spill detections from SQLite...</div>`;

  try {
    const res = await fetch(`${API_BASE}/api/spills`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    allSpills = await res.json();

    document.getElementById("spill-count").innerText = allSpills.length;
    renderSpillList(allSpills);

    // Auto-select first spill or requested spill
    if (allSpills.length > 0) {
      const target = selectId ? allSpills.find(s => s.id === selectId) || allSpills[0] : allSpills[0];
      selectSpill(target.id);
    } else {
      container.innerHTML = `<div class="empty-state">No spill detections recorded in database.</div>`;
    }
  } catch (err) {
    console.error("Failed to load spills:", err);
    container.innerHTML = `<div class="empty-state" style="color:#ff6b81">Error connecting to OceanGuard API: ${err.message}</div>`;
  }
}

function renderSpillList(spills) {
  const container = document.getElementById("spill-list-container");
  if (!spills.length) {
    container.innerHTML = `<div class="empty-state">No matching spill detections.</div>`;
    return;
  }

  container.innerHTML = spills.map(s => {
    const isOil = s.classification === "likely_oil_spill";
    const badgeClass = isOil ? "badge-likely_oil_spill" : "badge-natural_lookalike";
    const badgeText = isOil ? "Likely Oil Spill" : "Natural Look-alike";
    const confPercent = Math.round(s.confidence_score * 100);

    return `
      <div class="spill-card ${currentSpill && currentSpill.id === s.id ? 'active' : ''}" 
           id="card-${s.id}" onclick="selectSpill('${s.id}')">
        <div class="spill-card-head">
          <span class="spill-id">${s.id}</span>
          <span class="badge-classification ${badgeClass}">${badgeText} (${confPercent}%)</span>
        </div>
        <div class="spill-name">${s.name}</div>
        <div class="spill-meta-grid">
          <div>Area: <span class="spill-meta-val">${s.area_sq_km} km²</span></div>
          <div>Confidence: <span class="spill-meta-val">${confPercent}%</span></div>
          <div>Lat/Lon: <span class="spill-meta-val">${s.latitude.toFixed(3)}, ${s.longitude.toFixed(3)}</span></div>
          <div>Status: <span class="spill-meta-val">${s.status}</span></div>
        </div>
      </div>
    `;
  }).join("");
}

// -----------------------------------------------------------------
// 3. Select & Investigate Spill
// -----------------------------------------------------------------
async function selectSpill(spillId) {
  const spill = allSpills.find(s => s.id === spillId);
  if (!spill) return;

  currentSpill = spill;
  highlightedMmsi = null;

  // Highlight card in left sidebar
  document.querySelectorAll(".spill-card").forEach(c => c.classList.remove("active"));
  const activeCard = document.getElementById(`card-${spill.id}`);
  if (activeCard) activeCard.classList.add("active");

  document.getElementById("map-active-badge").innerHTML = 
    `Investigating: <strong>${spill.id}</strong> (${spill.classification === 'likely_oil_spill' ? 'Likely Slick' : 'Look-alike'})`;

  // Fly to spill on map
  map.flyTo([spill.latitude, spill.longitude], 11, { duration: 1.2 });

  // 1. Draw Spill Polygon
  renderSpillOnMap(spill);

  // 2. Fetch and render Hydrodynamic Drift
  await loadAndRenderDrift(spill);

  // 3. Fetch and render Candidate Vessels
  await loadAndRenderVessels(spill);

  // 4. Fetch and render Historical Log
  await loadAndRenderHistory(spill.id);

  // 5. Update Overview Details Tab
  renderOverviewTab(spill);
}

function renderSpillOnMap(spill) {
  spillLayerGroup.clearLayers();

  const isOil = spill.classification === "likely_oil_spill";
  const polyColor = isOil ? "#ff4757" : "#2ed573";
  const fillColor = isOil ? "#ff6b81" : "#7bed9f";

  if (spill.polygon_geojson && spill.polygon_geojson.coordinates) {
    const rawCoords = spill.polygon_geojson.coordinates[0];
    // GeoJSON is [lon, lat] or [lat, lon]; detect format
    const latLngs = rawCoords.map(pt => {
      if (Math.abs(pt[0]) > Math.abs(pt[1])) return [pt[1], pt[0]];
      return [pt[0], pt[1]];
    });

    const polygon = L.polygon(latLngs, {
      color: polyColor,
      weight: 2,
      fillColor: fillColor,
      fillOpacity: 0.45,
      dashArray: isOil ? null : "4, 4"
    }).addTo(spillLayerGroup);

    polygon.bindPopup(`
      <div style="font-family:var(--font-sans); color:#0f172a; min-width:180px;">
        <strong style="color:${polyColor}; font-size:1rem;">${spill.id}</strong><br>
        <strong>${spill.name}</strong><br>
        Classification: <strong>${spill.classification}</strong><br>
        Confidence: <strong>${Math.round(spill.confidence_score * 100)}%</strong><br>
        Area: <strong>${spill.area_sq_km} km²</strong><br>
        Observed: <strong>${spill.detection_time}</strong>
      </div>
    `);
  } else {
    // Fallback circular marker
    L.circle([spill.latitude, spill.longitude], {
      radius: Math.sqrt(spill.area_sq_km / Math.PI) * 1000,
      color: polyColor,
      fillColor: fillColor,
      fillOpacity: 0.4
    }).addTo(spillLayerGroup);
  }
}

// -----------------------------------------------------------------
// 4. Hydrodynamic Drift Estimation Call
// -----------------------------------------------------------------
async function loadAndRenderDrift(spill) {
  driftLayerGroup.clearLayers();
  sourceLayerGroup.clearLayers();

  const payload = {
    spill_id: spill.id,
    latitude: spill.latitude,
    longitude: spill.longitude,
    observation_time: spill.detection_time,
    backtrack_hours: 12.0,
    wind_speed_knots: spill.wind_speed_knots || 14.0,
    wind_direction_deg: spill.wind_direction_deg || 220.0,
    current_speed_knots: spill.current_speed_knots || 0.8,
    current_direction_deg: spill.current_direction_deg || 65.0
  };

  try {
    const res = await fetch(`${API_BASE}/api/drift`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`Drift API error ${res.status}`);
    currentDriftData = await res.json();

    // 1. Draw Backtrack Trajectory Line
    const pathCoords = currentDriftData.drift_path.map(pt => [pt.latitude, pt.longitude]);
    L.polyline(pathCoords, {
      color: "#00f2fe",
      weight: 3,
      dashArray: "6, 8",
      opacity: 0.9
    }).addTo(driftLayerGroup);

    // 2. Draw Waypoints
    currentDriftData.drift_path.forEach((pt, idx) => {
      if (idx === 0) return; // skip T-0 (spill center)
      const marker = L.circleMarker([pt.latitude, pt.longitude], {
        radius: 4,
        fillColor: "#00f2fe",
        color: "#ffffff",
        weight: 1,
        fillOpacity: 0.9
      }).addTo(driftLayerGroup);

      marker.bindPopup(`
        <div style="font-family:var(--font-sans); color:#0f172a;">
          <strong>Backtrack Horizon: T-${pt.hours_back}h</strong><br>
          Timestamp: ${pt.timestamp}<br>
          Uncertainty Radius: ±${pt.uncertainty_radius_km} km
        </div>
      `);
    });

    // 3. Draw Expanding Source Region
    const srcCenter = currentDriftData.source_region_center;
    const srcRadius = currentDriftData.source_region_radius_km;

    const sourceCircle = L.circle([srcCenter.latitude, srcCenter.longitude], {
      radius: srcRadius * 1000, // convert km to meters
      color: "#ffaa00",
      fillColor: "#ffaa00",
      fillOpacity: 0.22,
      dashArray: "6, 6",
      weight: 2
    }).addTo(sourceLayerGroup);

    sourceCircle.bindPopup(`
      <div style="font-family:var(--font-sans); color:#0f172a;">
        <strong style="color:#d97706">Estimated Source Region</strong><br>
        Search Radius: <strong>±${srcRadius} km</strong><br>
        Center: ${srcCenter.latitude.toFixed(4)}°N, ${srcCenter.longitude.toFixed(4)}°E<br>
        Estimated Release Window:<br>
        <strong>${currentDriftData.estimated_release_window.earliest.slice(11, 16)} to ${currentDriftData.estimated_release_window.latest.slice(11, 16)} UTC</strong><br>
        <em style="font-size:0.75rem; color:#64748b;">Decision-support search envelope</em>
      </div>
    `);

    // Render Drift Tab
    renderDriftTab(currentDriftData, spill);

  } catch (err) {
    console.error("Drift calculation failed:", err);
  }
}

// -----------------------------------------------------------------
// 5. Candidate Vessel Ranking Call
// -----------------------------------------------------------------
async function loadAndRenderVessels(spill) {
  vesselLayerGroup.clearLayers();

  if (!currentDriftData) return;

  const payload = {
    spill_id: spill.id,
    source_lat: currentDriftData.source_region_center.latitude,
    source_lon: currentDriftData.source_region_center.longitude,
    source_radius_km: currentDriftData.source_region_radius_km,
    release_window_start: currentDriftData.estimated_release_window.earliest,
    release_window_end: currentDriftData.estimated_release_window.latest,
    drift_path_points: currentDriftData.drift_path.map(p => ({ latitude: p.latitude, longitude: p.longitude })),
    weights: { timing: 0.25, proximity: 0.25, trajectory: 0.25, drift_consistency: 0.25 }
  };

  try {
    const res = await fetch(`${API_BASE}/api/rank-vessels`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`Vessel Ranking API error ${res.status}`);
    currentVesselData = await res.json();

    // Render Vessel Tracks on Map
    currentVesselData.ranked_candidate_vessels.forEach(v => {
      const isTopLead = v.is_high_interest;
      const lineColor = isTopLead ? "#ff4757" : (v.overall_score > 0.4 ? "#9b59b6" : "#64748b");
      const lineOpacity = isTopLead ? 0.9 : 0.4;
      const lineWeight = isTopLead ? 3 : 1.5;

      const poly = L.polyline(v.track_coordinates, {
        color: lineColor,
        opacity: lineOpacity,
        weight: lineWeight,
        dashArray: isTopLead ? null : "4, 4"
      }).addTo(vesselLayerGroup);

      poly.bindPopup(`
        <div style="font-family:var(--font-sans); color:#0f172a;">
          <strong>Candidate Vessel: ${v.name}</strong> (${v.vessel_type})<br>
          MMSI: ${v.mmsi} | Flag: ${v.flag}<br>
          Investigative Score: <strong>${Math.round(v.overall_score * 100)}%</strong><br>
          Min Dist to Source: <strong>${v.min_distance_to_source_km} km</strong><br>
          Closest Approach: <strong>${v.closest_approach_time}</strong><br>
          <em>Investigative lead only. Not proof of responsibility.</em>
        </div>
      `);

      // Current position marker at T-0
      if (v.track_coordinates.length > 0) {
        const lastPt = v.track_coordinates[v.track_coordinates.length - 1];
        const iconHtml = `<div class="vessel-icon-inner ${isTopLead ? 'high-interest' : ''}" id="vmarker-${v.mmsi}"></div>`;
        const customIcon = L.divIcon({
          className: "custom-vessel-marker",
          html: iconHtml,
          iconSize: [16, 16],
          iconAnchor: [8, 8]
        });

        const vMarker = L.marker(lastPt, { icon: customIcon }).addTo(vesselLayerGroup);
        vMarker.bindPopup(`<strong>${v.name}</strong><br>Lead Score: ${Math.round(v.overall_score * 100)}%`);
      }
    });

    // Render Vessels Tab
    renderVesselsTab(currentVesselData);

  } catch (err) {
    console.error("Vessel ranking failed:", err);
  }
}

// -----------------------------------------------------------------
// 6. Historical Correlation Call
// -----------------------------------------------------------------
async function loadAndRenderHistory(spillId) {
  try {
    const res = await fetch(`${API_BASE}/api/spills/${spillId}/history`);
    if (!res.ok) throw new Error(`History API error ${res.status}`);
    currentHistoryData = await res.json();

    renderHistoryTab(currentHistoryData);
  } catch (err) {
    console.error("Historical analysis failed:", err);
  }
}

// -----------------------------------------------------------------
// 7. Right Panel Tabs Rendering
// -----------------------------------------------------------------
function renderOverviewTab(spill) {
  const isOil = spill.classification === "likely_oil_spill";
  const confPercent = Math.round(spill.confidence_score * 100);
  const feat = spill.features_json || {};

  document.getElementById("pane-details").innerHTML = `
    <div class="detail-card">
      <div class="card-heading">
        <span>Identification & Classification</span>
        <span class="badge-classification ${isOil ? 'badge-likely_oil_spill' : 'badge-natural_lookalike'}">
          ${isOil ? 'Likely Oil Spill' : 'Natural Look-alike'}
        </span>
      </div>
      <div class="metric-row"><span class="metric-name">Detection ID:</span><span class="metric-val">${spill.id}</span></div>
      <div class="metric-row"><span class="metric-name">ML Validation Confidence:</span><span class="metric-val" style="color:var(--teal-primary)">${confPercent}%</span></div>
      <div class="metric-row"><span class="metric-name">Observation Timestamp:</span><span class="metric-val">${spill.detection_time}</span></div>
      <div class="metric-row"><span class="metric-name">Coordinates:</span><span class="metric-val">${spill.latitude.toFixed(4)}°N, ${spill.longitude.toFixed(4)}°E</span></div>
      <div class="metric-row"><span class="metric-name">Investigation Status:</span><span class="metric-val">${spill.status.toUpperCase()}</span></div>
    </div>

    <div class="detail-card">
      <div class="card-heading">Physical & Radar Morphology</div>
      <div class="metric-row"><span class="metric-name">Surface Area:</span><span class="metric-val">${spill.area_sq_km} km² (${feat.area_pixels || 'N/A'} px)</span></div>
      <div class="metric-row"><span class="metric-name">Perimeter:</span><span class="metric-val">${spill.perimeter_km} km</span></div>
      <div class="metric-row"><span class="metric-name">Elongation Ratio:</span><span class="metric-val">${feat.elongation || 'N/A'}x</span></div>
      <div class="metric-row"><span class="metric-name">Compactness (4πA/P²):</span><span class="metric-val">${feat.compactness || 'N/A'}</span></div>
      <div class="metric-row"><span class="metric-name">Mean Backscatter Intensity:</span><span class="metric-val">${feat.mean_intensity || 'N/A'}</span></div>
      <div class="metric-row"><span class="metric-name">Surrounding Ocean Contrast:</span><span class="metric-val">+${feat.surrounding_contrast || 'N/A'}</span></div>
    </div>

    <div class="detail-card">
      <div class="card-heading">Local Metocean Conditions</div>
      <div class="metric-row"><span class="metric-name">Surface Wind Speed:</span><span class="metric-val">${spill.wind_speed_knots} knots</span></div>
      <div class="metric-row"><span class="metric-name">Wind Direction (From):</span><span class="metric-val">${spill.wind_direction_deg}°</span></div>
      <div class="metric-row"><span class="metric-name">Ocean Current Velocity:</span><span class="metric-val">${spill.current_speed_knots} knots</span></div>
      <div class="metric-row"><span class="metric-name">Current Flow (Towards):</span><span class="metric-val">${spill.current_direction_deg}°</span></div>
    </div>

    <div class="detail-card">
      <div class="card-heading">Analyst Notes</div>
      <p style="font-size:0.78rem; color:var(--text-muted); line-height:1.5;">${spill.notes || 'No field notes entered.'}</p>
    </div>
  `;
}

function renderDriftTab(drift, spill) {
  let pane = document.getElementById("pane-drift");
  if (!pane) {
    pane = document.createElement("div");
    pane.className = "tab-pane";
    pane.id = "pane-drift";
    document.getElementById("tab-content-container").appendChild(pane);
  }

  pane.innerHTML = `
    <div class="detail-card">
      <div class="card-heading">Hydrodynamic Backtrack Vector</div>
      <div class="metric-row"><span class="metric-name">Net Drift Speed:</span><span class="metric-val" style="color:var(--teal-primary)">${drift.net_drift_speed_knots} knots</span></div>
      <div class="metric-row"><span class="metric-name">Net Drift Heading:</span><span class="metric-val">${drift.net_drift_direction_deg}°</span></div>
      <div class="metric-row"><span class="metric-name">Backtrack Duration:</span><span class="metric-val">${drift.backtrack_hours} hours</span></div>
      <div class="metric-row"><span class="metric-name">Physics Model:</span><span class="metric-val" style="font-size:0.7rem;">${drift.formula_used}</span></div>
    </div>

    <div class="detail-card">
      <div class="card-heading">Estimated Source Region (T-${drift.backtrack_hours}h)</div>
      <div class="metric-row"><span class="metric-name">Search Center:</span><span class="metric-val">${drift.source_region_center.latitude.toFixed(4)}°N, ${drift.source_region_center.longitude.toFixed(4)}°E</span></div>
      <div class="metric-row"><span class="metric-name">Search Radius:</span><span class="metric-val" style="color:#ffaa00">±${drift.source_region_radius_km} km</span></div>
      <div class="metric-row"><span class="metric-name">Release Window Earliest:</span><span class="metric-val">${drift.estimated_release_window.earliest.slice(11, 16)} UTC</span></div>
      <div class="metric-row"><span class="metric-name">Release Window Latest:</span><span class="metric-val">${drift.estimated_release_window.latest.slice(11, 16)} UTC</span></div>
    </div>

    <div class="detail-card">
      <div class="card-heading">Hourly Trajectory Waypoints</div>
      <div style="max-height:160px; overflow-y:auto; font-size:0.72rem;">
        ${drift.drift_path.map(p => `
          <div class="metric-row">
            <span class="metric-name">T-${p.hours_back}h (${p.timestamp.slice(11, 16)}Z)</span>
            <span class="metric-val">${p.latitude.toFixed(3)}N, ${p.longitude.toFixed(3)}E (±${p.uncertainty_radius_km}km)</span>
          </div>
        `).join("")}
      </div>
    </div>
  `;
}

function renderVesselsTab(vesselData) {
  let pane = document.getElementById("pane-vessels");
  if (!pane) {
    pane = document.createElement("div");
    pane.className = "tab-pane";
    pane.id = "pane-vessels";
    document.getElementById("tab-content-container").appendChild(pane);
  }

  const vessels = vesselData.ranked_candidate_vessels || [];

  pane.innerHTML = `
    <div style="font-size:0.76rem; color:var(--text-muted); margin-bottom:8px;">
      Evaluated <strong>${vesselData.total_vessels_evaluated} candidate vessels</strong>. Weights: 
      Timing (25%), Proximity (25%), Trajectory (25%), Drift Alignment (25%).
    </div>

    ${vessels.map(v => {
      const scoreInt = Math.round(v.overall_score * 100);
      const scoreClass = scoreInt >= 70 ? 'score-high' : (scoreInt >= 40 ? 'score-med' : 'score-low');
      const isSelected = highlightedMmsi === v.mmsi;

      return `
        <div class="vessel-card ${isSelected ? 'highlighted' : ''}" onclick="highlightVessel(${v.mmsi})">
          <div class="vessel-card-header">
            <div class="vessel-name-group">
              <span class="vessel-name">${v.name}</span>
              <span style="font-size:0.7rem; color:var(--text-dim);">(${v.vessel_type})</span>
            </div>
            <span class="overall-score-badge ${scoreClass}">${scoreInt}% Lead</span>
          </div>

          <div style="font-size:0.72rem; color:var(--text-muted); margin-bottom:6px;">
            MMSI: <strong>${v.mmsi}</strong> | Flag: <strong>${v.flag}</strong> | Closest: <strong>${v.min_distance_to_source_km} km</strong> @ ${v.closest_approach_time.slice(11, 16)} UTC
          </div>

          <div class="sub-score-bars">
            <div class="score-bar-group">
              <div class="score-bar-label"><span>Timing</span><span>${Math.round(v.sub_scores.timing * 100)}%</span></div>
              <div class="progress-track"><div class="progress-fill fill-timing" style="width:${v.sub_scores.timing * 100}%"></div></div>
            </div>
            <div class="score-bar-group">
              <div class="score-bar-label"><span>Proximity</span><span>${Math.round(v.sub_scores.proximity * 100)}%</span></div>
              <div class="progress-track"><div class="progress-fill fill-proximity" style="width:${v.sub_scores.proximity * 100}%"></div></div>
            </div>
            <div class="score-bar-group">
              <div class="score-bar-label"><span>Trajectory</span><span>${Math.round(v.sub_scores.trajectory * 100)}%</span></div>
              <div class="progress-track"><div class="progress-fill fill-trajectory" style="width:${v.sub_scores.trajectory * 100}%"></div></div>
            </div>
            <div class="score-bar-group">
              <div class="score-bar-label"><span>Drift Align</span><span>${Math.round(v.sub_scores.drift_consistency * 100)}%</span></div>
              <div class="progress-track"><div class="progress-fill fill-drift" style="width:${v.sub_scores.drift_consistency * 100}%"></div></div>
            </div>
          </div>

          <div class="vessel-assessment">${v.candidate_assessment}</div>
        </div>
      `;
    }).join("")}
  `;
}

function renderHistoryTab(historyData) {
  let pane = document.getElementById("pane-history");
  if (!pane) {
    pane = document.createElement("div");
    pane.className = "tab-pane";
    pane.id = "pane-history";
    document.getElementById("tab-content-container").appendChild(pane);
  }

  const timeline = historyData.timeline_events || [];
  const nearby = historyData.nearby_historical_incidents || [];

  pane.innerHTML = `
    <div class="detail-card">
      <div class="card-heading">Chronic Recurrence Assessment</div>
      <p style="font-size:0.78rem; color:#ffc048; line-height:1.5;">${historyData.local_repeat_offense_risk}</p>
    </div>

    <div class="detail-card">
      <div class="card-heading">Forensic Event Timeline</div>
      <div class="timeline-list">
        ${timeline.map(e => `
          <div class="timeline-item">
            <div>
              <span class="timeline-badge">${e.badge}</span>
              <span class="timeline-time">${e.timestamp.slice(0, 10)} ${e.timestamp.slice(11, 16)} UTC</span>
            </div>
            <div style="font-weight:600; font-size:0.8rem; margin-top:2px;">${e.event}</div>
            <div class="timeline-desc">${e.details}</div>
          </div>
        `).join("")}
      </div>
    </div>

    <div class="detail-card">
      <div class="card-heading">Nearby Historical Incidents on File</div>
      ${nearby.map(inc => `
        <div style="padding:6px 0; border-bottom:1px solid rgba(255,255,255,0.05); font-size:0.75rem;">
          <div style="display:flex; justify-content:space-between;">
            <strong style="color:var(--teal-primary)">${inc.id} – ${inc.spill_type}</strong>
            <span style="color:var(--text-dim)">${inc.distance_km} km away</span>
          </div>
          <div style="color:var(--text-muted); margin-top:2px;">${inc.source_description}</div>
          <div style="font-size:0.7rem; color:#a0aec0; margin-top:2px;"><em>${inc.similarity_notes}</em></div>
        </div>
      `).join("")}
    </div>
  `;
}

// -----------------------------------------------------------------
// 8. Tab Navigation & Highlight Interaction
// -----------------------------------------------------------------
function initTabs() {
  const tabButtons = document.querySelectorAll(".tab-btn");
  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      tabButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      const tabId = btn.getAttribute("data-tab");
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
      
      const activePane = document.getElementById(`pane-${tabId}`);
      if (activePane) activePane.classList.add("active");
    });
  });
}

function highlightVessel(mmsi) {
  highlightedMmsi = mmsi;
  // Re-render vessel cards with highlight
  if (currentVesselData) renderVesselsTab(currentVesselData);

  // Pan map to vessel
  const vessel = currentVesselData.ranked_candidate_vessels.find(v => v.mmsi === mmsi);
  if (vessel && vessel.track_coordinates.length > 0) {
    const pt = vessel.track_coordinates[vessel.track_coordinates.length - 1];
    map.panTo([pt[0], pt[1]]);
  }
}

// -----------------------------------------------------------------
// 9. Time Slider & Track Scrubbing
// -----------------------------------------------------------------
function initTimeSlider() {
  const slider = document.getElementById("time-slider");
  const label = document.getElementById("slider-timestamp-label");
  const playBtn = document.getElementById("btn-play-pause");
  const resetBtn = document.getElementById("btn-reset-time");

  slider.addEventListener("input", (e) => {
    currentSliderStep = parseInt(e.target.value);
    updateSliderLabel();
  });

  resetBtn.addEventListener("click", () => {
    stopAnimation();
    slider.value = 0;
    currentSliderStep = 0;
    updateSliderLabel();
  });

  playBtn.addEventListener("click", () => {
    if (isPlaying) {
      stopAnimation();
    } else {
      startAnimation();
    }
  });

  function updateSliderLabel() {
    const hours = currentSliderStep;
    const sign = hours <= 0 ? `T${hours}h` : `T+${hours}h`;
    label.innerText = `Relative Horizon: ${sign} (${hours === 0 ? 'Observation Time' : (hours < 0 ? 'Backtrack' : 'Forecast')})`;
  }

  function startAnimation() {
    isPlaying = true;
    playBtn.innerText = "⏸ Pause";
    animationInterval = setInterval(() => {
      let val = parseInt(slider.value);
      val += 1;
      if (val > 6) val = -16;
      slider.value = val;
      currentSliderStep = val;
      updateSliderLabel();
    }, 600);
  }

  function stopAnimation() {
    isPlaying = false;
    playBtn.innerText = "▶ Play";
    if (animationInterval) {
      clearInterval(animationInterval);
      animationInterval = null;
    }
  }
}

// -----------------------------------------------------------------
// 10. SAR Image Upload & Dynamic Validation Flow
// -----------------------------------------------------------------
function initUploadModal() {
  const modal = document.getElementById("upload-modal");
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const btnOpen = document.getElementById("btn-open-upload");
  const btnSubmit = document.getElementById("btn-submit-upload");
  const chips = document.querySelectorAll(".chip");

  let selectedSampleFile = "sar_dover_pass_081.png";
  let userFile = null;

  btnOpen.addEventListener("click", () => modal.classList.add("active"));

  chips.forEach(chip => {
    chip.addEventListener("click", () => {
      chips.forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      selectedSampleFile = chip.getAttribute("data-sample");
      userFile = null;
    });
  });

  dropZone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      userFile = e.target.files[0];
      dropZone.querySelector("p").innerText = `Selected file: ${userFile.name}`;
      chips.forEach(c => c.classList.remove("active"));
    }
  });

  btnSubmit.addEventListener("click", async () => {
    btnSubmit.innerText = "Analyzing Backscatter...";
    btnSubmit.disabled = true;

    try {
      let formData = new FormData();
      const refLat = parseFloat(document.getElementById("upload-ref-lat").value) || 50.450;
      const refLon = parseFloat(document.getElementById("upload-ref-lon").value) || 0.650;
      formData.append("reference_lat", refLat);
      formData.append("reference_lon", refLon);

      if (userFile) {
        formData.append("file", userFile);
      } else {
        // Fetch sample file as blob
        const sampleUrl = `/data/sample_images/${selectedSampleFile}`;
        const blobRes = await fetch(sampleUrl);
        const blob = await blobRes.blob();
        formData.append("file", blob, selectedSampleFile);
      }

      // 1. Post to Detection Endpoint
      const detectRes = await fetch(`${API_BASE}/api/detect`, {
        method: "POST",
        body: formData
      });
      if (!detectRes.ok) throw new Error(`Detection failed (${detectRes.status})`);
      const detectData = await detectRes.json();

      // Show results in modal preview
      const previewOrig = document.getElementById("preview-orig-img");
      const previewOverlay = document.getElementById("preview-overlay-img");
      const resultsContainer = document.getElementById("upload-results-container");
      const summaryBox = document.getElementById("modal-validation-summary");

      previewOrig.src = detectData.original_image_url;
      previewOverlay.src = detectData.overlay_image_url;
      resultsContainer.style.display = "block";

      // 2. Validate first detected patch with ML model
      if (detectData.patches.length > 0) {
        const p1 = detectData.patches[0];
        const valRes = await fetch(`${API_BASE}/api/validate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ patch_id: p1.patch_id, features: p1 })
        });
        const valData = await valRes.json();

        summaryBox.innerHTML = `
          <div><strong>Detections:</strong> ${detectData.patch_count} dark patches isolated in ${detectData.processing_time_ms} ms.</div>
          <div style="margin-top:4px;"><strong>Primary Patch Classification:</strong> 
            <span style="color:${valData.classification === 'likely_oil_spill' ? '#ff6b81' : '#2ed573'}; font-weight:700;">
              ${valData.classification.toUpperCase()} (${Math.round(valData.confidence_score * 100)}% Confidence)
            </span>
          </div>
          <div style="font-size:0.72rem; color:var(--text-muted); margin-top:4px;">${valData.investigative_notes}</div>
        `;
      } else {
        summaryBox.innerHTML = `<div>No dark damping patches exceeding threshold detected. Clear ocean backscatter.</div>`;
      }

    } catch (err) {
      alert(`Error processing SAR image: ${err.message}`);
    } finally {
      btnSubmit.innerText = "Process SAR Image";
      btnSubmit.disabled = false;
    }
  });
}

function initEventListeners() {
  document.getElementById("btn-refresh-data").addEventListener("click", () => {
    loadSpillDetections(currentSpill ? currentSpill.id : null);
  });

  const searchInput = document.getElementById("spill-search");
  searchInput.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();
    const filtered = allSpills.filter(s => 
      s.name.toLowerCase().includes(q) || 
      s.id.toLowerCase().includes(q) || 
      s.classification.toLowerCase().includes(q)
    );
    renderSpillList(filtered);
  });
}
