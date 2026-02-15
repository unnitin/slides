# Design Index Specification

## Purpose

The Design Index is the system's memory. It stores every slide, deck, and visual
element the system has ever produced or ingested, chunked at multiple granularities
so that any future query — from "how did we present revenue last quarter" to
"show me dark-background stat layouts" — returns relevant, proven designs.

## Core Principle: Multi-Granularity Chunking

A single presentation produces chunks at THREE levels. Each level captures
different semantic information and enables different search patterns.

```
┌─────────────────────────────────────────────────────┐
│                    DECK CHUNK                        │
│  "Q3 review deck for leadership, 12 slides,         │
│   covers platform metrics, team growth, roadmap"     │
│                                                      │
│  Searchable by: narrative arc, audience, purpose,    │
│  deck structure, topic coverage                      │
├─────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ SLIDE CHUNK │ │ SLIDE CHUNK │ │ SLIDE CHUNK │   │
│  │             │ │             │ │             │   │
│  │ "3-stat     │ │ "two-column │ │ "timeline   │   │
│  │  callout    │ │  comparison │ │  of team    │   │
│  │  showing    │ │  streaming  │ │  build-out  │   │
│  │  pipeline   │ │  vs batch   │ │  milestones"│   │
│  │  metrics"   │ │  strategy"  │ │             │   │
│  ├─────────────┤ ├─────────────┤ ├─────────────┤   │
│  │ ELEMENTS:   │ │ ELEMENTS:   │ │ ELEMENTS:   │   │
│  │ ┌─────────┐ │ │ ┌─────────┐ │ │ ┌─────────┐ │   │
│  │ │ stat:   │ │ │ │ col:    │ │ │ │ step:   │ │   │
│  │ │ 94%     │ │ │ │ streaming│ │ │ │ Jan 25  │ │   │
│  │ │ uptime  │ │ │ │ proto   │ │ │ │ joined  │ │   │
│  │ ├─────────┤ │ │ │ enforce │ │ │ ├─────────┤ │   │
│  │ │ stat:   │ │ │ ├─────────┤ │ │ │ step:   │ │   │
│  │ │ 3.2B    │ │ │ │ col:    │ │ │ │ Q2 25   │ │   │
│  │ │ events  │ │ │ │ batch   │ │ │ │ platform│ │   │
│  │ └─────────┘ │ │ │ dbt     │ │ │ │ v1 live │ │   │
│  │             │ │ └─────────┘ │ │ └─────────┘ │   │
│  └─────────────┘ └─────────────┘ └─────────────┘   │
└─────────────────────────────────────────────────────┘
```

## Chunk Types

### 1. Deck Chunk

Captures the presentation as a whole.

```python
@dataclass
class DeckChunk:
    id: str                         # uuid
    source_file: str                # original .sdsl or .pptx path
    title: str                      # presentation title
    author: str | None
    company: str | None
    created_at: datetime
    
    # Semantic summary (LLM-generated)
    narrative_summary: str          # 2-3 sentence description of the deck's story
    audience: str                   # who this was built for
    purpose: str                    # inform, persuade, update, propose, etc.
    
    # Structural fingerprint
    slide_count: int
    slide_type_sequence: list[str]  # ["title", "stat_callout", "two_column", ...]
    topic_tags: list[str]           # extracted topics: ["data platform", "hiring", ...]
    
    # Design metadata
    template_used: str | None
    brand_colors: list[str]
    
    # Embedding (for semantic search)
    embedding: list[float]          # from narrative_summary + topic_tags
    
    # References
    slide_chunk_ids: list[str]      # links to child slide chunks
```

**What makes this searchable:**
- "Show me all decks we've made for leadership" → matches `audience`
- "How do we usually structure a quarterly review?" → matches `slide_type_sequence` + `purpose`
- "Decks about the data platform" → matches `topic_tags` + `narrative_summary`

### 2. Slide Chunk

Captures an individual slide's semantics and visual structure.

