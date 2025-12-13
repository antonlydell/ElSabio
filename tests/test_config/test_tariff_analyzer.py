# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Unit tests for the module config.tariff_analyzer."""

# Standard library
from datetime import date
from pathlib import Path
from typing import Any

import pytest

# Third party
from sqlalchemy import make_url

# Local
from elsabio.config import ImportMethod, PluginType
from elsabio.config.tariff_analyzer import (
    DEFAULT_DATA_DIR,
    DataSource,
    DataSourceConfig,
    TariffAnalyzerConfig,
)
from elsabio.exceptions import ConfigError


class TestTariffAnalyzerConfig:
    r"""Tests for the class `elsabio.config.PluginConfig`."""

    def test_default_config(self) -> None:
        r"""Test the default configuration."""

        # Setup
        # ===========================================================
        exp_result = {'enabled': True, 'data_dir': DEFAULT_DATA_DIR, 'data': {}}

        # Exercise
        # ===========================================================
        result = TariffAnalyzerConfig()

        # Verify
        # ===========================================================
        print(f'result\n{result}\n')
        print(f'exp_result\n{exp_result}')

        assert result.model_dump(by_alias=True) == exp_result

        # Clean up - None
        # ===========================================================

    def test_data_config(self, tmp_path: Path) -> None:
        r"""Test to configure import methods for the input data."""

        # Setup
        # ===========================================================
        data_dir = tmp_path / 'data'
        data_dir.mkdir()

        facility_path_input = tmp_path / 'facility'
        facility_path_input.mkdir()

        facility_contract_path_input = tmp_path / 'facility_contract'
        facility_contract_path_input.mkdir()

        active_energy_cons_path_input = tmp_path / 'active_energy_cons'
        active_energy_cons_path_input.mkdir()

        input_data = {
            'enabled': False,
            'data_dir': str(data_dir),
            'data': {
                'facility': {
                    'method': 'file',
                    'path': str(facility_path_input),
                },
                'facility_contract': {
                    'method': 'plugin',
                    'path': str(facility_contract_path_input),
                    'interval': '2025-10-01..2025-11-01',
                    'plugin': {
                        'name': 'import_facility_contract',
                        'type': 'sqlalchemy',
                        'kwargs': {'db_url': 'sqlite://'},
                    },
                },
                'active_energy_cons': {
                    'method': 'plugin',
                    'path': str(active_energy_cons_path_input),
                    'interval': '2025-10-01',
                    'plugin': {
                        'name': 'import_active_energy_cons',
                        'type': 'generic',
                        'kwargs': {'base_url': 'https://api.example.com'},
                    },
                },
            },
        }
        exp_result = {
            'enabled': False,
            'data_dir': data_dir,
            'data': {
                DataSource.FACILITY: {
                    'method': ImportMethod.FILE,
                    'path': facility_path_input,
                    'interval': None,
                    'plugin': None,
                },
                DataSource.FACILITY_CONTRACT: {
                    'method': ImportMethod.PLUGIN,
                    'path': facility_contract_path_input,
                    'interval': (date(2025, 10, 1), date(2025, 11, 1)),
                    'plugin': {
                        'name': 'import_facility_contract',
                        'type': PluginType.SQLALCHEMY,
                        'kwargs': {'db_url': tuple(make_url('sqlite://'))},
                    },
                },
                DataSource.ACTIVE_ENERGY_CONS: {
                    'method': ImportMethod.PLUGIN,
                    'path': active_energy_cons_path_input,
                    'interval': (date(2025, 10, 1), None),
                    'plugin': {
                        'name': 'import_active_energy_cons',
                        'type': PluginType.GENERIC,
                        'kwargs': {'base_url': 'https://api.example.com'},
                    },
                },
            },
        }

        # Exercise
        # ===========================================================
        result = TariffAnalyzerConfig.model_validate(input_data)

        # Verify
        # ===========================================================
        print(f'result\n{result}\n')
        print(f'exp_result\n{exp_result}')

        assert result.model_dump(by_alias=True) == exp_result

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_invalid_data_source_name(self) -> None:
        r"""Test to supply an invalid data source name."""

        # Setup
        # ===========================================================
        input_data = {
            'enabled': False,
            'db': './tariff_analyzer.duckdb',
            'data': {
                'invalid': {
                    'method': 'plugin',
                    'path': '.',
                    'interval': '2025-10-01',
                    'plugin': {
                        'name': 'test_invalid_data_source',
                        'type': PluginType.GENERIC,
                    },
                },
            },
        }
        # Exercise
        # ===========================================================
        with pytest.raises(ConfigError) as exc_info:
            TariffAnalyzerConfig.model_validate(input_data)

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert 'invalid' in error_msg

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_data_dir_does_not_exist(self, tmp_path: Path) -> None:
        r"""Test to supply a directory that does not exist to the `data_dir` field."""

        # Setup
        # ===========================================================
        data_dir = tmp_path / 'data'
        error_msg_exp = f'The tariff_analyzer.data_dir = "{data_dir}" does not exist!'

        # Exercise
        # ===========================================================
        with pytest.raises(ConfigError) as exc_info:
            TariffAnalyzerConfig(data_dir=data_dir)

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert error_msg_exp in error_msg

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_data_dir_path_is_file(self, tmp_path: Path) -> None:
        r"""Test to supply a file to the `data_dir` field."""

        # Setup
        # ===========================================================
        file = tmp_path / 'data_dir.txt'
        file.touch()
        error_msg_exp = f'tariff_analyzer.data_dir = "{file}" must be a directory!'

        # Exercise
        # ===========================================================
        with pytest.raises(ConfigError) as exc_info:
            TariffAnalyzerConfig(data_dir=file)

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert error_msg_exp in error_msg

        # Clean up - None
        # ===========================================================


