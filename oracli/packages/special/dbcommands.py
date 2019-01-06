import logging
import os
import platform
from oracli import __version__
from oracli.packages.special import iocommands
from oracli.packages.special.utils import format_uptime
from .main import special_command, RAW_QUERY, PARSED_QUERY

log = logging.getLogger(__name__)



DATABASES_QUERY = '''select distinct(owner) from all_tables'''
TABLES_QUERY = '''select distinct(table_name) from all_tab_cols where owner='%s' '''
VERSION_QUERY = '''select * from V$VERSION'''
VERSION_COMMENT_QUERY = '''select * from V$VERSION'''
USERS_QUERY = '''select username from all_users'''
FUNCTIONS_QUERY = '''select object_name from ALL_OBJECTS where owner='%s' and object_type in ('FUNCTION','PROCEDURE')'''
ALL_TABLE_COLUMNS_QUERY = '''select table_name, column_name from all_tab_cols where owner='%s' '''
COLUMNS_QUERY = '''select column_name, data_type, data_length, nullable from all_tab_cols where owner='%s' and table_name='%s' '''
CONNECTION_ID_QUERY = '''select sys_context('USERENV', 'SID') from dual'''
CURRENT_SCHEMA_QUERY = '''select sys_context('USERENV', 'CURRENT_SCHEMA') from dual'''


def _resolve_table(cur, table_desc):
    table_desc = table_desc.upper()
    table_tokens = table_desc.split('.', 1)

    if len(table_tokens) == 2:
        return table_tokens  # schema and table

    # get the current schema
    log.debug(CURRENT_SCHEMA_QUERY)
    cur.execute(CURRENT_SCHEMA_QUERY)
    current_schema = cur.fetchall()[0][0]

    return current_schema, table_desc


@special_command('describe', 'desc[+] [schema.table]', 'describe table.',
                 arg_type=PARSED_QUERY, case_sensitive=False, aliases=['desc'])
def describe(cur, arg, arg_type=PARSED_QUERY, verbose=True):

    schema, table = _resolve_table(cur, arg)

    query = COLUMNS_QUERY % (schema, table)

    log.debug(query)
    cur.execute(query)
    tables = cur.fetchall()
    status = ''

    if cur.description:
        headers = [x[0] for x in cur.description]
        return [(None, tables, headers, status)]
    else:
        return [(None, None, None, '')]

@special_command('list', '\\l', 'List databases.', arg_type=RAW_QUERY, case_sensitive=True)
def list_databases(cur, **_):
    log.debug(DATABASES_QUERY)
    cur.execute(DATABASES_QUERY)
    if cur.description:
        headers = [x[0] for x in cur.description]
        return [(None, cur, headers, '')]
    else:
        return [(None, None, None, '')]

# @special_command('status', '\\s', 'Get status information from the server.',
#                  arg_type=RAW_QUERY, aliases=('\\s', ), case_sensitive=True)
def status(cur, **_):
    query = 'SHOW GLOBAL STATUS;'
    log.debug(query)
    cur.execute(query)
    status = dict(cur.fetchall())

    query = 'SHOW GLOBAL VARIABLES;'
    log.debug(query)
    cur.execute(query)
    variables = dict(cur.fetchall())

    # Create output buffers.
    title = []
    output = []
    footer = []

    title.append('--------------')

    # Output the oracli client information.
    implementation = platform.python_implementation()
    version = platform.python_version()
    client_info = []
    client_info.append('oracli {0},'.format(__version__))
    client_info.append('running on {0} {1}'.format(implementation, version))
    title.append(' '.join(client_info) + '\n')

    # Build the output that will be displayed as a table.
    output.append(('Connection id:', cur.connection.thread_id()))

    query = 'SELECT DATABASE(), USER();'
    log.debug(query)
    cur.execute(query)
    db, user = cur.fetchone()
    if db is None:
        db = ''

    output.append(('Current database:', db))
    output.append(('Current user:', user))

    if iocommands.is_pager_enabled():
        if 'PAGER' in os.environ:
            pager = os.environ['PAGER']
        else:
            pager = 'System default'
    else:
        pager = 'stdout'
    output.append(('Current pager:', pager))

    output.append(('Server version:', '{0} {1}'.format(
        variables['version'], variables['version_comment'])))
    output.append(('Protocol version:', variables['protocol_version']))

    if 'unix' in cur.connection.host_info.lower():
        host_info = cur.connection.host_info
    else:
        host_info = '{0} via TCP/IP'.format(cur.connection.host)

    output.append(('Connection:', host_info))

    query = ('SELECT @@character_set_server, @@character_set_database, '
             '@@character_set_client, @@character_set_connection LIMIT 1;')
    log.debug(query)
    cur.execute(query)
    charset = cur.fetchone()
    output.append(('Server characterset:', charset[0]))
    output.append(('Db characterset:', charset[1]))
    output.append(('Client characterset:', charset[2]))
    output.append(('Conn. characterset:', charset[3]))

    if 'TCP/IP' in host_info:
        output.append(('TCP port:', cur.connection.port))
    else:
        output.append(('UNIX socket:', variables['socket']))

    output.append(('Uptime:', format_uptime(status['Uptime'])))

    # Print the current server statistics.
    stats = []
    stats.append('Connections: {0}'.format(status['Threads_connected']))
    stats.append('Queries: {0}'.format(status['Queries']))
    stats.append('Slow queries: {0}'.format(status['Slow_queries']))
    stats.append('Opens: {0}'.format(status['Opened_tables']))
    stats.append('Flush tables: {0}'.format(status['Flush_commands']))
    stats.append('Open tables: {0}'.format(status['Open_tables']))
    queries_per_second = int(status['Queries']) / int(status['Uptime'])
    stats.append('Queries per second avg: {:.3f}'.format(queries_per_second))
    stats = '  '.join(stats)
    footer.append('\n' + stats)

    footer.append('--------------')
    return [('\n'.join(title), output, '', '\n'.join(footer))]
