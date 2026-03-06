import streamlit as st
import streamlit.components.v1 as components
import os
import shutil
import random
import string
import configparser
import logging
from logging.handlers import RotatingFileHandler
import json

def get_anon_output_path(output_path):
    """Return the path for the anonymized companion ICS file (mirrors sync_calendars.py)."""
    base, ext = os.path.splitext(output_path)
    return f"{base}_anon{ext}"


def render_share_button(username, ics_url, html_url):
    """Render a 'View online' link and a native share button side by side.
    Falls back to an inline share menu on non-HTTPS contexts (e.g. local dev)."""
    # Escape single quotes in values used inside JS string literals
    safe_username = username.replace("'", "\\'")
    safe_html_url = html_url.replace("'", "\\'")
    safe_ics_url = ics_url.replace("'", "\\'")
    share_html = f"""
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{ background: transparent; font-family: "Source Sans Pro", sans-serif; }}
      #row {{
        display: flex;
        align-items: center;
        gap: 0.6rem;
      }}
      #viewLink {{
        font-size: 0.875rem;
        color: rgb(49,51,63);
        text-decoration: underline;
        white-space: nowrap;
      }}
      #viewLink:hover {{ color: rgb(255,75,75); }}
      #shareBtn {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.2rem 0.6rem;
        background-color: transparent;
        color: rgb(49,51,63);
        border: 1px solid rgba(49,51,63,0.25);
        border-radius: 0.5rem;
        font-family: inherit;
        font-size: 0.875rem;
        font-weight: 400;
        cursor: pointer;
        user-select: none;
        white-space: nowrap;
        transition: color 0.1s, border-color 0.1s;
      }}
      #shareBtn:hover {{ color: rgb(255,75,75); border-color: rgb(255,75,75); }}
      #menu {{
        display: none;
        margin-top: 6px;
        border: 1px solid rgba(49,51,63,0.15);
        border-radius: 0.5rem;
        overflow: hidden;
        background: #fff;
        box-shadow: 0 2px 8px rgba(0,0,0,0.12);
      }}
      #menu a, #menu button {{
        display: flex;
        align-items: center;
        gap: 8px;
        width: 100%;
        padding: 0.5rem 0.75rem;
        font-size: 0.875rem;
        color: rgb(49,51,63);
        background: none;
        border: none;
        border-radius: 0;
        text-decoration: none;
        cursor: pointer;
        font-family: inherit;
        min-height: unset;
      }}
      #menu a:hover, #menu button:hover {{ background: rgba(49,51,63,0.06); }}
      #menu .divider {{ height: 1px; background: rgba(49,51,63,0.1); margin: 0; }}

      @media (prefers-color-scheme: dark) {{
        #viewLink {{ color: rgb(200,210,230); }}
        #viewLink:hover {{ color: rgb(255,100,100); }}
        #shareBtn {{ color: rgb(200,210,230); border-color: rgba(200,210,230,0.3); }}
        #shareBtn:hover {{ color: rgb(255,100,100); border-color: rgb(255,100,100); }}
        #menu {{ background: #1e2130; border-color: rgba(200,210,230,0.15); box-shadow: 0 2px 10px rgba(0,0,0,0.4); }}
        #menu a, #menu button {{ color: rgb(200,210,230); }}
        #menu a:hover, #menu button:hover {{ background: rgba(255,255,255,0.07); }}
        #menu .divider {{ background: rgba(200,210,230,0.12); }}
      }}
    </style>

    <div id='row'>
      <a id='viewLink' href='{safe_html_url}' target='_blank'>View online</a>
      <button id='shareBtn' onclick='toggleMenu()'>Share</button>
    </div>
    <div id='menu'>
      <a id='waLink' href='#' target='_blank'>💬 WhatsApp</a>
      <a id='tgLink' href='#' target='_blank'>✈️ Telegram</a>
      <a id='mailLink' href='#' target='_blank'>📧 Email</a>
      <div class='divider'></div>
      <button onclick='copyLink()'>📋 Copy link</button>
    </div>

    <script>
      var ics  = '{safe_ics_url}';
      var html = '{safe_html_url}';
      var name = '{safe_username}';
      var msg  = 'View my calendar: ' + html + '\\n\\nSubscribe ICS (do not download): ' + ics;

      document.getElementById('waLink').href   = 'https://wa.me/?text=' + encodeURIComponent(msg);
      document.getElementById('tgLink').href   = 'https://t.me/share/url?url=' + encodeURIComponent(html) + '&text=' + encodeURIComponent('Subscribe ICS (do not download): ' + ics);
      document.getElementById('mailLink').href = 'mailto:?subject=' + encodeURIComponent(name + ' Calendar') + '&body=' + encodeURIComponent(msg);

      function toggleMenu() {{
        if (navigator.share) {{
          navigator.share({{ title: name + ' Calendar', text: msg }}).catch(function(){{}});
          return;
        }}
        var m = document.getElementById('menu');
        m.style.display = m.style.display === 'block' ? 'none' : 'block';
      }}

      function copyLink() {{
        document.getElementById('menu').style.display = 'none';
        var btn = document.getElementById('shareBtn');
        function done() {{ btn.textContent = '✅ Copied!'; setTimeout(function(){{ btn.textContent = '🔗 Share'; }}, 2000); }}
        if (navigator.clipboard && window.isSecureContext) {{
          navigator.clipboard.writeText(html).then(done).catch(legacy);
        }} else {{ legacy(); }}
        function legacy() {{
          var ta = document.createElement('textarea');
          ta.value = html; ta.style.position='fixed'; ta.style.opacity='0';
          document.body.appendChild(ta); ta.focus(); ta.select();
          if (document.execCommand('copy')) done();
          else prompt('Copy link:', html);
          document.body.removeChild(ta);
        }}
      }}

      // Close menu when clicking outside
      document.addEventListener('click', function(e) {{
        if (!e.target.closest || (!e.target.closest('#shareBtn') && !e.target.closest('#menu'))) {{
          document.getElementById('menu').style.display = 'none';
        }}
      }});
    </script>
    """
    components.html(share_html, height=200)

