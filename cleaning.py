"""Data cleaning functions.

Every function here follows the same pattern:

    take a DataFrame  ->  return (new DataFrame, message describing what changed)

Two rules make the whole app easy to reason about:

1. Nothing is changed in place. Each function works on a copy, so the caller
   decides whether to keep the result. That is what makes "Undo" possible.
2. No Streamlit code lives in this file. These are plain pandas functions, so
   they can be tested, reused, or called from a notebook on their own.
"""

import pandas as pd


# ---------------------------------------------------------------- loading


def load_csv(uploaded_file):
    """Read an uploaded CSV into a DataFrame."""
    return pd.read_csv(uploaded_file)


# ---------------------------------------------------------------- duplicates


def count_duplicates(df, subset=None):
    """How many rows are duplicates of an earlier row."""
    return int(df.duplicated(subset=subset).sum())


def remove_duplicates(df, subset=None):
    """Keep the first copy of each row and drop the rest.

    `subset` limits the comparison to certain columns - useful when two rows
    describe the same customer but disagree on a timestamp.
    """
    removed = count_duplicates(df, subset=subset)
    cleaned = df.drop_duplicates(subset=subset, keep="first").reset_index(drop=True)

    where = f" (comparing {', '.join(subset)})" if subset else ""
    return cleaned, f"Removed {removed} duplicate row(s){where}"


# ---------------------------------------------------------------- missing values


def missing_summary(df):
    """A small table of how many values each column is missing."""
    missing = df.isna().sum()
    summary = pd.DataFrame(
        {
            "Column": missing.index,
            "Missing": missing.values,
            "Missing %": (missing.values / len(df) * 100).round(1) if len(df) else 0,
            "Type": [str(df[column].dtype) for column in df.columns],
        }
    )
    return summary.sort_values("Missing", ascending=False).reset_index(drop=True)


def drop_rows_with_missing(df, columns=None):
    """Delete rows that have a missing value in the given columns."""
    before = len(df)
    cleaned = df.dropna(subset=columns).reset_index(drop=True)
    removed = before - len(cleaned)

    where = f" in {', '.join(columns)}" if columns else ""
    return cleaned, f"Dropped {removed} row(s) with missing values{where}"


def fill_missing(df, column, method, custom_value=None):
    """Fill the gaps in one column.

    method is one of: "mean", "median", "mode", "zero", "custom".
    Mean and median only make sense for numbers, so the caller should offer
    them for numeric columns only.
    """
    cleaned = df.copy()
    missing_before = int(cleaned[column].isna().sum())

    if missing_before == 0:
        return cleaned, f"'{column}' had no missing values"

    if method == "mean":
        value = cleaned[column].mean()
    elif method == "median":
        value = cleaned[column].median()
    elif method == "mode":
        modes = cleaned[column].mode()
        if modes.empty:
            return cleaned, f"'{column}' is entirely empty, so there is no mode to fill with"
        value = modes.iloc[0]
    elif method == "zero":
        value = 0
    else:  # "custom"
        value = custom_value

    cleaned[column] = cleaned[column].fillna(value)
    return cleaned, f"Filled {missing_before} missing value(s) in '{column}' with {method} ({value})"


# ---------------------------------------------------------------- column operations


def drop_columns(df, columns):
    """Remove columns you do not need."""
    cleaned = df.drop(columns=columns)
    return cleaned, f"Dropped column(s): {', '.join(columns)}"


def rename_column(df, old_name, new_name):
    """Give one column a different name."""
    cleaned = df.rename(columns={old_name: new_name})
    return cleaned, f"Renamed '{old_name}' to '{new_name}'"


def clean_column_names(df):
    """Turn messy headers into simple lowercase names.

    "  Customer Name " becomes "customer_name", which is far easier to type
    and works as a Python attribute.
    """
    cleaned = df.copy()
    old_names = list(cleaned.columns)

    new_names = (
        pd.Index(old_names)
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[^\w\s]", "", regex=True)   # drop punctuation
        .str.replace(r"\s+", "_", regex=True)      # spaces become underscores
    )
    cleaned.columns = new_names

    changed = sum(1 for old, new in zip(old_names, new_names) if old != new)
    return cleaned, f"Cleaned {changed} column name(s)"


def strip_whitespace(df):
    """Trim leading/trailing spaces from every text column.

    " Austin " and "Austin" look identical on screen but count as two different
    values, so this quietly fixes a lot of duplicate and grouping problems.
    """
    cleaned = df.copy()
    text_columns = cleaned.select_dtypes(include="object").columns
    for column in text_columns:
        cleaned[column] = cleaned[column].str.strip()

    return cleaned, f"Trimmed whitespace in {len(text_columns)} text column(s)"


def change_case(df, column, case):
    """Make a text column all lower, upper or Title Case."""
    cleaned = df.copy()

    if case == "lower":
        cleaned[column] = cleaned[column].str.lower()
    elif case == "UPPER":
        cleaned[column] = cleaned[column].str.upper()
    else:  # "Title"
        cleaned[column] = cleaned[column].str.title()

    return cleaned, f"Changed '{column}' to {case} case"


def convert_type(df, column, new_type):
    """Convert a column to number, text or date.

    Values that cannot be converted become missing (NaN) rather than raising an
    error, so one bad cell does not stop the whole conversion.
    """
    cleaned = df.copy()

    if new_type == "number":
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    elif new_type == "date":
        cleaned[column] = pd.to_datetime(cleaned[column], errors="coerce")
    else:  # "text"
        cleaned[column] = cleaned[column].astype(str)

    failed = int(cleaned[column].isna().sum() - df[column].isna().sum())
    note = f", {failed} value(s) could not be converted" if failed > 0 else ""
    return cleaned, f"Converted '{column}' to {new_type}{note}"


# ---------------------------------------------------------------- statistics


def overview(df):
    """The handful of numbers shown at the top of the app."""
    return {
        "rows": len(df),
        "columns": df.shape[1],
        "missing": int(df.isna().sum().sum()),
        "duplicates": count_duplicates(df),
        "memory_kb": round(float(df.memory_usage(deep=True).sum()) / 1024, 1),
    }


def numeric_summary(df):
    """describe() for the numeric columns, or None when there are none."""
    numeric = df.select_dtypes(include="number")
    if numeric.empty:
        return None
    return numeric.describe().T.round(2)


def text_summary(df):
    """Count and most common value for each text column."""
    text = df.select_dtypes(include="object")
    if text.empty:
        return None

    rows = []
    for column in text.columns:
        values = text[column].dropna()
        rows.append(
            {
                "Column": column,
                "Unique values": values.nunique(),
                "Most common": values.mode().iloc[0] if not values.mode().empty else "-",
                "Count": int(values.value_counts().iloc[0]) if not values.empty else 0,
            }
        )
    return pd.DataFrame(rows)


def to_csv_bytes(df):
    """Turn the DataFrame into bytes for Streamlit's download button."""
    return df.to_csv(index=False).encode("utf-8")
