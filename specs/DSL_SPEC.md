# SlideDSL Grammar Specification v1

## Overview

SlideDSL (`.sdsl`) is a human-readable, LLM-friendly domain-specific language for
defining slide presentations. It is the single intermediate representation between
natural language input and rendered output (.pptx, .ee4p, .pdf).

Design goals:
- **Human-readable**: Anyone can read and edit a `.sdsl` file
- **Git-friendly**: Clean diffs, mergeable, reviewable
- **LLM-friendly**: Structured enough to validate, loose enough that LLMs produce it reliably
- **Round-trippable**: Parse → modify → serialize produces valid DSL

## File Structure

A `.sdsl` file has two parts:
1. **Frontmatter** — presentation-level metadata (wrapped in `---`)
2. **Slide blocks** — separated by `---` on its own line

```
---
<frontmatter>
---

<slide block>

---

<slide block>

---
...
```

## Frontmatter

YAML-like key-value pairs. Nesting uses 2-space indentation.

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Presentation title |

### Optional Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `author` | string | null | Author name |
| `company` | string | null | Company name |
| `template` | path | null | Path to .pptx template file |
| `output` | enum | "pptx" | Output format: `pptx`, `ee4p`, `pdf` |
| `brand` | object | defaults | Brand configuration block |

### Brand Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `primary` | hex color | "1E2761" | Primary brand color (no # prefix) |
| `secondary` | hex color | "CADCFC" | Secondary color |
| `accent` | hex color | "F96167" | Accent color |
| `header_font` | string | "Arial Black" | Font for headings |
| `body_font` | string | "Calibri" | Font for body text |
| `logo` | path | null | Path to logo image |

### Example

```
---
presentation:
  title: "Q3 Data Platform Review"
  author: "Nitin"
  company: "Create Music Group"
  template: "./templates/cmg_brand.pptx"
  output: "pptx"
  brand:
    primary: "1E2761"
    secondary: "CADCFC"
    accent: "F96167"
    header_font: "Arial Black"
    body_font: "Calibri"
    logo: "./assets/logo.png"
---
```

## Slide Blocks

Each slide block starts with a `# Slide Name` heading and contains directives,
content, and optional speaker notes.

### Slide Name (required)

```
# My Slide Title
```

This is the internal name of the slide. It appears in the parser output and the
design index but is NOT necessarily the rendered title (use `##` for that).

### Directives

Directives are metadata lines starting with `@`. They control layout and behavior.

| Directive | Values | Required | Description |
|-----------|--------|----------|-------------|
| `@type` | See Slide Types | Yes | Controls which layout/renderer to use |
| `@background` | `light`, `dark`, `gradient`, `image` | No | Background treatment |
| `@layout` | string | No | Layout variant hint (e.g. `icon_rows`) |
| `@image` | path/URL | No | Image reference for image_text slides |
| `@notes` | text | No | Speaker notes (can be multi-line) |

### Slide Types

| Type | Description | Expected Content |
|------|-------------|-----------------|
| `title` | Opening slide | `##` heading, `###` subtitle |
| `section_divider` | Section break | `##` heading |
| `bullet_points` | Bullet list | `-` items, optional `@icon` |
| `two_column` | Side-by-side | Two `@col:` blocks |
| `image_text` | Image + text | `@image` + bullets or body |
| `stat_callout` | Big numbers | `@stat` items |
| `comparison` | Table/matrix | `@compare` block |
| `timeline` | Sequential steps | `@step` items |
| `quote` | Quotation | `##` quote text, `###` attribution |
| `closing` | Final slide | `##` heading, `###` contact |
| `freeform` | Unstructured | Any content |

### Content Elements

#### Headings
```
## Main Heading          → rendered as slide title
### Subtitle             → rendered as subtitle / subtext
```

#### Bullets
```
- First point
- Second point
  - Sub-point (2 spaces = level 1)
    - Sub-sub-point (4 spaces = level 2)
```

#### Icon Bullets (for `@layout: icon_rows`)
```
- @icon: rocket   | Launch the new platform
- @icon: shield   | Security hardening complete
- @icon: database | Data migration finished
```

#### Stats
```
@stat: 94% | Pipeline Uptime | Up from 87% in Q2
@stat: 3.2B | Events/Day
```

Format: `@stat: <value> | <label> [| <description>]`

#### Timeline Steps
```
@step: Jan 2025 | Joined CMG | Data & AI org kickoff
@step: Feb 2025 | Infra foundations
```

Format: `@step: <time> | <title> [| <description>]`

#### Columns
```
@col:
  ## Column Title
  - Bullet one
  - Bullet two

@col:
  ## Other Column
  - Bullet three
```

#### Comparison Tables
```
@compare:
  header: Risk | Mitigation | Status
  row: Schema drift | Proto-first migration | 🟡 In Progress
  row: Talent gaps | BCG X pipeline | 🟢 On Track
```

#### Speaker Notes
```
@notes: This slide covers our progress on the medallion
architecture. Key callout is the uptime improvement.
```

Notes can be multi-line — they continue until the next `@` directive or `---`.

## Parsing Rules

1. **Frontmatter** is everything between the first `---` pair
2. **Slides** are separated by `---` on its own line (with optional surrounding whitespace)
3. **Directives** (`@key: value`) are parsed before content
4. **Content** is everything that isn't a directive, heading, or slide separator
5. **Lenient parsing**: Unknown directives are ignored, missing fields get defaults
6. **Whitespace**: Leading/trailing whitespace on values is trimmed
7. **Encoding**: UTF-8, emoji are valid in content

## Serialization Rules

1. Frontmatter fields are quoted with double quotes
2. Slides are separated by `\n\n---\n\n`
3. Only non-default directive values are emitted
4. Empty content sections are omitted
5. Round-trip: `parse(serialize(parse(text)))` produces identical output to `parse(text)`

## File Extension

`.sdsl` (SlideDSL)

## MIME Type

`text/x-slidedsl` (proposed)

## Versioning

The frontmatter may include `dsl_version: 1` to pin the grammar version.
Parsers should assume v1 if not specified.