def _write_viewer_html_with_map(template_path, dest_path, color_map):
    """Write a copy of the viewer template to dest_path, injecting a JS color map if provided.

    The template must contain the placeholder comment: <!--INJECT_EVENT_COLOR_MAP-->
    """
    try:
        with open(template_path, 'r') as f:
            content = f.read()
        inject = ''
        if color_map:
            js = json.dumps(color_map)
            inject = f"<script>window.EVENT_COLOR_MAP = {js};</script>"
        if '<!--INJECT_EVENT_COLOR_MAP-->' in content:
            content = content.replace('<!--INJECT_EVENT_COLOR_MAP-->', inject)
        else:
            content = content.replace('</body>', f"{inject}</body>")
        with open(dest_path, 'w') as f:
            f.write(content)
    except Exception:
        shutil.copyfile(template_path, dest_path)

def get_logger():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    log_level = config.get('settings', 'log_level', fallback='INFO').upper()
    log_output = config.get('settings', 'log_output', fallback='both').lower()
    log_file = config.get('settings', 'log_file', fallback='icalsynchub.log')
    max_log_file_size = int(config.get('settings', 'max_log_file_size', fallback=10)) * 1024 * 1024
    log_backup_count = int(config.get('settings', 'log_backup_count', fallback=5))
    logger = logging.getLogger('icalsynchub.tokens')
    logger.setLevel(getattr(logging, log_level))
    # Avoid duplicate handlers
    if not logger.handlers:
        handlers = []
        if log_output in ('file', 'both') and log_file:
            file_handler = RotatingFileHandler(log_file, maxBytes=max_log_file_size, backupCount=log_backup_count)
            file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            handlers.append(file_handler)
        if log_output in ('console', 'both'):
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(console_formatter)
            handlers.append(console_handler)
        for handler in handlers:
            logger.addHandler(handler)
    logger.propagate = False
    return logger

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
        # Each line: username:token:expiration:show_details
        # expiration may contain colons (ISO datetime), so split on first 2 only,
        # then strip :true/:false suffix from the remainder for show_details.
        pairs = []
        raw_lines = f.readlines()
        for line in raw_lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split(":", 2)  # username, token, rest
            if len(parts) < 2:
                continue
            username = parts[0]
            token = parts[1]
            rest = parts[2] if len(parts) > 2 else ""
            # Detect trailing :true / :false for the show_details flag
            show_details_str = "false"
            if rest.endswith(":true") or rest.endswith(":True"):
                show_details_str = "true"
                rest = rest[:-5]
            elif rest.endswith(":false") or rest.endswith(":False"):
                show_details_str = "false"
                rest = rest[:-6]
            expiration = rest
            pairs.append((username, token, expiration, show_details_str))
        return pairs

