import os
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score

print("VetScan Advanced ML Pipeline: Initiating...")

# ---------------------------------------------------------
# 1. SYNTHESIZE ADVANCED CLINICAL DATASET
# ---------------------------------------------------------
np.random.seed(42)

# Expanded Species & Breeds
ANIMAL_TYPES = ['Dog', 'Cat', 'Cow', 'Horse', 'Goat', 'Pig', 'Rabbit', 'Sheep', 'Bird']
BREEDS = {
    'Dog': ['Labrador', 'German Shepherd', 'Beagle', 'Bulldog', 'Poodle', 'Mixed'],
    'Cat': ['Siamese', 'Persian', 'Maine Coon', 'Bengal', 'Sphynx', 'Mixed'],
    'Cow': ['Holstein', 'Jersey', 'Angus', 'Hereford', 'Mixed'],
    'Horse': ['Arabian', 'Quarter Horse', 'Thoroughbred', 'Appaloosa', 'Mixed'],
    'Goat': ['Boer', 'Nubian', 'Alpine', 'LaMancha', 'Mixed'],
    'Pig': ['Yorkshire', 'Duroc', 'Hampshire', 'Berkshire', 'Mixed'],
    'Rabbit': ['Holland Lop', 'Mini Rex', 'Flemish Giant', 'Angora', 'Mixed'],
    'Sheep': ['Merino', 'Rambouillet', 'Dorper', 'Suffolk', 'Mixed'],
    'Bird': ['Parrot', 'Canary', 'Cockatiel', 'Finch', 'Mixed']
}

# Symptom Vocabulary
SYMPTOMS = [
    'None', 'Fever', 'Lethargy', 'Vomiting', 'Diarrhea', 'Coughing',
    'Sneezing', 'Loss of Appetite', 'Weight Loss', 'Lameness', 'Swelling',
    'Seizures', 'Skin Lesions', 'Hair Loss', 'Itching', 'Nasal Discharge',
    'Eye Discharge', 'Bleeding', 'Abdominal Pain', 'Aggression', 'Paralysis'
]

