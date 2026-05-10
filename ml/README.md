# Place your chatbot_ml.py file here.
# This directory (ml/) is the new home for all ML-related code and assets.
#
# Expected structure:
#   ml/
#   ├── chatbot_ml.py         ← move your AstridHybridML class here
#   ├── dataset/              ← move your dataset/ folder here
#   └── model/
#       ├── disease_model.pkl
#       ├── encoders.pkl
#       └── metadata.json
#
# The prediction_service.py (app/services/prediction_service.py) already
# points to ml/model/ for the pkl and json files.
#
# If you use AstridHybridML anywhere, import it like:
#   from ml.chatbot_ml import AstridHybridML
