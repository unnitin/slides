# Renderer Specification

## Overview

The renderer converts a `PresentationNode` (parsed DSL) into a `.pptx` file
using `python-pptx`. It is entirely deterministic — same input produces same
output, every time. All creative decisions happen upstream (in the DSL or the
design index), not in the renderer.

## Rendering Modes

### Mode 1: Template-Based (preferred)

When `meta.template` is set, the renderer maps slides to existing template layouts.

```
PresentationNode.meta.template = "./templates/cmg_brand.pptx"
    │
    ▼
┌──────────────────────────────────┐
│ 1. Open template .pptx           │
│ 2. Analyze available layouts     │
│ 3. Map each SlideNode → layout   │
│ 4. Clone layout, fill content    │
│ 5. Remove unused template slides │
│ 6. Save                          │
└──────────────────────────────────┘
```

### Mode 2: Brand-Based (fallback)

When no template is provided, the renderer generates slides from scratch using
the brand configuration (colors, fonts) and built-in layout algorithms.

```
PresentationNode.meta.brand = BrandConfig(...)
    │
    ▼
┌──────────────────────────────────┐
│ 1. Create blank presentation     │
│ 2. Apply brand colors/fonts      │
│ 3. For each slide: compute layout│
│ 4. Place elements using geometry │
│ 5. Save                          │
└──────────────────────────────────┘
```

## Slide Type → Layout Mapping

Each slide type has a rendering strategy:

### title
- Full-width heading centered vertically
- Subtitle below in smaller font
- Dark or gradient background recommended
- Logo in bottom-right if available

### section_divider
- Centered heading, large font
- Accent color strip or background
- Minimal content — breathing room

### stat_callout
- Stats arranged horizontally (2-4 per row)
- Value in 48-60pt bold, accent color
- Label in 16pt below value
- Description in 12pt muted color below label
- Layout: equally spaced across slide width

### bullet_points
- Left-aligned bullet list
- 14-16pt body font
- Proper `<a:buChar>` bullet formatting (NEVER unicode •)
- Sub-bullets indented with smaller font
- **icon_rows variant**: icon in colored circle left, text right

### two_column
- Slide split 50/50 (or 45/55 with visual weight)
- Column titles in bold
- Thin vertical divider line (optional)
- Independent bullet lists per column

### comparison
- Table layout with header row
- Header row: bold, brand primary background, white text
- Data rows: alternating light/white backgrounds
- Cell padding: 0.1" minimum

### timeline
- Horizontal or vertical step progression
- Connected by line/arrow
- Step number or date in accent color circle
- Title bold, description in muted text below
- Max 5-6 steps per slide (split if more)

### image_text
- Image on left or right (50% width)
- Text content on opposite side
- Image should use `sizing: contain` to preserve aspect ratio

### quote
- Large quotation text centered, 24-30pt italic
- Attribution below in 14pt, right-aligned
- Accent-colored quotation marks as decorative element

### closing
- Similar to title slide treatment
- Contact info / CTA centered
- Logo prominent

### freeform
- Best-effort rendering based on content present
- Falls back to bullet_points layout if uncertain

## Geometry Constants

All measurements in inches (python-pptx native unit via Inches()).

```python
# Slide dimensions (16:9)
SLIDE_WIDTH = 13.333
SLIDE_HEIGHT = 7.5

# Margins
MARGIN_TOP = 0.6
MARGIN_BOTTOM = 0.5
MARGIN_LEFT = 0.7
MARGIN_RIGHT = 0.7

# Content area
CONTENT_WIDTH = SLIDE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT   # 11.933
CONTENT_HEIGHT = SLIDE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM  # 6.4
CONTENT_TOP = MARGIN_TOP + 0.8  # below title area

# Title area
TITLE_LEFT = MARGIN_LEFT
TITLE_TOP = MARGIN_TOP
TITLE_WIDTH = CONTENT_WIDTH
TITLE_HEIGHT = 0.7

# Font sizes (points)
FONT_TITLE = 36
FONT_SUBTITLE = 20
FONT_HEADING = 24
FONT_BODY = 14
FONT_CAPTION = 11
FONT_STAT_VALUE = 54
FONT_STAT_LABEL = 16
FONT_STAT_DESC = 12

# Spacing
ELEMENT_GAP = 0.3          # between content blocks
COLUMN_GAP = 0.4           # between columns
BULLET_SPACING = 0.15      # between bullet items
```

## Background Rendering

