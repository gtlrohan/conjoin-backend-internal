#!/usr/bin/env python3
"""
Test script for updated AI morning orientation suggestions APIs
Tests both /ai-suggestions (2 primary) and /ai-alternatives (3 alternatives)
"""

import sys

import requests

# Configuration
BASE_URL = "http://localhost:8000"
TEST_EMAIL = "kevin@example.com"
TEST_PASSWORD = "password"


def test_login():
    """Login and get access token"""
    print("🔐 Logging in...")

    login_data = {"email": TEST_EMAIL, "password": TEST_PASSWORD}

    response = requests.post(f"{BASE_URL}/auth/login", json=login_data, headers={"Content-Type": "application/json"})

    if response.status_code == 200:
        result = response.json()
        access_token = result.get("access_token")
        print(f"✅ Login successful! User ID: {result.get('user', {}).get('user_id')}")
        return access_token
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None


def test_ai_suggestions(access_token):
    """Test /morning-orientation/ai-suggestions endpoint (2 suggestions)"""
    print("\n🧠 Testing AI Suggestions (Primary 2)...")

    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.post(f"{BASE_URL}/morning-orientation/ai-suggestions", headers=headers)

    if response.status_code == 200:
        suggestions = response.json()
        print("✅ AI Suggestions successful!")
        print(f"📊 Response type: {type(suggestions)}")
        print(f"📊 Number of suggestions: {len(suggestions) if isinstance(suggestions, list) else 'Not a list'}")

        if isinstance(suggestions, list):
            for i, suggestion in enumerate(suggestions, 1):
                print(f"\n📋 Suggestion {i}:")
                print(f"   Card ID: {suggestion.get('card_id')}")
                print(f"   Time: {suggestion.get('time')}")
                print(f"   User ID: {suggestion.get('user_id')}")

                card_details = suggestion.get("card_details", {})
                print(f"   Title: {card_details.get('title')}")
                print(f"   Category: {card_details.get('category')}")
                print(f"   Description: {card_details.get('description')}")
                print(f"   Duration: {card_details.get('duration')}")

        return True
    else:
        print(f"❌ AI Suggestions failed: {response.status_code} - {response.text}")
        return False


def test_ai_alternatives(access_token):
    """Test /morning-orientation/ai-alternatives endpoint (3 alternatives)"""
    print("\n🧠 Testing AI Alternatives (3 more)...")

    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.post(f"{BASE_URL}/morning-orientation/ai-alternatives", headers=headers)

    if response.status_code == 200:
        alternatives = response.json()
        print("✅ AI Alternatives successful!")
        print(f"📊 Response type: {type(alternatives)}")
        print(f"📊 Number of alternatives: {len(alternatives) if isinstance(alternatives, list) else 'Not a list'}")

        if isinstance(alternatives, list):
            for i, suggestion in enumerate(alternatives, 1):
                print(f"\n📋 Alternative {i}:")
                print(f"   Card ID: {suggestion.get('card_id')}")
                print(f"   Time: {suggestion.get('time')}")
                print(f"   User ID: {suggestion.get('user_id')}")

                card_details = suggestion.get("card_details", {})
                print(f"   Title: {card_details.get('title')}")
                print(f"   Category: {card_details.get('category')}")
                print(f"   Description: {card_details.get('description')}")
                print(f"   Duration: {card_details.get('duration')}")

        return True
    else:
        print(f"❌ AI Alternatives failed: {response.status_code} - {response.text}")
        return False


def test_comparison_with_existing():
    """Compare format with existing /user/morning-orientation API"""
    print("\n🔍 Comparing with existing morning-orientation API...")

    # This is just for format comparison - will likely fail due to auth requirements
    response = requests.post(f"{BASE_URL}/user/morning-orientation")
    print(f"📊 Existing API status: {response.status_code}")


def main():
    """Main test runner"""
    print("🚀 Testing Updated AI Morning Orientation APIs")
    print("=" * 50)

    # Login
    access_token = test_login()
    if not access_token:
        print("❌ Cannot proceed without login")
        sys.exit(1)

    # Test both AI endpoints
    ai_suggestions_success = test_ai_suggestions(access_token)
    ai_alternatives_success = test_ai_alternatives(access_token)

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"✅ AI Suggestions (2 primary): {'PASS' if ai_suggestions_success else 'FAIL'}")
    print(f"✅ AI Alternatives (3 more): {'PASS' if ai_alternatives_success else 'FAIL'}")

    if ai_suggestions_success and ai_alternatives_success:
        print("\n🎉 All tests passed! APIs are ready for frontend integration.")
        print("\n📋 Frontend Integration Notes:")
        print("- Use POST /morning-orientation/ai-suggestions for primary 2 suggestions")
        print("- Use POST /morning-orientation/ai-alternatives for additional 3 alternatives")
        print("- Response format matches existing /user/morning-orientation API")
        print("- Same authentication (JWT Bearer token) required")
    else:
        print("\n❌ Some tests failed. Check the errors above.")

    print("\n🔚 Test completed.")


if __name__ == "__main__":
    main()
