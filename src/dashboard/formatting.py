"""Formatting helpers that preserve missing and zero-valued evidence."""


def format_optional_currency(value: float | int | None) -> str:
    """Format an AUD metric without turning missing evidence into zero."""
    return f"${value:,.0f}" if value is not None else "Unknown"


def format_optional_percentage(value: float | int | None, *, ratio: bool = False) -> str:
    """Format a percentage while keeping a measured zero distinct from missing data."""
    if value is None:
        return "Unknown"
    return f"{value:.1%}" if ratio else f"{value:.1f}%"
