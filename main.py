from flask import Flask, render_template, request, send_file
import googlemaps
import openpyxl
import time
import os
import re
from playwright.sync_api import sync_playwright
import json
from dotenv import load_dotenv
import logging

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
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
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

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    try:
        api_key = request.form['api_key']
        location = request.form['location']
        industry = request.form['industry']
        
        # Initialize Google Maps client
        gmaps = googlemaps.Client(key=api_key)
        
        # Convert location string to tuple
        lat, lng = map(float, location.split(','))
        location_tuple = (lat, lng)
        
        # Search for places
        places = search_places(gmaps, location_tuple, industry)
        
        # Process each place
        businesses = []
        for place in places:
            place_id = place['place_id']
            details = get_place_details(gmaps, place_id)
            website = details.get('website')
            
            if website:
                emails = fetch_emails_from_website(website)
                details['email'] = emails
            else:
                details['email'] = ""
                
            businesses.append(details)
        
        # Save to Excel
        filename = f"{industry.replace(' ', '_')}_businesses.xlsx"
        file_path = os.path.join(os.path.expanduser('~'), 'Documents', filename)
        save_to_excel(businesses, file_path)
        
        # Return the file for download
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error in search: {e}")
        return render_template('index.html', 
                             message=f"Error: {str(e)}",
                             message_type="error")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)


