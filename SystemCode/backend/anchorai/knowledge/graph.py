from functools import lru_cache
from typing import Any

from neo4j import Driver, GraphDatabase, ManagedTransaction
from neo4j.exceptions import AuthError, ServiceUnavailable, SessionExpired

from anchorai.config import get_settings

GraphUnavailable = (ServiceUnavailable, SessionExpired, AuthError, OSError)


@lru_cache
def get_driver() -> Driver:
    s = get_settings()
    # Fail fast: the driver otherwise retries for ~60 s and the page that asked stalls.
    return GraphDatabase.driver(
        s.neo4j_uri,
        auth=(s.neo4j_user, s.neo4j_password),
        connection_timeout=3,
        connection_acquisition_timeout=3,
        max_transaction_retry_time=0,
    )


def neo4j_available(driver: Driver | None = None) -> bool:
    try:
        (driver or get_driver()).verify_connectivity()
    except GraphUnavailable:
        return False
    return True


def read(query: str, driver: Driver | None = None, **params: Any) -> list[dict[str, Any]]:
    """Run a query in a read transaction; Neo4j rejects any write inside it."""

    def work(tx: ManagedTransaction) -> list[dict[str, Any]]:
        return [record.data() for record in tx.run(query, params)]

    with (driver or get_driver()).session(default_access_mode="READ") as session:
        return session.execute_read(work)


def read_records(query: str, driver: Driver | None = None, **params: Any) -> list[Any]:
    """Like `read`, but keeps graph objects (nodes, paths) instead of plain dicts."""

    def work(tx: ManagedTransaction) -> list[Any]:
        return list(tx.run(query, params))

    with (driver or get_driver()).session(default_access_mode="READ") as session:
        return session.execute_read(work)
