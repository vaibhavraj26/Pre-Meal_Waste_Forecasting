import unittest
import json
import datetime
from backend.synthetic_data import generate_synthetic_dataset, FOOD_ITEMS_POOL
from backend.database import (
    create_meal,
    get_meal_by_id,
    get_meals,
    update_meal,
    delete_meal,
    get_dashboard_stats,
    get_historical_context
)
from backend.ml.predict import predict_food_waste
from backend.ml.model import get_model_pipeline, get_performance_summary
from backend.app import create_app

class TestSmartMessSystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_01_synthetic_dataset_generation(self):
        """Verify synthetic data generates 400 continuous days and 20 food items."""
        records = generate_synthetic_dataset(num_days=400)
        self.assertEqual(len(records), 1200, "Should generate exactly 1200 meals for 400 days (3 meals/day)")

        # Verify distinct food items
        unique_foods = set()
        for r in records:
            for item in r["menu_items"]:
                unique_foods.add(item)
        self.assertEqual(len(unique_foods), 20, "Must cover all 20 distinct food items")

        # Verify arithmetic consistency
        for r in records[:50]:
            leftover = r["food_prepared_kg"] - r["food_consumed_kg"]
            expected_waste_pct = round((r["leftover_food_kg"] / r["food_prepared_kg"]) * 100.0, 2)
            self.assertAlmostEqual(r["waste_percentage"], expected_waste_pct, delta=0.5)
            if r["waste_percentage"] > 15.0:
                self.assertEqual(r["waste_level"], "HIGH")
            else:
                self.assertEqual(r["waste_level"], "LOW")

    def test_02_mongodb_crud_operations(self):
        """Test full CRUD operations on meals collection."""
        sample_meal = {
            "date": "2026-11-10",
            "meal_type": "Dinner",
            "menu_items": ["Palak Paneer & Naan"],
            "food_category": "North Indian",
            "menu_complexity": "Heavy",
            "expected_students": 450,
            "actual_attendance": 410,
            "total_hostel_population": 500,
            "food_prepared_kg": 200.0,
            "food_consumed_kg": 160.0,
            "weather": "Cold",
            "temperature": 18.0,
            "is_holiday_or_event": False
        }

        # 1. CREATE
        created = create_meal(sample_meal)
        self.assertIn("id", created)
        meal_id = created["id"]
        self.assertEqual(created["leftover_food_kg"], 40.0)
        self.assertEqual(created["waste_percentage"], 20.0)
        self.assertEqual(created["waste_level"], "HIGH")

        # 2. READ
        fetched = get_meal_by_id(meal_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["id"], meal_id)
        self.assertEqual(fetched["actual_attendance"], 410)

        # 3. UPDATE
        updated = update_meal(meal_id, {
            "food_consumed_kg": 185.0,
            "actual_attendance": 435
        })
        self.assertIsNotNone(updated)
        self.assertEqual(updated["food_consumed_kg"], 185.0)
        self.assertEqual(updated["leftover_food_kg"], 15.0)
        # 15 / 200 * 100 = 7.5% -> LOW waste
        self.assertEqual(updated["waste_percentage"], 7.5)
        self.assertEqual(updated["waste_level"], "LOW")

        # 4. DELETE
        deleted = delete_meal(meal_id)
        self.assertTrue(deleted)
        self.assertIsNone(get_meal_by_id(meal_id))

    def test_03_zero_data_leakage_historical_analysis(self):
        """Verify that historical queries strictly filter date < target_date."""
        target_date = "2026-05-01"
        res = get_historical_context(
            target_date=target_date,
            meal_type="Lunch",
            food_category="North Indian",
            menu_items=["Rajma Chawal"]
        )
        self.assertIn("has_sufficient_history", res)
        self.assertIn("meal_avg_waste", res)
        self.assertIn("category_avg_waste", res)

        # Check an early date where history < 5
        early_date = "2020-01-01"
        early_res = get_historical_context(
            target_date=early_date,
            meal_type="Lunch",
            food_category="North Indian"
        )
        self.assertFalse(early_res["has_sufficient_history"])
        self.assertIn("Insufficient historical records", early_res["message"])

    def test_04_logistic_regression_prediction(self):
        """Test pre-meal prediction logic and mitigation suggestions."""
        input_data = {
            "date": "2026-11-05",
            "meal_type": "Lunch",
            "food_category": "North Indian",
            "menu_items": ["Rajma Chawal"],
            "expected_students": 430,
            "total_hostel_population": 500,
            "is_holiday_or_event": False,
            "weather": "Sunny",
            "temperature": 28.0,
            "menu_complexity": "Moderate"
        }

        pred = predict_food_waste(input_data)
        self.assertIn(pred["prediction"], ["HIGH WASTE", "LOW WASTE"])
        self.assertIn(pred["risk_level"], ["Low Risk", "Moderate Risk", "High Risk"])
        self.assertTrue(0.0 <= pred["probability_high_waste"] <= 100.0)
        self.assertTrue(pred["recommended_food_prep_kg"] > 0)
        self.assertTrue(len(pred["suggestions"]) > 0)
        self.assertIn("historical_analysis", pred)

    def test_05_api_endpoints(self):
        """Test Flask REST API routes."""
        # Health check
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "healthy")

        # Dashboard stats
        res = self.client.get("/api/dashboard/stats")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("total_meals", data)
        self.assertIn("total_prepared_kg", data)
        self.assertIn("total_wasted_kg", data)
        self.assertIn("avg_waste_percentage", data)

        # Food catalogue
        res = self.client.get("/api/foods")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data["foods"]), 20)

        # Analytics
        res = self.client.get("/api/analytics")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("daily_trend", data)
        self.assertIn("meal_type_waste", data)
        self.assertIn("weekday_waste", data)

        # ML performance
        res = self.client.get("/api/ml/performance")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("metrics", data)
        self.assertIn("accuracy", data["metrics"])
        self.assertIn("confusion_matrix", data["metrics"])

if __name__ == "__main__":
    unittest.main()
