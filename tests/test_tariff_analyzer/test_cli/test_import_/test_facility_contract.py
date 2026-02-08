# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Unit tests for the module cli.tariff_analyzer.import_.facility_contract."""

# Standard library
import re
from datetime import date
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
from elsabio.database import URL, SessionFactory
from elsabio.database.models.tariff_analyzer import Facility, FacilityContract, Product
from elsabio.models.tariff_analyzer import (
    FacilityContractDataFrameModel,
    FacilityContractImportDataFrameModel,
    FacilityDataFrameModel,
    ProductDataFrameModel,
)

# =================================================================================================
# Fixtures
# =================================================================================================


@pytest.fixture
def sqlite_db_with_facilities_and_products(
    initialized_sqlite_db: tuple[SessionFactory, URL],
    product_model: ProductDataFrameModel,
    facilities_model: FacilityDataFrameModel,
) -> SessionFactory:
    r"""An ElSabio SQLite database with all test products and facilities persisted.

    Returns
    -------
    session_factory : elsabio.db.SessionFactory
        The session factory that can produce new database sessions.
    """

    session_factory, _ = initialized_sqlite_db

    with session_factory() as session:
        conn = session.get_bind()
        facilities_model.df.to_sql(
            name=Facility.__tablename__, con=conn, if_exists='append', index=False
        )
        product_model.df.to_sql(
            name=Product.__tablename__, con=conn, if_exists='append', index=False
        )

    return session_factory


@pytest.fixture
def sqlite_db_with_2_facility_contracts(
    sqlite_db_with_facilities_and_products: SessionFactory,
) -> SessionFactory:
    r"""An ElSabio SQLite database with 2 facility contracts persisted.

    Returns
    -------
    session_factory : elsabio.db.SessionFactory
        The session factory that can produce new database sessions.
    """

    session_factory = sqlite_db_with_facilities_and_products

    with session_factory() as session:
        fc1 = FacilityContract(
            facility_id=1,
            date_id=date(2025, 11, 1),
            fuse_size=17,
            connection_power=12,
            account_nr=1234,
            customer_type_id=1,
        )
        fc2 = FacilityContract(
            facility_id=2,
            date_id=date(2025, 11, 1),
            account_nr=1234,
            customer_type_id=1,
            product_id=2,
        )
        session.add_all((fc1, fc2))
        session.commit()

    return session_factory


@pytest.fixture
def sqlite_db_with_all_facility_contracts(
    sqlite_db_with_facilities_and_products: SessionFactory,
    facility_contract_model: FacilityContractDataFrameModel,
) -> SessionFactory:
    r"""An ElSabio SQLite database with all test facility contracts persisted.

    Returns
    -------
    session_factory : elsabio.db.SessionFactory
        The session factory that can produce new database sessions.
    """

    session_factory = sqlite_db_with_facilities_and_products

    with session_factory() as session:
        facility_contract_model.df.to_sql(
            name=FacilityContract.__tablename__,
            con=session.get_bind(),
            if_exists='append',
            index=False,
        )

    return session_factory


