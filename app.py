"""Smart Data Cleaning Utility - Streamlit user interface.

Milestone 2: upload a CSV file and preview what is inside it.
Milestone 3: a Dataset Information dashboard describing the loaded file.

How the project is organised:

    app.py        the Streamlit interface  (what the user sees)
    cleaning.py   the pandas functions     (what reads and describes the data)

Every number on this page is calculated in cleaning.py. This file only asks
for the values and arranges them, so there is one place to look when a figure
needs checking or changing.

Streamlit re-runs this whole script every time the user interacts with the
page, so anything that must survive a click is stored in st.session_state.

Run it with:  streamlit run app.py
"""

import streamlit as st

import cleaning

st.set_page_config(page_title="Smart Data Cleaning Utility", page_icon="🧹", layout="wide")


# ---------------------------------------------------------------- session state

# Ordinary variables are forgotten between clicks, so the loaded DataFrame is
# kept in session_state instead.
if "df" not in st.session_state:
    st.session_state.df = None       # the dataset currently loaded
    st.session_state.filename = ""   # which file it came from


# ---------------------------------------------------------------- sidebar

with st.sidebar:
    st.title("🧹 Data Cleaner")
    st.caption("Milestone 3 — upload, preview and dataset information")

    # type="csv" makes the browser's file picker offer CSV files only.
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file is not None:
        # Reload only when a *different* file arrives. Without this check the
        # file would be re-read on every single click, which is wasteful now
        # and would discard the user's work once cleaning is added.
        if uploaded_file.name != st.session_state.filename:
            df, error = cleaning.load_csv(uploaded_file)

            if error:
                # Loading failed: show why, and keep whatever was loaded before.
                st.error(error)
            else:
                st.session_state.df = df
                st.session_state.filename = uploaded_file.name

    if st.session_state.df is not None:
        st.divider()
        st.caption(f"Loaded file: **{st.session_state.filename}**")


# ---------------------------------------------------------------- main area

st.title("Smart Data Cleaning Utility")

# Nothing loaded yet - explain what to do and stop here. st.stop() prevents
# the rest of the page from running with no data to show.
if st.session_state.df is None:
    st.info("👈 Upload a CSV file to begin.")
    st.markdown(
        """
        ### What this app does

        Upload a CSV file and this page will show you:

        - how many rows and columns it has
        - how much of it is missing or duplicated
        - the type, gaps and example values for every column
        - a preview of the data itself

        Data cleaning tools will be added in the next milestone.
        """
    )
    st.stop()


df = st.session_state.df

# Every figure below comes from this one call. app.py does no counting of its
# own, so the dashboard and the details table can never disagree.
info = cleaning.get_dataset_info(df)

# ---- confirmation that the file loaded ---------------------------------
st.success(
    f"✓ Dataset loaded successfully  \n"
    f"Rows: {info['rows']:,}  \n"
    f"Columns: {info['columns']:,}"
)

st.divider()

# ---- dataset information dashboard --------------------------------------
st.subheader("📊 Dataset Information")
st.caption("A summary of the file you uploaded.")

# Nine metric cards in three rows of three. border=True draws each one as a
# card, and help= adds the "?" tooltip explaining what the number means.
row1 = st.columns(3)
row1[0].metric("Total Rows", f"{info['rows']:,}", border=True, help="Records in the file.")
row1[1].metric("Total Columns", f"{info['columns']:,}", border=True, help="Fields in each record.")
row1[2].metric(
    "Memory Usage",
    info["memory_display"],
    border=True,
    help="How much memory the data takes up once loaded.",
)

row2 = st.columns(3)
row2[0].metric(
    "Missing Values",
    f"{info['missing_values']:,}",
    border=True,
    help="Empty cells across the whole file.",
)
row2[1].metric(
    "Missing %",
    f"{info['missing_percent']}%",
    border=True,
    help="Share of all cells that are empty.",
)
row2[2].metric(
    "Duplicate Rows",
    f"{info['duplicate_rows']:,}",
    border=True,
    help="Rows identical to an earlier row in every column.",
)

row3 = st.columns(3)
row3[0].metric(
    "Numeric Columns",
    f"{info['numeric_columns']:,}",
    border=True,
    help="Columns holding numbers.",
)
row3[1].metric(
    "Text Columns",
    f"{info['text_columns']:,}",
    border=True,
    help="Columns holding words or codes.",
)
row3[2].metric(
    "Date Columns",
    f"{info['date_columns']:,}",
    border=True,
    help="Columns holding dates, including dates still stored as text.",
)

# Booleans are counted separately so the three counts above match the spec.
# Mentioning them here keeps the totals honest when a file contains any.
if info["other_columns"]:
    st.caption(
        f"Plus {info['other_columns']} True/False column(s), "
        "which are not counted as numeric, text or date."
    )

st.divider()

# ---- per-column details -------------------------------------------------
st.subheader("Column details")
st.caption("Every column in the file, with its type, gaps and an example value.")
st.dataframe(cleaning.get_column_details(df), width="stretch", hide_index=True)

st.divider()

# ---- the data itself ----------------------------------------------------
st.subheader("Data preview")

# The slider needs a real range to work, so it is only shown when the file has
# more than 5 rows. A smaller file is simply displayed in full.
max_rows = min(100, info["rows"])

if max_rows > 5:
    rows_to_show = st.slider(
        "Rows to preview",
        min_value=5,
        max_value=max_rows,
        value=min(10, max_rows),  # default preview is 10 rows
        step=1,
    )
else:
    rows_to_show = info["rows"]
    st.caption(f"This file has only {info['rows']} row(s), so all of them are shown.")

st.dataframe(df.head(rows_to_show), width="stretch")
st.caption(f"Showing {min(rows_to_show, info['rows']):,} of {info['rows']:,} rows.")
