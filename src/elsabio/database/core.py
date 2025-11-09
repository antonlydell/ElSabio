# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The core database functionality."""

# Standard library
import logging

# Third party
from sqlalchemy import URL as URL
from sqlalchemy import make_url as make_url
from sqlalchemy.exc import SQLAlchemyError
from streamlit_passwordless.database import Session as Session
from streamlit_passwordless.database import SessionFactory as SessionFactory
from streamlit_passwordless.database import create_default_roles as create_default_roles
from streamlit_passwordless.database import create_session_factory as create_session_factory

# Local
from elsabio.core import OperationResult

logger = logging.getLogger(__name__)


def commit(session: Session, error_msg: str = 'Error committing transaction!') -> OperationResult:
    r"""Commit a database transaction.

    session : elsabio.db.Session
        An active database session.

    error_msg : str, default 'Error committing transaction!'
        An error message to add if an exception is raised when committing the transaction.

    Returns
    -------
    result : elsabio.OperationResult
        The result of committing the transaction.
    """

    try:
        session.commit()
    except SQLAlchemyError as e:
        long_msg = f'{error_msg}\n{e!s}'
        logger.exception(long_msg)
        result = OperationResult(
            ok=False,
            short_msg=error_msg,
            long_msg=long_msg,
            code=f'{e.__module__}.{e.__class__.__name__}',
        )
        session.rollback()
    else:
        result = OperationResult(ok=True)

    return result
