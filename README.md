# edwh-uuid7

A Python implementation of [pg_uuidv7](https://pgxn.org/dist/pg_uuidv7/), providing PostgreSQL-compatible UUIDv7
generation and conversion to/from `datetime`.

## Overview

UUIDv7 is a time-sortable UUID format composed of:

- **48 bits**: Unix timestamp in milliseconds (`datetime`)
- **4 bits**: Version (`0111` for UUIDv7)
- **12 bits**: Sub-millisecond randomness
- **62 bits**: Additional randomness

This makes UUIDv7 globally sortable by creation time while retaining enough entropy for distributed uniqueness.

The `edwh-uuid7` package provides:

- UUIDv7 generation compatible with `pg_uuidv7`’s `uuid_generate_v7()`
- Round-trip conversion between `UUIDv7` and `datetime`
- Optional timezone-aware conversion

## Why this package?

The standard [`uuid7`](https://pypi.org/project/uuid7/) Python package uses a different timestamp scheme (based
on [RFC 4122](https://datatracker.ietf.org/doc/html/rfc4122) drafts), which is **not compatible** with the PostgreSQL
`pg_uuidv7` extension. This library matches the behavior and binary format of PostgreSQL's implementation, including
millisecond-level timestamp encoding.

## Installation

```bash
pip install edwh-uuid7
