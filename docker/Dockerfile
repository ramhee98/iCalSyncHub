# Use Python base image
FROM python:3.9-slim

# Set working directory inside the container
WORKDIR /app/src

# Copy the source code into the container
COPY src/ /app/src
COPY requirements.txt /app/

# Create a virtual environment and install dependencies
RUN python3 -m venv /venv && \
    /venv/bin/pip install --no-cache-dir -r /app/requirements.txt

# Ensure config.ini is created if it doesn't exist and populate with default values
RUN touch /app/src/config.ini && \
    echo "[settings]" > /app/src/config.ini && \
    echo "# Directory where the merged calendar file will be saved" >> /app/src/config.ini && \
    echo "# Example: /var/www/html/" >> /app/src/config.ini && \
    echo "output_path = /app/webserver/" >> /app/src/config.ini && \
    echo "" >> /app/src/config.ini && \
    echo "# Filename for the merged calendar" >> /app/src/config.ini && \
    echo "# If left blank, a randomized filename will be generated" >> /app/src/config.ini && \
    echo "# Example: calendar.ics" >> /app/src/config.ini && \
    echo "filename = calendar.ics" >> /app/src/config.ini && \
    echo "" >> /app/src/config.ini && \
    echo "# Interval between synchronizations in seconds" >> /app/src/config.ini && \
    echo "# Example: 3600 (1 hour)" >> /app/src/config.ini && \
    echo "# Example: 0 (only sync once, useful for crontab)" >> /app/src/config.ini && \
    echo "sync_interval = 3600" >> /app/src/config.ini && \
    echo "" >> /app/src/config.ini && \
    echo "# Number of retries for fetching a calendar" >> /app/src/config.ini && \
    echo "retries = 3" >> /app/src/config.ini && \
    echo "" >> /app/src/config.ini && \
    echo "# Delay in seconds between retries" >> /app/src/config.ini && \
    echo "delay = 5" >> /app/src/config.ini && \
    echo "" >> /app/src/config.ini && \
    echo "# Timeout in seconds for HTTP requests" >> /app/src/config.ini && \
    echo "timeout = 10" >> /app/src/config.ini && \
    echo "" >> /app/src/config.ini && \
    echo "# Set to true to show event details; false to show only availability" >> /app/src/config.ini && \
    echo "show_details = true" >> /app/src/config.ini && \
    echo "" >> /app/src/config.ini && \
    echo "# Logging output destination: console, file, both, or none" >> /app/src/config.ini && \
    echo "log_output = both" >> /app/src/config.ini && \
    echo "" >> /app/src/config.ini && \
    echo "# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)" >> /app/src/config.ini && \
    echo "log_level = INFO" >> /app/src/config.ini && \
    echo "" >> /app/src/config.ini && \
    echo "# Logging output file" >> /app/src/config.ini && \
    echo "log_file = icalsynchub.log" >> /app/src/config.ini && \
    echo "" >> /app/src/config.ini && \
    echo "# Maximum size of a single log file in MB before rotation (used only if log_file is set)" >> /app/src/config.ini && \
    echo "max_log_file_size = 10" >> /app/src/config.ini && \
    echo "" >> /app/src/config.ini && \
    echo "# Number of backup log files to keep" >> /app/src/config.ini && \
    echo "log_backup_count = 5" >> /app/src/config.ini

# Ensure calendar_urls.txt is created if it doesn't exist and populate with default values
RUN touch /app/src/calendar_urls.txt && \
    echo "# Default calendar URLs" > /app/src/calendar_urls.txt && \
    echo "https://example.com/calendar1.ics" >> /app/src/calendar_urls.txt && \
    echo "https://example.com/calendar2.ics" >> /app/src/calendar_urls.txt

# Use the virtual environment's Python as the default Python
ENV PATH="/venv/bin:$PATH"

# Run the Python application
CMD ["python", "sync_calendars.py"]
