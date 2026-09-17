import streamlit as st
import pandas as pd
import os
import re
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import config_io

CONFIG_FILE = os.path.join(ROOT, 'config.ini')
TEMPLATE_FILE = os.path.join(ROOT, 'config_template.ini')
LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
LOG_OUTPUTS = ['console', 'file', 'both', 'none']
HEX_RE = re.compile(r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')

st.set_page_config(
    page_title="Settings — iCalSyncHub",
    page_icon="⚙️",
    layout="wide",
)

st.title("Settings")
st.caption(
    "Edit config.ini from the browser. Values are written straight to the file — "
    "comments and layout are preserved — and take effect on the next sync cycle."
)

if not os.path.exists(CONFIG_FILE):
    st.error(
        f"No config.ini at `{CONFIG_FILE}`. "
        "Copy `config_template.ini` to `config.ini` and reload this page."
    )
    if os.path.exists(TEMPLATE_FILE) and st.button("Create config.ini from template"):
        import shutil
        shutil.copyfile(TEMPLATE_FILE, CONFIG_FILE)
        st.rerun()
    st.stop()

# A message stashed by the previous run survives the rerun that reloads the
# widgets from the file we just wrote.
for level, message in st.session_state.pop('settings_flash', []):
    getattr(st, level)(message)

config = config_io.load_config(CONFIG_FILE)


def text_of(key, fallback=''):
    return config.get('settings', key, fallback=fallback)


def int_of(key, fallback):
    try:
        return int(text_of(key, str(fallback)))
    except ValueError:
        return fallback


def bool_of(key, fallback):
    try:
        return config.getboolean('settings', key, fallback=fallback)
    except ValueError:
        return fallback


def index_of(options, value, fallback=0):
    try:
        return options.index(value.strip().lower() if value else '')
    except ValueError:
        return fallback


def anon_name(filename):
    """The companion filename sync_calendars derives from `filename`."""
    base, ext = os.path.splitext(filename)
    return f"{base}_anon{ext}"


def log_line(message):
    """Append an audit line to the configured log file (best effort)."""
    if text_of('log_output', 'both').lower() not in ('file', 'both'):
        return
    log_file = text_of('log_file', 'icalsynchub.log').strip()
    if not log_file:
        return
    path = log_file if os.path.isabs(log_file) else os.path.join(ROOT, log_file)
    stamp = f"{datetime.now():%Y-%m-%d %H:%M:%S,%f}"[:-3]
    try:
        with open(path, 'a') as f:
            f.write(f"{stamp} - INFO - {message}\n")
    except OSError:
        pass


current_colors = config_io.read_entries(CONFIG_FILE, 'colors')

with st.form("settings_form"):
    tab_output, tab_sync, tab_events, tab_logging, tab_colors = st.tabs(
        ["Output & sharing", "Sync schedule", "Events", "Logging", "Event colors"]
    )

    with tab_output:
        output_path = st.text_input(
            "Output directory",
            value=text_of('output_path', './'),
            help="Where the merged .ics files and the per-user links are written.",
        )
        domain = st.text_input(
            "Domain",
            value=text_of('domain'),
            help="Public base URL the output directory is served from, used to build share links.",
        )
        col_a, col_b = st.columns(2)
        with col_a:
            filename = st.text_input(
                "Calendar filename",
                value=text_of('filename'),
                help="The merged calendar. Leave blank to have a random name generated on the next sync.",
            )
        with col_b:
            filename_raw = st.text_input(
                "Raw calendar filename",
                value=text_of('filename_raw'),
                help="Same calendar without the per-URL custom summaries — every event keeps its "
                     "original SUMMARY. Leave blank to have a random name generated on the next sync.",
            )

    with tab_sync:
        sync_interval = st.number_input(
            "Sync interval (seconds)",
            min_value=0, step=60,
            value=int_of('sync_interval', 3600),
            help="0 runs a single sync and exits — the right value for a cron job.",
        )
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            retries = st.number_input(
                "Retries per calendar", min_value=1, max_value=20,
                value=int_of('retries', 3),
            )
        with col_b:
            delay = st.number_input(
                "Delay between retries (s)", min_value=0, max_value=300,
                value=int_of('delay', 5),
            )
        with col_c:
            timeout = st.number_input(
                "HTTP timeout (s)", min_value=1, max_value=300,
                value=int_of('timeout', 10),
            )

    with tab_events:
        show_details = st.toggle(
            "Show event details",
            value=bool_of('show_details', True),
            help="Off replaces every SUMMARY with a plain availability label. When on, an "
                 "anonymized companion file is written alongside the main one for users "
                 "without detail access.",
        )
        filter_by_date = st.toggle(
            "Limit events to a date range",
            value=bool_of('filter_by_date', False),
        )
        col_a, col_b = st.columns(2)
        with col_a:
            past_days = st.number_input(
                "Days in the past", min_value=0, max_value=3650,
                value=int_of('past_days', 14),
            )
        with col_b:
            future_months = st.number_input(
                "Months in the future", min_value=0, max_value=120,
                value=int_of('future_months', 2),
            )
        if not filter_by_date:
            st.caption("The range is only applied while the toggle above is on.")

    with tab_logging:
        col_a, col_b = st.columns(2)
        with col_a:
            log_output = st.selectbox(
                "Log destination", LOG_OUTPUTS,
                index=index_of(LOG_OUTPUTS, text_of('log_output', 'both'), LOG_OUTPUTS.index('both')),
            )
        with col_b:
            log_level = st.selectbox(
                "Log level", LOG_LEVELS,
                index=(LOG_LEVELS.index(text_of('log_level', 'INFO').strip().upper())
                       if text_of('log_level', 'INFO').strip().upper() in LOG_LEVELS
                       else LOG_LEVELS.index('INFO')),
            )
        log_file = st.text_input("Log file", value=text_of('log_file', 'icalsynchub.log'))
        col_c, col_d = st.columns(2)
        with col_c:
            max_log_file_size = st.number_input(
                "Rotate at (MB)", min_value=1, max_value=1024,
                value=int_of('max_log_file_size', 10),
            )
        with col_d:
            log_backup_count = st.number_input(
                "Rotated files to keep", min_value=0, max_value=100,
                value=int_of('log_backup_count', 5),
            )

    with tab_colors:
        st.caption(
            "Maps an event's original SUMMARY to a colour used by the HTML viewer. "
            "The lookup is case-insensitive, and a `Default` entry colours everything unmatched."
        )
        colors_df = st.data_editor(
            pd.DataFrame(
                [{"Summary": k, "Color": v} for k, v in current_colors.items()],
                columns=["Summary", "Color"],
            ),
            num_rows="dynamic",
            hide_index=True,
            width="stretch",
            column_config={
                "Summary": st.column_config.TextColumn("Summary", required=False),
                "Color": st.column_config.TextColumn("Color", help="Hex value, e.g. #4E86D2"),
            },
            key="colors_editor",
        )

    submitted = st.form_submit_button("Save settings", type="primary")

if submitted:
    errors = []
    warnings = []

    output_path = output_path.strip()
    domain = domain.strip()
    filename = filename.strip()
    filename_raw = filename_raw.strip()
    log_file = log_file.strip()

    if not output_path:
        errors.append("Output directory must not be empty.")
    elif not os.path.isdir(output_path):
        errors.append(f"Output directory `{output_path}` does not exist — create it first.")
    elif not os.access(output_path, os.W_OK):
        warnings.append(f"Output directory `{output_path}` is not writable by this user.")

    for label, value in (("Calendar filename", filename), ("Raw calendar filename", filename_raw)):
        if not value:
            continue  # blank is legal: a random name is generated on the next sync
        if os.path.basename(value) != value or value in ('.', '..'):
            errors.append(f"{label} must be a bare filename, not a path.")
        elif not value.lower().endswith('.ics'):
            errors.append(f"{label} must end in .ics.")

    # The raw file is written in the same directory as the main one, so a
    # shared name would have the two syncs overwrite each other.
    if filename and filename_raw:
        if filename == filename_raw:
            errors.append("Calendar filename and raw calendar filename must differ.")
        elif filename_raw == anon_name(filename):
            errors.append(
                f"Raw calendar filename collides with the anonymized companion "
                f"`{anon_name(filename)}` that is generated from the calendar filename."
            )

    if domain and not domain.startswith(('http://', 'https://')):
        warnings.append("Domain does not start with http:// or https:// — share links may not work.")

    if log_output in ('file', 'both'):
        if not log_file:
            errors.append("A log file is required for the selected log destination.")
        elif os.path.isdir(log_file):
            errors.append(f"Log file `{log_file}` is a directory.")

    colors = {}
    seen = set()
    for row in colors_df.to_dict('records'):
        summary = str(row.get('Summary') or '').strip()
        color = str(row.get('Color') or '').strip()
        if not summary and not color:
            continue
        if not summary:
            errors.append(f"Colour `{color}` has no summary.")
            continue
        if not HEX_RE.match(color):
            errors.append(f"`{summary}` has an invalid colour `{color}` — use #rgb or #rrggbb.")
            continue
        if summary.lower() in seen:
            errors.append(f"Duplicate colour entry for `{summary}`.")
            continue
        seen.add(summary.lower())
        colors[summary] = color

    if errors:
        for message in errors:
            st.error(message)
    else:
        new_values = {
            'output_path': output_path,
            'domain': domain,
            'filename': filename,
            'filename_raw': filename_raw,
            'sync_interval': int(sync_interval),
            'retries': int(retries),
            'delay': int(delay),
            'timeout': int(timeout),
            'show_details': str(show_details).lower(),
            'filter_by_date': str(filter_by_date).lower(),
            'past_days': int(past_days),
            'future_months': int(future_months),
            'log_output': log_output,
            'log_level': log_level,
            'log_file': log_file,
            'max_log_file_size': int(max_log_file_size),
            'log_backup_count': int(log_backup_count),
        }

        changed = [
            key for key, value in new_values.items()
            if text_of(key) != str(value)
        ]
        colors_changed = colors != current_colors

        if not changed and not colors_changed:
            st.info("No changes to save.")
        else:
            try:
                config_io.set_values(CONFIG_FILE, 'settings', new_values)
                if colors_changed:
                    config_io.replace_entries(CONFIG_FILE, 'colors', colors)
            except OSError as e:
                st.error(f"Could not write config.ini: {e}")
            else:
                summary_parts = []
                if changed:
                    summary_parts.append(", ".join(changed))
                if colors_changed:
                    summary_parts.append("event colors")
                detail = "; ".join(summary_parts)
                log_line(f"Settings updated via the UI: {detail}")

                flash = [('success', f"Saved. Updated: {detail}.")]
                for message in warnings:
                    flash.append(('warning', message))
                if any(key in changed for key in ('output_path', 'filename')):
                    flash.append((
                        'warning',
                        "The calendar location changed. Existing per-user links still point at "
                        "the old file — run a sync, then use “Ensure Links for All Users” on the "
                        "token page.",
                    ))
                flash.append(('info', "Changes are picked up by the next sync cycle."))
                st.session_state['settings_flash'] = flash
                st.rerun()

with st.expander("Resolved paths"):
    resolved_dir = text_of('output_path', './')
    main_name = text_of('filename')
    raw_name = text_of('filename_raw')
    pending = "(generated on the next sync)"

    rows = [
        ("merged", os.path.join(resolved_dir, main_name) if main_name else pending),
        ("anonymized", os.path.join(resolved_dir, anon_name(main_name)) if main_name else pending),
        ("raw", os.path.join(resolved_dir, raw_name) if raw_name else pending),
        ("config", CONFIG_FILE),
    ]
    width = max(len(label) for label, _ in rows)
    st.code("\n".join(f"{label.ljust(width)}  {value}" for label, value in rows), language=None)
    if not bool_of('show_details', True):
        st.caption("The anonymized companion is only written while “Show event details” is on.")

with st.expander("Raw config.ini"):
    st.caption("Settings this page does not expose are left untouched when you save.")
    with open(CONFIG_FILE) as f:
        st.code(f.read(), language="ini")
