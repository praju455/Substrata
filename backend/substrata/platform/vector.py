"""Portable vector type: pgvector in PostgreSQL, explicit offline JSON in SQLite."""

import json
import math

from sqlalchemy import JSON
from sqlalchemy.types import TypeDecorator, UserDefinedType

DIMENSIONS = 384


class PostgreSQLVector(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kw):
        return f"VECTOR({DIMENSIONS})"


class Embedding(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(
            PostgreSQLVector() if dialect.name == "postgresql" else JSON()
        )

    def process_bind_param(self, value, dialect):
        if len(value) != DIMENSIONS or any(not math.isfinite(v) for v in value):
            raise ValueError("Embedding must have 384 finite dimensions.")
        return json.dumps(value) if dialect.name == "postgresql" else value

    def process_result_value(self, value, dialect):
        return json.loads(value) if isinstance(value, str) else value
