# nas_file_organizer/ml/train.py
import argparse
import os
import joblib
import numpy as np
from collections import Counter
from typing import Tuple, Dict, Any

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, classification_report

from .utils import connect_db, collect_training_set, upsert_model_registry

DEFAULT_DB      = os.environ.get("CACHE_DB", "/data/cache.db")
DEFAULT_OUT     = os.environ.get("MODEL_OUT", "/data/model.pkl")
DEFAULT_VERSION = os.environ.get("MODEL_VERSION", "tfidf-logreg-v1")

def build_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2)),
        ("clf",   LogisticRegression(max_iter=2000, class_weight="balanced"))
    ])

def train_and_save(db_path: str = DEFAULT_DB, out_path: str = DEFAULT_OUT,
                   version: str = DEFAULT_VERSION) -> Dict[str, Any]:
    conn = connect_db(db_path)
    texts, labels, hashes = collect_training_set(conn)
    if not texts:
        raise RuntimeError("No training samples. Confirm/correct items in /review first.")

    # Basic sanity: must have at least 2 classes
    if len(set(labels)) < 2:
        raise RuntimeError("Need at least two classes to train. Add more labeled samples.")

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )

    pipe = build_pipeline()
    pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    macro = f1_score(y_test, y_pred, average="macro")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    joblib.dump({"pipeline": pipe, "classes": sorted(set(labels))}, out_path)

    report = classification_report(y_test, y_pred, zero_division=0)

    upsert_model_registry(conn, version, out_path, float(acc), float(macro),
                          notes=f"classes={sorted(set(labels))}")

    return {
        "version": version,
        "out": out_path,
        "samples": len(texts),
        "classes": dict(Counter(labels)),
        "accuracy": float(acc),
        "macro_f1": float(macro),
        "report": report
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DEFAULT_DB, help="Path to cache DB (CACHE_DB)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="Model output path (MODEL_OUT)")
    ap.add_argument("--version", default=DEFAULT_VERSION, help="Model registry version")
    args = ap.parse_args()

    res = train_and_save(args.db, args.out, args.version)
    print("Saved:", res["out"])
    print("Samples:", res["samples"], "Classes:", res["classes"])
    print("Accuracy:", round(res["accuracy"], 4), "Macro-F1:", round(res["macro_f1"], 4))
    print(res["report"])

if __name__ == "__main__":
    main()
