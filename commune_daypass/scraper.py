import requests
import json
import hmac
import hashlib
import uuid
import logging
from datetime import datetime, timedelta

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

def calculate_hmac(nonce, payload, secret_key="2355062e-40ae-454c-bcaa-b450e42fe54c"):
    """Helper function to calculate HMAC"""
    payload_str = json.dumps(payload, separators=(',', ':'))
    message = f"{nonce}:{payload_str}"
    return hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha512).hexdigest()

def get_availability(start_date, days_to_check):
    """Fetch availability data from the API"""
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
    
    try:
        response = requests.get(url, headers=headers, params=payload)
        response.raise_for_status()
        """
        Response format:
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
        return response.json()
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        return None

def catch_abnormal_data(data):
    """
    Conditions for abnormal data:
    - <= today + 10 days:
        - Non-normal price (88 / 148 / 59 / 99)
        - Non-normal availability (B)
    - > today + 10 days:
        - Non-normal price (52 / 88 / 39 / 66)
        - Non-normal availability (D)
    """

    abnormal_data = []
    ten_days_from_now = datetime.now() + timedelta(days=9)

    # Normal prices and availabilities
    increased_normal_prices = [8800, 14800, 5900, 9900]
    reduced_normal_prices = [5200, 8800, 3900, 6600]
    abnormal_availability_increased = "F"
    abnormal_availability_reduced = "C"

    # Helper function to reconstruct abnormal data in desired format
    def format_abnormal_entry(travel_date, key, class_type, details):
        return {
            "travelDate": travel_date,
            "prices": {
                key: {
                    class_type: {
                        "price": details["price"],
                        "availability": details["availability"],
                    }
                }
            },
        }

    for entry in data:
        travel_date = datetime.strptime(entry["travelDate"], "%Y-%m-%dT%H:%M:%S.%fZ")
        prices_dict = entry["prices"]

        # Determine normal prices and availability based on the date
        normal_prices = (
            increased_normal_prices if travel_date <= ten_days_from_now else reduced_normal_prices
        )
        abnormal_availability = (
            abnormal_availability_increased if travel_date <= ten_days_from_now else abnormal_availability_reduced
        )

        # Iterate through KEINE and HTA123 categories in order
        flattened_data = []
        for key in ["KEINE", "HTA123"]:
            for class_type in ["second", "first"]:
                if key in prices_dict and class_type in prices_dict[key]:
                    details = prices_dict[key][class_type]
                    flattened_data.append((key, class_type, details)) # tuples of three elements

        # Compare prices and availability, catch abnormalities
        for i, (key, class_type, details) in enumerate(flattened_data):
            expected_price = normal_prices[i]
            actual_price = details["price"]
            actual_availability = details["availability"]

            if actual_price != expected_price or actual_availability == abnormal_availability:
                abnormal_data.append(format_abnormal_entry(entry["travelDate"], key, class_type, details))

    
    # return format_data(abnormal_data)
    return abnormal_data

# Example usage (for testing purposes)
if __name__ == "__main__":
    start_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    days_to_check = 10
    result = get_availability(start_date, days_to_check)

    if result:
        # use logging
        logging.info("Availability Data:")
        logging.info(json.dumps(result, indent=2))
    else:
        logging.error("Failed to fetch availability data.")

    if result:
        abnormal_data = catch_abnormal_data(result)
        logging.info("Abnormal Data:")
        logging.info(json.dumps(abnormal_data, indent=2))
    else:
        logging.error("Failed to fetch abnormal data.")


"""
    Availability scaler

    C -> reduced price, limited availability
    F -> increased price, limited availability
    A -> reduced price, high availability
    D -> increased price, high availability

    =====================
    Price scaler (no discount 2nd class / no discount 1st class / half fare 2nd class / half fare 1st class)

    Normal:
    > today + 10 days  -> reduced price (52 / 88 / 39 / 66)
    <= today + 10 days -> increased price (88 / 148 / 59 / 99)

    Abnormal:
    non-normal price, limited availability

"""