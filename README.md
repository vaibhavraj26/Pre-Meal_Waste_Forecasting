# Smart Mess Food Waste Prediction System

An end-to-end, production-ready machine learning and database application designed for college hostel mess organizers to predict whether an upcoming meal will generate **HIGH WASTE (>15%)** or **LOW WASTE (&le;15%)** before preparation begins.

---

## Architecture Overview

```
                      +---------------------------------------+
                      |         Web Browser Client            |
                      |   Bootstrap 5 + Chart.js + Modern UI  |
                      +-------------------+-------------------+
                                          | HTTP :3000
                                          v
                      +---------------------------------------+
                      |         Node.js Web Server            |
                      |           (Express App)               |
                      |  - Serves UI Pages (Dashboard, etc.)  |
                      |  - Reverse-proxies /api to Python     |
                      +-------------------+-------------------+
                                          | HTTP :5000
                                          v
                      +---------------------------------------+
                      |       Python Backend & ML API         |
                      |          (Flask + PyMongo)            |
                      |  - Logistic Regression Pipeline       |
                      |  - Feature Engineering (Zero Leakage) |
                      |  - Prior Record Query (date < target) |
                      |  - Aggregation Pipelines & CRUD       |
                      +-------------------+-------------------+
                                          | PyMongo
                                          v
                      +---------------------------------------+
                      |            MongoDB Database           |
                      |     (Atlas URI or Local MongoDB)      |
                      |  - meals collection                   |
                      |  - training_history collection        |
                      +---------------------------------------+
```

---

## Key Features

1. **Hostel Mess Dashboard:**
   - Real-time KPI summary: Total meals recorded, total food prepared (kg), total food wasted (kg), and average waste percentage.
   - Interactive 14-meal waste trend chart (Chart.js) with 15% high-waste ceiling.
   - Quick table of recent actual meals with one-click navigation.

2. **Pre-Meal Food Waste Prediction:**
   - **Zero Manual Historical Input:** The organizer enters only scheduling parameters known in advance:
     - Date & Meal Type (Breakfast, Lunch, Dinner)
     - Menu items & Food Category
     - Expected students & Total hostel population
     - Weather & Temperature
     - Menu complexity (Simple, Moderate, Heavy)
     - Holiday / Campus event flag
   - **Automatic Historical Intelligence:** Queries MongoDB strictly for records dated *before* the target meal date to compute past category waste rates, dish waste averages, and weekday attendance dips without data leakage.
   - **ML Probability & Risk Classification:** Displays exact high-waste risk percentage, risk tier (Low, Moderate, High), recommended safe food preparation quantity (kg), and contextual kitchen mitigation suggestions.

3. **Machine Learning Pipeline (Logistic Regression):**
   - Implemented with Scikit-learn using a `ColumnTransformer` (OneHotEncoder for categorical features, StandardScaler for numerical features).
   - High precision (94.5%) to minimize false high-waste alarms.
   - Interpretable feature weights showing which variables drive leftovers up or down.

4. **Add Actual Meal Records:**
   - After meal completion, organizers record actual attendance, food prepared (kg), food consumed (kg), and leftover food (kg).
   - Real-time calculation preview updates leftover kg, waste %, and High/Low waste classification as numbers are typed.
   - Directly saves into MongoDB `meals` collection.

5. **Meal History & Full CRUD Management:**
   - Paginated, searchable, and filterable table (filter by meal type, waste level, date range).
   - Edit modal to update actual attendance or consumption metrics with automatic metric recalculation.
   - Delete modal with confirmation to safely remove records from MongoDB.

6. **Analytics Hub:**
   - Interactive Chart.js visualizations:
     - Daily average waste trend & total kilograms wasted (Line + Bar).
     - Meal-wise waste comparison (Breakfast vs. Lunch vs. Dinner).
     - Weekday vs. weekend waste patterns (visualizing Saturday/Sunday dips).
     - Top 10 most wasted dishes across the hostel.
     - Food category waste distribution (Doughnut chart).
     - Predicted vs. actual waste evaluation table.

7. **Model Performance & Retraining:**
   - Displays Accuracy, Precision, Recall, F1-Score, and ROC-AUC.
   - 2x2 Interactive Confusion Matrix (True Negatives, False Positives, False Negatives, True Positives).
   - Feature coefficient bar chart.
   - On-demand "Retrain Model" button with minimum sample threshold check (50 records).
   - MongoDB-persisted training history log.

8. **Synthetic Dataset Included (400 Days, 20 Foods):**
   - Automatically pre-seeds 1,200 meal records across 400 continuous days covering 20 distinct Indian hostel dishes (Poha, Rajma Chawal, Paneer Butter Masala, Veg Biryani, etc.).
   - Pre-trains the model out of the box so predictions and analytics work immediately upon first launch.

---

## Technology Stack

- **Backend & ML:** Python 3.13, Flask, Scikit-learn, Pandas, NumPy, PyMongo, Python-Dotenv, Joblib.
- **Web Server:** Node.js, Express, `http-proxy-middleware`, Dotenv.
- **Database:** MongoDB Atlas or local MongoDB (`mongodb://localhost:27017/food_waste_db`) with automatic persistent mock fallback for offline environments.
- **Frontend:** HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons, Chart.js 4.4.

---

## Directory Structure

