from __future__ import annotations

from neo4j import Driver, GraphDatabase, basic_auth

from .config import AppSettings


def get_neo4j_driver(settings: AppSettings | None = None) -> Driver:
    settings = settings or AppSettings.cached_settings()
    if not settings.neo4j_uri or not settings.neo4j_user or not settings.neo4j_password:
        raise ValueError("Neo4j settings are incomplete")
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=basic_auth(settings.neo4j_user, settings.neo4j_password),
    )


def test_neo4j_connection(settings: AppSettings) -> bool:
    """
    Connects to the configured Neo4j endpoint and performs a smoke query.
    """
    if not settings.neo4j_uri or not settings.neo4j_user or not settings.neo4j_password:
        raise ValueError("Neo4j settings are incomplete")

    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=basic_auth(settings.neo4j_user, settings.neo4j_password),
    )

    try:
        with driver.session() as session:
            session.run("RETURN 1").single()
        return True
    finally:
        driver.close()
