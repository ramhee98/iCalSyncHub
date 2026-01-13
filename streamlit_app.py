import streamlit as st
import os
import random
import string
import configparser

TOKENS_FILE = "user_tokens.txt"
CONFIG_FILE = "config.ini"

def get_domain():
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        return ""
    config.read(CONFIG_FILE)
    return config.get('settings', 'domain', fallback="").rstrip('/')

def generate_token(length=64):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

from datetime import datetime, timedelta

def load_tokens():
    if not os.path.exists(TOKENS_FILE):
        return []
    with open(TOKENS_FILE, "r") as f:
        # Each line: username:token:expiration (expiration is ISO format or empty for no expiration)
        pairs = []
        raw_lines = f.readlines()
        for line in raw_lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split(":")
            if len(parts) == 2:
                username, token = parts
                expiration = ""
            elif len(parts) == 3:
                username, token, expiration = parts
            else:
                # If more than 3 parts, join everything after the second as expiration
                username, token = parts[:2]
                expiration = ":".join(parts[2:])
            pairs.append((username, token, expiration))
        return pairs

def save_tokens(pairs):
    with open(TOKENS_FILE, "w") as f:
        for username, token, expiration in pairs:
            f.write(f"{username}:{token}:{expiration}\n")

def add_token(username, expiration=None):
    pairs = load_tokens()
    if not username:
        return False, "Username cannot be empty."
    # Prevent duplicate usernames
    if any(u == username for u, _, _ in pairs):
        return False, f"Username '{username}' already exists."
    token = generate_token()
    expiration_str = expiration if expiration else ""
    pairs.append((username, token, expiration_str))
    save_tokens(pairs)
    # Create symlink for the token in output_path
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    output_path = config.get('settings', 'output_path', fallback='/var/www/html/').rstrip('/')
    filename = config.get('settings', 'filename', fallback='').lstrip('/')
    if output_path and filename:
        target = os.path.join(output_path, filename)
        link_name = os.path.join(output_path, f"{token}.ics")
        try:
            if os.path.islink(link_name) or os.path.exists(link_name):
                os.remove(link_name)
            os.symlink(target, link_name)
        except Exception as e:
            return False, f"Token created, but failed to create symlink: {e}"
    return True, token

def remove_token(username):
    pairs = load_tokens()
    removed_token = None
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    output_path = config.get('settings', 'output_path', fallback='/var/www/html/').rstrip('/')
    # Find the token to remove
    for u, t, e in pairs:
        if u == username:
            removed_token = t
            break
    new_pairs = [(u, t, e) for u, t, e in pairs if u != username]
    if len(new_pairs) == len(pairs):
        return False
    save_tokens(new_pairs)
    # Remove symlink if it exists
    if removed_token and output_path:
        link_name = os.path.join(output_path, f"{removed_token}.ics")
        try:
            if os.path.islink(link_name) or os.path.exists(link_name):
                os.remove(link_name)
        except Exception:
            pass
    return True


st.set_page_config(
    page_title="iCalSyncHub Token Management",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="auto",
)
st.title("iCalSyncHub Token Management")
st.write("Add or remove user tokens to control calendar sharing. Each token is associated with a username.")

domain = get_domain()
def get_merged_calendar_url():
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        return None
    config.read(CONFIG_FILE)
    domain = config.get('settings', 'domain', fallback="").rstrip('/')
    filename = config.get('settings', 'filename', fallback="").lstrip('/')
    if domain and filename:
        return f"{domain}/{filename}"
    return None

if not domain:
    st.warning("Domain is not set in config.ini. Please set the 'domain' value under [settings].")

# Add token with expiration
with st.form("add_token_form"):
    username = st.text_input("Enter username:")
    set_exp = st.checkbox("Set expiration date/time")
    default_date = (datetime.now() + timedelta(days=30)).date()
    exp_date = st.date_input("Expiration date", value=default_date)
    exp_time = st.time_input("Expiration time", value=datetime.now().time().replace(second=0, microsecond=0))
    expiration_str = ""
    if set_exp:
        exp_dt = datetime.combine(exp_date, exp_time)
        expiration_str = exp_dt.isoformat()
    submitted = st.form_submit_button("Add User & Generate Token")
    if submitted:
        success, result = add_token(username.strip(), expiration=expiration_str)
        if success:
            st.success(f"Token generated for '{username}': {result}")
            st.rerun()
        else:
            st.error(result)

# List and remove tokens, filter out expired

def token_expiry_status(expiration):
    """
    Returns: 'expired', 'today', 'week', or 'active'
    """
    if not expiration:
        return 'active'
    try:
        exp_dt = datetime.fromisoformat(expiration)
        now = datetime.now()
        if now > exp_dt:
            return 'expired'
        elif exp_dt.date() == now.date():
            return 'today'
        elif 0 < (exp_dt.date() - now.date()).days <= 7:
            return 'week'
        else:
            return 'active'
    except Exception:
        return 'active'

pairs = load_tokens()
if pairs:
    st.write("## Current Users and Shareable Calendar URLs:")
    merged_url = get_merged_calendar_url()
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    output_path = config.get('settings', 'output_path', fallback='/var/www/html/').rstrip('/')
    for idx, (username, token, expiration) in enumerate(pairs):
        status = token_expiry_status(expiration)
        # Remove symlink for expired tokens
        if status == 'expired' and output_path:
            link_name = os.path.join(output_path, f"{token}.ics")
            try:
                if os.path.islink(link_name) or os.path.exists(link_name):
                    os.remove(link_name)
            except Exception:
                pass
        col1, col2, col3 = st.columns([3,6,1])
        if status == 'expired':
            col1.write(f"**{username}** :red[EXPIRED]")
        elif status == 'today':
            col1.write(f"**{username}** :orange[EXPIRES TODAY]")
        elif status == 'week':
            col1.write(f"**{username}** :yellow[EXPIRES SOON]")
        else:
            col1.write(f"**{username}**")
        if expiration:
            col1.caption(f"Expires: {expiration}")
        else:
            col1.caption("No expiration")
        if domain:
            url = f"{domain}/{token}.ics"
            col2.code(url)
            if merged_url:
                col2.markdown(f"[Original merged calendar file]({merged_url})")
        else:
            col2.code(token)
        if col3.button(f"Remove", key=f"remove_{username}"):
            removed = remove_token(username)
            if removed:
                st.warning(f"User '{username}' removed.")
                st.rerun()
        # Add a visual separator between entries, except after the last one
        if idx < len(pairs) - 1:
            st.divider()
else:
    st.info("No users/tokens found.")
