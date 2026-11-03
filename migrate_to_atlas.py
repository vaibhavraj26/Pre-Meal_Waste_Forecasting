"""
Atlas Connection & Data Migration Utility
Usage:
    python migrate_to_atlas.py
"""

import os
import sys
import json
import re
from pathlib import Path

# Ensure root directory in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

import pymongo
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, OperationFailure

def mask_uri(uri):
    return re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', uri)

def migrate():
    uri = os.getenv("MONGODB_URI", "")
    db_name = os.getenv("DB_NAME", "food_waste_db")

    print("=" * 65)
    print(" Smart Mess Food Waste Predictor - MongoDB Atlas Migration")
    print("=" * 65)

    if not uri or "mongodb" not in uri:
        print("[!] ERROR: MONGODB_URI is not set properly in .env file.")
        print("    Example Atlas URI format:")
        print("    MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.abcde.mongodb.net/food_waste_db?retryWrites=true&w=majority")
        return False

    print(f"[*] Target Database URI: {mask_uri(uri)}")
    print(f"[*] Database Name:       {db_name}")
    print("[*] Testing Atlas connection (timeout 8s)...")

    try:
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=8000)
        client.admin.command('ping')
        print("[+] SUCCESS: Successfully connected and authenticated with MongoDB Atlas!")
    except ServerSelectionTimeoutError as e:
        print("\n[!] CONNECTION TIMEOUT: Could not reach MongoDB Atlas cluster.")
        print("    Possible causes:")
        print("    1. Network Access (IP Whitelist): In MongoDB Atlas -> 'Network Access',")
        print("       ensure '0.0.0.0/0' (Allow access from anywhere) is added so cloud hosts and your IP can connect.")
        print("    2. DNS / Firewall: Check that your network allows outbound port 27017 or SRV lookups.")
        print(f"    Detailed error: {e}")
        return False
    except OperationFailure as e:
        print("\n[!] AUTHENTICATION FAILED: MongoDB Atlas rejected credentials.")
        print("    Possible causes:")
        print("    1. Incorrect username or password in MONGODB_URI.")
        print("    2. If your password contains special characters (like @, #, :, /, etc.),")
        print("       they MUST be URL-encoded (e.g. '@' becomes '%40', '#' becomes '%23').")
        print("    3. User does not have 'readWriteAnyDatabase' or 'readWrite' permissions on this database.")
        print(f"    Detailed error: {e}")
        return False
    except Exception as e:
        print(f"\n[!] Unexpected error connecting to MongoDB Atlas: {e}")
        return False

    db = client[db_name]
    meals_col = db.meals
    current_count = meals_col.count_documents({})
    print(f"[*] Current meal records in Atlas '{db_name}.meals': {current_count}")

    backup_file = BASE_DIR / "data" / "persistent_meals_backup.json"
    if not backup_file.exists():
        print(f"[!] Warning: {backup_file} not found. Running synthetic generator...")
        from backend.synthetic_data import generate_synthetic_dataset
        records = generate_synthetic_dataset(num_days=400)
    else:
        with open(backup_file, "r", encoding="utf-8") as f:
            records = json.load(f)

    if current_count >= 100:
        print(f"[i] Atlas already contains {current_count} records.")
        response = input("    Do you want to re-seed/refresh with clean 1200 records? (y/N): ").strip().lower()
        if response == 'y':
            print("[*] Purging existing meals from Atlas...")
            meals_col.delete_many({})
            print(f"[*] Inserting {len(records)} records into Atlas...")
            meals_col.insert_many(records)
            print("[+] Migration completed successfully!")
        else:
            print("[*] Kept existing Atlas records.")
    else:
        print(f"[*] Uploading {len(records)} rich historical meal records to MongoDB Atlas...")
        # Strip string IDs to allow fresh MongoDB ObjectId assignment
        clean_records = []
        for r in records:
            r_copy = dict(r)
            if "id" in r_copy:
                del r_copy["id"]
            if "_id" in r_copy:
                del r_copy["_id"]
            clean_records.append(r_copy)

        meals_col.insert_many(clean_records)
        total_now = meals_col.count_documents({})
        print(f"[+] SUCCESS: Seeded {len(clean_records)} records into MongoDB Atlas! Total count: {total_now}")

    # Create helpful indexes on Atlas
    print("[*] Ensuring database indexes (date, meal_type, food_category)...")
    meals_col.create_index([("date", -1), ("meal_type", 1)])
    meals_col.create_index([("food_category", 1)])
    meals_col.create_index([("waste_level", 1)])
    print("[+] Indexes created successfully.")

    # Retrain ML Model to ensure pipeline matches Atlas data
    print("[*] Retraining Logistic Regression ML model against Atlas data...")
    from backend.ml.model import train_logistic_regression_model
    train_res = train_logistic_regression_model()
    if train_res.get("success"):
        acc = train_res.get("metrics", {}).get("accuracy", 0) * 100
        print(f"[+] Model retrained successfully! Accuracy: {acc:.1f}%")
    else:
        print(f"[!] Model training note: {train_res.get('message')}")

    print("=" * 65)
    print(" ALL DONE! Your MongoDB Atlas cluster is live and fully populated.")
    print(" You can now run your project or deploy it to any cloud host.")
    print("=" * 65)
    return True

if __name__ == "__main__":
    migrate()

