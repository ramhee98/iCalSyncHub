import streamlit as st
import json
import os
from datetime import datetime
from pytz import all_timezones, common_timezones

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNC_STATUS_FILE = os.path.join(ROOT, 'sync_status.json')
TZ_OVERRIDES_FILE = os.path.join(ROOT, 'tz_overrides.json')

st.set_page_config(
    page_title="Timezone Conflicts — iCalSyncHub",
    page_icon="🌍",
    layout="wide",
)

st.title("Timezone Conflicts")
st.caption(
    "Events whose timezone information is missing, ambiguous, or unknown. "
    "These often render at a different wall-clock time than the author intended. "
    "Use the actions below to assign a timezone — the override is applied on every sync."
)


def load_status():
    if not os.path.exists(SYNC_STATUS_FILE):
        return None
    try:
        with open(SYNC_STATUS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def load_overrides() -> dict:
    if not os.path.exists(TZ_OVERRIDES_FILE):
        return {}
    try:
        with open(TZ_OVERRIDES_FILE, 'r') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_overrides(data: dict) -> None:
    with open(TZ_OVERRIDES_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def set_override(uid: str, tzid: str) -> None:
    if not uid:
        return
    data = load_overrides()
    data[uid] = {
        'tzid': tzid,
        'updated_at': datetime.now().isoformat(timespec='seconds'),
    }
    save_overrides(data)


def clear_override(uid: str) -> None:
    data = load_overrides()
    if uid in data:
        del data[uid]
        save_overrides(data)


status = load_status()
if status is None:
    st.info("No sync data available yet. Run a sync cycle first.")
    st.stop()

conflicts = status.get('tz_conflicts', [])
overrides = load_overrides()
last_sync = status.get('last_sync', 'N/A')

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total conflicts", len(conflicts))
c2.metric("Floating time", sum(1 for c in conflicts if c.get('type') == 'floating'))
c3.metric("Unknown TZID", sum(1 for c in conflicts if c.get('type') == 'unknown_tzid'))
c4.metric("Active overrides", len(overrides))
st.caption(f"Last sync: {last_sync}")

if not conflicts and not overrides:
    st.success("No timezone conflicts detected and no overrides configured. 🎉")
    st.stop()

TYPE_LABEL = {
    'floating': '🟡 Floating time (no TZID, no UTC)',
    'unknown_tzid': '🔴 Unknown TZID (not in IANA, not declared)',
}

# Default tz options: common zones + UTC at the top
TZ_OPTIONS = ['UTC'] + [tz for tz in common_timezones if tz != 'UTC']

if conflicts:
    st.subheader("Conflicts in the last sync")

    # Group by source for readability
    by_source: dict[str, list[dict]] = {}
    for conflict in conflicts:
        by_source.setdefault(conflict.get('source_url', 'unknown'), []).append(conflict)

    for source_url, items in by_source.items():
        short = source_url if len(source_url) <= 80 else source_url[:77] + '...'
        with st.expander(f"`{short}` — {len(items)} conflict(s)", expanded=False):
            for c in items:
                uid = c.get('uid') or ''
                summary = c.get('summary') or '(no summary)'
                tzid = c.get('tzid')
                time_key = c.get('time_key', '?')
                type_label = TYPE_LABEL.get(c.get('type'), c.get('type', '?'))

                col_info, col_select, col_apply, col_utc = st.columns([5, 3, 1, 1])
                with col_info:
                    line = f"**{summary}**  \n{type_label} on `{time_key}`"
                    if tzid:
                        line += f" (TZID: `{tzid}`)"
                    line += f"  \nUID: `{uid or '(none)'}`"
                    existing = overrides.get(uid)
                    if existing:
                        line += f"  \n✅ Override active: `{existing.get('tzid')}`"
                    st.markdown(line)
                with col_select:
                    chosen = st.selectbox(
                        "Assign timezone",
                        options=TZ_OPTIONS,
                        key=f"select_{uid}",
                        label_visibility="collapsed",
                    )
                with col_apply:
                    if st.button("Apply", key=f"apply_{uid}", disabled=not uid):
                        set_override(uid, chosen)
                        st.success(f"Override saved for `{uid}` → {chosen}. Next sync will apply it.")
                        st.rerun()
                with col_utc:
                    if st.button("UTC", key=f"utc_{uid}", disabled=not uid, help="Force UTC"):
                        set_override(uid, 'UTC')
                        st.success(f"Override saved for `{uid}` → UTC. Next sync will apply it.")
                        st.rerun()
                st.divider()

if overrides:
    st.subheader("Configured overrides")
    for uid, info in list(overrides.items()):
        col1, col2, col3 = st.columns([6, 2, 1])
        col1.markdown(f"`{uid}` → **{info.get('tzid')}**  \n_set {info.get('updated_at', '?')}_")
        col2.write("")
        if col3.button("Remove", key=f"remove_{uid}"):
            clear_override(uid)
            st.rerun()
