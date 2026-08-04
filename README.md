# Smart Data Cleaning Utility

A Streamlit web app for cleaning messy CSV files.

This project is being built in milestones. **Milestone 3 is complete**: you can
upload a CSV file, see a dashboard describing it, and preview the data.
Cleaning tools come next.

![Python](https://img.shields.io/badge/python-3.9+-blue)
![Streamlit](https://img.shields.io/badge/streamlit-1.50+-red)

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501`. There is a `sample_data.csv` file in
this folder you can upload to try it out.

## Screenshots

**Before uploading**

![Empty state — the app waiting for a file](screenshots/01-empty-state.png)

<!-- Screenshot placeholder: run the app, take a screenshot of the starting
     page, and save it as screenshots/01-empty-state.png -->

**Dataset Information dashboard**

![Nine metric cards summarising the uploaded file](screenshots/02-dataset-information.png)

<!-- Screenshot placeholder: upload sample_data.csv, take a screenshot of the
     metric cards, and save it as screenshots/02-dataset-information.png -->

**Column details and data preview**

![Per-column table and the data preview with its row slider](screenshots/03-preview.png)

<!-- Screenshot placeholder: scroll down to the column details table and data
     preview, and save the screenshot as screenshots/03-preview.png -->

## Features

### CSV Upload

- A file uploader that accepts `.csv` files only
- The file is read with pandas and checked before anything is displayed
- Problems are reported in plain language instead of crashing the page:

  | Problem | What you see |
  |---|---|
  | Empty file | "This file is empty. Please upload a CSV that contains data." |
  | Only column headings, no rows | "This file has column headings but no rows of data." |
  | Broken rows or unclosed quotes | "This file could not be read as a CSV..." |
  | Not readable as text | "This file is not readable as text. If it was created in Excel..." |
  | Wrong file type | "'report.xlsx' is not a CSV file..." |

- A confirmation message appears once the file loads:

  ```
  ✓ Dataset loaded successfully
  Rows: 1245
  Columns: 12
  ```

- If no file has been uploaded, the page shows **"Upload a CSV file to begin."**

### Dataset Information

Nine metric cards summarising the file at a glance:

| Card | Shows |
|---|---|
| Total Rows | How many records the file holds |
| Total Columns | How many fields each record has |
| Memory Usage | Size once loaded, in KB or MB |
| Missing Values | Empty cells across the whole file |
| Missing % | Share of all cells that are empty |
| Duplicate Rows | Rows identical to an earlier row |
| Numeric Columns | Columns holding numbers |
| Text Columns | Columns holding words or codes |
| Date Columns | Columns holding dates, including dates still stored as text |

Below the cards, a **column details table** with one row per column:

| Column | Data Type | Missing | Missing % | Unique | Example |
|---|---|---|---|---|---|
| Order Date | Date (stored as text) | 0 | 0.0 | 22 | 2024-01-05 |
| Amount | Decimal number | 3 | 12.5 | 19 | 120.5 |
| City | Text | 2 | 8.3 | 9 | Austin |

### Dataset Preview

- **The data itself**, displayed as an interactive table
- **A row slider** to preview between 5 and 100 rows, starting at 10

  Files with 5 rows or fewer are shown in full, because a slider needs a range
  to be useful.

## Project structure

```
app.py            the Streamlit interface  (what the user sees)
cleaning.py       the pandas functions     (what reads and describes the data)
sample_data.csv   a small file for trying the app
requirements.txt  dependencies
screenshots/      images used in this README
```

`cleaning.py` contains no Streamlit code, so its functions can be tested or
reused in a notebook. `app.py` contains no data logic — it collects input,
calls a function, and displays the result.

## How it works

### Loading returns an error instead of raising one

`load_csv()` always returns the same pair of values:

```python
df, error = cleaning.load_csv(uploaded_file)

if error:
    st.error(error)          # something went wrong, show why
else:
    st.session_state.df = df # we have data
```

`(DataFrame, None)` on success, `(None, "explanation")` on failure. Every way a
CSV can fail is caught inside that one function, so `app.py` only ever has to
check whether `error` is set. It also keeps the wording of user-facing messages
in one place.

### The file is only read once

A plain `if uploaded_file:` block would re-read the file on **every** click,
because Streamlit re-runs the whole script each time. The app compares the file
name against the one already stored:

```python
if uploaded_file.name != st.session_state.filename:
    ...load it...
```

Right now that just avoids wasted work. Once cleaning is added, it is what stops
your changes from being silently thrown away.

### State survives between clicks

Streamlit forgets ordinary variables on every re-run, so the loaded data lives
in `st.session_state`:

```python
st.session_state.df        # the dataset currently loaded
st.session_state.filename  # which file it came from
```

### One classifier, used everywhere

`column_kind()` decides whether a column is numeric, a date, a boolean or
text. Both the dashboard counts and the details table call it:

```python
def column_kind(series):
    if pd.api.types.is_bool_dtype(series):          return "boolean"
    if pd.api.types.is_numeric_dtype(series):       return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series): return "date"
    if looks_like_dates(series):                     return "date"
    return "text"
```

Because there is only one implementation, a column can never be counted as
numeric on the dashboard and shown as text in the table.

### Dates hiding in text columns

A CSV carries no type information, so a column of dates arrives as plain text.
`looks_like_dates()` samples the values and asks pandas to parse them, treating
the column as dates when almost all of them succeed.

The catch is that pandas will happily read `"20240115"` as a date, which would
turn ID numbers, years and postcodes into date columns. So values made only of
digits and dots are rejected before parsing is attempted:

```python
if float(values.str.fullmatch(r"[\d.]+").mean()) > 0.5:
    return False
```

Verified against ID numbers, years and zero-padded postcodes — all correctly
stay as text, while `2024-01-05`, `01/05/2024` and mixed formats are detected.

### Numbers that always add up

Booleans are counted separately from numeric, text and date, so the three
headline counts mean exactly what they say. A file containing boolean columns
gets a caption noting them, which keeps the totals reconciling with the column
count instead of quietly losing a column.

## Milestones

- [x] **Milestone 1** — project setup
- [x] **Milestone 2** — CSV upload and dataset preview
- [x] **Milestone 3** — dataset information dashboard
- [ ] **Milestone 4** — data cleaning (duplicates, missing values, column operations)
- [ ] **Milestone 5** — statistics
- [ ] **Milestone 6** — download the cleaned file
