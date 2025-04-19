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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))

# Log environment variables
logger.info(f"FLASK_ENV: {os.getenv('FLASK_ENV')}")
logger.info(f"PORT: {os.getenv('PORT')}")
logger.info(f"PYTHONPATH: {os.getenv('PYTHONPATH')}")

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
    with sync_playwright() as p:
        try:
            browser_path = os.path.join(
                os.environ.get('PLAYWRIGHT_BROWSERS_PATH', ''),
                'chromium-1091',
                'chrome-linux',
                'chrome'
            )
            
            if not os.path.exists(browser_path):
                logger.error(f"Browser not found at path: {browser_path}")
                logger.error(f"Available files in directory: {os.listdir(os.path.dirname(browser_path))}")
                return "Browser not found"
            
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox'],
                executable_path=browser_path
            )
            page = browser.new_page()
            try:
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
            logger.error(f"Browser path: {browser_path}")
            logger.error(f"Environment: {os.environ.get('PLAYWRIGHT_BROWSERS_PATH')}")
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
    return render_template('index.html')

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
                location_tuple = get_location_coordinates(gmaps, location_name)
                yield f"Found coordinates: {location_tuple}\n"
            except Exception as e:
                yield f"Error: {str(e)}\n"
                return
            
            yield f"Searching for {industry} businesses near {location_name}...\n"
            
            # Search for places
            places = search_places(gmaps, location_tuple, industry)
            yield f"Found {len(places)} places\n"
            
            # Process each place
            businesses = []
            for i, place in enumerate(places, 1):
                place_id = place['place_id']
                place_name = place.get('name', 'Unknown')
                yield f"Processing {i}/{len(places)}: {place_name}...\n"
                
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
            
            # Save to Excel
            filename = f"{industry.replace(' ', '_')}_businesses.xlsx"
            file_path = os.path.join(os.path.expanduser('~'), 'Documents', filename)
            save_to_excel(businesses, file_path)
            yield f"Success! Results saved to {filename}\n"
            
        return Response(stream_with_context(generate_updates()), mimetype='text/plain')
        
    except Exception as e:
        logger.error(f"Error in search: {e}")
        return Response(f"Error: {str(e)}\n", mimetype='text/plain', status=500)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)


