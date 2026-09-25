import os
import requests

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("IGNAV_API_KEY")

BASE_URL = "https://ignav.com/api"


def collect_fares(
    origin,
    destination,
    departure_date
):

    response = requests.post(
        f"{BASE_URL}/fares/one-way",
        headers={
            "X-Api-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "adults": 1,
            "cabin_class": "economy",
            "market": "IN"
        },
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    fares = []

    for itinerary in data.get("itineraries", []):

        outbound = itinerary["outbound"]
        segments = outbound["segments"]

        first_segment = segments[0]
        last_segment = segments[-1]

        fares.append({

            # Basic information
            "source": "Ignav",

            "origin": first_segment["departure_airport"],
            "destination": last_segment["arrival_airport"],

            "airline": outbound.get(
                "carrier",
                "Unknown"
            ),

            "flight_number": first_segment.get(
                "flight_number"
            ),

            "departure_date": departure_date,

            # Times
            "departure_time": first_segment.get(
                "departure_time_local"
            ),

            "arrival_time": last_segment.get(
                "arrival_time_local"
            ),

            # Duration
            "duration_minutes": outbound.get(
                "duration_minutes"
            ),

            # Flight characteristics
            "cabin": itinerary.get(
                "cabin_class",
                "Economy"
            ),

            "stops": len(segments) - 1,

            "aircraft": first_segment.get(
                "aircraft"
            ),

            # Price
            "fare": float(
                itinerary["price"]["amount"]
            ),

            "currency": itinerary["price"].get(
                "currency",
                "INR"
            ),

            "price_status": itinerary["price"].get(
                "status"
            ),

            # Baggage
            "checked_bags": itinerary.get(
                "bags",
                {}
            ).get(
                "checked"
            ),

            # Transfer
            "requires_self_transfer": itinerary.get(
                "requires_self_transfer",
                False
            ),

            # Ignav identifier
            "ignav_id": itinerary.get(
                "ignav_id"
            ),

            # Preserve complete itinerary
            "raw_data": itinerary
        })

    return fares