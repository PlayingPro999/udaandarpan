
from app.db_config import get_connection


BOOKING_WINDOW_ORDER = {
    "T+1": 1,
    "T+7": 2,
    "T+15": 3,
    "T+30": 4,
    "T+45": 5,
}


def calculate_route_indices():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Get all distinct route and booking-window combinations.
        # The outer query handles ordering without PostgreSQL's
        # SELECT DISTINCT / ORDER BY restriction.
        cursor.execute("""
            SELECT
                origin,
                destination,
                booking_window
            FROM (
                SELECT DISTINCT
                    f.origin,
                    f.destination,
                    f.booking_window
                FROM fare_observations f
                WHERE
                    f.source = 'EaseMyTrip'
                    AND f.currency = 'INR'
                    AND f.booking_window IS NOT NULL
            ) AS route_windows
            ORDER BY
                origin,
                destination,
                CASE booking_window
                    WHEN 'T+1' THEN 1
                    WHEN 'T+7' THEN 2
                    WHEN 'T+15' THEN 3
                    WHEN 'T+30' THEN 4
                    WHEN 'T+45' THEN 5
                    ELSE 6
                END;
        """)

        route_windows = cursor.fetchall()
        results = []

        for origin, destination, booking_window in route_windows:

            # Find the first and latest observation dates.
            cursor.execute("""
                SELECT
                    MIN(search_timestamp::date),
                    MAX(search_timestamp::date)
                FROM fare_observations
                WHERE
                    source = 'EaseMyTrip'
                    AND currency = 'INR'
                    AND origin = %s
                    AND destination = %s
                    AND booking_window = %s;
            """, (origin, destination, booking_window))

            first_date, latest_date = cursor.fetchone()

            if first_date is None or latest_date is None:
                continue

            # A comparison requires observations from at least
            # two different collection dates.
            if first_date == latest_date:
                continue

            # Calculate the base-period average fare.
            cursor.execute("""
                SELECT
                    AVG(fare),
                    COUNT(*)
                FROM fare_observations
                WHERE
                    source = 'EaseMyTrip'
                    AND currency = 'INR'
                    AND origin = %s
                    AND destination = %s
                    AND booking_window = %s
                    AND search_timestamp::date = %s;
            """, (
                origin,
                destination,
                booking_window,
                first_date,
            ))

            base_fare, base_observations = cursor.fetchone()

            # Calculate the latest-period average fare.
            cursor.execute("""
                SELECT
                    AVG(fare),
                    COUNT(*)
                FROM fare_observations
                WHERE
                    source = 'EaseMyTrip'
                    AND currency = 'INR'
                    AND origin = %s
                    AND destination = %s
                    AND booking_window = %s
                    AND search_timestamp::date = %s;
            """, (
                origin,
                destination,
                booking_window,
                latest_date,
            ))

            current_fare, current_observations = cursor.fetchone()

            if base_fare is None or current_fare is None:
                continue

            base_fare = float(base_fare)
            current_fare = float(current_fare)

            if base_fare <= 0:
                continue

            # Index formula: base period = 100.
            route_index = (current_fare / base_fare) * 100

            # Insert the calculated index or update the existing
            # record for this route, window and index date.
            cursor.execute("""
                INSERT INTO airfare_index_values
                (
                    route_origin,
                    route_destination,
                    booking_window,
                    index_date,
                    base_fare,
                    current_fare,
                    route_index,
                    observation_count
                )
                VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT
                (
                    route_origin,
                    route_destination,
                    booking_window,
                    index_date
                )
                DO UPDATE SET
                    base_fare = EXCLUDED.base_fare,
                    current_fare = EXCLUDED.current_fare,
                    route_index = EXCLUDED.route_index,
                    observation_count = EXCLUDED.observation_count;
            """, (
                origin,
                destination,
                booking_window,
                latest_date,
                base_fare,
                current_fare,
                route_index,
                current_observations,
            ))

            results.append({
                "route": f"{origin}-{destination}",
                "booking_window": booking_window,
                "base_period": str(first_date),
                "current_period": str(latest_date),
                "base_fare": round(base_fare, 2),
                "current_fare": round(current_fare, 2),
                "index": round(route_index, 2),
                "base_observations": base_observations,
                "current_observations": current_observations,
            })

        conn.commit()
        return results

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()
