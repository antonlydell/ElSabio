# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Unit tests for the module `operations.tariff_analyzer.tariff.run`"""

# Standard library
from datetime import date, datetime
from typing import ClassVar

# Third party
import duckdb
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

# Local
from elsabio.config import ConfigManager
from elsabio.database import SessionFactory
from elsabio.models.tariff_analyzer import (
    TariffValueFacilityDataFrameModel,
    TariffValueTotalDataFrameModel,
)
from elsabio.operations.tariff_analyzer.tariff import run_tariff_calc

# =================================================================================================
# Helpers
# =================================================================================================


def load_tariff_value_result(pattern: str) -> pd.DataFrame:
    r"""Helper function to load the tariff value result.

    Parameters
    ----------
    pattern : str
        The file path glob pattern to apply when loading the tariff value result parquet files.

    Returns
    -------
    pandas.DataFrame
        The loaded tariff value result.
    """

    return duckdb.read_parquet(file_glob=pattern, hive_partitioning=True).to_df(date_as_object=True)


# =================================================================================================
# Tests
# =================================================================================================


class TestRunTariffCalc:
    r"""Tests for the operation `run_tariff_calc`."""

    facility_sort_cols_by: ClassVar[list[str]] = [
        TariffValueFacilityDataFrameModel.c_tariff_id,
        TariffValueFacilityDataFrameModel.c_date_id,
        TariffValueFacilityDataFrameModel.c_tariff_component_type_id,
        TariffValueFacilityDataFrameModel.c_tariff_cost_group_id,
        TariffValueFacilityDataFrameModel.c_customer_group_id,
        TariffValueFacilityDataFrameModel.c_facility_id,
    ]
    total_sort_cols_by: ClassVar[list[str]] = [
        TariffValueTotalDataFrameModel.c_tariff_id,
        TariffValueTotalDataFrameModel.c_date_id,
        TariffValueTotalDataFrameModel.c_tariff_component_type_id,
        TariffValueTotalDataFrameModel.c_tariff_cost_group_id,
        TariffValueTotalDataFrameModel.c_customer_group_id,
        TariffValueTotalDataFrameModel.c_tariff_component_id,
    ]
    facility_index_col: ClassVar[str] = TariffValueFacilityDataFrameModel.c_facility_id
    total_index_col: ClassVar[str] = TariffValueTotalDataFrameModel.c_tariff_id

    def assert_tariff_value_written(
        self,
        config: ConfigManager,
        df_facility_exp: pd.DataFrame,
        df_total_exp: pd.DataFrame,
    ) -> None:
        r"""Assert that the expected tariff value result was written to the parquet store.

        Parameters
        ----------
        config : elsabio.config.ConfigManager
            The configuration used for the tariff calculations.

        df_facility_exp : pandas.DataFrame
            The expected tariff value result per facility.

        df_total_exp : pandas.DataFrame
            The expected total tariff value result.
        """

        cfg = config.tariff_analyzer

        validation_set = (
            (
                'facility',
                cfg.tariff_value_facility_dir,
                self.facility_sort_cols_by,
                self.facility_index_col,
                df_facility_exp,
            ),
            (
                'total',
                cfg.tariff_value_total_dir,
                self.total_sort_cols_by,
                self.total_index_col,
                df_total_exp,
            ),
        )
        for value in validation_set:
            value_type, path, sort_by_cols, index_col, df_exp = value

            exp_cols = df_exp.columns.to_list()
            df_exp = df_exp.sort_values(sort_by_cols).set_index(index_col)

            df = load_tariff_value_result(pattern=str(path / '*' / '*' / '*.parquet'))

            missing_cols = set(exp_cols).difference(df.columns)
            assert not missing_cols, (
                f'Missing columns in tariff value {value_type} dataset : {missing_cols}'
            )

            df = df.loc[:, exp_cols].sort_values(sort_by_cols).set_index(index_col)

            print(f'assert {value_type=}')
            assert_frame_equal(df, df_exp, check_dtype=False, check_index_type=False)

    @pytest.mark.usefixtures('write_imported_meter_data_files')
    def test_calculate_all_tariffs(
        self,
        sqlite_db_with_tariffs: SessionFactory,
        config_calc_tariff: ConfigManager,
        tariff_value_facility_model: TariffValueFacilityDataFrameModel,
        tariff_value_total_model: TariffValueTotalDataFrameModel,
    ) -> None:
        r"""Test to calculate all defined tariffs without involving the CLI."""

        # Setup
        # ===========================================================
        cfg = config_calc_tariff.tariff_analyzer

        # Exercise
        # ===========================================================
        outcome, result = run_tariff_calc(
            session_factory=sqlite_db_with_tariffs,
            cfg=cfg,
            start_date=date(2025, 10, 1),
            end_date=date(2025, 12, 1),
        )

        # Verify
        # ===========================================================
        assert result.ok, f'result.ok is False! short_msg : {result.short_msg}'
        assert outcome.tariff_ids == (1, 2), 'Incorrect tariff_ids in outcome!'
        assert outcome.completed, 'outcome.completed is False!'
        assert outcome.df_invalid is None, 'outcome.df_invalid is not None!'
        assert outcome.error_file is None, 'outcome.error_file is not None!'
        assert outcome.write_errors == (), 'outcome.write_errors is not empty!'

        assert not list(cfg.tariff_value_error_dir.glob('*')), (
            f'Found files in error directory: "{cfg.tariff_value_error_dir}"!'
        )

        self.assert_tariff_value_written(
            config=config_calc_tariff,
            df_facility_exp=tariff_value_facility_model.df,
            df_total_exp=tariff_value_total_model.df,
        )

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures('write_imported_meter_data_files')
    def test_calculate_selected_tariff(
        self,
        sqlite_db_with_tariffs: SessionFactory,
        config_calc_tariff: ConfigManager,
        tariff_value_facility_model: TariffValueFacilityDataFrameModel,
        tariff_value_total_model: TariffValueTotalDataFrameModel,
    ) -> None:
        r"""Test to calculate a selection of the defined tariffs."""

        # Setup
        # ===========================================================
        cfg = config_calc_tariff.tariff_analyzer
        tariff_id = 1

        df_facility_exp = tariff_value_facility_model.df
        df_facility_exp = df_facility_exp.loc[
            df_facility_exp[TariffValueFacilityDataFrameModel.c_tariff_id].eq(tariff_id), :
        ]

        df_total_exp = tariff_value_total_model.df
        df_total_exp = df_total_exp.loc[
            df_total_exp[TariffValueTotalDataFrameModel.c_tariff_id].eq(tariff_id), :
        ]

        # Exercise
        # ===========================================================
        outcome, result = run_tariff_calc(
            session_factory=sqlite_db_with_tariffs,
            cfg=cfg,
            start_date=date(2025, 10, 1),
            end_date=date(2025, 12, 1),
            tariff_ids=(tariff_id,),
        )

        # Verify
        # ===========================================================
        assert result.ok, f'result.ok is False! short_msg : {result.short_msg}'
        assert outcome.tariff_ids == (tariff_id,), 'Incorrect tariff_ids in outcome!'
        assert outcome.completed, 'outcome.completed is False!'

        self.assert_tariff_value_written(
            config=config_calc_tariff,
            df_facility_exp=df_facility_exp,
            df_total_exp=df_total_exp,
        )

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures('tariff_calculation_data_with_errors')
    def test_facilities_that_fail_validation_are_reported(
        self,
        mocked_creation_datetime: tuple[str, datetime],
        sqlite_db_with_tariffs: SessionFactory,
        config_calc_tariff: ConfigManager,
        tariff_value_facility_error_dataframe: pd.DataFrame,
        tariff_value_facility_model_with_errors: TariffValueFacilityDataFrameModel,
        tariff_value_total_model_with_errors: TariffValueTotalDataFrameModel,
    ) -> None:
        r"""Test that facilities that fail the validation are reported without aborting the run.

        Two facilities cannot be properly calculated. The run should still write its
        result to the parquet store and report the failure as a not ok `OperationResult`
        rather than by raising or exiting.
        """

        # Setup
        # ===========================================================
        cfg = config_calc_tariff.tariff_analyzer

        creation_datetime, _ = mocked_creation_datetime
        error_file_exp = cfg.tariff_value_error_dir / f'{creation_datetime}_tariff_calc_error.csv'

        # Exercise
        # ===========================================================
        outcome, result = run_tariff_calc(
            session_factory=sqlite_db_with_tariffs,
            cfg=cfg,
            start_date=date(2025, 10, 1),
            end_date=date(2025, 12, 1),
        )

        # Verify
        # ===========================================================
        assert not result.ok, 'result.ok is True!'
        assert result.short_msg, 'result.short_msg is empty!'
        assert outcome.completed, 'outcome.completed is False!'
        assert outcome.tariff_ids == (1, 2), 'Incorrect tariff_ids in outcome!'
        assert outcome.write_errors == (), 'outcome.write_errors is not empty!'

        assert outcome.error_file == error_file_exp, 'Incorrect error file in outcome!'
        assert error_file_exp.exists(), f'Error file "{error_file_exp}" was not written!'

        df_error = pd.read_csv(
            filepath_or_buffer=outcome.error_file,
            sep=cfg.error_file_col_sep,
            encoding=cfg.error_file_encoding,
        )

        print('assert df_error')
        assert_frame_equal(df_error, tariff_value_facility_error_dataframe)

        assert outcome.df_invalid is not None, 'outcome.df_invalid is None!'
        assert not outcome.df_invalid.empty, 'outcome.df_invalid is empty!'

        self.assert_tariff_value_written(
            config=config_calc_tariff,
            df_facility_exp=tariff_value_facility_model_with_errors.df,
            df_total_exp=tariff_value_total_model_with_errors.df,
        )

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures('sqlite_db_with_tariffs')
    def test_tariff_ids_that_do_not_exist_abort_the_run(
        self,
        sqlite_db_with_tariffs: SessionFactory,
        config_calc_tariff: ConfigManager,
    ) -> None:
        r"""Test to supply tariff_id:s that do not exist in the database.

        The run should be aborted and report the failure as a not ok
        `OperationResult` without writing anything.
        """

        # Setup
        # ===========================================================
        cfg = config_calc_tariff.tariff_analyzer
        short_msg_exp = 'Tariffs with tariff_id:s (0,) do not exist!'

        # Exercise
        # ===========================================================
        outcome, result = run_tariff_calc(
            session_factory=sqlite_db_with_tariffs,
            cfg=cfg,
            start_date=date(2025, 10, 1),
            end_date=date(2025, 12, 1),
            tariff_ids=(1, 0),
        )

        # Verify
        # ===========================================================
        assert not result.ok, 'result.ok is True!'
        assert short_msg_exp in result.short_msg, 'Expected message missing in result.short_msg!'

        assert not outcome.completed, 'outcome.completed is True!'
        assert outcome.tariff_ids == (), 'outcome.tariff_ids is not empty!'
        assert outcome.error_file is None, 'outcome.error_file is not None!'

        assert not list(cfg.tariff_value_facility_dir.glob('**/*.parquet')), (
            'Tariff value per facility was written by an aborted run!'
        )
        assert not list(cfg.tariff_value_total_dir.glob('**/*.parquet')), (
            'Total tariff value was written by an aborted run!'
        )

        # Clean up - None
        # ===========================================================
