"""
skills/render_pptx.py — Render a PresentationNode to .pptx.

Wraps src.renderer.pptx_renderer.render.
"""

from pathlib import Path
from typing import Optional

from src.dsl.models import PresentationNode
from src.renderer.pptx_renderer import render as _render


def render(
    presentation: PresentationNode,
    output_dir: str,
    template_path: Optional[str] = None,
) -> Path:
    """Render a parsed presentation to a .pptx file.

    Args:
        presentation: Parsed PresentationNode from DSL.
        output_dir: Directory to write the output file.
        template_path: Optional .pptx template to use for layout matching.

    Returns:
        Path to the generated .pptx file.
    """
    return _render(
        presentation=presentation,
        output_dir=Path(output_dir),
        template_path=template_path,
    )
