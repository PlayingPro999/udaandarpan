import psycopg2

from app.db_config import (
    DB_HOST,
    DB_PORT,
    DB_USER,
    DB_PASSWORD,
    DB_NAME
)


def create_database():

    connection = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database="postgres",
        user=DB_USER,
        password=DB_PASSWORD
    )

    connection.autocommit = True

    cursor = connection.cursor()

    cursor.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s",
        (DB_NAME,)
    )

    exists = cursor.fetchone()

    if exists:

        print(
            f"Database '{DB_NAME}' already exists."
        )

    else:

        cursor.execute(
            f'CREATE DATABASE "{DB_NAME}"'
        )

        print(
            f"Database '{DB_NAME}' created successfully."
        )

    cursor.close()
    connection.close()


if __name__ == "__main__":
    create_database()