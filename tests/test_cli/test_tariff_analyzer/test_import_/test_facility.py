# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Unit tests for the module cli.tariff_analyzer.import_.facility."""

# Standard library
import re
from pathlib import Path
from unittest.mock import Mock

# Third party
import pandas as pd
import pytest
from click.testing import CliRunner
from pandas.testing import assert_frame_equal
from sqlalchemy import select

# Local
import elsabio.cli.main
from elsabio.cli.main import main
from elsabio.config import ConfigManager, load_config
from elsabio.config.tariff_analyzer import DataSource
from elsabio.database import SessionFactory
from elsabio.database.models.tariff_analyzer import Facility
from elsabio.models.tariff_analyzer import FacilityDataFrameModel, FacilityImportDataFrameModel

FILENAME_WITH_TIMESTAMP_PATTERN = re.compile(
    r'^\d{4}-\d{2}-\d{2}T\d{2}\.\d{2}\.\d{2}[+-]\d{4}_[\w\.]*$'
)

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
    df.loc[1, c_facility_type_code] = None
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
    def test_from_parquet_file_with_2_facilities_existing_in_db(
        self,
        facility_import_parquet_file: Path,
        sqlite_db_with_2_facilities: SessionFactory,
        facilities_model: FacilityDataFrameModel,
        facilities_model_to_import: FacilityImportDataFrameModel,
    ) -> None:
        r"""Test to import facilities to the database from a parquet file.

        Two of the facilities to import already exist in the database.
        """

        # Setup
        # ===========================================================
        input_filename = facility_import_parquet_file
        message_exp = 'Successfully imported 8 new facilities and updated 2 existing facilities!\n'

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

        session_factory = sqlite_db_with_2_facilities
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
        assert FILENAME_WITH_TIMESTAMP_PATTERN.match(target_file.name) is not None, (
            'Filename of moved file is incorrect!'
        )

        df_import = pd.read_parquet(target_file)

        assert_frame_equal(df_import, facilities_model_to_import.df, check_dtype=False)

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures('default_config_file_location_does_not_exist')
    def test_from_parquet_file_with_all_facilities_existing_in_db(
        self,
        facility_import_parquet_file: Path,
        config_data_import_method_file: tuple[str, ConfigManager],
        sqlite_db_with_all_facilities: SessionFactory,
        facilities_model: FacilityDataFrameModel,
        facilities_model_to_import: FacilityImportDataFrameModel,
        tmp_path: Path,
    ) -> None:
        r"""Test to import facilities to the database from a parquet file.

        All facilities to import already exist in the database.
        """

        # Setup
        # ===========================================================
        input_filename = facility_import_parquet_file
        config_data_str, _ = config_data_import_method_file
        config_file_path = tmp_path / 'ElSabio_from_env_var.toml'
        config_file_path.write_text(config_data_str)

        message_exp = 'Successfully imported 0 new facilities and updated 10 existing facilities!\n'

        runner = CliRunner()
        args = ['--config', str(config_file_path), 'ta', 'import', 'facility']

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        print(result.output)

        assert result.exit_code == 0, 'Exit code is not 0!'
        assert message_exp in result.output, 'Expected output message missing in terminal output!'

        session_factory = sqlite_db_with_all_facilities
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
        assert FILENAME_WITH_TIMESTAMP_PATTERN.match(target_file.name) is not None, (
            'Filename of moved file is incorrect!'
        )

        df_import = pd.read_parquet(target_file)

        assert_frame_equal(df_import, facilities_model_to_import.df, check_dtype=False)

        # Clean up - None
        # ===========================================================

    def test_no_input_file_found(
        self,
        config_data_import_method_file: tuple[str, ConfigManager],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        r"""Test to import facilities when no input parquet file exists."""

        # Setup
        # ===========================================================
        _, cm = config_data_import_method_file

        m = Mock(spec_set=load_config, name='mocked_load_config', return_value=cm)
        monkeypatch.setattr(elsabio.cli.main, 'load_config', m)

        data = cm.tariff_analyzer.data
        cfg = data.get(DataSource.FACILITY)
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
        message_exp = f'Found facilities ({len(eans_exp)}) with missing or invalid facility_type!'

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
