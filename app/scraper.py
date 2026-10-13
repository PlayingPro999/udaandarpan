import hashlib
import logging
import random
import time
import urllib.robotparser
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests


log = logging.getLogger("udaandarpan.scraper")

if not log.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )


USER_AGENT = "UdaanDarpanIndexBot/0.1 (+research index; contact: your-email@example.com)"

MIN_DELAY_SEC = 4.0
MAX_DELAY_SEC = 9.0
MAX_RETRIES = 3
REQUEST_TIMEOUT_SEC = 20

COMPLIANCE_LOG = "logs/scraping_compliance.log"


# ---------------------------------------------------------------------
# Compliance logger
#
# Records the robots.txt decision before every source request.
# This gives the hackathon judges an auditable record showing whether
# a source was allowed or blocked before the HTTP request was made.
# ---------------------------------------------------------------------

def log_compliance(
    source: str,
    url: str,
    robots_allowed: bool,
    action: str
):
    Path(COMPLIANCE_LOG).parent.mkdir(
        parents=True,
        exist_ok=True
    )

    status = "ALLOWED" if robots_allowed else "DISALLOWED"

    line = (
        f"{datetime.now(timezone.utc).isoformat()} | "
        f"SOURCE={source} | "
        f"ROBOTS={status} | "
        f"URL={url} | "
        f"ACTION={action}\n"
    )

    with open(
        COMPLIANCE_LOG,
        "a",
        encoding="utf-8"
    ) as file:
        file.write(line)

    log.info(line.strip())


# ---------------------------------------------------------------------
# robots.txt gate (fail-closed: if unsure, don't scrape).
#
# Per-host cache is used because different subdomains can have
# independent robots.txt files.
# ---------------------------------------------------------------------

class RobotsGate:

    def __init__(self):
        self._cache: dict[
            str,
            urllib.robotparser.RobotFileParser | None
        ] = {}

    def allowed(self, url: str) -> bool:

        parsed = urlparse(url)

        host = (
            f"{parsed.scheme}://"
            f"{parsed.netloc}"
        )

        if host not in self._cache:

            rp = urllib.robotparser.RobotFileParser()

            rp.set_url(
                f"{host}/robots.txt"
            )

            try:
                rp.read()

                self._cache[host] = rp

            except Exception as e:

                log.warning(
                    "Could not read robots.txt for %s (%s) "
                    "-- refusing to scrape.",
                    host,
                    e
                )

                self._cache[host] = None

        rp = self._cache[host]

        # robotparser treats a fetch that returned 404 as
        # "no restrictions declared" and can_fetch() correctly
        # returns True in that case.
        return (
            rp.can_fetch(USER_AGENT, url)
            if rp
            else False
        )


robots_gate = RobotsGate()


# ---------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------

class RateLimiter:

    def __init__(self):
        self._last: dict[str, float] = {}

    def wait(self, url: str):

        host = urlparse(url).netloc

        gap = random.uniform(
            MIN_DELAY_SEC,
            MAX_DELAY_SEC
        )

        elapsed = (
            time.monotonic()
            - self._last.get(host, 0)
        )

        if elapsed < gap:

            sleep_for = gap - elapsed

            log.info(
                "Rate limit: sleeping %.1fs "
                "before next request to %s",
                sleep_for,
                host
            )

            time.sleep(sleep_for)

        self._last[host] = time.monotonic()


rate_limiter = RateLimiter()


# ---------------------------------------------------------------------
# Synthetic ID
# ---------------------------------------------------------------------

def _synthetic_id(
    source: str,
    origin: str,
    destination: str,
    departure_date: date,
    airline: str,
    fare: float
) -> str:

    """
    Stand-in for ignav_id so the existing unique index
    (ignav_id, departure_date) still de-dupes scraped rows.

    NOTE:
    This column is currently named ignav_id for backward compatibility.
    It can later be renamed to source_id/external_id.
    """

    raw = (
        f"{source}|"
        f"{origin}|"
        f"{destination}|"
        f"{departure_date}|"
        f"{airline}|"
        f"{fare}"
    )

    digest = hashlib.sha1(
        raw.encode()
    ).hexdigest()[:16]

    return (
        f"{source.upper()}-"
        f"{digest}"
    )


