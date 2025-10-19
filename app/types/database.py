import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import TypeVar

import anodb
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class Database:
    def __init__(self):
        self._anodb = None
        self._driver = None
        self._path = None
        self._sql_dir = None

        # Configure datetime adapters to suppress deprecation warning
        sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
        sqlite3.register_converter("timestamp", lambda b: datetime.fromisoformat(b.decode()))

    def init_app(self, app) -> str:
        driver, path_ = app.config["SQLITE_DB"].split("://")
        self._driver = driver
        self._path = path_
        self._sql_dir = "app/sql/"
        # Create initial connection with check_same_thread=False for thread safety
        self._anodb = anodb.DB(
            driver, path_, self._sql_dir, conn_kwargs={"autocommit": True, "check_same_thread": False}
        )
        return path_

    def __getattr__(self, name):
        """Proxy all database methods to the underlying anodb instance."""
        if self._anodb is None:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        return getattr(self._anodb, name)

    @contextmanager
    def with_row_factory(self, model_class: type[T]):
        # Save original factory
        original_factory = self._anodb._conn.row_factory

        # Set pydantic factory
        def custom_factory(cursor, row):
            if cursor.description:  # Check if there are columns
                columns = [col[0] for col in cursor.description]
                return model_class.factory(**dict(zip(columns, row, strict=True)))
            return row

        self._anodb._conn.row_factory = custom_factory

        try:
            yield self
        finally:
            # Restore original factory
            self._anodb._conn.row_factory = original_factory
