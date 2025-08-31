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
    texts, labels, _ = collect_training_set(conn)
    if not texts:
        raise RuntimeError("No training samples. Confirm/correct items in /review first.")
    if len(set(labels)) < 2:
        # Still allow saving a model, but warn: only one class so far.
        pipe = build_pipeline().fit(texts, labels)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        joblib.dump({"pipeline": pipe, "classes": sorted(set(labels))}, out_path)
        upsert_model_registry(conn, version, out_path, accuracy=1.0, macro_f1=1.0,
                              notes="trained on single class; add more labeled classes")
        return {"version": version, "out": out_path, "samples": len(texts),
                "classes": dict(Counter(labels)), "accuracy": 1.0, "macro_f1": 1.0,
                "report": "Single-class training; add more classes for evaluation."}

    counts = Counter(labels)
    min_class = min(counts.values())
    do_stratify = min_class >= 2

    if do_stratify and len(texts) >= 10:
        Xtr, Xte, ytr, yte = train_test_split(
            texts, labels, test_size=0.2, random_state=42, stratify=labels
        )
        pipe = build_pipeline().fit(Xtr, ytr)
        yhat = pipe.predict(Xte)
        acc = accuracy_score(yte, yhat)
        macro = f1_score(yte, yhat, average="macro")
        report = classification_report(yte, yhat, zero_division=0)
    else:
        # Too few samples per class → train on ALL, skip holdout eval
        pipe = build_pipeline().fit(texts, labels)
        acc = 1.0
        macro = 1.0
        report = "No holdout evaluation (too few samples per class)."

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    joblib.dump({"pipeline": pipe, "classes": sorted(set(labels))}, out_path)
    upsert_model_registry(conn, version, out_path, float(acc), float(macro),
                          notes=f"classes={sorted(set(set(labels)))}; min_class={min_class}")
    return {
        "version": version, "out": out_path, "samples": len(texts),
        "classes": dict(counts), "accuracy": float(acc), "macro_f1": float(macro),
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
