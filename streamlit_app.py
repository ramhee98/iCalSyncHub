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

def load_tokens():
    if not os.path.exists(TOKENS_FILE):
        return []
    with open(TOKENS_FILE, "r") as f:
        # Each line: username:token
        pairs = []
        for line in f:
            line = line.strip()
            if line and ':' in line:
                username, token = line.split(':', 1)
                pairs.append((username, token))
        return pairs

def save_tokens(pairs):
    with open(TOKENS_FILE, "w") as f:
        for username, token in pairs:
            f.write(f"{username}:{token}\n")

def add_token(username):
    pairs = load_tokens()
    if not username:
        return False, "Username cannot be empty."
    # Prevent duplicate usernames
    if any(u == username for u, _ in pairs):
        return False, f"Username '{username}' already exists."
    token = generate_token()
    pairs.append((username, token))
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
    new_pairs = [(u, t) for u, t in pairs if u != username]
    if len(new_pairs) == len(pairs):
        return False
    save_tokens(new_pairs)
    return True

st.title("User Token Management for iCalSyncHub")
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

# Add token
with st.form("add_token_form"):
    username = st.text_input("Enter username:")
    submitted = st.form_submit_button("Add User & Generate Token")
    if submitted:
        success, result = add_token(username.strip())
        if success:
            st.success(f"Token generated for '{username}': {result}")
        else:
            st.error(result)

# List and remove tokens
pairs = load_tokens()
if pairs:
    st.write("## Current Users and Shareable Calendar URLs:")
    merged_url = get_merged_calendar_url()
    for username, token in pairs:
        col1, col2, col3 = st.columns([3,6,1])
        col1.write(f"**{username}**")
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
else:
    st.info("No users/tokens found.")
