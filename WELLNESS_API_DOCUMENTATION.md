# 🌟 **Wellness API Documentation**

## 📋 **Overview**

The Wellness API provides endpoints for tracking daily energy and stress levels. This API allows users to record their daily wellness metrics and retrieve historical data with statistics.

---

## 🎯 **Main Endpoint**

### **POST /wellness/daily-metrics**

**Purpose:** Create or update daily wellness metrics (energy level and stress level)

**Request Body:**
```json
{
  "energy_level": 7.5,
  "stress_level": 4.2
}
```

**Field Validation:**
- `energy_level`: Float between 1.0-10.0 (required)
  - 1.0 = Very low energy
  - 10.0 = Very high energy
  - Supports decimals: 5.5, 7.2, 8.7, etc.
- `stress_level`: Float between 1.0-10.0 (required)
  - 1.0 = Very low stress
  - 10.0 = Very high stress
  - Supports decimals: 3.4, 6.8, 9.1, etc.

**Response (200 OK):**
```json
{
  "id": 1,
  "user_id": 123,
  "energy_level": 7.5,
  "stress_level": 4.2,
  "date": "2025-01-18",
  "created_at": "2025-01-18T10:30:00.123456"
}
```

**Behavior:**
- If an entry already exists for today, it will be **updated**
- If no entry exists for today, a **new entry** will be created
- One entry per user per day (enforced by unique constraint)

**UI Integration Notes:**
- Perfect for **slider controls** in mobile apps
- Supports decimal precision (e.g., 5.7, 8.3, 9.1)
- Users can fine-tune their wellness levels with smooth sliding
- Values can be incremented by 0.1 or 0.5 steps

---

## 📊 **Additional Endpoints**

### **GET /wellness/daily-metrics**
Retrieve wellness metrics history

**Query Parameters:**
- `limit` (optional): Number of entries to retrieve (1-100, default: 30)
- `offset` (optional): Number of entries to skip (default: 0)

**Response:**
```json
{
  "metrics": [
    {
      "id": 1,
      "user_id": 123,
      "energy_level": 7,
      "stress_level": 4,
      "date": "2025-01-18",
      "created_at": "2025-01-18T10:30:00.123456"
    }
  ],
  "total_count": 1
}
```

### **GET /wellness/daily-metrics/latest**
Get the most recent wellness metrics entry

**Response:**
```json
{
  "id": 1,
  "user_id": 123,
  "energy_level": 7,
  "stress_level": 4,
  "date": "2025-01-18",
  "created_at": "2025-01-18T10:30:00.123456"
}
```

### **GET /wellness/daily-metrics/date-range**
Get wellness metrics for a specific date range

**Query Parameters:**
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (required): End date in YYYY-MM-DD format

**Example:** `/wellness/daily-metrics/date-range?start_date=2025-01-01&end_date=2025-01-18`

### **GET /wellness/stats**
Get wellness statistics and averages

**Query Parameters:**
- `days` (optional): Number of days to include (1-365, default: 30)

**Response:**
```json
{
  "avg_energy_level": 7.5,
  "avg_stress_level": 4.2,
  "total_entries": 15,
  "date_range": "2024-12-19 to 2025-01-18",
  "latest_entry": {
    "id": 1,
    "user_id": 123,
    "energy_level": 7,
    "stress_level": 4,
    "date": "2025-01-18",
    "created_at": "2025-01-18T10:30:00.123456"
  }
}
```

### **DELETE /wellness/daily-metrics/{metrics_id}**
Delete a specific wellness metrics entry

**Response:**
```json
{
  "message": "Wellness metrics entry deleted successfully"
}
```

---

## 🔐 **Authentication**

All endpoints require JWT authentication:

```bash
Authorization: Bearer <your_jwt_token>
```

Get JWT token from:
```bash
POST /auth/login
{
  "email": "your_email@example.com",
  "password": "your_password"
}
```

---

## 🗄️ **Database Schema**

