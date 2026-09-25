import json
from pathlib import Path

from app.db_config import get_connection


BASE_DIR = Path(__file__).resolve().parent.parent
BASELINES_FILE = BASE_DIR / "config" / "baselines.json"


def setup_baselines():

    with open(
        BASELINES_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        config = json.load(file)

    conn = get_connection()
    cursor = conn.cursor()

    for route in config["routes"]:

        cursor.execute("""
            INSERT INTO route_baselines
            (
                origin,
                destination,
                base_fare,
                base_date
            )
            VALUES (%s, %s, %s, %s)

            ON CONFLICT DO NOTHING
        """, (
            route["origin"],
            route["destination"],
            route["base_fare"],
            route["base_date"]
        ))

    conn.commit()

    cursor.close()
    conn.close()

    print("Route baselines loaded successfully.")


if __name__ == "__main__":
    setup_baselines()