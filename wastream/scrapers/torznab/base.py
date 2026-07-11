import xml.etree.ElementTree as ET
import urllib.parse
import re
from typing import List, Dict, Optional, Tuple

from wastream.utils.http_client import http_client
from wastream.utils.logger import scraper_logger
from wastream.utils.helpers import (
    build_display_name, normalize_size, normalize_tracker_url
)
from wastream.utils.quality import quality_sort_key
from wastream.utils.torrent import TorrentParser



class BaseTorznab:
    """
    Scraper implementation for querying Torznab-compatible indexers and trackers.
    Resolves searches by querying XML feeds, parsing custom metadata attributes,
    and validating results against the new TorrentParser.
    """
    def __init__(self, name: str, url: str, api_key: str, auth_type: str = "query"):
        self.name = name
        self.url = normalize_tracker_url(name, url)
        self.api_key = api_key
        self.auth_type = auth_type  # "query" or "header"

    async def search(self, title: str, year: Optional[str] = None, metadata: Optional[Dict] = None,
                     season: Optional[str] = None, episode: Optional[str] = None,
                     config: Optional[Dict] = None) -> List[Dict]:
        """
        Executes a search query against the configured Torznab indexer.
        
        Args:
            title (str): Title of the movie, series, or anime.
            year (Optional[str]): Production or release year.
            metadata (Optional[Dict]): Additional metadata context.
            season (Optional[str]): Season number for TV show queries.
            episode (Optional[str]): Episode number for TV show queries.
            config (Optional[Dict]): Settings dictionary for filters and preferences.
            
        Returns:
            List[Dict]: List of parsed torrent dictionaries containing magnet links, size, quality, and languages.
        """
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
                parsed = TorrentParser.parse(release_name)
                quality = parsed.quality
                language = parsed.language
                raw_language = parsed.raw_language

                # --- Episode validation ---
                # When we're searching for a specific episode, verify the release
                # name actually contains that episode (or is a season pack).
                # Trackers like C411/UNIT3D do fuzzy full-text search and may
                # return neighbouring episodes (E5, E6 …) alongside E4.
                if season and episode:
                    try:
                        req_s, req_e = int(season), int(episode)
                        if parsed.season is not None:
                            if parsed.season != req_s:
                                # Wrong season entirely → skip
                                scraper_logger.debug(
                                    f"[{self.name}] Skip S{parsed.season}E{parsed.episode} ≠ S{req_s}E{req_e}: {release_name}"
                                )
                                continue
                            if parsed.episode is not None and parsed.episode != req_e:
                                # Correct season but wrong episode → skip
                                scraper_logger.debug(
                                    f"[{self.name}] Skip S{parsed.season}E{parsed.episode} ≠ S{req_s}E{req_e}: {release_name}"
                                )
                                continue
                            # parsed.episode is None → season pack → keep
                        # parsed.season is None → no episode info in name → keep (conservative)

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
