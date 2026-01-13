# iCalSyncHub

iCalSyncHub is a lightweight Python program that synchronizes multiple online iCal calendars into a single merged calendar. The merged calendar is then shared as an iCal file, which can be hosted on a web server or used locally. Designed for simplicity and automation, it periodically updates the merged calendar based on a configurable sync interval.

## Features
- **Multi-Calendar Support**: Combine events from two or more iCal calendars into one.
- **Automatic Syncing**: Automatically updates the merged calendar at a specified interval.
- **Date Range Filtering**: Optionally filter events to keep only a configurable time window (e.g., past 14 days and next 2 months).
- **Custom Configuration**: Use a simple `.ini` file to configure calendar URLs, output location, and sync frequency.
- **Portable Output**: Generates a standard `.ics` file compatible with popular calendar apps like Google Calendar, Outlook, and Apple Calendar.
- **Error Handling**: Resilient to network errors or invalid calendar formats.

## Installation


### Quick Installation

Run the provided installer script to set up a Python virtual environment and install all dependencies (including Streamlit):

```bash
bash install.sh
```

This will create a `venv` directory and install all required packages. To activate the environment later, use:

```bash
source venv/bin/activate
```

---

#### Manual Prerequisites (if not using install.sh)
- Python 3.6 or higher
- Required Python libraries:
  - `requests`
  - `icalendar`
  - `pytz`
  - `streamlit`

Install the dependencies manually using pip if needed:

```bash
pip install requests icalendar pytz streamlit
```


## Usage

### 1. Clone the repository:

```bash
git clone https://github.com/ramhee98/iCalSyncHub.git
cd iCalSyncHub
```

### 2. Configure the app:

Copy the config template and edit as needed:

```bash
cp config_template.ini config.ini
nano config.ini
```

### 3. Add calendar URLs:

Create a `calendar_urls.txt` file in the project directory, listing the calendar URLs to sync:

```bash
https://example.com/calendar1.ics
https://example.com/calendar2.ics
```

### 4. Run the calendar sync:

```bash
python sync_calendars.py
```

The program will fetch the specified calendars, merge their events, and save the result as an iCal file at the configured location. It will then periodically sync the calendars based on the specified interval.

### 5. Manage user tokens and sharing (Streamlit app):

You can manage user tokens and generate shareable calendar links using the included Streamlit app:

```bash
source venv/bin/activate  # if using a virtual environment
streamlit run streamlit_app.py
```

By default, the Streamlit app will be available at [http://localhost:8501](http://localhost:8501) (or `http://<your-server-ip>:8501` for remote access). You can change the port with `--server.port <port>` if needed.

#### Features of the Streamlit app:
- Add/remove users, each with a unique token.
- For each token, a public .ics link is generated (e.g., `https://yourdomain.com/<token>.ics`).
- The app automatically creates a symlink for each token in the output directory (e.g., `/var/www/html/<token>.ics`), pointing to the merged calendar file. This makes each link immediately accessible and shareable.
- The original merged calendar file link is also shown for reference.

**Note:**
- Removing a user/token will also remove the corresponding symlink.
- All token-based .ics links point to the same merged calendar file unless you implement per-user customization.

#### Security Considerations:
- The Streamlit app does not require authentication by default. Anyone with access can manage tokens. Protect access as needed.
- Tokens do not expire automatically. Remove tokens to revoke access.

---

### Configuration Options

The `config.ini` file contains the following settings:

- **`output_path`**: Path where the merged calendar file will be saved.
- **`filename`**: Optional. Predefined filename for the output calendar. If not set, a random filename will be generated.
- **`sync_interval`**: Time interval (in seconds) between calendar syncs, if set to 0 it will only sync once.
- **`retries`**: Number of retry attempts if fetching a calendar fails.
- **`delay`**: Time in seconds to wait between retry attempts.
- **`timeout`**: Maximum time in seconds to wait for a response from a calendar URL.
- **`show_details`**: Boolean. Set to `true` to include event details (summary, description, location, etc.) in the merged calendar. Set to `false` to anonymize events and show only availability (e.g., "Busy").
- **`filter_by_date`**: Boolean. Set to `true` to enable date range filtering for events. When enabled, only events within the specified time window will be included in the merged calendar. Default is `false`.
- **`past_days`**: Number of days in the past to include when `filter_by_date` is enabled. For example, `14` includes events from the past 14 days. Default is `14`.
- **`future_months`**: Number of months in the future to include when `filter_by_date` is enabled. For example, `2` includes events up to 2 months ahead (approximately 60 days). Default is `2`.
- **`log_output`**: Specify where logs should be sent. Options are:
  - `console`: Logs are displayed only on the console.
  - `file`: Logs are saved only to the specified file.
  - `both`: Logs are sent to both the console and the file (default).
  - `none`: Disable logging entirely.
- **`log_level`**: Logging level to control the verbosity of the output. Options are `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`. Default is `INFO`.
- **`log_file`**: File path for the log output. Default is `icalsynchub.log`. Logs will be rotated if a file path is provided.
- **`max_log_file_size`**: Maximum size of a single log file in MB before rotation. Default in MB is `10`.
- **`log_backup_count`**: Number of backup log files to keep after rotation. Default is `5`.


### Example Configuration File (`config.ini`)

```ini
[settings]
output_path = /var/www/html/
filename = mycal.ics
sync_interval = 300
retries = 3
delay = 5
timeout = 10
show_details = true
filter_by_date = false
past_days = 14
future_months = 2
log_output = both
log_level = INFO
log_file = icalsynchub.log
max_log_file_size = 10
log_backup_count = 5
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! If you find a bug or have an idea for improvement, feel free to open an issue or submit a pull request.

## Acknowledgments

- Built using the [icalendar](https://icalendar.readthedocs.io/en/latest/) library.
- Inspired by the need for seamless calendar management.