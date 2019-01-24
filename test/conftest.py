import pytest
from utils import (
    HOST,
    USER,
    PASSWORD,
    SCHEMA,
    CHARSET,
    db_connection)
import oracli.sqlexecute


@pytest.yield_fixture(scope="function")
def connection():
    connection = db_connection()
    yield connection
    connection.close()


@pytest.fixture
def cursor(connection):
    with connection.cursor() as cur:
        return cur


@pytest.fixture
def executor(connection):
    return oracli.sqlexecute.SQLExecute(
        database=SCHEMA, user=USER,
        host=HOST, password=PASSWORD, port=666, charset=CHARSET)
