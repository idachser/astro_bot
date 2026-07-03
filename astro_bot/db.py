import logging
import sqlite3 as sq3
from sqlite3 import Error


def create_connection(db: str) -> sq3.Connection:
    connection = sq3.connect(db)
    return connection


def execute_query(conn: sq3.Connection, sql: str, params=()) -> None:
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        conn.commit()
    except Error as err:
        logging.exception(f"DB EXECUTE Query Error: {err}")


def execute_many(conn: sq3.Connection, sql: str, rows: list) -> None:
    cursor = conn.cursor()
    try:
        cursor.executemany(sql, rows)
        conn.commit()
    except Error as err:
        logging.exception(f"DB EXECUTE MANY Error: {err}")


def execute_read(conn: sq3.Connection, sql: str, params=()) -> list:
    cursor = conn.cursor()
    result = []
    try:
        cursor.execute(sql, params)
        result = cursor.fetchall()
    except Error as err:
        logging.exception(f"DB READ Error: {err}")
    return result


def db_init(db: str, sql: str) -> None:
    conn = create_connection(db)
    if conn:
        execute_query(conn, sql)
        conn.close()
        logging.info("DB inited successfully")


def write_into_db(db: str, sql: str, data: tuple = ()) -> None:
    conn = create_connection(db)
    if conn:
        execute_query(conn, sql, data)
        conn.close()


def write_many_into_db(db: str, sql: str, rows: list) -> None:
    conn = create_connection(db)
    if conn:
        execute_many(conn, sql, rows)
        conn.close()


def read_from_db(db: str, sql: str, params=()) -> list:
    conn = create_connection(db)
    if conn:
        data = execute_read(conn, sql, params)
        conn.close()
        return data
    return []