```python
@dataclass
class SlideChunk:
    id: str                         # uuid
    deck_chunk_id: str              # parent deck reference
    slide_index: int                # position in the deck (0-based)
    
    # From DSL
    slide_name: str
    slide_type: str                 # "stat_callout", "two_column", etc.
    layout_variant: str | None      # "icon_rows", etc.
    background: str                 # "dark", "light", etc.
    
    # Semantic content (what the slide is ABOUT)
    semantic_summary: str           # LLM-generated: "3 KPI metrics showing pipeline
                                    #   health improvement quarter over quarter"
    topic_tags: list[str]           # ["pipeline uptime", "event throughput", "data products"]
    content_domain: str             # "metrics", "strategy", "team", "risk", "roadmap"
    
    # Structural fingerprint (what the slide CONTAINS)
    has_stats: bool
    stat_count: int
    has_bullets: bool
    bullet_count: int
    has_columns: bool
    column_count: int
    has_timeline: bool
    step_count: int
    has_comparison: bool
    has_image: bool
    has_icons: bool
    
    # The actual DSL text for this slide (for retrieval)
    dsl_text: str
    
    # Visual metadata (populated after rendering)
    thumbnail_path: str | None      # rendered preview image
    color_palette: list[str]        # actual colors used on this slide
    
    # Embedding
    embedding: list[float]          # from semantic_summary + topic_tags + structural features
    
    # Neighborhood context (how this slide fits in the deck)
    prev_slide_type: str | None     # what comes before
    next_slide_type: str | None     # what comes after
    section_name: str | None        # which section of the deck
    deck_position: str              # "opening", "middle", "closing"
    
    # Signals
    use_count: int
    keep_count: int                 # user accepted as-is
    edit_count: int                 # user modified then kept
    regen_count: int                # user rejected / regenerated
    
    # References
    element_chunk_ids: list[str]    # links to child element chunks
```

**What makes this searchable:**
- "Show me stat callout slides" → matches `slide_type`
- "How did we present pipeline metrics?" → semantic match on `semantic_summary`
- "Dark background slides with 3 big numbers" → `background` + `stat_count`
- "What usually follows a section divider?" → `prev_slide_type` neighborhood search
- "Most reused slide designs" → sort by `keep_count`

### 3. Element Chunk

Captures individual visual elements within a slide. This is the finest
granularity — it lets you search for specific chart types, stat presentations,
icon treatments, or text patterns.

```python
@dataclass
class ElementChunk:
    id: str                         # uuid
    slide_chunk_id: str             # parent slide reference
    deck_chunk_id: str              # grandparent deck reference
    
    # Element type
    element_type: str               # "stat", "bullet_group", "column", "timeline_step",
                                    #   "comparison_row", "heading", "icon_bullet", "image"
    
    # Semantic content
    semantic_summary: str           # "Revenue metric showing 94% pipeline uptime with
                                    #   quarter-over-quarter improvement context"
    topic_tags: list[str]           # ["pipeline", "uptime", "SLA"]
    
    # Raw content (type-specific)
    raw_content: dict               # The actual data:
                                    #   stat: {"value": "94%", "label": "Pipeline Uptime", "desc": "..."}
                                    #   bullet_group: {"items": [...], "has_icons": true}
                                    #   column: {"title": "Streaming", "bullets": [...]}
                                    #   comparison_row: {"cells": [...]}
                                    #   timeline_step: {"time": "Jan 2025", "title": "..."}
    
    # Visual treatment metadata
    visual_treatment: dict          # {"font_size": "60pt", "color": "accent",
                                    #   "position": "left_third", "has_description": true}
    
    # Embedding
    embedding: list[float]          # from semantic_summary + element_type + content
    
    # Context
    slide_type: str                 # parent slide's type
    position_in_slide: int          # ordering within the slide
    sibling_count: int              # how many elements at this level
```

**What makes this searchable:**
- "Show me how we've displayed revenue numbers" → matches stat elements with revenue tags
- "Icon bullet examples" → matches `element_type: icon_bullet`
- "3-column comparison layouts" → matches column elements with `sibling_count: 3`
- "How do we usually present timelines?" → matches timeline_step elements across decks

## Embedding Strategy

### What Gets Embedded

Each chunk type produces a text string for embedding:

**Deck chunk embedding text:**
```
{title}. {narrative_summary}. Audience: {audience}. Purpose: {purpose}.
Topics: {topic_tags joined}. Structure: {slide_type_sequence joined}.
```

**Slide chunk embedding text:**
```
{slide_name}. {semantic_summary}. Type: {slide_type}.
Layout: {layout_variant}. Topics: {topic_tags joined}.
Content: {stat_count} stats, {bullet_count} bullets, {column_count} columns.
Position: {deck_position}. Domain: {content_domain}.
```

**Element chunk embedding text:**
```
{element_type}: {semantic_summary}. Topics: {topic_tags joined}.
Content: {raw_content summary}. Context: {slide_type} slide.
```

### Embedding Model

Use Anthropic's Voyage embeddings or OpenAI `text-embedding-3-small` for v1.
Store as numpy arrays, search with cosine similarity. Migrate to a proper
vector DB (Vertex AI Vector Search on GCP) when the index exceeds ~50K chunks.

### Hybrid Search

Retrieval combines:
1. **Semantic search** — cosine similarity on embeddings
2. **Structural filters** — SQL WHERE clauses on metadata
3. **Keyword match** — FTS5 full-text search on content fields

