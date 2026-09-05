# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Fixtures for testing the Tariff Analyzer command (`ta`) of the ElSabio CLI."""

# Standard library
import re
from datetime import date
from pathlib import Path
from unittest.mock import Mock

# Third party
import duckdb
import pandas as pd
import pytest
from sqlalchemy import select

# Local
import elsabio.cli.main
import elsabio.config.config
from elsabio.config import (
    BitwardenPasswordlessConfig,
    ConfigManager,
    DatabaseConfig,
    ImportMethod,
    load_config,
)
from elsabio.database import URL, SessionFactory
from elsabio.database.models.tariff_analyzer import (
    CustomerGroup,
    Facility,
    FacilityContract,
    FacilityCustomerGroupLink,
    FacilityType,
    Product,
    Tariff,
    TariffComponent,
    TariffComponentType,
    TariffCostGroup,
    TariffCostGroupCustomerGroupLink,
)
from elsabio.models.tariff_analyzer import (
    CustomerGroupDataFrameModel,
    FacilityContractDataFrameModel,
    FacilityContractImportDataFrameModel,
    FacilityCustomerGroupLinkDataFrameModel,
    FacilityDataFrameModel,
    FacilityImportDataFrameModel,
    ProductDataFrameModel,
    ProductImportDataFrameModel,
    SerieValueDataFrameModel,
    SerieValueImportDataFrameModel,
    TariffValueFacilityDataFrameModel,
    TariffValueTotalDataFrameModel,
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


@pytest.fixture(scope='module')
def facility_contract_model_file() -> Path:
    r"""The file path to the facility contract test dataset.

    Returns
    -------
    file : pathlib.Path
        The full path to the file containing the facility contract test dataset.
    """

    file = STATIC_FILES_TARIFF_ANALYZER_BASE_DIR / 'facility_contract.csv'
    assert file.exists(), f'File "{file}" does not exist!'

    return file


@pytest.fixture
def facility_contract_model_to_import(
    facility_contract_model_file: Path,
) -> FacilityContractImportDataFrameModel:
    r"""The test dataset of the facility contracts to import to the database.

    Returns
    -------
    elsabio.models.tariff_analyzer.FacilityContractImportDataFrameModel
        The DataFrame model of the facility contracts to import.
    """

    project = f"""* EXCLUDE(
    {FacilityContractDataFrameModel.c_facility_id}
    , {FacilityContractDataFrameModel.c_customer_type_id}
    , {FacilityContractDataFrameModel.c_product_id}
)
"""

    df = (
        duckdb.read_csv(str(facility_contract_model_file), sep=';')
        .project(project)
        .df(date_as_object=True)
        .astype(FacilityContractImportDataFrameModel.dtypes)
    )

    return FacilityContractImportDataFrameModel(df=df)


@pytest.fixture
def facility_contract_model(
    facility_contract_model_file: Path,
) -> FacilityContractDataFrameModel:
    r"""The test dataset of facility contracts as found when loaded from the database.

    The result of loading the content of fixture `facility_contract_model_to_import` into the database.

    Returns
    -------
    elsabio.models.tariff_analyzer.FacilityContractDataFrameModel
        The DataFrame model of the facility contracts.
    """

    project_cols = f"""* EXCLUDE(
    {FacilityContractImportDataFrameModel.c_ean}
    , {FacilityContractImportDataFrameModel.c_customer_type_code}
    , {FacilityContractImportDataFrameModel.c_ext_product_id}
)
"""

    df = (
        duckdb.read_csv(str(facility_contract_model_file), sep=';')
        .project(project_cols)
        .df(date_as_object=True)
        .astype(FacilityContractDataFrameModel.dtypes)
    )

    return FacilityContractDataFrameModel(df=df)


@pytest.fixture
def active_energy_cons_model() -> SerieValueDataFrameModel:
    r"""The test dataset of the active energy consumption meter data.

    The result of loading the content of fixture `active_energy_cons_model_to_import`
    into the parquet hive.

    Returns
    -------
    elsabio.models.tariff_analyzer.SerieValueDataFrameModel
        The DataFrame model of the active energy consumption meter data.
    """

    file = STATIC_FILES_TARIFF_ANALYZER_BASE_DIR / '2025-11_active_energy_cons.csv'
    assert file.exists(), f'File "{file}" does not exist!'

    df = (
        duckdb.read_csv(str(file), sep=';')
        .df(date_as_object=True)
        .astype(SerieValueDataFrameModel.dtypes)
    )

    return SerieValueDataFrameModel(df=df)


@pytest.fixture
def active_energy_cons_model_to_import(
    active_energy_cons_model: SerieValueDataFrameModel,
) -> SerieValueImportDataFrameModel:
    r"""The test dataset of the active energy consumption meter data to import.

    Returns
    -------
    elsabio.models.tariff_analyzer.SerieValueImportDataFrameModel
        The DataFrame model of the active energy consumption meter data to import.
    """

    df = (
        duckdb.from_df(active_energy_cons_model.df)
        .select(f'* EXCLUDE({SerieValueDataFrameModel.c_facility_id})')
        .df(date_as_object=True)
        .astype(SerieValueImportDataFrameModel.dtypes)
    )

    return SerieValueImportDataFrameModel(df=df)


@pytest.fixture
def max_reactive_power_cons_model() -> SerieValueDataFrameModel:
    r"""The test dataset of the max reactive power consumption meter data.

    The result of loading the content of fixture `max_reactive_power_cons_model_to_import`
    into the parquet hive.

    Returns
    -------
    elsabio.models.tariff_analyzer.SerieValueDataFrameModel
        The DataFrame model of the max reactive power consumption meter data.
    """

    file = STATIC_FILES_TARIFF_ANALYZER_BASE_DIR / '2025-10_2025-11_max_reactive_power_cons.csv'
    assert file.exists(), f'File "{file}" does not exist!'

    df = (
        duckdb.read_csv(str(file), sep=';')
        .df(date_as_object=True)
        .astype(SerieValueDataFrameModel.dtypes)
    )

    return SerieValueDataFrameModel(df=df)


@pytest.fixture
def max_reactive_power_cons_model_to_import(
    max_reactive_power_cons_model: SerieValueDataFrameModel,
) -> SerieValueImportDataFrameModel:
    r"""The test dataset of the max reactive power consumption meter data to import.

    Returns
    -------
    elsabio.models.tariff_analyzer.SerieValueImportDataFrameModel
        The DataFrame model of the max reactive power consumption meter data to import.
    """

    df = (
        duckdb.from_df(max_reactive_power_cons_model.df)
        .select(f'* EXCLUDE({SerieValueDataFrameModel.c_facility_id})')
        .df(date_as_object=True)
        .astype(SerieValueImportDataFrameModel.dtypes)
    )

    return SerieValueImportDataFrameModel(df=df)


@pytest.fixture
def active_energy_prod_model() -> SerieValueDataFrameModel:
    r"""The test dataset of the active energy production.

    Returns
    -------
    elsabio.models.tariff_analyzer.SerieValueDataFrameModel
        The DataFrame model of the active energy production.
    """

    file = STATIC_FILES_TARIFF_ANALYZER_BASE_DIR / '2025-10_2025-11_active_energy_prod.csv'
    assert file.exists(), f'File "{file}" does not exist!'

    df = (
        duckdb.read_csv(str(file), sep=';')
        .df(date_as_object=True)
        .astype(SerieValueDataFrameModel.dtypes)
    )

    return SerieValueDataFrameModel(df=df)


@pytest.fixture
def max_deb_active_power_cons_high_load_model() -> SerieValueDataFrameModel:
    r"""The test dataset of the max debitable active power consumption during high load.

    Returns
    -------
    elsabio.models.tariff_analyzer.SerieValueDataFrameModel
        The DataFrame model of the max debitable active power consumption during high load.
    """

    file = (
        STATIC_FILES_TARIFF_ANALYZER_BASE_DIR
        / '2025-10_2025-11_max_deb_active_power_cons_high_load.csv'
    )
    assert file.exists(), f'File "{file}" does not exist!'

    df = (
        duckdb.read_csv(str(file), sep=';')
        .df(date_as_object=True)
        .astype(SerieValueDataFrameModel.dtypes)
    )

    return SerieValueDataFrameModel(df=df)


@pytest.fixture
def max_active_power_cons_model() -> SerieValueDataFrameModel:
    r"""The test dataset of the max active power consumption.

    Returns
    -------
    elsabio.models.tariff_analyzer.SerieValueDataFrameModel
        The DataFrame model of the max active power consumption.
    """

    file = STATIC_FILES_TARIFF_ANALYZER_BASE_DIR / '2025-10_2025-11_max_active_power_cons.csv'
    assert file.exists(), f'File "{file}" does not exist!'

    df = (
        duckdb.read_csv(str(file), sep=';')
        .df(date_as_object=True)
        .astype(SerieValueDataFrameModel.dtypes)
    )

    return SerieValueDataFrameModel(df=df)


@pytest.fixture(scope='session')
def customer_group_model() -> CustomerGroupDataFrameModel:
    r"""The test dataset of the customer groups.

    Returns
    -------
    elsabio.models.tariff_analyzer.CustomerDataFrameModel
        The DataFrame model of the customer groups.
    """

    file = STATIC_FILES_TARIFF_ANALYZER_BASE_DIR / 'customer_group.csv'
    assert file.exists(), f'File "{file}" does not exist!'

    c_mapping_strategy_code = CustomerGroupDataFrameModel.c_mapping_strategy_code
    dtypes = {
        col: dtype
        for col, dtype in CustomerGroupDataFrameModel.dtypes.items()
        if col != c_mapping_strategy_code
    }

    df = (
        duckdb.read_csv(str(file), sep=';')
        .select(f'* EXCLUDE(description, {c_mapping_strategy_code})')
        .df(date_as_object=True)
        .astype(dtypes)
    )

    return CustomerGroupDataFrameModel(df=df)


@pytest.fixture(scope='session')
def facility_customer_group_link_model() -> FacilityCustomerGroupLinkDataFrameModel:
    r"""The test dataset of the facility customer group links.

    Returns
    -------
    elsabio.models.tariff_analyzer.CustomerDataFrameModel
        The DataFrame model of the facility customer group links.
    """

    file = STATIC_FILES_TARIFF_ANALYZER_BASE_DIR / 'facility_customer_group_link.csv'
    assert file.exists(), f'File "{file}" does not exist!'

    df = (
        duckdb.read_csv(str(file), sep=';')
        .df(date_as_object=True)
        .astype(FacilityCustomerGroupLinkDataFrameModel.dtypes)
    )

    return FacilityCustomerGroupLinkDataFrameModel(df=df)


@pytest.fixture(scope='session')
def tariff_df() -> pd.DataFrame:
    r"""The test dataset of the tariffs.

    Returns
    -------
    pandas.DataFrame
        The DataFrame of the tariffs.
    """

    file = STATIC_FILES_TARIFF_ANALYZER_BASE_DIR / 'tariff.csv'
    assert file.exists(), f'File "{file}" does not exist!'

    return pd.read_csv(file, sep=';', dtype_backend='pyarrow')


@pytest.fixture(scope='session')
def tariff_cost_group_df() -> pd.DataFrame:
    r"""The test dataset of the tariff cost groups.

    Returns
    -------
    pandas.DataFrame
        The DataFrame of the tariff cost groups.
    """

    file = STATIC_FILES_TARIFF_ANALYZER_BASE_DIR / 'tariff_cost_group.csv'
    assert file.exists(), f'File "{file}" does not exist!'

    return pd.read_csv(file, sep=';', dtype_backend='pyarrow')


@pytest.fixture(scope='session')
def tariff_cost_group_customer_group_link_df() -> pd.DataFrame:
    r"""The test dataset of the tariff cost group customer group links.

    Returns
    -------
    pandas.DataFrame
        The DataFrame of the tariff cost groups.
    """

    file = STATIC_FILES_TARIFF_ANALYZER_BASE_DIR / 'tariff_cost_group_customer_group_link.csv'
    assert file.exists(), f'File "{file}" does not exist!'

    return pd.read_csv(file, sep=';', dtype_backend='pyarrow')


@pytest.fixture(scope='session')
def tariff_component_type_df() -> pd.DataFrame:
    r"""The test dataset of the tariff component types.

    Returns
    -------
    pandas.DataFrame
        The DataFrame of the tariff component types.
    """

    file = STATIC_FILES_TARIFF_ANALYZER_BASE_DIR / 'tariff_component_type.csv'
    assert file.exists(), f'File "{file}" does not exist!'

    exclude_cols = ', '.join(
        c
        for c in (
            'unit_code',
            'calc_strategy_code',
            'periodize_strategy_code',
            'serie_type_code',
            'comparison_serie_type_code',
        )
    )

    return duckdb.read_csv(str(file), sep=';').select(f'* EXCLUDE({exclude_cols})').df()


@pytest.fixture(scope='session')
def tariff_component_df() -> pd.DataFrame:
    r"""The test dataset of the tariff components.

    Returns
    -------
    pandas.DataFrame
        The DataFrame of the tariff components
    """

    file = STATIC_FILES_TARIFF_ANALYZER_BASE_DIR / 'tariff_component.csv'
    assert file.exists(), f'File "{file}" does not exist!'

    return duckdb.read_csv(str(file), sep=';').select('* EXCLUDE(unit, description)').df()


@pytest.fixture(scope='session')
def tariff_value_facility_model() -> TariffValueFacilityDataFrameModel:
    r"""The test dataset of the calculated tariff value result per facility.

    Returns
    -------
    elsabio.models.tariff_analyzer.TariffValueFacilityDataFrameModel
        The DataFrame model of the tariff value result per facility.
    """

    file = STATIC_FILES_TARIFF_ANALYZER_BASE_DIR / '2025-10_2025-11_tariff_value_facility.csv'
    assert file.exists(), f'File "{file}" does not exist!'

    df = (
        duckdb.read_csv(str(file), sep=';')
        .select('* EXCLUDE(ean, description)')
        .df(date_as_object=True)
        .astype(TariffValueFacilityDataFrameModel.dtypes)
    )

    return TariffValueFacilityDataFrameModel(df=df)


@pytest.fixture(scope='session')
def tariff_value_total_model() -> TariffValueTotalDataFrameModel:
    r"""The test dataset of the calculated total tariff value result.

    Returns
    -------
    elsabio.models.tariff_analyzer.TariffValueTotalDataFrameModel
        The DataFrame model of the total tariff value result.
    """

    file = STATIC_FILES_TARIFF_ANALYZER_BASE_DIR / '2025-10_2025-11_tariff_value_total.csv'
    assert file.exists(), f'File "{file}" does not exist!'

    df = (
        duckdb.read_csv(str(file), sep=';')
        .df(date_as_object=True)
        .astype(TariffValueTotalDataFrameModel.dtypes)
    )
    return TariffValueTotalDataFrameModel(df=df)


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
def sqlite_db_with_products_and_facilities(
    initialized_sqlite_db: tuple[SessionFactory, URL],
    product_model: ProductDataFrameModel,
    facilities_model: FacilityDataFrameModel,
) -> SessionFactory:
    r"""An ElSabio SQLite database with products and facilities persisted.

    Returns
    -------
    session_factory : elsabio.db.SessionFactory
        The session factory that can produce new database sessions.
    """

    session_factory, _ = initialized_sqlite_db

    with session_factory() as session:
        conn = session.get_bind()
        product_model.df.to_sql(
            name=Product.__tablename__, con=conn, if_exists='append', index=False
        )
        facilities_model.df.to_sql(
            name=Facility.__tablename__, con=conn, if_exists='append', index=False
        )

    return session_factory


@pytest.fixture
def sqlite_db_with_tariffs(
    initialized_sqlite_db: tuple[SessionFactory, URL],
    product_model: ProductDataFrameModel,
    facilities_model: FacilityDataFrameModel,
    facility_contract_model: FacilityContractDataFrameModel,
    customer_group_model: CustomerGroupDataFrameModel,
    facility_customer_group_link_model: FacilityCustomerGroupLinkDataFrameModel,
    tariff_df: pd.DataFrame,
    tariff_cost_group_df: pd.DataFrame,
    tariff_cost_group_customer_group_link_df: pd.DataFrame,
    tariff_component_type_df: pd.DataFrame,
    tariff_component_df: pd.DataFrame,
) -> SessionFactory:
    r"""An ElSabio SQLite database with tariffs and their related objects defined.

    Contains all data to enable tariff calculations.

    Returns
    -------
    session_factory : elsabio.db.SessionFactory
        The session factory that can produce new database sessions.
    """

    session_factory, _ = initialized_sqlite_db

    with session_factory() as session:
        conn = session.get_bind()
        product_model.df.to_sql(
            name=Product.__tablename__, con=conn, if_exists='append', index=False
        )
        facilities_model.df.to_sql(
            name=Facility.__tablename__, con=conn, if_exists='append', index=False
        )
        facility_contract_model.df.to_sql(
            name=FacilityContract.__tablename__, con=conn, if_exists='append', index=False
        )
        customer_group_model.df.to_sql(
            name=CustomerGroup.__tablename__, con=conn, if_exists='append', index=False
        )
        facility_customer_group_link_model.df.to_sql(
            name=FacilityCustomerGroupLink.__tablename__, con=conn, if_exists='append', index=False
        )
        tariff_df.to_sql(name=Tariff.__tablename__, con=conn, if_exists='append', index=False)
        tariff_cost_group_df.to_sql(
            name=TariffCostGroup.__tablename__, con=conn, if_exists='append', index=False
        )
        tariff_cost_group_customer_group_link_df.to_sql(
            name=TariffCostGroupCustomerGroupLink.__tablename__,
            con=conn,
            if_exists='append',
            index=False,
        )
        tariff_component_type_df.to_sql(
            name=TariffComponentType.__tablename__, con=conn, if_exists='append', index=False
        )
        tariff_component_df.to_sql(
            name=TariffComponent.__tablename__, con=conn, if_exists='append', index=False
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

    max_reactive_power_cons_input_path = tmp_path / 'max_reactive_power_cons'
    max_reactive_power_cons_input_path.mkdir()

    config_data_str = (
        config_data_str.replace(':db_url', str(db_url))
        .replace(':ta_data_dir', str(data_dir))
        .replace(':product_data_path', str(product_input_path))
        .replace(':facility_data_path', str(facility_input_path))
        .replace(':facility_contract_data_path', str(facility_contract_input_path))
        .replace(':active_energy_cons_data_path', str(active_energy_cons_input_path))
        .replace(':max_reactive_power_cons_data_path', str(max_reactive_power_cons_input_path))
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
            'max_reactive_power_cons': {
                'method': ImportMethod.FILE,
                'path': max_reactive_power_cons_input_path,
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
def mocked_load_config_with_no_import_data(
    monkeypatch: pytest.MonkeyPatch, sqlite_db_with_2_facilities: SessionFactory
) -> tuple[Mock, ConfigManager]:
    r"""A mocked version of `elsabio.config.load_config`.

    The `load_config` function of the CLI is mocked to load a configuration
    without the Tariff Analyzer data section.

    Returns
    -------
    m : unittest.mock.Mock
        The mock object.

    cm : elsabio.config.ConfigManager
        The configuration.
    """

    engine = sqlite_db_with_2_facilities.kw['bind']
    db_cfg = DatabaseConfig(url=str(engine.url), create_database=False)

    cm = ConfigManager(
        database=db_cfg,
        bwp=BitwardenPasswordlessConfig(public_key='public_key', private_key='private_key'),
    )

    m = Mock(spec_set=load_config, name='mocked_load_config', return_value=cm)
    monkeypatch.setattr(elsabio.cli.main, 'load_config', m)

    return m, cm


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


# =================================================================================================
# Tariff calculations
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
