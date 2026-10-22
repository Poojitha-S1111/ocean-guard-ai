import numpy as np
import cv2
import os
from pathlib import Path

def generate_sar_texture(height, width, mean_intensity=120, speckle_scale=18):
    """
    Generates realistic SAR ocean background with Gamma/Rayleigh speckle noise.
    """
    # Base sea texture with swell waves
    x = np.linspace(0, 8 * np.pi, width)
    y = np.linspace(0, 8 * np.pi, height)
    X, Y = np.meshgrid(x, y)
    waves = 6 * np.sin(0.4 * X + 0.3 * Y) + 4 * np.cos(0.2 * X - 0.5 * Y)
    
    # Rayleigh / Gamma distributed SAR speckle noise
    speckle = np.random.gamma(shape=4.0, scale=speckle_scale / 4.0, size=(height, width))
    
    sar_image = mean_intensity + waves + (speckle - speckle_scale)
    return np.clip(sar_image, 10, 255).astype(np.uint8)

def inject_slick(img, center_x, center_y, major_r, minor_r, angle_deg, damping_factor=0.35, feather=15):
    """
    Simulates capillary wave damping caused by oil film (backscatter suppression).
    """
    mask = np.zeros(img.shape, dtype=np.float32)
    cv2.ellipse(mask, (center_x, center_y), (major_r, minor_r), angle_deg, 0, 360, 1.0, -1)
    
    # Add organic jaggedness along edge
    noise = cv2.GaussianBlur(np.random.normal(0, 0.25, img.shape), (15, 15), 0)
    mask = np.clip(mask + noise * mask, 0.0, 1.0)
    
    # Feather boundary
    if feather > 0:
        mask = cv2.GaussianBlur(mask, (feather * 2 + 1, feather * 2 + 1), 0)
    
    # Darken region according to radar damping
    dampened = img.astype(np.float32) * (1.0 - (1.0 - damping_factor) * mask)
    return np.clip(dampened, 5, 255).astype(np.uint8), mask

def add_ship_blips(img, num_ships=3):
    """
    Adds metallic point scatterers (bright corner reflection) with cross sidelobes.
    """
    result = img.copy()
    h, w = img.shape
    for _ in range(num_ships):
        sx = np.random.randint(40, w - 40)
        sy = np.random.randint(40, h - 40)
        # bright hull
        cv2.circle(result, (sx, sy), 2, 255, -1)
        # slight cross sidelobes characteristic of SAR antennas
        cv2.line(result, (sx - 4, sy), (sx + 4, sy), 240, 1)
        cv2.line(result, (sx, sy - 4), (sx, sy + 4), 240, 1)
    return result

def create_all_sample_images(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    H, W = 512, 512
    
    # 1. Spill Sample 1: Dover Strait Slick (Elongated, high contrast, heavy crude)
    img1 = generate_sar_texture(H, W, mean_intensity=135, speckle_scale=22)
    img1, _ = inject_slick(img1, 250, 240, major_r=130, minor_r=45, angle_deg=35, damping_factor=0.28, feather=7)
    # secondary smaller connected slick
    img1, _ = inject_slick(img1, 330, 300, major_r=60, minor_r=25, angle_deg=40, damping_factor=0.32, feather=5)
    img1 = add_ship_blips(img1, num_ships=4)
    cv2.imwrite(str(output_dir / "sar_dover_pass_081.png"), img1)
    
    # 2. Spill Sample 2: Calais Approach Slick (Linear trail)
    img2 = generate_sar_texture(H, W, mean_intensity=128, speckle_scale=20)
    img2, _ = inject_slick(img2, 260, 260, major_r=160, minor_r=30, angle_deg=65, damping_factor=0.30, feather=9)
    img2 = add_ship_blips(img2, num_ships=5)
    cv2.imwrite(str(output_dir / "sar_calais_pass_082.png"), img2)
    
    # 3. Lookalike Sample 1: Beachy Head Natural Biogenic Lookalike (Low wind / algal film)
    # Natural lookalikes have diffuse edges, lower contrast with surrounding, irregular non-linear shape
    img3 = generate_sar_texture(H, W, mean_intensity=105, speckle_scale=16)
    img3, _ = inject_slick(img3, 230, 230, major_r=120, minor_r=95, angle_deg=10, damping_factor=0.62, feather=25)
    img3 = add_ship_blips(img3, num_ships=2)
    cv2.imwrite(str(output_dir / "sar_beachy_head_083.png"), img3)
    
    # 4. Spill Sample 3: Wight Passage Weathered Sheen
    img4 = generate_sar_texture(H, W, mean_intensity=140, speckle_scale=24)
    img4, _ = inject_slick(img4, 280, 200, major_r=90, minor_r=35, angle_deg=-25, damping_factor=0.34, feather=8)
    img4, _ = inject_slick(img4, 180, 320, major_r=50, minor_r=22, angle_deg=-20, damping_factor=0.38, feather=6)
    img4 = add_ship_blips(img4, num_ships=3)
    cv2.imwrite(str(output_dir / "sar_wight_pass_084.png"), img4)

    # 5. Clean Sea Sample (No slick)
    img5 = generate_sar_texture(H, W, mean_intensity=130, speckle_scale=22)
    img5 = add_ship_blips(img5, num_ships=4)
    cv2.imwrite(str(output_dir / "sar_clean_sea_sample.png"), img5)

    print(f"Generated 5 realistic sample SAR images in {output_dir}")

if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "data" / "sample_images"
    create_all_sample_images(out)
