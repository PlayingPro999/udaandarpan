import json
from pathlib import Path

from app.db_config import get_connection


BASE_DIR = Path(__file__).resolve().parent.parent
WEIGHTS_FILE = BASE_DIR / "config" / "route_weights.json"


def load_weights():

    with open(
        WEIGHTS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        config = json.load(file)

    source = config["source"]
    period = config["period"]
    routes = config["routes"]

    total_passengers = sum(
        route["passenger_count"]
        for route in routes
    )

    conn = get_connection()
    cursor = conn.cursor()

    for route in routes:

        origin = route["origin"]
        destination = route["destination"]
        passengers = route["passenger_count"]

        weight = passengers / total_passengers

        cursor.execute("""
            INSERT INTO route_weights
            (
                origin,
                destination,
                passenger_count,
                weight,
                source,
                period
            )
            VALUES (%s, %s, %s, %s, %s, %s)

            ON CONFLICT (origin, destination, period)
            DO UPDATE SET
                passenger_count = EXCLUDED.passenger_count,
                weight = EXCLUDED.weight,
                source = EXCLUDED.source
        """, (
            origin,
            destination,
            passengers,
            weight,
            source,
            period
        ))

    conn.commit()

    cursor.close()
    conn.close()

    print("Route weights loaded successfully.")
    print()

    for route in routes:

        weight = (
            route["passenger_count"]
            / total_passengers
        )

        print(
            f"{route['origin']}-{route['destination']}: "
            f"{route['passenger_count']:,} passengers | "
            f"Weight: {weight:.4%}"
        )


if __name__ == "__main__":
    load_weights()