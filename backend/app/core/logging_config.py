import logging


class HealthcheckAccessFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return " /health " not in message


def setup_logging() -> None:
    if logging.getLogger().handlers:
        return

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    # Keep access logs, but suppress repetitive healthcheck requests.
    logging.getLogger("uvicorn.access").addFilter(HealthcheckAccessFilter())
