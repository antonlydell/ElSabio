# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Unit tests for the module config.log."""

# Standard library
from pathlib import Path
from typing import Any

# Third party
import pytest

# Local
from elsabio import exceptions
from elsabio.config import log
from elsabio.config.log import (
    LOGGING_DEFAULT_DATETIME_FORMAT,
    LOGGING_DEFAULT_FILE_PATH,
    LOGGING_DEFAULT_FILENAME,
    LOGGING_DEFAULT_FORMAT,
    LOGGING_DEFAULT_FORMAT_DEBUG,
    EmailLogHandler,
    FileLogHandler,
    LoggingConfig,
    LogHandler,
    LogLevel,
    Stream,
    StreamLogHandler,
)

ConfigDict = dict[str, Any]

# ==================================================================================================
# Fixtures
# ==================================================================================================


@pytest.fixture
def log_handler_default_config() -> ConfigDict:
    r"""The default configuration of `LogHandler`."""

    return {
        'disabled': False,
        'min_log_level': LogLevel.INFO,
        'format': LOGGING_DEFAULT_FORMAT,
        'datetime_format': LOGGING_DEFAULT_DATETIME_FORMAT,
    }


# ==================================================================================================
# Tests
# ==================================================================================================


class TestLogHandler:
    r"""Tests for the `LogHandler` model."""

    def test_defaults(self, log_handler_default_config: ConfigDict) -> None:
        r"""Test the default field values."""

        # Setup - None
        # ===========================================================

        # Exercise
        # ===========================================================
        lh = LogHandler()

        # Verify
        # ===========================================================
        assert lh.model_dump() == log_handler_default_config

        # Clean up - None
        # ===========================================================

    def test_init(self) -> None:
        r"""Test to create an instance of `LogHandler`."""

        # Setup
        # ===========================================================
        input_config = {
            'disabled': True,
            'min_log_level': LogLevel.DEBUG,
            'format': 'some format',
            'datetime_format': '%Y-%m',
        }

        # Exercise
        # ===========================================================
        lh = LogHandler.model_validate(input_config)

        # Verify
        # ===========================================================
        assert lh.model_dump() == input_config

        # Clean up - None
        # ===========================================================

    @pytest.mark.parametrize(
        ('min_log_level', '_format'),
        [
            pytest.param('NOTSET', LOGGING_DEFAULT_FORMAT, id='min_log_level=NOTSET'),
            pytest.param('DEBUG', LOGGING_DEFAULT_FORMAT_DEBUG, id='min_log_level=DEBUG'),
            pytest.param('INFO', LOGGING_DEFAULT_FORMAT, id='min_log_level=INFO'),
            pytest.param('WARNING', LOGGING_DEFAULT_FORMAT, id='min_log_level=WARNING'),
            pytest.param('ERROR', LOGGING_DEFAULT_FORMAT, id='min_log_level=ERROR'),
            pytest.param('CRITICAL', LOGGING_DEFAULT_FORMAT, id='min_log_level=CRITICAL'),
        ],
    )
    def test_default_format_with_min_log_level_set(self, min_log_level: str, _format: str) -> None:
        r"""Test the default log format at different log levels."""

        # Setup - None
        # ===========================================================

        # Exercise
        # ===========================================================
        lh = LogHandler(min_log_level=min_log_level)

        # Verify
        # ===========================================================
        assert lh.format == _format

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_invalid_log_level(self) -> None:
        r"""Test to supply an invalid log level."""

        # Setup - None
        # ===========================================================

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            LogHandler(min_log_level='invalid')

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert 'min_log_level' in error_msg

        # Clean up - None
        # ===========================================================


class TestStreamLogHandler:
    r"""Tests for the config model `StreamLogHandler`."""

    @pytest.mark.parametrize(
        ('stream', 'stream_exp'),
        [
            pytest.param(Stream.STDOUT, Stream.STDOUT, id='Stream.STDOUT'),
            pytest.param('stderr', Stream.STDERR, id='str=stderr'),
            pytest.param('stdin', Stream.STDIN, id='str=stdin'),
        ],
    )
    def test_init(
        self, stream: Stream | str, stream_exp: Stream, log_handler_default_config: ConfigDict
    ) -> None:
        r"""Test to create an instance of `StreamLogHandler`."""

        # Setup
        # ===========================================================
        exp_config = {'stream': stream_exp} | log_handler_default_config

        # Exercise
        # ===========================================================
        sh = StreamLogHandler(stream=stream)

        # Verify
        # ===========================================================
        assert sh.model_dump() == exp_config

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_invalid_stream(self) -> None:
        r"""Test to supply an invalid stream."""

        # Setup - None
        # ===========================================================

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            StreamLogHandler(stream='invalid')

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert 'stream' in error_msg

        # Clean up - None
        # ===========================================================


