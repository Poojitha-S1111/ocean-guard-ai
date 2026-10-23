import cv2
import numpy as np
import time
import math
import uuid
from pathlib import Path
from typing import List, Tuple, Dict, Any
from skimage.feature import graycomatrix, graycoprops

from app.schemas import DetectionResponse, PatchFeature

SAMPLE_IMAGES_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_images"

def apply_lee_filter(img: np.ndarray, window_size: int = 5) -> np.ndarray:
    """
    Applies the classic Lee speckle filter for SAR imagery.
    Formula: R = mean + W * (pixel - mean), where W = var / (var + noise_var)
    Preserves edges while smoothing Rayleigh speckle noise.
    """
    img_f = img.astype(np.float32)
    mean = cv2.blur(img_f, (window_size, window_size))
    mean_sq = cv2.blur(img_f * img_f, (window_size, window_size))
    variance = np.maximum(mean_sq - mean * mean, 0)
    
    # Estimate overall speckle noise variance
    overall_noise_var = np.mean(variance) + 1e-5
    weight = variance / (variance + overall_noise_var)
    weight = np.clip(weight, 0.0, 1.0)
    
    filtered = mean + weight * (img_f - mean)
    return np.clip(filtered, 0, 255).astype(np.uint8)

def compute_glcm_features(patch_roi: np.ndarray) -> Tuple[float, float, float]:
    """
    Calculates Gray-Level Co-occurrence Matrix (GLCM) texture metrics:
    homogeneity, contrast, and energy.
    """
    if patch_roi.size < 16 or min(patch_roi.shape) < 4:
        return 0.5, 20.0, 0.2
    
    # Quantize to 16 gray levels for fast and robust GLCM
    quantized = (patch_roi / 16).astype(np.uint8)
    glcm = graycomatrix(quantized, distances=[1], angles=[0, np.pi/4, np.pi/2], levels=16, symmetric=True, normed=True)
    
    homogeneity = float(np.mean(graycoprops(glcm, 'homogeneity')))
    contrast = float(np.mean(graycoprops(glcm, 'contrast')))
    energy = float(np.mean(graycoprops(glcm, 'energy')))
    return round(homogeneity, 4), round(contrast, 2), round(energy, 4)

def pixels_to_latlon(points_px: np.ndarray, ref_lat: float, ref_lon: float,
                      img_w: int, img_h: int, pixel_res_meters: float = 25.0) -> List[List[float]]:
    """
    Transforms image pixel coordinates to geographic coordinates (lat, lon).
    Assumes image center corresponds to (ref_lat, ref_lon).
    """
    center_x = img_w / 2.0
    center_y = img_h / 2.0
    
    lat_lon_coords = []
    # 1 deg latitude is approx 111,139 meters
    m_per_lat = 111139.0
    m_per_lon = 111139.0 * math.cos(math.radians(ref_lat))
    
    for pt in points_px:
        x, y = pt[0], pt[1]
        dx_meters = (x - center_x) * pixel_res_meters
        # In image coords, y increases downwards, whereas latitude increases upwards (north)
        dy_meters = (center_y - y) * pixel_res_meters
        
        lat = ref_lat + (dy_meters / m_per_lat)
        lon = ref_lon + (dx_meters / m_per_lon)
        lat_lon_coords.append([round(lat, 5), round(lon, 5)])
        
    return lat_lon_coords

