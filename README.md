# Token Blast Data Explorer

A small Python app for charting the **levels** CSV files from our Token Blast field work.
Pick a folder, choose X / Y / graph type from dropdowns, style the chart, and export it as PNG, JPEG, PDF or SVG.

## Setup (once per computer)

1. Install Python 3.10 or newer from <https://www.python.org/downloads/>.
   During setup, **tick "Add python.exe to PATH"**.
   (If you already use the `uv` Python manager, you can skip this. `Start.bat` will use uv.)
2. Download this repo (green **Code** button → **Download ZIP**, then unzip, or `git clone`).

## Running it

Double-click **`Start.bat`**.

- The first run takes a minute or two while it installs what it needs.
- The app opens in your browser. Keep the black window open while you use it; close it to quit.

## Using it

1. **Data folder** (sidebar): click **Browse for folder...** or paste a folder path.
   Every `.csv` in that folder must be a *levels* file (`token-blast-levels_*.csv`).
   If any file isn't, the app lists which files have problems and why. Subfolders are not read.
2. **Filters** (sidebar): limit the chart to certain models, difficulties, participants, dates, etc.
   Empty filter = include everything.
3. **Chart tab**
   - *Chart setup*: graph type, X axis, Y axis, how to combine Y values, and an optional **Color by** to split into groups.
   - *Titles & labels*: title, subtitle, axis labels, legend title, footnote.
   - *Colors*: one color, or a palette with a color per group.
   - *Axis scale & range*: log scale and min/max for each axis. Use these when a few huge values squash the rest.
     (Time columns also get a **Convert ms to seconds** checkbox in Chart setup.)
   - *Size & style*: chart size, font size, label rotation, legend position, grid lines.
   - *Export*: pick a format and resolution, then **Download**.
4. **Data tab**: the rows currently included (after filters) and the list of loaded files.

### "Combine Y values by" (Bar and Line charts)

Many rows share each X value (e.g. every level played on `chatgpt`), but a bar shows one number.
This setting decides that number: **Mean**, **Median**, **Sum**, **Count** (number of rows, no Y needed), **Min** or **Max**.

### Notes on the data

- `score` is a running total within a run; `level_points` is the points for that level alone.
  Use `level_points` when comparing levels or models level by level.
- A level number can appear twice in a run if a player exited and restarted that model.

## Project layout

```
Start.bat            one-click start (installs packages into .packages\, runs launch.py)
launch.py            starts the app and opens the browser
app.py               Streamlit entry point
frontend/            user interface only
  ui.py              all screens, dropdowns and buttons
  folder_picker.py   Windows "choose folder" dialog
backend/             data work only (no UI code)
  schema.py          expected columns of a levels file
  loader.py          reads + checks every CSV in a folder
  filters.py         applies the sidebar filters
  charts.py          builds the chart from the user's choices
  export.py          saves the chart as PNG / JPEG / PDF / SVG
```

If the game adds or renames a column, update `backend/schema.py`.

Field data (`*.csv`) is in `.gitignore` so participant data doesn't get pushed to GitHub.
