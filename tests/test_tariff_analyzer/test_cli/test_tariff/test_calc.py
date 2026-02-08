# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Unit tests for the module `cli.tariff_analyzer.tariff.calc`"""

# Standard library
from datetime import date, datetime
from pathlib import Path
from typing import ClassVar
from unittest.mock import Mock

# Third party
import duckdb
import pandas as pd
import pytest
from click.testing import CliRunner
from pandas.testing import assert_frame_equal

# Local
import elsabio.cli.main
from elsabio.cli.main import main
from elsabio.config import ConfigManager, load_config
from elsabio.database import URL, SessionFactory
from elsabio.database.models.tariff_analyzer import FacilityContract
from elsabio.models.tariff_analyzer import (
    SerieValueDataFrameModel,
    TariffValueFacilityDataFrameModel,
    TariffValueTotalDataFrameModel,
)
from tests.config import STATIC_FILES_TARIFF_ANALYZER_BASE_DIR

# =================================================================================================
# Fixtures
# =================================================================================================


@pytest.fixture
def config_calc_tariff(
    tmp_path: Path, empty_sqlite_db: tuple[SessionFactory, URL]
) -> ConfigManager:
    r"""The configuration of the tariff calculations.

    Returns
    -------
    cm : elsabio.config.ConfigManager
        The configuration to use for the tariff calculations.
    """

    _, db_url = empty_sqlite_db

    data_dir = tmp_path / 'data'
    data_dir.mkdir()

    config = {
        'database': {'url': db_url},
        'bwp': {'public_key': 'bwp_public_key', 'private_key': 'bwp_private_key'},
        'tariff_analyzer': {'data_dir': data_dir},
    }

    return ConfigManager.model_validate(config)


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


@pytest.fixture
def write_imported_meter_data_files(
    config_calc_tariff: ConfigManager,
    active_energy_cons_model: SerieValueDataFrameModel,
    active_energy_prod_model: SerieValueDataFrameModel,
    max_reactive_power_cons_model: SerieValueDataFrameModel,
    max_deb_active_power_cons_high_load_model: SerieValueDataFrameModel,
    max_active_power_cons_model: SerieValueDataFrameModel,
) -> Path:
    r"""Write the imported meter data files needed for the tariff calculations.

    Returns
    -------
    meter_data_dir : pathlib.Path
        The path to the meter data directory where the files are located.
    """

    meter_data_dir = config_calc_tariff.tariff_analyzer.data_dir / 'meter_data'
    partition_by = [SerieValueDataFrameModel.c_serie_type_code, SerieValueDataFrameModel.c_date_id]

    models = (
        active_energy_cons_model,
        active_energy_prod_model,
        max_deb_active_power_cons_high_load_model,
        max_reactive_power_cons_model,
        max_active_power_cons_model,
    )

    for m in models:
        rel = duckdb.from_df(m.df)
        rel.to_parquet(str(meter_data_dir), partition_by=partition_by, overwrite=True)

    return meter_data_dir


@pytest.fixture
def write_calculated_tariff_value_files(
    config_calc_tariff: ConfigManager,
    tariff_value_facility_model: TariffValueFacilityDataFrameModel,
    tariff_value_total_model: TariffValueTotalDataFrameModel,
) -> tuple[Path, Path]:
    r"""Write the parquet files with the calculated tariff values.

    Useful for testing overwriting tariff value files that already exist
    in the target location.

    Returns
    -------
    tariff_value_facility_dir : pathlib.Path
        The path to the directory where the existing tariff value per facility files are located.

    tariff_value_total_dir : pathlib.Path
        The path to the directory where the existing tariff value total files are located.
    """

    cfg = config_calc_tariff.tariff_analyzer

    data = (
        (
            tariff_value_facility_model,
            cfg.tariff_value_facility_dir,
            TariffValueFacilityDataFrameModel.c_total_value,
            [
                TariffValueFacilityDataFrameModel.c_tariff_id,
                TariffValueFacilityDataFrameModel.c_date_id,
            ],
        ),
        (
            tariff_value_total_model,
            cfg.tariff_value_total_dir,
            TariffValueTotalDataFrameModel.c_total_value,
            [
                TariffValueTotalDataFrameModel.c_tariff_id,
                TariffValueTotalDataFrameModel.c_date_id,
            ],
        ),
    )

    for d in data:
        model, path, change_col, partition_by = d

        df = model.df.copy()
        df.loc[:, change_col] = 0
        duckdb.from_df(df).to_parquet(
            file_name=str(path), partition_by=partition_by, overwrite=True
        )

    return cfg.tariff_value_facility_dir, cfg.tariff_value_total_dir


