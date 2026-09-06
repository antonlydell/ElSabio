# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Unit tests for the module `cli.tariff_analyzer.tariff.calc`"""

# Standard library
from datetime import datetime
from unittest.mock import Mock

# Third party
import pandas as pd
import pytest
from click.testing import CliRunner
from pandas.testing import assert_frame_equal

# Local
import elsabio.cli.main
from elsabio.cli.main import main
from elsabio.config import ConfigManager, load_config
from elsabio.models.tariff_analyzer import (
    TariffValueFacilityDataFrameModel,
    TariffValueTotalDataFrameModel,
)
from tests.test_tariff_analyzer.helpers.tariff_value import assert_tariff_value_written

# =================================================================================================
# Fixtures
# =================================================================================================


@pytest.fixture
def mocked_load_config(
    monkeypatch: pytest.MonkeyPatch,
    config_calc_tariff: ConfigManager,
) -> tuple[ConfigManager, Mock]:
    r"""A mocked version of `elsabio.config.load_config`.

    The `load_config` function of the CLI is mocked to a minimal
    configuration needed to perform the tariff calculations.

    Returns
    -------
    cm : elsabio.config.ConfigManager
        The configuration.

    m : unittest.mock.Mock
        The mock object.
    """

    m = Mock(spec_set=load_config, name='mocked_load_config', return_value=config_calc_tariff)
    monkeypatch.setattr(elsabio.cli.main, 'load_config', m)

    return config_calc_tariff, m


# =================================================================================================
# Tests
# =================================================================================================