@pytest.fixture
def facility_contract_import_parquet_file(
    facility_contract_model_to_import: FacilityContractImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> Path:
    r"""An input parquet file with the test facility contracts.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.
    """

    _, cm = config_data_import_method_file
    facility_contract_data = cm.tariff_analyzer.data.get(DataSource.FACILITY_CONTRACT)

    assert facility_contract_data is not None, (
        'Missing configuration "tariff_analyzer.data.facility_contract"!'
    )

    file = facility_contract_data.path / 'facility_contracts.parquet'
    facility_contract_model_to_import.df.to_parquet(path=file)

    return file


@pytest.fixture
def facility_contract_parquet_file_with_unknown_facility(
    facility_contract_model_to_import: FacilityContractImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> tuple[Path, str]:
    r"""A parquet file with facility contracts where one contract has an unknown EAN code.

    One facility contract does not have a corresponding facility in the
    facility table. This facility contract cannot be imported.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.

    ean_code : str
        The unknown EAN code.
    """

    _, cm = config_data_import_method_file
    facility_contract_data = cm.tariff_analyzer.data.get(DataSource.FACILITY_CONTRACT)

    assert facility_contract_data is not None, (
        'Missing configuration "tariff_analyzer.data.facility_contract"!'
    )

    c_ean = FacilityContractImportDataFrameModel.c_ean
    file = facility_contract_data.path / 'facility_contracts.parquet'

    df = facility_contract_model_to_import.df.copy()
    df.loc[3, c_ean] = 1234560000000000039
    ean_code = str(df.loc[3, c_ean])

    df.to_parquet(path=file)

    return file, ean_code


@pytest.fixture
def facility_contract_parquet_file_missing_required_columns(
    facility_contract_model_to_import: FacilityContractImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> Path:
    r"""An input facility contract parquet file with required columns missing.

    The `ean` and `date_id` columns are missing.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.
    """

    _, cm = config_data_import_method_file
    product_data = cm.tariff_analyzer.data.get(DataSource.FACILITY_CONTRACT)

    assert product_data is not None, (
        'Missing configuration "tariff_analyzer.data.facility_contract"!'
    )

    df = facility_contract_model_to_import.df.copy().drop(
        columns=[
            FacilityContractImportDataFrameModel.c_ean,
            FacilityContractImportDataFrameModel.c_date_id,
        ]
    )

    file = product_data.path / 'facility_contracts.parquet'
    df.to_parquet(path=file)

    return file


@pytest.fixture
def facility_contract_parquet_file_missing_values_in_required_columns(
    facility_contract_model_to_import: FacilityContractImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> tuple[Path, tuple[str, ...]]:
    r"""A facility contract parquet file with missing values for required columns.

    The 2 facility contracts have missing values for the
    required columns `date_id` and `customer_type_code`.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.

    ean_codes : tuple[str, str]
        The EAN codes of the facility contracts with missing values.
    """

    _, cm = config_data_import_method_file
    facility_data = cm.tariff_analyzer.data.get(DataSource.FACILITY_CONTRACT)

    assert facility_data is not None, (
        'Missing configuration for "tariff_analyzer.data.facility_contract"!'
    )

    c_ean = FacilityContractImportDataFrameModel.c_ean
    c_date_id = FacilityContractImportDataFrameModel.c_date_id
    c_customer_type_code = FacilityContractImportDataFrameModel.c_customer_type_code

    df = facility_contract_model_to_import.df.copy()
    df.loc[3, c_date_id] = None
    df.loc[4, c_customer_type_code] = None
    df.loc[5, c_ean] = None
    ean_codes = tuple(str(df.loc[i, c_ean]) for i in range(3, 6))

    file = facility_data.path / 'facility_contracts.parquet'
    df.to_parquet(path=file)

    return file, ean_codes


@pytest.fixture
def facility_contract_parquet_file_with_duplicate_rows(
    facility_contract_model_to_import: FacilityContractImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> tuple[Path, str]:
    r"""A facility contract parquet file with duplicate rows.

    Contains 1 duplicate row over the columns `ean` and `date_id`.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.

    ean_code : str
        The EAN code of the duplicate row.
    """

    _, cm = config_data_import_method_file
    data = cm.tariff_analyzer.data.get(DataSource.FACILITY_CONTRACT)

    assert data is not None, (
        f'Missing configuration for "tariff_analyzer.data.{DataSource.FACILITY_CONTRACT}"!'
    )

    c_ean = FacilityContractImportDataFrameModel.c_ean
    c_fuse_size = FacilityContractImportDataFrameModel.c_fuse_size

    df = facility_contract_model_to_import.df.copy()
    duplicate_row = df.shape[0] + 1
    df.loc[duplicate_row, :] = df.loc[3, :]
    df.loc[duplicate_row, c_fuse_size] = 93
    ean_code = str(df.loc[3, c_ean])

    file = data.path / 'facility_contracts.parquet'
    df.to_parquet(path=file)

    return file, ean_code


@pytest.fixture
def facility_contract_parquet_file_invalid_customer_type_code(
    facility_contract_model_to_import: FacilityContractImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> tuple[Path, tuple[str, str]]:
    r"""A facility contract parquet file with invalid values for the `customer_type_code` column.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.

    ean_codes : tuple[str, str]
        The EAN codes of the facility contracts with missing values.
    """

    _, cm = config_data_import_method_file
    facility_data = cm.tariff_analyzer.data.get(DataSource.FACILITY_CONTRACT)

    assert facility_data is not None, (
        'Missing configuration for "tariff_analyzer.data.facility_contract"!'
    )

    c_ean = FacilityContractImportDataFrameModel.c_ean
    c_customer_type_code = FacilityContractImportDataFrameModel.c_customer_type_code

    df = facility_contract_model_to_import.df.copy()
    df.loc[2, c_customer_type_code] = 'invalid'
    df.loc[4, c_customer_type_code] = 'test'
    ean_codes = (str(df.loc[2, c_ean]), str(df.loc[4, c_ean]))

    file = facility_data.path / 'facility_contracts.parquet'
    df.to_parquet(path=file)

    return file, ean_codes


@pytest.fixture
def facility_contract_parquet_file_date_id_not_at_month_start(
    facility_contract_model_to_import: FacilityContractImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> tuple[Path, tuple[str, str]]:
    r"""A facility contract parquet file with dates not at the start of a month.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.

    ean_codes : tuple[str, str]
        The EAN codes of the facility contracts with invalid dates.
    """

    _, cm = config_data_import_method_file
    facility_data = cm.tariff_analyzer.data.get(DataSource.FACILITY_CONTRACT)

    assert facility_data is not None, (
        'Missing configuration for "tariff_analyzer.data.facility_contract"!'
    )

    c_ean = FacilityContractImportDataFrameModel.c_ean
    c_date_id = FacilityContractImportDataFrameModel.c_date_id

    df = facility_contract_model_to_import.df.copy()
    df.loc[3, c_date_id] = date(2025, 11, 11)
    df.loc[5, c_date_id] = date(2025, 11, 12)
    ean_codes = (str(df.loc[3, c_ean]), str(df.loc[5, c_ean]))

    file = facility_data.path / 'facility_contracts.parquet'
    df.to_parquet(path=file)

    return file, ean_codes


@pytest.fixture
def empty_facility_contract_import_parquet_file(
    config_data_import_method_file: tuple[str, ConfigManager],
) -> Path:
    r"""An empty facility contract parquet file.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.
    """

    _, cm = config_data_import_method_file
    product_data = cm.tariff_analyzer.data.get(DataSource.FACILITY_CONTRACT)

    assert product_data is not None, (
        'Missing configuration "tariff_analyzer.data.facility_contract"!'
    )

    df = pd.DataFrame()

    file = product_data.path / 'facility_contracts.parquet'
    df.to_parquet(path=file)

    return file


# =================================================================================================
# Tests
# =================================================================================================


class TestTariffAnalyzerImportFacilityContractCommand:
    r"""Tests for CLI command `ta import facility-contract`."""

    @pytest.mark.usefixtures(
        'default_config_file_location_does_not_exist',
        'config_import_method_file_in_config_file_env_var',
    )
    @pytest.mark.parametrize(
        ('db_fixture', 'message_exp'),
        [
            pytest.param(
                'sqlite_db_with_2_facility_contracts',
                (
                    'Successfully imported 14 new facility contracts and '
                    'updated 2 existing facility contracts in interval '
                    '2025-10-01 - 2025-12-01!'
                ),
                id='2 facility contracts in db',
            ),
            pytest.param(
                'sqlite_db_with_all_facility_contracts',
                (
                    'Successfully imported 0 new facility contracts and '
                    'updated 16 existing facility contracts in interval '
                    '2025-10-01 - 2025-12-01!'
                ),
                id='All facility contracts in db',
            ),
            pytest.param(
                'sqlite_db_with_facilities_and_products',
                (
                    'Successfully imported 16 new facility contracts and '
                    'updated 0 existing facility contracts in interval '
                    '2025-10-01 - 2025-12-01!'
                ),
                id='No facility contracts in db',
            ),
        ],
    )
    def test_from_parquet_file(
        self,
        db_fixture: str,
        message_exp: str,
        request: pytest.FixtureRequest,
        facility_contract_import_parquet_file: Path,
        facility_contract_model: FacilityContractDataFrameModel,
        facility_contract_model_to_import: FacilityContractImportDataFrameModel,
        filename_with_timestamp_pattern_regex: re.Pattern,
    ) -> None:
        r"""Test to import facility contracts to the database from a parquet file."""

        # Setup
        # ===========================================================
        input_filename = facility_contract_import_parquet_file
        session_factory: SessionFactory = request.getfixturevalue(db_fixture)

        runner = CliRunner()
        args = ['ta', 'import', 'facility-contract']

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        print(result.output)

        assert result.exit_code == 0, 'Exit code is not 0!'
        assert message_exp in result.output, 'Expected message missing in terminal output!'

        query = select(FacilityContract).order_by(
            FacilityContract.date_id.asc(), FacilityContract.facility_id.asc()
        )
        c_date_id = FacilityContractDataFrameModel.c_date_id

        with session_factory() as session:
            df_facility_contract = pd.read_sql(
                sql=query,
                con=session.get_bind(),
                dtype_backend='pyarrow',
                dtype=FacilityContractDataFrameModel.dtypes,
                parse_dates=FacilityContractDataFrameModel.parse_dates,
            ).assign(**{c_date_id: lambda df_: df_[c_date_id].dt.date})

        assert_frame_equal(df_facility_contract, facility_contract_model.df)

        # Check that the imported file is moved to sub-directory success
        target_dir = input_filename.parent / 'success'
        assert not input_filename.exists(), 'Input file not moved!'

        target_files = list(target_dir.iterdir())
        assert len(target_files) == 1, 'Incorrect nr of items in target directory!'

        target_file = target_files[0]
        assert filename_with_timestamp_pattern_regex.match(target_file.name) is not None, (
            'Filename of moved file is incorrect!'
        )

        df_import = pd.read_parquet(target_file)

        assert_frame_equal(df_import, facility_contract_model_to_import.df, check_dtype=False)

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures('mocked_load_config_with_no_import_data')
    def test_no_config_found(self) -> None:
        r"""Test to import facility contracts when no configuration is defined."""

        # Setup
        # ===========================================================
        message_exp = (
            f'No data configuration found for '
            f'"tariff_analyzer.data.{DataSource.FACILITY_CONTRACT}"!\n'
        )

        runner = CliRunner()
        args = ['ta', 'import', 'facility-contract']

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
        r"""Test to import facility contracts when no input parquet file exists."""

        # Setup
        # ===========================================================
        _, cm = config_data_import_method_file
        cfg = cm.tariff_analyzer.data.get(DataSource.FACILITY_CONTRACT)

        assert cfg is not None, 'Missing configuration "tariff_analyzer.data.facility_contract"!'

        pattern_exp = f'{cfg.path}/*.parquet'

        runner = CliRunner()
        args = ['ta', 'import', 'facility-contract']

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        print(result.output)

        assert result.exit_code == 1, 'Exit code is not 1!'
        assert pattern_exp in result.output, 'Expected message missing in terminal output!'

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures(
        'default_config_file_location_does_not_exist',
        'config_import_method_file_in_config_file_env_var',
    )
    def test_missing_values_in_required_columns(
        self,
        facility_contract_parquet_file_missing_values_in_required_columns: tuple[
            Path, tuple[str, ...]
        ],
    ) -> None:
        r"""Test to import facility contracts with missing values in required columns."""

        # Setup
        # ===========================================================
        _, eans_exp = facility_contract_parquet_file_missing_values_in_required_columns
        required_cols = (
            FacilityContractImportDataFrameModel.c_ean,
            FacilityContractImportDataFrameModel.c_date_id,
        )
        message_exp = f'Found rows ({len(eans_exp)}) with missing values in required columns'

        runner = CliRunner()
        args = ['ta', 'import', 'facility-contract']

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
    )
    def test_duplicate_rows(
        self, facility_contract_parquet_file_with_duplicate_rows: tuple[Path, str]
    ) -> None:
        r"""Test to import facility contracts with duplicate rows."""

        # Setup
        # ===========================================================
        _, ean_exp = facility_contract_parquet_file_with_duplicate_rows
        required_cols = (
            FacilityContractImportDataFrameModel.c_ean,
            FacilityContractImportDataFrameModel.c_date_id,
        )
        message_exp = 'Found duplicate rows (1) over columns:'

        runner = CliRunner()
        args = ['ta', 'import', 'facility-contract']

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
        'sqlite_db_with_facilities_and_products',
    )
    def test_facility_not_in_facility_table(
        self,
        facility_contract_parquet_file_with_unknown_facility: tuple[Path, str],
    ) -> None:
        r"""Test to import a facility contract that does not have an entry in the facility table."""

        # Setup
        # ===========================================================
        _, ean_exp = facility_contract_parquet_file_with_unknown_facility

        message_exp = (
            'Found facility contracts (1) with unknown EAN codes '
            f'in column "{FacilityContractImportDataFrameModel.c_ean}"!'
        )

        runner = CliRunner()
        args = ['ta', 'import', 'facility-contract']

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

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures(
        'default_config_file_location_does_not_exist',
        'config_import_method_file_in_config_file_env_var',
        'sqlite_db_with_2_facility_contracts',
    )
    def test_invalid_values_for_customer_type_code_column(
        self,
        facility_contract_parquet_file_invalid_customer_type_code: tuple[Path, tuple[str, str]],
    ) -> None:
        r"""Test to import facility contracts with missing values in required columns."""

        # Setup
        # ===========================================================
        _, eans_exp = facility_contract_parquet_file_invalid_customer_type_code
        message_exp = (
            f'Found facility contracts ({len(eans_exp)}) with '
            'invalid values for column "customer_type_code"!'
        )

        runner = CliRunner()
        args = ['ta', 'import', 'facility-contract']

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
        facility_contract_parquet_file_date_id_not_at_month_start: tuple[Path, tuple[str, str]],
    ) -> None:
        r"""Test to import facility contracts with dates not at the start of a month."""

        # Setup
        # ===========================================================
        _, eans_exp = facility_contract_parquet_file_date_id_not_at_month_start
        message_exp = f'Found rows ({len(eans_exp)}) not at start of month!'

        runner = CliRunner()
        args = ['ta', 'import', 'facility-contract']

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
        'facility_contract_parquet_file_missing_required_columns',
    )
    def test_missing_required_columns(self) -> None:
        r"""Test to import facility contracts when required columns are missing."""

        # Setup
        # ===========================================================
        c_ean = FacilityContractImportDataFrameModel.c_ean
        c_date_id = FacilityContractImportDataFrameModel.c_date_id
        c_fuse_size = FacilityContractImportDataFrameModel.c_fuse_size
        c_subscribed_power = FacilityContractImportDataFrameModel.c_subscribed_power
        c_connection_power = FacilityContractImportDataFrameModel.c_connection_power
        c_account_nr = FacilityContractImportDataFrameModel.c_account_nr
        c_customer_type_code = FacilityContractImportDataFrameModel.c_customer_type_code
        c_ext_product_id = FacilityContractImportDataFrameModel.c_ext_product_id

        message_exp = 'Missing the required columns!'
        missing_cols_exp = f"('{c_date_id}', '{c_ean}')"
        required_cols_exp = f"('{c_customer_type_code}', '{c_date_id}', '{c_ean}')"
        available_cols_exp = (
            f"('{c_account_nr}', '{c_connection_power}', '{c_customer_type_code}', "
            f"'{c_ext_product_id}', '{c_fuse_size}', '{c_subscribed_power}')"
        )

        runner = CliRunner()
        args = ['ta', 'import', 'facility-contract']

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
    def test_empty_input_file(self, empty_facility_contract_import_parquet_file: Path) -> None:
        r"""Test to import facility contracts from an empty parquet file."""

        # Setup
        # ===========================================================
        runner = CliRunner()
        args = ['ta', 'import', 'facility-contract']

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        print(result.output)

        assert result.exit_code == 1, 'Exit code is not 1!'
        assert str(empty_facility_contract_import_parquet_file) in result.output, (
            'Input file path not in terminal output!'
        )

        # Clean up - None
        # ===========================================================
