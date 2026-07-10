"""
Verify the _parse_season_episode logic and filter behaviour.
Run from the project root: python wastream/scratch/verify_torznab_filter.py
"""
import re
from typing import Optional, Tuple

# ---- copy of the helper ----
_SXEX_RE = re.compile(r'[Ss](\d{1,2})[.\s]?[Ee](\d{1,3})', re.IGNORECASE)
_ALT_EP_RE = re.compile(r'(?<!\d)(\d{1,2})[x](\d{1,3})(?!\d)', re.IGNORECASE)
_SEASON_ONLY_RE = re.compile(r'[Ss](\d{1,2})(?![.\s]?[Ee])', re.IGNORECASE)


def _parse_season_episode(release_name: str) -> Tuple[Optional[int], Optional[int]]:
    m = _SXEX_RE.search(release_name)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = _ALT_EP_RE.search(release_name)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = _SEASON_ONLY_RE.search(release_name)
    if m:
        return int(m.group(1)), None
    return None, None


def should_keep(release_name, req_season, req_episode):
    """Returns True if result should be kept."""
    try:
        req_s, req_e = int(req_season), int(req_episode)
        parsed_s, parsed_e = _parse_season_episode(release_name)
        if parsed_s is not None:
            if parsed_s != req_s:
                return False
            if parsed_e is not None and parsed_e != req_e:
                return False
        return True
    except (ValueError, TypeError):
        return True  # can't validate → keep


# ---- test cases ----
cases = [
    # (release_name, req_s, req_e, expected_keep)
    ("Show.S02E04.1080p.BluRay",     2, 4, True,  "exact match"),
    ("Show.S02E05.1080p.BluRay",     2, 4, False, "wrong episode"),
    ("Show.S02E04E05.1080p.BluRay",  2, 4, True,  "multi-ep, first matches"),
    ("Show.S02.E04.1080p",           2, 4, True,  "dot-separated"),
    ("Show.2x04.1080p",              2, 4, True,  "Nx format"),
    ("Show.S02.COMPLETE.BluRay",     2, 4, True,  "season pack"),
    ("Show.S02.1080p.BluRay",        2, 4, True,  "season pack no label"),
    ("Show.S03E04.BluRay",           2, 4, False, "wrong season"),
    ("Show.S02E04-E06.1080p.VOSTFR", 2, 4, True,  "episode range starting at E4"),
    ("Show.1080p.BluRay",            2, 4, True,  "no episode info - keep"),
]

all_pass = True
for release_name, req_s, req_e, expected, label in cases:
    result = should_keep(release_name, req_s, req_e)
    status = "PASS" if result == expected else "FAIL"
    if result != expected:
        all_pass = False
    print(f"{status} [{label}] keep={result} | {release_name}")

print()
print("All tests passed!" if all_pass else "Some tests FAILED")