# =======================================================================
# EASEMYTRIP -- WORKING SOURCE
#
# Confirmed live via browser DevTools:
#
# POST
# https://flightservice-node.easemytrip.com/FareCalendar/FareCalendarByDate
#
# Body:
# {"CalKey_": "ORIGIN_DEST_DD/MM/YYYY"}
#
# Response:
# JSON array of daily fare-calendar entries.
#
# robots.txt:
# flightservice-node.easemytrip.com/robots.txt returns 404.
# Therefore no restrictions are declared for this host.
#
# This is a fare calendar, not a complete flight listing.
# =======================================================================

EASEMYTRIP_SOURCE = "EaseMyTrip"

EASEMYTRIP_URL = (
    "https://flightservice-node.easemytrip.com/"
    "FareCalendar/FareCalendarByDate"
)


def _fetch_easemytrip_calendar(
    origin: str,
    destination: str,
    departure_date: date
) -> list | None:

    cal_key = (
        f"{origin}_"
        f"{destination}_"
        f"{departure_date.strftime('%d/%m/%Y')}"
    )

    payload = {
        "CalKey_": cal_key
    }

    # -------------------------------------------------------------
    # robots.txt decision MUST happen before the HTTP request.
    # -------------------------------------------------------------

    allowed = robots_gate.allowed(
        EASEMYTRIP_URL
    )

    log_compliance(
        EASEMYTRIP_SOURCE,
        EASEMYTRIP_URL,
        allowed,
        (
            "REQUEST_ALLOWED"
            if allowed
            else "REQUEST_BLOCKED"
        )
    )

    if not allowed:

        log.warning(
            "robots.txt disallows %s -- skipping.",
            EASEMYTRIP_URL
        )

        return None

    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            rate_limiter.wait(
                EASEMYTRIP_URL
            )

            resp = requests.post(
                EASEMYTRIP_URL,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SEC
            )

            if resp.status_code == 429:

                delay = (
                    2 ** attempt
                ) * 5

                log.warning(
                    "Rate-limited (429) by "
                    "EaseMyTrip. Backing off %ds.",
                    delay
                )

                time.sleep(delay)

                continue

            resp.raise_for_status()

            return resp.json()

        except requests.exceptions.RequestException as e:

            log.warning(
                "Request error (attempt %d/%d) "
                "for CalKey=%s: %s",
                attempt,
                MAX_RETRIES,
                cal_key,
                e
            )

            time.sleep(
                2 ** attempt
            )

    log.error(
        "Giving up on EaseMyTrip calendar "
        "for %s after %d attempts",
        cal_key,
        MAX_RETRIES
    )

    return None


def _parse_easemytrip_response(
    entries: list,
    origin: str,
    destination: str
) -> list[dict]:

    results: list[dict] = []

    if not entries:
        return results

    for entry in entries:

        try:

            fare_raw = entry.get(
                "TtlFre"
            )

            if fare_raw is None:
                continue

            fare = float(
                fare_raw
            )

            if fare <= 0:
                continue

            date_str = entry.get(
                "DepDate"
            )

            if not date_str:
                continue

            departure_date = datetime.strptime(
                date_str,
                "%Y-%m-%d"
            ).date()

            airline = (
                entry.get("AirCode")
                or "Unknown"
            )

            results.append({

                "source":
                    EASEMYTRIP_SOURCE,

                "origin":
                    origin,

                "destination":
                    destination,

                "airline":
                    airline,

                "flight_number":
                    None,

                "departure_date":
                    departure_date,

                "search_timestamp":
                    datetime.utcnow(),

                "departure_time":
                    None,

                "arrival_time":
                    None,

                "duration_minutes":
                    None,

                "cabin":
                    "Economy",

                "aircraft":
                    None,

                "fare":
                    fare,

                "currency":
                    "INR",

                "price_status":
                    (
                        "cheapest_of_day"
                        if entry.get("IsCheapest")
                        else "lowest_of_day"
                    ),

                "checked_bags":
                    None,

                "requires_self_transfer":
                    False,

                "ignav_id":
                    _synthetic_id(
                        EASEMYTRIP_SOURCE,
                        origin,
                        destination,
                        departure_date,
                        airline,
                        fare
                    ),

                "raw_data":
                    entry,
            })

        except (
            TypeError,
            ValueError
        ) as e:

            log.warning(
                "Skipping malformed "
                "EaseMyTrip entry %s: %s",
                entry,
                e
            )

            continue

    return results


