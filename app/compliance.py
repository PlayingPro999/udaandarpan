from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "scraping_compliance.log"


def log_compliance(
    source,
    robots_status,
    target,
    action,
    details=""
):
    LOG_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()

    message = (
        f"{timestamp} | "
        f"SOURCE={source} | "
        f"ROBOTS={robots_status} | "
        f"TARGET={target} | "
        f"ACTION={action}"
    )

    if details:
        message += f" | DETAILS={details}"

    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(message + "\n")

    print(message)