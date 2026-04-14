import logging


def configure_logging() -> None:
    # Basic console logging. Keeps auth module independent of logging setup.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
