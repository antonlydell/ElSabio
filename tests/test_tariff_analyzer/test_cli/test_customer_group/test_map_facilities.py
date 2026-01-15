# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Unit tests for the module `cli.tariff_analyzer.customer_group.map_facilities`"""

# Standard library
from datetime import date
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
from elsabio.config import (
    BitwardenPasswordlessConfig,
    ConfigManager,
    DatabaseConfig,
    load_config,
)
from elsabio.database import URL, Session, SessionFactory
from elsabio.database.models.tariff_analyzer import (
    CustomerGroup,
    FacilityContract,
    FacilityCustomerGroupLink,
)
from elsabio.models.tariff_analyzer import (
    CustomerGroupDataFrameModel,
    FacilityContractDataFrameModel,
    FacilityCustomerGroupLinkDataFrameModel,
)

# =================================================================================================
# Fixtures
# =================================================================================================


@pytest.fixture
def mocked_load_config(
    monkeypatch: pytest.MonkeyPatch, initialized_sqlite_db: tuple[SessionFactory, URL]
) -> tuple[Mock, ConfigManager]:
    r"""A mocked version of `elsabio.config.load_config`.

    The `load_config` function of the CLI is mocked to a minimal
    configuration with an initialized ElSabio SQLite database.

    Returns
    -------
    m : unittest.mock.Mock
        The mock object.

    cm : elsabio.config.ConfigManager
        The configuration.
    """

    _, url = initialized_sqlite_db

    cm = ConfigManager(
        database=DatabaseConfig(url=url),
        bwp=BitwardenPasswordlessConfig(public_key='public_key', private_key='private_key'),
    )

    m = Mock(spec_set=load_config, name='mocked_load_config', return_value=cm)
    monkeypatch.setattr(elsabio.cli.main, 'load_config', m)

    return m, cm


@pytest.fixture
def sqlite_db_with_facility_contracts_and_customer_groups(
    sqlite_db_with_products_and_facilities: SessionFactory,
    customer_group_model: CustomerGroupDataFrameModel,
    facility_contract_model: FacilityContractDataFrameModel,
) -> SessionFactory:
    r"""An ElSabio SQLite database with all facility contracts and customer groups persisted.

    The database also has products and facilities persisted.

    Returns
    -------
    session_factory : elsabio.db.SessionFactory
        The session factory that can produce new database sessions.
    """

    session_factory = sqlite_db_with_products_and_facilities

    with session_factory() as session:
        conn = session.get_bind()
        facility_contract_model.df.to_sql(
            name=FacilityContract.__tablename__, con=conn, if_exists='append', index=False
        )
        customer_group_model.df.to_sql(
            name=CustomerGroup.__tablename__, con=conn, if_exists='append', index=False
        )

    return session_factory


@pytest.fixture
def sqlite_db_with_customer_groups_without_facility_contracts(
    sqlite_db_with_products_and_facilities: SessionFactory,
    customer_group_model: CustomerGroupDataFrameModel,
) -> SessionFactory:
    r"""An ElSabio SQLite database with customer groups and without facility contracts.

    The database also has products and facilities persisted.

    Returns
    -------
    session_factory : elsabio.db.SessionFactory
        The session factory that can produce new database sessions.
    """

    session_factory = sqlite_db_with_products_and_facilities

    with session_factory() as session:
        conn = session.get_bind()
        customer_group_model.df.to_sql(
            name=CustomerGroup.__tablename__, con=conn, if_exists='append', index=False
        )

    return session_factory


@pytest.fixture
def sqlite_db_with_2_facility_customer_group_links(
    sqlite_db_with_facility_contracts_and_customer_groups: SessionFactory,
) -> SessionFactory:
    r"""An ElSabio SQLite database with 2 facility customer group links.

    Returns
    -------
    session_factory : elsabio.db.SessionFactory
        The session factory that can produce new database sessions.
    """

    session_factory = sqlite_db_with_facility_contracts_and_customer_groups

    with session_factory() as session:
        fcgl1 = FacilityCustomerGroupLink(
            facility_id=1, date_id=date(2025, 11, 1), customer_group_id=15
        )
        fcgl2 = FacilityCustomerGroupLink(
            facility_id=2, date_id=date(2025, 11, 1), customer_group_id=4
        )
        session.add_all((fcgl1, fcgl2))
        session.commit()

    return session_factory


