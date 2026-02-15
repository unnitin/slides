# Agent Specification

## Overview

The system has three LLM-powered agents. Each has a strict contract:
defined inputs, outputs, and responsibilities. Agents communicate through
typed data structures, never through free-form text passed between them.

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  NL-to-DSL   │     │  QA Agent    │     │  Index       │
│  Agent        │     │              │     │  Curator     │
│              │     │              │     │              │
│  IN: text    │     │  IN: images  │     │  IN: chunks  │
│  OUT: .sdsl  │     │  OUT: issues │     │  OUT: tags   │
└──────────────┘     └──────────────┘     └──────────────┘
```

## Agent 1: NL-to-DSL Translation Agent

### Purpose
Converts natural language input into valid SlideDSL text. This is the
primary user-facing agent — it's what makes "make me a deck about Q3"
turn into a structured, renderable specification.

### Contract

```python
class NLToDSLAgent:
    """Translates natural language → SlideDSL."""
    
    def generate(
        self,
        user_input: str,                    # raw NL input
        context: GenerationContext,          # everything the agent needs
    ) -> GenerationResult: ...


@dataclass
class GenerationContext:
    # What the user wants
    user_input: str                         # "Make a Q3 update deck for leadership"
    
    # What the index knows (retrieved before calling the agent)
    similar_slides: list[SearchResult]      # top-K similar slide designs
    similar_decks: list[SearchResult]       # top-K similar deck structures
    relevant_elements: list[SearchResult]   # relevant element designs
    
    # Company context
    brand: BrandConfig | None               # brand settings
    template_layouts: list[str] | None      # available template layout names
    
    # Constraints
    target_slide_count: int | None          # user-specified or inferred
    output_format: str                      # "pptx", "ee4p", etc.
    
    # Optional: source material
    source_documents: list[str] | None      # text extracted from uploaded docs
    existing_dsl: str | None                # if editing an existing deck


@dataclass
class GenerationResult:
    dsl_text: str                           # the generated SlideDSL
    confidence: float                       # 0-1, how confident the agent is
    design_references: list[str]            # chunk_ids from index that influenced the output
    reasoning: str                          # brief explanation of structural choices
```

### System Prompt Structure

The NL-to-DSL agent prompt has these sections (see `agents/prompts/nl_to_dsl.txt`):

1. **Role**: You are a presentation architect that outputs SlideDSL
2. **Grammar**: Full DSL grammar reference (from DSL_SPEC.md)
3. **Design principles**: Vary layouts, 1 message per slide, stat callouts for numbers
4. **Retrieved context**: Injected similar designs from the index
5. **Brand context**: Colors, fonts, template layouts available
6. **Constraints**: Slide count, format, audience
7. **Output rules**: Output ONLY valid .sdsl, no commentary

### Retrieval-Augmented Generation (RAG) Flow

The orchestrator does retrieval BEFORE calling the agent:

```
User Input: "Q3 data platform update for leadership"
    │
    ▼
┌──────────────────────────────────────────────┐
│ 1. RETRIEVE from Design Index                │
│                                              │
│    query: "Q3 data platform update"          │
│    ├─ deck search → past quarterly decks     │
│    ├─ slide search → stat/timeline slides    │
│    └─ element search → KPI presentations     │
│                                              │
│ 2. BUILD GenerationContext                   │
│    ├─ similar_slides: [top 5 slide designs]  │
│    ├─ similar_decks: [top 3 deck structures] │
│    ├─ relevant_elements: [top 5 elements]    │
│    └─ brand + template info                  │
│                                              │
│ 3. CALL NL-to-DSL Agent                     │
│    ├─ system prompt + grammar + design rules │
│    ├─ retrieved context injected             │
│    └─ user input                             │
│                                              │
│ 4. PARSE result                              │
│    ├─ validate DSL structure                 │
│    ├─ retry on parse failure (max 2)         │
│    └─ return GenerationResult                │
└──────────────────────────────────────────────┘
```

### Context Injection Format

Retrieved designs are injected into the prompt as examples:

```
## Reference Designs (from your organization's history)

These are proven slide designs from past presentations. Use them as
inspiration for layout choices and content structure, but adapt the
content to the current request.

### Similar Deck Structure (used for "Q2 Platform Review"):
Slide sequence: title → stat_callout → two_column → timeline → comparison → closing

