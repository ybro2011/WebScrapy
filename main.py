import os
import math
import re
import gc
import logging
import time
from datetime import datetime
from flask import Flask, render_template, request, Response, stream_with_context, send_file
import googlemaps
from openpyxl import Workbook
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Constants for grid search
EARTH_RADIUS = 6371  # Earth's radius in kilometers
DEFAULT_GRID_RADIUS = 5  # Default 5km radius

# Ensure the Documents directory exists
DOCUMENTS_DIR = os.path.join(os.path.expanduser('~'), 'Documents')
os.makedirs(DOCUMENTS_DIR, exist_ok=True)

def get_grid_size(density):
    """
    Get the grid size based on density setting.
    Returns the number of points in one dimension of the grid.
    """
    density_map = {
        'low': 3,    # 3x3 grid = 9 points
        'medium': 5,  # 5x5 grid = 25 points
        'high': 7     # 7x7 grid = 49 points
    }
    return density_map.get(density, 5)  # Default to medium if invalid

def create_search_grid(center_lat, center_lng, radius, density='medium'):
    """
    Create a grid of search points around a center point.
    Returns a list of (lat, lng) tuples including the center point.
    """
    grid_points = []
    
    # Get grid size based on density
    grid_size = get_grid_size(density)
    half_size = (grid_size - 1) // 2
    
    # Calculate the distance between grid points (in radians)
    distance_radians = radius / EARTH_RADIUS
    
    # Convert center coordinates to radians
    center_lat_rad = math.radians(center_lat)
    center_lng_rad = math.radians(center_lng)
    
    # Create grid points
    for i in range(-half_size, half_size + 1):
        for j in range(-half_size, half_size + 1):
            # Calculate new latitude
            new_lat_rad = math.asin(
                math.sin(center_lat_rad) * math.cos(distance_radians) +
                math.cos(center_lat_rad) * math.sin(distance_radians) * math.cos(math.radians(i * 90))
            )
            
            # Calculate new longitude
            new_lng_rad = center_lng_rad + math.atan2(
                math.sin(math.radians(j * 90)) * math.sin(distance_radians) * math.cos(center_lat_rad),
                math.cos(distance_radians) - math.sin(center_lat_rad) * math.sin(new_lat_rad)
            )
            
            # Convert back to degrees
            new_lat = math.degrees(new_lat_rad)
            new_lng = math.degrees(new_lng_rad)
            
            grid_points.append((new_lat, new_lng))
    
    return grid_points

def get_location_coordinates(gmaps, location_name):
    """
    Get coordinates for a location name using Google Maps Geocoding API.
    Returns a tuple of (latitude, longitude).
    """
    try:
        geocode_result = gmaps.geocode(location_name)
        if not geocode_result:
            raise ValueError(f"Could not find coordinates for location: {location_name}")
        
        location = geocode_result[0]['geometry']['location']
        return (location['lat'], location['lng'])
    except Exception as e:
        logger.error(f"Error getting coordinates for {location_name}: {e}")
        raise

def search_places(gmaps, location, query, radius=5000):
    """
    Search for places near a location using Google Maps Places API.
    Returns a list of place results (up to 60 results per search).
    """
    try:
        all_results = []
        
        # Initial search with timeout handling
        try:
            places_result = gmaps.places_nearby(
                location=location,
                radius=radius,
                keyword=query
            )
            results = places_result.get('results', [])
            all_results.extend(results)
            
            # Handle pagination (up to 2 more pages = 60 total results)
            next_page_token = places_result.get('next_page_token')
            while next_page_token and len(all_results) < 60:
                # Wait for the token to become valid (Google requires a short delay)
                time.sleep(2)
                
                try:
                    # Get next page of results with timeout handling
                    places_result = gmaps.places_nearby(
                        page_token=next_page_token
                    )
                    results = places_result.get('results', [])
                    all_results.extend(results)
                    
                    # Get next page token if available
                    next_page_token = places_result.get('next_page_token')
                    
                    # Break if we've reached the maximum results
                    if len(all_results) >= 60:
                        break
                except Exception as e:
                    logger.error(f"Error getting next page: {e}")
                    break
        except Exception as e:
            logger.error(f"Error in initial search: {e}")
            return []
        
        return all_results
    except Exception as e:
        logger.error(f"Error searching places: {e}")
        return []

def get_place_details(gmaps, place_id):
    """
    Get detailed information about a place using Google Maps Places API.
    Returns a dictionary of place details.
    """
    try:
        place_details = gmaps.place(place_id, fields=['name', 'formatted_address', 'formatted_phone_number', 'website', 'rating', 'user_ratings_total'])
        result = place_details.get('result', {})
        
        return {
            'name': result.get('name', ''),
            'address': result.get('formatted_address', ''),
            'phone': result.get('formatted_phone_number', ''),
            'website': result.get('website', ''),
            'rating': result.get('rating', ''),
            'reviews': result.get('user_ratings_total', ''),
            'email': ''  # Empty email since we're not scraping websites
        }
    except Exception as e:
        logger.error(f"Error getting place details: {e}")
        return {
            'name': '',
            'address': '',
            'phone': '',
            'website': '',
            'rating': '',
            'reviews': '',
            'email': ''
        }