@pytest.fixture
def sqlite_db_with_all_facility_customer_group_links(
    sqlite_db_with_facility_contracts_and_customer_groups: SessionFactory,
    facility_customer_group_link_model: FacilityCustomerGroupLinkDataFrameModel,
) -> SessionFactory:
    r"""An ElSabio SQLite database with all test facility customer group links persisted.

    Returns
    -------
    session_factory : elsabio.db.SessionFactory
        The session factory that can produce new database sessions.
    """

    session_factory = sqlite_db_with_facility_contracts_and_customer_groups

    with session_factory() as session:
        facility_customer_group_link_model.df.to_sql(
            name=FacilityCustomerGroupLink.__tablename__,
            con=session.get_bind(),
            if_exists='append',
            index=False,
        )

    return session_factory


@pytest.fixture
def sqlite_db_with_unmapped_facility_contract(
    sqlite_db_with_products_and_facilities: SessionFactory,
    customer_group_model: CustomerGroupDataFrameModel,
    facility_contract_model: FacilityContractDataFrameModel,
) -> tuple[int, SessionFactory]:
    r"""An ElSabio SQLite database with a facility that can not be mapped to a customer group.

    Returns
    -------
    facility_id : int
        The ID of the facility that can not be mapped to a customer group.

    session_factory : elsabio.db.SessionFactory
        The session factory that can produce new database sessions.
    """

    session_factory = sqlite_db_with_products_and_facilities

    c_fuse_size = FacilityContractDataFrameModel.c_fuse_size
    c_facility_id = FacilityContractDataFrameModel.c_facility_id
    c_date_id = FacilityContractDataFrameModel.c_date_id

    df_fc = facility_contract_model.df.copy().set_index([c_facility_id, c_date_id])

    facility_id = 2  # facility contract 16 A
    df_fc.loc[(facility_id, date(2025, 11, 1)), c_fuse_size] = 15

    with session_factory() as session:
        conn = session.get_bind()
        df_fc.to_sql(name=FacilityContract.__tablename__, con=conn, if_exists='append', index=True)
        customer_group_model.df.to_sql(
            name=CustomerGroup.__tablename__, con=conn, if_exists='append', index=False
        )

    return facility_id, session_factory


@pytest.fixture
def sqlite_db_with_required_product_id_missing_for_product_strategy(
    sqlite_db_with_products_and_facilities: SessionFactory,
    customer_group_model: CustomerGroupDataFrameModel,
    facility_contract_model: FacilityContractDataFrameModel,
) -> tuple[int, int, SessionFactory]:
    r"""One customer group has the product mapping strategy but no value for `product_id`.

    This has the effect that one facility cannot be mapped to a customer group.

    Returns
    -------
    customer_group_id : int
        The ID of the customer group with the missing value for the `product_id` column.

    facility_id : int
        The ID of the facility that cannot be mapped to a customer group.

    session_factory : elsabio.db.SessionFactory
        The session factory that can produce new database sessions.
    """

    session_factory = sqlite_db_with_products_and_facilities

    c_product_id = CustomerGroupDataFrameModel.c_product_id
    c_customer_group_id = CustomerGroupDataFrameModel.c_customer_group_id

    df_cg = customer_group_model.df.copy().set_index(c_customer_group_id)

    customer_group_id = 1  # apartment
    df_cg.loc[customer_group_id, c_product_id] = pd.NA

    df_fc = facility_contract_model.df
    facility_id = 1  # facility contract 16 A Apartment

    with session_factory() as session:
        conn = session.get_bind()
        df_fc.to_sql(name=FacilityContract.__tablename__, con=conn, if_exists='append', index=False)
        df_cg.to_sql(name=CustomerGroup.__tablename__, con=conn, if_exists='append', index=True)

    return customer_group_id, facility_id, session_factory


@pytest.fixture
def sqlite_db_with_facility_mapped_to_2_customer_groups(
    sqlite_db_with_products_and_facilities: SessionFactory,
    customer_group_model: CustomerGroupDataFrameModel,
    facility_contract_model: FacilityContractDataFrameModel,
) -> tuple[int, SessionFactory]:
    r"""The customer groups are defined such that one facility can be mapped to two groups.

    Returns
    -------
    facility_id : int
        The ID of the facility that can be mapped to two customer groups.

    session_factory : elsabio.db.SessionFactory
        The session factory that can produce new database sessions.
    """

    session_factory = sqlite_db_with_products_and_facilities

    c_not_product_id = CustomerGroupDataFrameModel.c_not_product_id
    c_customer_group_id = CustomerGroupDataFrameModel.c_customer_group_id

    df_cg = customer_group_model.df.copy().set_index(c_customer_group_id)

    customer_group_id = 2  # 16_A
    df_cg.loc[customer_group_id, c_not_product_id] = pd.NA

    df_fc = facility_contract_model.df
    facility_id = 1  # facility contract 16 A Apartment

    with session_factory() as session:
        conn = session.get_bind()
        df_fc.to_sql(name=FacilityContract.__tablename__, con=conn, if_exists='append', index=False)
        df_cg.to_sql(name=CustomerGroup.__tablename__, con=conn, if_exists='append', index=False)

    return facility_id, session_factory


