# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Fixtures for testing the Tariff Analyzer command (`ta`) of the ElSabio CLI."""

# Standard library
import re
from pathlib import Path

# Third party
import duckdb
import pytest
from sqlalchemy import select

# Local
import elsabio.config.config
from elsabio.config import BitwardenPasswordlessConfig, ConfigManager, ImportMethod
from elsabio.database import URL, SessionFactory
from elsabio.database.models.tariff_analyzer import Facility, FacilityType
from elsabio.models.tariff_analyzer import (
    FacilityDataFrameModel,
    FacilityImportDataFrameModel,
    ProductDataFrameModel,
    ProductImportDataFrameModel,
)
from elsabio.models.tariff_analyzer import FacilityTypeEnum as FacilityTypeEnum
from tests.config import STATIC_FILES_TARIFF_ANALYZER_BASE_DIR

# =================================================================================================
# Models
# =================================================================================================


@pytest.fixture
def product_model() -> ProductDataFrameModel:
    r"""The full test dataset of product as found when loaded from the database.

    The result of loading the content of fixture `product_model_to_import` into the database.

    Returns
    -------
    elsabio.models.tariff_analyzer.ProductDataFrameModel
        The DataFrame model of the products.
    """

    file = STATIC_FILES_TARIFF_ANALYZER_BASE_DIR / 'product.csv'
    assert file.exists(), f'File "{file}" does not exist!'

    df = duckdb.read_csv(str(file), sep=';').df().astype(ProductDataFrameModel.dtypes)

    return ProductDataFrameModel(df=df)


@pytest.fixture
def product_model_to_import(product_model: ProductDataFrameModel) -> ProductImportDataFrameModel:
    r"""The test dataset of the products to import to the database.

    Returns
    -------
    elsabio.models.tariff_analyzer.ProductImportDataFrameModel
        The DataFrame model of the products.
    """

    rel = duckdb.from_df(product_model.df)
    df = rel.project(f'* EXCLUDE({ProductDataFrameModel.c_product_id})').to_df()

    return ProductImportDataFrameModel(df=df)


@pytest.fixture
def facilities_model_to_import() -> FacilityImportDataFrameModel:
    r"""The test dataset of the facilities to import to the database.

    Returns
    -------
    elsabio.models.tariff_analyzer.FacilityImportDataFrameModel
        The DataFrame model of the facilities.
    """

    file = STATIC_FILES_TARIFF_ANALYZER_BASE_DIR / 'facility_import.csv'
    assert file.exists(), f'File "{file}" does not exist!'

    df = duckdb.read_csv(str(file), sep=';').df().astype(FacilityImportDataFrameModel.dtypes)

    return FacilityImportDataFrameModel(df=df)


@pytest.fixture
def facilities_model() -> FacilityDataFrameModel:
    r"""The full test dataset of facilities as found when loaded from the database.

    The result of loading the content fixture `facilities_model_to_import` into the database.

    Returns
    -------
    elsabio.models.tariff_analyzer.FacilityDataFrameModel
        The DataFrame model of the facilities.
    """

    file = STATIC_FILES_TARIFF_ANALYZER_BASE_DIR / 'facility.csv'
    assert file.exists(), f'File "{file}" does not exist!'

    df = duckdb.read_csv(str(file), sep=';').df().astype(FacilityDataFrameModel.dtypes)

    return FacilityDataFrameModel(df=df)


# =================================================================================================
# Database
# =================================================================================================


@pytest.fixture
def sqlite_db_with_2_facilities(
    initialized_sqlite_db: tuple[SessionFactory, URL],
) -> SessionFactory:
    r"""An ElSabio SQLite database with 2 facilities persisted.

    Returns
    -------
    session_factory : elsabio.db.SessionFactory
        The session factory that can produce new database sessions.
    """

    session_factory, _ = initialized_sqlite_db

    with session_factory() as session:
        facility_type_cons = session.execute(
            select(FacilityType).where(FacilityType.code == FacilityTypeEnum.CONSUMPTION)
        ).scalar_one()

        f1 = Facility(facility_id=1, ean=123456000000000001, facility_type=facility_type_cons)
        f2 = Facility(
            facility_id=2, ean=123456000000000002, ean_prod=123, facility_type=facility_type_cons
        )
        session.add_all((f1, f2))
        session.commit()

    return session_factory


