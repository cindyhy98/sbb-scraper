import requests
import json
import hmac
import hashlib
import uuid
from datetime import datetime

# Function to calculate HMAC
def calculate_hmac(nonce, payload, secret_key="2355062e-40ae-454c-bcaa-b450e42fe54c"):
    payload_str = json.dumps(payload, separators=(',', ':'))
    message = f"{nonce}:{payload_str}"
    return hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha512).hexdigest()

# Scraper logic as a reusable function
def get_availability(start_date, days_to_check):
    url = 'https://www.cartejournaliere-commune.ch/api/v1/availabilities'
    nonce = str(uuid.uuid4())
    payload = {
        "startDate": start_date,
        "daysToCheck": str(days_to_check)
    }

    hmac_token = calculate_hmac(nonce, payload)
    
    headers = {
        'Authorization': f'HMAC {hmac_token}',
        'X-Correlation-Id': str(uuid.uuid4()),
        'X-Nonce': nonce,
        'User-Agent': 'Mozilla/5.0'
    }

    # headers = {
    #     'Host': 'www.cartejournaliere-commune.ch',
    #     'Authorization': f'HMAC {hmac_token}',
    #     'X-Correlation-Id': str(uuid.uuid4()),
    #     'X-Nonce': nonce,
    #     'Accept-Language': 'en-GB,en;q=0.9',
    #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.70 Safari/537.36',
    #     'Accept': 'application/json, text/plain, */*',
    #     'Referer': 'https://www.cartejournaliere-commune.ch/en',
    # }
    
    try:
        response = requests.get(url, headers=headers, params=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        return None

# Example usage (for testing purposes)
if __name__ == "__main__":
    start_date = datetime.now().strftime("%Y-%m-%d")
    days_to_check = 15
    result = get_availability(start_date, days_to_check)
    print(json.dumps(result, indent=2))
    

"""
    availability scaler

    A -> original price, high availability
    C -> original price, limited availability
    B(?) -> increased price, limited availability
    D -> increased price, high availability
"""

    
"""
    response structure
    {
        'travelDates': '...',
        'prices': {
            'KEINE': {
                'second': {
                    'price': 8800, 'availability': 'D'}, 
                'first': {
                    'price': 8800, 'availability': 'A'}
            }, 
            'HTA123': {
                'second': {
                    'price': 5900, 'availability': 'D'}, 
                'first': {
                    'price': 6600, 'availability': 'A'}
            }
        }
    }
"""