def load_facility_customer_group_links(session: Session) -> pd.DataFrame:
    r"""Helper function to load the facility customer group links."""

    query = select(FacilityCustomerGroupLink).order_by(
        FacilityCustomerGroupLink.date_id.asc(), FacilityCustomerGroupLink.facility_id.asc()
    )
    c_date_id = FacilityCustomerGroupLinkDataFrameModel.c_date_id

    return pd.read_sql(
        sql=query,
        con=session.get_bind(),
        dtype_backend='pyarrow',
        dtype=FacilityCustomerGroupLinkDataFrameModel.dtypes,
        parse_dates=FacilityCustomerGroupLinkDataFrameModel.parse_dates,
    ).assign(**{c_date_id: lambda df_: df_[c_date_id].dt.date})


# =================================================================================================
# Tests
# =================================================================================================


@pytest.mark.usefixtures('mocked_load_config')
class TestCustomerGroupMapFacilitiesCommand:
    r"""Tests for CLI command `elsabio ta cg map-facilities`."""

    @pytest.mark.parametrize(
        ('db_fixture', 'message_exp'),
        [
            pytest.param(
                'sqlite_db_with_2_facility_customer_group_links',
                (
                    'Successfully imported 8 new facility customer group links and '
                    'updated 2 existing facility customer group links in interval '
                    '2025-11-01 - 2025-12-01!'
                ),
                id='2 facility customer group links in db',
            ),
            pytest.param(
                'sqlite_db_with_facility_contracts_and_customer_groups',
                (
                    'Successfully imported 10 new facility customer group links and '
                    'updated 0 existing facility customer group links in interval '
                    '2025-11-01 - 2025-12-01!'
                ),
                id='No facility customer group links in db',
            ),
            pytest.param(
                'sqlite_db_with_all_facility_customer_group_links',
                (
                    'Successfully imported 0 new facility customer group links and '
                    'updated 10 existing facility customer group links in interval '
                    '2025-11-01 - 2025-12-01!'
                ),
                id='All facility customer group links in db',
            ),
        ],
    )
    def test_map_facilities(
        self,
        db_fixture: str,
        message_exp: str,
        request: pytest.FixtureRequest,
        facility_customer_group_link_model: FacilityContractDataFrameModel,
    ) -> None:
        r"""Test to map facilities to customer groups."""

        # Setup
        # ===========================================================
        session_factory: SessionFactory = request.getfixturevalue(db_fixture)

        runner = CliRunner()
        args = ['ta', 'cg', 'map-facilities', '--interval', '2025-11-01..2025-12-01']

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        print(result.output)

        assert result.exit_code == 0, 'Exit code is not 0!'
        assert message_exp in result.output, 'Expected message missing in terminal output!'

        with session_factory() as session:
            df_f_cg_link = load_facility_customer_group_links(session=session)

        assert_frame_equal(df_f_cg_link, facility_customer_group_link_model.df)

        # Clean up - None
        # ===========================================================

    @pytest.mark.parametrize(
        ('db_fixture', 'message_exp'),
        [
            pytest.param(
                'initialized_sqlite_db',
                'No customer groups exist!',
                id='No customer groups',
            ),
            pytest.param(
                'sqlite_db_with_customer_groups_without_facility_contracts',
                'No facility contracts exist!',
                id='No facility contracts',
            ),
        ],
    )
    def test_input_data_missing_in_db(
        self, db_fixture: str, message_exp: str, request: pytest.FixtureRequest
    ) -> None:
        r"""Test to map facilities to customer groups when input data is missing in db."""

        # Setup
        # ===========================================================
        _ = request.getfixturevalue(db_fixture)

        runner = CliRunner()
        args = ['ta', 'cg', 'map-facilities', '-i', '2025-11-01..2025-12-01']

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

    def test_unmapped_facilities(
        self,
        sqlite_db_with_unmapped_facility_contract: tuple[int, SessionFactory],
        facility_customer_group_link_model: FacilityContractDataFrameModel,
    ) -> None:
        r"""Test the case when a facility is not mapped to a customer group."""

        # Setup
        # ===========================================================
        facility_id_exp, session_factory = sqlite_db_with_unmapped_facility_contract

        unmapped_msg_exp = 'Facility contracts (1) could not be mapped to a customer group!'
        final_msg_exp = (
            'Successfully imported 9 new facility customer group links and '
            'updated 0 existing facility customer group links in interval '
            '2025-11-01 - 2025-12-01!'
        )
        c_facility_id = FacilityContractDataFrameModel.c_facility_id

        df_exp = facility_customer_group_link_model.df.copy()
        df_exp = df_exp.loc[~df_exp[c_facility_id].eq(facility_id_exp), :].set_index(c_facility_id)

        runner = CliRunner()
        args = ['ta', 'cg', 'map-facilities', '--interval', '2025-11-01..2025-12-01']

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        output = result.output
        print(result.output)

        assert result.exit_code == 0, 'Exit code is not 0!'
        assert unmapped_msg_exp in output, 'Expected unmapped message missing in terminal output!'
        assert str(facility_id_exp) in output, (
            f'facility_id "{facility_id_exp}" missing in terminal output!'
        )
        assert final_msg_exp in output, 'Expected final message missing in terminal output!'

        with session_factory() as session:
            df_f_cg_link = load_facility_customer_group_links(session=session)

        assert_frame_equal(df_f_cg_link.set_index(c_facility_id), df_exp)

        # Clean up - None
        # ===========================================================

    def test_missing_required_product_id_for_product_mapping_strategy(
        self,
        sqlite_db_with_required_product_id_missing_for_product_strategy: tuple[
            int, int, SessionFactory
        ],
        facility_customer_group_link_model: FacilityContractDataFrameModel,
    ) -> None:
        r"""Test the case when a facility is not mapped to a customer group.

        The `product_id` value is missing for a customer group while it has
        the product mapping strategy configured.
        """

        # Setup
        # ===========================================================
        customer_group_id_exp, facility_id_exp, session_factory = (
            sqlite_db_with_required_product_id_missing_for_product_strategy
        )

        required_product_id_msg_exp = (
            f'Required product_id param is None for customer_group_id={customer_group_id_exp}'
        )
        unmapped_msg_exp = 'Facility contracts (1) could not be mapped to a customer group!'
        final_msg_exp = (
            'Successfully imported 9 new facility customer group links and '
            'updated 0 existing facility customer group links in interval '
            '2025-11-01 - 2025-12-01!'
        )
        c_facility_id = FacilityContractDataFrameModel.c_facility_id

        df_exp = facility_customer_group_link_model.df.copy()
        df_exp = df_exp.loc[~df_exp[c_facility_id].eq(facility_id_exp), :].set_index(c_facility_id)

        runner = CliRunner()
        args = ['ta', 'cg', 'map-facilities', '--interval', '2025-11-01..2025-12-01']

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        output = result.output
        print(result.output)

        assert result.exit_code == 0, 'Exit code is not 0!'
        assert required_product_id_msg_exp in output, (
            'Expected required product_id message missing in terminal output!'
        )
        assert unmapped_msg_exp in output, 'Expected unmapped message missing in terminal output!'
        assert str(facility_id_exp) in output, (
            f'facility_id "{facility_id_exp}" missing in terminal output!'
        )
        assert final_msg_exp in output, 'Expected final message missing in terminal output!'

        with session_factory() as session:
            df_f_cg_link = load_facility_customer_group_links(session=session)

        assert_frame_equal(df_f_cg_link.set_index(c_facility_id), df_exp)

        # Clean up - None
        # ===========================================================

    def test_duplicate_facility_customer_group_links(
        self,
        sqlite_db_with_facility_mapped_to_2_customer_groups: tuple[int, SessionFactory],
    ) -> None:
        r"""Test the case when facilities are mapped to more than one customer group."""

        # Setup
        # ===========================================================
        facility_id_exp, session_factory = sqlite_db_with_facility_mapped_to_2_customer_groups
        msg_exp = 'Found duplicate facility customer group links (1)!'

        runner = CliRunner()
        args = ['ta', 'cg', 'map-facilities', '--interval', '2025-11-01..2025-12-01']

        # Exercise
        # ===========================================================
        result = runner.invoke(cli=main, args=args, catch_exceptions=False)

        # Verify
        # ===========================================================
        output = result.output
        print(output)

        assert result.exit_code == 1, 'Exit code is not 1!'
        assert msg_exp in output, 'Expected duplication message missing in terminal output!'
        assert str(facility_id_exp) in output, (
            f'facility_id "{facility_id_exp}" missing in terminal output!'
        )

        with session_factory() as session:
            df_f_cg_link = load_facility_customer_group_links(session=session)

        assert df_f_cg_link.empty

        # Clean up - None
        # ===========================================================
