import datetime
import pandas as pd
from backend.database import get_historical_context
from backend.ml.model import (
    get_model_pipeline,
    CATEGORICAL_FEATURES,
    NUMERICAL_FEATURES
)
from backend.config import logger

def generate_waste_reduction_suggestions(input_data, p_high, historical_info):
    """
    Generate actionable, contextual suggestions for the mess organiser to prevent food waste.
    """
    suggestions = []
    meal_type = input_data.get("meal_type", "Meal")
    expected_students = int(input_data.get("expected_students", 400))
    total_population = int(input_data.get("total_hostel_population", 500))
    is_holiday = bool(input_data.get("is_holiday_or_event", False))
    weather = input_data.get("weather", "Sunny")
    complexity = input_data.get("menu_complexity", "Moderate")
    weekday = historical_info.get("target_weekday", "Weekday")

    # Estimate safe food preparation recommendation
    std_portion_kg = 0.40  # kg per student on average
    recommended_kg = round(expected_students * std_portion_kg * 1.05, 1)  # 5% buffer

    # 1. High Risk Warning & Preparation Sizing
    if p_high >= 0.65:
        scaled_students = max(50, int(expected_students * 0.82))
        scaled_kg = round(scaled_students * std_portion_kg, 1)
        suggestions.append({
            "type": "danger",
            "title": "High Waste Risk Alert",
            "text": f"This meal exhibits a {round(p_high * 100, 1)}% probability of exceeding the 15% waste threshold. Recommend sizing preparation for {scaled_students} students (~{scaled_kg} kg) instead of {expected_students} students (~{recommended_kg} kg)."
        })
    elif p_high >= 0.35:
        suggestions.append({
            "type": "warning",
            "title": "Moderate Waste Risk",
            "text": f"Moderate waste probability ({round(p_high * 100, 1)}%). Keep buffer tight at +5% max (recommend preparing ~{recommended_kg} kg)."
        })
    else:
        suggestions.append({
            "type": "success",
            "title": "Low Waste Risk",
            "text": f"Predicted turnout and consumption are stable ({round(p_high * 100, 1)}% high-waste probability). Standard preparation quantity (~{recommended_kg} kg) is suitable."
        })

    # 2. Weekend / Holiday Dips
    if is_holiday or weekday in ["Saturday", "Sunday"]:
        suggestions.append({
            "type": "warning",
            "title": "Turnout Variance on Weekends / Events",
            "text": f"Attendance on {weekday}s and event days typically dips by 15-25%. Adopt staggered cooking (prepare 60% first, replenish based on dining counter crowd)."
        })

    # 3. Weather & Food Complexity Interactions
    if weather in ["Hot", "Humid"] and complexity == "Heavy":
        suggestions.append({
            "type": "info",
            "title": "Weather & Menu Pairing",
            "text": "Hot weather coupled with heavy menu items historically lowers individual appetite by 10-15%. Consider keeping rice/gravy portions moderate and keeping chilled curd/buttermilk accessible."
        })
    elif weather == "Rainy":
        suggestions.append({
            "type": "info",
            "title": "Rainy Weather Spike",
            "text": "During rainy days, off-campus eating declines and hostel mess attendance often exceeds expected headcount. Ensure hot staple items can be quickly extended if needed."
        })

    # 4. Historical Pattern Insight
    if historical_info.get("has_sufficient_history"):
        hist_item_waste = historical_info.get("menu_items_avg_waste", 15.0)
        if hist_item_waste > 18.0:
            suggestions.append({
                "type": "warning",
                "title": "Specific Item Waste Trend",
                "text": f"Historical records indicate dishes in this category average {hist_item_waste}% waste. Prepare standard batches and replenish in 20-minute intervals rather than bulk batching."
            })
    else:
        suggestions.append({
            "type": "info",
            "title": "Historical Notice",
            "text": historical_info.get("message", "Insufficient historical records prior to this date.")
        })

    return suggestions, recommended_kg

def predict_food_waste(input_data):
    """
    Predict High/Low waste probability using pre-meal inputs only.
    Automatically retrieves historical metrics strictly prior to date.
    """
    target_date = input_data.get("date", datetime.date.today().isoformat())
    meal_type = input_data.get("meal_type", "Lunch")
    food_category = input_data.get("food_category", "North Indian")
    menu_items = input_data.get("menu_items", [])
    if isinstance(menu_items, str):
        menu_items = [i.strip() for i in menu_items.split(",") if i.strip()]
    first_item = menu_items[0] if menu_items else "General"

    expected_students = int(input_data.get("expected_students", 400))
    total_population = int(input_data.get("total_hostel_population", 500))
    is_holiday = bool(input_data.get("is_holiday_or_event", False))
    weather = input_data.get("weather", "Sunny")
    temperature = float(input_data.get("temperature", 28.0))
    complexity = input_data.get("menu_complexity", "Moderate")

    # 1. Historical retrieval strictly dated BEFORE target_date (no leakage)
    historical_info = get_historical_context(
        target_date=target_date,
        meal_type=meal_type,
        food_category=food_category,
        menu_items=menu_items
    )

    try:
        dt = datetime.datetime.strptime(target_date, "%Y-%m-%d")
        day_of_week_num = dt.weekday()
    except Exception:
        day_of_week_num = 0

    attendance_ratio = expected_students / max(1, total_population)

    # 2. Assemble feature dataframe matching training pipeline
    feature_row = {
        "meal_type": meal_type,
        "food_category": food_category,
        "menu_complexity": complexity,
        "weather": weather,
        "expected_students": expected_students,
        "total_hostel_population": total_population,
        "attendance_ratio": attendance_ratio,
        "temperature": temperature,
        "is_holiday_or_event": int(is_holiday),
        "day_of_week_num": day_of_week_num,
        "historical_meal_avg_waste": historical_info.get("meal_avg_waste", 15.0),
        "historical_category_avg_waste": historical_info.get("category_avg_waste", 15.0),
        "historical_item_avg_waste": historical_info.get("menu_items_avg_waste", 15.0),
        "historical_weekday_avg_waste": historical_info.get("weekday_avg_waste", 15.0)
    }

    df_pred = pd.DataFrame([feature_row])

    # 3. Model inference
    pipeline = get_model_pipeline()
    if pipeline is None:
        raise RuntimeError("ML model pipeline could not be loaded or trained.")

    predicted_class = int(pipeline.predict(df_pred)[0])
    probabilities = pipeline.predict_proba(df_pred)[0]
    p_high = float(probabilities[1])
    p_low = float(probabilities[0])

    prediction_label = "HIGH WASTE" if predicted_class == 1 else "LOW WASTE"

    if p_high < 0.35:
        risk_level = "Low Risk"
        risk_badge_class = "success"
    elif p_high <= 0.65:
        risk_level = "Moderate Risk"
        risk_badge_class = "warning"
    else:
        risk_level = "High Risk"
        risk_badge_class = "danger"

    # 4. Generate contextual suggestions & recommended prep quantity
    suggestions, recommended_kg = generate_waste_reduction_suggestions(
        input_data, p_high, historical_info
    )

    return {
        "prediction": prediction_label,
        "risk_level": risk_level,
        "risk_badge_class": risk_badge_class,
        "probability_high_waste": round(p_high * 100, 1),
        "probability_low_waste": round(p_low * 100, 1),
        "recommended_food_prep_kg": recommended_kg,
        "suggestions": suggestions,
        "historical_analysis": historical_info,
        "input_features": feature_row
    }
