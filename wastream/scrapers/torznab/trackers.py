from typing import List, Dict, Optional
from wastream.config.settings import settings
from wastream.scrapers.torznab.base import BaseTorznab

class YggRebornScraper:
    async def search(self, title: str, year: Optional[str] = None, metadata: Optional[Dict] = None,
                     season: Optional[str] = None, episode: Optional[str] = None,
                     config: Optional[Dict] = None) -> List[Dict]:
        if not settings.YGGREBORN_API_KEY or not settings.YGGREBORN_URL:
            return []
        scraper = BaseTorznab("YggReborn", settings.YGGREBORN_URL, settings.YGGREBORN_API_KEY, auth_type="query")
        return await scraper.search(title, year, metadata, season, episode, config)


class Tr4kerScraper:
    async def search(self, title: str, year: Optional[str] = None, metadata: Optional[Dict] = None,
                     season: Optional[str] = None, episode: Optional[str] = None,
                     config: Optional[Dict] = None) -> List[Dict]:
        if not settings.TR4KER_API_KEY or not settings.TR4KER_URL:
            return []
        scraper = BaseTorznab("Tr4ker", settings.TR4KER_URL, settings.TR4KER_API_KEY, auth_type="query")
        return await scraper.search(title, year, metadata, season, episode, config)


class Torr9Scraper:
    async def search(self, title: str, year: Optional[str] = None, metadata: Optional[Dict] = None,
                     season: Optional[str] = None, episode: Optional[str] = None,
                     config: Optional[Dict] = None) -> List[Dict]:
        if not settings.TORR9_API_KEY or not settings.TORR9_URL:
            return []
        scraper = BaseTorznab("Torr9", settings.TORR9_URL, settings.TORR9_API_KEY, auth_type="query")
        return await scraper.search(title, year, metadata, season, episode, config)


class C411Scraper:
    async def search(self, title: str, year: Optional[str] = None, metadata: Optional[Dict] = None,
                     season: Optional[str] = None, episode: Optional[str] = None,
                     config: Optional[Dict] = None) -> List[Dict]:
        if not settings.C411_API_KEY or not settings.C411_URL:
            return []
        scraper = BaseTorznab("C411", settings.C411_URL, settings.C411_API_KEY, auth_type="query")
        return await scraper.search(title, year, metadata, season, episode, config)


yggreborn_scraper = YggRebornScraper()
tr4ker_scraper = Tr4kerScraper()
torr9_scraper = Torr9Scraper()
c411_scraper = C411Scraper()
