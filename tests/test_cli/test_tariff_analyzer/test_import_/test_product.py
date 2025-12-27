# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Unit tests for the module cli.tariff_analyzer.import_.product."""

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
from elsabio.database import URL, SessionFactory
from elsabio.database.models.tariff_analyzer import Product
from elsabio.models.tariff_analyzer import (
    ProductDataFrameModel,
    ProductImportDataFrameModel,
)

# =================================================================================================
# Fixtures
# =================================================================================================


@pytest.fixture
def sqlite_db_with_2_products(initialized_sqlite_db: tuple[SessionFactory, URL]) -> SessionFactory:
    r"""An ElSabio SQLite database with 2 products persisted.

    Returns
    -------
    session_factory : elsabio.db.SessionFactory
        The session factory that can produce new database sessions.
    """

    session_factory, _ = initialized_sqlite_db

    with session_factory() as session:
        p1 = Product(
            product_id=1, external_id=14001, name='APARTMENT', description='Description to update'
        )
        p2 = Product(product_id=2, external_id=27001, name='Fuse Size')
        session.add_all((p1, p2))
        session.commit()

    return session_factory


@pytest.fixture
def sqlite_db_with_all_products(
    initialized_sqlite_db: tuple[SessionFactory, URL], product_model: ProductDataFrameModel
) -> SessionFactory:
    r"""An ElSabio SQLite database with all test products persisted.

    Returns
    -------
    session_factory : elsabio.db.SessionFactory
        The session factory that can produce new database sessions.
    """

    session_factory, _ = initialized_sqlite_db

    with session_factory() as session:
        product_model.df.to_sql(
            name=Product.__tablename__, con=session.get_bind(), if_exists='append', index=False
        )

    return session_factory


