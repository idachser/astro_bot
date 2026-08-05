import logging
import sqlite3 as sq3
from sqlite3 import Error

logger = logging.getLogger(__name__)


def create_connection(db: str) -> sq3.Connection | None:
    """None when the file cannot be opened -- an unwritable volume or a
    bad DB path. Every caller already guards on that; without the guard
    the error escaped through `get_user_profile` into a day handler that
    catches nothing, and the user got no reply at all instead of a
    message saying to try later."""

    try:
        return sq3.connect(db)
    except Error as err:
        logger.exception(f"DB CONNECT Error: {err}")
        return None


def execute_query(conn: sq3.Connection, sql: str, params=()) -> None:
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        conn.commit()
    except Error as err:
        logger.exception(f"DB EXECUTE Query Error: {err}")


def execute_read(conn: sq3.Connection, sql: str, params=()) -> list:
    cursor = conn.cursor()
    result = []
    try:
        cursor.execute(sql, params)
        result = cursor.fetchall()
    except Error as err:
        logger.exception(f"DB READ Error: {err}")
    return result


def db_init(db: str, sql: str) -> None:
    conn = create_connection(db)
    if conn:
        execute_query(conn, sql)
        conn.close()
        logger.info("DB inited successfully")


def write_into_db(db: str, sql: str, data: tuple = ()) -> None:
    conn = create_connection(db)
    if conn:
        execute_query(conn, sql, data)
        conn.close()


def read_from_db(db: str, sql: str, params=()) -> list:
    conn = create_connection(db)
    if conn:
        data = execute_read(conn, sql, params)
        conn.close()
        return data
    return []
