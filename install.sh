#!/bin/bash
# iCalSyncHub installer script
# Installs Python dependencies and Streamlit for the project

set -e

# Optionally create and activate a virtual environment
echo "Creating Python virtual environment in ./.venv..."
python3 -m venv .venv
source .venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing required Python packages..."
pip install requests icalendar pytz streamlit

# Create config.ini from template if missing
if [ ! -f config.ini ]; then
  if [ -f config_template.ini ]; then
    cp config_template.ini config.ini
    echo "Created config.ini from config_template.ini"
  else
    echo "Warning: config_template.ini not found; skipping config creation."
  fi
else
  echo "config.ini already exists; not overwriting."
fi

echo "Installation complete."
echo "To activate the virtual environment, run: source .venv/bin/activate"
echo "To start the Streamlit app, run: streamlit run streamlit_app.py"
