"""Data processing functions for the Smart Data Cleaning Utility.

This file holds everything that touches the data. It contains no Streamlit
code at all, which means these functions can be tested, reused in a notebook,
or called from a plain script without a web app running.

Milestones so far:
    2 - loading a CSV file
    3 - describing what is inside it (the Dataset Information dashboard)

Cleaning functions will be added in a later milestone.
"""

import warnings

import pandas as pd


# ---------------------------------------------------------------- loading


def load_csv(uploaded_file):
    """Read an uploaded CSV file into a DataFrame.

    Reading a file the user chose can fail in many ways, so instead of
    crashing this function always returns the same pair:

        (DataFrame, None)             when the file was read successfully
        (None, "explanation")         when something went wrong

    The caller checks which one it got and shows the message. Returning the
    error instead of raising it keeps all the "what do we tell the user"
    decisions in app.py, where the user interface lives.
    """
    if uploaded_file is None:
        return None, "No file was provided."

    # Streamlit's uploader is already restricted to .csv, but a filename can
    # still arrive from somewhere else, so check it here too.
    if not uploaded_file.name.lower().endswith(".csv"):
        return None, (
            f"'{uploaded_file.name}' is not a CSV file. "
            "Please upload a file ending in .csv"
        )

    try:
        # A file object remembers how far it has been read. Rewinding to the
        # start means a second read attempt sees the whole file, not nothing.
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file)

    except pd.errors.EmptyDataError:
        # The file has no content at all - not even a header row.
        return None, "This file is empty. Please upload a CSV that contains data."

    except pd.errors.ParserError as error:
        # The file has content, but the rows do not line up into a table.
        # Usually a stray comma or an unclosed quotation mark.
        return None, (
            "This file could not be read as a CSV. Check for stray commas or "
            f"unclosed quotation marks.\n\nDetails: {error}"
        )

    except UnicodeDecodeError:
        # The bytes are not valid UTF-8, which usually means the file is not
        # really text - an Excel file renamed to .csv, for example.
        return None, (
            "This file is not readable as text. If it was created in Excel, "
            "use 'Save As' and choose 'CSV UTF-8'."
        )

    except Exception as error:
        # A catch-all so an unexpected problem still produces a friendly
        # message rather than a red traceback in the middle of the page.
        return None, f"Something went wrong while reading the file: {error}"

    # Reading succeeded, but the result may still be unusable.
    if df.columns.empty:
        return None, "No columns were found in this file."

    if df.empty:
        return None, "This file has column headings but no rows of data."

    return df, None


# ---------------------------------------------------------------- classifying columns


def looks_like_dates(series, sample_size=200, threshold=0.9):
    """Decide whether a text column is really holding dates.

    A CSV has no type information, so a column of dates arrives as plain text.
    This function takes a sample of the values and asks pandas to parse them:
    if almost all of them turn into real dates, the column is treated as a date
    column.

    Columns made of plain numbers are rejected first. pandas will happily read
    "20240115" as a date, which would wrongly turn ID numbers, years and
    quantities into date columns.

    Only a sample is checked because this runs for every text column, and a few
    hundred values are enough to tell dates from names.
    """
    values = series.dropna()
    if values.empty:
        return False

    values = values.head(sample_size).astype(str).str.strip()

    # More than half plain numbers (digits and dots only) means this is a
    # number column, not a date column.
    if float(values.str.fullmatch(r"[\d.]+").mean()) > 0.5:
        return False

    try:
        # errors="coerce" turns anything unparseable into "not a date" instead
        # of raising, so the share below measures how many really are dates.
        # The warnings filter hides pandas' notes about guessing formats.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parsed = pd.to_datetime(values, errors="coerce", format="mixed")
    except (ValueError, TypeError):
        return False

    return float(parsed.notna().mean()) >= threshold


def column_kind(series):
    """Sort one column into a single category: numeric, date, boolean or text.

    This is the one place where "what kind of column is this?" is decided.
    Both the dashboard counts and the details table call it, so a column can
    never be counted as numeric in one place and text in another.
    """
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"
    if looks_like_dates(series):
        return "date"
    return "text"


