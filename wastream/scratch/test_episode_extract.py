import re

test_names = [
    "Show.Name.S02E04.1080p.BluRay",
    "Show.Name.S02E05.1080p.BluRay",
    "Show.Name.S02E04E05.1080p.BluRay",       # multi-episode pack
    "Show.Name.S02.E04.1080p",
    "Show.Name.2x04.1080p",
    "Show.Name.Season.2.Episode.4.1080p",
    "Show.Name.S02.COMPLETE.BluRay",           # full season pack
    "Show.Name.S02.1080p.BluRay",              # full season pack
    "Show.Name.S02E04-E06.1080p.VOSTFR",       # episode range
    "Show Name - 2x04 - Episode Title.mkv",
    "show.name.s2.e4.french.hdtv",             # lower digits
]

# Pattern for SxxExx with optional separator between S and E
SXEX_PATTERN = re.compile(
    r'[Ss](\d{1,2})[.\s]?[Ee](\d{1,3})',
    re.IGNORECASE
)
# Alternate: 2x04 style
ALT_EPISODE_PATTERN = re.compile(
    r'(?<!\d)(\d{1,2})[x](\d{1,3})(?!\d)',
    re.IGNORECASE
)
# Full season pack (Sxx without Exx)
FULL_SEASON_ONLY = re.compile(
    r'[Ss](\d{1,2})(?![.\s]?[Ee])',
    re.IGNORECASE
)

def extract_episode_from_name(release_name):
    m = SXEX_PATTERN.search(release_name)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = ALT_EPISODE_PATTERN.search(release_name)
    if m:
        return int(m.group(1)), int(m.group(2))
    # Season pack but no episode
    m = FULL_SEASON_ONLY.search(release_name)
    if m:
        return int(m.group(1)), None
    return None, None

for name in test_names:
    s, e = extract_episode_from_name(name)
    result = f"s={s} e={e:>4}" if e is not None else f"s={s} e=None"
    print(f"  {result}  {name}")
