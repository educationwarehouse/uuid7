import datetime as dt
import uuid
from uuid import UUID

import pytest

# Import the module being tested
from src.edwh_uuid7 import datetime_to_uuid7, uuid7, uuid7_to_datetime


def test_uuid7_structure():
    """Test that uuid7 returns a properly structured UUID with the correct version and variant."""
    result = uuid7()

    # Check that it's a UUID object
    assert isinstance(result, UUID)

    # Check version and variant
    assert result.version == 7
    assert (result.bytes[8] >> 6) == 2  # Variant 1 - first two bits are 10


def test_uuid7_to_datetime_invalid_version():
    """Test uuid7_to_datetime with a non-v7 UUID."""
    # Create a non-v7 UUID
    non_v7_uuid = uuid.uuid4()

    result = uuid7_to_datetime(non_v7_uuid)

    assert result is None


def test_uuid7_invalid_args():
    with pytest.raises(ValueError):
        uuid7(0, 0)

    with pytest.raises(ValueError):
        uuid7(1000, 1000)

    with pytest.raises(ValueError):
        uuid7(timestamp_ms=-1)

    with pytest.raises(ValueError):
        uuid7(timestamp_ns=-1)


def test_uuid7_uniqueness():
    """Test that multiple calls to uuid7() generate unique UUIDs."""
    uuids = [uuid7() for _ in range(1000)]
    unique_uuids = set(uuids)
    assert len(unique_uuids) == 1000


def test_uuid7_datetime_roundtrip_naive():
    """Test that datetime_to_uuid7 and uuid7_to_datetime are inverse operations."""
    dt_now = dt.datetime.now()
    uuid_now = datetime_to_uuid7(dt_now)
    dt_recovered = uuid7_to_datetime(uuid_now, None)
    dt_recovered2 = uuid7_to_datetime(str(uuid_now), None)
    assert dt_recovered == dt_recovered2

    # pg_uuidv7's uuid_v7_to_timestamptz('01968be2-8c27-7490-b004-770b1dc4796f') -> 2025-05-01 12:46:42.215000 +00:00
    # -> dt_now and dt_recovered will not be == but they should have less than a ms difference:
    delta = abs(dt_now.timestamp() - dt_recovered.timestamp())

    assert delta < 0.001, f"{dt_now} != {dt_recovered}"


def test_uuid7_datetime_roundtrip_utc():
    """Test that datetime_to_uuid7 and uuid7_to_datetime are inverse operations."""
    dt_now = dt.datetime.now(dt.UTC)
    uuid_now = datetime_to_uuid7(dt_now)
    dt_recovered = uuid7_to_datetime(uuid_now)
    dt_recovered2 = uuid7_to_datetime(uuid_now, dt.UTC)
    assert dt_recovered == dt_recovered2

    # pg_uuidv7's uuid_v7_to_timestamptz('01968be2-8c27-7490-b004-770b1dc4796f') -> 2025-05-01 12:46:42.215000 +00:00
    # -> dt_now and dt_recovered will not be == but they should have less than a ms difference:
    delta = abs(dt_now.timestamp() - dt_recovered.timestamp())

    assert delta < 0.001, f"{dt_now} != {dt_recovered}"


def test_uuid7_datetime_roundtrip_timezone():
    # without utc:
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("Europe/Amsterdam")
    dt_now = dt.datetime.now(tz)
    uuid_now = datetime_to_uuid7(dt_now)
    dt_recovered = uuid7_to_datetime(uuid_now, tz=tz)

    delta = abs(dt_now.timestamp() - dt_recovered.timestamp())
    assert delta < 0.001, f"{dt_now} != {dt_recovered}"


def test_uuid7_monotonicity_with_ms_ts():
    """Test that UUIDs are monotonically increasing when generated in sequence."""
    # Generate UUIDs with increasing timestamps
    uuids = [str(uuid7(i)) for i in range(1000, 2000)]

    # Check they're in ascending order
    assert uuids == sorted(uuids)


