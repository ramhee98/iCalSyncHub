import streamlit as st
import altair as alt
import pandas as pd
import json
import os
from datetime import datetime

SYNC_STATUS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sync_status.json')

st.set_page_config(
    page_title="Sync Health — iCalSyncHub",
    page_icon="🩺",
    layout="wide",
)

st.title("Sync Health Dashboard")
st.caption("Live overview of calendar source status and sync history.")


def load_status():
    if not os.path.exists(SYNC_STATUS_FILE):
        return None
    try:
        with open(SYNC_STATUS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


status = load_status()

if status is None:
    st.info("No sync data available yet. Run a sync cycle first (sync_calendars.py).")
    st.stop()

# ── Summary metrics ──────────────────────────────────────────────────────────
last_sync_str = status.get('last_sync', 'N/A')
try:
    last_sync_dt = datetime.fromisoformat(last_sync_str)
    last_sync_display = last_sync_dt.strftime("%Y-%m-%d %H:%M:%S")
    age = datetime.now() - last_sync_dt
    age_minutes = int(age.total_seconds() // 60)
    if age_minutes < 1:
        age_label = "just now"
    elif age_minutes < 60:
        age_label = f"{age_minutes}m ago"
    else:
        age_label = f"{age_minutes // 60}h {age_minutes % 60}m ago"
except Exception:
    last_sync_display = last_sync_str
    age_label = ""

sources = status.get('sources', [])
ok_count = sum(1 for s in sources if s.get('status') == 'ok')
fail_count = sum(1 for s in sources if s.get('status') != 'ok')
total_events = status.get('total_events', 0)
sync_duration = status.get('sync_duration', 0)

mcol1, mcol2, mcol3, mcol4 = st.columns(4)
mcol1.metric("Last Sync", last_sync_display, help=age_label)
mcol2.metric("Duration", f"{sync_duration:.2f}s")
mcol3.metric("Total Events", total_events)
mcol4.markdown(f"**Sources**  \n:green[{ok_count} OK] / :red[{fail_count} Failed]")

# ── Per-source status table ──────────────────────────────────────────────────
st.write("## Source Status")

if sources:
    for src in sources:
        url = src.get('url', '')
        # Truncate long URLs for display
        display_url = url if len(url) <= 80 else url[:77] + "..."
        src_status = src.get('status', 'unknown')
        response_time = src.get('response_time', 0)
        event_count = src.get('event_count', 0)
        error = src.get('error')
        custom_summary = src.get('custom_summary')

        if src_status == 'ok':
            status_icon = "🟢"
        else:
            status_icon = "🔴"

        label = f" [{custom_summary}]" if custom_summary else ""

        col1, col2, col3, col4 = st.columns([5, 1, 1, 1])
        col1.write(f"{status_icon} `{display_url}`{label}")
        col2.write(f"**{response_time:.2f}s**")
        col3.write(f"**{event_count}** events")
        if error:
            col4.write(f":red[{error[:40]}]")
        else:
            col4.write(":green[OK]")

    # Failure alert
    if fail_count > 0:
        st.warning(f"{fail_count} source(s) failed to fetch in the last sync cycle.")
else:
    st.info("No source data recorded.")

# ── Sync history chart ───────────────────────────────────────────────────────
history = status.get('history', [])
if history:
    st.write("## Sync History")

    tab_duration, tab_events, tab_sources = st.tabs(["Duration", "Events", "Sources"])

    with tab_duration:
        chart_data = {
            'Timestamp': [],
            'Duration (s)': [],
        }
        for entry in history:
            try:
                ts = datetime.fromisoformat(entry['timestamp']).strftime("%m-%d %H:%M")
            except Exception:
                ts = entry.get('timestamp', '?')
            chart_data['Timestamp'].append(ts)
            chart_data['Duration (s)'].append(entry.get('duration', 0))
        st.line_chart(
            data={k: v for k, v in chart_data.items() if k != 'Timestamp'},
            height=250,
        )

    with tab_events:
        chart_data_events = {
            'Timestamp': [],
            'Events': [],
        }
        for entry in history:
            try:
                ts = datetime.fromisoformat(entry['timestamp']).strftime("%m-%d %H:%M")
            except Exception:
                ts = entry.get('timestamp', '?')
            chart_data_events['Timestamp'].append(ts)
            chart_data_events['Events'].append(entry.get('total_events', 0))
        st.line_chart(
            data={k: v for k, v in chart_data_events.items() if k != 'Timestamp'},
            height=250,
        )

    with tab_sources:
        rows = []
        for entry in history:
            try:
                ts = datetime.fromisoformat(entry['timestamp']).strftime("%m-%d %H:%M")
            except Exception:
                ts = entry.get('timestamp', '?')
            rows.append({'Timestamp': ts, 'Status': 'OK', 'Count': entry.get('sources_ok', 0)})
            rows.append({'Timestamp': ts, 'Status': 'Failed', 'Count': entry.get('sources_failed', 0)})
        df_src = pd.DataFrame(rows)
        chart = alt.Chart(df_src).mark_bar().encode(
            x=alt.X('Timestamp:N', sort=None, title='Timestamp'),
            y=alt.Y('Count:Q', title='Sources'),
            color=alt.Color('Status:N', scale=alt.Scale(
                domain=['OK', 'Failed'],
                range=['#22c55e', '#ef4444'],
            ), legend=alt.Legend(title='Status')),
            xOffset='Status:N',
        ).properties(height=250)
        st.altair_chart(chart, use_container_width=True)

    # Recent history table
    with st.expander("Raw history (last 10)"):
        recent = history[-10:][::-1]
        st.table([
            {
                'Timestamp': e.get('timestamp', ''),
                'Duration': f"{e.get('duration', 0):.2f}s",
                'Events': e.get('total_events', 0),
                'OK': e.get('sources_ok', 0),
                'Failed': e.get('sources_failed', 0),
            }
            for e in recent
        ])
else:
    st.info("No sync history available yet. History builds up over multiple sync cycles.")
