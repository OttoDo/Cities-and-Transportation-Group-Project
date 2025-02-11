import pandas as pd
import requests
import json
import random
import math
import time
import folium
from IPython.display import display
from datetime import datetime


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
API_KEY = "API" #########################Please change to your own API############################ 

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

# API Endpoints
ROADS_API_URL = "https://roads.googleapis.com/v1/nearestRoads"
DIRECTIONS_API_URL = "https://maps.googleapis.com/maps/api/directions/json"

# Function to find the closest road segment using Roads API
def get_nearest_road(lat, lon, api_key):
    url = f"{ROADS_API_URL}?points={lat},{lon}&key={api_key}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        snapped_points = data.get("snappedPoints", [])
        if snapped_points:
            snapped_location = snapped_points[0]["location"]
            return snapped_location["latitude"], snapped_location["longitude"]
    
    print(f"Error fetching nearest road for {lat}, {lon}: {response.status_code} - {response.text}")
    return lat, lon  # Fallback to original coordinates if snapping fails

# Function to get travel time, distance, and speed on the closest road segment
def get_car_travel_data(snapped_lat, snapped_lon, api_key):
    dest_lat = snapped_lat + 0.0005  # Offset destination slightly to avoid same point issue
    dest_lon = snapped_lon + 0.0005
    
    url = f"{DIRECTIONS_API_URL}?origin={snapped_lat},{snapped_lon}&destination={dest_lat},{dest_lon}&mode=driving&key={api_key}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if "routes" in data and data["routes"]:
            legs = data["routes"][0]["legs"]
            if legs:
                distance_m = legs[0]["distance"]["value"]  # Distance in meters
                duration_s = legs[0]["duration"]["value"]  # Duration in seconds
                speed_kmh = round((distance_m / duration_s) * 3.6, 2) if duration_s > 0 else "N/A"  # Convert m/s to km/h
                return duration_s, distance_m, speed_kmh

    print(f"Error fetching travel data for {snapped_lat}, {snapped_lon}: {response.status_code} - {response.text}")
    return "N/A", "N/A", "N/A"

# Process all GPS locations in the CSV file
output_data = []
for _, row in df.iterrows():
    try:
        arrond = row["Arrondissement"]
        lat, lon = map(float, row["GPS"].split(", "))

        # Find nearest road segment
        snapped_lat, snapped_lon = get_nearest_road(lat, lon, API_KEY)

        # Get travel time, distance, and speed on the nearest road segment
        travel_time, travel_distance, car_speed = get_car_travel_data(snapped_lat, snapped_lon, API_KEY)

        # Append data
        output_data.append({
            "Arrondissement": arrond,
            "Latitude": lat,
            "Longitude": lon,
            "SnappedLatitude": snapped_lat,
            "SnappedLongitude": snapped_lon,
            "TravelTimeSeconds": travel_time,
            "TravelDistanceMeters": travel_distance,
            "SpeedKmh": car_speed
        })

    except ValueError:
        print(f"Skipping invalid data: {row['GPS']}")

# Save results to separate CSV file
output_file = "Car_Travel_Speed_Snapped.csv"
output_df = pd.DataFrame(output_data)
output_df.to_csv(output_file, index=False)

print(f"Process completed! Results saved to {output_file}")


#################Road Density##################

# Parameters
RADIUS_KM = 0.5  # 1 km radius
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
            "AvgUniqueRoads500mRadius": unique_road_avg
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

# Parameters
RADIUS_METERS = 500  # Search within 500 m radius
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

#################Waiting Time########################

# Load the GPS data from the CSV file
csv_file_path = "GPS_Paris.csv"
df = pd.read_csv(csv_file_path)

# Clean GPS data
df["GPS"] = df["GPS"].astype(str).str.strip().str.replace("\n", "", regex=True)
df[["Latitude", "Longitude"]] = df["GPS"].str.split(",", expand=True)
df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")

