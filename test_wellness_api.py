#!/usr/bin/env python3
"""
Test script for the Wellness API endpoints
Run this after starting the server to test the new endpoints
"""

import requests
import json
from datetime import date

# Configuration
BASE_URL = "http://localhost:8000"
TEST_EMAIL = "kevinconjoin@gmail.com"
TEST_PASSWORD = "password"

def test_wellness_api():
    print("🧪 Testing Wellness API...")
    
    # Step 1: Login to get JWT token
    print("\n1️⃣ Testing login...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        headers={"Content-Type": "application/json"},
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code} - {login_response.text}")
        return
    
    token = login_response.json()["auth_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Login successful")
    
    # Step 2: Test creating wellness metrics
    print("\n2️⃣ Testing POST /wellness/daily-metrics...")
    wellness_data = {
        "energy_level": 7.5,
        "stress_level": 4.2
    }
    
    create_response = requests.post(
        f"{BASE_URL}/wellness/daily-metrics",
        headers={**headers, "Content-Type": "application/json"},
        json=wellness_data
    )
    
    if create_response.status_code == 200:
        print("✅ Wellness metrics created successfully")
        print(f"📊 Response: {json.dumps(create_response.json(), indent=2, default=str)}")
    else:
        print(f"❌ Failed to create wellness metrics: {create_response.status_code} - {create_response.text}")
        return
    
    # Step 3: Test getting latest wellness metrics
    print("\n3️⃣ Testing GET /wellness/daily-metrics/latest...")
    latest_response = requests.get(
        f"{BASE_URL}/wellness/daily-metrics/latest",
        headers=headers
    )
    
    if latest_response.status_code == 200:
        print("✅ Latest wellness metrics retrieved successfully")
        print(f"📊 Response: {json.dumps(latest_response.json(), indent=2, default=str)}")
    else:
        print(f"❌ Failed to get latest wellness metrics: {latest_response.status_code} - {latest_response.text}")
    
    # Step 4: Test getting wellness history
    print("\n4️⃣ Testing GET /wellness/daily-metrics...")
    history_response = requests.get(
        f"{BASE_URL}/wellness/daily-metrics?limit=10",
        headers=headers
    )
    
    if history_response.status_code == 200:
        print("✅ Wellness history retrieved successfully")
        history_data = history_response.json()
        print(f"📊 Found {history_data['total_count']} entries")
        print(f"📊 Response: {json.dumps(history_data, indent=2, default=str)}")
    else:
        print(f"❌ Failed to get wellness history: {history_response.status_code} - {history_response.text}")
    
    # Step 5: Test wellness statistics
    print("\n5️⃣ Testing GET /wellness/stats...")
    stats_response = requests.get(
        f"{BASE_URL}/wellness/stats?days=30",
        headers=headers
    )
    
    if stats_response.status_code == 200:
        print("✅ Wellness statistics retrieved successfully")
        print(f"📊 Response: {json.dumps(stats_response.json(), indent=2, default=str)}")
    else:
        print(f"❌ Failed to get wellness statistics: {stats_response.status_code} - {stats_response.text}")
    
    # Step 6: Test updating today's metrics (should update existing entry)
    print("\n6️⃣ Testing update of today's metrics...")
    updated_wellness_data = {
        "energy_level": 8.3,
        "stress_level": 3.7
    }
    
    update_response = requests.post(
        f"{BASE_URL}/wellness/daily-metrics",
        headers={**headers, "Content-Type": "application/json"},
        json=updated_wellness_data
    )
    
    if update_response.status_code == 200:
        print("✅ Wellness metrics updated successfully")
        print(f"📊 Response: {json.dumps(update_response.json(), indent=2, default=str)}")
    else:
        print(f"❌ Failed to update wellness metrics: {update_response.status_code} - {update_response.text}")
    
    print("\n🎉 Wellness API testing completed!")


if __name__ == "__main__":
    try:
        test_wellness_api()
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
