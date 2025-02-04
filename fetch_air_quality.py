import pandas as pd
import requests
import json
import random
import math
#import time
import folium
from IPython.display import display
###############100 GPS locations################

# Load the Excel file without assuming the first row as column names
file_path = "GPS_Paris.xlsx"
df = pd.read_excel(file_path, header=None)  # header=None ensures the first row remains as data

# Rename columns manually
df.columns = ["Arrondissement", "Coordinates"]

# Save as CSV without altering data
csv_file_path = "GPS_Paris.csv"
df.to_csv(csv_file_path, index=False, header=False)  # header=False keeps the original format

# Create a map centered on Paris
m = folium.Map(location=[48.8566, 2.3522], zoom_start=12)

# Count the number of valid coordinates (dots drawn)
#dot_count = 0

# Add dot markers to the map
for _, row in df.iterrows():
    try:
        lat, lon = map(float, str(row.iloc[1]).split(", "))  # Use .iloc[] to access by position
        folium.CircleMarker(
            location=[lat, lon],
            radius=3,  # Size of the dot
            color="red",  # Dot color
            fill=True,
            fill_color="red",
            fill_opacity=0.7,
            popup=f"Arrondissement {row.iloc[0]}"  # Use .iloc[] for safe indexing
        ).add_to(m)
        #dot_count += 1  # Count the valid dots
    except ValueError:
        continue  # Skip invalid data

# Display the map in the Jupyter Notebook
display(m)

# Print the number of dots drawn
print(f"Number of dots drawn: {dot_count}")
print(f"CSV file saved as: {csv_file_path}")


###############AIR QUAlITY DATA###################
# Google API Key
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

#####################Car Speed##################

# Load the CSV file with GPS coordinates
file_path = "GPS_Paris.csv"
df = pd.read_csv(file_path)

# Parameters
RADIUS_KM = 1  # 1 km radius
NUM_POINTS = 50  # Generate 50 random points per location
API_URL = "https://roads.googleapis.com/v1/nearestRoads"

# Function to generate random GPS points within a radius
def generate_random_points(center_lat, center_lon, radius_km, num_points):
    points = []
    for _ in range(num_points):
        angle = random.uniform(0, 2 * math.pi)  # Random direction
        distance_km = random.uniform(0, radius_km)  # Random distance within radius
        delta_lat = (distance_km / 111) * math.cos(angle)  # Convert km to degrees latitude
        delta_lon = (distance_km / (111 * math.cos(math.radians(center_lat)))) * math.sin(angle)  # Convert km to degrees longitude
        points.append(f"{center_lat + delta_lat},{center_lon + delta_lon}")
    return "|".join(points)

# Function to count unique roads by placeId near a location
def count_unique_roads_by_placeId(lat, lon, api_key):
    # Generate 50 random points in 1 km radius
    random_points = generate_random_points(lat, lon, RADIUS_KM, NUM_POINTS)

    # Google Roads API Request
    url = f"{API_URL}?points={random_points}&key={api_key}"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        unique_roads = set()  # Using a set to ensure uniqueness of road segments

        # Extract unique road segments from API response
        for point in data.get("snappedPoints", []):
            place_id = point.get("placeId")
            if place_id:  # Only add valid placeIds
                unique_roads.add(place_id)

        # Return the average number of unique roads per random point
        return len(unique_roads) / NUM_POINTS
    else:
        print(f"Error fetching data for {lat}, {lon}: {response.status_code} - {response.text}")
        return "N/A"

# Process all GPS locations in the CSV file
output_data = []
for _, row in df.iterrows():
    try:
        arrond = row["Arrondissement"]
        lat, lon = map(float, row["GPS"].split(", "))

        # Find average number of unique roads per random point
        unique_road_avg = count_unique_roads_by_placeId(lat, lon, API_KEY)

        # Append data
        output_data.append({
            "Arrondissement": arrond,
            "Latitude": lat,
            "Longitude": lon,
            "AvgUniqueRoads1kmRadius": unique_road_avg
        })

        #time.sleep(1)  # To avoid exceeding API rate limits

    except ValueError:
        print(f"Skipping invalid data: {row['GPS']}")

# Save results to CSV
output_file = "Avg_Unique_Roads_By_PlaceId.csv"
output_df = pd.DataFrame(output_data)
output_df.to_csv(output_file, index=False)

print(f"Process completed! Results saved to {output_file}")

#################Road Density##################

# Load the CSV file with GPS coordinates
file_path = "GPS_Paris.csv"
df = pd.read_csv(file_path)

