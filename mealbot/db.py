import logging

from mealbot.config import get_database_url

logger = logging.getLogger(__name__)

# DuplicateKeyErr matches the Go constant used to detect unique constraint violations
DuplicateKeyErr = "duplicate key value violates unique constraint"

# Global connection pool, initialized lazily
_pool = None


def init_pool():
    """Initialize the global connection pool using DATABASE_URL."""
    from psycopg_pool import ConnectionPool

    global _pool
    database_url = get_database_url()
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")
    _pool = ConnectionPool(conninfo=database_url, min_size=1, max_size=10)


def get_pool():
    """Get the global connection pool, initializing if needed."""
    global _pool
    if _pool is None:
        init_pool()
    return _pool


def close_pool():
    """Close the global connection pool."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def get_connection():
    """Get a connection from the pool. Use as a context manager.

    Usage:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT ...")
    """
    return get_pool().connection()


def execute(query, params=None):
    """Execute a query that does not return rows (INSERT, UPDATE, DELETE)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
        conn.commit()


def query_all(query, params=None):
    """Execute a query and return all rows as a list of tuples."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()


def query_one(query, params=None):
    """Execute a query and return a single row, or None."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()
