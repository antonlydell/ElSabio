# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Unit tests for the module cli.tariff_analyzer.import_.meter_data."""

# Standard library
import re
from datetime import date
from pathlib import Path
from typing import ClassVar

# Third party
import duckdb
import pandas as pd
import pytest
from click.testing import CliRunner
from pandas.testing import assert_frame_equal

# Local
from elsabio.cli.main import main
from elsabio.config import ConfigManager
from elsabio.config.tariff_analyzer import DataSource
from elsabio.models.core import SerieTypeEnum
from elsabio.models.tariff_analyzer import SerieValueDataFrameModel, SerieValueImportDataFrameModel

# =================================================================================================
# Fixtures
# =================================================================================================


@pytest.fixture
def active_energy_cons_import_parquet_file(
    active_energy_cons_model_to_import: SerieValueDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> Path:
    r"""A parquet file with the active energy consumption data to import.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.
    """

    _, cm = config_data_import_method_file
    data = cm.tariff_analyzer.data.get(DataSource.ACTIVE_ENERGY_CONS)

    assert data is not None, 'Missing configuration "tariff_analyzer.data.active_energy_cons"!'

    file = data.path / 'active_energy_cons.parquet'
    active_energy_cons_model_to_import.df.to_parquet(path=file)

    return file


@pytest.fixture
def max_reactive_power_cons_import_parquet_file(
    max_reactive_power_cons_model_to_import: SerieValueDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> Path:
    r"""A parquet file with the max reactive power consumption data to import.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.
    """

    _, cm = config_data_import_method_file
    data = cm.tariff_analyzer.data.get(DataSource.MAX_REACTIVE_POWER_CONS)

    assert data is not None, 'Missing configuration "tariff_analyzer.data.max_reactive_power_cons"!'

    file = data.path / 'max_reactive_power_cons.parquet'
    max_reactive_power_cons_model_to_import.df.to_parquet(path=file)

    return file


@pytest.fixture
def active_energy_cons_parquet_file_missing_required_columns(
    active_energy_cons_model_to_import: SerieValueImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> Path:
    r"""An input active energy consumption parquet file with required columns missing.

    The `ean` and `date_id` columns are missing.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.
    """

    _, cm = config_data_import_method_file
    data = cm.tariff_analyzer.data.get(DataSource.ACTIVE_ENERGY_CONS)

    assert data is not None, 'Missing configuration "tariff_analyzer.data.active_energy_cons"!'

    df = active_energy_cons_model_to_import.df.copy().drop(
        columns=[
            SerieValueImportDataFrameModel.c_ean,
            SerieValueImportDataFrameModel.c_date_id,
        ]
    )

    file = data.path / 'active_energy_cons.parquet'
    df.to_parquet(path=file)

    return file


@pytest.fixture
def active_energy_cons_parquet_file_missing_values_in_required_columns(
    active_energy_cons_model_to_import: SerieValueImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> tuple[Path, tuple[str, ...]]:
    r"""An active energy consumption parquet file with missing values for required columns.

    4 rows have missing values for the required columns `serie_type_code` `ean`,
    `date_id` and `serie_value`.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.

    ean_codes : tuple[str, ...]
        The EAN codes of the rows with missing values.
    """

    _, cm = config_data_import_method_file
    data = cm.tariff_analyzer.data.get(DataSource.ACTIVE_ENERGY_CONS)

    assert data is not None, 'Missing configuration for "tariff_analyzer.data.active_energy_cons"!'

    c_serie_type_code = SerieValueImportDataFrameModel.c_serie_type_code
    c_ean = SerieValueImportDataFrameModel.c_ean
    c_date_id = SerieValueImportDataFrameModel.c_date_id
    c_serie_value = SerieValueImportDataFrameModel.c_serie_value

    df = active_energy_cons_model_to_import.df.copy()
    df.loc[1, c_serie_type_code] = None
    df.loc[2, [c_serie_type_code, c_ean]] = [None, None]
    df.loc[3, c_date_id] = None
    df.loc[4, c_serie_value] = None
    ean_codes = tuple(str(df.loc[v, c_ean]) for v in range(1, 5))

    file = data.path / 'active_energy_cons.parquet'
    df.to_parquet(path=file)

    return file, ean_codes


@pytest.fixture
def active_energy_cons_parquet_file_with_duplicate_rows(
    active_energy_cons_model_to_import: SerieValueImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> tuple[Path, str]:
    r"""An active energy consumption parquet file with duplicate rows.

    Contains 1 duplicate row over the columns `serie_type_code`, `ean` and `date_id`.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.

    ean_code : str
        The EAN code of the duplicate row.
    """

    _, cm = config_data_import_method_file
    data = cm.tariff_analyzer.data.get(DataSource.ACTIVE_ENERGY_CONS)

    assert data is not None, 'Missing configuration for "tariff_analyzer.data.active_energy_cons"!'

    c_serie_type_code = SerieValueImportDataFrameModel.c_serie_type_code
    c_ean = SerieValueImportDataFrameModel.c_ean
    c_date_id = SerieValueImportDataFrameModel.c_date_id
    c_serie_value = SerieValueImportDataFrameModel.c_serie_value
    id_cols = [c_serie_type_code, c_ean, c_date_id]

    df = active_energy_cons_model_to_import.df.copy()
    duplicate_row = df.shape[0] + 1
    df.loc[duplicate_row, id_cols] = df.loc[7, id_cols]  # type: ignore[index]
    df.loc[duplicate_row, c_serie_value] = 89
    ean_code = str(df.loc[7, c_ean])

    file = data.path / 'active_energy_cons.parquet'
    df.to_parquet(path=file)

    return file, ean_code


@pytest.fixture
def active_energy_cons_parquet_file_invalid_serie_type_code_and_ean(
    active_energy_cons_model_to_import: SerieValueImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> tuple[Path, tuple[str, str]]:
    r"""An active energy consumption parquet file with invalid values.

    The dataset has invalid values for the `serie_type_code` and `ean` columns.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.

    ean_codes : tuple[str, str]
        The EAN codes of the rows with invalid values.
    """

    _, cm = config_data_import_method_file
    data = cm.tariff_analyzer.data.get(DataSource.ACTIVE_ENERGY_CONS)

    assert data is not None, 'Missing configuration for "tariff_analyzer.data.active_energy_cons"!'

    c_ean = SerieValueImportDataFrameModel.c_ean
    c_serie_type_code = SerieValueDataFrameModel.c_serie_type_code

    df = active_energy_cons_model_to_import.df.copy()
    df.loc[2, [c_serie_type_code, c_ean]] = ['invalid', 123456]
    df.loc[4, c_serie_type_code] = 'test'
    ean_codes = (str(df.loc[2, c_ean]), str(df.loc[4, c_ean]))

    file = data.path / 'active_energy_cons.parquet'
    df.to_parquet(path=file)

    return file, ean_codes


@pytest.fixture
def active_energy_cons_parquet_file_date_id_not_at_month_start(
    active_energy_cons_model_to_import: SerieValueImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> tuple[Path, tuple[str, str]]:
    r"""An active energy consumption parquet file with dates not at the start of a month.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.

    ean_codes : tuple[str, str]
        The EAN codes of the rows with invalid dates.
    """

    _, cm = config_data_import_method_file
    data = cm.tariff_analyzer.data.get(DataSource.ACTIVE_ENERGY_CONS)

    assert data is not None, 'Missing configuration for "tariff_analyzer.data.active_energy_cons"!'

    c_ean = SerieValueImportDataFrameModel.c_ean
    c_date_id = SerieValueImportDataFrameModel.c_date_id

    df = active_energy_cons_model_to_import.df.copy()
    df.loc[3, c_date_id] = date(2025, 12, 24)
    df.loc[5, c_date_id] = date(2025, 12, 20)
    ean_codes = (str(df.loc[3, c_ean]), str(df.loc[5, c_ean]))

    file = data.path / 'active_energy_cons.parquet'
    df.to_parquet(path=file)

    return file, ean_codes


@pytest.fixture
def empty_active_energy_cons_import_parquet_file(
    config_data_import_method_file: tuple[str, ConfigManager],
) -> Path:
    r"""An empty active energy consumption parquet file.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.
    """

    _, cm = config_data_import_method_file
    data = cm.tariff_analyzer.data.get(DataSource.ACTIVE_ENERGY_CONS)

    assert data is not None, 'Missing configuration "tariff_analyzer.data.active_energy_cons"!'

    df = pd.DataFrame()

    file = data.path / 'active_energy_cons.parquet'
    df.to_parquet(path=file)

    return file


# =================================================================================================
# Tests
# =================================================================================================


class TestTariffAnalyzerImportFacilityContractCommand:
    r"""Tests for the CLI command `ta import meter-data`."""

    sort_values_by: ClassVar[list[str]] = [
        SerieValueDataFrameModel.c_facility_id,
        SerieValueDataFrameModel.c_date_id,
    ]

    def load_imported_meter_data(self, path: Path) -> pd.DataFrame:
        r"""Helper method to load imported meter data from parquet files."""

        return (
            duckdb.read_parquet(
                file_glob=f'{path}/*.parquet',
                hive_partitioning=True,
            )
            .to_df(date_as_object=True)
            .astype(SerieValueDataFrameModel.dtypes)
            .sort_values(self.sort_values_by)
        )

    @pytest.mark.usefixtures(
        'default_config_file_location_does_not_exist',
        'config_import_method_file_in_config_file_env_var',
        'sqlite_db_with_all_facilities',
    )
    def test_load_all_available_sources(
        self,
        config_import_method_file_in_config_file_env_var: tuple[Path, ConfigManager],
        active_energy_cons_import_parquet_file: Path,
        active_energy_cons_model: SerieValueImportDataFrameModel,
        active_energy_cons_model_to_import: SerieValueDataFrameModel,
        max_reactive_power_cons_import_parquet_file: Path,
        max_reactive_power_cons_model: SerieValueImportDataFrameModel,
        max_reactive_power_cons_model_to_import: SerieValueDataFrameModel,
        filename_with_timestamp_pattern_regex: re.Pattern,
    ) -> None:
        r"""Test to import meter data from all available sources.

        The sources `active_energy_cons` and `max_reactive_power_cons` are configured.
        """

        # Setup
        # ===========================================================
        _, cm = config_import_method_file_in_config_file_env_var
        input_filenames = (
            active_energy_cons_import_parquet_file,
            max_reactive_power_cons_import_parquet_file,
        )
        dfs_to_import_exp = (
            active_energy_cons_model_to_import.df,
            max_reactive_power_cons_model_to_import.df,
        )
        dfs_imported_exp = (active_energy_cons_model.df, max_reactive_power_cons_model.df)

        c_serie_type_code = SerieValueDataFrameModel.c_serie_type_code
        c_date_id = SerieValueDataFrameModel.c_date_id

        meter_data_dir = cm.tariff_analyzer.data_dir / 'meter_data'
        active_energy_cons_dir = (
            meter_data_dir
            / f'{c_serie_type_code}={SerieTypeEnum.ACTIVE_ENERGY_CONS}'
            / f'{c_date_id}=2025-11-01'
        )
        max_reactive_power_cons_dir = (
            meter_data_dir / f'{c_serie_type_code}={SerieTypeEnum.MAX_REACTIVE_POWER_CONS}' / '*'
        )
        imported_dirs_exp = (active_energy_cons_dir, max_reactive_power_cons_dir)

        message_exp = (
            f'Successfully processed meter data for sources: '
            f"('{DataSource.ACTIVE_ENERGY_CONS}', '{DataSource.MAX_REACTIVE_POWER_CONS}')"
        )

        runner = CliRunner()
        args = ['ta', 'import', 'meter-data']

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        print(result.output)

        assert result.exit_code == 0, 'Exit code is not 0!'
        assert message_exp in result.output, 'Expected message missing in terminal output!'

        for i in range(0, 2):
            df_imported = self.load_imported_meter_data(path=imported_dirs_exp[i])
            df_exp = dfs_imported_exp[i].sort_values(self.sort_values_by)

            assert df_imported.shape == df_exp.shape, (
                'The shape of the imported DataFrame is incorrect!'
            )
            df_imported = df_imported.loc[:, df_exp.columns]

            assert_frame_equal(df_imported, df_exp)

            # Check that the imported file is moved to sub-directory success
            input_filename = input_filenames[i]
            target_dir = input_filename.parent / 'success'
            assert not input_filename.exists(), 'Input file not moved!'

            target_files = list(target_dir.iterdir())
            assert len(target_files) == 1, 'Incorrect nr of items in target directory!'

            target_file = target_files[0]
            assert filename_with_timestamp_pattern_regex.match(target_file.name) is not None, (
                'Filename of moved file is incorrect!'
            )

            df_import = pd.read_parquet(target_file)

            assert_frame_equal(df_import, dfs_to_import_exp[i], check_dtype=False)

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures(
        'default_config_file_location_does_not_exist',
        'config_import_method_file_in_config_file_env_var',
    )
    def test_import_active_energy_cons_and_active_energy_prod(self) -> None:
        r"""Test to import only active energy consumption and production."""

        # Setup
        # ===========================================================
        sources_processed_exp = (DataSource.ACTIVE_ENERGY_CONS, DataSource.ACTIVE_ENERGY_PROD)
        sources_not_processed_exp = (
            DataSource.MAX_ACTIVE_POWER_CONS,
            DataSource.MAX_ACTIVE_POWER_PROD,
            DataSource.MAX_REACTIVE_POWER_CONS,
            DataSource.MAX_REACTIVE_POWER_PROD,
            DataSource.MAX_DEB_ACTIVE_POWER_CONS_HIGH_LOAD,
            DataSource.MAX_DEB_ACTIVE_POWER_CONS_LOW_LOAD,
        )

        runner = CliRunner()
        args = [
            'ta',
            'import',
            'meter-data',
            DataSource.ACTIVE_ENERGY_CONS.value,
            DataSource.ACTIVE_ENERGY_PROD.value,
        ]

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        output = result.output
        print(output)

        assert result.exit_code == 1, 'Exit code is not 1!'

        for source in sources_processed_exp:
            assert str(source) in output, f'{source=} not found in terminal output!'

        for source in sources_not_processed_exp:
            assert str(source) not in output, f'{source=} found in terminal output!'

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures('mocked_load_config_with_no_import_data')
    def test_no_config_found(self) -> None:
        r"""Test to import active energy consumption when no configuration is defined."""

        # Setup
        # ===========================================================
        message_exp = (
            f'No configuration found for "tariff_analyzer.data.{DataSource.ACTIVE_ENERGY_CONS}"!\n'
        )

        runner = CliRunner()
        args = ['ta', 'import', 'meter-data', DataSource.ACTIVE_ENERGY_CONS.value]

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        print(result.output)

        assert result.exit_code == 1, 'Exit code is not 1!'
        assert result.output == message_exp, 'Expected message missing in terminal output!'

        # Clean up - None
        # ===========================================================

    def test_invalid_data_source(self) -> None:
        r"""Test to supply an invalid data source."""

        # Setup
        # ===========================================================
        exit_code_exp = 2
        runner = CliRunner()
        args = ['ta', 'import', 'meter-data', 'invalid']

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        print(result.output)

        assert result.exit_code == exit_code_exp, 'Exit code is not 2!'

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures(
        'default_config_file_location_does_not_exist',
        'config_import_method_file_in_config_file_env_var',
    )
    def test_no_input_file_found(
        self, config_data_import_method_file: tuple[str, ConfigManager]
    ) -> None:
        r"""Test to import meter data when no input parquet file exists."""

        # Setup
        # ===========================================================
        _, cm = config_data_import_method_file

        patterns_exp = []
        for source in (DataSource.ACTIVE_ENERGY_CONS, DataSource.MAX_REACTIVE_POWER_CONS):
            cfg = cm.tariff_analyzer.data.get(source)

            assert cfg is not None, f'Missing configuration "tariff_analyzer.data.{source}"!'

            patterns_exp.append(f'{cfg.path}/*.parquet')

        runner = CliRunner()
        args = ['ta', 'import', 'meter-data']

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        output = result.output
        print(output)

        assert result.exit_code == 1, 'Exit code is not 1!'

        for pattern_exp in patterns_exp:
            assert pattern_exp in output, 'Expected message missing in terminal output!'

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures(
        'default_config_file_location_does_not_exist',
        'config_import_method_file_in_config_file_env_var',
    )
    def test_missing_values_in_required_columns(
        self,
        active_energy_cons_parquet_file_missing_values_in_required_columns: tuple[
            Path, tuple[str, ...]
        ],
    ) -> None:
        r"""Test to import active energy consumption with missing values in required columns."""

        # Setup
        # ===========================================================
        _, eans_exp = active_energy_cons_parquet_file_missing_values_in_required_columns
        required_cols = (
            SerieValueImportDataFrameModel.c_serie_type_code,
            SerieValueImportDataFrameModel.c_ean,
            SerieValueImportDataFrameModel.c_date_id,
            SerieValueImportDataFrameModel.c_serie_value,
        )
        message_exp = f'Found rows ({len(eans_exp)}) with missing values in required columns'

        runner = CliRunner()
        args = ['ta', 'import', 'meter-data', DataSource.ACTIVE_ENERGY_CONS.value]

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        output = result.output
        print(output)

        assert result.exit_code == 1, 'Exit code is not 1!'
        assert message_exp in output, 'Expected output message missing in terminal output!'

        for ean in eans_exp:
            assert ean in output, f'EAN "{ean}" missing in terminal output!'

        for col in required_cols:
            assert col in output, f'Required column "{col}" missing in terminal output!'

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures(
        'default_config_file_location_does_not_exist',
        'config_import_method_file_in_config_file_env_var',
        'sqlite_db_with_all_facilities',
    )
    def test_duplicate_rows(
        self,
        active_energy_cons_parquet_file_with_duplicate_rows: tuple[Path, str],
    ) -> None:
        r"""Test to import active energy consumption with duplicate rows."""

        # Setup
        # ===========================================================
        _, ean_exp = active_energy_cons_parquet_file_with_duplicate_rows
        required_cols = (
            SerieValueImportDataFrameModel.c_serie_type_code,
            SerieValueImportDataFrameModel.c_ean,
            SerieValueImportDataFrameModel.c_date_id,
        )
        message_exp = 'Found duplicate rows (1) over columns:'

        runner = CliRunner()
        args = ['ta', 'import', 'meter-data', DataSource.ACTIVE_ENERGY_CONS.value]

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        output = result.output
        print(output)

        assert result.exit_code == 1, 'Exit code is not 1!'
        assert message_exp in output, 'Expected output message missing in terminal output!'

        assert ean_exp in output, f'EAN "{ean_exp}" missing in terminal output!'

        for col in required_cols:
            assert col in output, f'Required column "{col}" missing in terminal output!'

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures(
        'default_config_file_location_does_not_exist',
        'config_import_method_file_in_config_file_env_var',
        'sqlite_db_with_all_facilities',
    )
    def test_invalid_values_for_serie_type_code_and_facility_id_columns(
        self,
        active_energy_cons_parquet_file_invalid_serie_type_code_and_ean: tuple[
            Path, tuple[str, str]
        ],
    ) -> None:
        r"""Test to import meter data with invalid values.

        The columns `serie_type_code` and `ean` contain invalid values."""

        # Setup
        # ===========================================================
        _, eans_exp = active_energy_cons_parquet_file_invalid_serie_type_code_and_ean
        message_exp = (
            f'Found rows ({len(eans_exp)}) with invalid values for columns '
            f'"{SerieValueDataFrameModel.c_serie_type_code}" or "{SerieValueDataFrameModel.c_ean}"!'
        )

        runner = CliRunner()
        args = ['ta', 'import', 'meter-data', DataSource.ACTIVE_ENERGY_CONS.value]

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        output = result.output
        print(output)

        assert result.exit_code == 1, 'Exit code is not 1!'
        assert message_exp in output, 'Expected output message missing in terminal output!'

        for ean in eans_exp:
            assert ean in output, f'EAN "{ean}" missing in terminal output!'

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures(
        'default_config_file_location_does_not_exist',
        'config_import_method_file_in_config_file_env_var',
    )
    def test_date_id_not_at_start_of_month(
        self,
        active_energy_cons_parquet_file_date_id_not_at_month_start: tuple[Path, tuple[str, str]],
    ) -> None:
        r"""Test to import meter data with dates not at the start of a month."""

        # Setup
        # ===========================================================
        _, eans_exp = active_energy_cons_parquet_file_date_id_not_at_month_start
        message_exp = f'Found rows ({len(eans_exp)}) not at start of month!'

        runner = CliRunner()
        args = ['ta', 'import', 'meter-data', DataSource.ACTIVE_ENERGY_CONS.value]

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        output = result.output
        print(output)

        assert result.exit_code == 1, 'Exit code is not 1!'
        assert message_exp in output, 'Expected output message missing in terminal output!'

        for ean in eans_exp:
            assert ean in output, f'EAN "{ean}" missing in terminal output!'

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures(
        'default_config_file_location_does_not_exist',
        'config_import_method_file_in_config_file_env_var',
        'active_energy_cons_parquet_file_missing_required_columns',
    )
    def test_missing_required_columns(self) -> None:
        r"""Test to import meter data when required columns are missing."""

        # Setup
        # ===========================================================
        c_serie_type_code = SerieValueImportDataFrameModel.c_serie_type_code
        c_ean = SerieValueImportDataFrameModel.c_ean
        c_date_id = SerieValueImportDataFrameModel.c_date_id
        c_serie_value = SerieValueImportDataFrameModel.c_serie_value
        c_status_id = SerieValueImportDataFrameModel.c_status_id

        message_exp = 'Missing the required columns!'
        missing_cols_exp = f"('{c_date_id}', '{c_ean}')"
        required_cols_exp = f"('{c_date_id}', '{c_ean}', '{c_serie_type_code}', '{c_serie_value}')"
        available_cols_exp = f"('{c_serie_type_code}', '{c_serie_value}', '{c_status_id}')"

        runner = CliRunner()
        args = ['ta', 'import', 'meter-data', DataSource.ACTIVE_ENERGY_CONS.value]

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        output = result.output
        print(output)

        assert result.exit_code == 1, 'Exit code is not 1!'
        assert message_exp in output, 'Expected message missing in terminal output!'
        assert missing_cols_exp in output, 'missing_cols_exp not in terminal output!'
        assert required_cols_exp in output, 'required_cols_exp missing in terminal output!'
        assert available_cols_exp in output, 'available_cols_exp missing in terminal output!'

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures(
        'default_config_file_location_does_not_exist',
        'config_import_method_file_in_config_file_env_var',
    )
    def test_empty_input_file(self, empty_active_energy_cons_import_parquet_file: Path) -> None:
        r"""Test to import active energy consumption from an empty parquet file."""

        # Setup
        # ===========================================================
        runner = CliRunner()
        args = ['ta', 'import', 'meter-data', DataSource.ACTIVE_ENERGY_CONS.value]

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        print(result.output)

        assert result.exit_code == 1, 'Exit code is not 1!'
        assert str(empty_active_energy_cons_import_parquet_file) in result.output, (
            'Input file path not in terminal output!'
        )

        # Clean up - None
        # ===========================================================
