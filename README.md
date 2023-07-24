# Sort coordinates
This repo is for a script that sorts Lat - Lon coordinates and creates route based on a starting point.

### Things needed for script to run
- Coordinates with description in this format (just an example) - 40°01‘01“N 15°01‘01“E Description that can be long as you want

### Features
- this script uses Google Maps API
- it creates a list of sorted coordinates based on Google Maps route from one point to another by road
- generates a map by using Folium lib and creates red line that tracks the road

### Libraries used
- math
- re
- folium
- googlemaps
- matplotlib

### Issues
I've had some issues while developing, the coordinates were in a different format and Python couldn't recognize them, so I had to implement a method that unified the coordinates.