class TestFileLogHandler:
    r"""Tests for the config model `FileLogHandler`."""

    def test_init(self, log_handler_default_config: ConfigDict) -> None:
        r"""Test to create an instance of `FileLogHandler`."""

        # Setup
        # ===========================================================
        input_config = {
            'unique': False,
            'path': Path.cwd() / 'ElSabio.log',
            'max_bytes': 10,
            'backup_count': 5,
            'mode': 'w',
            'encoding': 'Windows-1252',
        }
        exp_config = input_config | log_handler_default_config

        # Exercise
        # ===========================================================
        fh = FileLogHandler.model_validate(input_config)

        # Verify
        # ===========================================================
        assert fh.model_dump() == exp_config

        # Clean up - None
        # ===========================================================

    @pytest.mark.parametrize(
        ('input_path', 'path_exp'),
        [
            pytest.param(
                './ElSabio_test.log',
                (Path() / 'ElSabio_test.log').resolve(),
                id='relative_path',
            ),
            pytest.param(
                '~/ElSabio_test.log',
                (Path.home() / 'ElSabio_test.log').expanduser(),
                id='expanduser',
            ),
        ],
    )
    def test_relative_path_resolved(self, input_path: str, path_exp: Path) -> None:
        r"""Test that a relative log file path is resolved to a full path."""

        # Setup - None
        # ===========================================================

        # Exercise
        # ===========================================================
        fh = FileLogHandler(path=input_path)

        # Verify
        # ===========================================================
        assert fh.path == path_exp

        # Clean up
        # ===========================================================
        path_exp.unlink(missing_ok=True)

    def test_log_dir_created(self, tmp_path: Path) -> None:
        r"""Test that the log file directory is created ."""

        # Setup
        # ===========================================================
        mocked_log_dir = tmp_path / 'log_dir'
        path = mocked_log_dir / 'ElSabio.log'

        # Exercise
        # ===========================================================
        fh = FileLogHandler(path=str(path))

        # Verify
        # ===========================================================
        assert mocked_log_dir.exists(), 'The logging directory does not exist!'
        assert fh.path == path, 'The path field is incorrect!'

        # Clean up - None
        # ===========================================================

    def test_log_file_path_is_dir(self) -> None:
        r"""Test to supply a directory instead of a file to the `path` field.

        The log file path should be the default log filename in the supplied directory.
        """

        # Setup
        # ===========================================================
        path = Path.cwd()
        path_exp = path / LOGGING_DEFAULT_FILENAME

        # Exercise
        # ===========================================================
        fh = FileLogHandler(path=path)

        # Verify
        # ===========================================================
        assert fh.path == path_exp

        # Clean up - None
        # ===========================================================

    def test_unique_default_log_file_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        r"""Test to create a unique log file using the default log file path."""

        # Setup
        # ===========================================================
        uuid = 'uuid'
        filename = LOGGING_DEFAULT_FILE_PATH.name
        path_exp = LOGGING_DEFAULT_FILE_PATH.with_name(f'{uuid}_{filename}')

        monkeypatch.setattr(log, 'uuid4', lambda: uuid)

        # Exercise
        # ===========================================================
        fh = FileLogHandler(unique=True)

        # Verify
        # ===========================================================
        assert fh.path == path_exp

        # Clean up - None
        # ===========================================================

    def test_unique_log_file_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        r"""Test to create a unique log file with a custom log file path."""

        # Setup
        # ===========================================================
        uuid = 'uuid'
        filename = 'ElSabio.log'
        path = Path.cwd() / filename

        filename_exp = f'{uuid}_{filename}'
        path_exp = path.parent / filename_exp

        monkeypatch.setattr(log, 'uuid4', lambda: uuid)

        # Exercise
        # ===========================================================
        fh = FileLogHandler(unique=True, path=path)

        # Verify
        # ===========================================================
        assert fh.path == path_exp

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_negative_max_bytes(self) -> None:
        r"""Test to supply a negative value to the `max_bytes` field."""

        # Setup - None
        # ===========================================================

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            FileLogHandler(max_bytes=-1)

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert 'max_bytes' in error_msg

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_negative_backup_count(self) -> None:
        r"""Test to supply a negative value to the `backup_count` field."""

        # Setup - None
        # ===========================================================

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            FileLogHandler(backup_count=-1)

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert 'backup_count' in error_msg

        # Clean up - None
        # ===========================================================


