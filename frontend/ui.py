"""The Streamlit user interface.

Layout:
  Sidebar  -> 1. pick the data folder, 2. filters
  Chart tab -> chart controls on the left, chart + export on the right
  Data tab  -> the loaded rows (after filters) and the list of files
"""

import pandas as pd
import streamlit as st

from backend import charts, export, filters, loader
from backend.schema import FILTER_COLUMNS, NUMBER_COLUMNS, TEXT_COLUMNS, TIME_COLUMN
from frontend.folder_picker import pick_folder

NONE = "(none)"
ALL_COLUMNS = [TIME_COLUMN] + TEXT_COLUMNS + NUMBER_COLUMNS
GROUPING_COLUMNS = TEXT_COLUMNS + ["run", "level", "difficulty", "hints_used"]


@st.cache_data(show_spinner="Loading files...")
def load_folder_cached(folder: str, signature: tuple) -> loader.LoadResult:
    # `signature` is only here so the cache refreshes when files change.
    return loader.load_folder(folder)


def main() -> None:
    st.set_page_config(page_title="Token Blast Explorer", page_icon="📊", layout="wide")
    st.title("Token Blast Data Explorer")

    folder = sidebar_folder_picker()
    if not folder:
        st.info("Choose a folder of **levels** CSV files in the sidebar to get started.")
        return

    try:
        result = load_folder_cached(folder, loader.folder_signature(folder))
    except loader.DataLoadError as err:
        st.error(f"Couldn't load this folder. {len(err.problems)} problem(s) found:")
        st.markdown("\n".join(f"- {p}" for p in err.problems))
        return

    with st.sidebar:
        st.success(f"Loaded {len(result.data):,} rows from {len(result.files)} file(s).")
        for warning in result.warnings:
            st.warning(warning)
        filtered = sidebar_filters(result.data)

    chart_tab, data_tab = st.tabs(["📈 Chart", "🗂️ Data"])
    with chart_tab:
        chart_page(filtered)
    with data_tab:
        data_page(filtered, result)


# ---------------------------------------------------------------- sidebar

def sidebar_folder_picker() -> str:
    with st.sidebar:
        st.header("1. Data folder")
        if st.button("📁 Browse for folder..."):
            chosen = pick_folder()
            if chosen:
                st.session_state.folder = chosen
        folder = st.text_input(
            "Folder path", key="folder",
            help="Every .csv file in this folder must be a levels file. Subfolders are not included.",
        )
    # "Copy as path" in Windows adds quotes around the path.
    return folder.strip().strip('"')


def sidebar_filters(data: pd.DataFrame) -> pd.DataFrame:
    st.header("2. Filters")
    st.caption("Leave a filter empty to include everything.")

    selections = {}
    for col in FILTER_COLUMNS:
        selections[col] = st.multiselect(
            col, filters.sorted_values(data[col]),
            format_func=charts.value_label, placeholder="All",
        )

    date_range = None
    days = data[TIME_COLUMN].dt.date.dropna()
    if not days.empty and days.min() != days.max():
        picked = st.date_input("Dates (UTC)", (days.min(), days.max()),
                               min_value=days.min(), max_value=days.max())
        if isinstance(picked, tuple) and len(picked) == 2:
            date_range = picked

    filtered = filters.apply_filters(data, selections, date_range)
    st.caption(f"{len(filtered):,} of {len(data):,} rows match.")
    return filtered


# ---------------------------------------------------------------- chart tab

def chart_page(data: pd.DataFrame) -> None:
    controls, preview = st.columns([1, 2.3], gap="large")

    with controls:
        spec = chart_setup_controls(data)
        style = chart_style_controls(data, spec)

    with preview:
        if data.empty:
            st.warning("No rows match the current filters.")
            return
        try:
            fig = charts.build_figure(data, spec, style)
        except Exception as exc:
            st.error(f"Couldn't draw this chart: {exc}")
            return
        st.image(export.figure_to_bytes(fig, "PNG", dpi=110))
        st.caption(f"Based on {len(data):,} rows.")
        export_controls(fig, style)


def chart_setup_controls(data: pd.DataFrame) -> charts.ChartSpec:
    with st.expander("Chart setup", expanded=True):
        chart_type = st.selectbox("Graph type", charts.CHART_TYPES)

        if chart_type == "Histogram":
            x_options = NUMBER_COLUMNS
        elif charts.x_is_optional(chart_type):
            x_options = [NONE] + TEXT_COLUMNS + NUMBER_COLUMNS
        else:
            x_options = ALL_COLUMNS
        x_default = "concept_accuracy" if chart_type == "Histogram" else "model"
        x = st.selectbox("X axis", x_options, index=_index_of(x_options, x_default))

        y, combine = None, "Mean"
        if charts.uses_combine(chart_type):
            combine = st.selectbox(
                "Combine Y values by", list(charts.COMBINE_OPTIONS),
                help="Many rows share each X value. This decides how their Y values become one bar or point.",
            )
        if charts.uses_y(chart_type) and combine != "Count":
            y = st.selectbox("Y axis", NUMBER_COLUMNS, index=_index_of(NUMBER_COLUMNS, "concept_accuracy"))

        color_by = st.selectbox("Color by", [NONE] + GROUPING_COLUMNS,
                                help="Split the chart into colored groups.")
        color_by = None if color_by == NONE else color_by
        if color_by and data[color_by].nunique() > 20:
            st.warning(f"'{color_by}' has {data[color_by].nunique()} groups, so the chart may be hard to read.")

        bins = 20
        if chart_type == "Histogram":
            bins = st.slider("Number of bins", 5, 100, 20)

        ms_to_seconds = False
        if charts.is_ms_column(x) or charts.is_ms_column(y):
            ms_to_seconds = st.checkbox("Convert ms to seconds", value=False)

    return charts.ChartSpec(
        chart_type=chart_type,
        x=None if x == NONE else x,
        y=y,
        color_by=color_by,
        combine=combine,
        bins=bins,
        ms_to_seconds=ms_to_seconds,
    )


