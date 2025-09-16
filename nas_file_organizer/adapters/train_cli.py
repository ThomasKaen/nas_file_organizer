import os, sys, json, argparse
from nas_file_organizer.ml.train import train_and_save

def main(argv=None):
    p = argparse.ArgumentParser(prog="nas-train", description="Retrain NAS model")
    p.add_argument("--db", default=os.getenv("CACHE_DB", "/data/cache.db"))
    p.add_argument("--out", default=os.getenv("MODEL_OUT", "/data/model.pkl"))
    p.add_argument("--version", default=os.getenv("MODEL_VERSION", "tfidf-logreg-v1"))
    args = p.parse_args(argv)

    metrics = train_and_save(args.db, args.out, args.version)
    print(json.dumps(metrics or {}, indent=2))

if __name__ == "__main__":
    main()