@pytest.fixture
def sqlite_db_with_all_facilities(
    initialized_sqlite_db: tuple[SessionFactory, URL], facilities_model: FacilityDataFrameModel
) -> SessionFactory:
    r"""An ElSabio SQLite database with all test facilities persisted.

    Returns
    -------
    session_factory : elsabio.db.SessionFactory
        The session factory that can produce new database sessions.
    """

    session_factory, _ = initialized_sqlite_db

    with session_factory() as session:
        facilities_model.df.to_sql(
            name=Facility.__tablename__, con=session.get_bind(), if_exists='append', index=False
        )

    return session_factory


@pytest.fixture
def config_data_import_method_file(
    tmp_path: Path, empty_sqlite_db: tuple[URL, SessionFactory]
) -> tuple[str, ConfigManager]:
    r"""An ElSabio Tariff Analyzer configuration with file based data imports.

    Returns
    -------
    config_data_str : str
        The configuration as a string of toml.

    cm : elsabio.config.ConfigManager
        The expected configuration after loading and parsing `config_data_str`.
    """

    source_filename = 'config_tariff_analyzer_import_method_file.toml'
    source_config_file_path = STATIC_FILES_TARIFF_ANALYZER_BASE_DIR / source_filename

    assert source_config_file_path.exists(), f'File "{source_config_file_path}" does not exist!'

    config_data_str = source_config_file_path.read_text()

    _, db_url = empty_sqlite_db

    data_dir = tmp_path / 'data'
    data_dir.mkdir()

    product_input_path = tmp_path / 'product'
    product_input_path.mkdir()

    facility_input_path = tmp_path / 'facility'
    facility_input_path.mkdir()

    facility_contract_input_path = tmp_path / 'facility_contract'
    facility_contract_input_path.mkdir()

    active_energy_cons_input_path = tmp_path / 'active_energy_cons'
    active_energy_cons_input_path.mkdir()

    config_data_str = (
        config_data_str.replace(':db_url', str(db_url))
        .replace(':ta_data_dir', str(data_dir))
        .replace(':product_data_path', str(product_input_path))
        .replace(':facility_data_path', str(facility_input_path))
        .replace(':facility_contract_data_path', str(facility_contract_input_path))
        .replace(':active_energy_cons_data_path', str(active_energy_cons_input_path))
    )

    database_config = {'url': db_url, 'create_database': True}

    bwp_config = {'public_key': 'bwp_public_key', 'private_key': 'bwp_private_key'}

    tariff_analyzer = {
        'enabled': True,
        'data_dir': data_dir,
        'data': {
            'product': {'method': ImportMethod.FILE, 'path': product_input_path},
            'facility': {'method': ImportMethod.FILE, 'path': facility_input_path},
            'facility_contract': {
                'method': ImportMethod.FILE,
                'path': facility_contract_input_path,
            },
            'active_energy_cons': {
                'method': ImportMethod.FILE,
                'path': active_energy_cons_input_path,
            },
        },
    }

    config = {
        'database': database_config,
        'bwp': bwp_config,
        'tariff_analyzer': tariff_analyzer,
    }

    cm = ConfigManager.model_validate(config)

    return config_data_str, cm


@pytest.fixture
def config_import_method_file_in_config_file_env_var(
    config_data_import_method_file: tuple[str, ConfigManager],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[Path, ConfigManager]:
    r"""A config file defined using the config file env var ELSABIO_CONFIG_FILE.

    Returns
    -------
    config_file_path : pathlib.Path
        The path to the config file defined in the environment variable.

    cm : elsabio.config.ConfigManager
        The configuration written to `config_file_path`.
    """

    config_data_str, cm = config_data_import_method_file

    config_file_path = tmp_path / 'ElSabio_from_env_var.toml'
    config_file_path.write_text(config_data_str)

    monkeypatch.setenv(elsabio.config.config.CONFIG_FILE_ENV_VAR, str(config_file_path))

    return config_file_path, cm


@pytest.fixture
def config_data_no_data_import() -> ConfigManager:
    r"""A minimal ElSabio config without the Tariff Analyzer data section.

    Returns
    -------
    cm : elsabio.config.ConfigManager
        The configuration.
    """

    return ConfigManager(
        bwp=BitwardenPasswordlessConfig(public_key='public_key', private_key='private_key')
    )


@pytest.fixture(scope='module')
def filename_with_timestamp_pattern_regex() -> re.Pattern:
    r"""The regex for matching a filename with a timestamp prepended.

    Useful for testing the filename of an import file that has been moved
    to a sub-directory after successful import.

    Returns
    -------
    re.Pattern
        The regex pattern.
    """

    return re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}\.\d{2}\.\d{2}[+-]\d{4}_[\w\.]*$')
