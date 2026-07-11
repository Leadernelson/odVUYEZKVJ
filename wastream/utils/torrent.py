import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any

from wastream.utils.languages import LANGUAGE_MAPPING
from wastream.utils.quality import normalize_quality, quality_sort_key

# ==============================================================================
# Regular Expressions for Season & Episode Parsing
# ==============================================================================
# Matches standard format S01E02, S1.E2, S01 E02, s1e2, etc.
# Capture groups: (1) Season number, (2) Episode number
SXEX_RE = re.compile(r'[Ss](\d{1,2})[.\s]?[Ee](\d{1,3})', re.IGNORECASE)

# Matches alternative format 1x02, 01x02 (often seen in older releases)
# Capture groups: (1) Season number, (2) Episode number
ALT_EP_RE = re.compile(r'(?<!\d)(\d{1,2})[x](\d{1,3})(?!\d)', re.IGNORECASE)

# Matches season-only pack identifiers (e.g. S01, Season 1) not followed by an episode indicator
# Capture groups: (1) Season number
SEASON_ONLY_RE = re.compile(r'[Ss](\d{1,2})(?![.\s]?[Ee])', re.IGNORECASE)

@dataclass
class ParsedTorrent:
    """
    Data container representing the structured metadata extracted from a raw torrent release name.
    
    Attributes:
        raw_title (str): The original unparsed filename or release title.
        season (Optional[int]): The parsed season number, if identified.
        episode (Optional[int]): The parsed episode number, if identified.
        resolution (str): The video resolution (e.g., '2160p', '1080p', '720p', '480p'). Defaults to 'Unknown'.
        release_type (str): The media source/rip type (e.g., 'REMUX', 'BluRay', 'WEB-DL', 'WEBRip'). Defaults to 'Unknown'.
        quality (str): Normalized string combining resolution and release type. Defaults to 'Unknown'.
        language (str): Normalized standard language name (e.g., 'French', 'English'). Defaults to 'Unknown'.
        raw_language (str): Original parsed language token from filename (e.g., 'VOSTFR', 'VFF'). Defaults to 'Unknown'.
    """
    raw_title: str
    season: Optional[int] = None
    episode: Optional[int] = None
    resolution: str = "Unknown"
    release_type: str = "Unknown"
    quality: str = "Unknown"
    language: str = "Unknown"
    raw_language: str = "Unknown"

    @property
    def is_season_pack(self) -> bool:
        """
        Helper property that checks if the torrent represents an entire season rather than a single episode.
        
        Returns:
            bool: True if a season is defined but no specific episode is defined; False otherwise.
        """
        return self.season is not None and self.episode is None


class TorrentParser:
    """
    Utility class implementing parsing logic to clean and extract metadata attributes from torrent filenames.
    """
    @staticmethod
    def tokenize(filename: str) -> List[str]:
        """
        Splits a torrent filename into lower-cased keyword tokens by removing file extension
        and split separators like dots, dashes, underscores, and brackets.
        
        Args:
            filename (str): The file or torrent name to tokenize.
            
        Returns:
            List[str]: Cleaned list of lowercase tokens.
        """
        # Strip trailing extension (.mkv, .mp4, etc.)
        name_no_ext = re.sub(r"\.\w{2,4}$", "", filename)
        # Split on characters: dot, space, dash, underscore, brackets, parenthesis
        tokens = re.split(r"[\.\s\-_\(\)\[\]]+", name_no_ext)
        return [t.lower() for t in tokens if t]

    @classmethod
    def parse(cls, filename: str) -> ParsedTorrent:
        """
        Parses a torrent filename and returns a ParsedTorrent containing metadata.
        
        Args:
            filename (str): The raw release name to parse.
            
        Returns:
            ParsedTorrent: Extracted metadata containing season, episode, quality, and languages.
        """
        tokens = cls.tokenize(filename)
        
        # 1. Parse Season and Episode metadata using regex patterns
        season, episode = None, None
        m = SXEX_RE.search(filename)
        if m:
            season, episode = int(m.group(1)), int(m.group(2))
        else:
            m = ALT_EP_RE.search(filename)
            if m:
                season, episode = int(m.group(1)), int(m.group(2))
            else:
                m = SEASON_ONLY_RE.search(filename)
                if m:
                    season = int(m.group(1))

        # 2. Parse Resolution and Release Type from tokens
        resolution = ""
        release_type = ""
        for token in tokens:
            if not resolution:
                if "2160p" in token or "4k" == token or "uhd" == token or "ultra" == token:
                    resolution = "2160p"
                elif "1080p" in token or "1080" == token or "hd" == token:
                    resolution = "1080p"
                elif "720p" in token or "720" == token:
                    resolution = "720p"
                elif "480p" in token or "480" == token:
                    resolution = "480p"

            if not release_type:
                token_upper = token.upper()
                if token_upper == "REMUX":
                    release_type = "REMUX"
                elif token_upper in ("BLURAY", "BDRIP", "BRRIP"):
                    release_type = "BluRay"
                elif token_upper == "WEBDL":
                    release_type = "WEB-DL"
                elif token_upper == "WEBRIP":
                    release_type = "WEBRip"
                elif token_upper == "HDLIGHT":
                    release_type = "HDLight"
                elif token_upper == "HDRIP":
                    release_type = "HDRip"
                elif token_upper == "HDTV":
                    release_type = "HDTV"
                elif token_upper == "DVDRIP":
                    release_type = "DVDRip"
                elif token_upper == "TVRIP":
                    release_type = "TVRip"

        resolution = resolution or "Unknown"
        release_type = release_type or "Unknown"
        
        # Combine resolution and release type to normalize quality representation
        if resolution != "Unknown" and release_type != "Unknown":
            raw_quality = f"{resolution} {release_type}"
        elif resolution != "Unknown":
            raw_quality = resolution
        elif release_type != "Unknown":
            raw_quality = release_type
        else:
            raw_quality = "Unknown"
            
        quality_normalized = normalize_quality(raw_quality)

        # 3. Parse Language using LANGUAGE_MAPPING lookups
        language = "Unknown"
        raw_language = "Unknown"
        for token in tokens:
            mapped = LANGUAGE_MAPPING.get(token)
            if mapped and mapped != "Unknown":
                language = mapped
                raw_language = token.upper()
                break

        return ParsedTorrent(
            raw_title=filename,
            season=season,
            episode=episode,
            resolution=resolution,
            release_type=release_type,
            quality=quality_normalized,
            language=language,
            raw_language=raw_language
        )