def save_to_excel(businesses, filename):
    """
    Save business data to an Excel file.
    Returns the path to the saved file.
    """
    wb = Workbook()
    ws = wb.active
    
    # Add headers
    headers = ['Name', 'Address', 'Phone', 'Website', 'Rating', 'Reviews']
    for col, header in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=header)
    
    # Add data
    for row, business in enumerate(businesses, 2):
        ws.cell(row=row, column=1, value=business['name'])
        ws.cell(row=row, column=2, value=business['address'])
        ws.cell(row=row, column=3, value=business['phone'])
        ws.cell(row=row, column=4, value=business['website'])
        ws.cell(row=row, column=5, value=business['rating'])
        ws.cell(row=row, column=6, value=business['reviews'])

    
    # Save file
    file_path = os.path.join(DOCUMENTS_DIR, filename)
    wb.save(file_path)
    return file_path

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    try:
        api_key = request.form['api_key']
        location_name = request.form['location']
        industry = request.form['industry']
        radius = float(request.form.get('radius', DEFAULT_GRID_RADIUS))
        density = request.form.get('density', 'medium')
        
        def generate_updates():
            yield "Starting search...\n"
            yield f"Using search radius: {radius} km\n"
            yield f"Using search density: {density} ({get_grid_size(density)}x{get_grid_size(density)} grid)\n"
            yield "Using 5km radius for each individual search point\n"
            yield "Fetching up to 60 results per search point\n"
            
            # Initialize Google Maps client
            gmaps = googlemaps.Client(key=api_key)
            
            yield f"Converting location '{location_name}' to coordinates...\n"
            try:
                center_location = get_location_coordinates(gmaps, location_name)
                yield f"Found center coordinates: {center_location}\n"
                
                # Create search grid
                grid_points = create_search_grid(center_location[0], center_location[1], radius, density)
                yield f"Created search grid with {len(grid_points)} points\n"
                
            except Exception as e:
                yield f"Error: {str(e)}\n"
                return
            
            yield f"Searching for {industry} businesses in the area...\n"
            
            # Search for places in each grid point
            all_places = []
            api_calls = 0
            max_api_calls = 45  # Leave room for place details
            
            for i, (lat, lng) in enumerate(grid_points, 1):
                if api_calls >= max_api_calls:
                    yield "Warning: Reached API quota limit. Some areas may not be searched.\n"
                    break
                    
                yield f"Searching grid point {i}/{len(grid_points)} at ({lat}, {lng})...\n"
                try:
                    places = search_places(gmaps, (lat, lng), industry)
                    all_places.extend(places)
                    api_calls += 1
                    yield f"Found {len(places)} places at this point\n"
                except Exception as e:
                    logger.error(f"Error searching grid point: {e}")
                    yield f"Error searching grid point: {str(e)}\n"
                    continue
                
                # Add a small delay between searches to avoid rate limiting
                time.sleep(1)
            
            # Remove duplicates based on place_id
            unique_places = {place['place_id']: place for place in all_places}.values()
            yield f"Total unique places found: {len(unique_places)}\n"
            
            # Process each place
            businesses = []
            for i, place in enumerate(unique_places, 1):
                if api_calls >= 60:  # Google's daily quota
                    yield "Warning: Reached API quota limit. Some place details may be missing.\n"
                    break
                    
                place_id = place['place_id']
                place_name = place.get('name', 'Unknown')
                yield f"Processing {i}/{len(unique_places)}: {place_name}...\n"
                
                try:
                    details = get_place_details(gmaps, place_id)
                    businesses.append(details)
                    api_calls += 1
                except Exception as e:
                    logger.error(f"Error getting place details: {e}")
                    yield f"Error getting details for {place_name}: {str(e)}\n"
                    continue
                
                # Force garbage collection after each business
                gc.collect()
                
                # Add a small delay between API calls
                time.sleep(1)
            
            # Save to Excel
            filename = f"{industry.replace(' ', '_')}_businesses.xlsx"
            file_path = save_to_excel(businesses, filename)
            yield f"Success! Results saved to {filename}\n"
            yield f"DOWNLOAD_URL:/download/{filename}\n"
            
        return Response(stream_with_context(generate_updates()), mimetype='text/plain')
        
    except Exception as e:
        logger.error(f"Error in search: {e}")
        return Response(f"Error: {str(e)}\n", mimetype='text/plain', status=500)

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(DOCUMENTS_DIR, filename)
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)


