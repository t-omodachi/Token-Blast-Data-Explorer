"""Load every levels CSV in a folder into one table."""

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from backend.schema import NUMBER_COLUMNS, REQUIRED_COLUMNS, TIME_COLUMN


class DataLoadError(Exception):
    """Raised when a folder can't be loaded. `problems` lists every issue found."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("\n".join(problems))


@dataclass
class LoadResult:
    data: pd.DataFrame
    files: list[tuple[str, int]]  # (file name, number of rows)
    warnings: list[str] = field(default_factory=list)


def folder_signature(folder: str) -> tuple:
    """A value that changes whenever a CSV in the folder is added, removed or edited.

    The frontend uses it so cached data refreshes when files change.
    """
    path = Path(folder)
    if not path.is_dir():
        return ()
    return tuple(
        (p.name, p.stat().st_mtime, p.stat().st_size) for p in sorted(path.glob("*.csv"))
    )


def load_folder(folder: str) -> LoadResult:
    """Read all .csv files in `folder` (not subfolders) and combine them.

    Raises DataLoadError if the folder is missing, has no CSVs, or any CSV is
    not a valid levels file.
    """
    path = Path(folder)
    if not path.is_dir():
        raise DataLoadError([f"Folder not found: {path}"])

    csv_paths = sorted(path.glob("*.csv"))
    if not csv_paths:
        raise DataLoadError([f"No .csv files found in {path}"])

    warnings = []
    other_files = [p.name for p in path.iterdir() if p.is_file() and p.suffix.lower() != ".csv"]
    if other_files:
        warnings.append(f"Ignored {len(other_files)} non-CSV file(s): {', '.join(other_files[:5])}")

    problems: list[str] = []
    tables: list[pd.DataFrame] = []
    files: list[tuple[str, int]] = []

    for csv_path in csv_paths:
        table, file_problems = _read_levels_file(csv_path)
        if file_problems:
            problems.extend(f"{csv_path.name}: {p}" for p in file_problems)
        else:
            tables.append(table)
            files.append((csv_path.name, len(table)))

    if problems:
        raise DataLoadError(problems)

    data = pd.concat(tables, ignore_index=True)
    return LoadResult(data=data, files=files, warnings=warnings)


def _read_levels_file(csv_path: Path) -> tuple[pd.DataFrame, list[str]]:
    """Read one file. Returns (table, problems). `problems` is empty if the file is valid."""
    try:
        # Read everything as text first so we can report bad values clearly.
        # utf-8-sig handles files re-saved by Excel.
        raw = pd.read_csv(csv_path, dtype=str, encoding="utf-8-sig")
    except Exception as exc:  # unreadable, empty, wrong encoding, etc.
        return pd.DataFrame(), [f"could not be read ({exc})"]

    raw.columns = raw.columns.str.strip()
    missing = [c for c in REQUIRED_COLUMNS if c not in raw.columns]
    if missing:
        hint = " This looks like an events file, not a levels file." if "event" in raw.columns else ""
        return pd.DataFrame(), [f"not a levels file. Missing columns: {', '.join(missing)}.{hint}"]

    problems = []
    table = raw.copy()

    for col in NUMBER_COLUMNS:
        table[col] = pd.to_numeric(raw[col], errors="coerce")
        problems += _bad_values(raw[col], table[col], col)

    times = pd.to_datetime(raw[TIME_COLUMN], errors="coerce", utc=True, format="mixed")
    problems += _bad_values(raw[TIME_COLUMN], times, TIME_COLUMN)
    table[TIME_COLUMN] = times.dt.tz_localize(None)  # keep UTC clock time, drop the tz tag

    return table, problems


def _bad_values(original: pd.Series, converted: pd.Series, col: str) -> list[str]:
    """Report cells that had a value but couldn't be converted."""
    had_value = original.notna() & (original.str.strip() != "")
    bad_rows = original.index[had_value & converted.isna()]
    if len(bad_rows) == 0:
        return []
    # +2: one for the header line, one because spreadsheets count from 1.
    examples = ", ".join(f"row {i + 2} ('{original[i]}')" for i in bad_rows[:3])
    more = f" and {len(bad_rows) - 3} more" if len(bad_rows) > 3 else ""
    return [f"column '{col}' has values that aren't valid: {examples}{more}"]
