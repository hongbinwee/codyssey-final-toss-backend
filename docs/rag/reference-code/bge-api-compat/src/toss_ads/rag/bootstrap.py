"""Create the isolated RAG schema and its restricted runtime role."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_SQL = ROOT / "deploy/product-rag.sql"
RAG_ROLE = "rag_runtime"


def create_schema(connection: psycopg.Connection) -> None:
    lines = [
        line
        for line in SCHEMA_SQL.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("--")
    ]
    for statement in "\n".join(lines).split(";"):
        if statement.strip():
            connection.execute(statement)
    versions = dict(
        connection.execute(
            "SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector', 'pg_search')"
        ).fetchall()
    )
    expected = {"vector": "0.8.7", "pg_search": "0.26.0"}
    if versions != expected:
        raise RuntimeError("database_extension_version_mismatch")


def bootstrap_database(admin_database_url: str, rag_password: str) -> None:
    if not admin_database_url.startswith(("postgresql://", "postgres://")):
        raise ValueError("invalid_admin_database_url")
    if not isinstance(rag_password, str) or len(rag_password) < 24:
        raise ValueError("rag_role_password_must_be_at_least_24_characters")
    role = sql.Identifier(RAG_ROLE)
    with psycopg.connect(admin_database_url) as connection:
        database_name = connection.execute("SELECT current_database()").fetchone()[0]
        if database_name != "toss_rag":
            raise ValueError("unexpected_database_name")
        create_schema(connection)
        exists = connection.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s", (RAG_ROLE,)
        ).fetchone()
        statement = sql.SQL("{} ROLE {} LOGIN PASSWORD {} NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS").format(
            sql.SQL("ALTER") if exists else sql.SQL("CREATE"),
            role,
            sql.Literal(rag_password),
        )
        connection.execute(statement)
        memberships = connection.execute(
            """
            SELECT granted_role.rolname
            FROM pg_auth_members AS membership
            JOIN pg_roles AS member_role ON member_role.oid = membership.member
            JOIN pg_roles AS granted_role ON granted_role.oid = membership.roleid
            WHERE member_role.rolname = %s
            """,
            (RAG_ROLE,),
        ).fetchall()
        for (granted_role,) in memberships:
            connection.execute(
                sql.SQL("REVOKE {} FROM {}").format(
                    sql.Identifier(granted_role), role
                )
            )
        connection.execute(sql.SQL("GRANT CONNECT ON DATABASE toss_rag TO {}").format(role))
        connection.execute(sql.SQL("GRANT USAGE ON SCHEMA rag TO {}").format(role))
        connection.execute(
            sql.SQL("GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA rag TO {}").format(role)
        )
        has_pdb = connection.execute(
            "SELECT to_regnamespace('pdb') IS NOT NULL"
        ).fetchone()[0]
        if has_pdb:
            connection.execute(sql.SQL("GRANT USAGE ON SCHEMA pdb TO {}").format(role))
        connection.execute(
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES IN SCHEMA rag "
                "GRANT SELECT, INSERT, UPDATE ON TABLES TO {}"
            ).format(role)
        )
def main() -> int:
    admin_url = os.getenv("RAG_ADMIN_DATABASE_URL", "")
    rag_password = os.getenv("RAG_ROLE_PASSWORD", "")
    try:
        bootstrap_database(admin_url, rag_password)
    except Exception:
        print("status=error code=database_bootstrap_failed")
        return 1
    print("status=ready schema=rag role=rag_runtime")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