def friendly_type(series):
    """Describe a column's type in plain English, for display in the table.

    pandas reports text columns as 'object' and whole numbers as 'int64',
    which is accurate but not friendly. This builds on column_kind() and adds
    a little more detail where it is useful.
    """
    kind = column_kind(series)

    if kind == "numeric":
        return "Whole number" if pd.api.types.is_integer_dtype(series) else "Decimal number"
    if kind == "date":
        # Distinguish a real date column from text that happens to hold dates,
        # because only the first can be sorted or subtracted correctly.
        if pd.api.types.is_datetime64_any_dtype(series):
            return "Date/time"
        return "Date (stored as text)"
    if kind == "boolean":
        return "True/False"
    return "Text"


def count_column_types(df):
    """Count how many columns fall into each category.

    Returns a dictionary rather than four separate values, so the dashboard can
    read the counts by name and nothing depends on their order.
    """
    counts = {"numeric": 0, "text": 0, "date": 0, "other": 0}

    for column in df.columns:
        kind = column_kind(df[column])
        # Booleans are counted under "other" so the three headline counts stay
        # exactly as specified and still add up to the total column count.
        counts[kind if kind in counts else "other"] += 1

    return counts


# ---------------------------------------------------------------- describing the dataset


def format_memory(num_bytes):
    """Turn a raw byte count into something readable, in KB or MB.

    Anything under a megabyte reads better in kilobytes, so the unit is chosen
    based on the size rather than being fixed.
    """
    kilobytes = num_bytes / 1024

    # Rounding happens before the comparison, otherwise a size just under the
    # limit would be displayed as "1024.0 KB" instead of "1.00 MB".
    if round(kilobytes, 1) < 1024:
        return f"{kilobytes:.1f} KB"
    return f"{kilobytes / 1024:.2f} MB"


def get_dataset_info(df):
    """Gather every number shown on the Dataset Information dashboard.

    One dictionary is returned instead of many separate values, so app.py can
    pull out what it needs by name and new facts can be added later without
    changing how the function is called.

    The guards against division by zero matter: a DataFrame with no rows or no
    columns would otherwise crash on the percentage calculation.
    """
    total_rows = len(df)
    total_columns = df.shape[1]
    total_cells = total_rows * total_columns

    missing_values = int(df.isna().sum().sum())
    type_counts = count_column_types(df)

    # deep=True measures the actual text stored in the columns. Without it,
    # pandas only reports the size of the pointers to that text, which badly
    # under-reports memory for text-heavy files.
    memory_bytes = int(df.memory_usage(deep=True).sum())

    return {
        "rows": total_rows,
        "columns": total_columns,
        "missing_values": missing_values,
        "missing_percent": round(missing_values / total_cells * 100, 1) if total_cells else 0.0,
        "duplicate_rows": int(df.duplicated().sum()) if total_rows else 0,
        "memory_display": format_memory(memory_bytes),
        "numeric_columns": type_counts["numeric"],
        "text_columns": type_counts["text"],
        "date_columns": type_counts["date"],
        "other_columns": type_counts["other"],
    }


def first_example(series):
    """Pick one real value from a column to show as an example.

    Missing values are skipped, because "nan" tells the user nothing. A column
    with no values at all shows a dash. Long values are shortened so one wide
    cell cannot stretch the whole table.
    """
    values = series.dropna()
    if values.empty:
        return "—"

    text = str(values.iloc[0])
    return text if len(text) <= 40 else text[:37] + "..."


def get_column_details(df):
    """Build the per-column table shown under the dashboard.

    One row per column, with everything needed to spot a problem at a glance:
    the type, how much is missing, how many distinct values there are, and an
    example of what the data actually looks like.
    """
    # A DataFrame with no columns still needs the right headings, otherwise
    # Streamlit has nothing to draw a table from.
    headings = ["Column", "Data Type", "Missing", "Missing %", "Unique", "Example"]
    if df.columns.empty:
        return pd.DataFrame(columns=headings)

    total_rows = len(df)
    rows = []

    for column in df.columns:
        series = df[column]
        missing = int(series.isna().sum())
        present = series.dropna()

        rows.append(
            {
                "Column": str(column),
                "Data Type": friendly_type(series),
                "Missing": missing,
                # Guarded the same way as the dashboard: a file with no rows
                # must not divide by zero.
                "Missing %": round(missing / total_rows * 100, 1) if total_rows else 0.0,
                "Unique": int(present.nunique()),
                "Example": first_example(series),
            }
        )

    return pd.DataFrame(rows, columns=headings)
