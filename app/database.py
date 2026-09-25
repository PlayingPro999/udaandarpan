from app.db_config import get_connection


def initialize_database():

    conn = get_connection()
    cursor = conn.cursor()

    # ---------------------------------------------------------
    # FARE OBSERVATIONS
    # ---------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fare_observations (
            id SERIAL PRIMARY KEY,
            source VARCHAR(50) NOT NULL,
            origin VARCHAR(10) NOT NULL,
            destination VARCHAR(10) NOT NULL,
            airline VARCHAR(100) NOT NULL,
            flight_number VARCHAR(50),
            departure_date DATE NOT NULL,
            search_timestamp TIMESTAMP NOT NULL,
            booking_window VARCHAR(10),
            departure_time TIMESTAMP,
            arrival_time TIMESTAMP,
            duration_minutes INTEGER,
            cabin VARCHAR(50),
            stops INTEGER,
            fare NUMERIC(12,2) NOT NULL,
            currency VARCHAR(10) NOT NULL,
            aircraft VARCHAR(100),
            price_status VARCHAR(50),
            checked_bags INTEGER,
            requires_self_transfer BOOLEAN,
            ignav_id VARCHAR(255),
            raw_data JSONB
        );
    """)

    # ---------------------------------------------------------
    # COLUMNS FOR EXISTING DATABASES
    # ---------------------------------------------------------

    cursor.execute("""
        ALTER TABLE fare_observations
        ADD COLUMN IF NOT EXISTS booking_window VARCHAR(10);
    """)

    cursor.execute("""
        ALTER TABLE fare_observations
        ADD COLUMN IF NOT EXISTS aircraft VARCHAR(100);
    """)

    cursor.execute("""
        ALTER TABLE fare_observations
        ADD COLUMN IF NOT EXISTS price_status VARCHAR(50);
    """)

    cursor.execute("""
        ALTER TABLE fare_observations
        ADD COLUMN IF NOT EXISTS checked_bags INTEGER;
    """)

    cursor.execute("""
        ALTER TABLE fare_observations
        ADD COLUMN IF NOT EXISTS requires_self_transfer BOOLEAN;
    """)

    cursor.execute("""
        ALTER TABLE fare_observations
        ADD COLUMN IF NOT EXISTS ignav_id VARCHAR(255);
    """)

    cursor.execute("""
        ALTER TABLE fare_observations
        ADD COLUMN IF NOT EXISTS raw_data JSONB;
    """)

    # ---------------------------------------------------------
    # FARE OBSERVATION INDEXES
    # ---------------------------------------------------------

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_fare_route
        ON fare_observations (origin, destination);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_fare_departure_date
        ON fare_observations (departure_date);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_fare_search_timestamp
        ON fare_observations (search_timestamp);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_fare_booking_window
        ON fare_observations (booking_window);
    """)

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS unique_ignav_departure
        ON fare_observations (ignav_id, departure_date)
        WHERE ignav_id IS NOT NULL;
    """)

    # ---------------------------------------------------------
    # ROUTE BASELINES
    # ---------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS route_baselines (
            id SERIAL PRIMARY KEY,
            origin VARCHAR(10) NOT NULL,
            destination VARCHAR(10) NOT NULL,
            base_fare NUMERIC(12,2) NOT NULL,
            base_date DATE NOT NULL
        );
    """)

    # ---------------------------------------------------------
    # AIRFARE INDEX VALUES
    # ---------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS airfare_index_values (
            id SERIAL PRIMARY KEY,
            route_origin VARCHAR(10) NOT NULL,
            route_destination VARCHAR(10) NOT NULL,
            booking_window VARCHAR(10),
            index_date DATE NOT NULL,
            base_fare NUMERIC(12,2) NOT NULL,
            current_fare NUMERIC(12,2) NOT NULL,
            route_index NUMERIC(12,4) NOT NULL,
            observation_count INTEGER NOT NULL
        );
    """)

    cursor.execute("""
        ALTER TABLE airfare_index_values
        ADD COLUMN IF NOT EXISTS booking_window VARCHAR(10);
    """)

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS unique_route_window_date
        ON airfare_index_values
        (
            route_origin,
            route_destination,
            booking_window,
            index_date
        );
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_index_route
        ON airfare_index_values
        (
            route_origin,
            route_destination
        );
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_index_booking_window
        ON airfare_index_values
        (
            booking_window
        );
    """)

    # ---------------------------------------------------------
    # ROUTE WEIGHTS
    # ---------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS route_weights (
            id SERIAL PRIMARY KEY,
            origin VARCHAR(10) NOT NULL,
            destination VARCHAR(10) NOT NULL,
            passenger_count BIGINT NOT NULL,
            weight NUMERIC(12,8) NOT NULL,
            source VARCHAR(100) NOT NULL,
            period VARCHAR(50) NOT NULL,
            UNIQUE(origin, destination, period)
        );
    """)

    conn.commit()

    cursor.close()
    conn.close()

    print("Database schema is ready!")


if __name__ == "__main__":
    initialize_database()