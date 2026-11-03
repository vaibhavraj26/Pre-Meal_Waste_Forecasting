import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from flask import Flask, jsonify
from flask_cors import CORS
from backend.config import PYTHON_PORT, logger, get_database
from backend.routes.api_routes import api_bp
from backend.synthetic_data import seed_database
from backend.ml.model import get_model_pipeline

def create_app():
    app = Flask(__name__)
    CORS(app)  # Enable cross-origin requests for Node.js frontend

    # Register API blueprint
    app.register_blueprint(api_bp)

    @app.route("/")
    def index():
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
    logger.info(f"Starting Python Flask ML backend on {host}:{PYTHON_PORT}...")
    app.run(host=host, port=PYTHON_PORT, debug=False)
