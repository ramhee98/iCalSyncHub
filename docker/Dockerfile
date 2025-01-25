# Use Python base image
FROM python:3.9-slim

# Set working directory inside the container
WORKDIR /app/src

# Copy the source code into the container
COPY src/ /app/src

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# Run the Python application
CMD ["python", "sync_calendars.py"]
