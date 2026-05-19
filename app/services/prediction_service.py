import os
import json
import numpy as np
import joblib

# ---------------------------------------------------------------------------
# Load small metadata at import time; load the large model lazily on prediction.
# ---------------------------------------------------------------------------
def get_robust_base():
    possible_bases = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'ml', 'model'),
        '/home/ubuntu/vet/ml/model',
        '/home/ubuntu/VET/ml/model',
        # EC2 app-relative path (app is inside /home/ubuntu/VET/)
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'ml', 'model'),
        os.path.abspath(os.path.join(os.getcwd(), 'ml', 'model')),
        os.path.abspath(os.path.join(os.getcwd(), '..', 'ml', 'model')),
    ]
    for path in possible_bases:
        path = os.path.abspath(path)
        if os.path.exists(os.path.join(path, 'metadata.json')):
            return path
    # Log all paths tried so EC2 debugging is easy
    import sys
    print(f"[VetScan] WARNING: metadata.json not found in any path:", file=sys.stderr)
    for p in possible_bases:
        print(f"  tried: {os.path.abspath(p)}", file=sys.stderr)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'ml', 'model')

_BASE = get_robust_base()

try:
    with open(os.path.join(_BASE, 'metadata.json')) as f:
        meta = json.load(f)
except Exception:
    meta = {}

FEATURE_COLS     = meta.get('feature_cols', [])
ANIMAL_TYPES     = meta.get('animal_types', ['Dog', 'Cat'])
BREEDS_BY_ANIMAL = meta.get('breeds_by_animal', {})
ALL_SYMPTOMS     = meta.get('all_symptoms', [])
DISEASES         = meta.get('diseases', [])

_model = None
_encoders = None


def _load_assets():
    global _model, _encoders
    if _model is None or _encoders is None:
        model_path = os.path.join(_BASE, 'disease_model.pkl')
        encoders_path = os.path.join(_BASE, 'encoders.pkl')
        
        if not os.path.exists(model_path) or not os.path.exists(encoders_path):
            raise FileNotFoundError(
                "The ML disease model files (disease_model.pkl or encoders.pkl) are currently unavailable "
                "on this server instance. Please upload them to the ml/model/ directory."
            )
            
        _model = joblib.load(model_path)
        if hasattr(_model, 'n_jobs'):
            _model.n_jobs = 1
        _encoders = joblib.load(encoders_path)
    return _model, _encoders

# ---------------------------------------------------------------------------
# Severity mapping
# ---------------------------------------------------------------------------
SEVERITY = {
    'critical': [
        'Parvovirus', 'Canine Parvovirus', 'Distemper', 'Canine Distemper',
        'Feline Panleukopenia', 'Feline Panleukopenia Virus',
        'Foot and Mouth Disease', 'African Swine Fever',
        'Viral Hemorrhagic Disease', 'Equine Encephalitis',
        'Bovine Spongiform Encephalopathy', 'Rabies',
    ],
    'high': [
        'Upper Respiratory Infection', 'Pneumonia', 'Equine Influenza',
        'Lyme Disease', 'Mastitis', 'Bovine Mastitis', 'Bovine Tuberculosis',
        'Bovine Respiratory Disease', 'Feline Immunodeficiency Virus',
        'Canine Infectious Hepatitis', 'Porcine Epidemic Diarrhea Virus',
    ],
    'medium': [
        'Gastroenteritis', 'Intestinal Parasites', 'Fungal Infection',
        'Ringworm', 'Mange', 'Kennel Cough', 'Caprine Arthritis Encephalitis',
        'Scrapie Disease', 'Goat Pox', 'Porcine Circovirus Disease',
    ],
}


def get_severity(disease: str) -> str:
    for level, diseases in SEVERITY.items():
        if disease in diseases:
            return level
    return 'low'


def encode_safe(le, value) -> int:
    try:
        return int(le.transform([value])[0])
    except ValueError:
        return 0


