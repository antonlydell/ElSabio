# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Unit tests for the module cli.tariff_analyzer.import_.facility."""

# Standard library
import re
from pathlib import Path

# Third party
import pandas as pd
import pytest
from click.testing import CliRunner
from pandas.testing import assert_frame_equal
from sqlalchemy import select

# Local
from elsabio.cli.main import main
from elsabio.config import ConfigManager
from elsabio.config.tariff_analyzer import DataSource
from elsabio.database.models.tariff_analyzer import Facility
from elsabio.models.tariff_analyzer import FacilityDataFrameModel, FacilityImportDataFrameModel

# =================================================================================================
# Fixtures
# =================================================================================================


@pytest.fixture
def facility_import_parquet_file(
    facilities_model_to_import: FacilityImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> Path:
    r"""Write the facility test input data parquet file.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.
    """

    _, cm = config_data_import_method_file
    data = cm.tariff_analyzer.data

    facility_data = data.get(DataSource.FACILITY)
    assert facility_data is not None, 'Missing configuration "tariff_analyzer.data.facility"!'

    file = facility_data.path / 'facilities.parquet'
    facilities_model_to_import.df.to_parquet(path=file)

    return file


@pytest.fixture
def facility_import_parquet_file_missing_values_in_required_columns(
    facilities_model_to_import: FacilityImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> tuple[Path, tuple[str, ...]]:
    r"""A facility parquet file with missing values in required columns.

    3 rows have missing values for the required columns `ean` and `facility_type_code`.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.

    ean_codes : tuple[str, ...]
        The EAN codes of the rows with missing values.
    """

    _, cm = config_data_import_method_file
    data = cm.tariff_analyzer.data.get(DataSource.FACILITY)

    assert data is not None, 'Missing configuration for "tariff_analyzer.facility"!'

    c_ean = FacilityImportDataFrameModel.c_ean
    facility_type_code = FacilityImportDataFrameModel.c_facility_type_code

    df = facilities_model_to_import.df.copy()
    df.loc[1, facility_type_code] = None
    df.loc[2, [c_ean]] = None
    df.loc[3, [facility_type_code, c_ean]] = [None, None]
    ean_codes = tuple(str(df.loc[v, c_ean]) for v in range(1, 4))

    file = data.path / 'facilities.parquet'
    df.to_parquet(path=file)

    return file, ean_codes


@pytest.fixture
def facility_import_parquet_file_with_duplicate_ean_rows(
    facilities_model_to_import: FacilityImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> tuple[Path, tuple[str, ...]]:
    r"""A facility parquet file with duplicate rows of the `ean` column.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.

    ean_codes : str
        The EAN codes of the duplicate rows.
    """

    _, cm = config_data_import_method_file
    data = cm.tariff_analyzer.data.get(DataSource.FACILITY)

    assert data is not None, 'Missing configuration for "tariff_analyzer.data.facility"!'

    c_ean = FacilityImportDataFrameModel.c_ean
    c_name = FacilityImportDataFrameModel.c_name

    df = facilities_model_to_import.df.copy()
    duplicate_row = df.shape[0] + 1
    df.loc[duplicate_row, :] = df.loc[6, :]
    df.loc[duplicate_row, c_name] = 'test'
    ean_codes = (str(df.loc[6, c_ean]),)

    file = data.path / 'facilities.parquet'
    df.to_parquet(path=file)

    return file, ean_codes


@pytest.fixture
def facility_import_parquet_file_with_duplicate_ean_prod_rows(
    facilities_model_to_import: FacilityImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> tuple[Path, tuple[str, ...]]:
    r"""A facility parquet file with duplicate rows of the `ean_prod` column.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.

    ean_codes : str
        The EAN codes of the duplicate rows.
    """

    _, cm = config_data_import_method_file
    data = cm.tariff_analyzer.data.get(DataSource.FACILITY)

    assert data is not None, 'Missing configuration for "tariff_analyzer.data.facility"!'

    c_ean = FacilityImportDataFrameModel.c_ean
    c_ean_prod = FacilityImportDataFrameModel.c_ean_prod

    df = facilities_model_to_import.df.copy()
    duplicate_row_1 = df.shape[0] + 1
    duplicate_row_2 = duplicate_row_1 + 1
    df.loc[duplicate_row_1, :] = df.loc[2, :]
    df.loc[duplicate_row_1, c_ean] = 123
    df.loc[duplicate_row_2, :] = df.loc[5, :]
    df.loc[duplicate_row_2, c_ean] = 124
    ean_codes = (str(df.loc[2, c_ean_prod]), str(df.loc[5, c_ean_prod]))

    file = data.path / 'facilities.parquet'
    df.to_parquet(path=file)

    return file, ean_codes


@pytest.fixture
def facility_import_parquet_file_invalid_facility_type(
    facilities_model_to_import: FacilityImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> tuple[Path, tuple[str, str]]:
    r"""Write the facility test input data parquet file with invalid facility types.

    One facility has a missing facility type code and another one has an invalid code.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.

    ean_codes : tuple[str, str]
        The EAN codes of the facilities with invalid facility type codes.
    """

    _, cm = config_data_import_method_file
    data = cm.tariff_analyzer.data

    facility_data = data.get(DataSource.FACILITY)
    assert facility_data is not None, 'Missing configuration "tariff_analyzer.data.facility"!'

    c_facility_type_code = FacilityImportDataFrameModel.c_facility_type_code
    c_ean = FacilityImportDataFrameModel.c_ean

    df = facilities_model_to_import.df.copy()
    df.loc[1, c_facility_type_code] = 'test'
    df.loc[3, c_facility_type_code] = 'invalid'
    ean_codes = (str(df.loc[1, c_ean]), str(df.loc[3, c_ean]))

    file = facility_data.path / 'facilities.parquet'
    df.to_parquet(path=file)

    return file, ean_codes


@pytest.fixture
def empty_facility_import_parquet_file(
    config_data_import_method_file: tuple[str, ConfigManager],
) -> Path:
    r"""Write an empty facility input parquet file.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.
    """

    _, cm = config_data_import_method_file
    data = cm.tariff_analyzer.data

    facility_data = data.get(DataSource.FACILITY)
    assert facility_data is not None, 'Missing configuration "tariff_analyzer.data.facility"!'

    df = pd.DataFrame()

    file = facility_data.path / 'facilities.parquet'
    df.to_parquet(path=file)

    return file


# =================================================================================================
# Tests
# =================================================================================================


class TestTariffAnalyzerImportFacilityCommand:
    r"""Tests for CLI command `ta import facility`."""

    @pytest.mark.usefixtures(
        'default_config_file_location_does_not_exist',
        'config_import_method_file_in_config_file_env_var',
    )
    @pytest.mark.parametrize(
        ('db_fixture', 'message_exp'),
        [
            pytest.param(
                'sqlite_db_with_2_facilities',
                'Successfully imported 8 new facilities and updated 2 existing facilities!',
                id='2 facilities in db',
            ),
            pytest.param(
                'sqlite_db_with_all_facilities',
                'Successfully imported 0 new facilities and updated 10 existing facilities!',
                id='All facilities in db',
            ),
            pytest.param(
                'initialized_sqlite_db',
                'Successfully imported 10 new facilities and updated 0 existing facilities!',
                id='No facilities in db',
            ),
        ],
    )
    @pytest.mark.usefixtures(
        'default_config_file_location_does_not_exist',
        'config_import_method_file_in_config_file_env_var',
    )
    def test_from_parquet_file(
        self,
        db_fixture: str,
        message_exp: str,
        request: pytest.FixtureRequest,
        facility_import_parquet_file: Path,
        facilities_model: FacilityDataFrameModel,
        facilities_model_to_import: FacilityImportDataFrameModel,
        filename_with_timestamp_pattern_regex: re.Pattern,
    ) -> None:
        r"""Test to import facilities to the database from a parquet file."""

        # Setup
        # ===========================================================
        input_filename = facility_import_parquet_file

        db = request.getfixturevalue(db_fixture)
        if isinstance(db, tuple):
            session_factory, _ = db
        else:
            session_factory = db

        runner = CliRunner()
        args = ['ta', 'import', 'facility']

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        print(result.output)

        assert result.exit_code == 0, 'Exit code is not 0!'
        assert message_exp in result.output, 'Expected output message missing in terminal output!'

        query = select(Facility).order_by(Facility.ean.asc())

        with session_factory() as session:
            df_facility = pd.read_sql(
                sql=query,
                con=session.get_bind(),
                dtype_backend='pyarrow',
                dtype=FacilityDataFrameModel.dtypes,
            )

        assert_frame_equal(df_facility, facilities_model.df)

        # Check that imported file is moved to sub-directory success
        target_dir = input_filename.parent / 'success'
        assert not input_filename.exists(), 'Input file not moved!'

        target_files = list(target_dir.iterdir())
        assert len(target_files) == 1, 'Incorrect nr of items in target directory!'

        target_file = target_files[0]
        assert filename_with_timestamp_pattern_regex.match(target_file.name) is not None, (
            'Filename of moved file is incorrect!'
        )

        df_import = pd.read_parquet(target_file)

        assert_frame_equal(df_import, facilities_model_to_import.df, check_dtype=False)

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures('mocked_load_config_with_no_import_data')
    def test_no_config_found(self) -> None:
        r"""Test to import facilities when no configuration is defined."""

        # Setup
        # ===========================================================
        message_exp = f'No configuration found for "tariff_analyzer.data.{DataSource.FACILITY}"!\n'

        runner = CliRunner()
        args = ['ta', 'import', 'facility']

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

    @pytest.mark.usefixtures(
        'default_config_file_location_does_not_exist',
        'config_import_method_file_in_config_file_env_var',
    )
    def test_no_input_file_found(
        self, config_data_import_method_file: tuple[str, ConfigManager]
    ) -> None:
        r"""Test to import facilities when no input parquet file exists."""

        # Setup
        # ===========================================================
        _, cm = config_data_import_method_file
        cfg = cm.tariff_analyzer.data.get(DataSource.FACILITY)

        assert cfg is not None, 'Missing configuration "tariff_analyzer.data.facility"!'

        pattern_exp = f'{cfg.path}/*.parquet'

        runner = CliRunner()
        args = ['ta', 'import', 'facility']

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        print(result.output)

        assert result.exit_code == 1, 'Exit code is not 1!'
        assert pattern_exp in result.output, 'Expected output message missing in terminal output!'

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures(
        'default_config_file_location_does_not_exist',
        'config_import_method_file_in_config_file_env_var',
    )
    def test_missing_values_in_required_columns(
        self,
        facility_import_parquet_file_missing_values_in_required_columns: tuple[
            Path, tuple[str, ...]
        ],
    ) -> None:
        r"""Test to import facilities with missing values in required columns."""

        # Setup
        # ===========================================================
        _, eans_exp = facility_import_parquet_file_missing_values_in_required_columns
        required_cols = (
            FacilityImportDataFrameModel.c_facility_type_code,
            FacilityImportDataFrameModel.c_ean,
        )
        message_exp = f'Found rows ({len(eans_exp)}) with missing values in required columns'

        runner = CliRunner()
        args = ['ta', 'import', 'facility']

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
    @pytest.mark.parametrize(
        ('fixture_func', 'required_col', 'nr_duplicates'),
        [
            pytest.param(
                'facility_import_parquet_file_with_duplicate_ean_rows',
                FacilityImportDataFrameModel.c_ean,
                1,
                id='ean',
            ),
            pytest.param(
                'facility_import_parquet_file_with_duplicate_ean_prod_rows',
                FacilityImportDataFrameModel.c_ean_prod,
                2,
                id='ean_prod',
            ),
        ],
    )
    def test_duplicate_rows(
        self,
        fixture_func: str,
        required_col: str,
        nr_duplicates: int,
        request: pytest.FixtureRequest,
    ) -> None:
        r"""Test to import facilities with duplicate values in unique columns."""

        # Setup
        # ===========================================================
        _, eans_exp = request.getfixturevalue(fixture_func)
        message_exp = f'Found duplicate rows ({nr_duplicates}) over columns:'

        runner = CliRunner()
        args = ['ta', 'import', 'facility']

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        output = result.output
        print(output)

        assert result.exit_code == 1, 'Exit code is not 1!'
        assert message_exp in output, 'Expected output message missing in terminal output!'

        for ean_exp in eans_exp:
            assert ean_exp in output, f'EAN "{ean_exp}" missing in terminal output!'

        assert required_col in output, (
            f'Required column "{required_col}" missing in terminal output!'
        )

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures(
        'default_config_file_location_does_not_exist',
        'config_import_method_file_in_config_file_env_var',
        'sqlite_db_with_2_facilities',
    )
    def test_invalid_facility_type_code(
        self,
        facility_import_parquet_file_invalid_facility_type: tuple[Path, tuple[str, str]],
    ) -> None:
        r"""Test to import facilities when 2 of the facilities have invalid facility type codes."""

        # Setup
        # ===========================================================
        _, eans_exp = facility_import_parquet_file_invalid_facility_type
        message_exp = (
            f'Found facilities ({len(eans_exp)}) with invalid values '
            f'for column "{FacilityImportDataFrameModel.c_facility_type_code}"!'
        )

        runner = CliRunner()
        args = ['ta', 'import', 'facility']

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
    def test_empty_input_file(self, empty_facility_import_parquet_file: Path) -> None:
        r"""Test to import facilities from an empty parquet file."""

        # Setup
        # ===========================================================
        runner = CliRunner()
        args = ['ta', 'import', 'facility']

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        print(result.output)

        assert result.exit_code == 1, 'Exit code is not 1!'
        assert str(empty_facility_import_parquet_file) in result.output, (
            'Input file path not in terminal output!'
        )

        # Clean up - None
        # ===========================================================
