
import json
from pathlib import Path

from app.db_config import get_connection

BASE_DIR = Path(__file__).resolve().parent.parent
BASELINES_FILE = BASE_DIR / "config" / "baselines.json"


def setup_baselines():
    with BASELINES_FILE.open("r", encoding="utf-8") as file:
        config = json.load(file)

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            for route in config["routes"]:
                origin = route["origin"].upper()
                destination = route["destination"].upper()
                base_fare = route["base_fare"]
                base_date = route["base_date"]

                cursor.execute(
                    """
                    UPDATE route_baselines
                    SET base_fare = %s, base_date = %s
                    WHERE origin = %s AND destination = %s
                    """,
                    (base_fare, base_date, origin, destination),
                )

                if cursor.rowcount == 0:
                    cursor.execute(
                        """
                        INSERT INTO route_baselines
                            (origin, destination, base_fare, base_date)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (origin, destination, base_fare, base_date),
                    )

        conn.commit()
        print("Route baselines loaded successfully.")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    setup_baselines()
