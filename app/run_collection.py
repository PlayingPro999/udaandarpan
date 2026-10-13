import json
import sys
from datetime import date, timedelta
from pathlib import Path

from app.browser_scraper import collect_fare_calendar_browser
from app.collector import collect_fares
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


def _ingest_fares(fares):
    inserted_count = 0

    for fare in fares:
        if ingest_fare(fare):
            inserted_count += 1

    return inserted_count


def run_playwright_collection():

    with open(ROUTES_FILE, "r", encoding="utf-8") as file:
        config = json.load(file)

    routes = config["routes"]
    today = date.today()
    total_inserted = 0

    for route in routes:

        origin = route["origin"].upper()
        destination = route["destination"].upper()

        print()
        print("==========================================")
        print(f"          {origin}-{destination}")
        print("==========================================")

        for days, booking_window in BOOKING_WINDOWS.items():

            departure_date = today + timedelta(days=days)

            print(
                f"{booking_window} | "
                f"{departure_date} | Playwright"
            )

            if collection_exists(
                origin,
                destination,
                departure_date,
                "EaseMyTrip",
                booking_window
            ):
                print(
                    f"{booking_window} | "
                    f"{departure_date} | "
                    f"Already collected - skipping"
                )
                continue

            fares = collect_fare_calendar_browser(
                origin=origin,
                destination=destination,
                target_date=departure_date,
                booking_window=booking_window
            )

            if not fares:
                print(
                    f"{booking_window} | "
                    f"{departure_date} | "
                    f"No fares returned"
                )
                continue

            inserted_count = _ingest_fares(fares)

            total_inserted += inserted_count

            print(
                f"{booking_window} | "
                f"{departure_date} | "
                f"Returned: {len(fares)} | "
                f"Inserted: {inserted_count}"
            )

    print()
    print("==========================================")
    print("       PLAYWRIGHT COLLECTION DONE")
    print("==========================================")
    print(f"Total inserted: {total_inserted}")


def run_ignav_collection():

    with open(ROUTES_FILE, "r", encoding="utf-8") as file:
        config = json.load(file)

    routes = config["routes"]
    today = date.today()
    total_inserted = 0

    for route in routes:

        origin = route["origin"].upper()
        destination = route["destination"].upper()

        print()
        print("==========================================")
        print(f"          {origin}-{destination}")
        print("==========================================")

        for days, booking_window in BOOKING_WINDOWS.items():

            departure_date = today + timedelta(days=days)

            print(
                f"{booking_window} | "
                f"{departure_date} | Ignav"
            )

            if collection_exists(
                origin,
                destination,
                departure_date,
                "Ignav",
                booking_window
            ):
                print(
                    f"{booking_window} | "
                    f"{departure_date} | "
                    f"Already collected - skipping"
                )
                continue

            fares = collect_fares(
                origin=origin,
                destination=destination,
                departure_date=departure_date
            )

            for fare in fares:
                fare["booking_window"] = booking_window

            if not fares:
                print(
                    f"{booking_window} | "
                    f"{departure_date} | "
                    f"No fares returned"
                )
                continue

            inserted_count = _ingest_fares(fares)

            total_inserted += inserted_count

            print(
                f"{booking_window} | "
                f"{departure_date} | "
                f"Returned: {len(fares)} | "
                f"Inserted: {inserted_count}"
            )

    print()
    print("==========================================")
    print("          IGNAV COLLECTION DONE")
    print("==========================================")
    print(f"Total inserted: {total_inserted}")


if __name__ == "__main__":

    if len(sys.argv) != 2:

        print("Usage:")
        print("  python -m app.run_collection playwright")
        print("  python -m app.run_collection ignav")

        raise SystemExit(1)

    mode = sys.argv[1].lower()

    if mode == "playwright":

        run_playwright_collection()

    elif mode == "ignav":

        run_ignav_collection()

    else:

        print(f"Unknown collection mode: {mode}")
        print("Use either 'playwright' or 'ignav'.")

        raise SystemExit(1)