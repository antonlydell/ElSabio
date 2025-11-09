# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Unit tests for the module config.core."""

# Third party
import pytest

# Local
from elsabio import exceptions
from elsabio.config import DatabaseConfig
from elsabio.database import make_url


class TestDatabaseSection:
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
