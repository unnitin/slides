"""
skills/format_convert.py — Convert .pptx to other formats (.ee4p, .pdf).

Wraps src.renderer.format_plugins.get_converter.
"""

from pathlib import Path

from src.renderer.format_plugins import get_converter


def convert(pptx_path: str, output_path: str, target_format: str) -> Path:
    """Convert a .pptx file to the specified format.

    Args:
        pptx_path: Path to the source .pptx file.
        output_path: Path for the output file.
        target_format: Target format ("pdf", "ee4p").

    Returns:
        Path to the converted file.
    """
    converter = get_converter(target_format)
    return converter.convert(Path(pptx_path), Path(output_path))
