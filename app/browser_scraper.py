import re

from datetime import date, datetime

from playwright.sync_api import sync_playwright

from app.scraper import (
    EASEMYTRIP_SOURCE,
    USER_AGENT,
)


EASEMYTRIP_CALENDAR_URL = (
    "https://www.easemytrip.com/airfare-calender"
)


def _get_visible_city_inputs(page):

    inputs = page.locator(
        "input.autoFlll.input_city"
    )

    visible_inputs = []

    for index in range(inputs.count()):

        element = inputs.nth(index)

        try:
            if element.is_visible():
                visible_inputs.append(element)
        except Exception:
            continue

    return visible_inputs


def _get_city_input(page, index):

    inputs = _get_visible_city_inputs(page)

    if index >= len(inputs):
        raise RuntimeError(
            f"Could not find visible city input at index {index}."
        )

    return inputs[index]


def _select_city(
    page,
    input_element,
    city_code
):

    input_element.click()

    input_element.fill(
        city_code
    )

    page.wait_for_timeout(1000)

    city_code_upper = city_code.upper()

    candidates = page.locator(
        "li, div, span"
    )

    for index in range(
        candidates.count()
    ):

        element = candidates.nth(index)

        try:

            if not element.is_visible():
                continue

            text = element.inner_text().strip()

            if not text:
                continue

            if city_code_upper not in text.upper():
                continue

            if len(text) > 200:
                continue

            element.click()

            page.wait_for_timeout(500)

            return

        except Exception:
            continue

    raise RuntimeError(
        f"Could not select airport/city: {city_code}"
    )


def _get_search_button(page):

    selectors = [
        "button:has-text('Search')",
        "input[value='Search']",
        "a:has-text('Search')",
        ".search_btn",
        "#search_button",
    ]

    for selector in selectors:

        locator = page.locator(
            selector
        )

        for index in range(
            locator.count()
        ):

            element = locator.nth(index)

            try:

                if element.is_visible():
                    return element

            except Exception:
                continue

    raise RuntimeError(
        "Could not find EaseMyTrip Search button."
    )


def _close_search_overlay(page):

    try:
        page.keyboard.press(
            "Escape"
        )
    except Exception:
        pass

    try:

        overlay = page.locator(
            "#overlaybg1"
        )

        if overlay.count() == 0:
            return

        for index in range(
            overlay.count()
        ):

            element = overlay.nth(index)

            try:

                if element.is_visible():

                    element.evaluate(
                        """
                        element => {
                            element.style.display = 'none';
                            element.style.visibility = 'hidden';
                            element.style.pointerEvents = 'none';
                        }
                        """
                    )

            except Exception:
                continue

    except Exception:
        pass


def _parse_calendar_text(
    text,
    origin,
    destination,
    target_date,
    booking_window
):

    fare_pattern = re.compile(
        r"\b"
        r"(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|"
        r"OCT|NOV|DEC)"
        r"\s+(\d{1,2})"
        r"\s+Rs\.?\s*"
        r"([\d,]+(?:\.\d+)?)",
        re.IGNORECASE,
    )

    month_numbers = {
        "JAN": 1,
        "FEB": 2,
        "MAR": 3,
        "APR": 4,
        "MAY": 5,
        "JUN": 6,
        "JUL": 7,
        "AUG": 8,
        "SEP": 9,
        "OCT": 10,
        "NOV": 11,
        "DEC": 12,
    }

    fares = []

    for match in fare_pattern.finditer(text):

        month_name = match.group(1).upper()

        day = int(
            match.group(2)
        )

        fare = float(
            match.group(3).replace(",", "")
        )

        month = month_numbers[
            month_name
        ]

        try:

            parsed_date = date(
                target_date.year,
                month,
                day,
            )

        except ValueError:
            continue

        if parsed_date != target_date:
            continue

        if fare <= 0:
            continue

        fares.append({

            "source": EASEMYTRIP_SOURCE,

            "origin": origin,

            "destination": destination,

            "airline": "EaseMyTrip",

            "flight_number": "CALENDAR",

            "departure_date": target_date,

            "booking_window": booking_window,

            "search_timestamp": datetime.utcnow(),

            "departure_time": None,

            "arrival_time": None,

            "duration_minutes": None,

            "cabin": "economy",

            "stops": 0,

            "fare": fare,

            "currency": "INR",

            "aircraft": "",

            "price_status": "available",

            "checked_bags": 0,

            "requires_self_transfer": False,

            "ignav_id": None,

            "raw_data": {

                "calendar_text": match.group(0),

                "collector": (
                    "easemytrip_browser"
                ),

                "booking_window": booking_window,

            },

        })

    return fares


def collect_fare_calendar_browser(
    origin,
    destination,
    target_date,
    booking_window
):

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            user_agent=USER_AGENT
        )

        page = context.new_page()

        try:

            print(
                f"EaseMyTrip | "
                f"{origin} -> {destination} | "
                f"{target_date} | "
                f"{booking_window}"
            )

            page.goto(
                EASEMYTRIP_CALENDAR_URL,
                wait_until="domcontentloaded",
            )

            page.wait_for_timeout(
                2000
            )

            visible_inputs = (
                _get_visible_city_inputs(page)
            )

            if len(visible_inputs) < 2:

                raise RuntimeError(
                    "Could not find both visible city inputs."
                )

            origin_input = (
                visible_inputs[0]
            )

            destination_input = (
                visible_inputs[1]
            )

            print(
                f"EaseMyTrip | "
                f"Selecting origin: {origin}"
            )

            _select_city(
                page,
                origin_input,
                origin,
            )

            print(
                f"EaseMyTrip | "
                f"Selecting destination: {destination}"
            )

            _select_city(
                page,
                destination_input,
                destination,
            )

            _close_search_overlay(
                page
            )

            search_button = (
                _get_search_button(page)
            )

            print(
                "EaseMyTrip | "
                "Clicking Search"
            )

            try:

                search_button.click(
                    timeout=5000
                )

            except Exception:

                _close_search_overlay(
                    page
                )

                search_button.evaluate(
                    "element => element.click()"
                )

            page.wait_for_timeout(
                4000
            )

            body_text = (
                page.locator("body").inner_text()
            )

            fares = _parse_calendar_text(
                body_text,
                origin,
                destination,
                target_date,
                booking_window,
            )

            print(
                f"EaseMyTrip | "
                f"Fares found: {len(fares)}"
            )

            return fares

        finally:

            context.close()
            browser.close()