class TestEmailLogHandler:
    r"""Tests for the config model `EmailLogHandler`."""

    def test_init(self) -> None:
        r"""Test to create an instance of `EmailLogHandler`."""

        # Setup
        # ===========================================================
        input_config = {
            'host': 'test@a7x.com',
            'port': 20,
            'subject': 'My subject',
            'from_address': 'syn@a7x.com',
            'to_addresses': ['mshadows@a7x.com', 'rev@a7x.com'],
            'timeout': 2,
        }
        exp_config = {
            'host': 'test@a7x.com',
            'port': 20,
            'subject': 'My subject',
            'from_address': 'syn@a7x.com',
            'to_addresses': ['mshadows@a7x.com', 'rev@a7x.com'],
            'timeout': 2,
            'disabled': True,
            'min_log_level': LogLevel.WARNING,
            'format': LOGGING_DEFAULT_FORMAT,
            'datetime_format': LOGGING_DEFAULT_DATETIME_FORMAT,
        }

        # Exercise
        # ===========================================================
        eh = EmailLogHandler.model_validate(input_config)

        # Verify
        # ===========================================================
        assert eh.model_dump() == exp_config

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_missing_host(self) -> None:
        r"""Test to not supply the required `host` field."""

        # Setup - None
        # ===========================================================

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            EmailLogHandler()  # type: ignore [call-arg]

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert 'host' in error_msg

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_missing_to_addresses(self) -> None:
        r"""Test to not supply the required `to_addresses` field."""

        # Setup - None
        # ===========================================================

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            EmailLogHandler(host='test@a7x.com')  # type: ignore [call-arg]

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert 'to_addresses' in error_msg

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_negative_timeout(self) -> None:
        r"""Test to supply a negative value to the `timeout` field."""

        # Setup - None
        # ===========================================================

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            EmailLogHandler(timeout=-1)  # type: ignore [call-arg]

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert 'timeout' in error_msg, 'timeout not in error message!'

        # Clean up - None
        # ===========================================================


class TestLoggingConfig:
    r"""Tests for the config model `LoggingConfig`."""

    def test_email_config(self) -> None:
        r"""Test to create an instance of `LoggingConfig` with an email logger configured."""

        # Setup
        # ===========================================================
        disabled = True
        min_log_level = LogLevel.WARNING
        _format = 'some format'
        datetime_format = r'%y-%m-%d'

        input_config = {
            'disabled': disabled,
            'min_log_level': 'WARNING',
            'format': _format,
            'datetime_format': datetime_format,
            'email': {
                'email-handler': {
                    'host': 'test@a7x.com',
                    'port': 20,
                    'subject': 'My subject',
                    'from_address': 'syn@a7x.com',
                    'to_addresses': ['mshadows@a7x.com', 'rev@a7x.com'],
                    'timeout': 2,
                    'disabled': False,
                    'min_log_level': 'ERROR',
                }
            },
        }
        exp_config = {
            'disabled': disabled,
            'min_log_level': min_log_level,
            'format': _format,
            'datetime_format': datetime_format,
            'stream': None,
            'file': None,
            'email': {
                'email-handler': {
                    'host': 'test@a7x.com',
                    'port': 20,
                    'subject': 'My subject',
                    'from_address': 'syn@a7x.com',
                    'to_addresses': ['mshadows@a7x.com', 'rev@a7x.com'],
                    'timeout': 2,
                    'disabled': False,
                    'min_log_level': LogLevel.ERROR,
                    'format': LOGGING_DEFAULT_FORMAT,
                    'datetime_format': LOGGING_DEFAULT_DATETIME_FORMAT,
                }
            },
        }

        # Exercise
        # ===========================================================
        ls = LoggingConfig.model_validate(input_config)

        # Verify
        # ===========================================================
        assert ls.model_dump() == exp_config

        # Clean up - None
        # ===========================================================
