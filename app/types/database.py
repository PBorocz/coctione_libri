from contextlib import contextmanager
from typing import TypeVar

import anodb
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class Database:
    def __init__(self):
        self._db = None

    def init_app(self, app) -> str:
        driver, path_ = app.config["SQLITE_DB"].split(":")
        self._db = anodb.DB(driver, path_, "app/sql/sql.sql", conn_kwargs={"autocommit": True})
        return path_

    def __getattr__(self, name):
        """Proxy all database methods to the actual connection."""
        if self._db is None:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        return getattr(self._db, name)

    @contextmanager
    def with_row_factory(self, model_class: type[T]):
        # Save original factory
        original_factory = self._db._conn.row_factory

        # Set pydantic factory
        def pydantic_factory(cursor, row):
            if cursor.description:  # Check if there are columns
                columns = [col[0] for col in cursor.description]
                return model_class.factory(**dict(zip(columns, row)))
            return row

        self._db._conn.row_factory = pydantic_factory

        try:
            yield self
        finally:
            # Restore original factory
            self._db._conn.row_factory = original_factory
