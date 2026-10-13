import json
import time
from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path

from app.scraper import collect_fare_calendar
from app.ingestion import ingest_fare
from app.repository import collection_exists


BASE_DIR = Path(__file__).resolve().parent.parent
ROUTES_FILE = BASE_DIR / "config" / "routes.json"

BOOKING_WINDOWS = {
    1: "T+1",
    7: "T+7",
    15: "T+15",
    30: "T+30",
    45: "T+45",
}

PAUSE_BETWEEN_ROUTES_SEC = 5


def run_scraping():

    with open(ROUTES_FILE, "r", encoding="utf-8") as file:
        config = json.load(file)

    routes = config["routes"]
    today = date.today()
    target_dates = {today + timedelta(days=d): w for d, w in BOOKING_WINDOWS.items()}

    # FIX: anchor search_timestamp to the same local "today" used to compute
    # target_date above, rather than the scraper's internal datetime.utcnow().
    # UTC lags IST by 5:30, so any run between ~18:30-23:59 IST would have
    # utcnow().date() still on "yesterday", making departure_date minus
    # search_timestamp.date() come out one day higher than intended --
    # e.g. a T+1 target silently computing as a 2-day gap, which doesn't
    # match any entry in normalizer.py's BOOKING_WINDOWS map, so
    # get_booking_window() returns None. Anchoring here guarantees the day
    # count always matches exactly what run_scraping1.py intended,
    # regardless of what time of day (or which timezone) this runs in.
    run_timestamp = datetime.combine(today, dtime.min)

    for route in routes:

        origin = route["origin"]
        destination = route["destination"]

        print()
        print(f"========== [SCRAPED] {origin}-{destination} ==========")

        calendar_rows = collect_fare_calendar(origin, destination, today)
        by_date = {row["departure_date"]: row for row in calendar_rows}

        for target_date, booking_window in target_dates.items():

            if target_date in by_date:
                continue

            print(f"{booking_window} | {target_date} | Not in first calendar window, fetching separately...")

            try:
                extra_rows = collect_fare_calendar(origin, destination, target_date)
            except Exception as e:
                print(f"{booking_window} | {target_date} | Extra fetch failed: {e}")
                continue

            for row in extra_rows:
                by_date.setdefault(row["departure_date"], row)

        for target_date, booking_window in target_dates.items():

            if collection_exists(origin, destination, target_date, "EaseMyTrip", booking_window):
                print(f"{booking_window} | {target_date} | Already collected - skipping")
                continue

            row = by_date.get(target_date)
            if row is None:
                print(f"{booking_window} | {target_date} | No fare in scraped calendar (still missing after retry)")
                continue

            # FIX: overwrite with the anchored timestamp (see comment above)
            # instead of whatever the scraper stamped internally.
            row["search_timestamp"] = run_timestamp

            inserted = ingest_fare(row)
            print(
                f"{booking_window} | {target_date} | "
                f"Fare: Rs.{row['fare']:.0f} ({row['airline']}) | "
                f"Inserted: {inserted}"
            )

        time.sleep(PAUSE_BETWEEN_ROUTES_SEC)


if __name__ == "__main__":
    run_scraping()