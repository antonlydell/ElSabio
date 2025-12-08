# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The core data models of ElSabio."""

# Standard library
from collections.abc import Mapping
from typing import Any, ClassVar

# Third party
import pandas as pd
from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, ValidationError
from streamlit_passwordless import User as User

# Local
from elsabio.exceptions import ElSabioError

type StrMapping = Mapping[str, str]
type ColumnList = list[str]


class BaseModel(PydanticBaseModel):
    r"""The BaseModel that all models inherit from."""

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True, frozen=True)

    def __init__(self, **kwargs: Any) -> None:
        try:
            super().__init__(**kwargs)
        except ValidationError as e:
            raise ElSabioError(str(e)) from None


class BaseDataFrameModel(BaseModel):
    r"""The base model that all DataFrame models will inherit from.

    A DataFrame model represents a database table, a query or some other table like structure.
    using a :class:`pandas.DataFrame`. The DataFrame is accessible from the `df` attribute.
    Each column name of the DataFrame should be implemented as a class variable starting with
    the prefix "c_", e.g. `c_name: ClassVar[str] = 'name'` for a name column. The class variables
    listed below should be defined for each subclass of this model.

    Class Variables
    ---------------
    dtypes : ClassVar[dict[str, str]]
        The mapping of column names to their datatypes of the DataFrame.

    index_cols : ClassVar[list[str]]
        The index columns of the DataFrame.

    parse_dates : ClassVar[list[str]]
        The columns of the DataFrame that should be parsed into datetime columns.

    Parameters
    ----------
    df : pandas.DataFrame
        The contents of the model as a DataFrame.
    """

    dtypes: ClassVar[StrMapping] = {}
    index_cols: ClassVar[ColumnList] = []
    parse_dates: ClassVar[ColumnList] = []

    df: pd.DataFrame

    @property
    def shape(self) -> tuple[int, int]:
        r"""The shape (rows, cols) of the DataFrame."""

        return self.df.shape

    @property
    def index(self) -> pd.Index:
        r"""The index column(s) of the DataFrame."""

        return self.df.index

    @property
    def row_count(self) -> int:
        r"""The number of rows of the DataFrame."""

        return self.df.shape[0]

    @property
    def empty(self) -> bool:
        r"""Check if the DataFrame is empty or not."""

        return self.row_count == 0

    @property
    def col_dtypes(self) -> pd.Series:
        r"""The dtypes of the columns of the DataFrame."""

        return self.df.dtypes
