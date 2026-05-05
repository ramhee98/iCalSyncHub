import streamlit as st
import json
import os
from datetime import datetime

SYNC_STATUS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'sync_status.json',
)

st.set_page_config(
    page_title="Timezone Conflicts — iCalSyncHub",
    page_icon="🌍",
    layout="wide",
)

st.title("Timezone Conflicts")
st.caption(
    "Events whose timezone information is missing, ambiguous, or unknown. "
    "These often render at a different wall-clock time than the author intended."
)


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
    st.info("No sync data available yet. Run a sync cycle first.")
    st.stop()

conflicts = status.get('tz_conflicts', [])
last_sync = status.get('last_sync', 'N/A')

c1, c2, c3 = st.columns(3)
c1.metric("Total conflicts", len(conflicts))
c2.metric(
    "Floating time",
    sum(1 for c in conflicts if c.get('type') == 'floating'),
)
c3.metric(
    "Unknown TZID",
    sum(1 for c in conflicts if c.get('type') == 'unknown_tzid'),
)
st.caption(f"Last sync: {last_sync}")

if not conflicts:
    st.success("No timezone conflicts detected in the most recent sync. 🎉")
    st.stop()

# Group by source for readability
by_source: dict[str, list[dict]] = {}
for conflict in conflicts:
    by_source.setdefault(conflict.get('source_url', 'unknown'), []).append(conflict)

TYPE_LABEL = {
    'floating': '🟡 Floating time (no TZID, no UTC)',
    'unknown_tzid': '🔴 Unknown TZID (not in IANA, not declared)',
}

for source_url, items in by_source.items():
    short = source_url if len(source_url) <= 80 else source_url[:77] + '...'
    with st.expander(f"`{short}` — {len(items)} conflict(s)", expanded=False):
        for c in items:
            type_label = TYPE_LABEL.get(c.get('type'), c.get('type', '?'))
            summary = c.get('summary') or '(no summary)'
            uid = c.get('uid') or '(no uid)'
            tzid = c.get('tzid')
            time_key = c.get('time_key', '?')
            line = f"**{summary}** — {type_label} on `{time_key}`"
            if tzid:
                line += f" (TZID: `{tzid}`)"
            line += f"  \nUID: `{uid}`"
            st.markdown(line)
            st.divider()
