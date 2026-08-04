# Smart Data Cleaning Utility

A Streamlit web app for cleaning messy CSV files. Upload a file, fix the common
problems with a few clicks, and download the result.

![Python](https://img.shields.io/badge/python-3.9+-blue)
![Streamlit](https://img.shields.io/badge/streamlit-1.50+-red)

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501`. Click **Use sample data** in the
sidebar to try it without uploading anything.

## Features

**Upload & preview** — drop in a CSV and see the first rows, each column's type,
and how many values are missing.

**Clean**

- *Quick fixes* — clean up column names (`Customer Name` → `customer_name`),
  trim stray spaces, and remove duplicate rows, one click each
- *Duplicates* — see the duplicate rows before deleting them, and optionally
  compare only certain columns
- *Missing values* — fill gaps with mean, median, mode, zero or your own value,
  or delete the incomplete rows
- *Column operations* — drop, rename, convert type (number/date/text), change
  text case

**Statistics** — row/column counts, `describe()` for numeric columns, unique and
most-common values for text columns, plus bar charts for any single column.

**Download** — a before/after comparison, the list of every change you made, and
a download button for the cleaned CSV.

**Undo and Reset** — every change can be undone one step at a time, or you can
reset back to the file you uploaded. Nothing is ever written to your original
file.

## Project structure

Two files, split by responsibility:

```
app.py            the Streamlit interface  (what the user sees)
cleaning.py       the pandas functions     (what actually changes the data)
sample_data.csv   a small messy file for trying the app
requirements.txt  dependencies
```

`cleaning.py` contains no Streamlit code, so those functions can be reused in a
notebook or a script. `app.py` contains no real data logic — it collects input,
calls a cleaning function, and displays the result.

## How it works

### Every cleaning function looks the same

```python
def remove_duplicates(df, subset=None):
    removed = count_duplicates(df, subset=subset)
    cleaned = df.drop_duplicates(subset=subset, keep="first").reset_index(drop=True)
    return cleaned, f"Removed {removed} duplicate row(s)"
```

Take a DataFrame, return **(new DataFrame, message)**. Two things follow from
this:

1. Nothing is modified in place — each function works on a copy, so the caller
   decides whether to keep the result.
2. Every function explains itself, which is where the change log in the Download
   tab comes from. No separate bookkeeping needed.

### State survives between clicks

Streamlit re-runs the entire script every time you click something, so ordinary
variables are lost. Anything that must survive lives in `st.session_state`:

```python
st.session_state.df        # the data being cleaned right now
st.session_state.original  # the file as uploaded, for Reset
st.session_state.history   # previous versions, for Undo
st.session_state.log       # the list of changes made
```

Undo is just a stack. Before each change, the current DataFrame is pushed onto
`history`; undoing pops it back off:

```python
def apply_change(result):
    new_df, message = result
    st.session_state.history.append(st.session_state.df.copy())
    st.session_state.df = new_df
    st.session_state.log.append(message)
```

### Uploads only load once

A naive `if uploaded_file:` block would reload the file on *every* click and
silently throw away your cleaning. The app compares the file name against the
one already in state and only reloads when it actually changes.

## Notes on the design

- **Bad values become missing, not errors.** Type conversion uses
  `errors="coerce"`, so one unparseable cell doesn't stop the conversion — the
  app just reports how many values failed.
- **Fill options depend on the column.** Mean and median are only offered for
  numeric columns; text columns get mode or a custom value.
- **Edge cases are handled rather than crashed on**: an all-empty column has no
  mode to fill with, a column that is entirely missing has no range to plot a
  histogram from, and a file with fewer than 6 rows has nothing to put a row
  slider on.

## Possible extensions

- Outlier detection with the IQR method
- Excel (`.xlsx`) upload alongside CSV
- Find and replace across a column
- Save and reload a sequence of cleaning steps