# Function to check if it's night when the metro is closed
def is_metro_closed():
    now = datetime.now()
    if now.weekday() in [0, 1, 2, 3, 6]:  # Mon-Thu, Sun
        return now.hour >= 0 and now.hour < 5.5  # 12:30 AM - 5:30 AM
    elif now.weekday() in [4, 5]:  # Fri-Sat
        return now.hour >= 1.25 and now.hour < 5.5  # 1:15 AM - 5:30 AM
    return False

# Function to find the nearest transit station (metro or night bus)
def find_nearest_transit(lat, lon, transit_type="transit_station"):
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lon}&radius=1000&type={transit_type}&key={API_KEY}"
    response = requests.get(url).json()

    if "results" in response and response["results"]:
        place = response["results"][0]  # Pick the first nearby station
        name = place["name"]
        place_id = place["place_id"]
        print(f"🚏 Nearest station: {name} (Place ID: {place_id})")
        return place_id, name

    print("⚠️ No nearby transit station found.")
    return None, None

# Function to get the next departure, considering metro closures
def get_next_departure(lat, lon):
    now_timestamp = int(time.time())  # Current time in UNIX format
    future_timestamp = now_timestamp

    # If metro is closed, search for night buses
    if is_metro_closed():
        print("🚇 Metro is closed. Searching for night bus...")
        nearest_bus_stop_id, nearest_bus_stop_name = find_nearest_transit(lat, lon, "bus_station")
        if not nearest_bus_stop_id:
            print("❌ No night bus available. Metro reopens at 5:30 AM.")
            return None, None, "Metro closed, next departure at 5:30 AM"


    # Get the next transit departure (metro if open, night bus if metro is closed)
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={lat},{lon}&destination={lat+0.01},{lon+0.01}&mode=transit&departure_time={future_timestamp}&key={API_KEY}"
    response = requests.get(url).json()

    if "routes" in response and response["routes"]:
        for leg in response["routes"][0]["legs"]:
            for step in leg["steps"]:
                if step["travel_mode"] == "TRANSIT":
                    transit_details = step["transit_details"]
                    departure_time = transit_details["departure_time"]["text"]
                    departure_unix = transit_details["departure_time"]["value"]
                    waiting_time = max(0, (departure_unix - now_timestamp) // 60)  # Convert seconds to minutes

                    departure_stop = transit_details["departure_stop"]["name"]
                    arrival_stop = transit_details["arrival_stop"]["name"]

                    print(f"🕒 Next departure from {departure_stop} at {departure_time} (Waiting time: {waiting_time} min)")
                    return departure_stop, arrival_stop, waiting_time

    print("⚠️ No transit departures found.")
    return None, None, "N/A"

# Process each GPS location from the file
output_data = []


for _, row in df.iterrows():
    arrondissement = row["Arrondissement"]
    lat, lon = row["Latitude"], row["Longitude"]
    
    print(f"\n🔹 Processing location: {arrondissement}, {lat}, {lon}")

    # 1. Find nearest transit station
    nearest_station_id, nearest_station_name = find_nearest_transit(lat, lon)

    if not nearest_station_id:
        output_data.append([arrondissement, lat, lon, "N/A", "N/A", "N/A"])
        continue  # Skip to next row

    # 2. Get the next departure time and waiting time
    departure_stop, arrival_stop, waiting_time = get_next_departure(lat, lon)

    if not departure_stop:
        output_data.append([arrondissement, lat, lon, nearest_station_name, "N/A", "N/A"])
        continue  # Skip to next row

    # Save results
    output_data.append([arrondissement, lat, lon, departure_stop, arrival_stop, waiting_time])

    # Delay between API calls to avoid hitting rate limits
    time.sleep(1)

# Save output to CSV in the correct format
output_csv_path = "transit_wait_times_fixed.csv"
df_output = pd.DataFrame(output_data, columns=["Arrondissement", "Latitude", "Longitude", "DepartureStop", "ArrivalStop", "WaitingTime (min)"])
df_output.to_csv(output_csv_path, index=False)

print(f"\n CSV saved: {output_csv_path}")

