"""Save a figure to bytes in the format the user picked."""

import io

from matplotlib.figure import Figure

# Display name -> (matplotlib format, file extension, MIME type)
EXPORT_FORMATS = {
    "PNG": ("png", "png", "image/png"),
    "JPEG": ("jpeg", "jpg", "image/jpeg"),
    "PDF": ("pdf", "pdf", "application/pdf"),
    "SVG": ("svg", "svg", "image/svg+xml"),
}


def figure_to_bytes(fig: Figure, format_name: str = "PNG", dpi: int = 200) -> bytes:
    fmt, _, _ = EXPORT_FORMATS[format_name]
    buffer = io.BytesIO()
    # White background so JPEGs and PDFs don't come out with transparent/black edges.
    fig.savefig(buffer, format=fmt, dpi=dpi, bbox_inches="tight", facecolor="white")
    return buffer.getvalue()


def file_name(base: str, format_name: str) -> str:
    _, ext, _ = EXPORT_FORMATS[format_name]
    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in base).strip() or "chart"
    return f"{safe}.{ext}"


def mime_type(format_name: str) -> str:
    return EXPORT_FORMATS[format_name][2]
