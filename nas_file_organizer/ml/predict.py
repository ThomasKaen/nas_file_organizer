import os
import joblib
from typing import Tuple
from .utils import normalize_text


MODEL_PATH = os.environ.get("MODEL_PATH", "/data/model.pkl")


class MLPredictor:
    def __init__(self, model_path: str = MODEL_PATH):
        obj = joblib.load(model_path)
        self.pipe = obj["pipeline"]
    def predict(self, text: str) -> Tuple[str, float]:
        text = normalize_text(text)
        proba = self.pipe.predict_proba([text])[0]
        idx = int(proba.argmax())
        label = self.pipe.classes_[idx]
        conf = float(proba[idx])
        return label, conf