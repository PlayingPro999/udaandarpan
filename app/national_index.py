BOOKING_WINDOW_ORDER = {
    "T+1": 1,
    "T+7": 2,
    "T+15": 3,
    "T+30": 4,
    "T+45": 5
}


from app.db_config import get_connection


def calculate_national_index():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            i.route_origin,
            i.route_destination,
            i.booking_window,
            i.index_date,
            i.route_index,
            w.weight
        FROM airfare_index_values i
        JOIN route_weights w
            ON i.route_origin = w.origin
            AND i.route_destination = w.destination
        WHERE
            w.period = (
                SELECT MAX(period)
                FROM route_weights
            )
        ORDER BY
            i.booking_window;
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    if not rows:
        return {
            "national_indices": [],
            "final_index": None,
            "method":
                "Passenger-weighted routes; "
                "equal booking-window weights"
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
                "weighted_sum": 0,
                "weight_sum": 0,
                "index_date": index_date
            }

        window_data[booking_window]["weighted_sum"] += (
            float(route_index) * float(weight)
        )

        window_data[booking_window]["weight_sum"] += (
            float(weight)
        )

    national_indices = []

    for booking_window, data in window_data.items():

        if data["weight_sum"] == 0:
            continue

        national_index = (
            data["weighted_sum"] /
            data["weight_sum"]
        )

        national_indices.append({
            "booking_window": booking_window,
            "index_date": data["index_date"],
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

    if len(national_indices) > 0:

        final_index = round(
            sum(
                item["national_index"]
                for item in national_indices
            )
            /
            len(national_indices),
            2
        )

    else:
        final_index = None

    return {
        "national_indices": national_indices,
        "final_index": final_index,
        "method":
            "Passenger-weighted routes; "
            "equal booking-window weights"
    }


if __name__ == "__main__":

    result = calculate_national_index()

    print("\nNATIONAL AIRFARE PRICE INDEX")
    print("============================")

    for item in result["national_indices"]:

        print(
            f"{item['booking_window']} | "
            f"National Index: "
            f"{item['national_index']:.2f}"
        )

    print(
        f"\nFinal National Index: "
        f"{result['final_index']}"
    )

    print(
        f"Method: {result['method']}"
    )