```sql
CREATE TABLE daily_wellness_metrics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES "User"(user_id),
    energy_level REAL CHECK (energy_level >= 1.0 AND energy_level <= 10.0),
    stress_level REAL CHECK (stress_level >= 1.0 AND stress_level <= 10.0),
    created_at TIMESTAMP DEFAULT NOW(),
    date DATE DEFAULT CURRENT_DATE,
    UNIQUE(user_id, date) -- One entry per user per day
);
```

**Indexes:**
- Primary key on `id`
- Index on `user_id` for fast user queries
- Index on `date` for date range queries
- Unique index on `(user_id, date)` to prevent duplicates

---

## 🧪 **Testing**

### **Quick Test with cURL:**

```bash
# 1. Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "kevinconjoin@gmail.com", "password": "password"}'

# 2. Create/Update Wellness Metrics (replace TOKEN with actual token)
curl -X POST http://localhost:8000/wellness/daily-metrics \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"energy_level": 7.5, "stress_level": 4.2}'

# 3. Get Latest Metrics
curl -X GET http://localhost:8000/wellness/daily-metrics/latest \
  -H "Authorization: Bearer TOKEN"

# 4. Get Statistics
curl -X GET http://localhost:8000/wellness/stats \
  -H "Authorization: Bearer TOKEN"
```

### **Automated Test Script:**
Run the included test script:
```bash
python test_wellness_api.py
```

---

## 🚨 **Error Handling**

### **Validation Errors (400):**
```json
{
  "detail": [
    {
      "loc": ["body", "energy_level"],
      "msg": "ensure this value is greater than or equal to 1",
      "type": "value_error.number.not_ge",
      "ctx": {"limit_value": 1}
    }
  ]
}
```

### **Authentication Errors (403):**
```json
{
  "detail": "Access denied."
}
```

### **Server Errors (500):**
```json
{
  "detail": "Failed to create wellness metrics: <error_message>"
}
```

---

## 🔄 **Migration**

To apply the database changes:

```bash
# Generate migration (if not already done)
alembic revision --autogenerate -m "Add daily wellness metrics table"

# Apply migration
alembic upgrade head
```

---

## 🎯 **Use Cases**

### **Daily Check-in Flow:**
1. User opens app in morning/evening
2. App calls `GET /wellness/daily-metrics/latest` to check if today's entry exists
3. If no entry exists, show wellness input form
4. User submits `POST /wellness/daily-metrics` with energy/stress levels
5. App calls `GET /wellness/stats` to show progress

### **Historical Analysis:**
1. App calls `GET /wellness/daily-metrics?limit=30` for recent entries
2. Display charts/graphs of energy and stress trends
3. Use `GET /wellness/stats?days=7` for weekly averages

### **Date Range Reports:**
1. User selects date range in app
2. App calls `GET /wellness/daily-metrics/date-range?start_date=X&end_date=Y`
3. Display detailed report for selected period

---

## 📈 **Integration with Existing Features**

The wellness metrics can be integrated with:

1. **Cognitive Fingerprint:** Correlate stress levels with anxiety domains
2. **Card Completion:** Track how activities affect energy/stress
3. **Voice Therapy:** Use wellness data to personalize therapy sessions
4. **Digital Mentor:** Suggest activities based on current energy/stress levels

---

## 🛠️ **Technical Implementation**

### **Code Structure:**
- **Schema:** `app/postgres/schema/wellness.py` - SQLAlchemy model
- **Models:** `app/postgres/models/wellness.py` - Pydantic request/response models
- **CRUD:** `app/postgres/crud/wellness.py` - Database operations
- **Routes:** `app/routes/wellness.py` - API endpoints
- **Migration:** `alembic/versions/20250118_000000_add_daily_wellness_metrics.py`

### **Key Features:**
- ✅ **Upsert Logic:** Updates existing entry or creates new one
- ✅ **Data Validation:** Ensures 1-10 range for both metrics
- ✅ **User Isolation:** Each user only sees their own data
- ✅ **Performance:** Proper indexing for fast queries
- ✅ **Statistics:** Built-in averaging and analytics
- ✅ **Error Handling:** Comprehensive error responses

---

## 🎉 **Status: Ready for Production!**

The Wellness API is fully implemented and tested, following all established patterns in the ConjoinAI codebase. It's ready for frontend integration and production deployment! 🚀