def chart_style_controls(data: pd.DataFrame, spec: charts.ChartSpec) -> charts.ChartStyle:
    style = charts.ChartStyle()
    auto_x, auto_y = charts.auto_labels(spec)

    with st.expander("Titles & labels"):
        style.title = st.text_input("Title")
        style.subtitle = st.text_input("Subtitle")
        style.x_label = st.text_input("X axis label", placeholder=auto_x, help="Leave blank for the automatic label.")
        style.y_label = st.text_input("Y axis label", placeholder=auto_y, help="Leave blank for the automatic label.")
        if spec.color_by:
            style.legend_title = st.text_input("Legend title", placeholder=charts.pretty(spec.color_by))
        style.footnote = st.text_input("Footnote", placeholder="e.g. Source: Day 1 field work, n = 24")

    with st.expander("Colors"):
        if spec.color_by:
            groups = charts.group_labels(data, spec.color_by) if not data.empty else []
            palette = st.selectbox("Palette", charts.PALETTES)
            defaults = charts.default_group_colors(groups, palette)
            if len(groups) <= 20:
                st.caption("Click a swatch to change one group's color.")
                columns = st.columns(3)
                for i, group in enumerate(groups):
                    with columns[i % 3]:
                        style.group_colors[group] = st.color_picker(
                            group, defaults[group], key=f"color|{spec.color_by}|{palette}|{group}")
            else:
                st.caption("Too many groups to pick one by one, so the palette is used.")
                style.group_colors = defaults
        else:
            style.single_color = st.color_picker("Chart color", style.single_color)

    with st.expander("Axis scale & range"):
        st.caption("Use log scale or a narrower range when a few very large values squash the rest.")
        # Keys include the column so limits reset when you switch columns or units.
        units = "s" if spec.ms_to_seconds else "raw"
        if charts.x_is_continuous(spec.chart_type, spec.x, NUMBER_COLUMNS):
            style.log_x = st.checkbox("Log scale on X axis")
            left, right = st.columns(2)
            style.x_min = left.number_input("X min", value=None, placeholder="auto", key=f"xmin|{spec.x}|{units}")
            style.x_max = right.number_input("X max", value=None, placeholder="auto", key=f"xmax|{spec.x}|{units}")
        y_key = spec.y or "count"
        style.log_y = st.checkbox("Log scale on Y axis")
        left, right = st.columns(2)
        style.y_min = left.number_input("Y min", value=None, placeholder="auto", key=f"ymin|{y_key}|{units}")
        style.y_max = right.number_input("Y max", value=None, placeholder="auto", key=f"ymax|{y_key}|{units}")

    with st.expander("Size & style"):
        left, right = st.columns(2)
        style.width = left.number_input("Width (inches)", 4.0, 24.0, 10.0, step=0.5)
        style.height = right.number_input("Height (inches)", 3.0, 18.0, 6.0, step=0.5)
        style.font_size = st.slider("Font size", 8, 24, 12)
        style.x_tick_rotation = st.radio("Rotate X axis labels", [0, 45, 90], horizontal=True,
                                         format_func=lambda d: f"{d}°")
        if spec.color_by:
            style.legend_position = st.selectbox("Legend position", charts.LEGEND_POSITIONS)
        style.show_grid = st.checkbox("Show grid lines", value=True)

    return style


def export_controls(fig, style: charts.ChartStyle) -> None:
    st.subheader("Export")
    fmt_col, dpi_col, name_col = st.columns([1, 1, 2])
    format_name = fmt_col.selectbox("Format", list(export.EXPORT_FORMATS))
    is_raster = format_name in ("PNG", "JPEG")
    dpi = dpi_col.selectbox("Resolution (DPI)", [100, 200, 300, 600], index=2, disabled=not is_raster,
                            help="Only affects PNG and JPEG. PDF and SVG are always sharp.")
    base_name = name_col.text_input("File name", value=style.title or "chart")

    st.download_button(
        f"⬇️ Download {format_name}",
        data=export.figure_to_bytes(fig, format_name, dpi),
        file_name=export.file_name(base_name, format_name),
        mime=export.mime_type(format_name),
        type="primary",
    )


# ---------------------------------------------------------------- data tab

def data_page(data: pd.DataFrame, result: loader.LoadResult) -> None:
    st.caption(f"Showing {len(data):,} rows (after filters). Click a column header to sort.")
    st.dataframe(data, hide_index=True)
    with st.expander(f"Files loaded ({len(result.files)})"):
        st.dataframe(pd.DataFrame(result.files, columns=["file", "rows"]), hide_index=True)


def _index_of(options: list, value) -> int:
    return options.index(value) if value in options else 0
