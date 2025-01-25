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

# Use the virtual environment's Python as the default Python
ENV PATH="/venv/bin:$PATH"

# Run the Python application
CMD ["python", "sync_calendars.py"]
