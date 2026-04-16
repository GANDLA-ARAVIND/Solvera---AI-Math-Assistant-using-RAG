import requests
import json

# First login to get token
login_data = {
    "email": "test@example.com",
    "password": "password123"
}

try:
    print("1. Logging in...")
    login_response = requests.post("http://localhost:8000/api/auth/login", json=login_data)
    print(f"Login Status: {login_response.status_code}")
    
    if login_response.status_code == 200:
        response_data = login_response.json()
        print(f"Response keys: {response_data.keys()}")
        token = response_data.get("token") or response_data.get("access_token")
        print(f"Token received: {token[:20] if token else 'NO TOKEN'}...")
        
        if not token:
            print(f"Full response: {response_data}")
            exit(1)
        
        # Now test solve endpoint
        print("\n2. Testing solve endpoint...")
        headers = {"Authorization": f"Bearer {token}"}
        solve_data = {"query": "Solve x^2 + 5x + 6 = 0"}
        
        solve_response = requests.post("http://localhost:8000/api/solve/", json=solve_data, headers=headers)
        print(f"Solve Status: {solve_response.status_code}")
        
        if solve_response.status_code == 200:
            result = solve_response.json()
            print(f"Success: {result.get('success')}")
            print(f"Has solution: {bool(result.get('solution'))}")
            if result.get('solution'):
                print(f"Solution preview: {result['solution'][:100]}...")
            else:
                print(f"Error field: {result.get('error')}")
                print(f"Message: {result.get('message')}")
                print(f"Full response: {json.dumps(result, indent=2)}")
        else:
            print(f"Error: {solve_response.text}")
    else:
        print(f"Login failed: {login_response.text}")
        
except Exception as e:
    print(f"Error: {e}")
