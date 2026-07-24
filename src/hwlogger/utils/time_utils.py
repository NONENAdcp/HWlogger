from datetime import UTC, datetime


def local_and_utc() -> tuple[str, str]:
    now = datetime.now().astimezone()
    return now.isoformat(timespec="milliseconds"), now.astimezone(UTC).isoformat(
        timespec="milliseconds"
    )
