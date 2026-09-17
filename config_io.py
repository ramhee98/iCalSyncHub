"""Read and write config.ini without destroying its comments.

``configparser.write()`` regenerates the file from its parsed state, which
silently drops every comment and blank line.  config.ini ships with the
documentation for each setting inline, so any code path that persists a
single value would wipe that documentation.  The helpers below edit the
file as text instead, touching only the lines they actually need to.
"""

import configparser
import os
import re
import tempfile

_SECTION_RE = re.compile(r'^\s*\[([^\]]+)\]\s*$')
_COMMENT_PREFIXES = ('#', ';')


def load_config(config_path):
    """Load a configuration file with interpolation disabled."""
    config = configparser.ConfigParser(interpolation=None)
    config.read(config_path)
    return config


def _read_lines(config_path):
    if not os.path.exists(config_path):
        return []
    with open(config_path, 'r') as f:
        return f.read().splitlines()


def _write_lines(config_path, lines):
    """Write the file via a temporary file so a crash cannot truncate it."""
    directory = os.path.dirname(os.path.abspath(config_path))
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix='.config_io_', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        if os.path.exists(config_path):
            # Keep the original file mode rather than the 0600 mkstemp default.
            os.chmod(tmp_path, os.stat(config_path).st_mode & 0o7777)
        os.replace(tmp_path, config_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def _section_bounds(lines, section):
    """Return (header_index, end_index) for `section`, or (None, None).

    `end_index` is one past the section's last line, i.e. the index of the
    next section header or the end of the file.
    """
    start = None
    for i, line in enumerate(lines):
        match = _SECTION_RE.match(line)
        if not match:
            continue
        if start is not None:
            return start, i
        if match.group(1).strip().lower() == section.lower():
            start = i
    if start is None:
        return None, None
    return start, len(lines)


def _ensure_section(lines, section):
    """Return the bounds of `section`, appending the header if it is missing."""
    start, end = _section_bounds(lines, section)
    if start is not None:
        return start, end
    if lines and lines[-1].strip():
        lines.append('')
    lines.append(f'[{section}]')
    return len(lines) - 1, len(lines)


def _key_line_re(key):
    """Match `key = value` / `key: value`, capturing the layout around it."""
    return re.compile(r'^(\s*)(' + re.escape(key) + r')(\s*[:=]\s*)(.*)$', re.IGNORECASE)


def _split_entry(line):
    """Split a `key = value` line, or return None if it is not one."""
    candidates = [line.find(sep) for sep in ('=', ':')]
    candidates = [i for i in candidates if i > 0]
    if not candidates:
        return None
    index = min(candidates)
    return line[:index].strip(), line[index + 1:].strip()


def set_values(config_path, section, values):
    """Update `values` (a key -> value mapping) inside `section`.

    Keys already present keep their position and surrounding layout; only the
    value after the separator is rewritten.  Keys that are missing are
    appended to the end of the section, and the section itself is created at
    the end of the file if it does not exist.
    """
    lines = _read_lines(config_path)
    start, end = _ensure_section(lines, section)

    for key, value in values.items():
        text = '' if value is None else str(value)
        pattern = _key_line_re(key)
        replaced = False
        for i in range(start + 1, end):
            match = pattern.match(lines[i])
            if match:
                lines[i] = f'{match.group(1)}{match.group(2)}{match.group(3)}{text}'.rstrip()
                replaced = True
                break
        if replaced:
            continue
        # Insert after the section's last real entry.  Falling back to the
        # last non-blank line would drop the key into the comment block that
        # documents the *next* section, since those comments sit above its
        # header and therefore still count as part of this section.
        insert_at = start
        for i in range(start + 1, end):
            stripped = lines[i].strip()
            if stripped and not stripped.startswith(_COMMENT_PREFIXES) and _split_entry(stripped):
                insert_at = i
        lines.insert(insert_at + 1, f'{key} = {text}'.rstrip())
        end += 1

    _write_lines(config_path, lines)


def read_entries(config_path, section):
    """Return a section's key/value pairs with the original key casing.

    ``configparser`` lower-cases keys, which matters for ``[colors]`` where the
    key is an event SUMMARY.  Reading the raw text keeps the user's spelling.
    """
    lines = _read_lines(config_path)
    start, end = _section_bounds(lines, section)
    entries = {}
    if start is None:
        return entries
    for line in lines[start + 1:end]:
        stripped = line.strip()
        if not stripped or stripped.startswith(_COMMENT_PREFIXES):
            continue
        entry = _split_entry(stripped)
        if entry:
            entries[entry[0]] = entry[1]
    return entries


def replace_entries(config_path, section, entries):
    """Replace every key/value line in `section` with `entries`.

    Comment lines are kept, so the commented examples that document the
    section survive.  Keys absent from `entries` are removed.
    """
    lines = _read_lines(config_path)
    start, end = _ensure_section(lines, section)

    kept = [
        line for line in lines[start + 1:end]
        if not line.strip() or line.lstrip().startswith(_COMMENT_PREFIXES)
    ]
    while kept and not kept[-1].strip():
        kept.pop()

    lines[start + 1:end] = kept + [f'{k} = {v}' for k, v in entries.items()]
    _write_lines(config_path, lines)
