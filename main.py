import math
import re
import folium
import googlemaps


class CoordinatesSorter:
    """
    This class is used for sorting coordinates from a txt file and creating a map from the sorted coordinates. It uses
    Google Maps API which will calculate route between two coordinates on the road. This was used to create route for
    low-cost car "race" event - attendees were given unsorted list of coordinates.

    What information does this map has:
    - Checkpoint number
    - Coordinates
    - Description
    - Distance to next checkpoint

    :param gmaps_api_key: API key for Google Maps API
    :param coordinates_file_path: Filepath for file containing unsorted coordinates
    :param coordinates_start_point: Used if you want to start for example on third coordinate of coordinates list.
    """

    def __init__(self, gmaps_api_key: str, coordinates_file_path: str, coordinates_start_point: int = 0):
        self.gmaps_api_key = gmaps_api_key
        self.coordinates_file_path = coordinates_file_path
        self.gmaps = googlemaps.Client(key=self.gmaps_api_key)
        self.coordinates_start_point = coordinates_start_point

    @staticmethod
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

    @staticmethod
    def distance(coord1, coord2):
        """Calculate the Euclidean distance between two coordinates. Used before Google Maps API implementation."""
        x1, y1 = coord1
        x2, y2 = coord2
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    @staticmethod
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

    def read_coordinates_from_file(self, file_path):
        coordinates = []
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_number, line in enumerate(file, 1):
                try:
                    data = line.strip().split()
                    lat_dms, lon_dms = data[0], data[1]
                    description = ' '.join(data[2:]) if len(data) > 2 else None
                    lat_decimal = self.dms_to_decimal(lat_dms)
                    lon_decimal = self.dms_to_decimal(lon_dms)
                    coordinates.append((lat_decimal, lon_decimal, description))
                except ValueError as e:
                    print(f"Error in line {line_number}: {e}")
                    continue
        return coordinates

    @staticmethod
    def save_coordinates_to_file(file_path, coordinates, efficient_route):
        """Save the ordered coordinates to a new text file."""
        with open(file_path, 'w', encoding='utf-8') as file:
            for index in efficient_route:
                lat, lon, description = coordinates[index]
                file.write(f"{lat} {lon} {description}\n")

    @staticmethod
    def plot_map(coordinates, efficient_route):
        map_center = [sum(lat for lat, lon, _ in coordinates) / len(coordinates),
                      sum(lon for lat, lon, _ in coordinates) / len(coordinates)]
        my_map = folium.Map(location=map_center, zoom_start=12, tiles='Stamen Terrain')

        for i, (lat, lon, description) in enumerate([coordinates[i] for i in efficient_route]):
            popup = f"Coordinate {i + 1}: {description}" if description else f"Coordinate {i + 1}"
            folium.Marker(location=[lat, lon], popup=popup).add_to(my_map)

        folium.PolyLine(locations=[coordinates[i][:2] for i in efficient_route], color='red').add_to(my_map)

        my_map.save('map.html')

    def calculate_route(self):
        coordinates = self.read_coordinates_from_file(self.coordinates_file_path)

        efficient_route = self.nearest_neighbor(coordinates, self.coordinates_start_point, self.gmaps)

        print("Most efficient route:")
        for index in efficient_route:
            lat, lon, description = coordinates[index]
            print(f"Coordinate {index + 1}: ({lat}, {lon}) - {description}")

        # Save the ordered coordinates to a new text file
        save_path = 'ordered_coordinates.txt'  # Replace with the desired output file path
        self.save_coordinates_to_file(save_path, coordinates, efficient_route)
        print(f"Ordered coordinates saved to {save_path}")

        # Generate and display the satellite map
        self.plot_map(coordinates, efficient_route)

    def create_map_from_file(self, file_path):
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
        my_map = folium.Map(location=map_center, zoom_start=6, tiles=None)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Satellite',
            overlay=False,
            control=True
        ).add_to(my_map)
        folium.TileLayer(tiles='openstreetmap', name='Basic').add_to(my_map)

        for i, (lat, lon, description) in enumerate(coordinates):
            popup = self.get_marker_popup(i, f"Checkpoint {i + 1}, Location: {lat} {lon}: <br>{description}",
                                          coordinates)
            folium.Marker(location=[lat, lon], popup=folium.Popup(popup, max_width=300)).add_to(my_map)

        waypoints = [(lat, lon) for lat, lon, _ in coordinates]

        # Plot the red line by making requests for each pair of consecutive waypoints
        for i in range(len(waypoints) - 1):
            start_waypoint, end_waypoint = waypoints[i], waypoints[i + 1]
            directions = self.gmaps.directions(origin=start_waypoint, destination=end_waypoint, mode='driving')

            for step in directions[0]['legs'][0]['steps']:
                points = googlemaps.convert.decode_polyline(step['polyline']['points'])
                locations = [(point['lat'], point['lng']) for point in points]
                folium.PolyLine(locations=locations, color='red').add_to(my_map)

        folium.LayerControl().add_to(my_map)

        my_map.save('final_map_output.html')
        print("Map saved to final_map_output.html")

    def get_marker_popup(self, number, description, coordinates):
        if not description:
            return f"Checkpoint {number + 1}"

        popup = description

        if number < len(coordinates) - 1:
            current_coord = coordinates[number][:2]
            next_coord = coordinates[number + 1][:2]
            print(current_coord, next_coord)

            directions = self.gmaps.directions(origin=current_coord, destination=next_coord, mode='driving')
            print(directions)
            distance = directions[0]['legs'][0]['distance']['text']
            print(distance)
            popup += f"<br>Distance to next checkpoint: {distance}"

        string_of_popup = str(popup)

        with open("test.txt", "a", encoding="utf-8") as f:
            f.write(string_of_popup)
            f.write("\n")

        return popup


if __name__ == "__main__":
    sorter = CoordinatesSorter(gmaps_api_key='', coordinates_file_path='')

    sorter.calculate_route()
