# coding: utf-8
import os
import stat
import tempfile

import pytest

import ocli.packages.special
from ocli.packages.special.main import CommandNotFound
from utils import db_connection, dbtest


def test_set_get_pager():
    ocli.packages.special.set_pager_enabled(True)
    assert ocli.packages.special.is_pager_enabled()
    ocli.packages.special.set_pager_enabled(False)
    assert not ocli.packages.special.is_pager_enabled()
    ocli.packages.special.set_pager('less')
    assert os.environ['PAGER'] == "less"
    ocli.packages.special.set_pager(False)
    assert os.environ['PAGER'] == "less"
    del os.environ['PAGER']
    ocli.packages.special.set_pager(False)
    ocli.packages.special.disable_pager()
    assert not ocli.packages.special.is_pager_enabled()


def test_set_get_timing():
    ocli.packages.special.set_timing_enabled(True)
    assert ocli.packages.special.is_timing_enabled()
    ocli.packages.special.set_timing_enabled(False)
    assert not ocli.packages.special.is_timing_enabled()


def test_set_get_expanded_output():
    ocli.packages.special.set_expanded_output(True)
    assert ocli.packages.special.is_expanded_output()
    ocli.packages.special.set_expanded_output(False)
    assert not ocli.packages.special.is_expanded_output()


def test_editor_command():
    assert ocli.packages.special.editor_command(r'ed hello')
    assert not ocli.packages.special.editor_command(r'hello')

    assert ocli.packages.special.get_filename(r'ed filename') == "filename"

    os.environ['EDITOR'] = 'true'
    ocli.packages.special.open_external_editor(r'select 1') == "select 1"


def test_spool_command():
    ocli.packages.special.write_tee(u"hello world")  # write without file set
    with tempfile.NamedTemporaryFile() as f:
        ocli.packages.special.execute(None, u"spool " + f.name)
        ocli.packages.special.write_tee(u"hello world")
        assert f.read() == b"hello world"

        ocli.packages.special.execute(None, u"spool -o " + f.name)
        ocli.packages.special.write_tee(u"hello world")
        f.seek(0)
        assert f.read() == b"hello world"

        ocli.packages.special.execute(None, u"nospool")
        ocli.packages.special.write_tee(u"hello world")
        f.seek(0)
        assert f.read() == b"hello world"


def test_tee_command_error():
    with pytest.raises(TypeError):
        ocli.packages.special.execute(None, 'tee')

    with pytest.raises(OSError):
        with tempfile.NamedTemporaryFile() as f:
            os.chmod(f.name, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
            ocli.packages.special.execute(None, 'tee {}'.format(f.name))


@dbtest
def test_favorite_query():
    with db_connection().cursor() as cur:
        query = u'select "✔"'
        ocli.packages.special.execute(cur, u'\\fs check {0}'.format(query))
        assert next(ocli.packages.special.execute(
            cur, u'\\f check'))[0] == "> " + query


def test_once_command():
    with pytest.raises(TypeError):
        ocli.packages.special.execute(None, u"\once")

    ocli.packages.special.execute(None, u"\once /proc/access-denied")
    with pytest.raises(OSError):
        ocli.packages.special.write_once(u"hello world")

    ocli.packages.special.write_once(u"hello world")  # write without file set
    with tempfile.NamedTemporaryFile() as f:
        ocli.packages.special.execute(None, u"\once " + f.name)
        ocli.packages.special.write_once(u"hello world")
        assert f.read() == b"hello world\n"

        ocli.packages.special.execute(None, u"\once -o " + f.name)
        ocli.packages.special.write_once(u"hello world")
        f.seek(0)
        assert f.read() == b"hello world\n"

