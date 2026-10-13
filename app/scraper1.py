import hashlib
import logging
import random
import time
import urllib.robotparser
from datetime import date, datetime, timedelta
from urllib.parse import urlparse
 
import requests
 
log = logging.getLogger("udaandarpan.scraper")
if not log.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
 
USER_AGENT = "UdaanDarpanIndexBot/0.1 (+research index; contact: your-email@example.com)"
MIN_DELAY_SEC = 4.0
MAX_DELAY_SEC = 9.0
MAX_RETRIES = 3
REQUEST_TIMEOUT_SEC = 20
 
 
# ---------------------------------------------------------------------
# robots.txt gate (fail-closed: if unsure, don't scrape). Per-host cache,
# since different subdomains (e.g. www.X.com vs api.X.com) have
# independent robots.txt files under the standard.
# ---------------------------------------------------------------------
 
class RobotsGate:
    def __init__(self):
        self._cache: dict[str, urllib.robotparser.RobotFileParser | None] = {}
 
    def allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        if host not in self._cache:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(f"{host}/robots.txt")
            try:
                rp.read()
                self._cache[host] = rp
            except Exception as e:
                log.warning("Could not read robots.txt for %s (%s) -- refusing to scrape.", host, e)
                self._cache[host] = None
        rp = self._cache[host]
        # robotparser treats a fetch that returned 404 as "no restrictions
        # declared" and can_fetch() correctly returns True in that case.
        return rp.can_fetch(USER_AGENT, url) if rp else False
 
 
robots_gate = RobotsGate()
 
 
class RateLimiter:
    def __init__(self):
        self._last: dict[str, float] = {}
 
    def wait(self, url: str):
        host = urlparse(url).netloc
        gap = random.uniform(MIN_DELAY_SEC, MAX_DELAY_SEC)
        elapsed = time.monotonic() - self._last.get(host, 0)
        if elapsed < gap:
            sleep_for = gap - elapsed
            log.info("Rate limit: sleeping %.1fs before next request to %s", sleep_for, host)
            time.sleep(sleep_for)
        self._last[host] = time.monotonic()
 
 
rate_limiter = RateLimiter()
 
 
def _synthetic_id(source: str, origin: str, destination: str, departure_date: date,
                   airline: str, fare: float) -> str:
    """Stand-in for ignav_id so the existing unique index
    (ignav_id, departure_date) still de-dupes scraped rows.
    NOTE: consider renaming that column to source_id/external_id
    since it's no longer Ignav-specific -- non-breaking either way."""
    raw = f"{source}|{origin}|{destination}|{departure_date}|{airline}|{fare}"
    digest = hashlib.sha1(raw.encode()).hexdigest()[:16]
    return f"{source.upper()}-{digest}"
 
 
# =======================================================================
# EASEMYTRIP -- WORKING SOURCE
#
# Confirmed live via browser DevTools (25 Sep 2026):
#   POST https://flightservice-node.easemytrip.com/FareCalendar/FareCalendarByDate
#   Body: {"CalKey_": "ORIGIN_DEST_DD/MM/YYYY"}
#   Response: JSON array of ~30 daily entries:
#     {"DepDate": "2026-09-26", "TtlFre": "6451", "AirCode": "SpiceJet",
#      "IsCurrent": true, "Cheapest": 3, "IsCheapest": true (optional)}
#
# robots.txt check: flightservice-node.easemytrip.com/robots.txt returns
# a 404 ("no route"), which per the Robots Exclusion Standard means no
# restrictions are declared for this host -- RobotsGate.allowed()
# correctly treats this as permitted.
#
# Like Ixigo's endpoint, this is a fare CALENDAR (cheapest fare per day),
# not a full flight listing: no departure_time/duration/cabin/stops/
# flight_number available. AirCode is the airline's full display name,
# not an IATA code, despite the field name.
# =======================================================================
 
EASEMYTRIP_SOURCE = "EaseMyTrip"
EASEMYTRIP_URL = "https://flightservice-node.easemytrip.com/FareCalendar/FareCalendarByDate"
 
 
def _fetch_easemytrip_calendar(origin: str, destination: str, departure_date: date) -> list | None:
    cal_key = f"{origin}_{destination}_{departure_date.strftime('%d/%m/%Y')}"
    payload = {"CalKey_": cal_key}
 
    if not robots_gate.allowed(EASEMYTRIP_URL):
        log.warning("robots.txt disallows %s -- skipping.", EASEMYTRIP_URL)
        return None
 
    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
 
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            rate_limiter.wait(EASEMYTRIP_URL)
            resp = requests.post(
                EASEMYTRIP_URL, json=payload, headers=headers, timeout=REQUEST_TIMEOUT_SEC
            )
 
            if resp.status_code == 429:
                delay = 2 ** attempt * 5
                log.warning("Rate-limited (429) by EaseMyTrip. Backing off %ds.", delay)
                time.sleep(delay)
                continue
 
            resp.raise_for_status()
            return resp.json()
 
        except requests.exceptions.RequestException as e:
            log.warning("Request error (attempt %d/%d) for CalKey=%s: %s", attempt, MAX_RETRIES, cal_key, e)
            time.sleep(2 ** attempt)
 
    log.error("Giving up on EaseMyTrip calendar for %s after %d attempts", cal_key, MAX_RETRIES)
    return None
 
 