# Parameters
RADIUS_KM = 1  # 1 km radius
NUM_POINTS = 50  # Generate 50 random points per location
API_URL = "https://roads.googleapis.com/v1/nearestRoads"

# Function to generate random GPS points within a radius
def generate_random_points(center_lat, center_lon, radius_km, num_points):
    points = []
    for _ in range(num_points):
        angle = random.uniform(0, 2 * math.pi)  # Random direction
        distance_km = random.uniform(0, radius_km)  # Random distance within radius
        delta_lat = (distance_km / 111) * math.cos(angle)  # Convert km to degrees latitude
        delta_lon = (distance_km / (111 * math.cos(math.radians(center_lat)))) * math.sin(angle)  # Convert km to degrees longitude
        points.append(f"{center_lat + delta_lat},{center_lon + delta_lon}")
    return "|".join(points)

# Function to count unique roads by placeId near a location
def count_unique_roads_by_placeId(lat, lon, api_key):
    # Generate 50 random points in 1 km radius
    random_points = generate_random_points(lat, lon, RADIUS_KM, NUM_POINTS)

    # Google Roads API Request
    url = f"{API_URL}?points={random_points}&key={api_key}"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        unique_roads = set()  # Using a set to ensure uniqueness of road segments

        # Extract unique road segments from API response
        for point in data.get("snappedPoints", []):
            place_id = point.get("placeId")
            if place_id:  # Only add valid placeIds
                unique_roads.add(place_id)

        # Return the average number of unique roads per random point
        return len(unique_roads) / NUM_POINTS
    else:
        print(f"Error fetching data for {lat}, {lon}: {response.status_code} - {response.text}")
        return "N/A"

# Process all GPS locations in the CSV file
output_data = []
for _, row in df.iterrows():
    try:
        arrond = row["Arrondissement"]
        lat, lon = map(float, row["GPS"].split(", "))

        # Find average number of unique roads per random point
        unique_road_avg = count_unique_roads_by_placeId(lat, lon, API_KEY)

        # Append data
        output_data.append({
            "Arrondissement": arrond,
            "Latitude": lat,
            "Longitude": lon,
            "AvgUniqueRoads1kmRadius": unique_road_avg
        })

        #time.sleep(1)  # To avoid exceeding API rate limits

    except ValueError:
        print(f"Skipping invalid data: {row['GPS']}")

# Save results to CSV
output_file = "Avg_Unique_Roads_By_PlaceId.csv"
output_df = pd.DataFrame(output_data)
output_df.to_csv(output_file, index=False)

print(f"Process completed! Results saved to {output_file}")

##############Number of bus and metro stations##############

# Load the CSV file with GPS coordinates
file_path = "GPS_Paris.csv"
df = pd.read_csv(file_path)

# Parameters
RADIUS_METERS = 1000  # Search within 1 km radius
API_URL = "https://places.googleapis.com/v1/places:searchNearby"

# Function to count nearby places of a specific type
def count_nearby_places(lat, lon, place_types, api_key):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.types"
    }
    
    data = {
        "includedTypes": place_types,  # Search for specified place types
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": lat,
                    "longitude": lon
                },
                "radius": RADIUS_METERS  # Search radius in meters
            }
        }
    }
    
    response = requests.post(API_URL, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        results = response.json().get("places", [])
        return len(results)  # Count the number of results
    else:
        print(f"Error fetching data for {lat}, {lon}: {response.status_code} - {response.text}")
        return "N/A"

# Process all GPS locations in the CSV file
output_data = []
for _, row in df.iterrows():
    try:
        arrond = row["Arrondissement"]
        lat, lon = map(float, row["GPS"].split(", "))

        # Count bus stations within the radius
        bus_station_count = count_nearby_places(lat, lon, ["bus_station"], API_KEY)

        # Count metro stations within the radius
        metro_station_count = count_nearby_places(lat, lon, ["subway_station"], API_KEY)

        # Append data
        output_data.append({
            "Arrondissement": arrond,
            "Latitude": lat,
            "Longitude": lon,
            "BusStations1km": bus_station_count,
            "MetroStations1km": metro_station_count,
            "TotalStations1km": (bus_station_count if isinstance(bus_station_count, int) else 0) + 
                                  (metro_station_count if isinstance(metro_station_count, int) else 0)
        })

    except ValueError:
        print(f"Skipping invalid data: {row['GPS']}")

# Save results to CSV
output_file = "Stations_Count.csv"
output_df = pd.DataFrame(output_data)
output_df.to_csv(output_file, index=False)

print(f"Process completed! Results saved to {output_file}")