def save_tokens(pairs):
    with open(TOKENS_FILE, "w") as f:
        for entry in pairs:
            username, token, expiration = entry[0], entry[1], entry[2]
            show_details_str = entry[3] if len(entry) > 3 else "false"
            f.write(f"{username}:{token}:{expiration}:{show_details_str}\n")

# Move update_token_expiry to top level
def update_token_expiry(username, new_expiry):
    pairs = load_tokens()
    logger = get_logger()
    updated = False
    token = None
    old_expiry = None
    show_details_for_user = "false"
    for i, entry in enumerate(pairs):
        u, t, e = entry[0], entry[1], entry[2]
        sd = entry[3] if len(entry) > 3 else "false"
        if u == username:
            old_expiry = e
            show_details_for_user = sd
            pairs[i] = (u, t, new_expiry, sd)
            token = t
            updated = True
            break
    if updated:
        save_tokens(pairs)
        # Log the change
        logger.info(f"Token expiry changed for user '{username}' (token: {token}) from '{old_expiry or 'never'}' to '{new_expiry or 'never'}'")
        # If new_expiry is in the future, recreate symlink if missing
        try:
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE)
            output_path = config.get('settings', 'output_path', fallback='/var/www/html/').rstrip('/')
            filename = config.get('settings', 'filename', fallback='').lstrip('/')
            if output_path and filename and token:
                target = os.path.join(output_path, filename)
                link_name = os.path.join(output_path, f"{token}.ics")
                recreate = False
                if not new_expiry:
                    # No expiry, always recreate
                    recreate = True
                else:
                    try:
                        exp_dt = datetime.fromisoformat(new_expiry)
                        if exp_dt > datetime.now():
                            recreate = True
                    except Exception:
                        pass
                if recreate and not os.path.islink(link_name) and not os.path.exists(link_name):
                    sd_bool = show_details_for_user.lower() == "true"
                    ensure_token_links(token, sd_bool)
        except Exception:
            pass
    return updated
def update_user_show_details(username, show_details_for_user: bool):
    """Toggle the per-user show_details flag and reroute the symlink accordingly."""
    pairs = load_tokens()
    logger = get_logger()
    token = None
    sd_str = "true" if show_details_for_user else "false"
    for i, entry in enumerate(pairs):
        if entry[0] == username:
            token = entry[1]
            pairs[i] = (entry[0], entry[1], entry[2], sd_str)
            break
    if token is None:
        return False
    save_tokens(pairs)
    logger.info(f"show_details set to '{sd_str}' for user '{username}' (token: {token})")
    ensure_token_links(token, show_details_for_user)
    return True


