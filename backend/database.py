import datetime
from bson import ObjectId
from backend.config import get_database, sync_mock_storage, WASTE_THRESHOLD_PERCENT, logger

def normalize_meal_record(record):
    """Format and normalize ObjectId and dates for JSON responses."""
    if not record:
        return None
    record = dict(record)
    if "_id" in record:
        record["id"] = str(record["_id"])
        del record["_id"]
    return record

def calculate_waste_metrics(data):
    """
    Ensure food prepared, consumed, leftover, and waste percentage are properly calculated.
    """
    prepared = float(data.get("food_prepared_kg", 0.0))
    consumed = float(data.get("food_consumed_kg", 0.0))
    leftover = data.get("leftover_food_kg")

    if leftover is None or leftover == "":
        leftover = max(0.0, prepared - consumed)
    else:
        leftover = float(leftover)

    # Waste percentage
    if prepared > 0:
        waste_percentage = round((leftover / prepared) * 100.0, 2)
    else:
        waste_percentage = 0.0

    is_high_waste = bool(waste_percentage > WASTE_THRESHOLD_PERCENT)
    waste_level = "HIGH" if is_high_waste else "LOW"

    return {
        "food_prepared_kg": round(prepared, 2),
        "food_consumed_kg": round(consumed, 2),
        "leftover_food_kg": round(leftover, 2),
        "waste_percentage": waste_percentage,
        "is_high_waste": is_high_waste,
        "waste_level": waste_level
    }

def create_meal(data):
    """Insert a new actual meal record into MongoDB."""
    db = get_database()
    metrics = calculate_waste_metrics(data)
    data.update(metrics)

    # Process menu items as a list
    menu_items = data.get("menu_items", [])
    if isinstance(menu_items, str):
        menu_items = [item.strip() for item in menu_items.split(",") if item.strip()]
    data["menu_items"] = menu_items

    # Day of week from date
    date_str = data.get("date", datetime.date.today().isoformat())
    data["date"] = date_str
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        data["day_of_week"] = dt.strftime("%A")
        data["day_of_week_num"] = dt.weekday()
        data["month"] = dt.month
        data["year"] = dt.year
    except Exception:
        data["day_of_week"] = "Unknown"
        data["day_of_week_num"] = 0
        data["month"] = 1
        data["year"] = 2026

    # Convert numeric fields
    data["expected_students"] = int(data.get("expected_students", 0))
    data["actual_attendance"] = int(data.get("actual_attendance", data["expected_students"]))
    data["total_hostel_population"] = int(data.get("total_hostel_population", 500))
    data["temperature"] = float(data.get("temperature", 28.0))
    data["is_holiday_or_event"] = bool(data.get("is_holiday_or_event", False))
    data["created_at"] = datetime.datetime.now().isoformat()

    result = db.meals.insert_one(data)
    sync_mock_storage()
    data["id"] = str(result.inserted_id)
    if "_id" in data:
        del data["_id"]
    return data

