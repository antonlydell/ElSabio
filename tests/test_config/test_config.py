# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Unit tests for the module config.config."""

# Standard library
from pathlib import Path
from types import MappingProxyType
from typing import Any, ClassVar
from zoneinfo import ZoneInfo

# Third party
import pytest
from pydantic import AnyHttpUrl

# Local
from elsabio import exceptions
from elsabio.config import (
    BITWARDEN_PASSWORDLESS_API_URL,
    SECRETS_FILE_ENV_VAR,
    ConfigManager,
    load_config,
)

bwp = MappingProxyType({'public_key': 'bwp_public_key', 'private_key': 'bwp_private_key'})


class TestConfigManagerTimezone:
    r"""Tests for timezone field of `elsabio.config.ConfigManager`."""

    default_tz: ClassVar[ZoneInfo] = ZoneInfo('Europe/Stockholm')

    def test_default_value(self) -> None:
        r"""Test the default value of the timezone field."""

        # Setup - None
        # ===========================================================

        # Exercise
        # ===========================================================
        cm = ConfigManager(bwp=bwp)

        # Verify
        # ===========================================================
        assert cm.timezone == self.default_tz

        # Clean up - None
        # ===========================================================

    @pytest.mark.parametrize(
        'timezone',
        [
            pytest.param(None, id='None'),
            pytest.param('', id='""'),
            pytest.param('    ', id='spaces'),
        ],
    )
    def test_empty_values(self, timezone: str | None) -> None:
        r"""Test empty values such as None and "", which should yield the default timezone."""

        # Setup - None
        # ===========================================================

        # Exercise
        # ===========================================================
        cm = ConfigManager(timezone=timezone, bwp=bwp)

        # Verify
        # ===========================================================
        assert cm.timezone == self.default_tz

        # Clean up - None
        # ===========================================================

    @pytest.mark.parametrize(
        ('timezone', 'exp_timezone'),
        [
            pytest.param('Europe/Berlin', ZoneInfo('Europe/Berlin'), id='str'),
            pytest.param(ZoneInfo('America/Denver'), ZoneInfo('America/Denver'), id='ZoneInfo'),
        ],
    )
    def test_valid_timezone(self, timezone: str | ZoneInfo, exp_timezone: ZoneInfo) -> None:
        r"""Test to supply a valid timezone."""

        # Setup - None
        # ===========================================================

        # Exercise
        # ===========================================================
        cm = ConfigManager(timezone=timezone, bwp=bwp)

        # Verify
        # ===========================================================
        assert cm.timezone == exp_timezone

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_invalid_timezone(self) -> None:
        r"""Test to to supply an invalid timezone."""

        # Setup
        # ===========================================================
        error_msg_exp = (
            'Failed to load timezone "invalid". Either the IANA timezone key is invalid '
            'or the system timezone database is missing. Install the tzdata package '
            'for your system or provide a valid timezone like "Europe/Stockholm".'
        )

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            ConfigManager(timezone='invalid', bwp=bwp)

        # Verify
        # ===========================================================
        error_msg = exc_info.value.args[0]
        print(error_msg)

        assert error_msg_exp in error_msg

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_unsupported_type(self) -> None:
        r"""Test to to supply an unsupported type."""

        # Setup
        # ===========================================================
        error_msg_exp = 'Invalid timezone: "[]". Expected str or zoneinfo.ZoneInfo, got "list".'

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            ConfigManager(timezone=[], bwp=bwp)

        # Verify
        # ===========================================================
        error_msg = exc_info.value.args[0]
        print(error_msg)

        assert error_msg_exp in error_msg

        # Clean up - None
        # ===========================================================