def process_sar_image(
    image_bytes: bytes,
    original_filename: str,
    reference_lat: float = 50.450,
    reference_lon: float = 0.650,
    pixel_res_meters: float = 25.0
) -> DetectionResponse:
    start_time = time.time()
    
    # 1. Decode image
    nparr = np.frombuffer(image_bytes, np.uint8)
    src_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if src_img is None:
        raise ValueError("Invalid image file. Could not decode SAR raster.")
    
    h, w = src_img.shape[:2]
    gray = cv2.cvtColor(src_img, cv2.COLOR_BGR2GRAY) if len(src_img.shape) == 3 else src_img
    
    # 2. Speckle noise reduction (Lee filter + 3x3 median)
    despeckled = apply_lee_filter(gray, window_size=5)
    despeckled = cv2.medianBlur(despeckled, 3)
    
    # 3. Dynamic range normalization
    p2, p98 = np.percentile(despeckled, (2, 98))
    norm = np.clip((despeckled.astype(np.float32) - p2) / (p98 - p2 + 1e-5) * 255.0, 0, 255).astype(np.uint8)
    
    # 4. Ocean masking (exclude high backscatter land or strong metallic clutter)
    ocean_mask = (norm < 220).astype(np.uint8)
    
    # Dark patch detection via localized damping thresholding
    # Oil and biogenic slicks dampen capillary waves, resulting in significant local backscatter depression
    blur_large = cv2.GaussianBlur(norm, (45, 45), 0)
    diff = blur_large.astype(np.int16) - norm.astype(np.int16)
    
    mean_val = float(np.mean(norm))
    std_val = float(np.std(norm))
    
    # A true SAR dark patch requires both significant contrast against surrounding sea (diff >= 22)
    # and an absolute depressed backscatter below the local sea mean (norm <= mean - 1.2 * std)
    dark_mask = ((diff >= 22) & (norm <= (mean_val - 1.1 * std_val))).astype(np.uint8) * ocean_mask
    
    # Morphological cleaning (closing to fill holes inside slick, opening to eliminate single-pixel noise)
    kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    kernel_medium = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    cleaned_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, kernel_small)
    cleaned_mask = cv2.morphologyEx(cleaned_mask, cv2.MORPH_CLOSE, kernel_medium)
    
    # 6. Find contours of dark patches
    contours, _ = cv2.findContours(cleaned_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Prepare visualization overlay
    overlay = src_img.copy()
    
    # Add a semi-transparent HUD overlay
    hud_layer = np.zeros_like(src_img)
    
    patches: List[PatchFeature] = []
    patch_id_counter = 1
    
    # Sort contours by area descending, filtering out minor noise fragments
    valid_contours = [c for c in contours if cv2.contourArea(c) >= 300]
    valid_contours = sorted(valid_contours, key=cv2.contourArea, reverse=True)
    
    for cnt in valid_contours:
        area_px = float(cv2.contourArea(cnt))
        perimeter_px = float(cv2.arcLength(cnt, True))
        if perimeter_px < 1e-5:
            continue
            
        x, y, bw, bh = cv2.boundingRect(cnt)
        
        # Elongation via minimum area rectangle
        rect = cv2.minAreaRect(cnt)
        dim1, dim2 = rect[1]
        major_axis = max(dim1, dim2)
        minor_axis = min(dim1, dim2)
        elongation = float(major_axis / (minor_axis + 1e-4))
        
        # Compactness (Isoperimetric quotient)
        compactness = float((4.0 * math.pi * area_px) / (perimeter_px * perimeter_px + 1e-5))
        
        # Patch mask and intensity
        cnt_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.drawContours(cnt_mask, [cnt], -1, 255, -1)
        patch_mean_intensity = float(cv2.mean(norm, mask=cnt_mask)[0])
        
        # Surrounding ocean buffer (dilation minus patch)
        dilated = cv2.dilate(cnt_mask, kernel_medium, iterations=4)
        surrounding_mask = cv2.subtract(dilated, cnt_mask)
        surrounding_mean = float(cv2.mean(norm, mask=surrounding_mask)[0])
        surrounding_contrast = float(max(surrounding_mean - patch_mean_intensity, 0.0))
        
        # Texture analysis on bounding ROI
        roi = norm[max(0, y):min(h, y+bh), max(0, x):min(w, x+bw)]
        homogeneity, tex_contrast, energy = compute_glcm_features(roi)
        
        # Approximate real-world geographic footprint
        # Area in sq km: area_px * (res * res) / 1,000,000
        area_sq_km = round(area_px * (pixel_res_meters * pixel_res_meters) / 1_000_000.0, 3)
        perimeter_km = round(perimeter_px * pixel_res_meters / 1000.0, 3)
        
        # Simplify contour for GeoJSON polygon
        epsilon = 0.015 * perimeter_px
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        approx_pts = approx.reshape(-1, 2)
        lat_lon_polygon = pixels_to_latlon(approx_pts, reference_lat, reference_lon, w, h, pixel_res_meters)
        # Ensure closed polygon
        if lat_lon_polygon and lat_lon_polygon[0] != lat_lon_polygon[-1]:
            lat_lon_polygon.append(lat_lon_polygon[0])
            
        patch_obj = PatchFeature(
            patch_id=patch_id_counter,
            area_pixels=round(area_px, 1),
            perimeter_pixels=round(perimeter_px, 1),
            elongation=round(elongation, 2),
            compactness=round(compactness, 3),
            mean_intensity=round(patch_mean_intensity, 1),
            surrounding_contrast=round(surrounding_contrast, 1),
            texture_homogeneity=homogeneity,
            texture_contrast=tex_contrast,
            texture_energy=energy,
            bounding_box=[y, x, y + bh, x + bw],
            polygon_coords=lat_lon_polygon,
            area_sq_km=area_sq_km,
            perimeter_km=perimeter_km
        )
        patches.append(patch_obj)
        
        # Visual annotations for overlay
        # Draw glowing contour: cyan/teal glow
        cv2.drawContours(hud_layer, [cnt], -1, (240, 210, 0), 2) # BGR: teal-cyan
        cv2.circle(hud_layer, (int(rect[0][0]), int(rect[0][1])), 3, (0, 255, 255), -1)
        
        # Label badge
        badge_text = f"#{patch_id_counter} ({area_sq_km} km2)"
        cv2.putText(hud_layer, badge_text, (max(10, x), max(20, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
        
        patch_id_counter += 1

    # Blend HUD layer with original image
    cv2.addWeighted(hud_layer, 0.85, overlay, 1.0, 0, overlay)
    
    # Save original and overlay to sample_images folder
    detection_uuid = f"DET-{uuid.uuid4().hex[:8].upper()}"
    base_name = Path(original_filename).stem
    saved_orig_name = f"{base_name}_{detection_uuid}.png"
    saved_overlay_name = f"{base_name}_{detection_uuid}_overlay.png"
    
    cv2.imwrite(str(SAMPLE_IMAGES_DIR / saved_orig_name), src_img)
    cv2.imwrite(str(SAMPLE_IMAGES_DIR / saved_overlay_name), overlay)
    
    processing_time_ms = round((time.time() - start_time) * 1000.0, 1)
    
    return DetectionResponse(
        detection_id=detection_uuid,
        image_name=original_filename,
        original_image_url=f"/data/sample_images/{saved_orig_name}",
        overlay_image_url=f"/data/sample_images/{saved_overlay_name}",
        patch_count=len(patches),
        patches=patches,
        center_lat=reference_lat,
        center_lon=reference_lon,
        processing_time_ms=processing_time_ms
    )
