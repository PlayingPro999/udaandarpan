import json
from datetime import date, timedelta
from pathlib import Path

from app.collector import collect_fares
from app.ingestion import ingest_fare


BASE_DIR = Path(__file__).resolve().parent.parent

ROUTES_FILE = BASE_DIR / "config" / "routes.json"


BOOKING_WINDOWS = {
    1: "T+1",
    7: "T+7",
    15: "T+15",
    30: "T+30",
    45: "T+45"
}


def load_routes():

    with open(
        ROUTES_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    return [
        (
            route["origin"],
            route["destination"]
        )
        for route in data["routes"]
    ]


def run_collection():

    routes = load_routes()

    today = date.today()

    total_collected = 0
    total_inserted = 0

    for origin, destination in routes:

        print(
            f"\n========== {origin}-{destination} =========="
        )

        for days, window in BOOKING_WINDOWS.items():

            departure_date = (
                today + timedelta(days=days)
            ).isoformat()

            print(
                f"\nCollecting {window} "
                f"({departure_date})..."
            )

            raw_fares = collect_fares(
                origin=origin,
                destination=destination,
                departure_date=departure_date
            )

            inserted = 0

            for raw_fare in raw_fares:

                if ingest_fare(raw_fare):
                    inserted += 1

            total_collected += len(raw_fares)
            total_inserted += inserted

            print(
                f"{window}: "
                f"{len(raw_fares)} fares collected, "
                f"{inserted} inserted"
            )

    print("\nCollection complete.")

    print(
        f"Total collected: {total_collected}"
    )

    print(
        f"Total inserted: {total_inserted}"
    )


if __name__ == "__main__":
    run_collection()