# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Unit tests for the module `database.init`"""

# Standard library
from pathlib import Path

# Third party
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

# Local
import elsabio.database.models.core as core_models
import elsabio.database.models.tariff_analyzer as ta_models
from elsabio.database import create_session_factory, init

# =============================================================================================
# Tests
# =============================================================================================


class TestInit:
    r"""Tests for the function `init`."""

    def test_initialize_sqlite_database(self, tmp_path: Path) -> None:
        r"""Test to initialize a SQLite database."""

        # Setup
        # ===========================================================
        db = tmp_path / 'ElSabio.db'
        url = f'sqlite:///{db!s}'
        session_factory = create_session_factory(url=url, create_database=True)

        get_tables_query = text("SELECT name FROM sqlite_master WHERE type = 'table'")
        tables_exp = {
            t.__tablename__
            for m in core_models.__dict__
            if hasattr(t := getattr(core_models, m), '__tablename__')
        } | {
            t.__tablename__
            for m in ta_models.__dict__
            if hasattr(t := getattr(ta_models, m), '__tablename__')
        }

        # Tables with default records.
        queries = {
            # core
            'Currency': select(func.count()).select_from(core_models.Currency),
            'Unit': select(func.count()).select_from(core_models.Unit),
            'SerieType': select(func.count()).select_from(core_models.SerieType),
            # tariff_analyzer
            'FacilityType': select(func.count()).select_from(ta_models.FacilityType),
            'CalcStrategy': select(func.count()).select_from(ta_models.CalcStrategy),
        }

        # Exercise
        # ===========================================================
        with session_factory() as session:
            result = init(session=session)

        # Verify
        # ===========================================================
        assert result.ok, 'result.ok is False!'
        assert result.short_msg == '', 'result.short_msg is incorrect!'
        assert result.long_msg == '', 'result.long_msg is incorrect!'
        assert result.code is None, 'result.code is not None!'

        with session_factory() as session:
            tables = set(session.scalars(get_tables_query))

            for table, query in queries.items():
                count = session.scalars(query).one()

                assert count > 0, f'{table} : Default records not created!'

        # Not all expected tables have been created.
        diff_in_tables_exp_not_in_tables = tables_exp.difference(tables)
        print(f'{diff_in_tables_exp_not_in_tables=}')

        assert not diff_in_tables_exp_not_in_tables, 'diff_in_tables_exp_not_in_tables'

        # All other tables than the expected ones should belong to streamlit_passwordless.
        diff_in_tables_not_in_tables_exp = tables.difference(tables_exp)
        print(f'{diff_in_tables_not_in_tables_exp=}')

        for table in diff_in_tables_not_in_tables_exp:
            assert table.startswith('stp_'), f'{table=} is not a streamlit_passwordless table!'

        # Clean up - None
        # ===========================================================

    def test_initialize_already_initialized_database(self, tmp_path: Path) -> None:
        r"""Test to initialize an already initialized database."""

        # Setup
        # ===========================================================
        db = tmp_path / 'ElSabio.db'
        url = f'sqlite:///{db!s}'
        session_factory = create_session_factory(url=url, create_database=True)

        # Exercise
        # ===========================================================
        with session_factory() as session:
            init(session=session)
            result = init(session=session)

        # Verify
        # ===========================================================
        assert result.ok is False, 'result.ok is True!'
        assert result.short_msg == 'Error initializing database!', 'result.short_msg is incorrect!'
        assert 'Error initializing database!' in result.long_msg, 'result.long_msg is incorrect!'
        assert result.code == 'sqlalchemy.exc.IntegrityError', 'result.code is incorrect!'

        # Clean up - None
        # ===========================================================

    @pytest.mark.raises
    def test_sqlite_foreign_key_constraints_enabled(self) -> None:
        r"""Test that foreign key constraints are enabled in a SQLite database."""

        # Setup
        # ===========================================================
        session_factory = create_session_factory(url='sqlite://', create_database=True)

        # Exercise
        # ===========================================================
        with session_factory() as session:
            session.add(ta_models.Facility(facility_id=1, ean=1, facility_type_id=1))

            with pytest.raises(IntegrityError) as exc_info:
                session.commit()

        # Verify
        # ===========================================================
        error_msg = exc_info.exconly()
        print(error_msg)

        assert 'FOREIGN KEY constraint failed' in error_msg

        # Clean up - None
        # ===========================================================