@pytest.fixture
def tariff_calculation_data_with_errors(
    write_imported_meter_data_files: Path,
    sqlite_db_with_tariffs: SessionFactory,
    max_deb_active_power_cons_high_load_model: SerieValueDataFrameModel,
) -> tuple[int, int]:
    r"""Prepare tariff calculation data that will yield invalid results.

    Facility (facility_id = 4) has no subscribed power for 2025-10-01
    and facility (facility_id = 5) has no meter data for serie type
    "max_deb_active_power_cons_high_load".

    Returns
    -------
    facility_id_4 : int
        The first facility with calculation errors (facility_id = 4).

    facility_id_5 : int
        The second facility with calculation errors (facility_id = 5).
    """

    facility_id_4 = 4
    facility_id_5 = 5

    with sqlite_db_with_tariffs() as session:
        f = session.get(FacilityContract, (facility_id_4, date(2025, 10, 1)))

        assert f is not None, (
            f'facility_contract (facility_id={facility_id_4}, date_id=2025-10-01) not found in database!'
        )
        f.subscribed_power = None
        session.commit()

    df_max_deb = max_deb_active_power_cons_high_load_model.df.copy()
    df_max_deb = df_max_deb.loc[
        df_max_deb[SerieValueDataFrameModel.c_facility_id].ne(facility_id_5), :
    ]
    partition_by = [SerieValueDataFrameModel.c_serie_type_code, SerieValueDataFrameModel.c_date_id]

    rel = duckdb.from_df(df_max_deb)
    rel.to_parquet(str(write_imported_meter_data_files), partition_by=partition_by, overwrite=True)

    return facility_id_4, facility_id_5


@pytest.fixture
def tariff_value_facility_error_dataframe() -> pd.DataFrame:
    r"""The DataFrame with facilities with errors during tariff calculations.

    The expected result after running the calculations with fixture
    `tariff_calculation_data_with_errors`.

    Returns
    -------
    df_error : pandas.DataFrame
        The DataFrame with the expected error content.
    """

    file = (
        STATIC_FILES_TARIFF_ANALYZER_BASE_DIR
        / '2025-10_2025-11_tariff_value_facility_error_dataframe.csv'
    )
    assert file.exists(), f'File "{file}" does not exist!'

    return pd.read_csv(file, sep=';')


@pytest.fixture(scope='session')
def tariff_value_facility_model_with_errors() -> TariffValueFacilityDataFrameModel:
    r"""The calculated tariff value result per facility with errors.

    The expected result after running the calculations with fixture
    `tariff_calculation_data_with_errors`.

    Returns
    -------
    elsabio.models.tariff_analyzer.TariffValueFacilityDataFrameModel
        The DataFrame model of the tariff value result per facility.
    """

    file = (
        STATIC_FILES_TARIFF_ANALYZER_BASE_DIR
        / '2025-10_2025-11_tariff_value_facility_with_errors.csv'
    )
    assert file.exists(), f'File "{file}" does not exist!'

    df = (
        duckdb.read_csv(str(file), sep=';')
        .select('* EXCLUDE(ean, description)')
        .df(date_as_object=True)
        .astype(TariffValueFacilityDataFrameModel.dtypes)
    )

    return TariffValueFacilityDataFrameModel(df=df)


@pytest.fixture(scope='session')
def tariff_value_total_model_with_errors() -> TariffValueTotalDataFrameModel:
    r"""The calculated total tariff value result with errors.

    The expected result after running the calculations with fixture
    `tariff_calculation_data_with_errors`.

    Returns
    -------
    elsabio.models.tariff_analyzer.TariffValueTotalDataFrameModel
        The DataFrame model of the total tariff value result.
    """

    file = (
        STATIC_FILES_TARIFF_ANALYZER_BASE_DIR / '2025-10_2025-11_tariff_value_total_with_errors.csv'
    )
    assert file.exists(), f'File "{file}" does not exist!'

    df = (
        duckdb.read_csv(str(file), sep=';')
        .df(date_as_object=True)
        .astype(TariffValueTotalDataFrameModel.dtypes)
    )
    return TariffValueTotalDataFrameModel(df=df)


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


