"""Detail levels shared by the sync, the token page and the settings page.

A calendar can be shared at three levels of detail, from least to most:

    none   only availability: every event is titled Busy or Free
    title  the event title, time and recurrence, but no description, location,
           attendees or any other field
    all    the complete event

The global ``show_details`` setting in config.ini is the highest level that is
written at all; each user's level is capped by it. The main calendar file holds
the global level and every lower level gets a companion file next to it.

The older boolean spelling is still understood: ``true`` means ``all`` and
``false`` means ``none``.
"""
import os

NONE, TITLE, ALL = 'none', 'title', 'all'
LEVELS = (NONE, TITLE, ALL)  # ascending amount of detail
LABELS = {NONE: 'No details', TITLE: 'Title only', ALL: 'All details'}

_ALIASES = {'false': NONE, 'true': ALL}
_COMPANION_SUFFIX = {NONE: '_anon', TITLE: '_title'}


def is_level(value):
    """True if `value` is a level name or the legacy boolean spelling."""
    if isinstance(value, bool):
        return True
    text = str(value).strip().lower() if value is not None else ''
    return _ALIASES.get(text, text) in LEVELS


def parse_level(value, default=NONE):
    """Normalise a config or token value to a level name.

    Booleans and the legacy ``true``/``false`` map to ``all``/``none``. Anything
    unrecognised becomes `default`, which is ``none`` so that a typo can never
    publish more than intended.
    """
    if isinstance(value, bool):
        return ALL if value else NONE
    text = str(value).strip().lower() if value is not None else ''
    text = _ALIASES.get(text, text)
    return text if text in LEVELS else default


def effective_level(user_level, global_level):
    """A user never sees more than the global setting allows."""
    return LEVELS[min(LEVELS.index(parse_level(user_level)), LEVELS.index(parse_level(global_level)))]


def levels_up_to(level):
    """The levels a user can be given under a global `level`, lowest first."""
    return LEVELS[:LEVELS.index(parse_level(level)) + 1]


def companion_path(main_path, level):
    """Where the file for a level below the global one is written.

    ``all`` is never a companion: it is the main file whenever it is enabled.
    """
    if level not in _COMPANION_SUFFIX:
        raise ValueError(f"'{level}' has no companion file")
    base, ext = os.path.splitext(main_path)
    return f"{base}{_COMPANION_SUFFIX[level]}{ext}"


def companion_levels(global_level):
    """Levels that need a companion file: every one below the global level."""
    return LEVELS[:LEVELS.index(parse_level(global_level))]


def stale_companion_levels(global_level):
    """Levels that have a companion file name but must not have one right now.

    Leaving them behind would keep serving the old content, e.g. a ``_title``
    file full of event titles after the global level was lowered to ``none``.
    """
    return tuple(level for level in _COMPANION_SUFFIX if level not in companion_levels(global_level))


def route_target(main_path, global_level, user_level):
    """The file a user's ICS link should point at."""
    level = effective_level(user_level, global_level)
    if level == parse_level(global_level):
        return main_path
    return companion_path(main_path, level)


def split_token_rest(rest):
    """Split the part of a user_tokens.txt line after ``username:token:``.

    The line format is ``username:token:expiration:level``. The expiration is
    an ISO datetime and may itself contain colons, so the level is peeled off
    the right-hand end. Returns ``(expiration, level)``; a missing or
    unrecognised level is ``none``.
    """
    rest = rest or ''
    if rest.strip().lower() in _ALIASES or rest.strip().lower() in LEVELS:
        return '', parse_level(rest)
    if ':' in rest:
        head, last = rest.rsplit(':', 1)
        if is_level(last):
            return head, parse_level(last)
    return rest, NONE