### Proven Slide Design #1 (used 8 times, kept 7 times):
```sdsl
# Pipeline Metrics
@type: stat_callout
@background: light

@stat: 94% | Pipeline Uptime | Up from 87% in Q2
@stat: 3.2B | Events Processed Daily | Pub/Sub → BigQuery
```

### Proven Element Pattern:
When presenting KPIs, use 3 stats max per slide with descriptions.
```

### Error Handling

If the agent produces invalid DSL:
1. Parse the output and identify specific errors
2. Send error feedback + the malformed output back to the agent
3. Agent corrects (max 2 retries)
4. If still invalid, fall back to partial extraction of valid slides

## Agent 2: QA Agent

### Purpose
Visually inspects rendered slides and identifies layout, formatting,
and design issues. Runs after every render cycle.

### Contract

```python
class QAAgent:
    """Inspects rendered slides for visual issues."""
    
    def inspect(
        self,
        slide_images: list[SlideImage],
        expected: list[SlideNode],          # what we intended
    ) -> QAReport: ...


@dataclass
class SlideImage:
    slide_index: int
    image_path: str                         # path to rendered .jpg
    dsl_text: str                           # the DSL that produced this


@dataclass
class QAIssue:
    slide_index: int
    severity: str                           # "critical", "warning", "minor"
    category: str                           # "overlap", "overflow", "alignment",
                                            #   "contrast", "spacing", "content_missing"
    description: str
    suggested_fix: str | None


@dataclass  
class QAReport:
    issues: list[QAIssue]
    pass_: bool                             # True if no critical issues
    summary: str
```

### System Prompt

See `agents/prompts/qa_inspection.txt`. Key instructions:
- Assume there ARE issues — your job is to find them
- Check: overlapping elements, text overflow, alignment, contrast, spacing
- Check: content matches the DSL specification
- Report severity honestly — don't minimize

### QA Loop

```
Render → Screenshot → QA Agent → Fix issues → Re-render → QA Agent → Done
                                     │
                                     └─ max 3 iterations
```

## Agent 3: Index Curator

### Purpose
Enriches the design index by generating semantic summaries, topic tags,
audience labels, and content domain classifications for ingested chunks.
Runs asynchronously as a background process.

### Contract

```python
class IndexCuratorAgent:
    """Generates semantic metadata for index chunks."""
    
    def enrich_deck(self, deck: PresentationNode) -> DeckEnrichment: ...
    def enrich_slide(self, slide: SlideNode, deck_context: str) -> SlideEnrichment: ...
    def enrich_element(self, element: dict, slide_context: str) -> ElementEnrichment: ...


@dataclass
class DeckEnrichment:
    narrative_summary: str
    audience: str
    purpose: str
    topic_tags: list[str]


@dataclass
class SlideEnrichment:
    semantic_summary: str
    topic_tags: list[str]
    content_domain: str             # "metrics", "strategy", "team", "risk", "roadmap"


@dataclass
class ElementEnrichment:
    semantic_summary: str
    topic_tags: list[str]
```

### System Prompt

See `agents/prompts/index_curation.txt`. Key instructions:
- Be specific and concrete in summaries — "3 KPIs about pipeline health" not "some metrics"
- Topic tags should be 2-4 words, lowercase, specific to the content
- Content domain must be one of the predefined categories
- Audience should describe the role/level, not a name

### Batching

The curator processes chunks in batches to minimize API calls:

```python
# Batch all slides from a deck into one call
enrichments = curator.enrich_slides_batch(
    slides=[slide1, slide2, slide3],
    deck_context="Q3 quarterly review for leadership team"
)
```

## Model Selection

| Agent | Model | Reasoning |
|-------|-------|-----------|
| NL-to-DSL | claude-sonnet-4-5-20250514 | Best balance of quality + speed for generation |
| QA Agent | claude-sonnet-4-5-20250514 | Needs vision capabilities for image inspection |
| Index Curator | claude-haiku-4-5-20250929 | High volume, simpler task, cost-sensitive |

## Rate Limiting & Cost

- NL-to-DSL: 1 call per generation (+ up to 2 retries) = max 3 calls
- QA Agent: 1 call per QA cycle × max 3 cycles = max 3 calls
- Index Curator: 1 call per deck ingestion (batched) = 1 call
- Total per generation: ~4-7 API calls
- Total per ingestion: ~1-2 API calls

## Security

- Never pass user credentials or PII through agent prompts
- Template file paths are validated before injection
- Source documents are size-limited (max 50K tokens per generation)
- Agent outputs are always parsed/validated, never executed directly
