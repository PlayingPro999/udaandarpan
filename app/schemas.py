from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class FareObservation:
    source: str

    origin: str
    destination: str

    airline: str
    flight_number: Optional[str]

    departure_date: date
    search_timestamp: datetime
    booking_window: Optional[str]
    departure_time: Optional[datetime]
    arrival_time: Optional[datetime]
    duration_minutes: Optional[int]

    cabin: str
    stops: int

    fare: float
    currency: str

    aircraft: Optional[str]
    price_status: Optional[str]
    checked_bags: Optional[int]
    requires_self_transfer: Optional[bool]

    ignav_id: Optional[str]
    raw_data: Optional[dict]

    def validate(self):

        if not self.origin:
            raise ValueError("Origin is required")

        if not self.destination:
            raise ValueError("Destination is required")

        if self.origin == self.destination:
            raise ValueError("Origin and destination cannot be the same")

        if not self.airline:
            raise ValueError("Airline is required")

        if self.fare <= 0:
            raise ValueError("Fare must be greater than zero")

        if self.stops < 0:
            raise ValueError("Stops cannot be negative")

        if not self.currency:
            raise ValueError("Currency is required")

        return True