class TestDataSourceConfig:
    r"""Tests for the class `elsabio.config.tariff_analyzer.DataSourceConfig`."""

    @pytest.mark.raises
    def test_path_does_not_exist(self, tmp_path: Path) -> None:
        r"""Test to supply a path that does not exist."""

        # Setup
        # ===========================================================
        path = tmp_path / 'does_not_exist'
        error_msg_exp = f'The import path = "{path}" does not exist!'

        # Exercise
        # ===========================================================
        with pytest.raises(ConfigError) as exc_info:
            DataSourceConfig(method='file', path=str(path))

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert error_msg_exp in error_msg

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_relative_path_does_not_exist(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        r"""Test to supply a relative path that does not exist."""

        # Setup
        # ===========================================================
        path = tmp_path / 'does_not_exist'
        monkeypatch.chdir(tmp_path)
        rel_path = './does_not_exist'

        error_msg_exp = f'The import path = "{path}" does not exist!'

        # Exercise
        # ===========================================================
        with pytest.raises(ConfigError) as exc_info:
            DataSourceConfig(method='file', path=str(rel_path))

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert error_msg_exp in error_msg

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_path_is_file(self, tmp_path: Path) -> None:
        r"""Test to supply a path that is a file and not a directory."""

        # Setup
        # ===========================================================
        path = tmp_path / 'file.txt'
        path.touch()
        error_msg_exp = f'The import path = "{path}" is not a directory!'

        # Exercise
        # ===========================================================
        with pytest.raises(ConfigError) as exc_info:
            DataSourceConfig(method='file', path=path)

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert error_msg_exp in error_msg

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_relative_path_is_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        r"""Test to supply a relative path that is a file and not a directory."""

        # Setup
        # ===========================================================
        path = tmp_path / 'file.txt'
        path.touch()
        monkeypatch.chdir(tmp_path)
        rel_path = './file.txt'

        error_msg_exp = f'The import path = "{path}" is not a directory!'

        # Exercise
        # ===========================================================
        with pytest.raises(ConfigError) as exc_info:
            DataSourceConfig(method='file', path=rel_path)

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert error_msg_exp in error_msg

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    @pytest.mark.parametrize(
        ('interval', 'error_msg_exp'),
        [
            pytest.param('X', '"X" is not a valid relative or iso-formatted datetime!'),
            pytest.param([1, 2], 'Invalid interval "[1, 2]"!'),
        ],
    )
    def test_invalid_interval(self, interval: Any, error_msg_exp: str) -> None:
        r"""Test to supply an invalid interval."""

        # Setup - None
        # ===========================================================

        # Exercise
        # ===========================================================
        with pytest.raises(ConfigError) as exc_info:
            DataSourceConfig(method='file', path=Path.cwd(), interval=interval)

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert error_msg_exp in error_msg

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_no_plugin_config_defined_for_method_plugin(self) -> None:
        r"""Test to not supply a plugin config when the import method is "plugin"."""

        # Setup
        # ===========================================================
        error_msg_exp = 'No plugin configuration found and method = "plugin"!'

        # Exercise
        # ===========================================================
        with pytest.raises(ConfigError) as exc_info:
            DataSourceConfig(method='plugin', path=Path.cwd())

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert error_msg_exp in error_msg

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_no_interval_defined_and_plugin_config_defined(self) -> None:
        r"""Test to not supply an interval when the import method is "plugin"."""

        # Setup
        # ===========================================================
        error_msg_exp = 'No interval specified and method = "plugin"!'

        # Exercise
        # ===========================================================
        with pytest.raises(ConfigError) as exc_info:
            DataSourceConfig(method='plugin', path=Path.cwd(), plugin={'name': 'test'})

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert error_msg_exp in error_msg

        # Clean up - None
        # ===========================================================