class TestConfigManagerEnvVarsAndSecrets:
    r"""Tests to set config keys with environment variables and the secrets file."""

    def test_load_from_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        r"""Test to supply part of the configuration from environment variables.

        Configuration passed to the constructor should override values
        from environment variables.
        """

        # Setup
        # ===========================================================
        tz = 'UTC'
        bwp_url = 'https://test.bwp.com'
        bwp_public_key = 'public_key'
        bwp_private_key = 'private_key'
        bwp_url = 'https://test.bwp.com'
        bwp_exp_values = (
            ('public_key', bwp_public_key),
            ('private_key', bwp_private_key),
            ('url', AnyHttpUrl(bwp_url)),
        )
        db_url_env = 'sqlite:///ElSabio_from_env.db'
        db_url_init = 'sqlite:///ElSabio_from_init.db'

        monkeypatch.setenv('ElSabio_database__url', db_url_env)
        monkeypatch.setenv('elsabio_bwp__url', bwp_url)
        monkeypatch.setenv('ELSABIO_BWP__public_key', bwp_public_key)
        monkeypatch.setenv('ELSABIO_Bwp__private_key', bwp_private_key)
        monkeypatch.setenv('elsabio_bwp__invalid', 'invalid')  # Extra value that should be ignored
        monkeypatch.setenv('elsabio_timezone', tz)

        # Exercise
        # ===========================================================
        cm = ConfigManager(database={'url': db_url_init})

        # Verify
        # ===========================================================
        print(f'result\n{cm}\n')

        assert str(cm.timezone) == tz, 'cm.timezone is incorrect!'
        assert str(cm.database.url) == db_url_init, 'cm.database.url is incorrect!'

        bwp_cfg = cm.bwp
        for attr, exp_value in bwp_exp_values:
            assert getattr(bwp_cfg, attr) == exp_value, f'bwp_cfg.{attr} is incorrect!'

        # Clean up - None
        # ===========================================================

    def test_secrets_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        r"""Test to load part of the configuration from a secrets file.

        The order in which the configuration sources should override each other:
        1. Values passed to the constructor
        2. Environment variables
        3. Values from the secrets file
        """

        # Setup
        # ===========================================================
        bwp_public_key = 'public_key'
        bwp_private_key_secret = 'private_key_secret'  # noqa: S105
        bwp_private_key_init = 'private_key_init'
        bwp_private_key_env = 'private_key_env_var'
        bwp_exp_values = (
            ('public_key', bwp_public_key),
            ('private_key', bwp_private_key_init),
            ('url', BITWARDEN_PASSWORDLESS_API_URL),
        )
        db_url = 'sqlite:///ElSabio_from_secret.db'
        secrets_file_content = f"""\
[database]
url = '{db_url}'

[bwp]
public_key = '{bwp_public_key}'
private_key = '{bwp_private_key_secret}'
"""
        secrets_file = tmp_path / '.elsabio'
        secrets_file.write_text(secrets_file_content)

        monkeypatch.setenv('ELSABIO_BWP__PRIVATE_KEY', bwp_private_key_env)
        monkeypatch.setenv(SECRETS_FILE_ENV_VAR, str(secrets_file))

        # Exercise
        # ===========================================================
        cm = ConfigManager(bwp={'private_key': bwp_private_key_init})

        # Verify
        # ===========================================================
        print(f'result\n{cm}\n')

        assert str(cm.database.url) == db_url, 'cm.database.url is incorrect!'

        bwp_cfg = cm.bwp
        for attr, exp_value in bwp_exp_values:
            assert getattr(bwp_cfg, attr) == exp_value, f'bwp_cfg.{attr} is incorrect!'

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_secrets_file_is_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        r"""Test to load secrets from a path that is a directory."""

        # Setup
        # ===========================================================
        error_msg_exp = f'The secrets file "{tmp_path}" must be a file not a directory!'

        monkeypatch.setenv(SECRETS_FILE_ENV_VAR, str(tmp_path))

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.SecretsFileNotFoundError) as exc_info:
            ConfigManager(bwp=bwp)

        # Verify
        # ===========================================================
        error_msg = exc_info.value.args[0]
        print(error_msg)

        assert error_msg_exp == error_msg

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_secrets_file_does_not_exist(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        r"""The to load secrets from a file that does not exist."""

        # Setup
        # ===========================================================
        secrets_file = tmp_path / 'does_not_exist'
        error_msg_exp = f'The secrets file "{secrets_file}" does not exist!'

        monkeypatch.setenv(SECRETS_FILE_ENV_VAR, str(secrets_file))

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.SecretsFileNotFoundError) as exc_info:
            ConfigManager(bwp=bwp)

        # Verify
        # ===========================================================
        error_msg = exc_info.value.args[0]
        print(error_msg)

        assert error_msg == error_msg_exp

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_secrets_file_with_syntax_errors(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        r"""Test to load secrets from a file with syntax errors."""

        # Setup
        # ===========================================================
        secrets_file_content = """\
        [database
        url = 'sqlite:///ElSabio_from_secret.db'
"""
        secrets_file = tmp_path / '.elsabio'
        secrets_file.write_text(secrets_file_content)

        monkeypatch.setenv(SECRETS_FILE_ENV_VAR, str(secrets_file))
        error_msg_exp = f'Toml syntax error in secrets file : "{secrets_file}"!'

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ParseConfigError) as exc_info:
            ConfigManager(bwp=bwp)

        # Verify
        # ===========================================================
        error_msg = exc_info.value.args[0]
        print(error_msg)

        assert error_msg_exp in error_msg

        # Clean up - None
        # ===========================================================


