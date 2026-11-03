import os
import sys
import json
import datetime
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_auc_score,
    classification_report
)

from backend.config import get_database, DATA_DIR, MIN_RETRAIN_RECORDS, logger

MODEL_PATH = DATA_DIR / "food_waste_model.joblib"
METRICS_PATH = DATA_DIR / "model_metrics.json"

CATEGORICAL_FEATURES = ["meal_type", "food_category", "menu_complexity", "weather"]
NUMERICAL_FEATURES = [
    "expected_students",
    "total_hostel_population",
    "attendance_ratio",
    "temperature",
    "is_holiday_or_event",
    "day_of_week_num",
    "historical_meal_avg_waste",
    "historical_category_avg_waste",
    "historical_item_avg_waste",
    "historical_weekday_avg_waste"
]

def prepare_dataset_from_mongo():
    """
    Load meal records from MongoDB and engineer training features.
    Computes prior historical averages using expanding historical windows to prevent data leakage.
    """
    db = get_database()
    records = list(db.meals.find().sort([("date", 1), ("meal_type", 1)]))

    if len(records) < 20:
        logger.warning(f"Insufficient meal records for training (found {len(records)}).")
        return None

    df = pd.DataFrame(records)

    # Basic type casting
    df["date"] = pd.to_datetime(df["date"])
    df["expected_students"] = pd.to_numeric(df["expected_students"], errors="coerce").fillna(400)
    df["total_hostel_population"] = pd.to_numeric(df["total_hostel_population"], errors="coerce").fillna(500)
    df["attendance_ratio"] = df["expected_students"] / df["total_hostel_population"]
    df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce").fillna(28.0)
    df["is_holiday_or_event"] = df["is_holiday_or_event"].astype(int)
    df["day_of_week_num"] = pd.to_numeric(df.get("day_of_week_num", df["date"].dt.weekday), errors="coerce").fillna(0)
    df["first_menu_item"] = df["menu_items"].apply(lambda items: items[0] if isinstance(items, list) and len(items) > 0 else "General")

    # Target variable
    if "is_high_waste" in df.columns:
        df["target"] = df["is_high_waste"].astype(int)
    else:
        df["target"] = (df["waste_percentage"] > 15.0).astype(int)

    # Compute expanding historical averages prior to each date (strictly prevents leakage)
    # Group by meal_type, food_category, item, and weekday expanding means
    df = df.sort_values(by=["date", "meal_type"]).reset_index(drop=True)

    # Shifted cumulative expanding mean by meal_type
    df["historical_meal_avg_waste"] = (
        df.groupby("meal_type")["waste_percentage"]
        .transform(lambda x: x.shift(1).expanding().mean())
        .fillna(15.0)
    )

    # Shifted cumulative expanding mean by food_category
    df["historical_category_avg_waste"] = (
        df.groupby("food_category")["waste_percentage"]
        .transform(lambda x: x.shift(1).expanding().mean())
        .fillna(15.0)
    )

    # Shifted cumulative expanding mean by menu item
    df["historical_item_avg_waste"] = (
        df.groupby("first_menu_item")["waste_percentage"]
        .transform(lambda x: x.shift(1).expanding().mean())
        .fillna(15.0)
    )

    # Shifted cumulative expanding mean by day_of_week_num
    df["historical_weekday_avg_waste"] = (
        df.groupby("day_of_week_num")["waste_percentage"]
        .transform(lambda x: x.shift(1).expanding().mean())
        .fillna(15.0)
    )

    return df

