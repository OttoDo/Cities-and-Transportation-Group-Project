import pandas as pd
import requests
import json

# Google Air Quality API Key
API_KEY = "API" #Please change to your own API. 

# Load the CSV file correctly
file_path = "GPS_Paris.csv"
df = pd.read_csv(file_path)

# Function to fetch air quality data from Google API
def fetch_air_quality_data(lat, lon, api_key):
    url = f"https://airquality.googleapis.com/v1/currentConditions:lookup?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    # Correct request body with extraComputations
    data = {
        "universalAqi": True,
        "location": {"latitude": lat, "longitude": lon},
        "extraComputations": [
            "HEALTH_RECOMMENDATIONS",
            "DOMINANT_POLLUTANT_CONCENTRATION",
            "POLLUTANT_CONCENTRATION",
            "LOCAL_AQI",
            "POLLUTANT_ADDITIONAL_INFO"
        ],
        "languageCode": "en"
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching data for {lat}, {lon}: {response.status_code} - {response.text}")
        return None

# Function to parse the API response and extract pollution data
def parse_air_quality_data(data):
    if data and 'pollutants' in data:
        pollutants = data['pollutants']
        
        # Extract concentrations for all six pollutants
        return {
            'CO': next((p['concentration']['value'] for p in pollutants if p['code'] == 'co'), 'N/A'),
            'NO2': next((p['concentration']['value'] for p in pollutants if p['code'] == 'no2'), 'N/A'),
            'O3': next((p['concentration']['value'] for p in pollutants if p['code'] == 'o3'), 'N/A'),
            'PM10': next((p['concentration']['value'] for p in pollutants if p['code'] == 'pm10'), 'N/A'),
            'PM2.5': next((p['concentration']['value'] for p in pollutants if p['code'] == 'pm25'), 'N/A'),
            'SO2': next((p['concentration']['value'] for p in pollutants if p['code'] == 'so2'), 'N/A')
        }
    return {'CO': 'N/A', 'NO2': 'N/A', 'O3': 'N/A', 'PM10': 'N/A', 'PM2.5': 'N/A', 'SO2': 'N/A'}

# Process the GPS locations and fetch air quality data
air_quality_data = []

for _, row in df.iterrows():
    try:
        lat, lon = map(float, row['GPS'].split(", "))
        pollution_data = fetch_air_quality_data(lat, lon, API_KEY)
        parsed_data = parse_air_quality_data(pollution_data)

        air_quality_data.append({
            "Arrondissement": row['Arrondissement'],
            "Latitude": lat,
            "Longitude": lon,
            **parsed_data
        })

    except ValueError:
        print(f"Skipping invalid data: {row['GPS']}")

# Save results to a new CSV file
output_csv = "AirQuality_Paris.csv"
air_quality_df = pd.DataFrame(air_quality_data)
air_quality_df.to_csv(output_csv, index=False)

print(f"Air quality data saved to {output_csv}")
