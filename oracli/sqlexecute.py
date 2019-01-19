import logging
import sqlparse
from .packages import special
import cx_Oracle
from oracli.packages.special.dbcommands import (
    TABLES_QUERY,
    VERSION_QUERY,
    VERSION_COMMENT_QUERY,
    USERS_QUERY,
    FUNCTIONS_QUERY,
    ALL_TABLE_COLUMNS_QUERY,
    DATABASES_QUERY,
    CONNECTION_ID_QUERY,
)


_logger = logging.getLogger(__name__)


class SQLExecute(object):

    def __init__(self, database, user, password, host, port, charset):
        self.dbname = database
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.charset = charset
        self._server_type = None
        self.connection_id = None
        self.connect()

    def connect(self, database=None, user=None, password=None, host=None,
            port=None, charset=None):
        db = (database or self.dbname)
        user = (user or self.user)
        password = (password or self.password)
        host = (host or self.host)
        port = (port or self.port)

        charset = (charset or self.charset)
        _logger.debug(''''Connection DB Params:
        database: {database},
        user: {user},
        host: {host},
        port: {port},
        '''.format(**locals()))

        conn = cx_Oracle.connect(user=user, password=password, dsn=host)
        current_schema = db.upper() if db else ''
        if current_schema:
            _logger.info('current_schema {}'.format(current_schema))
            conn.current_schema = str(current_schema) # type-cast required

        if hasattr(self, 'conn'):
            self.conn.close()
        self.conn = conn

        # Update them after the connection is made to ensure that it was a
        # successful connection.
        self.dbname = db
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.charset = charset
        # retrieve connection id
        self.set_connection_id()

    def run(self, statement):
        """Execute the sql in the database and return the results. The results
        are a list of tuples. Each tuple has 4 values
        (title, rows, headers, status).
        """

        # Remove spaces and EOL
        statement = statement.strip()
        if not statement:  # Empty string
            yield (None, None, None, None)

        components = sqlparse.split(statement)

        for sql in components:
            # Remove spaces, eol and semi-colons.
            sql = sql.rstrip(';')

            cur = self.conn.cursor()

            try:   # Special command
                _logger.debug('Trying a dbspecial command. sql: %r', sql)
                for result in special.execute(cur, sql):
                    yield result
            except special.CommandNotFound:  # Regular SQL
                _logger.debug('Regular sql statement. sql: %r', sql)
                cur.execute(sql)
                result = self.get_result(cur)
                yield result

    def get_result(self, cursor):
        """Get the current result's data from the cursor."""
        title = headers = None

        # cursor.description is not None for queries that return result sets,
        # e.g. SELECT or SHOW.
        if cursor.description is not None:
            headers = [x[0] for x in cursor.description]

        return (title, cursor if cursor.description else None, headers, 'Query OK')

    def get_status(self, cursor):
        if isinstance(cursor, list):
            return '' # used for help
        if cursor.description is not None:
            status = '{0} row{1} in set'
        else:
            status = 'Query OK, {0} row{1} affected'
        return status.format(cursor.rowcount,
                             '' if cursor.rowcount == 1 else 's')


    def tables(self, schema=None):
        """Yields table names"""

        cur = self.conn.cursor()
        schema = schema if schema else self.dbname 
        try:
            _logger.debug('Tables Query. sql: %r', TABLES_QUERY)
            # return [x[0] for x in
            #         cur.execute(self.tables_query).fetchall()]
            return [row for row in cur.execute(TABLES_QUERY  % schema)]

        finally:
            cur.close()

    def table_columns(self, schema=None):
        """Yields column names"""
        cur = self.conn.cursor()
        schema = schema if schema else self.dbname 

        try:
            _logger.debug('Columns Query. sql: %r', ALL_TABLE_COLUMNS_QUERY)
            # return [x[0] for x in
            #         cur.execute(self.table_columns_query % self.dbname).fetchall()]
            return [row for row in cur.execute(ALL_TABLE_COLUMNS_QUERY % schema)]
        finally:
            cur.close()

            # for row in cur:
            #     yield row

    def databases(self):
        cur = self.conn.cursor()
        try:

            databases = [x[0] for x in cur.execute(DATABASES_QUERY).fetchall()]
            _logger.debug('Databases Query. {} got {} '.format(DATABASES_QUERY, databases))
            return databases
        finally:
            cur.close()

    def functions(self, schema=None):
        """Yields tuples of (schema_name, function_name)"""
        schema = schema if schema else self.dbname 
        cur = self.conn.cursor()
        try:
            _logger.debug('Functions Query. sql: %r', FUNCTIONS_QUERY)
            return [x[0] for x in
                    cur.execute(FUNCTIONS_QUERY % schema).fetchall()]
            # for row in cur:
            #     yield row
        finally:
            cur.close()

    def users(self):
        cur = self.conn.cursor()
        try:
            _logger.debug('Users Query. sql: %r', USERS_QUERY)
            return [x[0] for x in
                    cur.execute(USERS_QUERY).fetchall()]
        except Exception:
            _logger.error('Could not get user completions', exc_info=True)
        finally:
            cur.close()

    def server_type(self):
        if self._server_type:
            return self._server_type
        cur = self.conn.cursor()
        try:
            _logger.debug('Version Query. sql: %r', VERSION_QUERY)
            cur.execute(VERSION_QUERY)
            version = cur.fetchone()[0]
            _logger.debug('Version Comment. sql: %r', VERSION_COMMENT_QUERY)
            cur.execute(VERSION_COMMENT_QUERY)
            version_comment = cur.fetchone()[0].lower()
        finally:
            cur.close()

        _logger.info('Found  version {} and version comment {}'.format(version, version_comment))

        product_type = 'Oracle-{}'.format(version.split()[2])

        self._server_type = (product_type, version)
        return self._server_type

    def get_connection_id(self):
        if not self.connection_id:
            self.set_connection_id()
        return self.connection_id

    def set_connection_id(self):
        res = self.run(CONNECTION_ID_QUERY)
        for _, cur, _, _ in res:
            self.connection_id = cur.fetchone()[0]
        _logger.debug('Current connection id: {}'.format(self.connection_id))
