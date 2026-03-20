"""
Centralized outbound data logger.

Logs every piece of presence/detection data sent to any client,
from any endpoint or event stream, to a single persistent file.
"""
import os
from datetime import datetime

LOG_PATH = "/tmp/ziggy-webcam/outbound.log"


def log_outbound(source: str, data: dict) -> None:
    """Log outbound data to the shared log file.

    Args:
        source: Where the data is being sent from (e.g. "HTTP /presence",
                "SSE presence_changed", "event_publisher.publish")
        data: The payload being sent
    """
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"{ts} [{source}] {data}\n"
        with open(LOG_PATH, "a") as f:
            f.write(line)
    except Exception:
        pass