```python
def apply_background(slide, bg_type: BackgroundType, brand: BrandConfig):
    if bg_type == "dark":
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor.from_string(brand.primary)
        # All text on this slide uses white/light colors
    elif bg_type == "light":
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    elif bg_type == "gradient":
        # Use primary → secondary gradient
        # python-pptx gradient support is limited; use image fallback
        pass
    elif bg_type == "image":
        # Apply image from @image directive
        pass
```

## Text Rendering Rules

1. **Never use unicode bullets (•)** — use python-pptx paragraph bullet formatting
2. **Bold all headers and inline labels** — set `font.bold = True`
3. **Multi-item content**: Create separate `<a:p>` elements, never concatenate
4. **Whitespace**: Add `xml:space="preserve"` for text with intentional spacing
5. **Smart quotes**: Use proper unicode quotes (\u201C \u201D), not ASCII
6. **Font fallback**: If specified font unavailable, fall back to Calibri (body) / Arial (headers)

## Color Resolution

Colors can be specified as:
- `"primary"` / `"secondary"` / `"accent"` → resolved from BrandConfig
- `"1E2761"` → direct hex (no # prefix)
- `"white"` / `"black"` → predefined constants

```python
def resolve_color(color_ref: str, brand: BrandConfig) -> RGBColor:
    NAMED = {"white": "FFFFFF", "black": "000000"}
    BRAND = {"primary": brand.primary, "secondary": brand.secondary, "accent": brand.accent}
    
    hex_val = BRAND.get(color_ref) or NAMED.get(color_ref) or color_ref
    r, g, b = int(hex_val[0:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16)
    return RGBColor(r, g, b)
```

## Format Converter Plugin System

The renderer always produces `.pptx` first, then optionally converts:

```python
class FormatConverter(Protocol):
    """Plugin interface for output format converters."""
    
    def can_convert(self, target_format: str) -> bool: ...
    def convert(self, pptx_path: Path, output_path: Path) -> Path: ...


class EE4PConverter(FormatConverter):
    """
    Converts .pptx → .ee4p
    
    Implementation strategy (choose one):
    a) CLI wrapper around vendor tool that produces .ee4p
    b) Direct serialization if .ee4p format spec is documented
    c) API call to a conversion service
    """
    
    def can_convert(self, target_format: str) -> bool:
        return target_format.lower() == "ee4p"
    
    def convert(self, pptx_path: Path, output_path: Path) -> Path:
        # Implementation depends on .ee4p format details
        raise NotImplementedError(
            "EE4P conversion requires format specification. "
            "Provide the .ee4p spec or a reference converter tool."
        )


class PDFConverter(FormatConverter):
    """Converts .pptx → .pdf via LibreOffice."""
    
    def can_convert(self, target_format: str) -> bool:
        return target_format.lower() == "pdf"
    
    def convert(self, pptx_path: Path, output_path: Path) -> Path:
        import subprocess
        subprocess.run([
            "soffice", "--headless", "--convert-to", "pdf",
            "--outdir", str(output_path.parent),
            str(pptx_path)
        ], check=True)
        return output_path
```

## Rendering Pipeline

```python
def render(presentation: PresentationNode) -> Path:
    """Full rendering pipeline."""
    
    # 1. Initialize
    if presentation.meta.template:
        pptx = load_template(presentation.meta.template)
        layout_map = analyze_template_layouts(pptx)
    else:
        pptx = create_blank_presentation()
        layout_map = None
    
    # 2. Render each slide
    for slide_node in presentation.slides:
        if layout_map:
            layout = match_layout(slide_node, layout_map)
            slide = clone_and_fill(pptx, layout, slide_node)
        else:
            slide = render_from_scratch(pptx, slide_node, presentation.meta.brand)
    
    # 3. Save .pptx
    pptx_path = Path("output.pptx")
    pptx.save(str(pptx_path))
    
    # 4. Convert if needed
    if presentation.meta.output != "pptx":
        converter = get_converter(presentation.meta.output)
        output_path = converter.convert(pptx_path, Path(f"output.{presentation.meta.output}"))
        return output_path
    
    return pptx_path
```

## QA Integration

After rendering, the pipeline automatically:
1. Converts slides to images via LibreOffice + pdftoppm
2. Passes images to the QA Agent
3. If issues found: fix → re-render → re-inspect (max 3 cycles)
4. Returns final output only after QA passes

## Error Handling

| Error | Handling |
|-------|----------|
| Template not found | Fall back to brand-based rendering |
| Font not available | Fall back to Calibri/Arial |
| Image not found | Skip image, log warning |
| Layout mismatch | Use closest match, log warning |
| Content overflow | Truncate with "..." and log |
| python-pptx exception | Log full error, save partial output |
