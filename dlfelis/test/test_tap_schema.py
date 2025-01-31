# Licensed under a BSD-style 3-clause license - see LICENSE.md.
# -*- coding: utf-8 -*-
"""Test dlfelis.tap_schema.
"""
import logging
import subprocess
import sys
from ..tap_schema import validate, _options


class MockPopen(object):
    """Simulate the behavior of subprocess.Popen.
    """

    def __init__(self, command, stdout, stderr):
        self.command = command
        self.filename = self.command[-1]
        self.stdout = stdout
        self.stderr = stderr
        if self.filename == 'failure.json':
            self.returncode = 1
        else:
            self.returncode = 0
        return

    def communicate(self):
        if self.filename == 'failure.json':
            return ("some output".encode('utf-8'),
                    (f"INFO:felis:Validating {self.filename}\n" +
                    "ERROR:felis:Some sort of error!\n").encode('utf-8'))
        else:
            return (''.encode('utf-8'),
                    f"INFO:felis:Validating {self.filename}\n".encode('utf-8'))


def test__options(monkeypatch):
    """Test option processing
    """
    monkeypatch.setattr(sys, 'argv', ['convert_tap_schema', 'sdss_dr12.json'])
    foo = _options()
    assert not foo.debug
    assert foo.json == 'sdss_dr12.json'


def test_validate(monkeypatch, caplog):
    """Test running felis validate.
    """
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(subprocess, 'Popen', MockPopen)
    status = validate('success.json')
    assert status == 0
    assert caplog.record_tuples == []
    status = validate('failure.json')
    assert status == 1
    assert caplog.record_tuples == [('dlfelis.tap_schema.validate', logging.ERROR,
                                     'STDOUT ='),
                                    ('dlfelis.tap_schema.validate', logging.ERROR,
                                     'some output'),
                                    ('dlfelis.tap_schema.validate', logging.ERROR,
                                     'STDERR ='),
                                    ('dlfelis.tap_schema.validate', logging.ERROR,
                                     'INFO:felis:Validating failure.json\n'
                                    'ERROR:felis:Some sort of error!\n')]
