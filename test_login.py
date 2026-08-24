import requests

try:
    response = requests.post('http://127.0.0.1:8005/api/auth/login/', json={
        'username': 'admin',
        'password': 'admin1234'
    })
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