def ensure_token_links(token, show_details_for_user=False):
    """Ensure the .ics symlink and the per-token .html viewer exist.
    When the global show_details=true, users with show_details_for_user=False
    get a symlink to the anonymized companion ICS instead of the main file.
    Returns (success: bool, message: str)
    """
    logger = get_logger()
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    output_path = config.get('settings', 'output_path', fallback='/var/www/html/').rstrip('/')
    filename = config.get('settings', 'filename', fallback='').lstrip('/')
    global_show_details = config.getboolean('settings', 'show_details', fallback=True)
    if not output_path or not filename:
        return False, 'output_path or filename not configured in config.ini'
    main_target = os.path.join(output_path, filename)
    # Route to anon companion when global details are on but user has no detail access
    if global_show_details and not show_details_for_user:
        target = get_anon_output_path(main_target)
    else:
        target = main_target
    link_name = os.path.join(output_path, f"{token}.ics")
    html_dest = os.path.join(output_path, f"{token}.html")
    try:
        # create or replace symlink
        if os.path.islink(link_name) or os.path.exists(link_name):
            os.remove(link_name)
        os.symlink(target, link_name)
        # copy template (non-fatal) with injected color map if configured
        try:
            template = os.path.join(os.path.dirname(__file__), 'viewer_template.html')
            if os.path.exists(template):
                try:
                    cfg = configparser.ConfigParser()
                    cfg.read(CONFIG_FILE)
                    color_map = {}
                    # Always inject color mappings for the viewer if provided
                    if cfg.has_section('colors'):
                        for k, v in cfg.items('colors'):
                            color_map[k] = v
                    _write_viewer_html_with_map(template, html_dest, color_map)
                except Exception:
                    shutil.copyfile(template, html_dest)
        except Exception as e:
            logger.warning(f"Failed to copy viewer template for token '{token}': {e}")
        return True, 'Links ensured'
    except Exception as e:
        logger.error(f"Failed to ensure links for token '{token}': {e}")
        return False, str(e)


def add_token(username, expiration=None, show_details_for_user=False):
    pairs = load_tokens()
    logger = get_logger()
    if not username:
        return False, "Username cannot be empty."
    # Prevent duplicate usernames
    if any(entry[0] == username for entry in pairs):
        return False, f"Username '{username}' already exists."
    token = generate_token()
    expiration_str = expiration if expiration else ""
    sd_str = "true" if show_details_for_user else "false"
    pairs.append((username, token, expiration_str, sd_str))
    save_tokens(pairs)
    # Create symlink for the token in output_path
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    output_path = config.get('settings', 'output_path', fallback='/var/www/html/').rstrip('/')
    filename = config.get('settings', 'filename', fallback='').lstrip('/')
    if output_path and filename:
        try:
            ok, msg = ensure_token_links(token, show_details_for_user)
            if not ok:
                logger.error(f"Token created for '{username}' but failed to create symlink: {msg}")
                return False, f"Token created, but failed to create symlink: {msg}"
        except Exception as e:
            logger.error(f"Token created for '{username}' but failed to create symlink: {e}")
            return False, f"Token created, but failed to create symlink: {e}"
    logger.info(f"Token created for user '{username}' (token: {token}, expires: {expiration_str or 'never'})")
    return True, token

def remove_token(username):
    pairs = load_tokens()
    logger = get_logger()
    removed_token = None
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    output_path = config.get('settings', 'output_path', fallback='/var/www/html/').rstrip('/')
    # Find the token to remove
    for entry in pairs:
        if entry[0] == username:
            removed_token = entry[1]
            break
    new_pairs = [entry for entry in pairs if entry[0] != username]
    if len(new_pairs) == len(pairs):
        return False
    save_tokens(new_pairs)
    # Remove symlink if it exists
    if removed_token and output_path:
        link_name = os.path.join(output_path, f"{removed_token}.ics")
        html_name = os.path.join(output_path, f"{removed_token}.html")
        try:
            if os.path.islink(link_name) or os.path.exists(link_name):
                os.remove(link_name)
            if os.path.islink(html_name) or os.path.exists(html_name):
                os.remove(html_name)
        except Exception:
            pass
    logger.info(f"Token deleted for user '{username}' (token: {removed_token})")
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

# Bulk action: ensure links for all users
if st.button("Ensure Links for All Users"):
    pairs_all = load_tokens()
    if not pairs_all:
        st.info("No users found.")
    else:
        with st.spinner("Ensuring .ics and .html links for all users..."):
            progress = st.progress(0)
            total = len(pairs_all)
            failures = []
            for i, entry in enumerate(pairs_all):
                u, t = entry[0], entry[1]
                sd = (entry[3] if len(entry) > 3 else "false").lower() == "true"
                ok, msg = ensure_token_links(t, sd)
                if not ok:
                    failures.append((u, t, msg))
                progress.progress(int((i+1)/total*100))
        if failures:
            st.error(f"Failed for {len(failures)} users. Check logs for details.")
        else:
            st.success("All links ensured.")
        st.rerun()

