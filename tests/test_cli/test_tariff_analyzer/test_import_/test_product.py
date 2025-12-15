# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Unit tests for the module cli.tariff_analyzer.import_.product."""

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

    def test_no_config_found(
        self, config_data_no_data_import: ConfigManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        r"""Test to import products when no product import configuration is defined."""

        # Setup
        # ===========================================================
        cm = config_data_no_data_import

        m = Mock(spec_set=load_config, name='mocked_load_config', return_value=cm)
        monkeypatch.setattr(elsabio.cli.main, 'load_config', m)

        message_exp = 'No data configuration found for "tariff_analyzer.data.product"!\n'

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

    def test_no_input_file_found(
        self,
        config_data_import_method_file: tuple[str, ConfigManager],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        r"""Test to import products when no input parquet file exists."""

        # Setup
        # ===========================================================
        _, cm = config_data_import_method_file

        m = Mock(spec_set=load_config, name='mocked_load_config', return_value=cm)
        monkeypatch.setattr(elsabio.cli.main, 'load_config', m)

        data = cm.tariff_analyzer.data
        cfg = data.get(DataSource.PRODUCT)
        assert cfg is not None, 'Missing configuration "tariff_analyzer.data.product"!'

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
        'product_import_parquet_file_missing_external_id_column',
    )
    def test_missing_external_id_column(self) -> None:
        r"""Test to import products when the `external_id` column is missing."""

        # Setup
        # ===========================================================
        message_exp = 'Missing the required columns!'
        required_cols_exp = "('external_id', 'name')"
        available_cols_exp = "('description', 'name')"

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
