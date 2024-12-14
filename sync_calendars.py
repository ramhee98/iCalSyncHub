import os
import time
import requests
import icalendar
import configparser
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from urllib.parse import urlparse, urlunparse, quote, unquote
import random
import string
from pytz import timezone, all_timezones


def setup_logging(config):
    """Set up logging with rotation based on configuration."""
    # Get log level from config, default to INFO
    log_level = config.get('settings', 'log_level', fallback='INFO').upper()
    
    # Validate log level
    valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if log_level not in valid_log_levels:
        raise ValueError(f"Invalid log_level specified in config.ini: {log_level}. Must be one of {', '.join(valid_log_levels)}")

    # Get log output and file settings
    default = 'icalsynchub.log'
    log_output = config.get('settings', 'log_output', fallback='both').lower()
    log_file = config.get('settings', 'log_file', fallback=default)
    if not log_file.strip(): log_file=default
    max_log_file_size = int(config.get('settings', 'max_log_file_size', fallback=10)) * 1024 * 1024  # MB to bytes
    log_backup_count = int(config.get('settings', 'log_backup_count', fallback=5))

    # Configure logger
    logger = logging.getLogger(__name__)
    logger.setLevel(getattr(logging, log_level))

    # Create handlers based on log_output
    handlers = []

    if log_output in ('file', 'both') and log_file:
        if os.path.isdir(log_file):
            raise ValueError(f"The log_file setting points to a directory, not a file: {log_file}")
        file_handler = RotatingFileHandler(log_file, maxBytes=max_log_file_size, backupCount=log_backup_count)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)

    if log_output in ('console', 'both'):
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        handlers.append(console_handler)

    # No logging (disable all handlers)
    if log_output == 'none':
        logger.disabled = True
        return logger

    # Add handlers to logger
    for handler in handlers:
        logger.addHandler(handler)

    logger.info(f"Logging initialized with level {log_level}.")
    return logger


def load_config(config_path):
    """Load configuration from a file."""
    config = configparser.ConfigParser(interpolation=None)  # Disable interpolation
    config.read(config_path)
    return config


def save_config(config, config_path):
    """Save the updated configuration back to the file."""
    with open(config_path, 'w') as config_file:
        config.write(config_file)


