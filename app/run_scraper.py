import json
import time
from datetime import date, timedelta
from pathlib import Path

# Existing HTTP scraper — KEEP IT
from app.scraper import collect_fare_calendar

# New Playwright scraper
from app.browser_scraper import collect_fare_calendar_browser

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

    with open(
        ROUTES_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        config = json.load(file)

    routes = config["routes"]

    today = date.today()

    target_dates = {
        today + timedelta(days=days): booking_window
        for days, booking_window in BOOKING_WINDOWS.items()
    }

    total_inserted = 0

    # ==========================================================
    # 15 ROUTES
    # ==========================================================

    for route in routes:

        origin = route["origin"]
        destination = route["destination"]

        print()
        print(
            "=================================================="
        )
        print(
            f"ROUTE: {origin}-{destination}"
        )
        print(
            "=================================================="
        )

        # ======================================================
        # EXISTING HTTP SCRAPER
        #
        # KEEP THIS CODE.
        # We are NOT removing the GET/POST implementation.
        # It is simply not used for this Playwright run.
        # ======================================================

        # Existing HTTP collector remains available:
        #
        # calendar_rows = collect_fare_calendar(
        #     origin,
        #     destination,
        #     today
        # )

        # ======================================================
        # PLAYWRIGHT
        #
        # One browser calendar gives the fares for the
        # required booking-window dates.
        # ======================================================

        print(
            f"[PLAYWRIGHT] Collecting "
            f"{origin}-{destination}..."
        )

        calendar_rows = (
            collect_fare_calendar_browser(
                origin,
                destination,
                today,
            )
        )

        by_date = {
            row["departure_date"]: row
            for row in calendar_rows
        }

        print(
            f"[PLAYWRIGHT] Received "
            f"{len(calendar_rows)} calendar records."
        )

        # ======================================================
        # T+45
        #
        # If the first browser calendar does not contain
        # T+45, open a second calendar centred on T+45.
        # ======================================================

        t45_date = (
            today + timedelta(days=45)
        )

        if t45_date not in by_date:

            print(
                f"[PLAYWRIGHT] T+45 "
                f"({t45_date}) not present."
            )

            print(
                "[PLAYWRIGHT] Fetching second "
                "calendar for T+45..."
            )

            extra_rows = (
                collect_fare_calendar_browser(
                    origin,
                    destination,
                    t45_date,
                )
            )

            for row in extra_rows:

                by_date.setdefault(
                    row["departure_date"],
                    row,
                )

        # ======================================================
        # EXACTLY THE 5 BOOKING WINDOWS
        # ======================================================

        route_inserted = 0

        for (
            target_date,
            booking_window,
        ) in target_dates.items():

            # Don't create duplicate observations
            # if this route/date was already collected.
            if collection_exists(
                origin,
                destination,
                target_date,
            ):

                print(
                    f"{booking_window} | "
                    f"{target_date} | "
                    f"Already collected - skipping"
                )

                continue

            row = by_date.get(
                target_date
            )

            if row is None:

                print(
                    f"{booking_window} | "
                    f"{target_date} | "
                    f"NO FARE FOUND"
                )

                continue

            # Attach booking-window information.
            row["booking_window"] = (
                booking_window
            )

            inserted = ingest_fare(
                row
            )

            if inserted:
                route_inserted += 1
                total_inserted += 1

            print(
                f"{booking_window} | "
                f"{target_date} | "
                f"Fare: ₹{row['fare']:.2f} | "
                f"Inserted: {inserted}"
            )

        print()
        print(
            f"{origin}-{destination}: "
            f"{route_inserted}/5 booking-window "
            f"observations inserted"
        )

        time.sleep(
            PAUSE_BETWEEN_ROUTES_SEC
        )

    # ==========================================================
    # FINAL RESULT
    # ==========================================================

    print()
    print(
        "=================================================="
    )
    print(
        "PLAYWRIGHT COLLECTION COMPLETE"
    )
    print(
        "=================================================="
    )

    print(
        f"Routes processed: {len(routes)}"
    )

    print(
        f"Target observations: "
        f"{len(routes) * len(BOOKING_WINDOWS)}"
    )

    print(
        f"Inserted this run: "
        f"{total_inserted}"
    )

    print(
        "=================================================="
    )


if __name__ == "__main__":
    run_scraping()