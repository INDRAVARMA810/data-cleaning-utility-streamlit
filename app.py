"""Smart Data Cleaning Utility - a Streamlit app for cleaning CSV files.

Upload a messy CSV, fix it with a few clicks, and download the result.

How the app is organised:

    cleaning.py  -  the pandas logic (no Streamlit code)
    app.py       -  the user interface (no pandas logic beyond display)

Streamlit re-runs this whole script top to bottom every time you click
something, so anything that must survive a click is kept in st.session_state.

Run it with:  streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import streamlit as st

import cleaning

st.set_page_config(page_title="Smart Data Cleaning Utility", page_icon="🧹", layout="wide")

# Built from this file's location, so the sample loads no matter which folder
# you launched Streamlit from.
SAMPLE_FILE = Path(__file__).parent / "sample_data.csv"


# ---------------------------------------------------------------- session state

# Streamlit forgets ordinary variables between clicks, so the working
# DataFrame lives in session_state instead.
if "df" not in st.session_state:
    st.session_state.df = None        # the data we are cleaning right now
    st.session_state.original = None  # the file as uploaded, for "Reset"
    st.session_state.history = []     # previous versions, for "Undo"
    st.session_state.log = []         # a readable list of what we did
    st.session_state.filename = ""


def load_data(df, filename):
    """Start a fresh cleaning session with a newly loaded file."""
    st.session_state.df = df
    st.session_state.original = df.copy()
    st.session_state.history = []
    st.session_state.log = []
    st.session_state.filename = filename


def apply_change(result):
    """Accept the (DataFrame, message) a cleaning function returned.

    The current version is pushed onto the history stack first, which is all
    "Undo" needs to work.
    """
    new_df, message = result
    st.session_state.history.append(st.session_state.df.copy())
    st.session_state.df = new_df
    st.session_state.log.append(message)
    st.toast(message, icon="✅")


def undo():
    """Step back to the version before the last change."""
    if st.session_state.history:
        st.session_state.df = st.session_state.history.pop()
        st.session_state.log.pop()


# ---------------------------------------------------------------- sidebar

with st.sidebar:
    st.title("🧹 Data Cleaner")
    st.caption("Upload a CSV, clean it, download the result.")

    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file is not None:
        # Only reload when a *different* file arrives, otherwise every click
        # would wipe out the cleaning done so far.
        if uploaded_file.name != st.session_state.filename:
            try:
                load_data(cleaning.load_csv(uploaded_file), uploaded_file.name)
                st.success(f"Loaded {uploaded_file.name}")
            except Exception as error:
                st.error(f"Could not read that file: {error}")

    if st.button("Use sample data", width="stretch"):
        load_data(pd.read_csv(SAMPLE_FILE), SAMPLE_FILE.name)
        st.rerun()

    if st.session_state.df is not None:
        st.divider()
        stats = cleaning.overview(st.session_state.df)

        left, right = st.columns(2)
        left.metric("Rows", f"{stats['rows']:,}")
        right.metric("Columns", stats["columns"])
        left.metric("Missing", f"{stats['missing']:,}")
        right.metric("Duplicates", f"{stats['duplicates']:,}")

        st.divider()
        undo_column, reset_column = st.columns(2)
        if undo_column.button("↩️ Undo", width="stretch", disabled=not st.session_state.history):
            undo()
            st.rerun()
        if reset_column.button("🔄 Reset", width="stretch"):
            load_data(st.session_state.original, st.session_state.filename)
            st.rerun()


# ---------------------------------------------------------------- main area

st.title("Smart Data Cleaning Utility")

if st.session_state.df is None:
    st.info("👈 Upload a CSV file to get started, or click **Use sample data** to try the app.")
    st.markdown(
        """
        ### What this app does

        | Tab | Purpose |
        |---|---|
        | **Preview** | See your data and what is wrong with it |
        | **Clean** | Fix duplicates, missing values and columns |
        | **Statistics** | Summary numbers and simple charts |
        | **Download** | Save the cleaned CSV |

        Every change is listed in the Download tab, and **Undo** reverses the
        last one, so it is safe to experiment.
        """
    )
    st.stop()  # nothing below makes sense without data

df = st.session_state.df
preview_tab, clean_tab, stats_tab, download_tab = st.tabs(
    ["📄 Preview", "🧹 Clean", "📊 Statistics", "💾 Download"]
)


# ---------------------------------------------------------------- preview tab

with preview_tab:
    st.subheader("Your data")

    # A slider needs a real range, so only offer one when there is something
    # to slide through.
    if len(df) > 5:
        row_count = st.slider("Rows to show", 5, min(100, len(df)), min(10, len(df)))
    else:
        row_count = len(df)

    st.dataframe(df.head(row_count), width="stretch")

    st.subheader("Columns")
    st.caption("A quick health check: what type each column is and how much is missing.")
    st.dataframe(cleaning.missing_summary(df), width="stretch", hide_index=True)


# ---------------------------------------------------------------- clean tab

with clean_tab:
    st.subheader("Quick fixes")
    st.caption("The three most common problems, one click each.")

    quick1, quick2, quick3 = st.columns(3)

    with quick1:
        if st.button("✨ Clean column names", width="stretch"):
            apply_change(cleaning.clean_column_names(df))
            st.rerun()
        st.caption("`Customer Name` → `customer_name`")

    with quick2:
        if st.button("✂️ Trim spaces", width="stretch"):
            apply_change(cleaning.strip_whitespace(df))
            st.rerun()
        st.caption("`\" Austin \"` → `\"Austin\"`")

    with quick3:
        duplicate_count = cleaning.count_duplicates(df)
        if st.button(
            f"🗑️ Remove {duplicate_count} duplicate(s)",
            width="stretch",
            disabled=duplicate_count == 0,
        ):
            apply_change(cleaning.remove_duplicates(df))
            st.rerun()
        st.caption("Identical rows, keeping the first")

    st.divider()

    # ---- duplicates -----------------------------------------------------
    with st.expander("🗑️ Duplicates"):
        st.write(
            "By default a duplicate is a row identical in **every** column. "
            "Pick specific columns if two rows describe the same thing but "
            "differ in a detail like a timestamp."
        )

        subset = st.multiselect("Compare these columns only (optional)", list(df.columns))
        found = cleaning.count_duplicates(df, subset=subset or None)

        if found:
            st.warning(f"Found {found} duplicate row(s).")
            st.dataframe(
                df[df.duplicated(subset=subset or None, keep=False)].head(20),
                width="stretch",
            )
            if st.button("Remove these duplicates"):
                apply_change(cleaning.remove_duplicates(df, subset=subset or None))
                st.rerun()
        else:
            st.success("No duplicates found.")

    # ---- missing values -------------------------------------------------
    with st.expander("🕳️ Missing values"):
        summary = cleaning.missing_summary(df)
        columns_with_gaps = summary[summary["Missing"] > 0]["Column"].tolist()

        if not columns_with_gaps:
            st.success("No missing values.")
        else:
            st.dataframe(
                summary[summary["Missing"] > 0], width="stretch", hide_index=True
            )

            st.markdown("**Fill the gaps in one column**")
            fill_column = st.selectbox("Column", columns_with_gaps)
            is_numeric = pd.api.types.is_numeric_dtype(df[fill_column])

            # Mean and median only make sense for numbers.
            methods = ["mean", "median", "zero", "mode", "custom"] if is_numeric else ["mode", "custom"]
            method = st.radio("Fill with", methods, horizontal=True)

            custom_value = None
            if method == "custom":
                custom_value = st.text_input("Value to use", "unknown")
                if is_numeric:
                    try:
                        custom_value = float(custom_value)
                    except ValueError:
                        st.warning("That is not a number - it will be stored as text.")

            if st.button("Fill missing values"):
                apply_change(cleaning.fill_missing(df, fill_column, method, custom_value))
                st.rerun()

            st.divider()
            st.markdown("**Or delete the incomplete rows**")
            drop_columns_choice = st.multiselect(
                "Only if missing in these columns (leave empty for any column)",
                list(df.columns),
            )
            if st.button("Drop rows with missing values"):
                apply_change(cleaning.drop_rows_with_missing(df, drop_columns_choice or None))
                st.rerun()

    # ---- column operations ----------------------------------------------
    with st.expander("📐 Column operations"):
        drop_column, rename_column = st.columns(2)

        with drop_column:
            st.markdown("**Drop columns**")
            to_drop = st.multiselect("Columns to remove", list(df.columns))
            if st.button("Drop selected", disabled=not to_drop):
                apply_change(cleaning.drop_columns(df, to_drop))
                st.rerun()

        with rename_column:
            st.markdown("**Rename a column**")
            old_name = st.selectbox("Column", list(df.columns), key="rename_source")
            new_name = st.text_input("New name", old_name)
            if st.button("Rename", disabled=new_name == old_name or not new_name.strip()):
                apply_change(cleaning.rename_column(df, old_name, new_name.strip()))
                st.rerun()

        st.divider()
        type_column, case_column = st.columns(2)

        with type_column:
            st.markdown("**Change a column's type**")
            st.caption("Values that will not convert become missing.")
            convert_target = st.selectbox("Column", list(df.columns), key="convert_source")
            new_type = st.radio("Convert to", ["number", "date", "text"], horizontal=True)
            if st.button("Convert"):
                apply_change(cleaning.convert_type(df, convert_target, new_type))
                st.rerun()

        with case_column:
            st.markdown("**Change text case**")
            text_columns = list(df.select_dtypes(include="object").columns)
            if not text_columns:
                st.caption("No text columns in this file.")
            else:
                case_target = st.selectbox("Column", text_columns, key="case_source")
                case = st.radio("Case", ["lower", "UPPER", "Title"], horizontal=True)
                if st.button("Apply case"):
                    apply_change(cleaning.change_case(df, case_target, case))
                    st.rerun()


# ---------------------------------------------------------------- statistics tab

with stats_tab:
    stats = cleaning.overview(df)

    a, b, c, d = st.columns(4)
    a.metric("Rows", f"{stats['rows']:,}")
    b.metric("Columns", stats["columns"])
    c.metric("Missing values", f"{stats['missing']:,}")
    d.metric("Memory", f"{stats['memory_kb']} KB")

    st.divider()
    st.subheader("Numeric columns")
    numeric_stats = cleaning.numeric_summary(df)
    if numeric_stats is None:
        st.info("No numeric columns. Use **Clean → Column operations** to convert one.")
    else:
        st.dataframe(numeric_stats, width="stretch")

    st.subheader("Text columns")
    text_stats = cleaning.text_summary(df)
    if text_stats is None:
        st.info("No text columns.")
    else:
        st.dataframe(text_stats, width="stretch", hide_index=True)

    st.divider()
    st.subheader("Explore one column")

    chosen = st.selectbox("Column", list(df.columns), key="explore")
    left, right = st.columns(2)

    with left:
        st.markdown("**Most common values**")
        counts = df[chosen].value_counts().head(10)
        if counts.empty:
            st.info("This column is empty.")
        else:
            st.bar_chart(counts)

    with right:
        numeric_values = df[chosen].dropna()

        if pd.api.types.is_numeric_dtype(df[chosen]) and not numeric_values.empty:
            st.markdown("**Distribution**")
            # value_counts(bins=...) buckets the numbers into a histogram.
            # The empty check above matters: a column that is entirely missing
            # has no range to build buckets from.
            histogram = numeric_values.value_counts(bins=10, sort=False)
            histogram.index = [f"{interval.left:,.0f} - {interval.right:,.0f}" for interval in histogram.index]
            st.bar_chart(histogram)
        else:
            st.markdown("**Details**")
            st.write(
                {
                    "Unique values": int(df[chosen].nunique()),
                    "Missing": int(df[chosen].isna().sum()),
                    "Type": str(df[chosen].dtype),
                }
            )


# ---------------------------------------------------------------- download tab

with download_tab:
    st.subheader("Cleaned data")
    st.dataframe(df.head(20), width="stretch")

    before = cleaning.overview(st.session_state.original)
    after = cleaning.overview(df)

    st.subheader("Before and after")
    comparison = pd.DataFrame(
        {
            "Before": [before["rows"], before["columns"], before["missing"], before["duplicates"]],
            "After": [after["rows"], after["columns"], after["missing"], after["duplicates"]],
        },
        index=["Rows", "Columns", "Missing values", "Duplicate rows"],
    )
    st.dataframe(comparison, width="stretch")

    st.subheader("What was changed")
    if not st.session_state.log:
        st.info("No changes yet.")
    else:
        for number, message in enumerate(st.session_state.log, start=1):
            st.write(f"{number}. {message}")

    st.divider()
    default_name = f"cleaned_{st.session_state.filename or 'data.csv'}"
    output_name = st.text_input("File name", default_name)

    st.download_button(
        "⬇️ Download cleaned CSV",
        data=cleaning.to_csv_bytes(df),
        file_name=output_name,
        mime="text/csv",
        type="primary",
    )
