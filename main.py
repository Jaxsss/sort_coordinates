import math
import re
import folium
import googlemaps


def dms_to_decimal(dms_str):
    """Convert coordinates in DMS (Degrees Minutes Seconds) format to decimal format."""

    dms_pattern = re.compile(r'(\d+)°(\d+)‘(\d+)“([NSEW])')
    match = dms_pattern.match(dms_str)

    if match:
        degrees, minutes, seconds, direction = match.groups()
        degrees, minutes, seconds = int(degrees), int(minutes), int(seconds)

        decimal = degrees + minutes / 60 + seconds / 3600
        if direction in ['S', 'W']:
            decimal = -decimal

        return decimal
    else:
        raise ValueError(f"Invalid DMS format: {dms_str}")


def distance(coord1, coord2):
    """Calculate the Euclidean distance between two coordinates."""

    x1, y1 = coord1
    x2, y2 = coord2
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def nearest_neighbor(coordinates, start, gmaps):
    """Find the nearest neighbor to each coordinate starting from the given point."""

    num_coords = len(coordinates)
    remaining_coords = set(range(num_coords))
    remaining_coords.remove(start)
    current_coord = start
    route = [current_coord]

    while remaining_coords:
        nearest_distance = float('inf')
        nearest_coord = None

        for coord in remaining_coords:
            origin = coordinates[current_coord]
            destination = coordinates[coord]
            result = gmaps.distance_matrix(origin, destination, mode="driving", units="metric")

            if result["rows"][0]["elements"][0]["status"] == "OK":
                dist = result["rows"][0]["elements"][0]["distance"]["value"]
                if dist < nearest_distance:
                    nearest_distance = dist
                    nearest_coord = coord

        route.append(nearest_coord)
        current_coord = nearest_coord
        remaining_coords.remove(nearest_coord)

    return route


def read_coordinates_from_file(file_path):
    coordinates = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line_number, line in enumerate(file, 1):
            try:
                data = line.strip().split()
                lat_dms, lon_dms = data[0], data[1]
                description = ' '.join(data[2:]) if len(data) > 2 else None
                lat_decimal = dms_to_decimal(lat_dms)
                lon_decimal = dms_to_decimal(lon_dms)
                coordinates.append((lat_decimal, lon_decimal, description))
            except ValueError as e:
                print(f"Error in line {line_number}: {e}")
                continue
    return coordinates


def save_coordinates_to_file(file_path, coordinates, efficient_route):
    """Save the ordered coordinates to a new text file."""
    with open(file_path, 'w', encoding='utf-8') as file:
        for index in efficient_route:
            lat, lon, description = coordinates[index]
            file.write(f"{lat} {lon} {description}\n")


def plot_map(coordinates, efficient_route):
    map_center = [sum(lat for lat, lon, _ in coordinates) / len(coordinates),
                  sum(lon for lat, lon, _ in coordinates) / len(coordinates)]
    my_map = folium.Map(location=map_center, zoom_start=12, tiles='Stamen Terrain')

    for i, (lat, lon, description) in enumerate([coordinates[i] for i in efficient_route]):
        popup = f"Coordinate {i + 1}: {description}" if description else f"Coordinate {i + 1}"
        folium.Marker(location=[lat, lon], popup=popup).add_to(my_map)

    folium.PolyLine(locations=[coordinates[i][:2] for i in efficient_route], color='red').add_to(my_map)

    my_map.save('map.html')


def main():
    gmaps_api_key = 'YOUR_API_KEY'
    gmaps = googlemaps.Client(key=gmaps_api_key)

    # Replace with the path to your text file
    file_path = 'coordinates.txt'
    coordinates = read_coordinates_from_file(file_path)

    # Replace '0' with the index of the starting point in the coordinates list
    start_point = 0

    efficient_route = nearest_neighbor(coordinates, start_point, gmaps)

    print("Most efficient route:")
    for index in efficient_route:
        lat, lon, description = coordinates[index]
        print(f"Coordinate {index + 1}: ({lat}, {lon}) - {description}")

    # Save the ordered coordinates to a new text file
    # Replace with the desired output file path
    save_path = 'ordered_coordinates.txt'
    save_coordinates_to_file(save_path, coordinates, efficient_route)
    print(f"Ordered coordinates saved to {save_path}")

    # Generate and display the satellite map
    plot_map(coordinates, efficient_route)


def create_map_from_file(file_path):
    coordinates = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            try:
                data = line.strip().split()
                lat, lon = map(float, data[:2])
                description = ' '.join(data[2:]) if len(data) > 2 else None
                coordinates.append((lat, lon, description))
            except ValueError as e:
                print(f"Error in line: {e}")
                continue

    map_center = [sum(lat for lat, lon, _ in coordinates) / len(coordinates),
                  sum(lon for lat, lon, _ in coordinates) / len(coordinates)]
    my_map = folium.Map(location=map_center, zoom_start=12, tiles='Stamen Terrain')

    for i, (lat, lon, description) in enumerate(coordinates):
        popup = f"Coordinate {i + 1}, Location: {lat} {lon}: <br>{description}" if description else f"Coordinate {i + 1}"
        folium.Marker(location=[lat, lon], popup=folium.Popup(popup, max_width=300)).add_to(my_map)

    # Fetch directions using Google Maps Directions API
    gmaps_api_key = 'YOUR_API_KEY'
    gmaps = googlemaps.Client(key=gmaps_api_key)

    waypoints = [(lat, lon) for lat, lon, _ in coordinates]

    # Plot the red line by making requests for each pair of consecutive waypoints
    for i in range(len(waypoints) - 1):
        start_waypoint, end_waypoint = waypoints[i], waypoints[i + 1]
        directions = gmaps.directions(origin=start_waypoint, destination=end_waypoint, mode='driving')

        for step in directions[0]['legs'][0]['steps']:
            points = googlemaps.convert.decode_polyline(step['polyline']['points'])
            locations = [(point['lat'], point['lng']) for point in points]
            folium.PolyLine(locations=locations, color='red').add_to(my_map)

    my_map.save('map_from_file.html')
    print("Map saved to map_from_file.html")


if __name__ == "__main__":
    create_map_from_file('ordered_coordinates.txt')
    # main()
