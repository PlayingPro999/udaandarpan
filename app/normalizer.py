from datetime import datetime, date


BOOKING_WINDOWS = {
    1: "T+1",
    7: "T+7",
    15: "T+15",
    30: "T+30",
    45: "T+45"
}


def get_booking_window(departure_date, search_timestamp):
    """
    Classify a fare into one of the required booking windows.

    The window is based on:
        departure_date - search_timestamp.date()

    Only exact windows are accepted.
    """

    if isinstance(departure_date, str):
        departure_date = date.fromisoformat(departure_date)

    if isinstance(search_timestamp, str):
        search_timestamp = datetime.fromisoformat(search_timestamp)

    days_before_departure = (
        departure_date - search_timestamp.date()
    ).days

    return BOOKING_WINDOWS.get(days_before_departure)


def normalize_fare(raw):

    search_timestamp = raw.get(
        "search_timestamp",
        datetime.now()
    )

    departure_date = raw["departure_date"]

    return {
        "source": raw.get("source", "Unknown"),

        "origin": raw["origin"].upper().strip(),
        "destination": raw["destination"].upper().strip(),

        "airline": raw["airline"].strip(),
        "flight_number": raw.get("flight_number"),

        "departure_date": departure_date,

        "search_timestamp": search_timestamp,

        "booking_window": get_booking_window(
            departure_date,
            search_timestamp
        ),

        "departure_time": raw.get("departure_time"),
        "arrival_time": raw.get("arrival_time"),

        "duration_minutes": raw.get("duration_minutes"),

        "cabin": raw.get(
            "cabin",
            "Economy"
        ).strip(),

        "stops": int(raw.get("stops", 0)),

        "fare": float(raw["fare"]),

        "currency": raw.get(
            "currency",
            "INR"
        ).upper(),

        "aircraft": raw.get("aircraft"),

        "price_status": raw.get("price_status"),

        "checked_bags": raw.get("checked_bags"),

        "requires_self_transfer": raw.get(
            "requires_self_transfer",
            False
        ),

        "ignav_id": raw.get("ignav_id"),

        "raw_data": raw.get("raw_data")
    }