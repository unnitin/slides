"""
src/renderer/pptx_renderer.py — PPTX Rendering Engine (STUB)

TODO (Claude Code Phase 3):
    Implement per RENDERER_SPEC.md. Key methods:
    - render(presentation: PresentationNode, output_dir: Path) -> Path
    - render_slide(slide: SlideNode, pptx, brand: BrandConfig)
    - Per slide-type renderers: _render_title, _render_stat_callout, etc.
    - Template-based mode: analyze_template_layouts, match_layout, clone_and_fill
    - Brand-based mode: render_from_scratch with geometry constants

Dependencies: python-pptx>=1.0
"""

from pathlib import Path
from typing import Optional

from src.dsl.models import BrandConfig, PresentationNode, SlideNode


def render(
    presentation: PresentationNode,
    output_dir: Path,
    template_path: Optional[str] = None,
) -> Path:
    """
    Render a PresentationNode to .pptx.

    Args:
        presentation: Parsed presentation from DSL.
        output_dir: Directory to write output file.
        template_path: Optional .pptx template to use.

    Returns:
        Path to the generated .pptx file.
    """
    raise NotImplementedError(
        "PPTX renderer not yet implemented. "
        "See specs/RENDERER_SPEC.md for full specification."
    )
