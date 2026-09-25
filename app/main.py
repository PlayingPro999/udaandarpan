from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db_config import get_connection
from app.national_index import calculate_national_index


app = FastAPI(
    title="Real-time Airfare Price Index API",
    version="1.0.0"
)


app.mount(
    "/dashboard",
    StaticFiles(
        directory="app/static",
        html=True
    ),
    name="dashboard"
)


@app.get("/")
def home():
    return {
        "message": "Airfare Price Index API is running"
    }


@app.get("/fares")
def get_fares():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            source,
            origin,
            destination,
            airline,
            flight_number,
            departure_date,
            booking_window,
            departure_time,
            arrival_time,
            duration_minutes,
            cabin,
            stops,
            fare,
            currency,
            aircraft,
            price_status,
            checked_bags,
            requires_self_transfer,
            ignav_id,
            search_timestamp
        FROM fare_observations
        ORDER BY departure_time, fare;
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return [
        {
            "id": row[0],
            "source": row[1],
            "origin": row[2],
            "destination": row[3],
            "airline": row[4],
            "flight_number": row[5],
            "departure_date": row[6],
            "booking_window": row[7],
            "departure_time": row[8],
            "arrival_time": row[9],
            "duration_minutes": row[10],
            "cabin": row[11],
            "stops": row[12],
            "fare": float(row[13]),
            "currency": row[14],
            "aircraft": row[15],
            "price_status": row[16],
            "checked_bags": row[17],
            "requires_self_transfer": row[18],
            "ignav_id": row[19],
            "search_timestamp": row[20]
        }
        for row in rows
    ]


@app.get("/index")
def get_index():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            route_origin,
            route_destination,
            booking_window,
            index_date,
            base_fare,
            current_fare,
            route_index,
            observation_count
        FROM airfare_index_values
        ORDER BY
            route_origin,
            route_destination,
            CASE booking_window
                WHEN 'T+1' THEN 1
                WHEN 'T+7' THEN 2
                WHEN 'T+15' THEN 3
                WHEN 'T+30' THEN 4
                WHEN 'T+45' THEN 5
                ELSE 6
            END;
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return [
        {
            "route": f"{row[0]}-{row[1]}",
            "booking_window": row[2],
            "index_date": row[3],
            "base_fare": float(row[4]),
            "current_fare": float(row[5]),
            "index": float(row[6]),
            "observations": row[7]
        }
        for row in rows
    ]


@app.get("/national-index")
def get_national_index():

    return calculate_national_index()