class TestLoadConfig:
    r"""Tests for the function `elsabio.config.load_config`."""

    @pytest.mark.usefixtures(
        'config_in_stdin', 'config_file_from_config_env_var', 'config_file_from_default_location'
    )
    def test_load_from_config_file(self, config_file: tuple[Path, str, dict[str, Any]]) -> None:
        r"""Test to load the config from a direct path to a config file.

        The config is also present in:
        1. stdin,
        2. the config file environment variable,
        3. the default config file location.

        These locations should be ignored since supplying a direct path
        to a config file should take precedence over the other options.
        """

        # Setup
        # ===========================================================
        config_file_path, _, exp_result = config_file

        # Exercise
        # ===========================================================
        cm = load_config(path=config_file_path)

        # Verify
        # ===========================================================
        print(f'result\n{cm}\n')
        print(f'exp_result\n{exp_result}')

        assert cm.model_dump() == exp_result

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures('config_file_from_config_env_var', 'config_file_from_default_location')
    def test_load_from_stdin(self, config_in_stdin: tuple[str, dict[str, Any]]) -> None:
        r"""Test to load the config from stdin.

        The config is also present in:
        1. the config file environment variable,
        2. the default config file location.

        These locations should be ignored since stdin will take precedence over the other two.
        """

        # Setup
        # ===========================================================
        _, exp_result = config_in_stdin

        # Exercise
        # ===========================================================
        cm = load_config(path=Path('-'))

        # Verify
        # ===========================================================
        print(f'result\n{cm}\n')
        print(f'exp_result\n{exp_result}')

        assert cm.model_dump() == exp_result

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures(
        'remove_config_file_env_var', 'default_config_file_location_does_not_exist'
    )
    def test_path_is_none_and_config_in_stdin(
        self, config_in_stdin: tuple[str, dict[str, Any]]
    ) -> None:
        r"""Test to not specify a config file path while config exists in stdin.

        The config should be loaded from stdin.
        """

        # Setup
        # ===========================================================
        _, exp_result = config_in_stdin

        # Exercise
        # ===========================================================
        cm = load_config()

        # Verify
        # ===========================================================
        print(f'result\n{cm}\n')
        print(f'exp_result\n{exp_result}')

        assert cm.model_dump() == exp_result

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures('config_file_from_default_location')
    def test_load_from_config_file_env_var(
        self, config_file_from_config_env_var: tuple[Path, str, dict[str, Any]]
    ) -> None:
        r"""Test specifying the config file environment variable ELSABIO_CONFIG_FILE.

        A config file in the default config file location is also present, but it
        should not be touched since the environment variable will take precedence.
        """

        # Setup
        # ===========================================================
        _, _, exp_result = config_file_from_config_env_var

        # Exercise
        # ===========================================================
        cm = load_config()

        # Verify
        # ===========================================================
        print(f'result\n{cm}\n')
        print(f'exp_result\n{exp_result}')

        assert cm.model_dump() == exp_result

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures('remove_config_file_env_var')
    def test_load_from_default_location(
        self, config_file_from_default_location: tuple[Path, str, dict[str, Any]]
    ) -> None:
        r"""Test to load the config from a config file in the default location.

        No other configuration sources are defined.
        """

        # Setup
        # ===========================================================
        _, _, exp_result = config_file_from_default_location

        # Exercise
        # ===========================================================
        cm = load_config()

        # Verify
        # ===========================================================
        print(f'result\n{cm}\n')
        print(f'exp_result\n{exp_result}')

        assert cm.model_dump() == exp_result

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    @pytest.mark.usefixtures(
        'remove_config_file_env_var', 'empty_stdin', 'default_config_file_location_does_not_exist'
    )
    def test_no_config_sources(self) -> None:
        r"""Test to load the configuration when no config sources exist."""

        # Setup
        # ===========================================================
        error_msg_exp = 'No configuration found! Check your sources!'

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            load_config()

        # Verify
        # ===========================================================
        error_msg = exc_info.value.args[0]
        print(error_msg)

        assert error_msg_exp == error_msg

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_from_config_file_is_dir(self, tmp_path: Path) -> None:
        r"""Test to load the config from a path that is a directory."""

        # Setup
        # ===========================================================
        error_msg_exp = f'The config file "{tmp_path}" must be a file not a directory!'

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigFileNotFoundError) as exc_info:
            load_config(path=tmp_path)

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert error_msg_exp in error_msg

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_from_config_file_does_not_exist(self, tmp_path: Path) -> None:
        r"""Test to load the config from a config file that does not exist."""

        # Setup
        # ===========================================================
        config_file_path = tmp_path / 'does_not_exist.toml'
        error_msg_exp = f'The config file "{config_file_path}" does not exist!'

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigFileNotFoundError) as exc_info:
            load_config(path=config_file_path)

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert error_msg_exp in error_msg

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_config_with_syntax_errors(self, config_file_with_syntax_error: Path) -> None:
        r"""Test to load a config file with syntax errors."""

        # Setup
        # ===========================================================
        error_msg_exp = 'Syntax error in config :'

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ParseConfigError) as exc_info:
            load_config(path=config_file_with_syntax_error)

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert error_msg_exp in error_msg

        # Clean up - None
        # ===========================================================
