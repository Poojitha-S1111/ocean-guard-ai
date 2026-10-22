import joblib
import numpy as np
from pathlib import Path
from typing import Dict, Any
from app.schemas import ValidationResponse

MODEL_PATH = Path(__file__).resolve().parent.parent / "ml" / "oil_spill_classifier.joblib"

_MODEL_BUNDLE = None

def get_model():
    global _MODEL_BUNDLE
    if _MODEL_BUNDLE is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model file not found at {MODEL_PATH}. Please run ml/train.py first.")
        _MODEL_BUNDLE = joblib.load(str(MODEL_PATH))
    return _MODEL_BUNDLE

def validate_patch_features(patch_id: int, features: Dict[str, float]) -> ValidationResponse:
    bundle = get_model()
    model = bundle["model"]
    feature_names = bundle["feature_names"]
    
    # Construct input vector in required order with sensible defaults
    vector = []
    for fname in feature_names:
        val = features.get(fname, 0.0)
        vector.append(float(val))
    
    X = np.array([vector])
    proba = model.predict_proba(X)[0] # [P(lookalike), P(oil_spill)]
    
    p_lookalike = float(proba[0])
    p_oil = float(proba[1])
    
    if p_oil >= 0.5:
        classification = "likely_oil_spill"
        confidence_score = round(p_oil, 3)
    else:
        classification = "natural_lookalike"
        confidence_score = round(p_lookalike, 3)
        
    # Generate contextual investigative notes based on observed physical characteristics
    elongation = features.get("elongation", 1.0)
    contrast = features.get("surrounding_contrast", 0.0)
    mean_int = features.get("mean_intensity", 120.0)
    
    notes = []
    if classification == "likely_oil_spill":
        notes.append(f"High damping signature detected (contrast: +{contrast:.1f} vs sea surface).")
        if elongation >= 2.0:
            notes.append(f"Significant elongation ({elongation:.1f}x) consistent with discharge while vessel was underway.")
        else:
            notes.append("Moderate elongation; indicative of localized stationary discharge or early diffusion.")
        notes.append("Investigation Recommended: cross-reference with historical incidents and backtracking drift path.")
    else:
        notes.append(f"Subdued contrast ({contrast:.1f}) and moderate backscatter ({mean_int:.1f}) indicate low wave damping.")
        notes.append(f"Morphological profile (elongation {elongation:.1f}x) is characteristic of biogenic surfactant film or meteorological calm zone.")
        notes.append("Investigation Lead: likely natural look-alike; human analyst verification suggested.")
        
    return ValidationResponse(
        patch_id=patch_id,
        classification=classification,
        confidence_score=confidence_score,
        probabilities={
            "likely_oil_spill": round(p_oil, 4),
            "natural_lookalike": round(p_lookalike, 4)
        },
        feature_importance=bundle.get("feature_importances", {}),
        investigative_notes=" ".join(notes)
    )
