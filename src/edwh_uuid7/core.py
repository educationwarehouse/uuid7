"""
uuid7pg: PostgreSQL-compatible UUIDv7 generator for Python

This module provides utilities for generating and interpreting
UUIDv7 identifiers compatible with PostgreSQL extensions that
follow the timestamp-left-shifted format.
"""

import secrets
import time
from datetime import UTC, datetime, timezone
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from dateutil.parser import parse as dt_parse


def uuid7(
    timestamp_ms: Optional[int | float] = None,
    timestamp_ns: Optional[int | float] = None,
) -> UUID:
    """
    Generates a UUIDv7-style UUID with full 64-bit nanosecond timestamp precision.

    UUID Layout (128 bits):
    -------------------------------------------------------------------
    Bits  | Field           | Description
    ------|-----------------|--------------------------------------------------
    0-47  | timestamp_ms    | Unix timestamp in milliseconds (sortable)
    48-51 | version         | UUID version (0b0111 for v7)
    52-71 | sub_ms_ns       | Sub-millisecond nanoseconds (20 bits = 0-999_999)
    72-127| random          | 54 bits of randomness (variant bits embedded)
    -------------------------------------------------------------------
    Variant is stored in bits 70–71 (byte 8, bits 6–7), set to 0b10 per RFC 4122.
    """
    if timestamp_ms is not None and timestamp_ns is not None:
        raise ValueError("Specify only one of timestamp_ms or timestamp_ns, not both.")

    if (timestamp_ms == 0 and timestamp_ns is None) or (
        timestamp_ns == 0 and timestamp_ms is None
    ):
        return UUID("00000000-0000-0000-0000-000000000000")

    if timestamp_ns is not None:
        timestamp_ns = int(timestamp_ns)
    elif timestamp_ms is not None:
        timestamp_ns = int(timestamp_ms * 1_000_000_000)
    else:
        timestamp_ns = time.time_ns()

    if timestamp_ns < 0:
        raise ValueError("Timestamp must be positive.")

    timestamp_ms = timestamp_ns // 1_000_000
    sub_ms_ns = timestamp_ns % 1_000_000  # 20 bits max

    uuid_int = 0
    uuid_int |= (timestamp_ms & ((1 << 48) - 1)) << 80  # Bits 0–47
    uuid_int |= 0x7 << 76  # Bits 48–51 (version 7)
    uuid_int |= (sub_ms_ns & 0xFFFFF) << 56  # Bits 52–71 (20 bits)

    random_bits = secrets.randbits(54)  # 54-bit random
    uuid_int |= random_bits

    # Set variant (RFC 4122) in bits 62–63 to 0b10
    uuid_int &= ~(0b11 << 62)
    uuid_int |= 0b10 << 62

    return UUID(int=uuid_int)


# def datetime_to_uuid7(dt: datetime | str) -> UUID:
#     if dt.tzinfo is None:
#         raise ValueError("datetime must be timezone-aware (e.g., UTC)")
#     timestamp_ns = int(dt.timestamp() * 1_000_000_000)
#     return uuid7(timestamp_ns)
#
#
# def uuid7_to_datetime(uuid_obj: UUID) -> Optional[datetime]:
#     if uuid_obj.version != 7:
#         return None
#
#     uuid_int = uuid_obj.int
#     timestamp_ms = (uuid_int >> 80) & ((1 << 48) - 1)
#     sub_ms_ns = (uuid_int >> 56) & 0xFFFFF
#     timestamp_ns = timestamp_ms * 1_000_000 + sub_ms_ns
#     return datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=timezone.utc)


def uuid7_to_datetime(
    uuid: UUID | str, tz: Optional[ZoneInfo | timezone] = UTC
) -> Optional[datetime]:
    """
    Extract the timestamp from a UUIDv7 and return as a datetime.

    Args:
        uuid (uuid.UUID): A UUIDv7-compliant UUID.
        tz (Optional[timezone]): Desired timezone. Defaults to UTC.
                                 Use tz=None for naive datetime.

    Returns:
        datetime: Timestamp extracted from UUIDv7 or None if UUID is not version 7.
    """
    if isinstance(uuid, str):
        uuid = UUID(uuid)

    if uuid.version != 7:
        return None

    # Extract 6 timestamp bytes and convert to full 64-bit int with two zero bytes
    ts_bytes = uuid.bytes[:6] + b"\x00\x00"
    ms_since_epoch = int.from_bytes(ts_bytes, "big") >> 16

    return datetime.fromtimestamp(ms_since_epoch / 1000, tz=tz)


def datetime_to_uuid7(dt: datetime | str) -> UUID:
    """
    Generate a PostgreSQL-compatible UUIDv7 from a given datetime.

    Args:
        dt (datetime | str): The datetime to encode.

    Returns:
        UUID: PostgreSQL-compatible UUIDv7.
    """
    if isinstance(dt, str):
        dt = dt_parse(dt)
    return uuid7(timestamp_ms=dt.timestamp())
