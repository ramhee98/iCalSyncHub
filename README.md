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

Install the dependencies using pip:

```bash
pip install requests icalendar
```

## Usage

1. Clone the repository:

```bash
git clone https://github.com/yourusername/iCalSyncHub.git
cd iCalSyncHub
```

2. Create a configuration file named `calendar_sync_config.ini` in the project directory with the following format:

```ini
[settings]
calendar_urls=https://example.com/calendar1.ics,https://example.com/calendar2.ics
output_path=/path/to/output/merged_calendar.ics
sync_interval=3600
```

- **`calendar_urls`**: Comma-separated URLs of the iCal calendars to sync.
- **`output_path`**: Path where the merged calendar file will be saved.
- **`sync_interval`**: Time interval (in seconds) between calendar syncs.

3. Run the program:

```bash
python sync_calendars.py
```

The program will fetch the specified calendars, merge their events, and save the result as an iCal file at the configured location. It will then periodically sync the calendars based on the specified interval.

## Example Configuration

```ini
[settings]
calendar_urls=https://example.com/work_calendar.ics,https://example.com/personal_calendar.ics
output_path=/var/www/html/merged_calendar.ics
sync_interval=3600
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! If you find a bug or have an idea for improvement, feel free to open an issue or submit a pull request.

## Acknowledgments

- Built using the [icalendar](https://icalendar.readthedocs.io/en/latest/) library.
- Inspired by the need for seamless calendar management.