# Disease Profiles (Rules for synthetic generation)
DISEASE_PROFILES = {
    'Parvovirus': {'species': ['Dog'], 'symptoms': ['Vomiting', 'Diarrhea', 'Lethargy', 'Fever'], 'vitals': {'temp': 40.5, 'hr': 140}, 'flags': {'Vomiting': 1, 'Diarrhea': 1, 'Appetite_Loss': 1}},
    'Canine Distemper': {'species': ['Dog'], 'symptoms': ['Coughing', 'Nasal Discharge', 'Eye Discharge', 'Fever', 'Seizures'], 'vitals': {'temp': 40.0, 'hr': 130}, 'flags': {'Coughing': 1, 'Nasal_Discharge': 1}},
    'Feline Panleukopenia': {'species': ['Cat'], 'symptoms': ['Vomiting', 'Diarrhea', 'Lethargy', 'Fever'], 'vitals': {'temp': 40.5, 'hr': 180}, 'flags': {'Vomiting': 1, 'Diarrhea': 1, 'Appetite_Loss': 1}},
    'Rabies': {'species': ['Dog', 'Cat', 'Cow', 'Horse'], 'symptoms': ['Aggression', 'Seizures', 'Paralysis', 'Lethargy'], 'vitals': {'temp': 39.5, 'hr': 120}, 'flags': {}},
    'Bovine Mastitis': {'species': ['Cow', 'Goat', 'Sheep'], 'symptoms': ['Swelling', 'Fever', 'Lethargy', 'Pain'], 'vitals': {'temp': 40.0, 'hr': 80}, 'flags': {}},
    'Equine Influenza': {'species': ['Horse'], 'symptoms': ['Coughing', 'Nasal Discharge', 'Fever', 'Lethargy'], 'vitals': {'temp': 39.5, 'hr': 60}, 'flags': {'Coughing': 1, 'Nasal_Discharge': 1}},
    'African Swine Fever': {'species': ['Pig'], 'symptoms': ['Fever', 'Skin Lesions', 'Lethargy', 'Bleeding', 'Diarrhea'], 'vitals': {'temp': 41.0, 'hr': 100}, 'flags': {'Skin_Lesions': 1, 'Diarrhea': 1}},
    'Gastroenteritis': {'species': ['Dog', 'Cat', 'Pig'], 'symptoms': ['Vomiting', 'Diarrhea', 'Abdominal Pain', 'Lethargy'], 'vitals': {'temp': 39.0, 'hr': 110}, 'flags': {'Vomiting': 1, 'Diarrhea': 1}},
    'Ringworm': {'species': ['Dog', 'Cat', 'Cow', 'Horse', 'Rabbit', 'Goat'], 'symptoms': ['Skin Lesions', 'Hair Loss', 'Itching', 'None'], 'vitals': {'temp': 38.5, 'hr': 90}, 'flags': {'Skin_Lesions': 1}},
    'Kennel Cough': {'species': ['Dog'], 'symptoms': ['Coughing', 'Sneezing', 'Nasal Discharge', 'None'], 'vitals': {'temp': 38.8, 'hr': 110}, 'flags': {'Coughing': 1, 'Nasal_Discharge': 1}},
    'Lyme Disease': {'species': ['Dog', 'Horse'], 'symptoms': ['Lameness', 'Fever', 'Swelling', 'Lethargy'], 'vitals': {'temp': 39.5, 'hr': 100}, 'flags': {'Lameness': 1}},
    'Pneumonia': {'species': ['Dog', 'Cat', 'Cow', 'Horse', 'Sheep', 'Goat', 'Pig'], 'symptoms': ['Coughing', 'Labored Breathing', 'Fever', 'Lethargy', 'Nasal Discharge'], 'vitals': {'temp': 40.0, 'hr': 120}, 'flags': {'Coughing': 1, 'Labored_Breathing': 1, 'Nasal_Discharge': 1}},
    'Intestinal Parasites': {'species': ['Dog', 'Cat', 'Cow', 'Horse', 'Pig', 'Sheep', 'Goat'], 'symptoms': ['Weight Loss', 'Diarrhea', 'Vomiting', 'Lethargy', 'None'], 'vitals': {'temp': 38.5, 'hr': 100}, 'flags': {'Diarrhea': 1}},
    'Healthy': {'species': ANIMAL_TYPES, 'symptoms': ['None', 'None', 'None', 'None'], 'vitals': {'temp': 38.0, 'hr': 80}, 'flags': {}}
}

# Generate 20,000 samples for robust training
N_SAMPLES = 20000
data = []

for _ in range(N_SAMPLES):
    disease = np.random.choice(list(DISEASE_PROFILES.keys()))
    prof = DISEASE_PROFILES[disease]
    animal = np.random.choice(prof['species'])
    breed = np.random.choice(BREEDS[animal])
    age = np.random.randint(1, 15)
    gender = np.random.choice(['Male', 'Female'])
    weight = np.random.uniform(2.0, 500.0) if animal in ['Cow', 'Horse'] else np.random.uniform(1.0, 40.0)
    
    # Vitlas with noise
    temp = np.random.normal(prof['vitals']['temp'], 0.5)
    hr = int(np.random.normal(prof['vitals']['hr'], 10))
    duration = np.random.randint(1, 14)
    
    # Select up to 4 symptoms
    symptom_pool = prof['symptoms']
    symps = np.random.choice(symptom_pool, 4, replace=True)
    if 'None' not in symps and np.random.rand() > 0.5:
        symps[3] = 'None'
    
    row = {
        'Animal_Type': animal,
        'Breed': breed,
        'Age': age,
        'Gender': gender,
        'Weight': round(weight, 1),
        'Symptom_1': symps[0],
        'Symptom_2': symps[1],
        'Symptom_3': symps[2],
        'Symptom_4': symps[3],
        'Duration_days': duration,
        'Appetite_Loss': 1 if 'Appetite_Loss' in prof['flags'] else np.random.choice([0, 1], p=[0.8, 0.2]),
        'Vomiting': 1 if 'Vomiting' in prof['flags'] else np.random.choice([0, 1], p=[0.9, 0.1]),
        'Diarrhea': 1 if 'Diarrhea' in prof['flags'] else np.random.choice([0, 1], p=[0.9, 0.1]),
        'Coughing': 1 if 'Coughing' in prof['flags'] else np.random.choice([0, 1], p=[0.9, 0.1]),
        'Labored_Breathing': 1 if 'Labored_Breathing' in prof['flags'] else np.random.choice([0, 1], p=[0.9, 0.1]),
        'Lameness': 1 if 'Lameness' in prof['flags'] else np.random.choice([0, 1], p=[0.95, 0.05]),
        'Skin_Lesions': 1 if 'Skin_Lesions' in prof['flags'] else np.random.choice([0, 1], p=[0.95, 0.05]),
        'Nasal_Discharge': 1 if 'Nasal_Discharge' in prof['flags'] else np.random.choice([0, 1], p=[0.9, 0.1]),
        'Eye_Discharge': 1 if 'Eye_Discharge' in prof['flags'] else np.random.choice([0, 1], p=[0.9, 0.1]),
        'Body_Temperature': round(temp, 1),
        'Heart_Rate': hr,
        'Disease': disease
    }
    data.append(row)

