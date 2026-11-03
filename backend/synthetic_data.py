import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import random
import datetime
from backend.config import get_database, sync_mock_storage, WASTE_THRESHOLD_PERCENT, logger

# 20 Distinct Food Items
FOOD_ITEMS_POOL = [
    {"name": "Poha", "category": "South/West Indian", "meal_types": ["Breakfast"], "complexity": "Simple", "base_waste_prob": 0.12},
    {"name": "Idli Sambar", "category": "South Indian", "meal_types": ["Breakfast"], "complexity": "Simple", "base_waste_prob": 0.15},
    {"name": "Aloo Paratha", "category": "North Indian", "meal_types": ["Breakfast"], "complexity": "Moderate", "base_waste_prob": 0.20},
    {"name": "Puri Bhaji", "category": "North Indian", "meal_types": ["Breakfast"], "complexity": "Heavy", "base_waste_prob": 0.28},
    {"name": "Masala Dosa", "category": "South Indian", "meal_types": ["Breakfast"], "complexity": "Moderate", "base_waste_prob": 0.18},
    {"name": "Upma", "category": "South Indian", "meal_types": ["Breakfast"], "complexity": "Simple", "base_waste_prob": 0.22},
    {"name": "Chole Bhature", "category": "North Indian", "meal_types": ["Breakfast", "Lunch"], "complexity": "Heavy", "base_waste_prob": 0.32},
    {"name": "Rajma Chawal", "category": "North Indian", "meal_types": ["Lunch"], "complexity": "Moderate", "base_waste_prob": 0.16},
    {"name": "Paneer Butter Masala & Roti", "category": "North Indian", "meal_types": ["Dinner"], "complexity": "Heavy", "base_waste_prob": 0.15},
    {"name": "Dal Tadka & Jeera Rice", "category": "North Indian", "meal_types": ["Lunch", "Dinner"], "complexity": "Simple", "base_waste_prob": 0.14},
    {"name": "Veg Biryani", "category": "Mughlai/Special", "meal_types": ["Lunch", "Dinner"], "complexity": "Heavy", "base_waste_prob": 0.30},
    {"name": "Kadhi Pakoda & Rice", "category": "North Indian", "meal_types": ["Lunch"], "complexity": "Moderate", "base_waste_prob": 0.24},
    {"name": "Sambar Rice", "category": "South Indian", "meal_types": ["Lunch"], "complexity": "Simple", "base_waste_prob": 0.13},
    {"name": "Mixed Veg & Chapati", "category": "North Indian", "meal_types": ["Lunch", "Dinner"], "complexity": "Simple", "base_waste_prob": 0.21},
    {"name": "Palak Paneer & Naan", "category": "North Indian", "meal_types": ["Dinner"], "complexity": "Heavy", "base_waste_prob": 0.18},
    {"name": "Aloo Gobi & Roti", "category": "North Indian", "meal_types": ["Lunch", "Dinner"], "complexity": "Simple", "base_waste_prob": 0.25},
    {"name": "Egg Curry & Rice", "category": "Non-Veg", "meal_types": ["Dinner"], "complexity": "Moderate", "base_waste_prob": 0.17},
    {"name": "Chicken Curry & Rice", "category": "Non-Veg", "meal_types": ["Dinner"], "complexity": "Heavy", "base_waste_prob": 0.16},
    {"name": "Matar Paneer & Paratha", "category": "North Indian", "meal_types": ["Dinner"], "complexity": "Heavy", "base_waste_prob": 0.19},
    {"name": "Veg Pulao & Raita", "category": "North Indian", "meal_types": ["Lunch", "Dinner"], "complexity": "Moderate", "base_waste_prob": 0.22}
]

WEATHER_TYPES = ["Sunny", "Rainy", "Cold", "Humid", "Hot"]