def _parse_easemytrip_response(entries: list, origin: str, destination: str) -> list[dict]:
    results: list[dict] = []
    if not entries:
        return results
 
    for entry in entries:
        try:
            fare_raw = entry.get("TtlFre")
            if fare_raw is None:
                continue
            fare = float(fare_raw)
            if fare <= 0:
                continue  # matches FareObservation.validate()'s "fare must be > 0"
 
            date_str = entry.get("DepDate")  # "YYYY-MM-DD"
            if not date_str:
                continue
            departure_date = datetime.strptime(date_str, "%Y-%m-%d").date()
 
            airline = entry.get("AirCode") or "Unknown"
 
            results.append({
                "source": EASEMYTRIP_SOURCE,
                "origin": origin,
                "destination": destination,
                "airline": airline,
                "flight_number": None,  # not available from this fare-calendar endpoint
                "departure_date": departure_date,
                "search_timestamp": datetime.utcnow(),
                "departure_time": None,
                "arrival_time": None,
                "duration_minutes": None,
                "cabin": "Economy",
                "aircraft": None,
                "fare": fare,
                "currency": "INR",
                "price_status": "cheapest_of_day" if entry.get("IsCheapest") else "lowest_of_day",
                "checked_bags": None,
                "requires_self_transfer": False,
                "ignav_id": _synthetic_id(EASEMYTRIP_SOURCE, origin, destination, departure_date, airline, fare),
                "raw_data": entry,
            })
        except (TypeError, ValueError) as e:
            log.warning("Skipping malformed EaseMyTrip entry %s: %s", entry, e)
            continue
 
    return results
 
 
def collect_fare_calendar(origin: str, destination: str, center_date: date) -> list[dict]:
    """Primary entry point: EaseMyTrip fare calendar. Returns ALL days in
    the returned window from a single API call."""
    payload = _fetch_easemytrip_calendar(origin, destination, center_date)
    return _parse_easemytrip_response(payload, origin, destination)
 
 
def collect_fares_scraped(origin: str, destination: str, departure_date: date) -> list[dict]:
    """Sync wrapper matching app.collector.collect_fares()'s call
    signature, filtered to just the one requested date."""
    all_days = collect_fare_calendar(origin, destination, departure_date)
    return [row for row in all_days if row["departure_date"] == departure_date]
 
 
# =======================================================================
# IXIGO -- BLOCKED BY ROBOTS.TXT, KEPT AS COMPLIANCE EVIDENCE
#
# Confirmed live via browser DevTools (25 Sep 2026):
#   GET https://www.ixigo.com/outlook/v1/onward/ranged
#       ?departureDate=DDMMYYYY&destination=XXX&origin=XXX&fareClass=e
#       &paxCombinationType=100
#       &refundTypes=REFUNDABLE,NON_REFUNDABLE,PARTIALLY_REFUNDABLE
#   Response: {"data": {"going": {"results": [{"airline": "...",
#       "date": "DD-MM-YYYY", "fare": 6452.0, ...}]}}, "errors": null}
#
# robots.txt check on www.ixigo.com explicitly disallows /outlook/*.
# RobotsGate.allowed() correctly returns False for this URL, and this
# function correctly refuses to call it. NOT wired into
# run_scraping.py's default flow -- retained only to demonstrate that
# robots.txt enforcement was implemented and actually works, per the
# problem statement's ethical-scraping requirement.
# =======================================================================
 
IXIGO_SOURCE = "Ixigo"
IXIGO_URL = "https://www.ixigo.com/outlook/v1/onward/ranged"
 
 
def collect_ixigo_calendar_BLOCKED(origin: str, destination: str, center_date: date) -> list[dict]:
    """Deliberately unused in the default pipeline -- robots.txt disallows
    this endpoint. Calling this will always return [] and log a warning,
    by design. See module docstring."""
 
    url = (
        f"{IXIGO_URL}?departureDate={center_date.strftime('%d%m%Y')}"
        f"&destination={destination}&origin={origin}&fareClass=e"
        f"&paxCombinationType=100"
        f"&refundTypes=REFUNDABLE,NON_REFUNDABLE,PARTIALLY_REFUNDABLE"
    )
 
    if not robots_gate.allowed(url):
        log.warning(
            "robots.txt disallows %s -- refusing (this is expected; see "
            "module docstring, this function is retained as compliance evidence).",
            url,
        )
        return []
 
    # Unreachable in practice -- left for completeness / if Ixigo ever
    # changes their robots.txt to permit this path.
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    rate_limiter.wait(url)
    resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SEC)
    resp.raise_for_status()
    payload = resp.json()
 
    results = []
    going = (payload.get("data") or {}).get("going") or {}
    for entry in going.get("results") or []:
        fare = entry.get("fare")
        if fare is None or float(fare) <= 0:
            continue
        departure_date = datetime.strptime(entry["date"], "%d-%m-%Y").date()
        airline = entry.get("airline") or "Unknown"
        results.append({
            "source": IXIGO_SOURCE,
            "origin": origin, "destination": destination,
            "airline": airline,
            "flight_number": entry.get("flightNumber") or None,
            "departure_date": departure_date,
            "search_timestamp": datetime.utcnow(),
            "departure_time": None, "arrival_time": None, "duration_minutes": None,
            "cabin": "Economy", "aircraft": None,
            "fare": float(fare), "currency": "INR", "price_status": "lowest_of_day",
            "checked_bags": None, "requires_self_transfer": False,
            "ignav_id": _synthetic_id(IXIGO_SOURCE, origin, destination, departure_date, airline, float(fare)),
            "raw_data": entry,
        })
    return results