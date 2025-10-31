"""
Test script for Authentication APIs
Run this after starting the server to test registration and login
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"


def test_register():
    """Test user registration"""
    print("\n" + "="*50)
    print("Testing User Registration")
    print("="*50)
    
    url = f"{BASE_URL}/auth/register"
    data = {
        "email": "testuser@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "password": "password123"
    }
    
    print(f"\nPOST {url}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(url, json=data)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            print("✅ Registration successful!")
            return True
        else:
            print("❌ Registration failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_login():
    """Test user login"""
    print("\n" + "="*50)
    print("Testing User Login")
    print("="*50)
    
    url = f"{BASE_URL}/auth/login"
    data = {
        "username": "testuser",
        "password": "password123"
    }
    
    print(f"\nPOST {url}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(url, json=data)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Login successful!")
            token = response.json().get("access_token")
            print(f"\n🔑 Access Token: {token[:50]}...")
            return token
        else:
            print("❌ Login failed!")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_protected_route(token):
    """Test a protected route with authentication token"""
    print("\n" + "="*50)
    print("Testing Protected Route")
    print("="*50)
    
    url = f"{BASE_URL}/auth/me"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    print(f"\nGET {url}")
    print(f"Headers: Authorization: Bearer {token[:30]}...")
    
    try:
        response = requests.get(url, headers=headers)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Protected route access successful!")
            return True
        else:
            print("⚠️  Protected route returned non-200 status")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("\n" + "="*50)
    print("🧪 HRMS Authentication API Testing")
    print("="*50)
    print("\nMake sure the server is running:")
    print("  uvicorn app.main:app --reload")
    print("\nServer should be at: http://localhost:8000")
    
    input("\nPress Enter to start testing...")
    
    # Test registration
    register_success = test_register()
    
    if register_success:
        # Test login
        token = test_login()
        
        if token:
            # Test protected route
            test_protected_route(token)
    
    print("\n" + "="*50)
    print("Testing Complete!")
    print("="*50)


if __name__ == "__main__":
    main()


