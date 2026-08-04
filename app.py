"""Smart Data Cleaning Utility - Streamlit user interface.

Milestone 2: upload a CSV file and preview what is inside it.

How the project is organised:

    app.py        the Streamlit interface  (what the user sees)
    cleaning.py   the pandas functions     (what reads and describes the data)

Keeping the two apart means the data logic can be tested on its own, and this
file stays short enough to read top to bottom.

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
    st.caption("Milestone 2 — upload and preview")

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
        - the name and data type of every column
        - a preview of the data itself

        Data cleaning tools will be added in the next milestone.
        """
    )
    st.stop()


df = st.session_state.df
info = cleaning.get_dataset_info(df)

# ---- confirmation that the file loaded ---------------------------------
st.success(
    f"✓ Dataset loaded successfully  \n"
    f"Rows: {info['rows']:,}  \n"
    f"Columns: {info['columns']:,}"
)

# ---- headline numbers ---------------------------------------------------
left, right = st.columns(2)
left.metric("Rows", f"{info['rows']:,}")
right.metric("Columns", f"{info['columns']:,}")

st.divider()

# ---- column names and data types ---------------------------------------
st.subheader("Columns and data types")
st.caption("Every column in the file, and the kind of value pandas found in it.")
st.dataframe(cleaning.get_column_info(df), width="stretch", hide_index=True)

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
