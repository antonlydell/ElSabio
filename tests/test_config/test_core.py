# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Unit tests for the module config.core."""

# Third party
import pytest

# Local
from elsabio import exceptions
from elsabio.config import DatabaseConfig, PluginConfig, PluginType
from elsabio.database import make_url


class TestPluginConfig:
    r"""Tests for the class `elsabio.config.PluginConfig`."""

    def test_generic_plugin_without_kwargs(self) -> None:
        r"""Test to create a plugin without any keyword arguments."""

        # Setup
        # ===========================================================
        name = 'api_plugin'
        input_data = {'name': name, 'type': 'generic'}
        exp_result = {'name': name, 'type': PluginType.GENERIC, 'kwargs': {}}

        # Exercise
        # ===========================================================
        result = PluginConfig.model_validate(input_data)

        # Verify
        # ===========================================================
        print(f'result\n{result}\n')
        print(f'exp_result\n{exp_result}')

        assert result.model_dump() == exp_result

        # Clean up - None
        # ===========================================================

    def test_generic_plugin_with_kwargs(self) -> None:
        r"""Test to create a generic plugin with keyword arguments."""

        # Setup
        # ===========================================================
        kwargs = {'base_url': 'https://api.example.com', 'start_date': '2025-12-04'}
        input_data = {'name': 'api_plugin', 'type': 'generic', 'kwargs': kwargs}

        exp_result = input_data.copy()
        exp_result['type'] = PluginType.GENERIC

        # Exercise
        # ===========================================================
        result = PluginConfig.model_validate(input_data)

        # Verify
        # ===========================================================
        print(f'result\n{result}\n')
        print(f'exp_result\n{exp_result}')

        assert result.model_dump() == exp_result

        # Clean up - None
        # ===========================================================

    def test_sqlalchemy_plugin(self) -> None:
        r"""Test to create a SQLAlchemy plugin."""

        # Setup
        # ===========================================================
        name = 'sqlalchemy_plugin'
        kwargs = {'db_url': 'sqlite://', 'value_ids': [1, 2, 3]}

        kwargs_exp = kwargs.copy()
        kwargs_exp['db_url'] = tuple(make_url('sqlite://'))

        input_data = {'name': name, 'type': 'sqlalchemy', 'kwargs': kwargs}
        exp_result = {'name': name, 'type': PluginType.SQLALCHEMY, 'kwargs': kwargs_exp}

        # Exercise
        # ===========================================================
        result = PluginConfig.model_validate(input_data)

        # Verify
        # ===========================================================
        print(f'result\n{result}\n')
        print(f'exp_result\n{exp_result}')

        assert result.model_dump() == exp_result

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_invalid_type(self) -> None:
        r"""Test to supply an invalid plugin type to the `type` field."""

        # Setup - None
        # ===========================================================

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            PluginConfig(name='test', type='abc')

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert 'type' in error_msg

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_sqlalchemy_plugin_with_missing_db_url(self) -> None:
        r"""Test to not supply the required `db_url kwarg to a SQLAlchemy plugin."""

        # Setup
        # ===========================================================
        name = 'sqlalchemy_plugin_no_db_url'
        error_msg_exp = f'Missing required kwarg "db_url" for SQLAlchemy plugin with name "{name}"!'

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            PluginConfig(name=name, type=PluginType.SQLALCHEMY, kwargs={'value_id': 1})

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert error_msg_exp in error_msg

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_invalid_url(self) -> None:
        r"""Test to supply an invalid url to the `db_url` of the kwargs field."""

        # Setup
        # ===========================================================
        db_url = 'sqlite::///tariff_analyzer.db'

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            PluginConfig(
                name='sqlalchemy_plugin', type=PluginType.SQLALCHEMY, kwargs={'db_url': db_url}
            )

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert 'db_url' in error_msg

        # Clean up - None
        # ===========================================================


class TestDatabaseConfig:
    r"""Tests for the class `elsabio.config.DatabaseConfig`."""

    def test_defaults(self) -> None:
        r"""Test to create an instance with all default values."""

        # Setup
        # ===========================================================
        exp_result = {
            'url': tuple(make_url('sqlite:///ElSabio.db')),
            'autoflush': False,
            'expire_on_commit': False,
            'create_database': True,
            'connect_args': {},
            'engine_config': {},
        }

        # Exercise
        # ===========================================================
        result = DatabaseConfig()

        # Verify
        # ===========================================================
        print(f'result\n{result}\n')
        print(f'exp_result\n{exp_result}')

        assert result.model_dump() == exp_result

        # Clean up - None
        # ===========================================================

    def test_specify_all_fields(self) -> None:
        r"""Test to create an instance and specify all fields."""

        # Setup
        # ===========================================================
        url = 'postgresql+psycopg2://user:pw@myserver:5432/postgresdb'
        autoflush = True
        expire_on_commit = True
        create_database = False
        connect_args = {'arg1': 1, 1: [1, 2, 3]}
        engine_config = {'echo': True}

        exp_result = {
            'url': tuple(make_url(url)),
            'autoflush': autoflush,
            'expire_on_commit': expire_on_commit,
            'create_database': create_database,
            'connect_args': connect_args,
            'engine_config': engine_config,
        }

        # Exercise
        # ===========================================================
        result = DatabaseConfig(
            url=url,
            autoflush=autoflush,
            expire_on_commit=expire_on_commit,
            create_database=create_database,
            connect_args=connect_args,
            engine_config=engine_config,
        )

        # Verify
        # ===========================================================
        print(f'result\n{result}\n')
        print(f'exp_result\n{exp_result}')

        assert result.model_dump() == exp_result

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_invalid_url(self) -> None:
        r"""Test to supply an invalid URL to the `url` field."""

        # Setup
        # ===========================================================
        url = 'sqlite::///db_with_error.db'

        # Exercise
        # ===========================================================
        with pytest.raises(exceptions.ConfigError) as exc_info:
            DatabaseConfig(url=url)

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert 'url' in error_msg

        # Clean up - None
        # ===========================================================
