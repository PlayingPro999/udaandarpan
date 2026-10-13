import psycopg2.extras

from app.db_config import get_connection


def collection_exists(
    origin,
    destination,
    departure_date,
    source,
    booking_window
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM fare_observations
            WHERE origin = %s
              AND destination = %s
              AND departure_date = %s
              AND source = %s
              AND booking_window = %s
              AND search_timestamp::date = CURRENT_DATE
        )
        """,
        (
            origin,
            destination,
            departure_date,
            source,
            booking_window
        )
    )

    exists = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return exists


def insert_fare(fare):
    fare.validate()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO fare_observations
        (
            source, origin, destination, airline, flight_number,
            departure_date, search_timestamp, booking_window,
            departure_time, arrival_time, duration_minutes,
            cabin, stops, fare, currency, aircraft, price_status,
            checked_bags, requires_self_transfer, ignav_id, raw_data
        )
        VALUES
        (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (ignav_id, departure_date)
        DO NOTHING
        """,
        (
            fare.source,
            fare.origin,
            fare.destination,
            fare.airline,
            fare.flight_number,
            fare.departure_date,
            fare.search_timestamp,
            fare.booking_window,
            fare.departure_time,
            fare.arrival_time,
            fare.duration_minutes,
            fare.cabin,
            fare.stops,
            fare.fare,
            fare.currency,
            fare.aircraft,
            fare.price_status,
            fare.checked_bags,
            fare.requires_self_transfer,
            fare.ignav_id,
            psycopg2.extras.Json(fare.raw_data)
        )
    )

    conn.commit()

    inserted = cursor.rowcount

    cursor.close()
    conn.close()

    return inserted == 1