def get_meals(page=1, limit=15, search="", meal_type="", waste_level="", start_date="", end_date="", sort_by="date", sort_order=-1):
    """Search, filter, and paginate meal records from MongoDB."""
    db = get_database()
    query = {}

    if search:
        query["$or"] = [
            {"menu_items": {"$regex": search, "$options": "i"}},
            {"food_category": {"$regex": search, "$options": "i"}},
            {"event_details": {"$regex": search, "$options": "i"}}
        ]

    if meal_type:
        query["meal_type"] = meal_type

    if waste_level:
        query["waste_level"] = waste_level.upper()

    if start_date or end_date:
        query["date"] = {}
        if start_date:
            query["date"]["$gte"] = start_date
        if end_date:
            query["date"]["$lte"] = end_date

    total_records = db.meals.count_documents(query)
    skip = (page - 1) * limit

    sort_field = sort_by if sort_by in ["date", "waste_percentage", "food_prepared_kg", "food_consumed_kg"] else "date"
    cursor = db.meals.find(query).sort([(sort_field, sort_order), ("meal_type", 1)]).skip(skip).limit(limit)

    records = [normalize_meal_record(doc) for doc in cursor]
    total_pages = max(1, (total_records + limit - 1) // limit)

    return {
        "records": records,
        "total_records": total_records,
        "total_pages": total_pages,
        "current_page": page,
        "limit": limit
    }

def get_meal_by_id(meal_id):
    """Retrieve a single meal record by ID."""
    db = get_database()
    doc = None
    try:
        doc = db.meals.find_one({"_id": ObjectId(meal_id)})
    except Exception:
        pass
    if not doc:
        doc = db.meals.find_one({"id": meal_id})
    return normalize_meal_record(doc)

def update_meal(meal_id, updates):
    """Update an existing meal record and recalculate waste metrics."""
    db = get_database()
    existing = get_meal_by_id(meal_id)
    if not existing:
        return None

    # Merge updates
    for k, v in updates.items():
        if k != "id" and k != "_id":
            existing[k] = v

    if "leftover_food_kg" not in updates and ("food_prepared_kg" in updates or "food_consumed_kg" in updates):
        existing["leftover_food_kg"] = None

    metrics = calculate_waste_metrics(existing)
    existing.update(metrics)

    if isinstance(existing.get("menu_items"), str):
        existing["menu_items"] = [i.strip() for i in existing["menu_items"].split(",") if i.strip()]

    date_str = existing.get("date", datetime.date.today().isoformat())
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        existing["day_of_week"] = dt.strftime("%A")
        existing["day_of_week_num"] = dt.weekday()
    except Exception:
        pass

    target_filter = {}
    try:
        target_filter = {"_id": ObjectId(meal_id)}
    except Exception:
        target_filter = {"id": meal_id}

    db.meals.update_one(target_filter, {"$set": existing})
    sync_mock_storage()
    return normalize_meal_record(existing)

def delete_meal(meal_id):
    """Delete a meal record from MongoDB."""
    db = get_database()
    target_filter = {}
    try:
        target_filter = {"_id": ObjectId(meal_id)}
    except Exception:
        target_filter = {"id": meal_id}

    result = db.meals.delete_one(target_filter)
    sync_mock_storage()
    return result.deleted_count > 0

def get_dashboard_stats():
    """Aggregate dashboard summary metrics directly from MongoDB."""
    db = get_database()
    total_meals = db.meals.count_documents({})

    if total_meals == 0:
        return {
            "total_meals": 0,
            "total_prepared_kg": 0.0,
            "total_consumed_kg": 0.0,
            "total_wasted_kg": 0.0,
            "avg_waste_percentage": 0.0,
            "high_waste_count": 0,
            "low_waste_count": 0,
            "high_waste_percentage": 0.0,
            "recent_trend": []
        }

    # Aggregate totals
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_prepared": {"$sum": "$food_prepared_kg"},
                "total_consumed": {"$sum": "$food_consumed_kg"},
                "total_wasted": {"$sum": "$leftover_food_kg"},
                "avg_waste": {"$avg": "$waste_percentage"},
                "high_waste_count": {
                    "$sum": {"$cond": [{"$eq": ["$waste_level", "HIGH"]}, 1, 0]}
                },
                "low_waste_count": {
                    "$sum": {"$cond": [{"$eq": ["$waste_level", "LOW"]}, 1, 0]}
                }
            }
        }
    ]

    agg_res = list(db.meals.aggregate(pipeline))
    if agg_res:
        stat = agg_res[0]
        total_prep = round(stat.get("total_prepared", 0.0), 2)
        total_wasted = round(stat.get("total_wasted", 0.0), 2)
        total_consumed = round(stat.get("total_consumed", 0.0), 2)
        avg_waste = round(stat.get("avg_waste", 0.0), 2)
        high_cnt = int(stat.get("high_waste_count", 0))
        low_cnt = int(stat.get("low_waste_count", 0))
    else:
        total_prep = total_wasted = total_consumed = avg_waste = 0.0
        high_cnt = low_cnt = 0

    high_pct = round((high_cnt / total_meals * 100.0), 1) if total_meals > 0 else 0.0

    # Recent 14 meals for dashboard mini chart
    recent_cursor = db.meals.find({}, {
        "date": 1, "meal_type": 1, "waste_percentage": 1, "waste_level": 1, "food_prepared_kg": 1, "leftover_food_kg": 1
    }).sort([("date", -1), ("meal_type", -1)]).limit(14)
    recent_trend = [normalize_meal_record(r) for r in recent_cursor]
    recent_trend.reverse()

    return {
        "total_meals": total_meals,
        "total_prepared_kg": total_prep,
        "total_consumed_kg": total_consumed,
        "total_wasted_kg": total_wasted,
        "avg_waste_percentage": avg_waste,
        "high_waste_count": high_cnt,
        "low_waste_count": low_cnt,
        "high_waste_percentage": high_pct,
        "recent_trend": recent_trend
    }

