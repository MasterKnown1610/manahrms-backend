"""
Quick test script for login with specific credentials
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"

def test_login():
    """Test login with karthikeya credentials"""
    print("\n" + "="*50)
    print("Testing Login with karthikeya credentials")
    print("="*50)
    
    url = f"{BASE_URL}/auth/login"
    data = {
        "username": "karthikeya",
        "password": "Karthik"
    }
    
    print(f"\nPOST {url}")
    print(f"Username: {data['username']}")
    print(f"Password: {'*' * len(data['password'])}")
    
    try:
        response = requests.post(url, json=data, timeout=10)
        print(f"\nStatus Code: {response.status_code}")
        
        try:
            response_json = response.json()
            print(f"Response: {json.dumps(response_json, indent=2)}")
        except:
            print(f"Response Text: {response.text}")
        
        if response.status_code == 200:
            print("\n✅ Login successful!")
            token = response_json.get("access_token")
            if token:
                print(f"🔑 Access Token: {token[:50]}...")
            return True
        else:
            print(f"\n❌ Login failed with status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server.")
        print("   Make sure the server is running at http://localhost:8000")
        return False
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_login()
    sys.exit(0 if success else 1)

