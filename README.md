# iCalSyncHub

iCalSyncHub is a lightweight Python program that synchronizes multiple online iCal calendars into a single merged calendar. The merged calendar is then shared as an iCal file, which can be hosted on a web server or used locally. Designed for simplicity and automation, it periodically updates the merged calendar based on a configurable sync interval.

## Features
- **Multi-Calendar Support**: Combine events from two or more iCal calendars into one.
- **Automatic Syncing**: Automatically updates the merged calendar at a specified interval.
- **Custom Configuration**: Use a simple `.ini` file to configure calendar URLs, output location, and sync frequency.
- **Portable Output**: Generates a standard `.ics` file compatible with popular calendar apps like Google Calendar, Outlook, and Apple Calendar.
- **Error Handling**: Resilient to network errors or invalid calendar formats.

## Installation

### Prerequisites
- Python 3.6 or higher
- Required Python libraries:
  - `requests`
  - `icalendar`
  - `pytz`

Install the dependencies using pip:

```bash
pip install requests icalendar pytz
```

## Usage

1. Clone the repository:

```bash
git clone https://github.com/ramhee98/iCalSyncHub.git
cd iCalSyncHub
```

2. Copy the config_template.ini file and customize it according to your requirements:

```bash
cp config_template.ini config.ini
nano config.ini
```

3. Create a calendar_urls.txt file in the project directory, listing the calendar URLs to sync:

```bash
https://example.com/calendar1.ics
https://example.com/calendar2.ics
```

4. Run the program:

```bash
python sync_calendars.py
```

The program will fetch the specified calendars, merge their events, and save the result as an iCal file at the configured location. It will then periodically sync the calendars based on the specified interval.

### Configuration Options

The `config.ini` file contains the following settings:

- **`output_path`**: Path where the merged calendar file will be saved.
- **`filename`**: Optional. Predefined filename for the output calendar. If not set, a random filename will be generated.
- **`sync_interval`**: Time interval (in seconds) between calendar syncs, if set to 0 it will only sync once.
- **`retries`**: Number of retry attempts if fetching a calendar fails.
- **`delay`**: Time in seconds to wait between retry attempts.
- **`timeout`**: Maximum time in seconds to wait for a response from a calendar URL.
- **`show_details`**: Boolean. Set to `true` to include event details (summary, description, location, etc.) in the merged calendar. Set to `false` to anonymize events and show only availability (e.g., "Busy").

### Example Configuration File (`config.ini`)

```ini
[settings]
output_path = /var/www/html/
filename = mycal.ics
sync_interval = 300
retries = 3
delay = 5
timeout = 10
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! If you find a bug or have an idea for improvement, feel free to open an issue or submit a pull request.

## Acknowledgments

- Built using the [icalendar](https://icalendar.readthedocs.io/en/latest/) library.
- Inspired by the need for seamless calendar management.
