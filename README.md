# Business Search Web Application

A Flask-based web application that searches for businesses in a specified location using the Google Maps API and generates an Excel spreadsheet with their details.

## Features

- Search for businesses by location and industry
- Automatically scrape email addresses from business websites
- Generate Excel spreadsheets with business information
- Simple and intuitive web interface

## Requirements

- Python 3.9 or higher
- Google Maps API key with Places API enabled
- Playwright for web scraping

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/business-search.git
cd business-search
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:
```bash
python -m playwright install
```

## Usage

1. Start the Flask application:
```bash
python main.py
```

2. Open your web browser and navigate to `http://localhost:5001`

3. Enter your Google Maps API key, location coordinates (latitude,longitude), and industry to search for

4. Click "Search" to generate and download the Excel spreadsheet

## Configuration

The application uses environment variables for configuration. Create a `.env` file with the following variables:

```
FLASK_SECRET_KEY=your_secret_key
```

## License

MIT License 