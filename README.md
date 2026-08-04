# Smart Data Cleaning Utility

A Streamlit web app for cleaning messy CSV files.

This project is being built in milestones. **Milestone 2 is complete**: you can
upload a CSV file and preview what is inside it. Cleaning tools come next.

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

**After uploading a CSV**

![Dataset preview with row counts, column types and the data table](screenshots/02-preview.png)

<!-- Screenshot placeholder: upload sample_data.csv, take a screenshot of the
     preview page, and save it as screenshots/02-preview.png -->

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

### Dataset Preview

- **Row and column counts** shown as metrics at the top of the page
- **Column names and data types** in a table, with pandas dtypes translated
  into readable names (`object` becomes "Text", `int64` becomes "Whole number")
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

## Milestones

- [x] **Milestone 1** — project setup
- [x] **Milestone 2** — CSV upload and dataset preview
- [ ] **Milestone 3** — data cleaning (duplicates, missing values, column operations)
- [ ] **Milestone 4** — statistics
- [ ] **Milestone 5** — download the cleaned file