def get_analytics_data():
    """Compute detailed analytics for charts (daily, meal-wise, weekday, top wasted foods)."""
    db = get_database()
    total_meals = db.meals.count_documents({})
    if total_meals == 0:
        return {
            "daily_trend": [],
            "meal_type_waste": [],
            "weekday_waste": [],
            "category_waste": [],
            "top_wasted_items": [],
            "predicted_vs_actual": []
        }

    # 1. Daily trend (latest 30 days)
    daily_pipe = [
        {
            "$group": {
                "_id": "$date",
                "avg_waste_pct": {"$avg": "$waste_percentage"},
                "total_prepared": {"$sum": "$food_prepared_kg"},
                "total_wasted": {"$sum": "$leftover_food_kg"},
                "meals_count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": -1}},
        {"$limit": 30}
    ]
    daily_res = list(db.meals.aggregate(daily_pipe))
    daily_res.reverse()
    daily_trend = [
        {
            "date": d["_id"],
            "avg_waste_percentage": round(d.get("avg_waste_pct", 0), 2),
            "total_prepared_kg": round(d.get("total_prepared", 0), 2),
            "total_wasted_kg": round(d.get("total_wasted", 0), 2)
        }
        for d in daily_res
    ]

    # 2. Meal-wise average waste percentage
    meal_pipe = [
        {
            "$group": {
                "_id": "$meal_type",
                "avg_waste": {"$avg": "$waste_percentage"},
                "total_prepared": {"$sum": "$food_prepared_kg"},
                "total_wasted": {"$sum": "$leftover_food_kg"},
                "count": {"$sum": 1}
            }
        }
    ]
    meal_type_waste = [
        {
            "meal_type": m["_id"],
            "avg_waste_percentage": round(m.get("avg_waste", 0), 2),
            "total_prepared_kg": round(m.get("total_prepared", 0), 2),
            "total_wasted_kg": round(m.get("total_wasted", 0), 2),
            "count": m["count"]
        }
        for m in db.meals.aggregate(meal_pipe)
    ]

    # Order Breakfast, Lunch, Dinner
    order = {"Breakfast": 0, "Lunch": 1, "Dinner": 2}
    meal_type_waste.sort(key=lambda x: order.get(x["meal_type"], 99))

    # 3. Weekday waste trends
    weekdays_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_pipe = [
        {
            "$group": {
                "_id": "$day_of_week",
                "avg_waste": {"$avg": "$waste_percentage"},
                "count": {"$sum": 1}
            }
        }
    ]
    weekday_map = {w["_id"]: round(w["avg_waste"], 2) for w in db.meals.aggregate(weekday_pipe) if w["_id"]}
    weekday_waste = [
        {"day": day, "avg_waste_percentage": weekday_map.get(day, 0.0)}
        for day in weekdays_order
    ]

    # 4. Food Category waste
    cat_pipe = [
        {
            "$group": {
                "_id": "$food_category",
                "avg_waste": {"$avg": "$waste_percentage"},
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"avg_waste": -1}}
    ]
    category_waste = [
        {
            "category": c["_id"] or "General",
            "avg_waste_percentage": round(c.get("avg_waste", 0), 2),
            "count": c["count"]
        }
        for c in db.meals.aggregate(cat_pipe)
    ]

    # 5. Top 10 most wasted food items
    item_pipe = [
        {"$unwind": "$menu_items"},
        {
            "$group": {
                "_id": "$menu_items",
                "avg_waste": {"$avg": "$waste_percentage"},
                "total_wasted_kg": {"$sum": "$leftover_food_kg"},
                "occurrence": {"$sum": 1}
            }
        },
        {"$sort": {"avg_waste": -1}},
        {"$limit": 10}
    ]
    top_wasted_items = [
        {
            "item_name": item["_id"],
            "avg_waste_percentage": round(item["avg_waste"], 2),
            "total_wasted_kg": round(item["total_wasted_kg"], 1),
            "count": item["occurrence"]
        }
        for item in db.meals.aggregate(item_pipe)
    ]

    # 6. Predicted vs Actual comparison (where predictions were logged)
    pred_pipe = [
        {"$match": {"predicted_waste_level": {"$exists": True, "$ne": None}}},
        {"$sort": {"date": -1}},
        {"$limit": 20}
    ]
    pred_res = list(db.meals.aggregate(pred_pipe))
    pred_res.reverse()
    predicted_vs_actual = [
        {
            "date": p.get("date"),
            "meal_type": p.get("meal_type"),
            "actual_waste_pct": p.get("waste_percentage", 0),
            "predicted_waste_level": p.get("predicted_waste_level"),
            "predicted_high_prob": round(float(p.get("predicted_high_prob", 0.5)) * 100, 1),
            "actual_waste_level": p.get("waste_level")
        }
        for p in pred_res
    ]

    return {
        "daily_trend": daily_trend,
        "meal_type_waste": meal_type_waste,
        "weekday_waste": weekday_waste,
        "category_waste": category_waste,
        "top_wasted_items": top_wasted_items,
        "predicted_vs_actual": predicted_vs_actual
    }

