# OceanGuard AI – Machine Learning Module

This directory contains the machine learning classification pipeline for distinguishing **"likely oil spills"** from **"natural look-alikes"** in SAR (Synthetic Aperture Radar) satellite imagery.

## 1. Feature Representation

For each candidate dark patch extracted during SAR speckle reduction, adaptive thresholding, and contour extraction, the following 9 physical and statistical features are computed:

| Feature Name | Description | Physical Interpretation |
|---|---|---|
| `area_pixels` | Area in pixels | Scale of the spill footprint |
| `perimeter_pixels` | Boundary perimeter in pixels | Extent of oil-water interface |
| `elongation` | Major axis / Minor axis ratio | Discharges from underway vessels form long trails (\(\ge 2.5\)), while natural slicks are more circular (\(\sim 1.0 - 1.8\)) |
| `compactness` | Isoperimetric quotient \(4\pi A / P^2\) | Measures ribbon-like vs circular morphology |
| `mean_intensity` | Average backscatter pixel intensity | Hydrocarbon films damp capillary waves strongly (low values) |
| `surrounding_contrast` | Background sea mean minus patch mean | Steep gradients indicate mineral oil; gentle gradients indicate biogenic films |
| `texture_homogeneity` | GLCM Homogeneity metric | Calm internal surface produces higher local homogeneity |
| `texture_contrast` | GLCM Contrast metric | Internal texture roughness |
| `texture_energy` | GLCM Angular Second Moment | Uniformity of the patch surface |

## 2. Model Architecture

- **Classifier**: Calibrated `RandomForestClassifier` (120 estimators, depth-constrained to avoid overfitting on noise artifacts).
- **Output**: Multi-class probability and confidence score (\(0.0 - 1.0\)).
- **Decision-support Role**: Provides probabilistic validation confidence. Results serve as investigative leads, not definitive proof.

## 3. Training the Model

Run the training pipeline:
```bash
python ml/train.py
```
This generates synthetic benchmark patches calibrated against empirical SAR oceanography literature (Solberg et al., Topouzelis et al.), computes metrics (Accuracy, Precision, Recall, F1, Confusion Matrix), and saves the model artifact to `ml/oil_spill_classifier.joblib`.

## 4. How to Swap in a Real Dataset

To train the classifier on real-world satellite acquisitions:

### Recommended Public Datasets
1. **Sentinel-1 SAR Oil Spill Dataset** (e.g., Kaloorazi et al., or University of Stirling / IEEE Dataport).
2. **CleanSea / NOAA Marine Pollution Surveillance Dataset**.
3. **Mera et al. SAR Oil Spill Database** (ERS-1/2, ENVISAT ASAR).

### Step-by-Step Dataset Ingestion
1. Place your labeled SAR image patches (or GeoTIFFs) in a directory such as `backend/data/real_sar/`:
   ```
   backend/data/real_sar/
     ├── oil_spill/
     │   ├── spill_001.png
     │   └── ...
     └── lookalike/
         ├── lookalike_001.png
         └── ...
   ```
2. In `ml/train.py`, replace `generate_synthetic_sar_dataset()` with an image feature extraction loop:
   ```python
   import cv2
   from services.detection import apply_lee_filter, compute_glcm_features

   def load_real_sar_dataset(data_dir: Path):
       X, y = [], []
       for category, label in [("oil_spill", 1), ("lookalike", 0)]:
           folder = data_dir / category
           for img_path in folder.glob("*.png"):
               img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
               # extract features using detection service functions
               # append to X and y
       return np.array(X), np.array(y)
   ```
3. Run `python ml/train.py` to train and save the updated `oil_spill_classifier.joblib`.
