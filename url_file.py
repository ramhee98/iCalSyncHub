"""Read and write calendar_urls.txt for the Settings page.

Each source is one line, ``<url>`` or ``<url> #<label>``, optionally preceded
by a ``# Name`` comment line that the file uses as a heading.  A source can be
switched off by commenting its line out (``#<url>``); the sync skips it like any
comment, and here it is a row with ``enabled`` false.  ``load_urls()``
in sync_calendars.py is the authority on how the sync reads these lines; the
parser here mirrors it, but also keeps each heading so the editor can show it
and the file keeps its structure when saved.

Comments that do not sit directly above a URL are not tied to any row.  They
are kept at the top of the file when it is rewritten instead of being dropped.
"""

import os
import tempfile
from collections import namedtuple
from urllib.parse import unquote

Source = namedtuple('Source', ['name', 'url', 'label', 'enabled'], defaults=[True])


def _is_comment(line):
    return line.strip().startswith('#')


def _disabled_source_text(line):
    """Return the text of a commented-out source line, or None for an ordinary comment.

    Only ``#http://…`` and ``# http://…`` count: a comment that merely mentions
    a URL after other words stays a plain comment.
    """
    text = line.strip().lstrip('#').strip()
    if text.startswith(('http://', 'https://')):
        return text
    return None


def parse(lines):
    """Return (sources, loose_comments) for the lines of a URL file."""
    sources = []
    loose = []
    pending = []  # comment lines seen since the last URL or blank line
    for raw in lines:
        line = raw.rstrip('\n')
        if not line.strip():
            loose.extend(pending)
            pending = []
            continue
        enabled = True
        if _is_comment(line):
            text = _disabled_source_text(line)
            if text is None:
                pending.append(line.strip())
                continue
            enabled, line = False, text
        url, label = line, ''
        if '#' in line:
            url, fragment = line.split('#', 1)
            fragment = fragment.strip()
            # Same rule as load_urls(): an empty fragment means "Busy".
            label = unquote(fragment) if fragment else 'Busy'
        # Only the comment directly above the URL is its heading; anything
        # earlier in the same block stays a loose comment.
        name = pending.pop()[1:].strip() if pending else ''
        loose.extend(pending)
        pending = []
        sources.append(Source(name, url.strip(), label, enabled))
    loose.extend(pending)
    return sources, loose


def read(path):
    """Read `path`; a missing file is an empty list."""
    if not os.path.exists(path):
        return [], []
    with open(path, 'r') as f:
        return parse(f.read().splitlines())


def serialize(sources, loose=()):
    lines = list(loose)
    for source in sources:
        if lines:
            lines.append('')
        if source.name:
            lines.append(f'# {source.name}')
        entry = f'{source.url} #{source.label}' if source.label else source.url
        lines.append(entry if source.enabled else f'#{entry}')
    return '\n'.join(lines) + '\n' if lines else ''


def write(path, sources, loose=()):
    """Write the file through a temporary one so a crash cannot truncate it."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix='.url_file_', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(serialize(sources, loose))
        if os.path.exists(path):
            os.chmod(tmp_path, os.stat(path).st_mode & 0o7777)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def validate(sources):
    """Return a list of human-readable problems; empty means the rows are safe to write."""
    errors = []
    seen = {}
    for number, source in enumerate(sources, start=1):
        where = f"Row {number}"
        if not source.url.startswith(('http://', 'https://')):
            errors.append(f"{where}: the URL must start with http:// or https://.")
        elif any(ch.isspace() for ch in source.url):
            errors.append(f"{where}: the URL must not contain spaces — encode them as %20.")
        elif '#' in source.url:
            # Everything after '#' is read as the label, so a URL fragment can't be stored.
            errors.append(f"{where}: the URL must not contain '#'; put the label in the Label column.")
        elif source.url in seen:
            errors.append(f"{where}: duplicate of row {seen[source.url]}, its events would appear twice.")
        else:
            seen[source.url] = number
        if '\n' in source.name or '\r' in source.name or '\n' in source.label or '\r' in source.label:
            errors.append(f"{where}: Name and Label must be a single line.")
    return errors
