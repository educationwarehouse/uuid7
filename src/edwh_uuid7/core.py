"""
uuid7pg: PostgreSQL-compatible UUIDv7 generator for Python

This module provides utilities for generating and interpreting
UUIDv7 identifiers compatible with PostgreSQL extensions that
follow the timestamp-left-shifted format.
"""

import os
import time
from uuid import UUID
from datetime import datetime, timezone, UTC
from typing import Optional
from zoneinfo import ZoneInfo
from dateutil.parser import parse as dt_parse


def uuid7(ms: Optional[int | float] = None) -> UUID:
    """
    Generate a UUIDv7 compatible with PostgreSQL format.

    This uses a Unix epoch timestamp in milliseconds (default: now),
    left-shifted by 16 bits, with the top 48 bits stored in the UUID timestamp field.

    Args:
        ms (Optional[int | float]): Milliseconds since Unix epoch. If None, uses current time.

    Returns:
        UUID: A version 7, variant 1 UUID.
    """
    if isinstance(ms, int) and ms == 0:
        # special case which stevesimmons/uuid7 also has:
        return UUID('00000000-0000-0000-0000-000000000000')

    # Get current time in nanoseconds for maximum precision
    now_ns = time.time_ns()

    if ms is None:
        ms = now_ns / 1_000_000_000  # Convert ns to seconds

    # Convert to milliseconds
    ms_int = int(ms * 1000)

    # Timestamp bytes (48 bits)
    timestamp_bytes = (ms_int << 16).to_bytes(8, 'big')[:6]

    # Use nanosecond precision to ensure monotonicity
    # We'll use the last 12 digits of nanoseconds as our "serial" number
    # This should be unique and monotonic for rapid generations
    serial = now_ns % 1_000_000_000  # 0-999,999,999

    # Create random bytes
    rand = bytearray(10)

    # Put most significant bits of serial in the first byte (after version bits)
    rand[0] = (serial >> 32) & 0x0F

    # Fill the next 4 bytes with the remainder of the serial for monotonicity
    rand[1] = (serial >> 24) & 0xFF
    rand[2] = ((serial >> 16) & 0x3F) | 0x80  # Include variant bits
    rand[3] = (serial >> 8) & 0xFF
    rand[4] = serial & 0xFF

    # Fill the remaining bytes with random data
    random_bytes = os.urandom(5)
    rand[5:] = random_bytes

    # Set version bits
    rand[0] = (rand[0] & 0x0F) | 0x70  # version 7

    uuid_bytes = timestamp_bytes + rand
    return UUID(bytes=bytes(uuid_bytes))

def uuid7_to_datetime(u: UUID, tz: Optional[ZoneInfo | timezone] = UTC) -> Optional[datetime]:
    """
    Extract the timestamp from a UUIDv7 and return as a datetime.

    Args:
        u (uuid.UUID): A UUIDv7-compliant UUID.
        tz (Optional[timezone]): Desired timezone. Defaults to UTC.
                                 Use tz=None for naive datetime.

    Returns:
        datetime: Timestamp extracted from UUIDv7 or None if UUID is not version 7.
    """
    if u.version != 7:
        return None

    # Extract 6 timestamp bytes and convert to full 64-bit int with two zero bytes
    ts_bytes = u.bytes[:6] + b'\x00\x00'
    ms_since_epoch = int.from_bytes(ts_bytes, 'big') >> 16

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
    return uuid7(dt.timestamp())