@pytest.fixture
def product_import_parquet_file(
    product_model_to_import: ProductImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> Path:
    r"""Write the product input data parquet file.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.
    """

    _, cm = config_data_import_method_file
    data = cm.tariff_analyzer.data

    product_data = data.get(DataSource.PRODUCT)
    assert product_data is not None, 'Missing configuration "tariff_analyzer.data.product"!'

    file = product_data.path / 'products.parquet'
    product_model_to_import.df.to_parquet(path=file)

    return file


@pytest.fixture
def product_parquet_file_missing_values_in_required_columns(
    product_model_to_import: ProductImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> tuple[Path, tuple[str, str]]:
    r"""A product parquet file with missing values for required columns.

    Two products have missing values for the required columns `external_id` and `name`.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.

    external_ids : tuple[str, str]
        The external ID:s of the products with missing values.
    """

    _, cm = config_data_import_method_file
    data = cm.tariff_analyzer.data.get(DataSource.PRODUCT)

    assert data is not None, (
        f'Missing configuration for "tariff_analyzer.data.{DataSource.PRODUCT}"!'
    )

    c_external_id = ProductImportDataFrameModel.c_external_id
    c_name = ProductImportDataFrameModel.c_name

    df = product_model_to_import.df.copy()
    df.loc[3, c_external_id] = None
    df.loc[5, c_name] = None
    external_ids = (str(df.loc[3, c_external_id]), str(df.loc[5, c_external_id]))

    file = data.path / 'products.parquet'
    df.to_parquet(path=file)

    return file, external_ids


@pytest.fixture
def product_parquet_file_with_duplicate_external_id_rows(
    product_model_to_import: ProductImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> tuple[Path, str]:
    r"""A product parquet file with duplicate rows of the `external_id` column.


    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.

    external_id : str
        The external_id of the duplicate row.
    """

    _, cm = config_data_import_method_file
    data = cm.tariff_analyzer.data.get(DataSource.PRODUCT)

    assert data is not None, (
        f'Missing configuration for "tariff_analyzer.data.{DataSource.PRODUCT}"!'
    )

    c_external_id = ProductImportDataFrameModel.c_external_id
    c_name = ProductImportDataFrameModel.c_name

    df = product_model_to_import.df.copy()
    duplicate_row = df.shape[0] + 1
    df.loc[duplicate_row, :] = df.loc[3, :]
    df.loc[duplicate_row, c_name] = 'test'
    external_id = str(df.loc[3, c_external_id])

    file = data.path / 'products.parquet'
    df.to_parquet(path=file)

    return file, external_id


@pytest.fixture
def product_parquet_file_with_duplicate_name_rows(
    product_model_to_import: ProductImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> tuple[Path, str]:
    r"""A product parquet file with duplicate rows fo the `name` column.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.

    name : str
        The name of the duplicate row.
    """

    _, cm = config_data_import_method_file
    data = cm.tariff_analyzer.data.get(DataSource.PRODUCT)

    assert data is not None, (
        f'Missing configuration for "tariff_analyzer.data.{DataSource.PRODUCT}"!'
    )

    c_external_id = ProductImportDataFrameModel.c_external_id
    c_name = ProductImportDataFrameModel.c_name

    df = product_model_to_import.df.copy()
    duplicate_row = df.shape[0] + 1
    df.loc[duplicate_row, :] = df.loc[3, :]
    df.loc[duplicate_row, c_external_id] = 'unique_new'
    name = str(df.loc[3, c_name])

    file = data.path / 'products.parquet'
    df.to_parquet(path=file)

    return file, name


@pytest.fixture
def product_import_parquet_file_missing_external_id_column(
    product_model_to_import: ProductImportDataFrameModel,
    config_data_import_method_file: tuple[str, ConfigManager],
) -> Path:
    r"""Write the product input data parquet file with the `external_id` column missing.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.
    """

    _, cm = config_data_import_method_file
    data = cm.tariff_analyzer.data

    product_data = data.get(DataSource.PRODUCT)
    assert product_data is not None, 'Missing configuration "tariff_analyzer.data.product"!'

    df = product_model_to_import.df.copy().drop(columns=[ProductImportDataFrameModel.c_external_id])

    file = product_data.path / 'products.parquet'
    df.to_parquet(path=file)

    return file


@pytest.fixture
def empty_product_import_parquet_file(
    config_data_import_method_file: tuple[str, ConfigManager],
) -> Path:
    r"""Write an empty product input parquet file.

    Returns
    -------
    file : pathlib.Path
        The full path to the parquet file.
    """

    _, cm = config_data_import_method_file
    data = cm.tariff_analyzer.data

    product_data = data.get(DataSource.PRODUCT)
    assert product_data is not None, 'Missing configuration "tariff_analyzer.data.product"!'

    df = pd.DataFrame()

    file = product_data.path / 'products.parquet'
    df.to_parquet(path=file)

    return file


# =================================================================================================
# Tests
# =================================================================================================


class TestTariffAnalyzerImportProductCommand:
    r"""Tests for CLI command `ta import product`."""

    @pytest.mark.usefixtures(
        'default_config_file_location_does_not_exist',
        'config_import_method_file_in_config_file_env_var',
    )
    @pytest.mark.parametrize(
        ('db_fixture', 'message_exp'),
        [
            pytest.param(
                'sqlite_db_with_2_products',
                'Successfully imported 3 new products and updated 2 existing products!\n',
                id='2 products in db',
            ),
            pytest.param(
                'sqlite_db_with_all_products',
                'Successfully imported 0 new products and updated 5 existing products!\n',
                id='All products in db',
            ),
            pytest.param(
                'initialized_sqlite_db',
                'Successfully imported 5 new products and updated 0 existing products!\n',
                id='No products in db',
            ),
        ],
    )
    def test_from_parquet_file(
        self,
        db_fixture: str,
        message_exp: str,
        request: pytest.FixtureRequest,
        product_import_parquet_file: Path,
        product_model: ProductDataFrameModel,
        product_model_to_import: ProductImportDataFrameModel,
        filename_with_timestamp_pattern_regex: re.Pattern,
    ) -> None:
        r"""Test to import products to the database from a parquet file."""

        # Setup
        # ===========================================================
        input_filename = product_import_parquet_file

        db = request.getfixturevalue(db_fixture)
        if isinstance(db, tuple):
            session_factory, _ = db
        else:
            session_factory = db

        runner = CliRunner()
        args = ['ta', 'import', 'product']

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        print(result.output)

        assert result.exit_code == 0, 'Exit code is not 0!'
        assert message_exp in result.output, 'Expected message missing in terminal output!'

        query = select(Product).order_by(Product.external_id.asc())

        with session_factory() as session:
            df_product = pd.read_sql(
                sql=query,
                con=session.get_bind(),
                dtype_backend='pyarrow',
                dtype=ProductDataFrameModel.dtypes,
            )

        assert_frame_equal(df_product, product_model.df)

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

        assert_frame_equal(df_import, product_model_to_import.df, check_dtype=False)

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures('mocked_load_config_with_no_import_data')
    def test_no_config_found(self) -> None:
        r"""Test to import products when no product import configuration is defined."""

        # Setup
        # ===========================================================
        message_exp = (
            f'No data configuration found for "tariff_analyzer.data.{DataSource.PRODUCT}"!\n'
        )

        runner = CliRunner()
        args = ['ta', 'import', 'product']

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
        r"""Test to import products when no input parquet file exists."""

        # Setup
        # ===========================================================
        _, cm = config_data_import_method_file
        cfg = cm.tariff_analyzer.data.get(DataSource.PRODUCT)

        assert cfg is not None, (
            f'Missing configuration "tariff_analyzer.data.{DataSource.PRODUCT}"!'
        )

        pattern_exp = f'{cfg.path}/*.parquet'

        runner = CliRunner()
        args = ['ta', 'import', 'product']

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
        product_parquet_file_missing_values_in_required_columns: tuple[Path, tuple[str, str]],
    ) -> None:
        r"""Test to import products with missing values in required columns."""

        # Setup
        # ===========================================================
        _, external_ids_exp = product_parquet_file_missing_values_in_required_columns
        required_cols = (
            ProductImportDataFrameModel.c_external_id,
            ProductImportDataFrameModel.c_name,
        )
        message_exp = (
            f'Found rows ({len(external_ids_exp)}) with missing values in required columns'
        )

        runner = CliRunner()
        args = ['ta', 'import', 'product']

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        output = result.output
        print(output)

        assert result.exit_code == 1, 'Exit code is not 1!'
        assert message_exp in output, 'Expected output message missing in terminal output!'

        for col in required_cols:
            assert col in output, f'Required column "{col}" missing in terminal output!'

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures(
        'default_config_file_location_does_not_exist',
        'config_import_method_file_in_config_file_env_var',
    )
    @pytest.mark.parametrize(
        ('fixture_func', 'required_col'),
        [
            pytest.param(
                'product_parquet_file_with_duplicate_external_id_rows',
                ProductImportDataFrameModel.c_external_id,
                id='external_id',
            ),
            pytest.param(
                'product_parquet_file_with_duplicate_name_rows',
                ProductImportDataFrameModel.c_name,
                id='name',
            ),
        ],
    )
    def test_duplicate_rows(
        self, fixture_func: str, required_col: str, request: pytest.FixtureRequest
    ) -> None:
        r"""Test to import products with duplicate rows."""

        # Setup
        # ===========================================================
        _, external_id_exp = request.getfixturevalue(fixture_func)
        message_exp = 'Found duplicate rows (1) over columns:'

        runner = CliRunner()
        args = ['ta', 'import', 'product']

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        output = result.output
        print(output)

        assert result.exit_code == 1, 'Exit code is not 1!'
        assert message_exp in output, 'Expected output message missing in terminal output!'

        assert external_id_exp in output, (
            f'external_id "{external_id_exp}" missing in terminal output!'
        )
        assert required_col in output, (
            f'Required column "{required_col}" missing in terminal output!'
        )

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures(
        'default_config_file_location_does_not_exist',
        'config_import_method_file_in_config_file_env_var',
        'product_import_parquet_file_missing_external_id_column',
    )
    def test_missing_external_id_column(self) -> None:
        r"""Test to import products when the `external_id` column is missing."""

        # Setup
        # ===========================================================
        c_external_id = ProductImportDataFrameModel.c_external_id
        c_name = ProductImportDataFrameModel.c_name
        c_description = ProductImportDataFrameModel.c_description

        message_exp = 'Missing the required columns!'
        required_cols_exp = f"('{c_external_id}', '{c_name}')"
        available_cols_exp = f"('{c_description}', '{c_name}')"

        runner = CliRunner()
        args = ['ta', 'import', 'product']

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        output = result.output
        print(output)

        assert result.exit_code == 1, 'Exit code is not 1!'
        assert message_exp in output, 'Expected message missing in terminal output!'
        assert required_cols_exp in output, 'Required cols missing in terminal output!'
        assert available_cols_exp in output, 'Available cols missing in terminal output!'

        # Clean up - None
        # ===========================================================

    @pytest.mark.usefixtures(
        'default_config_file_location_does_not_exist',
        'config_import_method_file_in_config_file_env_var',
    )
    def test_empty_input_file(self, empty_product_import_parquet_file: Path) -> None:
        r"""Test to import products from an empty parquet file."""

        # Setup
        # ===========================================================
        runner = CliRunner()
        args = ['ta', 'import', 'product']

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        print(result.output)

        assert result.exit_code == 1, 'Exit code is not 1!'
        assert str(empty_product_import_parquet_file) in result.output, (
            'Input file path not in terminal output!'
        )

        # Clean up - None
        # ===========================================================
