import numpy as np
import joblib
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import StandardScaler

FEATURE_NAMES = [
    "area_pixels",
    "perimeter_pixels",
    "elongation",
    "compactness",
    "mean_intensity",
    "surrounding_contrast",
    "texture_homogeneity",
    "texture_contrast",
    "texture_energy"
]

def generate_synthetic_sar_dataset(n_samples_per_class: int = 600, random_state: int = 42):
    """
    Generates realistic, physically motivated synthetic SAR patch features based on
    published literature (Solberg et al. 2007, Topouzelis 2008, Mera et al. 2012).
    
    Class 1: likely_oil_spill
      - Caused by vessel discharge or offshore platforms
      - High elongation (linear trailing discharge from underway ship)
      - Sharp damping gradient (low mean intensity inside, high surrounding contrast)
      - Smooth internal surface (high GLCM homogeneity, low internal texture contrast)
      - Moderate to low compactness
      
    Class 0: natural_lookalike
      - Caused by biogenic surfactant films (algal blooms, plankton), low wind calm areas (<3 m/s),
        rain cells, or internal waves
      - Lower elongation (more amoeboid/circular/feathered)
      - Fainter damping (higher mean intensity, lower surrounding contrast)
      - Higher internal texture variance due to wave penetration
    """
    np.random.seed(random_state)
    
    # -------------------------------------------------------------
    # 1. Oil Spill Samples (Label 1)
    # -------------------------------------------------------------
    # Area: 1,000 to 12,000 pixels
    area_oil = np.random.gamma(shape=3.5, scale=1200, size=n_samples_per_class) + 800
    # Elongation: typically 2.0 to 5.5 (mean ~3.2)
    elong_oil = np.random.normal(loc=3.2, scale=0.8, size=n_samples_per_class)
    elong_oil = np.clip(elong_oil, 1.6, 7.0)
    # Compactness: 0.15 to 0.45
    compact_oil = np.random.normal(loc=0.32, scale=0.06, size=n_samples_per_class)
    compact_oil = np.clip(compact_oil, 0.12, 0.50)
    # Perimeter calculated approximately from area & compactness
    perim_oil = np.sqrt((4.0 * np.pi * area_oil) / compact_oil) + np.random.normal(0, 30, n_samples_per_class)
    # Mean intensity: 25 to 55 (dark dampened radar return)
    mean_int_oil = np.random.normal(loc=38.0, scale=6.5, size=n_samples_per_class)
    mean_int_oil = np.clip(mean_int_oil, 18.0, 58.0)
    # Surrounding contrast: 50 to 95 (steep edge gradient)
    contrast_oil = np.random.normal(loc=68.0, scale=12.0, size=n_samples_per_class)
    contrast_oil = np.clip(contrast_oil, 42.0, 110.0)
    # GLCM Homogeneity: 0.68 to 0.88
    homog_oil = np.random.normal(loc=0.76, scale=0.05, size=n_samples_per_class)
    homog_oil = np.clip(homog_oil, 0.60, 0.92)
    # GLCM Contrast: 10 to 30
    tex_cont_oil = np.random.normal(loc=19.0, scale=4.5, size=n_samples_per_class)
    tex_cont_oil = np.clip(tex_cont_oil, 8.0, 35.0)
    # GLCM Energy: 0.24 to 0.42
    energy_oil = np.random.normal(loc=0.31, scale=0.04, size=n_samples_per_class)
    energy_oil = np.clip(energy_oil, 0.20, 0.48)
    
    X_oil = np.column_stack([
        area_oil, perim_oil, elong_oil, compact_oil,
        mean_int_oil, contrast_oil, homog_oil, tex_cont_oil, energy_oil
    ])
    y_oil = np.ones(n_samples_per_class, dtype=int)
    
    # -------------------------------------------------------------
    # 2. Natural Look-alike Samples (Label 0)
    # -------------------------------------------------------------
    # Area: wider distribution, large diffuse biogenic films or small calm patches
    area_look = np.random.gamma(shape=2.5, scale=2000, size=n_samples_per_class) + 600
    # Elongation: typically 1.1 to 2.2 (mean ~1.5)
    elong_look = np.random.normal(loc=1.5, scale=0.4, size=n_samples_per_class)
    elong_look = np.clip(elong_look, 1.05, 2.5)
    # Compactness: higher, 0.35 to 0.65
    compact_look = np.random.normal(loc=0.52, scale=0.08, size=n_samples_per_class)
    compact_look = np.clip(compact_look, 0.30, 0.75)
    perim_look = np.sqrt((4.0 * np.pi * area_look) / compact_look) + np.random.normal(0, 40, n_samples_per_class)
    # Mean intensity: 50 to 80 (fainter suppression)
    mean_int_look = np.random.normal(loc=62.0, scale=8.0, size=n_samples_per_class)
    mean_int_look = np.clip(mean_int_look, 45.0, 90.0)
    # Surrounding contrast: 15 to 45 (diffuse, gentle gradient)
    contrast_look = np.random.normal(loc=28.0, scale=8.0, size=n_samples_per_class)
    contrast_look = np.clip(contrast_look, 10.0, 48.0)
    # GLCM Homogeneity: 0.45 to 0.65
    homog_look = np.random.normal(loc=0.54, scale=0.06, size=n_samples_per_class)
    homog_look = np.clip(homog_look, 0.35, 0.68)
    # GLCM Contrast: 30 to 65
    tex_cont_look = np.random.normal(loc=42.0, scale=7.5, size=n_samples_per_class)
    tex_cont_look = np.clip(tex_cont_look, 26.0, 75.0)
    # GLCM Energy: 0.12 to 0.22
    energy_look = np.random.normal(loc=0.16, scale=0.03, size=n_samples_per_class)
    energy_look = np.clip(energy_look, 0.08, 0.25)
    
    X_look = np.column_stack([
        area_look, perim_look, elong_look, compact_look,
        mean_int_look, contrast_look, homog_look, tex_cont_look, energy_look
    ])
    y_look = np.zeros(n_samples_per_class, dtype=int)
    
    X = np.vstack([X_oil, X_look])
    y = np.concatenate([y_oil, y_look])
    
    # Shuffle
    indices = np.arange(len(y))
    np.random.shuffle(indices)
    return X[indices], y[indices]

