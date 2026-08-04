"""Data processing functions for the Smart Data Cleaning Utility.

This file holds everything that touches the data. It contains no Streamlit
code at all, which means these functions can be tested, reused in a notebook,
or called from a plain script without a web app running.

Milestone 2 covers loading a CSV and describing what is inside it.
Cleaning functions will be added in a later milestone.
"""

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


# ---------------------------------------------------------------- describing


def get_dataset_info(df):
    """Return the headline numbers shown at the top of the page.

    A dictionary is used rather than two separate values so more facts can be
    added later without changing everywhere this function is called.
    """
    return {
        "rows": len(df),
        "columns": df.shape[1],
    }


def get_column_info(df):
    """Build a small table listing every column and its data type.

    pandas stores each column's type as a dtype such as int64 or object.
    Those names mean little to most people, so friendly_type() translates
    them before they are displayed.
    """
    return pd.DataFrame(
        {
            "Column": [str(column) for column in df.columns],
            "Data Type": [friendly_type(df[column]) for column in df.columns],
            "pandas dtype": [str(df[column].dtype) for column in df.columns],
        }
    )


def friendly_type(series):
    """Describe one column's type in plain English.

    pandas reports text columns as 'object', which is accurate but confusing,
    so each dtype family is given a readable name instead.
    """
    if pd.api.types.is_bool_dtype(series):
        return "True/False"
    if pd.api.types.is_integer_dtype(series):
        return "Whole number"
    if pd.api.types.is_float_dtype(series):
        return "Decimal number"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "Date/time"
    return "Text"