def collect_fare_calendar(
    origin: str,
    destination: str,
    center_date: date
) -> list[dict]:

    """
    Primary entry point:
    EaseMyTrip fare calendar.

    Returns all days in the returned window
    from a single API call.
    """

    payload = _fetch_easemytrip_calendar(
        origin,
        destination,
        center_date
    )

    return _parse_easemytrip_response(
        payload,
        origin,
        destination
    )


def collect_fares_scraped(
    origin: str,
    destination: str,
    departure_date: date
) -> list[dict]:

    """
    Sync wrapper matching
    app.collector.collect_fares()
    call signature.

    Filters the calendar to the requested date.
    """

    all_days = collect_fare_calendar(
        origin,
        destination,
        departure_date
    )

    return [
        row
        for row in all_days
        if row["departure_date"]
        == departure_date
    ]


# =======================================================================
# IXIGO -- BLOCKED BY ROBOTS.TXT
#
# Kept as compliance evidence.
#
# robots.txt on www.ixigo.com explicitly disallows:
# /outlook/*
#
# Therefore the scraper checks robots.txt and refuses the request.
#
# This function is NOT part of the normal scraping pipeline.
# =======================================================================

IXIGO_SOURCE = "Ixigo"

IXIGO_URL = (
    "https://www.ixigo.com/"
    "outlook/v1/onward/ranged"
)


def collect_ixigo_calendar_BLOCKED(
    origin: str,
    destination: str,
    center_date: date
) -> list[dict]:

    """
    Deliberately unused in the default pipeline.

    robots.txt disallows this endpoint.

    Calling this function will return [] and record
    the robots.txt compliance decision.
    """

    url = (
        f"{IXIGO_URL}"
        f"?departureDate="
        f"{center_date.strftime('%d%m%Y')}"
        f"&destination={destination}"
        f"&origin={origin}"
        f"&fareClass=e"
        f"&paxCombinationType=100"
        f"&refundTypes="
        f"REFUNDABLE,"
        f"NON_REFUNDABLE,"
        f"PARTIALLY_REFUNDABLE"
    )

    # -------------------------------------------------------------
    # robots.txt decision MUST happen before requests.get().
    # -------------------------------------------------------------

    allowed = robots_gate.allowed(
        url
    )

    log_compliance(
        IXIGO_SOURCE,
        url,
        allowed,
        (
            "REQUEST_ALLOWED"
            if allowed
            else "REQUEST_BLOCKED"
        )
    )

    if not allowed:

        log.warning(
            "robots.txt disallows %s -- refusing "
            "(this is expected; this function is "
            "retained as compliance evidence).",
            url
        )

        return []

    # -------------------------------------------------------------
    # Unreachable while Ixigo disallows this path.
    #
    # Left here only in case Ixigo changes its robots.txt policy
    # in the future.
    # -------------------------------------------------------------

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json"
    }

    rate_limiter.wait(
        url
    )

    resp = requests.get(
        url,
        headers=headers,
        timeout=REQUEST_TIMEOUT_SEC
    )

    resp.raise_for_status()

    payload = resp.json()

    results = []

    going = (
        (payload.get("data") or {})
        .get("going")
        or {}
    )

    for entry in (
        going.get("results")
        or []
    ):

        fare = entry.get(
            "fare"
        )

        if fare is None:
            continue

        if float(fare) <= 0:
            continue

        departure_date = datetime.strptime(
            entry["date"],
            "%d-%m-%Y"
        ).date()

        airline = (
            entry.get("airline")
            or "Unknown"
        )

        results.append({

            "source":
                IXIGO_SOURCE,

            "origin":
                origin,

            "destination":
                destination,

            "airline":
                airline,

            "flight_number":
                entry.get(
                    "flightNumber"
                ) or None,

            "departure_date":
                departure_date,

            "search_timestamp":
                datetime.utcnow(),

            "departure_time":
                None,

            "arrival_time":
                None,

            "duration_minutes":
                None,

            "cabin":
                "Economy",

            "aircraft":
                None,

            "fare":
                float(fare),

            "currency":
                "INR",

            "price_status":
                "lowest_of_day",

            "checked_bags":
                None,

            "requires_self_transfer":
                False,

            "ignav_id":
                _synthetic_id(
                    IXIGO_SOURCE,
                    origin,
                    destination,
                    departure_date,
                    airline,
                    float(fare)
                ),

            "raw_data":
                entry,
        })

    return results