# Add token with expiration
with st.form("add_token_form"):
    username = st.text_input("Enter username:")
    set_exp = st.checkbox("Set expiration date/time")
    # Set default expiration date to the same day next month
    today = datetime.now().date()
    if today.month == 12:
        next_month = today.replace(year=today.year+1, month=1)
    else:
        # Handle months with fewer days
        try:
            next_month = today.replace(month=today.month+1)
        except ValueError:
            # If next month doesn't have this day, use the last day of next month
            from calendar import monthrange
            last_day = monthrange(today.year + (today.month // 12), ((today.month % 12) + 1))[1]
            next_month = today.replace(month=((today.month % 12) + 1), day=last_day)
    default_date = next_month
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
    global_show_details = config.getboolean('settings', 'show_details', fallback=True)
    for idx, entry in enumerate(pairs):
        username = entry[0]
        token = entry[1]
        expiration = entry[2]
        user_show_details = (entry[3] if len(entry) > 3 else "false").lower() == "true"
        status = token_expiry_status(expiration)
        # Remove symlink for expired tokens
        if status == 'expired' and output_path:
            link_name = os.path.join(output_path, f"{token}.ics")
            html_name = os.path.join(output_path, f"{token}.html")
            try:
                if os.path.islink(link_name) or os.path.exists(link_name):
                    os.remove(link_name)
                if os.path.islink(html_name) or os.path.exists(html_name):
                    os.remove(html_name)
            except Exception:
                pass
        col1, col2, col3 = st.columns([3,6,2])
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

        # Per-user show_details toggle (only visible when the global setting is enabled)
        if global_show_details:
            toggle_label = "Details: ON" if user_show_details else "Details: OFF"
            toggle_help = "User can see full event details" if user_show_details else "User sees anonymized events (Busy/Free)"
            btn_type = "primary" if user_show_details else "secondary"
            if col1.button(toggle_label, key=f"toggle_details_{username}", help=toggle_help, type=btn_type):
                if update_user_show_details(username, not user_show_details):
                    st.rerun()

        # Expiry date/time management UI
        with col3:
            edit_exp = st.expander("Edit Expiry", expanded=False)
            with edit_exp:
                # Show current expiry or allow to set
                if expiration:
                    try:
                        exp_dt = datetime.fromisoformat(expiration)
                        exp_date = exp_dt.date()
                        exp_time = exp_dt.time().replace(second=0, microsecond=0)
                    except Exception:
                        exp_date = datetime.now().date()
                        exp_time = datetime.now().time().replace(second=0, microsecond=0)
                else:
                    exp_date = datetime.now().date()
                    exp_time = datetime.now().time().replace(second=0, microsecond=0)
                new_date = st.date_input(f"Date for {username}", value=exp_date, key=f"date_{username}")
                new_time = st.time_input(f"Time for {username}", value=exp_time, key=f"time_{username}")
                if st.button("Update Expiry", key=f"update_expiry_{username}"):
                    new_expiry = datetime.combine(new_date, new_time).isoformat()
                    if update_token_expiry(username, new_expiry):
                        st.success("Expiry updated.")
                        # Recalculate status after update
                        st.rerun()
                    else:
                        st.error("Failed to update expiry.")
                if expiration:
                    if st.button("Remove Expiry", key=f"remove_expiry_{username}"):
                        if update_token_expiry(username, ""):
                            st.success("Expiry removed.")
                            # Recalculate status after removal
                            st.rerun()
                        else:
                            st.error("Failed to remove expiry.")
        if domain:
            ics_url = f"{domain}/{token}.ics"
            html_url = f"{domain}/{token}.html"
            col2.code(ics_url)
            with col2:
                render_share_button(username, ics_url, html_url)
        else:
            col2.code(token)
        if col3.button(f"Ensure Links", key=f"ensure_{username}"):
            ok, msg = ensure_token_links(token, user_show_details)
            if ok:
                st.success("Links ensured.")
                st.rerun()
            else:
                st.error(f"Failed to ensure links: {msg}")
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
