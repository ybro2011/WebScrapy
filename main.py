from flask import Flask, render_template, request, send_file, Response
import googlemaps
import openpyxl
import time
import os
import re
from playwright.sync_api import sync_playwright
import json
from dotenv import load_dotenv
import logging
from flask import stream_with_context
import gc
import math

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))

# Constants for grid search
EARTH_RADIUS = 6371  # Earth's radius in kilometers
GRID_SIZE = 3  # 3x3 grid
GRID_RADIUS = 5  # 5km radius

def create_search_grid(center_lat, center_lng):
    """
    Create a grid of search points around a center point.
    Returns a list of (lat, lng) tuples including the center point.
    """
    grid_points = []
    
    # Calculate the distance between grid points (in radians)
    distance_radians = GRID_RADIUS / EARTH_RADIUS
    
    # Convert center coordinates to radians
    center_lat_rad = math.radians(center_lat)
    center_lng_rad = math.radians(center_lng)
    
    # Create grid points
    for i in range(-1, 2):  # -1, 0, 1 for 3x3 grid
        for j in range(-1, 2):
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

def search_places(gmaps, location, industry, radius=500):
    places = []
    response = gmaps.places_nearby(location=location, radius=radius, keyword=industry)
    places.extend(response.get('results', []))
    while 'next_page_token' in response:
        time.sleep(2)  # Comply with API requirements
        response = gmaps.places_nearby(page_token=response['next_page_token'])
        places.extend(response.get('results', []))
    return places

def get_place_details(gmaps, place_id):
    fields = ['name', 'formatted_address', 'website']
    detail = gmaps.place(place_id=place_id, fields=fields)
    return detail.get('result', {})

def fetch_emails_from_website(url):
    emails = set()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            try:
                page = browser.new_page()
                page.goto(url, timeout=10000)
                # Extract emails from mailto links
                mailto_links = page.query_selector_all('a[href^="mailto:"]')
                for link in mailto_links:
                    email = link.get_attribute('href').replace('mailto:', '').split('?')[0]
                    emails.add(email)
                # Extract emails from the text content
                page_content = page.content()
                found_emails = re.findall(r'[\w\.-]+@[\w\.-]+', page_content)
                emails.update(found_emails)
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
            finally:
                browser.close()
    except Exception as e:
        logger.error(f"Error launching browser: {e}")
    return ', '.join(emails)

def save_to_excel(businesses, filename):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Businesses"
    headers = ["Name", "Website", "Address", "Email"]
    ws.append(headers)
    for b in businesses:
        ws.append([
            b.get("name"),
            b.get("website", ""),
            b.get("formatted_address", ""),
            b.get("email", "")
        ])
    wb.save(filename)
    return filename

def get_location_coordinates(gmaps, location_name):
    try:
        # Check if the input is already in coordinate format (lat,lng)
        if ',' in location_name:
            try:
                lat, lng = map(float, location_name.split(','))
                return (lat, lng)
            except ValueError:
                pass  # Not valid coordinates, continue with geocoding
        
        # If not coordinates, try geocoding
        geocode_result = gmaps.geocode(location_name)
        if not geocode_result:
            raise ValueError(f"Could not find coordinates for location: {location_name}")
        location = geocode_result[0]['geometry']['location']
        return (location['lat'], location['lng'])
    except Exception as e:
        logger.error(f"Error geocoding location {location_name}: {e}")
        raise

@app.route('/', methods=['GET'])
def index():
    # Get Google Maps API key from environment variable or use the one from the form
    api_key = os.getenv('GOOGLE_MAPS_API_KEY', '')
    return render_template('index.html', api_key=api_key)

@app.route('/search', methods=['POST'])
def search():
    try:
        api_key = request.form['api_key']
        location_name = request.form['location']
        industry = request.form['industry']
        
        def generate_updates():
            yield "Starting search...\n"
            
            # Initialize Google Maps client
            gmaps = googlemaps.Client(key=api_key)
            
            yield f"Converting location '{location_name}' to coordinates...\n"
            try:
                center_location = get_location_coordinates(gmaps, location_name)
                yield f"Found center coordinates: {center_location}\n"
                
                # Create search grid
                grid_points = create_search_grid(center_location[0], center_location[1])
                yield f"Created search grid with {len(grid_points)} points\n"
                
            except Exception as e:
                yield f"Error: {str(e)}\n"
                return
            
            yield f"Searching for {industry} businesses in the area...\n"
            
            # Search for places in each grid point
            all_places = []
            for i, (lat, lng) in enumerate(grid_points, 1):
                yield f"Searching grid point {i}/{len(grid_points)} at ({lat}, {lng})...\n"
                places = search_places(gmaps, (lat, lng), industry, radius=500)
                all_places.extend(places)
                yield f"Found {len(places)} places at this point\n"
            
            # Remove duplicates based on place_id
            unique_places = {place['place_id']: place for place in all_places}.values()
            yield f"Total unique places found: {len(unique_places)}\n"
            
            # Process each place
            businesses = []
            for i, place in enumerate(unique_places, 1):
                place_id = place['place_id']
                place_name = place.get('name', 'Unknown')
                yield f"Processing {i}/{len(unique_places)}: {place_name}...\n"
                
                details = get_place_details(gmaps, place_id)
                website = details.get('website')
                
                if website:
                    yield f"Scraping emails from {website}...\n"
                    emails = fetch_emails_from_website(website)
                    details['email'] = emails
                    if emails:
                        yield f"Found emails: {emails}\n"
                else:
                    details['email'] = ""
                    yield "No website found\n"
                    
                businesses.append(details)
                
                # Force garbage collection after each business
                gc.collect()
            
            # Save to Excel
            filename = f"{industry.replace(' ', '_')}_businesses.xlsx"
            file_path = os.path.join(os.path.expanduser('~'), 'Documents', filename)
            save_to_excel(businesses, file_path)
            yield f"Success! Results saved to {filename}\n"
            yield f"DOWNLOAD_URL:/download/{filename}\n"
            
        return Response(stream_with_context(generate_updates()), mimetype='text/plain')
        
    except Exception as e:
        logger.error(f"Error in search: {e}")
        return Response(f"Error: {str(e)}\n", mimetype='text/plain', status=500)

@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join(os.path.expanduser('~'), 'Documents', filename)
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {e}")
        return Response(f"Error downloading file: {str(e)}", status=500)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)


