import os
import time
import requests
import icalendar
from datetime import datetime
from urllib.parse import urlparse, urlunparse, quote, unquote
import configparser

def load_config(config_path):
    """Load configuration from a file."""
    config = configparser.ConfigParser(interpolation=None)  # Disable interpolation
    config.read(config_path)
    return config

def load_urls(file_path):
    """Load URLs from a file, ignoring comments and empty lines."""
    urls = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line.startswith('#') or not line:
                    continue
                urls.append(line)
    except FileNotFoundError:
        print(f"URL file '{file_path}' not found.")
    return urls

def sanitize_url(url):
    """Sanitize URL to ensure proper encoding."""
    parsed_url = urlparse(url)
    # Decode any already-encoded path
    decoded_path = unquote(parsed_url.path)
    # Re-encode the path to ensure proper encoding
    sanitized_path = quote(decoded_path)
    return urlunparse((parsed_url.scheme, parsed_url.netloc, sanitized_path, parsed_url.params, parsed_url.query, parsed_url.fragment))

def fetch_calendar(url):
    """Fetch an iCal calendar from a URL."""
    sanitized_url = sanitize_url(url)
    try:
        response = requests.get(sanitized_url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching calendar from {sanitized_url}: {e}")
        return None

def merge_calendars(calendar_urls):
    """Merge multiple iCal calendars into one."""
    combined_calendar = icalendar.Calendar()
    combined_calendar.add('prodid', '-//Merged Calendar//Example//EN')
    combined_calendar.add('version', '2.0')

    for url in calendar_urls:
        calendar_data = fetch_calendar(url)
        if calendar_data:
            try:
                calendar = icalendar.Calendar.from_ical(calendar_data)
                for component in calendar.walk():
                    if component.name == "VEVENT":
                        combined_calendar.add_component(component)
            except ValueError as e:
                print(f"Error parsing calendar from {url}: {e}")

    return combined_calendar

def save_calendar(calendar, output_path):
    """Save the merged calendar to a file."""
    with open(output_path, 'wb') as f:
        f.write(calendar.to_ical())

def sync_calendars(url_file_path, config):
    """Sync calendars as per the configuration."""
    output_path = config.get('settings', 'output_path')
    sync_interval = int(config.get('settings', 'sync_interval'))

    while True:
        print(f"Starting sync at {datetime.now()}")
        calendar_urls = load_urls(url_file_path)
        if not calendar_urls:
            print("No valid calendar URLs found.")
        else:
            merged_calendar = merge_calendars(calendar_urls)
            save_calendar(merged_calendar, output_path)
        print(f"Sync complete. Next sync in {sync_interval} seconds.")
        time.sleep(sync_interval)

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    CONFIG_PATH = os.path.join(script_dir, 'config.ini')
    URL_FILE_PATH = os.path.join(script_dir, 'calendar_urls.txt')

    if not os.path.exists(CONFIG_PATH):
        print(f"Configuration file '{CONFIG_PATH}' not found.")
        exit(1)

    if not os.path.exists(URL_FILE_PATH):
        print(f"URL file '{URL_FILE_PATH}' not found.")
        print("Please create a URL file with the following format:\n")
        print("""
# Example of a URL file
https://example.com/calendar1.ics
https://example.com/calendar2.ics
# Comments are ignored
        """)
        exit(1)

    config = load_config(CONFIG_PATH)
    sync_calendars(URL_FILE_PATH, config)