def get_historical_context(target_date, meal_type, food_category, menu_items=None):
    """
    CRITICAL: Retrieve and analyze historical records strictly BEFORE target_date.
    Never uses target meal's own outcome (prevents data leakage).
    Informs user if data is insufficient (< 5 records).
    """
    db = get_database()
    prior_filter = {"date": {"$lt": target_date}}

    total_prior_records = db.meals.count_documents(prior_filter)
    if total_prior_records < 5:
        return {
            "has_sufficient_history": False,
            "total_prior_records": total_prior_records,
            "message": f"Insufficient historical records dated before {target_date} ({total_prior_records} records found; minimum 5 required). Model will rely on baseline pattern assumptions.",
            "meal_avg_waste": 15.0,
            "category_avg_waste": 15.0,
            "menu_items_avg_waste": 15.0,
            "weekday_avg_waste": 15.0,
            "prior_meals_trend": []
        }

    # 1. Meal type historical average
    meal_type_prior = list(db.meals.aggregate([
        {"$match": {"$and": [prior_filter, {"meal_type": meal_type}]}},
        {"$group": {"_id": None, "avg_waste": {"$avg": "$waste_percentage"}, "count": {"$sum": 1}}}
    ]))
    meal_avg_waste = round(meal_type_prior[0]["avg_waste"], 2) if meal_type_prior else 15.0
    meal_count = meal_type_prior[0]["count"] if meal_type_prior else 0

    # 2. Category historical average
    category_prior = list(db.meals.aggregate([
        {"$match": {"$and": [prior_filter, {"food_category": food_category}]}},
        {"$group": {"_id": None, "avg_waste": {"$avg": "$waste_percentage"}, "count": {"$sum": 1}}}
    ]))
    cat_avg_waste = round(category_prior[0]["avg_waste"], 2) if category_prior else 15.0
    cat_count = category_prior[0]["count"] if category_prior else 0

    # 3. Menu items historical average
    items_list = menu_items if isinstance(menu_items, list) else [i.strip() for i in str(menu_items).split(",") if i.strip()]
    menu_items_prior = list(db.meals.aggregate([
        {"$match": {"$and": [prior_filter, {"menu_items": {"$in": items_list}}]}},
        {"$group": {"_id": None, "avg_waste": {"$avg": "$waste_percentage"}, "count": {"$sum": 1}}}
    ]))
    menu_items_avg_waste = round(menu_items_prior[0]["avg_waste"], 2) if menu_items_prior else 15.0
    items_count = menu_items_prior[0]["count"] if menu_items_prior else 0

    # 4. Weekday historical average
    try:
        dt = datetime.datetime.strptime(target_date, "%Y-%m-%d")
        target_weekday = dt.strftime("%A")
    except Exception:
        target_weekday = "Unknown"

    weekday_prior = list(db.meals.aggregate([
        {"$match": {"$and": [prior_filter, {"day_of_week": target_weekday}]}},
        {"$group": {"_id": None, "avg_waste": {"$avg": "$waste_percentage"}, "count": {"$sum": 1}}}
    ]))
    weekday_avg_waste = round(weekday_prior[0]["avg_waste"], 2) if weekday_prior else 15.0

    # 5. Recent 5 prior meals trend
    recent_prior_cursor = db.meals.find(prior_filter, {
        "date": 1, "meal_type": 1, "waste_percentage": 1, "waste_level": 1, "menu_items": 1
    }).sort([("date", -1), ("meal_type", -1)]).limit(5)
    recent_trend = [normalize_meal_record(r) for r in recent_prior_cursor]

    return {
        "has_sufficient_history": True,
        "total_prior_records": total_prior_records,
        "message": f"Successfully retrieved historical metrics from {total_prior_records} prior meals.",
        "meal_avg_waste": meal_avg_waste,
        "meal_type_prior_samples": meal_count,
        "category_avg_waste": cat_avg_waste,
        "category_prior_samples": cat_count,
        "menu_items_avg_waste": menu_items_avg_waste,
        "menu_items_prior_samples": items_count,
        "target_weekday": target_weekday,
        "weekday_avg_waste": weekday_avg_waste,
        "recent_prior_meals": recent_trend
    }
