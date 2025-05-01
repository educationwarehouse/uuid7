import uuid
import datetime as dt
from uuid import UUID

from dateutil.parser import parse as dt_parse

# Import the module being tested
from src.edwh_uuid7 import uuid7, uuid7_to_datetime, datetime_to_uuid7


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

def test_uuid7_monotonicity_with_ts():
    """Test that UUIDs are monotonically increasing when generated in sequence."""
    # Generate UUIDs with increasing timestamps
    uuids = [str(uuid7(i)) for i in range(1000, 2000)]

    # Check they're in ascending order
    assert uuids == sorted(uuids)

def test_uuid7_monotonicity_subms():
    """Test that UUIDs are monotonically increasing when generated in sequence."""
    # Generate UUIDs with increasing timestamps
    uuids = [str(uuid7()) for _ in range(1000)]

    # Check they're in ascending order
    assert uuids == sorted(uuids)

def test_uuid7_special_case_0():
    assert uuid7(0) == UUID('00000000-0000-0000-0000-000000000000')


def test_uuid7_at_specific_date():
    assert str(datetime_to_uuid7('1970-01-01 00:00:00.001+00')).startswith("00000000-0001-7")

    assert str(datetime_to_uuid7('2025-05-01 00:00:00.001+00')).startswith("01968")
