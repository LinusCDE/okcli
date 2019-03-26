import logging

import sql.connection
import sql.parse

from .main import OCli

_logger = logging.getLogger(__name__)


def load_ipython_extension(ipython):

    # This is called via the ipython command '%load_ext ocli.magic'.

    # First, load the sql magic if it isn't already loaded.
    if not ipython.find_line_magic('sql'):
        ipython.run_line_magic('load_ext', 'sql')

    # Register our own magic.
    ipython.register_magic_function(ocli_line_magic, 'line', 'ocli')


def ocli_line_magic(line):
    _logger.debug('ocli magic called: %r', line)
    parsed = sql.parse.parse(line, {})
    conn = sql.connection.Connection.get(parsed['connection'])

    try:
        # A corresponding ocli object already exists
        ocli = conn._ocli
        _logger.debug('Reusing existing ocli')
    except AttributeError:
        ocli = OCli()
        u = conn.session.engine.url
        _logger.debug('New ocli: %r', str(u))

        ocli.connect(u.database, u.host, u.username, u.password)
        conn._ocli = ocli

    # For convenience, print the connection alias
    print('Connected: {}'.format(conn.name))

    try:
        ocli.run_cli()
    except SystemExit:
        pass

    if not ocli.query_history:
        return

    q = ocli.query_history[-1]
    if q.mutating:
        _logger.debug('Mutating query detected -- ignoring')
        return

    if q.successful:
        ipython = get_ipython()
        return ipython.run_cell_magic('sql', line, q.query)