def train_logistic_regression_model():
    """
    Train Scikit-learn Logistic Regression model on historical dataset,
    evaluate performance metrics, extract interpretable feature weights,
    and persist model and evaluation metrics.
    """
    df = prepare_dataset_from_mongo()
    if df is None or len(df) < 30:
        return {
            "success": False,
            "message": "Insufficient records to train model (minimum 30 required)."
        }

    X = df[CATEGORICAL_FEATURES + NUMERICAL_FEATURES]
    y = df["target"]

    # Stratified train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
            ("num", StandardScaler(), NUMERICAL_FEATURES)
        ]
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42, C=1.0))
        ]
    )

    pipeline.fit(X_train, y_train)

    # Predictions & Probabilities
    y_pred = pipeline.predict(X_test)
    y_pred_proba = pipeline.predict_proba(X_test)[:, 1]

    # Metrics
    acc = float(accuracy_score(y_test, y_pred))
    prec = float(precision_score(y_test, y_pred, zero_division=0))
    rec = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    try:
        roc_auc = float(roc_auc_score(y_test, y_pred_proba))
    except Exception:
        roc_auc = 0.5

    cm = confusion_matrix(y_test, y_pred).tolist()
    # Format: [[True Negative, False Positive], [False Negative, True Positive]]
    tn, fp, fn, tp = int(cm[0][0]), int(cm[0][1]), int(cm[1][0]), int(cm[1][1])

    # Extract Feature Importance / Coefficients
    clf = pipeline.named_steps["classifier"]
    encoded_cat_names = pipeline.named_steps["preprocessor"].named_transformers_["cat"].get_feature_names_out(CATEGORICAL_FEATURES)
    all_feature_names = list(encoded_cat_names) + NUMERICAL_FEATURES
    coefficients = clf.coef_[0]

    feature_importance = [
        {"feature": name, "weight": round(float(coef), 4), "impact": "Increases Waste" if coef > 0 else "Decreases Waste"}
        for name, coef in zip(all_feature_names, coefficients)
    ]
    feature_importance.sort(key=lambda x: abs(x["weight"]), reverse=True)

    timestamp = datetime.datetime.now().isoformat()
    metrics_data = {
        "model_name": "Logistic Regression Classifier",
        "last_trained": timestamp,
        "total_records_trained": len(df),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "accuracy": round(acc * 100, 2),
        "precision": round(prec * 100, 2),
        "recall": round(rec * 100, 2),
        "f1_score": round(f1 * 100, 2),
        "roc_auc": round(roc_auc * 100, 2),
        "confusion_matrix": {
            "raw": cm,
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn,
            "true_positives": tp
        },
        "top_risk_factors": feature_importance[:12],
        "status": "ready"
    }

    # Save pipeline
    joblib.dump(pipeline, MODEL_PATH)

    # Save metrics JSON
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)

    # Record training history into MongoDB
    db = get_database()
    history_entry = {
        "timestamp": timestamp,
        "total_records": len(df),
        "accuracy": metrics_data["accuracy"],
        "precision": metrics_data["precision"],
        "recall": metrics_data["recall"],
        "f1_score": metrics_data["f1_score"],
        "roc_auc": metrics_data["roc_auc"],
        "confusion_matrix": metrics_data["confusion_matrix"]
    }
    db.training_history.insert_one(history_entry)

    logger.info(f"Model trained successfully! Accuracy: {metrics_data['accuracy']}%, F1: {metrics_data['f1_score']}%")
    return {
        "success": True,
        "message": "Model trained and evaluated successfully.",
        "metrics": metrics_data
    }

def get_model_pipeline():
    """Load model pipeline from disk, or train on the fly if not exists."""
    if MODEL_PATH.exists():
        try:
            return joblib.load(MODEL_PATH)
        except Exception as e:
            logger.warning(f"Error loading model from {MODEL_PATH}: {e}")

    logger.info("Model file not found or corrupted. Triggering fresh model training...")
    res = train_logistic_regression_model()
    if res.get("success") and MODEL_PATH.exists():
        return joblib.load(MODEL_PATH)
    return None

def get_performance_summary():
    """Return model performance metrics and training history."""
    if METRICS_PATH.exists():
        try:
            with open(METRICS_PATH, "r", encoding="utf-8") as f:
                metrics = json.load(f)
        except Exception:
            metrics = None
    else:
        metrics = None

    if not metrics:
        res = train_logistic_regression_model()
        metrics = res.get("metrics")

    # Fetch training history from MongoDB
    db = get_database()
    history_cursor = db.training_history.find({}, {"_id": 0}).sort("timestamp", -1).limit(10)
    training_history = list(history_cursor)

    total_meals = db.meals.count_documents({})
    can_retrain = bool(total_meals >= MIN_RETRAIN_RECORDS)

    return {
        "metrics": metrics,
        "training_history": training_history,
        "total_available_meals": total_meals,
        "can_retrain": can_retrain,
        "min_retrain_threshold": MIN_RETRAIN_RECORDS
    }

if __name__ == "__main__":
    print("Training Logistic Regression Model...")
    res = train_logistic_regression_model()
    print("Result:", res)
