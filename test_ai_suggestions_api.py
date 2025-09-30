#!/usr/bin/env python3
"""
Test script for the AI Morning Orientation Suggestions API
Run this after starting the server to test the new AI suggestions endpoint
"""

import requests
import json
from datetime import date

# Configuration
BASE_URL = "http://localhost:8000"
TEST_EMAIL = "kevinconjoin@gmail.com"
TEST_PASSWORD = "password"

def test_ai_suggestions_api():
    print("🤖 Testing AI Morning Orientation Suggestions API...")
    
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
    
    # Step 2: Check user state (make sure they have required data)
    print("\n2️⃣ Checking user state...")
    state_response = requests.get(
        f"{BASE_URL}/morning-orientation/user-state",
        headers=headers
    )
    
    if state_response.status_code == 200:
        state_data = state_response.json()
        print("✅ User state retrieved successfully")
        print(f"📊 Has cognitive fingerprint: {state_data['has_cognitive_fingerprint']}")
        print(f"📊 Has wellness data: {state_data['has_wellness_data']}")
        print(f"📊 Ready for AI suggestions: {state_data['ready_for_ai_suggestions']}")
        
        if not state_data['ready_for_ai_suggestions']:
            print("⚠️ User not ready for AI suggestions. Missing data:")
            if not state_data['has_cognitive_fingerprint']:
                print("   - Missing cognitive fingerprint")
            if not state_data['has_wellness_data']:
                print("   - Missing wellness data (run wellness API first)")
            return
    else:
        print(f"❌ Failed to get user state: {state_response.status_code} - {state_response.text}")
        return
    
    # Step 3: Test AI suggestions endpoint
    print("\n3️⃣ Testing AI Suggestions...")
    suggestions_response = requests.post(
        f"{BASE_URL}/morning-orientation/ai-suggestions",
        headers=headers
    )
    
    if suggestions_response.status_code == 200:
        print("✅ AI suggestions generated successfully")
        suggestions_data = suggestions_response.json()
        
        print(f"\n🤖 AI Suggestions for Kevin:")
        print(f"📅 Generated at: {suggestions_data['timestamp']}")
        print(f"📊 Total suggestions: {suggestions_data['total_suggestions']}")
        
        print(f"\n📈 User Context:")
        context = suggestions_data['context']
        print(f"   Energy Level: {context['daily_state']['energy_level']}")
        print(f"   Stress Level: {context['daily_state']['stress_level']}")
        print(f"   Work Anxiety: {context['cognitive_fingerprint']['work_anxiety']}")
        print(f"   Social Anxiety: {context['cognitive_fingerprint']['social_anxiety']}")
        print(f"   Family Anxiety: {context['cognitive_fingerprint']['family_anxiety']}")
        
        print(f"\n🎯 AI Generated Suggestions:")
        suggestions = suggestions_data['suggestions']
        for i in range(1, 6):
            suggestion_key = f"suggestion_{i}"
            if suggestion_key in suggestions:
                suggestion = suggestions[suggestion_key]
                print(f"\n   {i}. {suggestion['title']}")
                print(f"      {suggestion['description']}")
        
        # Pretty print the full response for debugging
        print(f"\n📋 Full Response:")
        print(json.dumps(suggestions_data, indent=2, default=str))
        
    else:
        print(f"❌ Failed to generate AI suggestions: {suggestions_response.status_code}")
        print(f"Error details: {suggestions_response.text}")
        return
    
    print("\n🎉 AI Suggestions API testing completed!")


def check_prerequisites():
    """Check if user has the required data for AI suggestions"""
    print("🔍 Checking prerequisites for AI suggestions...")
    
    # Login first
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        headers={"Content-Type": "application/json"},
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return False
    
    token = login_response.json()["auth_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Check wellness data
    wellness_response = requests.get(
        f"{BASE_URL}/wellness/daily-metrics/latest",
        headers=headers
    )
    
    if wellness_response.status_code != 200:
        print("❌ No wellness data found. Please create wellness data first:")
        print("   Run: python test_wellness_api.py")
        return False
    
    print("✅ All prerequisites met!")
    return True


if __name__ == "__main__":
    try:
        # Check prerequisites first
        if not check_prerequisites():
            print("\n💡 To fix this, first run:")
            print("   python test_wellness_api.py")
            print("   Then run this script again.")
            exit(1)
        
        # Run the actual test
        test_ai_suggestions_api()
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