def generate_random_filename():
    """Generate a random filename for the iCal file."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=64)) + '.ics'


def resolve_output_filename(config, config_path):
    """Ensure the filename is defined and saved to the configuration."""
    output_path = config.get('settings', 'output_path', fallback='./')
    filename = config.get('settings', 'filename', fallback=None)

    # Generate a random filename if not already defined
    if not filename:
        filename = generate_random_filename()
        config.set('settings', 'filename', filename)
        save_config(config, config_path)

    return os.path.join(output_path, filename)


def load_urls(file_path):
    """Load valid calendar URLs from a file."""
    try:
        with open(file_path, 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        logger.critical(f"URL file '{file_path}' not found.")
        logger.critical("Sync aborted, exiting!")
        exit(1)
        return []


def sanitize_url(url):
    """Sanitize URL to ensure proper encoding."""
    parsed_url = urlparse(url)
    # Decode any already-encoded path
    decoded_path = unquote(parsed_url.path)
    # Re-encode the path to ensure proper encoding
    sanitized_path = quote(decoded_path)
    return urlunparse((parsed_url.scheme, parsed_url.netloc, sanitized_path, parsed_url.params, parsed_url.query, parsed_url.fragment))


def fetch_calendar(url, retries, delay, timeout):
    """Fetch an iCal calendar from a URL with retries and timeout."""
    sanitized_url = sanitize_url(url)
    for attempt in range(retries):
        try:
            response = requests.get(sanitized_url, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.warning(f"Error fetching calendar from {sanitized_url} (Attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(delay)
    logger.error(f"Failed to fetch calendar from {sanitized_url} after {retries} attempts.")
    return None


def normalize_event_timezone(event):
    """Normalize time zones in VEVENT components."""
    for time_key in ['DTSTART', 'DTEND', 'RECURRENCE-ID']:
        if time_key in event:
            tzid = event[time_key].params.get('TZID')
            try:
                if tzid and tzid in all_timezones:
                    event[time_key].dt = event[time_key].dt.replace(tzinfo=timezone(tzid))
            except Exception as e:
                logger.warning(f"Error normalizing timezone for {time_key}: {e}")


def extract_timezones(calendar):
    """Extract and return VTIMEZONE components from a calendar."""
    timezones = []
    for component in calendar.walk():
        if component.name == "VTIMEZONE":
            timezones.append(component)
    return timezones

def add_timezones_to_calendar(target_calendar, timezones):
    """Add VTIMEZONE components to the target calendar."""
    for timezone in timezones:
        target_calendar.add_component(timezone)


def anonymize_event(event):
    """Anonymize event details to show only availability."""
    event['SUMMARY'] = "Busy"  # Replace with generic text
    if 'DESCRIPTION' in event:
        del event['DESCRIPTION']  # Remove description
    if 'LOCATION' in event:
        del event['LOCATION']  # Remove location
    if 'ATTENDEE' in event:
        del event['ATTENDEE']  # Remove attendee details
    if 'ORGANIZER' in event:
        del event['ORGANIZER']  # Remove organizer details


def merge_calendars(calendar_urls, retries, delay, timeout, show_details):
    """Merge multiple iCal calendars into one."""
    combined_calendar = icalendar.Calendar()
    combined_calendar.add('prodid', '-//ramhee98//iCalSyncHub//EN')
    combined_calendar.add('version', '2.0')

    for url in calendar_urls:
        calendar_data = fetch_calendar(url, retries, delay, timeout)
        if calendar_data:
            try:
                calendar = icalendar.Calendar.from_ical(calendar_data)
                timezones = extract_timezones(calendar)
                add_timezones_to_calendar(combined_calendar, timezones)
                for component in calendar.walk():
                    if component.name == "VEVENT":
                        if not show_details:
                            anonymize_event(component)
                        normalize_event_timezone(component)
                        combined_calendar.add_component(component)
            except ValueError as e:
                logger.error(f"Error parsing calendar from {url}: {e}")

    return combined_calendar


def save_calendar(calendar, output_path):
    """Save the merged calendar to a file."""
    # Serialize the calendar
    ical_output = calendar.to_ical().decode('utf-8')

    # Fix TZID quoting globally
    ical_output = ical_output.replace('TZID="', 'TZID=').replace('"', '')

    # Save the corrected data
    with open(output_path, 'w') as f:
        f.write(ical_output)


def sync_calendars(url_file_path, config, config_path, logger):
    """Sync calendars as per the configuration."""
    output_path = resolve_output_filename(config, config_path)
    sync_interval = int(config.get('settings', 'sync_interval'))
    retries = int(config.get('settings', 'retries', fallback=3))
    delay = int(config.get('settings', 'delay', fallback=5))
    timeout = int(config.get('settings', 'timeout', fallback=10))
    show_details = config.getboolean('settings', 'show_details', fallback=True)

    logger.info(f"Output file: {os.path.basename(output_path)}")
    logger.info(f"Output directory: {os.path.dirname(output_path)}")

    while True:
        logger.info(f"Starting sync at {datetime.now()}")
        calendar_urls = load_urls(url_file_path)
        if not calendar_urls:
            logger.error("No valid calendar URLs found.")
        else:
            merged_calendar = merge_calendars(calendar_urls, retries, delay, timeout, show_details)
            save_calendar(merged_calendar, output_path)
        logger.info("Sync complete.")

        if sync_interval == 0:
            logger.info("Sync interval is 0. Ending after one sync.")
            break

        logger.info(f"Next sync in {sync_interval} seconds.")
        time.sleep(sync_interval)


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    CONFIG_PATH = os.path.join(script_dir, 'config.ini')
    URL_FILE_PATH = os.path.join(script_dir, 'calendar_urls.txt')

    if not os.path.exists(CONFIG_PATH):
        print(f"Configuration file '{CONFIG_PATH}' not found.")
        print("Sync aborted, exiting!")
        exit(1)

    config = load_config(CONFIG_PATH)
    logger = setup_logging(config)
    sync_calendars(URL_FILE_PATH, config, CONFIG_PATH, logger)