"""Turn the data plus the user's choices into a matplotlib figure.

The frontend fills in a ChartSpec (what to plot) and a ChartStyle (how it
looks), then calls build_figure().
"""

from dataclasses import dataclass, field

import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from backend.filters import sorted_values

CHART_TYPES = ["Bar", "Line", "Scatter", "Box plot", "Histogram"]

# How several Y values for the same X get combined into one (Bar and Line only).
COMBINE_OPTIONS = {
    "Mean": "mean",
    "Median": "median",
    "Sum": "sum",
    "Count": "count",
    "Min": "min",
    "Max": "max",
}

PALETTES = ["tab10", "colorblind", "deep", "pastel", "dark", "Set2", "viridis", "rocket"]

LEGEND_POSITIONS = ["Best", "Upper right", "Upper left", "Lower right", "Lower left", "Outside right", "Hidden"]

VALUE = "value"  # name of the combined Y column in aggregated tables


@dataclass
class ChartSpec:
    chart_type: str
    x: str | None
    y: str | None = None
    color_by: str | None = None
    combine: str = "Mean"
    bins: int = 20
    ms_to_seconds: bool = False  # show *_ms columns in seconds


@dataclass
class ChartStyle:
    title: str = ""
    subtitle: str = ""
    x_label: str = ""  # blank means "use an automatic label"
    y_label: str = ""
    legend_title: str = ""
    footnote: str = ""
    single_color: str = "#1f77b4"  # used when there is no "Color by"
    group_colors: dict[str, str] = field(default_factory=dict)  # group label -> hex color
    width: float = 10.0
    height: float = 6.0
    font_size: int = 12
    x_tick_rotation: int = 0
    legend_position: str = "Best"
    show_grid: bool = True
    # Axis scale and range. None means "automatic".
    log_x: bool = False
    log_y: bool = False
    x_min: float | None = None
    x_max: float | None = None
    y_min: float | None = None
    y_max: float | None = None


# ----- What each chart type needs (used by the frontend to show/hide inputs) -----

def uses_y(chart_type: str) -> bool:
    return chart_type != "Histogram"


def uses_combine(chart_type: str) -> bool:
    return chart_type in ("Bar", "Line")


def x_is_optional(chart_type: str) -> bool:
    return chart_type == "Box plot"


def x_is_continuous(chart_type: str, x: str | None, numeric_columns: list[str]) -> bool:
    """True when the X axis is a number line (so log scale and min/max make sense)."""
    return chart_type in ("Scatter", "Line", "Histogram") and x in numeric_columns


def is_ms_column(column: str | None) -> bool:
    return bool(column) and column.endswith("_ms")


# ----- Helpers -----

