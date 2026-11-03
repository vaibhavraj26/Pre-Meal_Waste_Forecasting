import datetime
from flask import Blueprint, request, jsonify
from backend.config import get_db_status, get_database, logger, WASTE_THRESHOLD_PERCENT
from backend.database import (
    create_meal,
    get_meals,
    get_meal_by_id,
    update_meal,
    delete_meal,
    get_dashboard_stats,
    get_analytics_data,
    get_historical_context
)
from backend.ml.predict import predict_food_waste
from backend.ml.model import (
    get_performance_summary,
    train_logistic_regression_model
)
from backend.synthetic_data import FOOD_ITEMS_POOL, seed_database

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/health", methods=["GET"])
def health_check():
    """Return system and MongoDB database health status."""
    db = get_database()
    total_meals = db.meals.count_documents({})
    return jsonify({
        "status": "healthy",
        "database": get_db_status(),
        "total_meals": total_meals,
        "waste_threshold": WASTE_THRESHOLD_PERCENT,
        "server_time": datetime.datetime.now().isoformat()
    })

@api_bp.route("/foods", methods=["GET"])
def get_food_items():
    """Return catalogue of 20 food items and standard categories."""
    categories = sorted(list(set(f["category"] for f in FOOD_ITEMS_POOL)))
    return jsonify({
        "foods": FOOD_ITEMS_POOL,
        "categories": categories
    })

@api_bp.route("/dashboard/stats", methods=["GET"])
def dashboard_stats():
    """Return aggregated statistics directly from MongoDB."""
    try:
        stats = get_dashboard_stats()
        stats["db_status"] = get_db_status()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route("/predict", methods=["POST"])
def predict_meal():
    """
    ML Prediction endpoint. Accepts only pre-meal inputs,
    automatically retrieves historical records, and predicts High/Low Waste.
    """
    try:
        data = request.get_json() or {}
        required = ["date", "meal_type", "food_category", "expected_students"]
        for field in required:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        result = predict_food_waste(data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error making prediction: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route("/meals", methods=["GET"])
def list_meals():
    """List meals with filtering, search, sorting, and pagination."""
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 15))
        search = request.args.get("search", "").strip()
        meal_type = request.args.get("meal_type", "").strip()
        waste_level = request.args.get("waste_level", "").strip()
        start_date = request.args.get("start_date", "").strip()
        end_date = request.args.get("end_date", "").strip()
        sort_by = request.args.get("sort_by", "date").strip()
        sort_order = int(request.args.get("sort_order", -1))

        res = get_meals(
            page=page,
            limit=limit,
            search=search,
            meal_type=meal_type,
            waste_level=waste_level,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return jsonify(res)
    except Exception as e:
        logger.error(f"Error listing meals: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route("/meals", methods=["POST"])
def add_meal():
    """Create a new post-meal record in MongoDB."""
    try:
        data = request.get_json() or {}
        required = ["date", "meal_type", "food_prepared_kg", "food_consumed_kg"]
        for field in required:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        created = create_meal(data)
        return jsonify({"success": True, "meal": created}), 201
    except Exception as e:
        logger.error(f"Error adding meal: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route("/meals/<meal_id>", methods=["GET"])
def get_meal(meal_id):
    """Get single meal details."""
    meal = get_meal_by_id(meal_id)
    if not meal:
        return jsonify({"error": "Meal not found"}), 404
    return jsonify(meal)

@api_bp.route("/meals/<meal_id>", methods=["PUT"])
def edit_meal(meal_id):
    """Update existing meal record."""
    try:
        data = request.get_json() or {}
        updated = update_meal(meal_id, data)
        if not updated:
            return jsonify({"error": "Meal not found"}), 404
        return jsonify({"success": True, "meal": updated})
    except Exception as e:
        logger.error(f"Error updating meal: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route("/meals/<meal_id>", methods=["DELETE"])
def remove_meal(meal_id):
    """Delete a meal record from MongoDB."""
    try:
        success = delete_meal(meal_id)
        if not success:
            return jsonify({"error": "Meal not found"}), 404
        return jsonify({"success": True, "message": "Meal record deleted successfully"})
    except Exception as e:
        logger.error(f"Error deleting meal: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route("/analytics", methods=["GET"])
def analytics_hub():
    """Return comprehensive analytics data for Chart.js charts."""
    try:
        data = get_analytics_data()
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error retrieving analytics data: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route("/ml/performance", methods=["GET"])
def ml_performance():
    """Return model performance metrics and training history."""
    try:
        data = get_performance_summary()
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error retrieving ML metrics: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route("/ml/retrain", methods=["POST"])
def retrain_ml_model():
    """Retrain model with available records."""
    try:
        db = get_database()
        total_records = db.meals.count_documents({})
        if total_records < 30:
            return jsonify({
                "success": False,
                "message": f"Insufficient data to retrain model. Found {total_records} records, minimum 30 required."
            }), 400

        res = train_logistic_regression_model()
        return jsonify(res)
    except Exception as e:
        logger.error(f"Error retraining model: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route("/seed", methods=["POST"])
def trigger_seed():
    """Seed or re-seed synthetic dataset."""
    try:
        force = request.args.get("force", "false").lower() == "true"
        days = int(request.args.get("days", 400))
        res = seed_database(force=force, days=days)
        # Also trigger model retrain
        train_logistic_regression_model()
        return jsonify(res)
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        return jsonify({"error": str(e)}), 500
