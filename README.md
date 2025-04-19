# Business Search and Email Scraper

A web application that searches for businesses in a specified area and scrapes their contact information, including email addresses.

## Features

- Interactive map interface for selecting search locations
- Grid-based search covering a 5km radius
- Business information collection including:
  - Business name
  - Address
  - Website
  - Email addresses
- Excel file export of results
- Real-time progress updates

## Requirements

- Python 3.11 or higher
- Google Maps API key
- Playwright for web scraping

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/business-search.git
cd business-search
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
playwright install-deps
```

4. Create a `.env` file with your API keys:
```
GOOGLE_MAPS_API_KEY=your_api_key_here
FLASK_SECRET_KEY=your_secret_key_here
```

## Usage

1. Start the Flask application:
```bash
python main.py
```

2. Open your web browser and navigate to `http://localhost:5001`

3. Enter your Google Maps API key, select a location (either by clicking on the map or entering an address), and specify the industry to search for.

4. Click "Search" and wait for the results. The application will:
   - Create a search grid around your selected location
   - Find businesses in the area
   - Scrape their websites for email addresses
   - Generate an Excel file with all the information

5. Download the results by clicking the "Download Results" button that appears after the search is complete.

## Configuration

The application can be configured by modifying the following constants in `main.py`:
- `GRID_SIZE`: Number of points in the search grid (default: 3x3)
- `GRID_RADIUS`: Search radius in kilometers (default: 5km)
- `SEARCH_RADIUS`: Individual search radius in meters (default: 500m)

## License

MIT License

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request 