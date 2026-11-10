"""Narrow the data down before charting. Nothing is deleted, only hidden from the chart."""

from datetime import date

import pandas as pd

from backend.schema import TIME_COLUMN


def sorted_values(series: pd.Series) -> list:
    """Unique values of a column in natural order (numbers by size, text A-Z)."""
    values = series.dropna().unique().tolist()
    try:
        return sorted(values)
    except TypeError:  # mixed types
        return sorted(values, key=str)


def apply_filters(
    data: pd.DataFrame,
    selections: dict[str, list],
    date_range: tuple[date, date] | None = None,
) -> pd.DataFrame:
    """Keep rows whose value in each column is one of the selected values.

    `selections` maps a column name to the values to keep. An empty or missing
    list means "keep everything" for that column.
    """
    mask = pd.Series(True, index=data.index)

    for col, keep in selections.items():
        if keep:
            mask &= data[col].isin(keep)

    if date_range is not None:
        start, end = date_range
        days = data[TIME_COLUMN].dt.date
        mask &= (days >= start) & (days <= end)

    return data[mask]
