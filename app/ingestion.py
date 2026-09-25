from app.schemas import FareObservation
from app.normalizer import normalize_fare
from app.repository import insert_fare


def ingest_fare(raw_data):

    normalized = normalize_fare(raw_data)

    fare = FareObservation(**normalized)

    return insert_fare(fare)