def build_features(form: dict) -> np.ndarray:
    _, encoders = _load_assets()
    yn = lambda v: 1 if v == 'Yes' else 0

    body_temp = float(form.get('body_temperature', 39.0))
    try:
        duration_days = int(form.get('duration', 3))
    except (ValueError, TypeError):
        duration_days = 3

    row = {
        'Animal_Type_enc':   encode_safe(encoders['Animal_Type'],  form.get('animal_type', 'Dog')),
        'Breed_enc':         encode_safe(encoders['Breed'],         form.get('breed', 'Labrador')),
        'Age':               int(form.get('age', 3)),
        'Gender_enc':        1 if form.get('gender', 'Male') == 'Male' else 0,
        'Weight':            float(form.get('weight', 20.0)),
        'Symptom_1_enc':     encode_safe(encoders['Symptom_1'],     form.get('symptom_1', 'Fever')),
        'Symptom_2_enc':     encode_safe(encoders['Symptom_2'],     form.get('symptom_2', 'Lethargy')),
        'Symptom_3_enc':     encode_safe(encoders['Symptom_3'],     form.get('symptom_3', 'Vomiting')),
        'Symptom_4_enc':     encode_safe(encoders['Symptom_4'],     form.get('symptom_4', 'Diarrhea')),
        'Duration_days':     duration_days,
        'Appetite_Loss':     yn(form.get('appetite_loss', 'No')),
        'Vomiting':          yn(form.get('vomiting', 'No')),
        'Diarrhea':          yn(form.get('diarrhea', 'No')),
        'Coughing':          yn(form.get('coughing', 'No')),
        'Labored_Breathing': yn(form.get('labored_breathing', 'No')),
        'Lameness':          yn(form.get('lameness', 'No')),
        'Skin_Lesions':      yn(form.get('skin_lesions', 'No')),
        'Nasal_Discharge':   yn(form.get('nasal_discharge', 'No')),
        'Eye_Discharge':     yn(form.get('eye_discharge', 'No')),
        'Body_Temperature':  body_temp,
        'Heart_Rate':        int(form.get('heart_rate', 100)),
    }
    return np.array([[row[f] for f in FEATURE_COLS]])


def predict_disease(form: dict) -> list:
    """Returns top-5 disease predictions sorted by confidence."""
    model, _ = _load_assets()
    X = build_features(form)
    proba = model.predict_proba(X)[0]
    classes = model.classes_

    top_idx = np.argsort(proba)[::-1][:5]
    results = []
    for idx in top_idx:
        class_val = classes[idx]
        # Safely resolve the disease name whether DISEASES is a list or dict,
        # and whether class_val is an int index or already a string label.
        if isinstance(DISEASES, list):
            if isinstance(class_val, (int, np.integer)) and 0 <= int(class_val) < len(DISEASES):
                disease = DISEASES[int(class_val)]
            elif isinstance(class_val, str) and class_val in DISEASES:
                disease = class_val
            else:
                disease = str(class_val)
        elif isinstance(DISEASES, dict):
            disease = DISEASES.get(str(class_val), str(class_val))
        else:
            disease = str(class_val)

        conf = float(proba[idx])
        if conf < 0.01:
            break
        results.append({
            'disease':    disease,
            'confidence': round(conf * 100, 1),
            'severity':   get_severity(disease),
        })

    if not results:
        fallback_val = classes[top_idx[0]]
        if isinstance(DISEASES, list) and isinstance(fallback_val, (int, np.integer)) and 0 <= int(fallback_val) < len(DISEASES):
            fallback_disease = DISEASES[int(fallback_val)]
        elif isinstance(DISEASES, dict):
            fallback_disease = DISEASES.get(str(fallback_val), str(fallback_val))
        else:
            fallback_disease = str(fallback_val)
        results.append({
            'disease':    fallback_disease,
            'confidence': round(float(proba[top_idx[0]]) * 100, 1),
            'severity':   'low',
        })

    return results