```
FoodWastePredictor/
├── backend/
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── model.py            # Logistic Regression training & metrics
│   │   └── predict.py          # Pre-meal inference & leak-free historical queries
│   ├── routes/
│   │   ├── __init__.py
│   │   └── api_routes.py       # Flask REST API endpoints
│   ├── app.py                  # Flask server entrypoint (port 5000)
│   ├── config.py               # Database connection manager & environment loader
│   ├── database.py             # PyMongo CRUD operations & aggregation pipelines
│   └── synthetic_data.py       # 400-day 20-food dataset generator & seeder
├── frontend/
│   └── public/
│       ├── css/
│       │   └── style.css       # Custom modern responsive styling
│       ├── js/
│       │   ├── api.js          # Shared API client & notifications
│       │   ├── dashboard.js    # Dashboard KPIs & mini trend chart
│       │   ├── predict.js      # Prediction controller & suggestions
│       │   ├── add-meal.js     # Add meal form & live waste calculator
│       │   ├── history.js      # Search, filter, pagination, edit & delete
│       │   ├── analytics.js    # Chart.js analytics visualizations
│       │   └── model.js        # Model metrics, confusion matrix & retraining
│       ├── index.html          # Dashboard page
│       ├── predict.html        # Pre-meal food waste prediction page
│       ├── add-meal.html       # Add actual meal record page
│       ├── history.html        # Meal history & CRUD page
│       ├── analytics.html      # Analytics intelligence hub
│       └── model.html          # Model performance & retrain page
├── server/
│   └── server.js               # Node.js Express server & proxy (port 3000)
├── data/                       # Local model artifacts and persistent store
├── test_app.py                 # Automated unit test suite
├── run_all.py                  # Simultaneous dual-server launcher
├── start.bat                   # Windows one-click start script
├── package.json                # Node dependencies & npm scripts
├── .env                        # Active environment configuration
├── .env.example                # Configuration template
└── README.md                   # Complete documentation
```

---

## Quick Setup & Running Locally

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Node.js 18+ (tested on Node v24)
- (Optional) Local MongoDB Community Server running on `localhost:27017` OR a MongoDB Atlas cluster URI.

### 2. Install Dependencies
```bash
# Install Node.js dependencies
npm install

# Install Python dependencies
python -m pip install flask flask-cors pandas numpy scikit-learn python-dotenv mongomock requests
```

### 3. Configure Database
Inspect or edit `.env`:
```env
# For local MongoDB:
MONGODB_URI=mongodb://localhost:27017/food_waste_db

# Or for MongoDB Atlas:
# MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/food_waste_db?retryWrites=true&w=majority

DB_NAME=food_waste_db
PYTHON_PORT=5000
NODE_PORT=3000
WASTE_THRESHOLD_PERCENT=15.0
MIN_RETRAIN_RECORDS=50
```
> **Note:** If MongoDB is not yet running locally and no Atlas URI is provided, the application will automatically run in persistent PyMongo-compatible fallback mode, saving records to `data/persistent_meals_backup.json` without failing.

### 4. Start the Application
You can start both servers simultaneously:

**On Windows:**
Double-click `start.bat` or run:
```bash
python run_all.py
```

**Or run services independently:**
```bash
# Terminal 1: Python Flask Backend
python backend/app.py

# Terminal 2: Node.js Web Server
node server/server.js
```

### 5. Access the Web Application
Open your browser and navigate to:
**`http://localhost:3000`**

---

## Running Automated Tests

Run the complete test suite verifying synthetic data generation, PyMongo CRUD, zero data leakage checks, ML inference, and REST APIs:

```bash
python test_app.py
```

Output:
```
Ran 5 tests in ~4s
OK
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Check database connectivity & record counts |
| `GET` | `/api/dashboard/stats` | Aggregated meals, prepared kg, wasted kg, and waste rate |
| `POST` | `/api/predict` | Logistic Regression prediction on pre-meal parameters |
| `GET` | `/api/meals` | Paginated, searchable, filterable meal history |
| `POST` | `/api/meals` | Add a new meal record with actual attendance & food kg |
| `GET` | `/api/meals/<id>` | Retrieve a single meal by ID |
| `PUT` | `/api/meals/<id>` | Update meal record & recalculate waste metrics |
| `DELETE` | `/api/meals/<id>` | Delete meal record from MongoDB |
| `GET` | `/api/analytics` | Analytics datasets for daily, meal-type, and weekday charts |
| `GET` | `/api/ml/performance` | Accuracy, precision, recall, confusion matrix & history |
| `POST` | `/api/ml/retrain` | Retrain Logistic Regression model on current MongoDB records |
| `GET` | `/api/foods` | Catalogue of 20 distinct dishes & culinary categories |
| `POST` | `/api/seed` | Trigger / re-seed 400 continuous days of synthetic data |

---

## College Project Highlights

- **Zero Data Leakage:** When predicting waste for a meal scheduled on `YYYY-MM-DD`, only MongoDB records with `date < YYYY-MM-DD` are utilized to extract historical dish performance and attendance patterns.
- **Dual-Service Web Architecture:** Demonstrates modern microservice design with Node.js serving as the client-facing gateway and Python serving as the specialized ML compute engine.
- **Full PyMongo Integration:** Leverages MongoDB document indexing, `$match`, `$group`, and `$sort` aggregation pipelines.
- **Interpretable Machine Learning:** Features mapped back to regression coefficients so kitchen organizers understand *why* waste is predicted to occur.
