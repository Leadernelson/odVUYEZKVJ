import time
from asyncio import sleep
from typing import Optional, List, Dict
from urllib.parse import urlparse

from wastream.config.settings import settings
from wastream.debrid.base import BaseDebridService, HTTP_RETRY_ERRORS
from wastream.services.hoster_status import mark_hoster_down, is_hoster_up, schedule_recheck
from wastream.utils.http_client import http_client
from wastream.utils.logger import debrid_logger, cache_logger
from wastream.utils.quality import quality_sort_key

# ===========================
# AllDebrid Error Constants
# ===========================
RETRY_ERRORS = [
    "LINK_HOST_UNAVAILABLE",
    "LINK_TEMPORARY_UNAVAILABLE",
    "LINK_TOO_MANY_DOWNLOADS",
    "LINK_HOST_FULL",
    "LINK_HOST_LIMIT_REACHED",
    "REDIRECTOR_ERROR",
]

DEAD_LINK_ERRORS = [
    "LINK_PASS_PROTECTED",
]


# ===========================
# AllDebrid Service Class
# ===========================
class AllDebridService(BaseDebridService):
    def get_service_name(self) -> str:
        return "AllDebrid"

    async def check_cache_and_enrich(self, results: List[Dict], api_key: str, config: Dict, timeout_remaining: float, user_season: Optional[str] = None, user_episode: Optional[str] = None, user_hosts: Optional[List[str]] = None) -> List[Dict]:
        start_time = time.time()

        if not api_key or not results:
            for result in results:
                result["cache_status"] = "uncached"
            return results

        supported_hosts = user_hosts if user_hosts else settings.ALLDEBRID_SUPPORTED_HOSTS

        initial_count = len(results)
        filtered_results = []
        for result in results:
            if result.get("model_type") == "nzb":
                continue
            hoster = result.get("hoster", "").lower()
            if any(supported_host in hoster for supported_host in supported_hosts):
                filtered_results.append(result)

        if len(filtered_results) < initial_count:
            debrid_logger.debug(f"[AllDebrid] Filtered: {initial_count} → {len(filtered_results)} links")

        if not filtered_results:
            debrid_logger.debug("[AllDebrid] No supported hosts")
            return []

        # Filter out hosters marked as down (reactive detection)
        before_count = len(filtered_results)
        down_hosters = {}
        kept_results = []
        for r in filtered_results:
            hoster = r.get("hoster", "").lower()
            if is_hoster_up("alldebrid", hoster):
                kept_results.append(r)
            else:
                if hoster and hoster not in down_hosters:
                    down_hosters[hoster] = r.get("link", "")
        filtered_results = kept_results
        if len(filtered_results) < before_count:
            debrid_logger.debug(f"[AllDebrid] Hoster status: {before_count} → {len(filtered_results)}")

        # Background recheck: test one real link per DOWN host
        if down_hosters and config.get("recheck_hoster_status", False):
            for hoster_name, link in down_hosters.items():
                schedule_recheck(link, api_key, hoster_name)
                debrid_logger.debug(f"[AllDebrid] Background recheck scheduled for '{hoster_name}'")

        if not filtered_results:
            debrid_logger.debug("[AllDebrid] No available hosts")
            return []

        results = filtered_results

        for result in results:
            if result.get("model_type") == "torrent":
                result["cache_status"] = "uncached"
            else:
                result["cache_status"] = "cached"

        deduplicate_results = config.get("deduplicate_results", False)

        if deduplicate_results:
            groups = self.group_identical_links(results)
            cached_results = []
            for group_key, group_links in groups.items():
                cached_results.append(group_links[0])
        else:
            cached_results = self.deduplicate_by_exact_link(results)

        cached_results.sort(key=quality_sort_key)

        elapsed = time.time() - start_time
        cache_logger.debug(f"[AllDebrid] Done in {elapsed:.1f}s: {len(cached_results)} results")

        return cached_results

    async def convert_link(self, link: str, api_key: str, season: Optional[str] = None, episode: Optional[str] = None, hoster: Optional[str] = None) -> Optional[str]:
        if not api_key:
            debrid_logger.error("[AllDebrid] Empty API key")
            return None

        debrid_logger.debug("[AllDebrid] Converting link")

        is_direct_link = any(host in link for host in ["1fichier.com", "turbobit.net", "rapidgator.net", "alldebrid.com"])
        http_error_count = 0

        for attempt in range(settings.DEBRID_MAX_RETRIES):
            try:
                if is_direct_link:
                    response1 = await http_client.get(
                        f"{settings.ALLDEBRID_API_URL}/link/unlock",
                        params={"agent": settings.ADDON_NAME, "apikey": api_key, "link": link}
                    )
                else:
                    response1 = await http_client.get(
                        f"{settings.ALLDEBRID_API_URL}/link/redirector",
                        params={"agent": settings.ADDON_NAME, "apikey": api_key, "link": link}
                    )

                should_retry, http_error_count = await self._handle_http_retry_error(
                    response1, http_error_count, "ALLDEBRID",
                    settings.DEBRID_HTTP_ERROR_RETRY_DELAY, settings.DEBRID_HTTP_ERROR_MAX_RETRIES
                )
                if should_retry:
                    continue
                elif response1.status_code in HTTP_RETRY_ERRORS:
                    debrid_logger.error(f"[AllDebrid] Max HTTP retries ({settings.DEBRID_HTTP_ERROR_MAX_RETRIES})")
                    return "RETRY_ERROR"

                http_error_count = 0

                if response1.status_code != 200:
                    debrid_logger.error(f"[AllDebrid] Redirector HTTP {response1.status_code}")
                    if attempt >= settings.DEBRID_MAX_RETRIES - 1:
                        return "FATAL_ERROR"
                    await sleep(settings.DEBRID_RETRY_DELAY_SECONDS)
                    continue

                data1 = response1.json()
                if data1.get("status") != "success":
                    error = data1.get("error", {})
                    error_code = error.get("code")

                    if error_code == "LINK_DOWN":
                        debrid_logger.debug(f"[AllDebrid] {error_code}")
                        return "LINK_DOWN"

                    if error_code in DEAD_LINK_ERRORS:
                        debrid_logger.debug(f"[AllDebrid] {error_code} - link is password-protected (universally undebridable)")
                        return "LINK_DOWN"

                    if error_code == "NO_SERVER":
                        debrid_logger.warning(f"[AllDebrid] NO_SERVER - server blocked by AllDebrid (VPN/datacenter detected)")
                        return "FATAL_ERROR"

                    if error_code in RETRY_ERRORS:
                        if error_code == "LINK_HOST_UNAVAILABLE":
                            hoster_name = hoster if hoster else urlparse(link).netloc.replace("www.", "")
                            mark_hoster_down("alldebrid", hoster_name)
                        debrid_logger.error(f"[AllDebrid] {error_code}")
                        if attempt >= settings.DEBRID_MAX_RETRIES - 1:
                            return "RETRY_ERROR"
                        await sleep(settings.DEBRID_RETRY_DELAY_SECONDS)
                        continue

                    debrid_logger.error(f"[AllDebrid] Fatal: {error_code}")
                    return "FATAL_ERROR"

                if is_direct_link:
                    if "delayed" in data1.get("data", {}):
                        debrid_logger.debug("[AllDebrid] Delayed - uncached")
                        return "LINK_UNCACHED"

                    direct_link = data1.get("data", {}).get("link")
                    if direct_link:
                        debrid_logger.debug("[AllDebrid] Converted")
                        return direct_link
                    else:
                        debrid_logger.error("[AllDebrid] No direct link")
                        await sleep(settings.DEBRID_RETRY_DELAY_SECONDS)
                        continue

                redirected_links = data1.get("data", {}).get("links", [])
                if not redirected_links:
                    debrid_logger.error("[AllDebrid] No redirected links")
                    await sleep(settings.DEBRID_RETRY_DELAY_SECONDS)
                    continue

                first_link = redirected_links[0]
                response2 = await http_client.get(
                    f"{settings.ALLDEBRID_API_URL}/link/unlock",
                    params={"agent": settings.ADDON_NAME, "apikey": api_key, "link": first_link}
                )

                should_retry, http_error_count = await self._handle_http_retry_error(
                    response2, http_error_count, "ALLDEBRID",
                    settings.DEBRID_HTTP_ERROR_RETRY_DELAY, settings.DEBRID_HTTP_ERROR_MAX_RETRIES
                )
                if should_retry:
                    continue
                elif response2.status_code in HTTP_RETRY_ERRORS:
                    debrid_logger.error(f"[AllDebrid] Max HTTP retries ({settings.DEBRID_HTTP_ERROR_MAX_RETRIES})")
                    return "RETRY_ERROR"

                http_error_count = 0

                if response2.status_code != 200:
                    debrid_logger.error(f"[AllDebrid] Unlock HTTP {response2.status_code}")
                    if attempt >= settings.DEBRID_MAX_RETRIES - 1:
                        return "FATAL_ERROR"
                    await sleep(settings.DEBRID_RETRY_DELAY_SECONDS)
                    continue

                data2 = response2.json()
                if data2.get("status") != "success":
                    error = data2.get("error", {})
                    error_code2 = error.get("code")

                    if error_code2 == "LINK_DOWN":
                        debrid_logger.debug(f"[AllDebrid] {error_code2}")
                        return "LINK_DOWN"

                    if error_code2 in DEAD_LINK_ERRORS:
                        debrid_logger.debug(f"[AllDebrid] {error_code2} - link is password-protected (universally undebridable)")
                        return "LINK_DOWN"

                    if error_code2 == "NO_SERVER":
                        debrid_logger.warning(f"[AllDebrid] NO_SERVER - server blocked by AllDebrid (VPN/datacenter detected)")
                        return "FATAL_ERROR"

                    if error_code2 in RETRY_ERRORS:
                        if error_code2 == "LINK_HOST_UNAVAILABLE":
                            hoster_name = hoster if hoster else urlparse(link).netloc.replace("www.", "")
                            mark_hoster_down("alldebrid", hoster_name)
                        debrid_logger.error(f"[AllDebrid] {error_code2}")
                        if attempt >= settings.DEBRID_MAX_RETRIES - 1:
                            return "RETRY_ERROR"
                        await sleep(settings.DEBRID_RETRY_DELAY_SECONDS)
                        continue

                    debrid_logger.error(f"[AllDebrid] Fatal: {error_code2}")
                    return "FATAL_ERROR"

                if "delayed" in data2.get("data", {}):
                    debrid_logger.debug("[AllDebrid] Delayed - uncached")
                    return "LINK_UNCACHED"

                direct_link = data2.get("data", {}).get("link")
                if direct_link:
                    debrid_logger.debug("[AllDebrid] Converted")
                    return direct_link

            except Exception as e:
                debrid_logger.error(f"[AllDebrid] Attempt {attempt + 1} failed: {type(e).__name__}: {e}")
                if attempt < settings.DEBRID_MAX_RETRIES - 1:
                    await sleep(settings.DEBRID_RETRY_DELAY_SECONDS)

        debrid_logger.error(f"[AllDebrid] Failed after {settings.DEBRID_MAX_RETRIES} attempts")
        return "FATAL_ERROR"


# ===========================
# Singleton Instance
# ===========================
alldebrid_service = AllDebridService()
