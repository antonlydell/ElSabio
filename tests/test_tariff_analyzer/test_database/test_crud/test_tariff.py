# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Unit tests for the module `database.tariff_analyzer.crud.tariff`"""

# Standard library
from datetime import date

# Third party
import pandas as pd

# Local
from elsabio.database import URL, SessionFactory
from elsabio.database.tariff_analyzer import load_tariff_model
from elsabio.models.tariff_analyzer import TariffDataFrameModel

# =================================================================================================
# Tests
# =================================================================================================


class TestLoadTariffModel:
    r"""Tests for the function `load_tariff_model`."""

    def test_load_the_tariffs_of_the_database(self, sqlite_db_with_tariffs: SessionFactory) -> None:
        r"""Test to load all tariffs of the database."""

        # Setup
        # ===========================================================
        m = TariffDataFrameModel

        # Exercise
        # ===========================================================
        with sqlite_db_with_tariffs() as session:
            model, result = load_tariff_model(session=session)

        # Verify
        # ===========================================================
        assert result.ok, f'result.ok is False! short_msg : {result.short_msg}'

        df = model.df
        assert df[m.c_name].tolist() == ['Tariff 1', 'Tariff 2'], 'Incorrect tariff names!'
        assert df[m.c_tariff_id].tolist() == [1, 2], 'Incorrect tariff_id:s!'
        assert df[m.c_currency_iso_code].tolist() == ['SEK', 'SEK'], 'Incorrect currencies!'
        assert df[m.c_validity_start].tolist() == [
            pd.Timestamp(date(2025, 10, 1)),
            pd.NaT,
        ], 'Incorrect validity start dates!'
        assert df[m.c_validity_end].isna().all(), 'Incorrect validity end dates!'
        assert df[m.c_last_edited_at].notna().all(), 'Last edited timestamps are missing!'

    def test_load_from_a_database_without_tariffs(
        self, initialized_sqlite_db: tuple[SessionFactory, URL]
    ) -> None:
        r"""Test to load the tariffs from a database that has no tariffs defined."""

        # Setup
        # ===========================================================
        session_factory, _ = initialized_sqlite_db

        # Exercise
        # ===========================================================
        with session_factory() as session:
            model, result = load_tariff_model(session=session)

        # Verify
        # ===========================================================
        assert result.ok, f'result.ok is False! short_msg : {result.short_msg}'
        assert model.empty, 'The loaded model is not empty!'
