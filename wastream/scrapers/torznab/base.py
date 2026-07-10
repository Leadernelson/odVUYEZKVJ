import xml.etree.ElementTree as ET
import urllib.parse
import re
from typing import List, Dict, Optional, Tuple

from wastream.utils.http_client import http_client
from wastream.utils.logger import scraper_logger
from wastream.utils.helpers import (
    tokenize_filename, extract_quality_from_tokens,
    extract_language_from_tokens, extract_raw_language_from_tokens,
    build_display_name, normalize_size, normalize_tracker_url
)
from wastream.utils.quality import quality_sort_key


# ===========================
# Episode Parsing Helpers
# ===========================
# Matches S02E04, S2E4, S02.E04, s2.e4, etc.
_SXEX_RE = re.compile(r'[Ss](\d{1,2})[.\s]?[Ee](\d{1,3})', re.IGNORECASE)
# Matches 2x04, 02x04 style
_ALT_EP_RE = re.compile(r'(?<!\d)(\d{1,2})[x](\d{1,3})(?!\d)', re.IGNORECASE)
# Matches S02 NOT followed by an episode marker (season pack)
_SEASON_ONLY_RE = re.compile(r'[Ss](\d{1,2})(?![.\s]?[Ee])', re.IGNORECASE)


def _parse_season_episode(release_name: str) -> Tuple[Optional[int], Optional[int]]:
    """Return (season, episode) parsed from a release name.
    Returns (season, None) for season packs, (None, None) if unrecognised.
    """
    m = _SXEX_RE.search(release_name)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = _ALT_EP_RE.search(release_name)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = _SEASON_ONLY_RE.search(release_name)
    if m:
        return int(m.group(1)), None  # season pack — no specific episode
    return None, None


class BaseTorznab:
    def __init__(self, name: str, url: str, api_key: str, auth_type: str = "query"):
        self.name = name
        self.url = normalize_tracker_url(name, url)
        self.api_key = api_key
        self.auth_type = auth_type  # "query" or "header"

    async def search(self, title: str, year: Optional[str] = None, metadata: Optional[Dict] = None,
                     season: Optional[str] = None, episode: Optional[str] = None,
                     config: Optional[Dict] = None) -> List[Dict]:
        if not self.api_key or not self.url:
            scraper_logger.debug(f"[{self.name}] URL or API key not configured, skipping")
            return []

        # 1. Formulate search query
        search_query = title
        if season and episode:
            try:
                search_query += f" S{int(season):02d}E{int(episode):02d}"
            except (ValueError, TypeError):
                search_query += f" S{season}E{episode}"
        elif year:
            search_query += f" {year}"

        # 2. Build URL and headers
        headers = {
            "User-Agent": "WAStream/1.0"
        }
        if self.auth_type == "header":
            headers["Authorization"] = f"Bearer {self.api_key}"
            url = f"{self.url}?t=search&q={urllib.parse.quote(search_query)}"
        else:
            url = f"{self.url}?t=search&q={urllib.parse.quote(search_query)}&apikey={self.api_key}"

        scraper_logger.debug(f"[{self.name}] Querying: {search_query}")

        try:
            response = await http_client.get(url, headers=headers)
            if response.status_code != 200:
                scraper_logger.error(f"[{self.name}] Torznab search failed: HTTP {response.status_code}")
                return []

            # 3. Parse XML response
            root = ET.fromstring(response.content)
            results = []

            for item in root.findall(".//item"):
                title_node = item.find("title")
                if title_node is None or not title_node.text:
                    continue
                release_name = title_node.text

                # Parse custom Torznab attributes
                size = 0
                infohash = None
                for attr in item.findall(".//{http://torznab.com/schemas/2015/feed}attr"):
                    attr_name = attr.attrib.get("name")
                    attr_value = attr.attrib.get("value")
                    if attr_name == "infohash":
                        infohash = attr_value.lower() if attr_value else None
                    elif attr_name == "size":
                        try:
                            size = int(attr_value)
                        except ValueError:
                            pass

                # Extract magnet or enclosure link
                enclosure = item.find("enclosure")
                torrent_url = None
                if enclosure is not None:
                    torrent_url = enclosure.attrib.get("url")
                if not torrent_url:
                    link_node = item.find("link")
                    if link_node is not None:
                        torrent_url = link_node.text

                # We need either an infohash or a download link
                if not infohash and not torrent_url:
                    continue

                # If we don't have infohash but have magnet URL, extract hash from magnet
                if not infohash and torrent_url and torrent_url.startswith("magnet:"):
                    match = re.search(r"urn:btih:([a-fA-F0-9]{32,40})", torrent_url)
                    if match:
                        infohash = match.group(1).lower()

                if not infohash:
                    # Some trackers might only provide torrent URL, but TorBox / debrid check cached requires infohash.
                    # In case infohash is missing, we try to see if name/link contains it or skip
                    continue

                # Normalize size
                if size > 0:
                    size_gb = size / (1024 ** 3)
                    size_str = f"{size_gb:.2f} GB"
                else:
                    size_str = "Unknown"
                size_str = normalize_size(size_str)

                # Tokenize and parse release name
                tokens = tokenize_filename(release_name)
                quality = extract_quality_from_tokens(tokens)
                language = extract_language_from_tokens(tokens)
                raw_language = extract_raw_language_from_tokens(tokens)

                # --- Episode validation ---
                # When we're searching for a specific episode, verify the release
                # name actually contains that episode (or is a season pack).
                # Trackers like C411/UNIT3D do fuzzy full-text search and may
                # return neighbouring episodes (E5, E6 …) alongside E4.
                if season and episode:
                    try:
                        req_s, req_e = int(season), int(episode)
                        parsed_s, parsed_e = _parse_season_episode(release_name)

                        if parsed_s is not None:
                            if parsed_s != req_s:
                                # Wrong season entirely → skip
                                scraper_logger.debug(
                                    f"[{self.name}] Skip S{parsed_s}E{parsed_e} ≠ S{req_s}E{req_e}: {release_name}"
                                )
                                continue
                            if parsed_e is not None and parsed_e != req_e:
                                # Correct season but wrong episode → skip
                                scraper_logger.debug(
                                    f"[{self.name}] Skip S{parsed_s}E{parsed_e} ≠ S{req_s}E{req_e}: {release_name}"
                                )
                                continue
                            # parsed_e is None → season pack → keep
                        # parsed_s is None → no episode info in name → keep (conservative)

                    except (ValueError, TypeError):
                        pass  # can't validate → keep
                # --------------------------

                # Format display name
                display_name = build_display_name(
                    title=title,
                    year=year,
                    language=language,
                    quality=quality,
                    season=season,
                    episode=episode,
                    raw_language=raw_language
                )
                if not display_name:
                    display_name = release_name

                # Construct magnet link if we have infohash
                magnet_link = f"magnet:?xt=urn:btih:{infohash}"

                result = {
                    "link": magnet_link,
                    "infohash": infohash,
                    "quality": quality,
                    "language": language,
                    "raw_language": raw_language,
                    "source": self.name,
                    "hoster": "Torrent",
                    "size": size_str,
                    "display_name": display_name,
                    "model_type": "torrent"
                }

                if season:
                    result["season"] = str(season)
                if episode:
                    result["episode"] = str(episode)

                results.append(result)

            results.sort(key=quality_sort_key)
            scraper_logger.debug(f"[{self.name}] Found {len(results)} torrents")
            return results

        except Exception as e:
            scraper_logger.error(f"[{self.name}] Error searching Torznab: {e}")
            return []
