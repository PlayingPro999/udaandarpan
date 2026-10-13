from app.db_config import get_connection


BOOKING_WINDOW_ORDER = {
    "T+1": 1,
    "T+7": 2,
    "T+15": 3,
    "T+30": 4,
    "T+45": 5
}


def calculate_national_index():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT MAX(index_date)
        FROM airfare_index_values;
    """)

    latest_index_date = cursor.fetchone()[0]

    if latest_index_date is None:
        cursor.close()
        conn.close()

        return {
            "national_indices": [],
            "final_index": None,
            "index_date": None,
            "method": (
                "Route-level price relatives aggregated using "
                "passenger-traffic weights; booking-window "
                "subindices equally weighted."
            )
        }

    cursor.execute("""
        SELECT
            i.route_origin,
            i.route_destination,
            i.booking_window,
            i.index_date,
            i.route_index,
            w.weight
        FROM airfare_index_values i
        INNER JOIN route_weights w
            ON i.route_origin = w.origin
            AND i.route_destination = w.destination
        WHERE
            i.index_date = %s
            AND w.period = (
                SELECT MAX(period)
                FROM route_weights
            )
        ORDER BY
            i.route_origin,
            i.route_destination,
            CASE i.booking_window
                WHEN 'T+1' THEN 1
                WHEN 'T+7' THEN 2
                WHEN 'T+15' THEN 3
                WHEN 'T+30' THEN 4
                WHEN 'T+45' THEN 5
                ELSE 6
            END;
    """, (latest_index_date,))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    if not rows:
        return {
            "national_indices": [],
            "final_index": None,
            "index_date": latest_index_date,
            "method": (
                "Route-level price relatives aggregated using "
                "passenger-traffic weights; booking-window "
                "subindices equally weighted."
            )
        }

    window_data = {}

    for (
        origin,
        destination,
        booking_window,
        index_date,
        route_index,
        weight
    ) in rows:

        if booking_window not in window_data:
            window_data[booking_window] = {
                "weighted_sum": 0.0,
                "weight_sum": 0.0
            }

        window_data[booking_window]["weighted_sum"] += (
            float(route_index) * float(weight)
        )

        window_data[booking_window]["weight_sum"] += float(weight)

    national_indices = []

    for booking_window, data in window_data.items():

        if data["weight_sum"] <= 0:
            continue

        national_index = (
            data["weighted_sum"] /
            data["weight_sum"]
        )

        national_indices.append({
            "booking_window": booking_window,
            "index_date": latest_index_date,
            "national_index": round(
                national_index,
                2
            )
        })

    national_indices.sort(
        key=lambda item:
            BOOKING_WINDOW_ORDER.get(
                item["booking_window"],
                99
            )
    )

    if national_indices:

        final_index = round(
            sum(
                item["national_index"]
                for item in national_indices
            ) / len(national_indices),
            2
        )

    else:

        final_index = None

    return {
        "national_indices": national_indices,
        "final_index": final_index,
        "index_date": latest_index_date,
        "method": (
            "Route-level price relatives aggregated using "
            "passenger-traffic weights; booking-window "
            "subindices equally weighted."
        )
    }