```python
# Example: "dark background stat slides about revenue"
results = index.search(
    query="revenue metrics performance",     # → semantic embedding
    filters={
        "slide_type": "stat_callout",        # → SQL filter
        "background": "dark",                # → SQL filter
    },
    keywords=["revenue"],                     # → FTS5
    granularity="slide",                     # search slide chunks
    limit=10,
)
```

## Storage Schema (SQLite)

```sql
-- Deck-level chunks
CREATE TABLE deck_chunks (
    id TEXT PRIMARY KEY,
    source_file TEXT,
    title TEXT NOT NULL,
    author TEXT,
    company TEXT,
    created_at TEXT NOT NULL,
    narrative_summary TEXT,
    audience TEXT,
    purpose TEXT,
    slide_count INTEGER,
    slide_type_sequence TEXT,       -- JSON array
    topic_tags TEXT,                -- JSON array
    template_used TEXT,
    brand_colors TEXT,              -- JSON array
    embedding BLOB                  -- numpy array bytes
);

-- Full-text search on decks
CREATE VIRTUAL TABLE deck_chunks_fts USING fts5(
    title, narrative_summary, audience, purpose, topic_tags,
    content=deck_chunks, content_rowid=rowid
);

-- Slide-level chunks
CREATE TABLE slide_chunks (
    id TEXT PRIMARY KEY,
    deck_chunk_id TEXT NOT NULL REFERENCES deck_chunks(id),
    slide_index INTEGER NOT NULL,
    slide_name TEXT,
    slide_type TEXT NOT NULL,
    layout_variant TEXT,
    background TEXT DEFAULT 'light',
    semantic_summary TEXT,
    topic_tags TEXT,                -- JSON array
    content_domain TEXT,
    has_stats INTEGER DEFAULT 0,
    stat_count INTEGER DEFAULT 0,
    has_bullets INTEGER DEFAULT 0,
    bullet_count INTEGER DEFAULT 0,
    has_columns INTEGER DEFAULT 0,
    column_count INTEGER DEFAULT 0,
    has_timeline INTEGER DEFAULT 0,
    step_count INTEGER DEFAULT 0,
    has_comparison INTEGER DEFAULT 0,
    has_image INTEGER DEFAULT 0,
    has_icons INTEGER DEFAULT 0,
    dsl_text TEXT,
    thumbnail_path TEXT,
    color_palette TEXT,            -- JSON array
    prev_slide_type TEXT,
    next_slide_type TEXT,
    section_name TEXT,
    deck_position TEXT,
    use_count INTEGER DEFAULT 0,
    keep_count INTEGER DEFAULT 0,
    edit_count INTEGER DEFAULT 0,
    regen_count INTEGER DEFAULT 0,
    embedding BLOB
);

CREATE VIRTUAL TABLE slide_chunks_fts USING fts5(
    slide_name, semantic_summary, topic_tags, content_domain, dsl_text,
    content=slide_chunks, content_rowid=rowid
);

-- Element-level chunks
CREATE TABLE element_chunks (
    id TEXT PRIMARY KEY,
    slide_chunk_id TEXT NOT NULL REFERENCES slide_chunks(id),
    deck_chunk_id TEXT NOT NULL REFERENCES deck_chunks(id),
    element_type TEXT NOT NULL,
    semantic_summary TEXT,
    topic_tags TEXT,                -- JSON array
    raw_content TEXT,              -- JSON object
    visual_treatment TEXT,         -- JSON object
    slide_type TEXT,
    position_in_slide INTEGER,
    sibling_count INTEGER,
    embedding BLOB
);

CREATE VIRTUAL TABLE element_chunks_fts USING fts5(
    element_type, semantic_summary, topic_tags,
    content=element_chunks, content_rowid=rowid
);

-- Phrase trigger index: maps natural language phrases to slide designs
-- This is what accumulates over time from NL→DSL translations
CREATE TABLE phrase_triggers (
    id TEXT PRIMARY KEY,
    phrase TEXT NOT NULL,           -- the NL phrase that triggered this
    normalized_phrase TEXT,         -- lowercased, stopwords removed
    matched_slide_chunk_id TEXT REFERENCES slide_chunks(id),
    matched_element_chunk_id TEXT REFERENCES element_chunks(id),
    confidence REAL DEFAULT 0.5,
    hit_count INTEGER DEFAULT 1,
    created_at TEXT,
    updated_at TEXT
);

CREATE INDEX idx_phrase_normalized ON phrase_triggers(normalized_phrase);

-- Feedback log: raw signal data before aggregation
CREATE TABLE feedback_log (
    id TEXT PRIMARY KEY,
    chunk_id TEXT NOT NULL,        -- which chunk got feedback
    chunk_type TEXT NOT NULL,      -- "deck", "slide", "element"
    signal TEXT NOT NULL,          -- "keep", "edit", "regen", "delete"
    context TEXT,                  -- JSON: what the user changed, why
    created_at TEXT NOT NULL
);
```

