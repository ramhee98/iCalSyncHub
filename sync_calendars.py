import os
import time
import requests
import icalendar
import configparser
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse, quote, unquote
import random
import re
import string
from pytz import UTC, all_timezones, timezone


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


def measure_time(log_level='DEBUG'):
    """
    Decorator factory to measure and log the execution time of a function.

    Args:
        log_level (str): Logging level for the message ('INFO' or 'DEBUG').
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            log_message = f"{func.__name__} took {elapsed_time:.3f} seconds."
            
            # Log with the specified level
            if log_level.upper() == 'INFO':
                logger.info(log_message)
            else:
                logger.debug(log_message)
            
            return result
        return wrapper
    return decorator


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


def get_anon_output_path(output_path):
    """Return the path for the anonymized companion ICS file."""
    base, ext = os.path.splitext(output_path)
    return f"{base}_anon{ext}"


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
    """Load valid calendar URLs and optional per-URL custom summaries from a file."""
    entries = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.rstrip('\n')
                if not line or line.strip().startswith('#'):
                    continue

                custom_summary = None
                url = line

                # If there's a fragment (allow optional space before '#'), treat the fragment as the custom summary
                if '#' in line:
                    base_url, fragment = line.split('#', 1)
                    base_url = base_url.strip()
                    fragment = fragment.strip()

                    # Treat whole fragment as the custom summary; empty fragment -> default 'Busy'
                    custom_summary = unquote(fragment) if fragment else 'Busy'

                    # Use the base URL (without the fragment) for fetching
                    url = base_url

                if custom_summary:
                    logger.debug(f"Loaded URL '{url}' with custom summary: '{custom_summary}'")
                entries.append((url, custom_summary))
        return entries
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


@measure_time(log_level='DEBUG')
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
    """Add VTIMEZONE components to the target calendar, skipping duplicates."""
    existing_tzids = set()
    for component in target_calendar.walk():
        if component.name == "VTIMEZONE":
            existing_tzids.add(str(component.get('TZID')))
    for tz in timezones:
        tzid = str(tz.get('TZID'))
        if tzid not in existing_tzids:
            target_calendar.add_component(tz)
            existing_tzids.add(tzid)


def get_availability_label(event):
    """Return 'Free' if the event is transparent (free), otherwise 'Busy'."""
    transp = str(event.get('TRANSP', 'OPAQUE')).upper()
    return 'Free' if transp == 'TRANSPARENT' else 'Busy'


def anonymize_event(event, summary="Busy"):
    """Anonymize event details to show only availability.

    Args:
        event: The VEVENT to anonymize
        summary: The text to use for the SUMMARY property when anonymized
    """
    if 'SUMMARY' in event:
        del event['SUMMARY']
    event.add('SUMMARY', summary)  # Replace with generic or custom text
    for prop in ('DESCRIPTION', 'LOCATION', 'ATTENDEE', 'ORGANIZER'):
        if prop in event:
            del event[prop]  # Remove sensitive details


def get_event_date(event):
    """Extract the start date from an event, handling various formats."""
    if 'DTSTART' not in event:
        return None
    
    dt = event['DTSTART'].dt
    
    # Handle date-only events (convert to datetime)
    if isinstance(dt, datetime):
        # If it's already a datetime, use it
        event_dt = dt
    else:
        # If it's a date, convert to datetime at midnight
        from datetime import date
        if isinstance(dt, date):
            event_dt = datetime.combine(dt, datetime.min.time())
        else:
            return None
    
    # Convert to UTC if it has timezone info, otherwise assume UTC
    if event_dt.tzinfo is None:
        event_dt = event_dt.replace(tzinfo=UTC)
    else:
        event_dt = event_dt.astimezone(UTC)
    
    return event_dt


def is_recurring_event(event):
    """Check if an event is recurring (has RRULE or RDATE)."""
    return 'RRULE' in event or 'RDATE' in event


def get_rrule_until(event):
    """Extract the UNTIL date from an RRULE, if present. Returns a UTC datetime or None."""
    if 'RRULE' not in event:
        return None
    rrule = event['RRULE']
    until_list = rrule.get('UNTIL')
    if not until_list:
        return None
    until = until_list[0] if isinstance(until_list, list) else until_list
    from datetime import date
    if isinstance(until, datetime):
        if until.tzinfo is None:
            return until.replace(tzinfo=UTC)
        return until.astimezone(UTC)
    elif isinstance(until, date):
        return datetime.combine(until, datetime.max.time()).replace(tzinfo=UTC)
    return None


def should_include_event(event, start_date, end_date):
    """
    Determine if an event should be included based on the date range.
    
    Args:
        event: The calendar event to check
        start_date: Earliest date to include (datetime with timezone)
        end_date: Latest date to include (datetime with timezone)
    
    Returns:
        bool: True if the event should be included, False otherwise
    """
    # Recurring events should always be included unless they have definitively ended
    if is_recurring_event(event):
        until = get_rrule_until(event)
        if until is not None and until < start_date:
            logger.debug("Recurring event excluded: RRULE UNTIL is before date range")
            return False
        logger.debug("Recurring event included")
        return True

    event_date = get_event_date(event)
    
    if event_date is None:
        # If we can't determine the date, include the event to be safe
        logger.debug("Event has no valid DTSTART, including by default")
        return True
    
    # Check if event is within the date range
    if start_date <= event_date <= end_date:
        return True
    
    # Check if DTEND exists and the event spans into our range
    if 'DTEND' in event:
        dt_end = event['DTEND'].dt
        if isinstance(dt_end, datetime):
            event_end = dt_end
        else:
            from datetime import date
            if isinstance(dt_end, date):
                event_end = datetime.combine(dt_end, datetime.max.time())
            else:
                return False
        
        if event_end.tzinfo is None:
            event_end = event_end.replace(tzinfo=UTC)
        else:
            event_end = event_end.astimezone(UTC)
        
        # Include if the event spans into our date range
        if event_date <= end_date and event_end >= start_date:
            return True
    
    return False


@measure_time(log_level='DEBUG')
def merge_calendars(calendar_entries, retries, delay, timeout, show_details, filter_by_date=False, past_days=14, future_months=2):
    """Merge multiple iCal calendars into one.

    Args:
        calendar_entries: Iterable of (url, custom_summary) tuples where custom_summary may be None.
    """
    combined_calendar = icalendar.Calendar()
    combined_calendar.add('prodid', '-//ramhee98//iCalSyncHub//EN')
    combined_calendar.add('version', '2.0')
    combined_calendar.add('calscale', 'GREGORIAN')
    combined_calendar.add('method', 'PUBLISH')

    # Calculate date range if filtering is enabled
    start_date = None
    end_date = None
    if filter_by_date:
        now = datetime.now(UTC)
        start_date = now - timedelta(days=past_days)
        end_date = now + timedelta(days=future_months * 30)  # Approximate months as 30 days
        logger.info(f"Filtering events: from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    total_events = 0
    filtered_events = 0

    for url, custom_summary in calendar_entries:
        calendar_data = fetch_calendar(url, retries, delay, timeout)
        if calendar_data:
            try:
                calendar = icalendar.Calendar.from_ical(calendar_data)
                timezones = extract_timezones(calendar)
                add_timezones_to_calendar(combined_calendar, timezones)
                for component in calendar.walk():
                    if component.name == "VEVENT":
                        total_events += 1
                        
                        # Apply date filtering if enabled
                        if filter_by_date and not should_include_event(component, start_date, end_date):
                            filtered_events += 1
                            continue
                        
                        label = f" [{custom_summary}]" if custom_summary else ""
                        if not show_details:
                            status = get_availability_label(component)
                            anonymize_event(component, f"{status}{label}")
                        elif label:
                            existing = str(component.get('SUMMARY', ''))
                            if 'SUMMARY' in component:
                                del component['SUMMARY']
                            component.add('SUMMARY', f"{existing}{label}")
                        normalize_event_timezone(component)
                        combined_calendar.add_component(component)
            except ValueError as e:
                logger.error(f"Error parsing calendar from {url}: {e}")

    if filter_by_date:
        logger.info(f"Processed {total_events} events, filtered out {filtered_events}, kept {total_events - filtered_events}")

    return combined_calendar


@measure_time(log_level='DEBUG')
def save_calendar(calendar, output_path):
    """Save the merged calendar to a file."""
    # Serialize the calendar
    ical_output = calendar.to_ical().decode('utf-8')

    # Unfold continuation lines (CRLF + space/tab) so we can process full logical lines
    ical_output = re.sub(r'\r?\n[ \t]', '', ical_output)

    # Fix TZID quoting (only remove quotes around TZID values, not all quotes)
    ical_output = re.sub(r'TZID="([^"]*)"', r'TZID=\1', ical_output)

    # Split comma-separated EXDATE values into separate lines (Outlook compatibility)
    def split_exdates(match):
        prefix = match.group(1)  # e.g. "EXDATE;TZID=Europe/Zurich:"
        dates = match.group(2).split(',')
        return '\r\n'.join(f'{prefix}{d}' for d in dates)

    ical_output = re.sub(
        r'(EXDATE[^:]*:)([^\r\n]*,[^\r\n]*)',
        split_exdates,
        ical_output
    )

    # Re-fold lines longer than 75 octets per RFC 5545
    lines = ical_output.splitlines()
    folded_lines = []
    for line in lines:
        encoded = line.encode('utf-8')
        if len(encoded) <= 75:
            folded_lines.append(line)
        else:
            # First chunk is 75 octets, continuation chunks are 74 (plus leading space)
            first = encoded[:75].decode('utf-8', errors='ignore')
            folded_lines.append(first)
            remaining = encoded[75:]
            while remaining:
                chunk = remaining[:74].decode('utf-8', errors='ignore')
                folded_lines.append(' ' + chunk)
                remaining = remaining[74:]

    ical_output = '\r\n'.join(folded_lines) + '\r\n'

    # Save the corrected data
    with open(output_path, 'w') as f:
        f.write(ical_output)


@measure_time(log_level='DEBUG')
def validate_calendar(file_path):
    try:
        with open(file_path, 'r') as f:
            icalendar.Calendar.from_ical(f.read())
        logger.debug("Exported ICS file is valid.")
    except Exception as e:
        logger.error(f"Validation of exported ICS file failed: {e}")


def sync_calendars(url_file_path, config, config_path, logger):
    """Sync calendars as per the configuration."""
    output_path = resolve_output_filename(config, config_path)
    sync_interval = int(config.get('settings', 'sync_interval'))
    retries = int(config.get('settings', 'retries', fallback=3))
    delay = int(config.get('settings', 'delay', fallback=5))
    timeout = int(config.get('settings', 'timeout', fallback=10))
    show_details = config.getboolean('settings', 'show_details', fallback=True)
    filter_by_date = config.getboolean('settings', 'filter_by_date', fallback=False)
    past_days = int(config.get('settings', 'past_days', fallback=14))
    future_months = int(config.get('settings', 'future_months', fallback=2))

    logger.info(f"Output file: {os.path.basename(output_path)}")
    logger.info(f"Output directory: {os.path.dirname(output_path)}")
    
    if filter_by_date:
        logger.info(f"Date filtering enabled: past {past_days} days, future {future_months} months")

    def remove_expired_symlinks():
        tokens_file = os.path.join(os.path.dirname(__file__), 'user_tokens.txt')
        if not os.path.exists(tokens_file):
            return
        with open(tokens_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(':', 2)
                if len(parts) == 2:
                    username, token = parts
                    expiration = ''
                elif len(parts) == 3:
                    username, token, expiration = parts
                else:
                    continue
                if expiration:
                    try:
                        exp_dt = datetime.fromisoformat(expiration)
                        if datetime.now() > exp_dt:
                            link_name = os.path.join(os.path.dirname(output_path), f"{token}.ics")
                            if os.path.islink(link_name) or os.path.exists(link_name):
                                os.remove(link_name)
                                logger.info(f"Removed expired token symlink: {link_name}")
                    except Exception:
                        continue

    while True:
        remove_expired_symlinks()
        logger.info(f"Starting sync at {datetime.now()}")
        start_time = time.time()
        calendar_urls = load_urls(url_file_path)
        if not calendar_urls:
            logger.error("No valid calendar URLs found.")
        else:
            merged_calendar = merge_calendars(calendar_urls, retries, delay, timeout, show_details,
                                             filter_by_date, past_days, future_months)
            save_calendar(merged_calendar, output_path)
            validate_calendar(output_path)
            # When details are enabled, also generate an anonymized companion file
            # so per-user access can be controlled without detail exposure.
            if show_details:
                anon_path = get_anon_output_path(output_path)
                anon_calendar = merge_calendars(calendar_urls, retries, delay, timeout, False,
                                               filter_by_date, past_days, future_months)
                save_calendar(anon_calendar, anon_path)
                validate_calendar(anon_path)
                logger.info(f"Anonymized companion ICS saved: {os.path.basename(anon_path)}")
        logger.info(f"Sync completed in {round(time.time() - start_time, 3)} seconds.")

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