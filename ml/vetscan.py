import json
import numpy as np
import joblib
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Load model, encoders, metadata
model    = joblib.load('model/disease_model.pkl')
encoders = joblib.load('model/encoders.pkl')
with open('model/metadata.json') as f:
    meta = json.load(f)

FEATURE_COLS    = meta['feature_cols']
ANIMAL_TYPES    = meta['animal_types']
BREEDS_BY_ANIMAL = meta['breeds_by_animal']
ALL_SYMPTOMS    = meta['all_symptoms']
DISEASES        = meta['diseases']

# Severity map — editable
SEVERITY = {
    'critical': ['Parvovirus','Canine Parvovirus','Distemper','Canine Distemper',
                 'Feline Panleukopenia','Feline Panleukopenia Virus',
                 'Foot and Mouth Disease','African Swine Fever',
                 'Viral Hemorrhagic Disease','Equine Encephalitis',
                 'Bovine Spongiform Encephalopathy','Rabies'],
    'high':     ['Upper Respiratory Infection','Pneumonia','Equine Influenza',
                 'Lyme Disease','Mastitis','Bovine Mastitis','Bovine Tuberculosis',
                 'Bovine Respiratory Disease','Feline Immunodeficiency Virus',
                 'Canine Infectious Hepatitis','Porcine Epidemic Diarrhea Virus'],
    'medium':   ['Gastroenteritis','Intestinal Parasites','Fungal Infection',
                 'Ringworm','Mange','Kennel Cough','Caprine Arthritis Encephalitis',
                 'Scrapie Disease','Goat Pox','Porcine Circovirus Disease'],
}

def get_severity(disease):
    for level, diseases in SEVERITY.items():
        if disease in diseases:
            return level
    return 'low'

def encode_safe(le, value):
    """Encode a value; return 0 if unseen."""
    try:
        return int(le.transform([value])[0])
    except ValueError:
        return 0

def build_features(form):
    yn = lambda v: 1 if v == 'Yes' else 0
    body_temp = float(form.get('body_temperature', 39.0))
    duration_raw = form.get('duration', '3')
    try:
        duration_days = int(duration_raw)
    except:
        duration_days = 3

    row = {
        'Animal_Type_enc':  encode_safe(encoders['Animal_Type'],  form.get('animal_type','Dog')),
        'Breed_enc':        encode_safe(encoders['Breed'],         form.get('breed','Labrador')),
        'Age':              int(form.get('age', 3)),
        'Gender_enc':       1 if form.get('gender','Male') == 'Male' else 0,
        'Weight':           float(form.get('weight', 20.0)),
        'Symptom_1_enc':    encode_safe(encoders['Symptom_1'],     form.get('symptom_1','Fever')),
        'Symptom_2_enc':    encode_safe(encoders['Symptom_2'],     form.get('symptom_2','Lethargy')),
        'Symptom_3_enc':    encode_safe(encoders['Symptom_3'],     form.get('symptom_3','Vomiting')),
        'Symptom_4_enc':    encode_safe(encoders['Symptom_4'],     form.get('symptom_4','Diarrhea')),
        'Duration_days':    duration_days,
        'Appetite_Loss':    yn(form.get('appetite_loss','No')),
        'Vomiting':         yn(form.get('vomiting','No')),
        'Diarrhea':         yn(form.get('diarrhea','No')),
        'Coughing':         yn(form.get('coughing','No')),
        'Labored_Breathing':yn(form.get('labored_breathing','No')),
        'Lameness':         yn(form.get('lameness','No')),
        'Skin_Lesions':     yn(form.get('skin_lesions','No')),
        'Nasal_Discharge':  yn(form.get('nasal_discharge','No')),
        'Eye_Discharge':    yn(form.get('eye_discharge','No')),
        'Body_Temperature': body_temp,
        'Heart_Rate':       int(form.get('heart_rate', 100)),
    }
    return np.array([[row[f] for f in FEATURE_COLS]])


@app.route('/vetscan')
def index():
    return render_template('vetscan.html',
        animal_types=ANIMAL_TYPES,
        breeds_by_animal=BREEDS_BY_ANIMAL,
        all_symptoms=ALL_SYMPTOMS,
        meta=meta
    )

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        X = build_features(data)
        proba = model.predict_proba(X)[0]
        classes = model.classes_

        # Top 5 predictions
        top_idx = np.argsort(proba)[::-1][:5]
        results = []
        for idx in top_idx:
            disease = DISEASES[classes[idx]]
            conf = float(proba[idx])
            if conf < 0.01:
                break
            results.append({
                'disease':    disease,
                'confidence': round(conf * 100, 1),
                'severity':   get_severity(disease)
            })

        if not results:
            results.append({
                'disease':    DISEASES[classes[top_idx[0]]],
                'confidence': round(float(proba[top_idx[0]]) * 100, 1),
                'severity':   'low'
            })

        return jsonify({'success': True, 'predictions': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/breeds/<animal_type>')
def get_breeds(animal_type):
    breeds = BREEDS_BY_ANIMAL.get(animal_type, [])
    return jsonify(breeds)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
