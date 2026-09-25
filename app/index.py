from datetime import date

from app.db_config import get_connection


def calculate_route_indices():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            f.origin,
            f.destination,
            f.booking_window,
            AVG(f.fare) AS current_fare,
            COUNT(*) AS observation_count,
            b.base_fare
        FROM fare_observations f
        JOIN route_baselines b
            ON f.origin = b.origin
            AND f.destination = b.destination
        WHERE
            f.currency = 'INR'
            AND f.booking_window IS NOT NULL
        GROUP BY
            f.origin,
            f.destination,
            f.booking_window,
            b.base_fare
        ORDER BY
            f.origin,
            f.destination,
            CASE f.booking_window
                WHEN 'T+1' THEN 1
                WHEN 'T+7' THEN 2
                WHEN 'T+15' THEN 3
                WHEN 'T+30' THEN 4
                WHEN 'T+45' THEN 5
                ELSE 6
            END;
    """)

    routes = cursor.fetchall()
    results = []

    for (
        origin,
        destination,
        booking_window,
        current_fare,
        observation_count,
        base_fare
    ) in routes:

        route_index = (
            float(current_fare) /
            float(base_fare)
        ) * 100

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
                observation_count = EXCLUDED.observation_count
        """, (
            origin,
            destination,
            booking_window,
            date.today(),
            base_fare,
            current_fare,
            route_index,
            observation_count
        ))

        results.append({
            "route": f"{origin}-{destination}",
            "booking_window": booking_window,
            "base_fare": round(float(base_fare), 2),
            "current_fare": round(float(current_fare), 2),
            "index": round(route_index, 2),
            "observations": observation_count
        })

    conn.commit()

    cursor.close()
    conn.close()

    return results


if __name__ == "__main__":

    results = calculate_route_indices()

    print("\nAIRFARE PRICE INDEX")
    print("===================")

    for result in results:

        print(
            f"{result['route']} | "
            f"{result['booking_window']} | "
            f"Base: ₹{result['base_fare']:.2f} | "
            f"Current: ₹{result['current_fare']:.2f} | "
            f"Index: {result['index']:.2f} | "
            f"Observations: {result['observations']}"
        )