def value_label(value) -> str:
    """Show 2.0 as '2' so number categories look clean."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def group_labels(data: pd.DataFrame, column: str) -> list[str]:
    """The groups a column splits into, in natural order, as display text."""
    return [value_label(v) for v in sorted_values(data[column])]


def default_group_colors(groups: list[str], palette: str) -> dict[str, str]:
    colors = sns.color_palette(palette, n_colors=max(len(groups), 1)).as_hex()
    return dict(zip(groups, colors))


def pretty(column: str, seconds: bool = False) -> str:
    """'time_in_level_ms' -> 'Time in level (ms)', or 'Time in level (s)' if seconds=True."""
    text = column.replace("_", " ")
    if text.endswith(" ms"):
        text = text[:-3] + (" (s)" if seconds else " (ms)")
    return text[:1].upper() + text[1:]


def convert_ms_to_seconds(data: pd.DataFrame, columns: list[str | None]) -> pd.DataFrame:
    """Return a copy where the given *_ms columns are divided by 1000."""
    data = data.copy()
    for col in set(columns):
        if is_ms_column(col):
            data[col] = data[col] / 1000
    return data


def aggregate(data: pd.DataFrame, x: str, y: str | None, color_by: str | None, combine: str) -> pd.DataFrame:
    """One row per X (and per color group) with the combined Y in column 'value'."""
    keys = [x] if not color_by or color_by == x else [x, color_by]
    if combine == "Count":
        result = data.groupby(keys).size()
    else:
        result = data.groupby(keys)[y].agg(COMBINE_OPTIONS[combine])
    return result.reset_index(name=VALUE)


def auto_labels(spec: ChartSpec) -> tuple[str, str]:
    secs = spec.ms_to_seconds
    x_label = pretty(spec.x, secs) if spec.x else ""
    if spec.chart_type == "Histogram" or (uses_combine(spec.chart_type) and spec.combine == "Count"):
        y_label = "Count (level attempts)"
    elif uses_combine(spec.chart_type):
        y_label = f"{spec.combine} {pretty(spec.y, secs).lower()}"
    else:
        y_label = pretty(spec.y, secs) if spec.y else ""
    return x_label, y_label


# ----- Main entry point -----

def build_figure(data: pd.DataFrame, spec: ChartSpec, style: ChartStyle) -> Figure:
    if data.empty:
        raise ValueError("There are no rows to plot. Try loosening the filters.")
    if spec.ms_to_seconds:
        data = convert_ms_to_seconds(data, [spec.x, spec.y])

    grid_style = "whitegrid" if style.show_grid else "white"
    with sns.axes_style(grid_style), sns.plotting_context("notebook", font_scale=style.font_size / 12):
        fig = Figure(figsize=(style.width, style.height), layout="constrained")
        ax = fig.subplots()
        _draw(ax, data, spec, style)
        _apply_axes(ax, style)
        _apply_labels(fig, ax, spec, style)
    return fig


def _apply_axes(ax, style: ChartStyle) -> None:
    # "symlog" is a log scale that also handles 0 (plain log can't show zeros).
    # Values between -1 and 1 stay linear; beyond that each tick is 10x the last.
    plain_numbers = FuncFormatter(lambda value, _: f"{value:g}")  # 10 instead of 10^1
    if style.log_x:
        ax.set_xscale("symlog", linthresh=1)
        ax.xaxis.set_major_formatter(plain_numbers)
        if ax.dataLim.x0 >= 0:  # no negative data: start at 0, leave a little room past the max
            ax.set_xlim(left=0, right=max(ax.dataLim.x1 * 1.5, 1))
    if style.log_y:
        ax.set_yscale("symlog", linthresh=1)
        ax.yaxis.set_major_formatter(plain_numbers)
        if ax.dataLim.y0 >= 0:
            ax.set_ylim(bottom=0, top=max(ax.dataLim.y1 * 1.5, 1))
    if style.x_min is not None or style.x_max is not None:
        ax.set_xlim(left=style.x_min, right=style.x_max)
    if style.y_min is not None or style.y_max is not None:
        ax.set_ylim(bottom=style.y_min, top=style.y_max)


def _draw(ax, data: pd.DataFrame, spec: ChartSpec, style: ChartStyle) -> None:
    x, y, hue, kind = spec.x, spec.y, spec.color_by, spec.chart_type

    # Color settings: one color, or one color per group.
    if hue:
        hue_order = group_labels(data, hue)
        fallback = default_group_colors(hue_order, "tab10")
        palette = {g: style.group_colors.get(g, fallback[g]) for g in hue_order}
        colors = {"hue": hue, "hue_order": hue_order, "palette": palette}
    else:
        colors = {"color": style.single_color}

    if kind in ("Bar", "Line"):
        plot = aggregate(data, x, y, hue, spec.combine)
    else:
        plot = data.copy()

    # Group values become text labels so they match the color choices.
    if hue:
        plot[hue] = plot[hue].map(value_label)

    # Bar and box charts always treat X as categories.
    x_order = None
    if x and (kind in ("Bar", "Box plot") or not pd.api.types.is_numeric_dtype(plot[x])):
        if not pd.api.types.is_datetime64_any_dtype(plot[x]):
            x_order = group_labels(plot, x)
            plot[x] = plot[x].map(value_label)

    if kind == "Bar":
        sns.barplot(data=plot, x=x, y=VALUE, order=x_order, errorbar=None, ax=ax, **colors)
    elif kind == "Line":
        sns.lineplot(data=plot, x=x, y=VALUE, marker="o", errorbar=None, sort=False, ax=ax, **colors)
    elif kind == "Scatter":
        sns.scatterplot(data=plot, x=x, y=y, alpha=0.8, ax=ax, **colors)
    elif kind == "Box plot":
        sns.boxplot(data=plot, x=x, y=y, order=x_order, ax=ax, **colors)
    elif kind == "Histogram":
        sns.histplot(data=plot, x=x, bins=spec.bins, multiple="layer", ax=ax, **colors)
    else:
        raise ValueError(f"Unknown chart type: {kind}")


def _apply_labels(fig: Figure, ax, spec: ChartSpec, style: ChartStyle) -> None:
    auto_x, auto_y = auto_labels(spec)
    ax.set_xlabel(style.x_label or auto_x)
    ax.set_ylabel(style.y_label or auto_y)

    if style.title:
        fig.suptitle(style.title, fontweight="bold", fontsize=style.font_size * 1.4)
    if style.subtitle:
        ax.set_title(style.subtitle, color="#555555", fontsize=style.font_size * 1.05)

    if style.x_tick_rotation:
        align = "center" if style.x_tick_rotation == 90 else "right"
        for label in ax.get_xticklabels():
            label.set_rotation(style.x_tick_rotation)
            label.set_horizontalalignment(align)
            label.set_rotation_mode("anchor")

    legend = ax.get_legend()
    if legend is not None:
        title = style.legend_title or pretty(spec.color_by or "")
        if style.legend_position == "Hidden":
            legend.remove()
        elif style.legend_position == "Outside right":
            sns.move_legend(ax, "upper left", bbox_to_anchor=(1.01, 1), title=title, frameon=False)
        else:
            sns.move_legend(ax, style.legend_position.lower(), title=title)

    if style.footnote:
        # Sits just below the figure; exports use bbox_inches="tight" so it is included.
        fig.text(0.01, -0.01, style.footnote, ha="left", va="top",
                 fontsize=style.font_size * 0.85, color="#555555")
