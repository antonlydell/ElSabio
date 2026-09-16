# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Message components."""

# Third party
import streamlit as st

# Local
from elsabio.app.components.icons import ICON_ERROR
from elsabio.core import OperationResult


def operation_error(result: OperationResult) -> None:
    r"""Render the error message of an operation that failed.

    Only the short message of `result` is displayed, since the long message
    may contain sensitive details and belongs in the log.

    Parameters
    ----------
    result : elsabio.core.OperationResult
        The result of the operation that failed.
    """

    st.error(result.short_msg, icon=ICON_ERROR)