@pytest.mark.usefixtures('mocked_load_config')
class TestTariffCalcCommand:
    r"""Tests for CLI command `elsabio ta tariff calc`."""

    @pytest.mark.usefixtures('write_imported_meter_data_files', 'sqlite_db_with_tariffs')
    @pytest.mark.parametrize(
        ('fixture', 'args', 'message_exp'),
        [
            pytest.param(
                None,
                ['ta', 'tariff', 'calc', '--interval', '2025-10-01..2025-12-01'],
                'Successfully calculated tariffs with tariff_id:s (1, 2) in interval [2025-10-01, 2025-12-01)!',
                id='No tariff value files exist',
            ),
            pytest.param(
                'write_calculated_tariff_value_files',
                [
                    'ta',
                    'tariff',
                    'calc',
                    '--interval',
                    '2025-10-01..2025-12-01',
                    '--tariffs',
                    '1, 2',
                ],
                'Successfully calculated tariffs with tariff_id:s (1, 2) in interval [2025-10-01, 2025-12-01)!',
                id='Overwrite existing tariff value files',
            ),
        ],
    )
    def test_calc_all_tariffs(
        self,
        fixture: str | None,
        args: list[str],
        message_exp: str,
        request: pytest.FixtureRequest,
        tariff_value_facility_model: TariffValueFacilityDataFrameModel,
        tariff_value_total_model: TariffValueTotalDataFrameModel,
        config_calc_tariff: ConfigManager,
    ) -> None:
        r"""Test to calculate all defined tariffs."""

        # Setup
        # ===========================================================
        if fixture:
            request.getfixturevalue(fixture)

        cfg = config_calc_tariff.tariff_analyzer

        runner = CliRunner()

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        output = result.output
        print(output)

        assert result.exit_code == 0, 'Exit code is not 0!'
        assert message_exp in output, 'Expected message missing in terminal output!'
        assert (
            'missing values in columns: "total_value" or "price_value" or "authority_fee_value"!'
            not in output
        )

        assert not list(cfg.tariff_value_error_dir.glob('*')), (
            f'Found files in error directory: "{cfg.tariff_value_error_dir}"!'
        )

        assert_tariff_value_written(
            cfg=cfg,
            df_facility_exp=tariff_value_facility_model.df,
            df_total_exp=tariff_value_total_model.df,
        )

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures('write_imported_meter_data_files', 'sqlite_db_with_tariffs')
    def test_calc_selected_tariff(
        self,
        tariff_value_facility_model: TariffValueFacilityDataFrameModel,
        tariff_value_total_model: TariffValueTotalDataFrameModel,
        config_calc_tariff: ConfigManager,
    ) -> None:
        r"""Test to calculate a selected tariff."""

        # Setup
        # ===========================================================
        cfg = config_calc_tariff.tariff_analyzer

        message_exp = 'Successfully calculated tariffs with tariff_id:s (1,) in interval [2025-10-01, 2025-12-01)!'
        tariff_id = 1

        df_facility_exp = tariff_value_facility_model.df
        filter_by_tariff_id = df_facility_exp[TariffValueFacilityDataFrameModel.c_tariff_id].eq(
            tariff_id
        )
        df_facility_exp = df_facility_exp.loc[filter_by_tariff_id, :]

        df_total_exp = tariff_value_total_model.df
        filter_by_tariff_id = df_total_exp[TariffValueTotalDataFrameModel.c_tariff_id].eq(tariff_id)
        df_total_exp = df_total_exp.loc[filter_by_tariff_id, :]

        runner = CliRunner()
        args = [
            'ta',
            'tariff',
            'calc',
            '--interval',
            '2025-10-01..2025-12-01',
            '--tariffs',
            str(tariff_id),
        ]

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        output = result.output
        print(output)

        assert result.exit_code == 0, 'Exit code is not 0!'
        assert message_exp in output, 'Expected message missing in terminal output!'
        assert (
            'missing values in columns: "total_value" or "price_value" or "authority_fee_value"!'
            not in output
        )

        assert not list(cfg.tariff_value_error_dir.glob('*')), (
            f'Found files in error directory: "{cfg.tariff_value_error_dir}"!'
        )

        assert_tariff_value_written(
            cfg=cfg,
            df_facility_exp=df_facility_exp,
            df_total_exp=df_total_exp,
        )

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures('tariff_calculation_data_with_errors')
    def test_errors_in_tariff_calculations(
        self,
        mocked_creation_datetime: tuple[str, datetime],
        tariff_value_facility_error_dataframe: pd.DataFrame,
        tariff_value_facility_model_with_errors: TariffValueFacilityDataFrameModel,
        tariff_value_total_model_with_errors: TariffValueTotalDataFrameModel,
        config_calc_tariff: ConfigManager,
    ) -> None:
        r"""Test to calculate tariffs when 2 facilities cannot be properly calculated."""

        # Setup
        # ===========================================================
        cfg = config_calc_tariff.tariff_analyzer

        creation_datetime, _ = mocked_creation_datetime
        error_file = cfg.tariff_value_error_dir / f'{creation_datetime}_tariff_calc_error.csv'

        message_exp = (
            f'Calculated tariffs with tariff_id:s (1, 2) '
            f'in interval [2025-10-01, 2025-12-01) with errors detected!\n'
            f'Check "{error_file}" for details about the facilities that could not be calculated.'
        )

        df_facility_exp = tariff_value_facility_model_with_errors.df
        df_total_exp = tariff_value_total_model_with_errors.df

        runner = CliRunner()
        args = ['ta', 'tariff', 'calc', '-i', '2025-10-01..2025-12-01']

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        print(result.output)

        assert result.exit_code == 1, 'Exit code is not 1!'
        assert message_exp in result.output, 'Expected message missing in terminal output!'

        df_error = pd.read_csv(
            filepath_or_buffer=error_file,
            sep=cfg.error_file_col_sep,
            encoding=cfg.error_file_encoding,
        )

        print('assert df_error')
        assert_frame_equal(df_error, tariff_value_facility_error_dataframe)

        assert_tariff_value_written(
            cfg=cfg,
            df_facility_exp=df_facility_exp,
            df_total_exp=df_total_exp,
        )

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures('sqlite_db_with_tariffs')
    @pytest.mark.parametrize(
        ('tariff_ids', 'tariff_ids_in_error_msg'),
        [
            pytest.param('0', '(0,)', id='tariff_ids=0'),
            pytest.param('0,-1', '(-1, 0)', id='tariff_ids=0,-1'),
            pytest.param('1,2, 0', '(0,)', id='tariff_ids=1,2, 0'),
        ],
    )
    def test_invalid_tariff_ids(self, tariff_ids: str, tariff_ids_in_error_msg: str) -> None:
        r"""Test to supply tariff_ids that do not exist in the database."""

        # Setup
        # ===========================================================
        message_exp = f'Tariffs with tariff_id:s {tariff_ids_in_error_msg} do not exist!'

        runner = CliRunner()
        args = ['ta', 'tariff', 'calc', '-i', '2025-10-01..2025-12-01', '-t', tariff_ids]

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        print(result.output)

        assert result.exit_code == 1, 'Exit code is not 1!'
        assert message_exp in result.output, 'Expected message missing in terminal output!'

        # Clean up - None
        # ===========================================================