def test_uuid7_datetime_high_precision():
    """Test that high_precision mode extracts microsecond precision correctly."""
    # Create UUIDs with specific nanosecond values to test precision
    test_cases = [
        (123456789, 123456),  # Nanoseconds, expected microseconds
        (123100000, 123100),
        (123456000, 123456),
        (999999000, 999999),  # Max value for microseconds
    ]

    for ns_value, expected_micros in test_cases:
        # Generate UUIDs with specific nanosecond timestamps
        specific_uuid = uuid7(timestamp_ns=ns_value)

        # Extract datetime with default precision (millisecond)
        dt_default = uuid7_to_datetime(specific_uuid)

        # Extract datetime with high precision (microsecond)
        dt_high_precision = uuid7_to_datetime(specific_uuid, high_precision=True)

        # Verify default precision truncates to milliseconds
        assert dt_default.microsecond == (ns_value // 1_000_000) * 1000

        # Verify high precision preserves microseconds
        assert dt_high_precision.microsecond == expected_micros

        # Timestamps should be different due to added precision
        assert dt_default != dt_high_precision

        # But the millisecond part should match
        assert dt_default.replace(microsecond=0) == dt_high_precision.replace(microsecond=0)


def test_uuid7_datetime_roundtrip_high_precision():
    """Test that datetime_to_uuid7 and uuid7_to_datetime with high_precision have better precision."""
    dt_now = dt.datetime.now(dt.UTC)
    uuid_now = datetime_to_uuid7(dt_now)

    # Compare recovery with and without high precision
    dt_recovered_standard = uuid7_to_datetime(uuid_now)
    dt_recovered_high_precision = uuid7_to_datetime(uuid_now, high_precision=True)

    # Standard precision should be within 1ms
    delta_standard = abs(dt_now.timestamp() - dt_recovered_standard.timestamp())
    assert delta_standard < 0.001

    # High precision should be within 1µs (microsecond)
    delta_high_precision = abs(dt_now.timestamp() - dt_recovered_high_precision.timestamp())
    assert delta_high_precision < 0.000001

    # High precision should be more accurate than standard precision
    assert delta_high_precision < delta_standard

def test_uuid7_monotonicity_with_ns_ts():
    """
    Test that UUIDs are monotonically increasing when generated in sequence.

    Note:
    UUIDv7 encodes time as:
    - 48 bits for milliseconds since Unix epoch
    - 20 bits for sub-millisecond precision (fractional nanoseconds: 0–999_999 ns)

    This limits the temporal resolution to 1,000,000 distinct values per millisecond,
    i.e., 1 microsecond (μs) precision within the millisecond.

    Therefore, UUIDv7 cannot guarantee sort order accuracy for sequences generated
    with less than 1μs (i.e., <1000ns) increments. This test steps by 1000ns (1μs),
    which is the finest resolution UUIDv7 can fully encode in its 20-bit sub-ms field.
    """
    uuids = [str(uuid7(timestamp_ns=i)) for i in range(100_000, 200_000, 1000)]

    # Check they're in ascending order
    assert uuids == sorted(uuids)


def test_uuid7_monotonicity_subms():
    """Test that UUIDs are monotonically increasing when generated in sequence."""
    # Generate UUIDs with increasing timestamps
    uuids = [str(uuid7()) for _ in range(1000)]

    # Check they're in ascending order
    assert uuids == sorted(uuids)


def test_uuid7_special_case_0():
    assert uuid7(0) == UUID("00000000-0000-0000-0000-000000000000")


def test_uuid7_at_specific_date():
    assert str(datetime_to_uuid7("1970-01-01 00:00:00.001+00")).startswith(
        "00000000-0001-7"
    )

    assert str(datetime_to_uuid7("2025-05-01 00:00:00.001+00")).startswith("01968")