def train_and_evaluate(model_save_path: Path):
    print("=" * 65)
    print(" OceanGuard AI – Patch Feature Classifier Training Pipeline")
    print("=" * 65)
    
    # 1. Generate or load dataset
    X, y = generate_synthetic_sar_dataset(n_samples_per_class=600, random_state=42)
    print(f"Dataset generated: {X.shape[0]} samples across {X.shape[1]} features.")
    print(f"Class distribution: {np.sum(y == 1)} Oil Spills, {np.sum(y == 0)} Natural Look-alikes.")
    
    # 2. Train / Test Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    
    # 3. Model Training: Random Forest
    rf_model = RandomForestClassifier(
        n_estimators=120,
        max_depth=7,
        min_samples_split=4,
        min_samples_leaf=2,
        class_weight='balanced',
        random_state=42
    )
    
    # 5-fold cross-validation
    cv_scores = cross_val_score(rf_model, X_train, y_train, cv=5, scoring='accuracy')
    print(f"\n5-Fold Cross-Validation Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
    
    rf_model.fit(X_train, y_train)
    
    # 4. Evaluation on Test Set
    y_pred = rf_model.predict(X_test)
    y_proba = rf_model.predict_proba(X_test)[:, 1]
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    
    print("\nTest Set Performance Metrics:")
    print(f"  Accuracy : {acc * 100:.2f}%")
    print(f"  Precision: {prec * 100:.2f}%")
    print(f"  Recall   : {rec * 100:.2f}%")
    print(f"  F1-Score : {f1 * 100:.2f}%")
    
    print("\nConfusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(f"  [TN={cm[0,0]:3d}  FP={cm[0,1]:3d}]  (Row 0: Look-alike)")
    print(f"  [FN={cm[1,0]:3d}  TP={cm[1,1]:3d}]  (Row 1: Oil Spill)")
    
    print("\nDetailed Classification Report:")
    target_names = ["natural_lookalike", "likely_oil_spill"]
    print(classification_report(y_test, y_pred, target_names=target_names))
    
    print("Feature Importance Ranking:")
    importances = rf_model.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    feature_importance_dict = {}
    for idx in sorted_idx:
        fname = FEATURE_NAMES[idx]
        imp = importances[idx]
        feature_importance_dict[fname] = round(float(imp), 4)
        print(f"  {fname:<22}: {imp * 100:5.2f}%")
    
    # 5. Save model bundle
    bundle = {
        "model": rf_model,
        "feature_names": FEATURE_NAMES,
        "feature_importances": feature_importance_dict,
        "metrics": {
            "accuracy": round(float(acc), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "confusion_matrix": cm.tolist()
        },
        "target_names": target_names
    }
    
    model_save_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, str(model_save_path))
    print(f"\nTrained model bundle successfully saved to: {model_save_path}")

if __name__ == "__main__":
    out_path = Path(__file__).resolve().parent / "oil_spill_classifier.joblib"
    train_and_evaluate(out_path)