def generate_synthetic_dataset(num_days=400, end_date=None):
    """
    Generate around 400 continuous days of synthetic meal records (Breakfast, Lunch, Dinner).
    Incorporates realistic attendance variances, weather, weekday trends, and food complexity.
    """
    random.seed(42)  # Reproducible dataset
    if end_date is None:
        end_date = datetime.date.today() - datetime.timedelta(days=1)

    start_date = end_date - datetime.timedelta(days=num_days - 1)
    records = []
    hostel_population = 500

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.isoformat()
        weekday_name = current_date.strftime("%A")
        weekday_num = current_date.weekday()  # 5=Saturday, 6=Sunday
        month = current_date.month

        # Weather simulation by season
        if month in [6, 7, 8]:
            weather = random.choices(["Rainy", "Humid", "Sunny"], weights=[0.6, 0.3, 0.1])[0]
            temperature = round(random.uniform(25.0, 31.0), 1)
        elif month in [4, 5]:
            weather = random.choices(["Hot", "Sunny"], weights=[0.7, 0.3])[0]
            temperature = round(random.uniform(34.0, 42.0), 1)
        elif month in [12, 1]:
            weather = random.choices(["Cold", "Sunny"], weights=[0.7, 0.3])[0]
            temperature = round(random.uniform(12.0, 20.0), 1)
        else:
            weather = random.choices(WEATHER_TYPES, weights=[0.4, 0.2, 0.1, 0.2, 0.1])[0]
            temperature = round(random.uniform(22.0, 32.0), 1)

        # Holiday or Special Event (~10% probability, higher on festivals)
        is_holiday = random.random() < 0.08
        if weekday_num in [5, 6] and random.random() < 0.15:
            is_holiday = True

        event_details = "None"
        if is_holiday:
            event_details = random.choice(["Campus Fest", "National Holiday", "Exam Preparatory Leave", "Sports Tournament", "Long Weekend Outing"])

        for meal_type in ["Breakfast", "Lunch", "Dinner"]:
            # Filter available foods for this meal type
            valid_foods = [f for f in FOOD_ITEMS_POOL if meal_type in f["meal_types"]]
            chosen_food = random.choice(valid_foods)
            food_category = chosen_food["category"]
            complexity = chosen_food["complexity"]
            menu_item_name = chosen_food["name"]

            # Expected students base
            if meal_type == "Breakfast":
                base_expected = int(hostel_population * random.uniform(0.65, 0.80))
            elif meal_type == "Lunch":
                base_expected = int(hostel_population * random.uniform(0.80, 0.92))
            else:  # Dinner
                base_expected = int(hostel_population * random.uniform(0.85, 0.95))

            # Weekend drops
            if weekday_num in [5, 6]:
                expected_students = int(base_expected * random.uniform(0.70, 0.85))
            else:
                expected_students = base_expected

            # Actual attendance variation
            # If holiday, turnout can drop drastically if students go out, or spike if stuck in hostel
            if is_holiday:
                turnout_factor = random.uniform(0.55, 0.90)
            elif weekday_num == 6:  # Sunday
                turnout_factor = random.uniform(0.65, 0.85)
            elif weather == "Rainy":
                turnout_factor = random.uniform(0.85, 0.98)  # More people stay indoors
            elif weather == "Hot" and complexity == "Heavy":
                turnout_factor = random.uniform(0.70, 0.85)  # Less appetite for heavy food
            else:
                turnout_factor = random.uniform(0.82, 0.98)

            actual_attendance = max(50, int(expected_students * turnout_factor))

            # Food prepared based on expected students (~0.40 - 0.45 kg per student)
            portion_kg_per_student = random.uniform(0.38, 0.44)
            # Organiser usually prepares buffer (+5% to +15%)
            safety_buffer = random.uniform(1.05, 1.15)
            food_prepared_kg = round(expected_students * portion_kg_per_student * safety_buffer, 1)

            # Food consumed based on actual attendance
            actual_consumption_rate = random.uniform(0.35, 0.42)
            food_consumed_kg = round(min(food_prepared_kg * 0.95, actual_attendance * actual_consumption_rate), 1)

            leftover_food_kg = round(max(0.0, food_prepared_kg - food_consumed_kg), 1)
            waste_percentage = round((leftover_food_kg / food_prepared_kg) * 100.0, 2) if food_prepared_kg > 0 else 0.0

            is_high_waste = bool(waste_percentage > WASTE_THRESHOLD_PERCENT)
            waste_level = "HIGH" if is_high_waste else "LOW"

            record = {
                "date": date_str,
                "meal_type": meal_type,
                "menu_items": [menu_item_name],
                "food_category": food_category,
                "menu_complexity": complexity,
                "expected_students": expected_students,
                "actual_attendance": actual_attendance,
                "total_hostel_population": hostel_population,
                "is_holiday_or_event": is_holiday,
                "event_details": event_details,
                "weather": weather,
                "temperature": temperature,
                "food_prepared_kg": food_prepared_kg,
                "food_consumed_kg": food_consumed_kg,
                "leftover_food_kg": leftover_food_kg,
                "waste_percentage": waste_percentage,
                "is_high_waste": is_high_waste,
                "waste_level": waste_level,
                "day_of_week": weekday_name,
                "day_of_week_num": weekday_num,
                "month": month,
                "year": current_date.year,
                "is_synthetic": True,
                "created_at": f"{date_str}T21:00:00"
            }
            records.append(record)

        current_date += datetime.timedelta(days=1)

    logger.info(f"Generated {len(records)} synthetic meal records across {num_days} continuous days.")
    return records

def seed_database(force=False, days=400):
    """Seed MongoDB with synthetic records if count is low or forced."""
    db = get_database()
    current_count = db.meals.count_documents({})

    if current_count >= 100 and not force:
        logger.info(f"Database already contains {current_count} meal records. Skipping seed.")
        return {"status": "skipped", "count": current_count}

    if force and current_count > 0:
        logger.info("Force seed requested. Purging existing synthetic records...")
        db.meals.delete_many({"is_synthetic": True})

    records = generate_synthetic_dataset(num_days=days)
    if records:
        db.meals.insert_many(records)
        sync_mock_storage()
        total_now = db.meals.count_documents({})
        logger.info(f"Database successfully seeded! Total records now: {total_now}")
        return {"status": "success", "inserted": len(records), "total": total_now}

    return {"status": "empty", "total": current_count}

if __name__ == "__main__":
    print("Running synthetic data seeder...")
    result = seed_database(force=True, days=400)
    print("Seed result:", result)