class TorrentRanker:
    """
    Responsible for generating comprehensive sorting profiles/keys for search results
    based on the parsed torrent metadata and user preferences.
    """
    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the ranker with configuration parameters.
        
        Args:
            config (Dict[str, Any]): Dictionary of configuration keys (e.g. prioritize_vff_multi, stream_type_preference).
        """
        self.config = config

    def get_sort_values(self, result: Dict[str, Any], parsed: ParsedTorrent, cache_status: str, size_bytes: int) -> Dict[str, Any]:
        """
        Computes a mapping of sorting values used by StreamService to compare streams.
        
        Args:
            result (Dict[str, Any]): Raw result mapping from scrapers.
            parsed (ParsedTorrent): Pre-parsed metadata for this stream item.
            cache_status (str): Cache state, either "cached" or "uncached".
            size_bytes (int): Total size of the file in bytes.
            
        Returns:
            Dict[str, Any]: Sort weights for caching, resolution, size, release type, language, and stream type.
        """
        # 1. Cached status priority: cached (0) takes precedence over uncached (1)
        cached_val = 0 if cache_status == "cached" else 1

        # 2. Quality priorities (returns a tuple sorting resolution & release type)
        q_key = quality_sort_key({"quality": parsed.quality})

        # 3. Language priority (identified language is prioritized over unknown)
        lang_priority = 0 if parsed.language != "Unknown" else 1

        # 4. French Audio vs VOSTFR sub-priority
        # Prioritizes VFF/MULTI audio over VOSTFR subtitles if configured by user
        french_sub_priority = 0
        if self.config.get("prioritize_vff_multi", False) and parsed.language == "French":
            display_name = result.get("display_name") or parsed.raw_title
            display_name_upper = display_name.upper()
            is_vostfr = any(tag in display_name_upper for tag in ["VOSTFR", "SUBFRENCH", "SUBFR", ".SUB."])
            is_audio = any(tag in display_name_upper for tag in ["VFF", "MULTI", "VF", "TRUEFRENCH"])
            if is_audio and not is_vostfr:
                french_sub_priority = 0
            elif is_vostfr:
                french_sub_priority = 1

        # 5. Stream type priority
        # Determines direct downloads/links vs torrent stream type ordering preference
        is_torrent = (result.get("model_type") == "torrent")
        pref = self.config.get("stream_type_preference", "ddl_first")
        if pref == "torrent_first":
            stream_type_priority = 0 if is_torrent else 1
        else:
            stream_type_priority = 1 if is_torrent else 0

        return {
            "cached": cached_val,
            "resolution": q_key[0],
            "size": -size_bytes, # Negative value allows ascending sorts to sort descending by size
            "release_type": q_key[1],
            "language": (lang_priority, french_sub_priority, parsed.language),
            "stream_type": stream_type_priority,
        }