df = pd.DataFrame(data)

# ---------------------------------------------------------
# 2. DATA PREPROCESSING & ENCODING
# ---------------------------------------------------------
encoders = {}
categorical_cols = ['Animal_Type', 'Breed', 'Gender', 'Symptom_1', 'Symptom_2', 'Symptom_3', 'Symptom_4']

for col in categorical_cols:
    le = LabelEncoder()
    # Fit on all possible values for robustness
    if col == 'Animal_Type':
        le.fit(ANIMAL_TYPES + ['Unknown'])
    elif col == 'Breed':
        all_breeds = [b for blist in BREEDS.values() for b in blist]
        le.fit(all_breeds + ['Unknown', 'Mixed'])
    elif col == 'Gender':
        le.fit(['Male', 'Female', 'Unknown'])
    elif col.startswith('Symptom'):
        le.fit(SYMPTOMS + ['Unknown'])
        
    df[col + '_enc'] = le.transform(df[col].apply(lambda x: x if x in le.classes_ else 'Unknown'))
    encoders[col] = le

# Target encoding
le_target = LabelEncoder()
df['Disease_enc'] = le_target.fit_transform(df['Disease'])

FEATURE_COLS = [
    'Animal_Type_enc', 'Breed_enc', 'Age', 'Gender_enc', 'Weight',
    'Symptom_1_enc', 'Symptom_2_enc', 'Symptom_3_enc', 'Symptom_4_enc',
    'Duration_days', 'Appetite_Loss', 'Vomiting', 'Diarrhea', 'Coughing',
    'Labored_Breathing', 'Lameness', 'Skin_Lesions', 'Nasal_Discharge',
    'Eye_Discharge', 'Body_Temperature', 'Heart_Rate'
]

X = df[FEATURE_COLS]
y = df['Disease_enc']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# ---------------------------------------------------------
# 3. ADVANCED MODEL TRAINING & CALIBRATION
# ---------------------------------------------------------
print("Training HistGradientBoostingClassifier ensemble...")
# HistGradientBoosting is fast and highly performant for tabular data
base_model = HistGradientBoostingClassifier(
    max_iter=200, 
    learning_rate=0.1, 
    max_leaf_nodes=31,
    random_state=42
)

# Use CalibratedClassifierCV to ensure predictive probabilities are well-calibrated (Dependable clinical outputs)
calibrated_model = CalibratedClassifierCV(base_model, method='isotonic', cv=5)
calibrated_model.fit(X_train, y_train)

# Evaluation
y_pred = calibrated_model.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"Validation Accuracy: {acc * 100:.2f}%")
print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=le_target.classes_))

# ---------------------------------------------------------
# 4. SAVE ASSETS
# ---------------------------------------------------------
os.makedirs('model', exist_ok=True)
calibrated_model.classes_ = le_target.classes_  # Attach classes for prediction_service.py

joblib.dump(calibrated_model, 'model/disease_model.pkl')
joblib.dump(encoders, 'model/encoders.pkl')

meta = {
    "feature_cols": FEATURE_COLS,
    "animal_types": ANIMAL_TYPES,
    "breeds_by_animal": BREEDS,
    "all_symptoms": SYMPTOMS,
    "diseases": {str(i): cls for i, cls in enumerate(le_target.classes_)}
}

with open('model/metadata.json', 'w') as f:
    json.dump(meta, f, indent=2)

print("VetScan Engine successfully upgraded. Assets saved to ml/model/")
