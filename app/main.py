
from datetime import date
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles

from app.db_config import get_connection
from app.national_index import calculate_national_index


app = FastAPI(
    title="Real-time Airfare Price Index API",
    description=(
        "API for India's real-time airfare price observations, "
        "route-level indices, and passenger-weighted national airfare index."
    ),
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


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def home():

    return {
        "message": "Airfare Price Index API is running",
        "version": "1.0.0",
        "documentation": "/docs"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/v1/health")
def health_check():

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT 1;")
        cursor.fetchone()

        return {
            "status": "healthy",
            "database": "connected"
        }

    except Exception as exc:

        return {
            "status": "unhealthy",
            "database": "unavailable",
            "error": str(exc)
        }

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# FARES
# ============================================================

@app.get("/fares")
def get_fares(
    source: str = Query(default="EaseMyTrip")
):

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
        WHERE source = %s
        ORDER BY departure_time, fare;
    """, (source,))

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


# ============================================================
# VERSIONED FARE API
# ============================================================

@app.get("/api/v1/fares")
def get_fares_v1(
    origin: Optional[str] = Query(default=None),
    destination: Optional[str] = Query(default=None),
    airline: Optional[str] = Query(default=None),
    booking_window: Optional[str] = Query(default=None),
    departure_date: Optional[date] = Query(default=None),
    source: str = Query(default="EaseMyTrip"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0)
):

    conn = get_connection()
    cursor = conn.cursor()

    query = """
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
        WHERE source = %s
    """

    params = [source]

    if origin:

        query += " AND origin = %s"
        params.append(origin.upper())

    if destination:

        query += " AND destination = %s"
        params.append(destination.upper())

    if airline:

        query += " AND airline = %s"
        params.append(airline)

    if booking_window:

        query += " AND booking_window = %s"
        params.append(booking_window)

    if departure_date:

        query += " AND departure_date = %s"
        params.append(departure_date)

    query += """
        ORDER BY departure_date, fare
        LIMIT %s OFFSET %s
    """

    params.extend([
        limit,
        offset
    ])

    cursor.execute(
        query,
        params
    )

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    data = [
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

    return {
        "count": len(data),
        "limit": limit,
        "offset": offset,
        "source": source,
        "data": data
    }


# ============================================================
# ROUTES
# ============================================================

@app.get("/api/v1/routes")
def get_routes():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT
            origin,
            destination
        FROM fare_observations
        WHERE source = 'EaseMyTrip'
        ORDER BY origin, destination;
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        "count": len(rows),
        "routes": [
            {
                "origin": row[0],
                "destination": row[1],
                "route": f"{row[0]}-{row[1]}"
            }
            for row in rows
        ]
    }


# ============================================================
# ROUTE-LEVEL INDEX
# ============================================================

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
        FROM (
            SELECT
                route_origin,
                route_destination,
                booking_window,
                index_date,
                base_fare,
                current_fare,
                route_index,
                observation_count,

                ROW_NUMBER() OVER (
                    PARTITION BY
                        route_origin,
                        route_destination,
                        booking_window
                    ORDER BY
                        index_date DESC
                ) AS rn

            FROM airfare_index_values

        ) latest

        WHERE rn = 1

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


# ============================================================
# VERSIONED INDEX API
# ============================================================

@app.get("/api/v1/index")
def get_index_v1(
    origin: Optional[str] = Query(default=None),
    destination: Optional[str] = Query(default=None),
    booking_window: Optional[str] = Query(default=None)
):

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            route_origin,
            route_destination,
            booking_window,
            index_date,
            base_fare,
            current_fare,
            route_index,
            observation_count

        FROM (
            SELECT
                route_origin,
                route_destination,
                booking_window,
                index_date,
                base_fare,
                current_fare,
                route_index,
                observation_count,

                ROW_NUMBER() OVER (
                    PARTITION BY
                        route_origin,
                        route_destination,
                        booking_window
                    ORDER BY
                        index_date DESC
                ) AS rn

            FROM airfare_index_values

            WHERE 1 = 1
    """

    params = []

    if origin:

        query += """
            AND route_origin = %s
        """

        params.append(
            origin.upper()
        )

    if destination:

        query += """
            AND route_destination = %s
        """

        params.append(
            destination.upper()
        )

    if booking_window:

        query += """
            AND booking_window = %s
        """

        params.append(
            booking_window
        )

    query += """
        ) latest

        WHERE rn = 1

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
            END
    """

    cursor.execute(
        query,
        params
    )

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        "count": len(rows),

        "data": [
            {
                "route": f"{row[0]}-{row[1]}",
                "origin": row[0],
                "destination": row[1],
                "booking_window": row[2],
                "index_date": row[3],
                "base_fare": float(row[4]),
                "current_fare": float(row[5]),
                "index": float(row[6]),
                "observations": row[7]
            }
            for row in rows
        ]
    }


# ============================================================
# NATIONAL INDEX
# ============================================================

@app.get("/national-index")
def get_national_index():

    return calculate_national_index()


@app.get("/api/v1/national-index")
def get_national_index_v1():

    return {
        "data": calculate_national_index()
    }

