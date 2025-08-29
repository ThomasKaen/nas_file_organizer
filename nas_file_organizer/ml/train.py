import argparse
import os
import joblib
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, classification_report
from .utils import connect_db, collect_training_set, upsert_model_registry

DEFAULT_DB = os.environ.get("CACHE_DB", "/data/cache.db")
DEFAULT_OUT = os.environ.get("MODEL_OUT", "/data/model.pkl")
DEFAULT_ARCHIVE = os.environ.get("ARCHIVE_ROOT", "/data/archive")


def build_pipeline(max_features: int = 100_000) -> Pipeline:
    return Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1,2), max_features=max_features)),
    ("clf", LogisticRegression(max_iter=400, n_jobs=None, class_weight="balanced"))
    ])

def main():
    ap = argparse.ArgumentParser(description="Train NAS classifier and save model.pkl")
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--archive-root", default=DEFAULT_ARCHIVE)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--version", default="v1")
    args = ap.parse_args()

    conn = connect_db(args.db)
    texts, labels, hashes = collect_training_set(conn, args.archive_root)
    if len(texts) < 20:
        raise SystemExit("Not enough samples in archive to train (need >= 20)")

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )

    pipe = build_pipeline()
    pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    macro = f1_score(y_test, y_pred, average="macro")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    joblib.dump({"pipeline": pipe, "classes": sorted(set(labels))}, args.out)

    print("Saved:", args.out)
    print("Accuracy:", round(acc, 4), "Macro-F1:", round(macro, 4))
    print(classification_report(y_test, y_pred))

    upsert_model_registry(conn, args.version, args.out, float(acc), float(macro), notes="tfidf+logreg")

if __name__ == "__main__":
    main()