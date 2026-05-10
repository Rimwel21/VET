from flask import Blueprint, render_template, request, jsonify
from app.services.prediction_service import (
    predict_disease, ANIMAL_TYPES, BREEDS_BY_ANIMAL, ALL_SYMPTOMS, meta, BREEDS_BY_ANIMAL
)

vetscan_bp = Blueprint('vetscan', __name__)


@vetscan_bp.route('/vetscan')
def vetscan():
    return render_template('vetscan.html',
                           animal_types=ANIMAL_TYPES,
                           breeds_by_animal=BREEDS_BY_ANIMAL,
                           all_symptoms=ALL_SYMPTOMS,
                           meta=meta)


@vetscan_bp.route('/predict', methods=['POST'])
def predict():
    try:
        data    = request.get_json()
        results = predict_disease(data)
        return jsonify({'success': True, 'predictions': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@vetscan_bp.route('/breeds/<animal_type>')
def get_breeds(animal_type):
    breeds = BREEDS_BY_ANIMAL.get(animal_type, [])
    return jsonify(breeds)