@pytest.mark.usefixtures('mocked_load_config')
class TestTariffCalcCommand:
    r"""Tests for CLI command `elsabio ta tariff calc`."""

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

        df_facility_exp = tariff_value_facility_model.df
        facility_cols_exp = df_facility_exp.columns.to_list()
        df_facility_exp = df_facility_exp.sort_values(self.facility_sort_cols_by).set_index(
            self.facility_index_col
        )

        df_total_exp = tariff_value_total_model.df
        exp_total_cols = df_total_exp.columns.to_list()
        df_total_exp = df_total_exp.sort_values(self.total_sort_cols_by).set_index(
            self.total_index_col
        )

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

        validation_set = (
            (
                'facility',
                cfg.tariff_value_facility_dir,
                facility_cols_exp,
                self.facility_sort_cols_by,
                self.facility_index_col,
                df_facility_exp,
            ),
            (
                'total',
                cfg.tariff_value_total_dir,
                exp_total_cols,
                self.total_sort_cols_by,
                self.total_index_col,
                df_total_exp,
            ),
        )
        for value in validation_set:
            value_type, path, exp_cols, sort_by_cols, index_col, df_exp = value

            df = load_tariff_value_result(pattern=str(path / '*' / '*' / '*.parquet'))

            missing_cols = set(exp_cols).difference(df.columns)
            assert not missing_cols, (
                f'Missing columns in tariff value {value_type} dataset : {missing_cols}'
            )

            df = df.loc[:, exp_cols].sort_values(sort_by_cols).set_index(index_col)

            print(f'assert {value_type=}')
            assert_frame_equal(df, df_exp, check_dtype=False, check_index_type=False)

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
        facility_cols_exp = df_facility_exp.columns.to_list()
        df_facility_exp = df_facility_exp.sort_values(self.facility_sort_cols_by).set_index(
            self.facility_index_col
        )

        df_total_exp = tariff_value_total_model.df
        filter_by_tariff_id = df_total_exp[TariffValueTotalDataFrameModel.c_tariff_id].eq(tariff_id)
        df_total_exp = df_total_exp.loc[filter_by_tariff_id, :]
        total_cols_exp = df_total_exp.columns.to_list()
        df_total_exp = df_total_exp.sort_values(self.total_sort_cols_by).set_index(
            self.total_index_col
        )

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

        validation_set = (
            (
                'facility',
                cfg.tariff_value_facility_dir,
                facility_cols_exp,
                self.facility_sort_cols_by,
                self.facility_index_col,
                df_facility_exp,
            ),
            (
                'total',
                cfg.tariff_value_total_dir,
                total_cols_exp,
                self.total_sort_cols_by,
                self.total_index_col,
                df_total_exp,
            ),
        )
        for value in validation_set:
            value_type, path, exp_cols, sort_by_cols, index_col, df_exp = value

            df = load_tariff_value_result(pattern=str(path / '*' / '*' / '*.parquet'))

            missing_cols = set(exp_cols).difference(df.columns)
            assert not missing_cols, (
                f'Missing columns in tariff value {value_type} dataset : {missing_cols}'
            )

            df = df.loc[:, exp_cols].sort_values(sort_by_cols).set_index(index_col)

            print(f'assert {value_type=}')
            assert_frame_equal(df, df_exp, check_dtype=False, check_index_type=False)

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
        facility_cols_exp = df_facility_exp.columns.to_list()
        df_facility_exp = df_facility_exp.sort_values(self.facility_sort_cols_by).set_index(
            self.facility_index_col
        )

        df_total_exp = tariff_value_total_model_with_errors.df
        exp_total_cols = df_total_exp.columns.to_list()
        df_total_exp = df_total_exp.sort_values(self.total_sort_cols_by).set_index(
            self.total_index_col
        )

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

        validation_set = (
            (
                'facility',
                cfg.tariff_value_facility_dir,
                facility_cols_exp,
                self.facility_sort_cols_by,
                self.facility_index_col,
                df_facility_exp,
            ),
            (
                'total',
                cfg.tariff_value_total_dir,
                exp_total_cols,
                self.total_sort_cols_by,
                self.total_index_col,
                df_total_exp,
            ),
        )
        for value in validation_set:
            value_type, path, exp_cols, sort_by_cols, index_col, df_exp = value

            df = load_tariff_value_result(pattern=str(path / '*' / '*' / '*.parquet'))

            missing_cols = set(exp_cols).difference(df.columns)
            assert not missing_cols, (
                f'Missing columns in tariff value {value_type} dataset : {missing_cols}'
            )

            df = df.loc[:, exp_cols].sort_values(sort_by_cols).set_index(index_col)

            print(f'assert {value_type=}')
            assert_frame_equal(df, df_exp, check_dtype=False, check_index_type=False)

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
