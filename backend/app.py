import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from backend.config import PYTHON_PORT, logger, get_database
from backend.routes.api_routes import api_bp
from backend.synthetic_data import seed_database
from backend.ml.model import get_model_pipeline

def create_app():
    public_path = ROOT_DIR / "frontend" / "public"
    app = Flask(__name__, static_folder=str(public_path), static_url_path="")
    CORS(app)  # Enable cross-origin requests

    # Register API blueprint
    app.register_blueprint(api_bp)

    @app.route("/")
    def index():
        return send_from_directory(public_path, "index.html")

    @app.route("/predict")
    def predict_page():
        return send_from_directory(public_path, "predict.html")

    @app.route("/add-meal")
    def add_meal_page():
        return send_from_directory(public_path, "add-meal.html")

    @app.route("/history")
    def history_page():
        return send_from_directory(public_path, "history.html")

    @app.route("/analytics")
    def analytics_page():
        return send_from_directory(public_path, "analytics.html")

    @app.route("/model")
    def model_page():
        return send_from_directory(public_path, "model.html")

    @app.route("/api")
    def api_info():
        return jsonify({
            "service": "Smart Mess Food Waste Prediction Backend & ML API",
            "version": "1.0.0",
            "status": "online",
            "endpoints": [
                "/api/health",
                "/api/dashboard/stats",
                "/api/predict",
                "/api/meals",
                "/api/analytics",
                "/api/ml/performance",
                "/api/ml/retrain",
                "/api/foods"
            ]
        })

    # Ensure database is seeded and model is ready
    with app.app_context():
        try:
            logger.info("Initializing Smart Mess backend...")
            db = get_database()
            if db.meals.count_documents({}) < 50:
                logger.info("Database records are below threshold. Running initial seed (400 days)...")
                seed_database(force=False, days=400)

            # Ensure model is ready
            get_model_pipeline()
            logger.info("Backend and ML components ready.")
        except Exception as e:
            logger.error(f"Startup initialization warning: {e}")

    return app

if __name__ == "__main__":
    app = create_app()
    host = os.getenv("PYTHON_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("PYTHON_PORT", 5000)))
    logger.info(f"Starting Python Flask ML backend on {host}:{port}...")
    app.run(host=host, port=port, debug=False)