## Ingestion Pipeline

When a new deck is ingested (from .sdsl or .pptx):

```
Input (.sdsl or .pptx)
    │
    ▼
┌──────────────────┐
│ 1. Parse to       │  .pptx → extract text/structure → generate DSL
│    PresentationNode│  .sdsl → parse directly
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 2. Generate       │  Call Claude to produce:
│    Semantic        │    - deck narrative_summary, audience, purpose
│    Summaries       │    - per-slide semantic_summary, content_domain
│    (LLM)          │    - per-element semantic_summary
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 3. Chunk at       │  Create DeckChunk, SlideChunks, ElementChunks
│    3 Granularities │  Populate structural fingerprints
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 4. Compute        │  Embed each chunk's text representation
│    Embeddings      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 5. Store          │  Write to SQLite + FTS5 + embedding blobs
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 6. Render         │  Generate thumbnail for visual reference
│    Thumbnails      │  (optional, runs async)
└──────────────────┘
```

## Retrieval API

```python
class DesignIndexRetriever:
    
    def search(
        self,
        query: str,                              # natural language query
        granularity: Literal["deck", "slide", "element"] = "slide",
        filters: dict[str, Any] | None = None,   # structural filters
        keywords: list[str] | None = None,        # FTS5 keywords
        limit: int = 10,
        min_score: float = 0.3,
    ) -> list[SearchResult]: ...

    def find_similar_slides(
        self, 
        slide: SlideNode,                        # find slides like this one
        limit: int = 5,
    ) -> list[SearchResult]: ...

    def get_slide_context(
        self, 
        slide_chunk_id: str,                     # get deck context for a slide
    ) -> SlideContext: ...
    
    def suggest_next_slide(
        self,
        current_slides: list[SlideNode],         # what's been built so far
        limit: int = 3,
    ) -> list[SearchResult]: ...

    def get_best_design_for(
        self,
        content_type: str,                       # "stat_callout"
        topic: str,                              # "revenue metrics"
        audience: str | None = None,
    ) -> SearchResult | None: ...


@dataclass
class SearchResult:
    chunk_id: str
    chunk_type: str                  # "deck", "slide", "element"
    score: float                     # 0.0 - 1.0 combined relevance
    semantic_score: float            # cosine similarity component
    structural_score: float          # filter match component
    keyword_score: float             # FTS5 rank component
    
    # The actual content
    dsl_text: str | None             # for slide chunks
    raw_content: dict | None         # for element chunks
    semantic_summary: str
    topic_tags: list[str]
    
    # Context
    deck_title: str | None
    slide_type: str | None
    thumbnail_path: str | None
    
    # Quality signals
    keep_count: int
    regen_count: int
    quality_score: float             # keep_count / (keep_count + regen_count)


@dataclass
class SlideContext:
    """Full context of where a slide lives in its deck."""
    deck_title: str
    deck_summary: str
    slide_index: int
    total_slides: int
    prev_slide: SlideChunk | None
    next_slide: SlideChunk | None
    section_name: str | None
    deck_position: str               # "opening", "middle", "closing"
```

## Feedback Integration

```python
class FeedbackProcessor:
    """Processes user signals back into the index."""
    
    def record_keep(self, chunk_id: str):
        """User accepted the generated slide as-is."""
        # Increment keep_count
        # Boost embedding weight for this design
        # Record phrase trigger if we have the NL input
    
    def record_edit(self, chunk_id: str, edited_dsl: str):
        """User modified the slide then kept it."""
        # Increment edit_count on original
        # INGEST the edited version as a NEW slide chunk
        # The edited version starts with higher quality_score
    
    def record_regen(self, chunk_id: str):
        """User rejected and asked for regeneration."""
        # Increment regen_count
        # Lower quality_score
        # If regen_count > 3x keep_count, flag for review
    
    def record_phrase_hit(self, phrase: str, matched_chunk_id: str):
        """A natural language phrase matched to this design."""
        # Insert/update phrase_triggers table
        # Increment hit_count for existing phrases
```

## Scaling Notes

**v1 (SQLite, local)**
- Fine for up to ~50K chunks (~5K decks)
- Embeddings stored as BLOB, loaded into numpy for search
- Single-process, no concurrent writes

**v2 (GCP)**
- Migrate to Cloud SQL (Postgres) or Firestore for metadata
- Vertex AI Vector Search for embeddings
- Cloud Run for the retrieval API
- Pub/Sub for async ingestion pipeline
- BigQuery for analytics on usage patterns
