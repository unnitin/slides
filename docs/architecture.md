# SlideDSL — Architecture Diagram

## End-to-End Pipeline

```
                         ┌─────────────────────────────────────────────┐
                         │            PHASE 5: ORCHESTRATOR            │
                         │         src/services/orchestrator.py        │
                         │                                             │
  "Q3 data platform      │  ┌───────┐   ┌────────┐   ┌───────────┐   │
   update for leadership" │  │ Route │──▶│ Enrich │──▶│ Assemble  │   │
  ───────────────────────▶│  │ input │   │ w/index│   │ pipeline  │   │
                         │  └───────┘   └────────┘   └─────┬─────┘   │
                         │                                  │         │
                         └──────────────────────────────────┼─────────┘
                                                            │
                    ┌───────────────────────────────────────┼──────────────────┐
                    │                                       │                  │
                    ▼                                       ▼                  ▼
  ┌──────────────────────────┐   ┌──────────────────────────────┐   ┌─────────────────┐
  │   PHASE 4: AGENTS        │   │   PHASE 2: DESIGN INDEX      │   │  PHASE 3:       │
  │                          │   │                               │   │  RENDERER       │
  │  agents/nl_to_dsl.py     │   │  src/index/                   │   │                 │
  │  ┌────────────────────┐  │   │  ┌───────────┐               │   │  src/renderer/  │
  │  │  NL-to-DSL Agent   │◀─┼───┼──│ retriever │  SearchResult │   │  ┌───────────┐  │
  │  │  (Claude)          │  │   │  │  .py      │──────────────▶│   │  │ pptx_     │  │
  │  │                    │  │   │  └───────────┘               │   │  │ renderer  │  │
  │  │  Prompt + retrieved│  │   │       ▲                      │   │  │ .py       │  │
  │  │  examples → DSL    │  │   │       │ query                │   │  └─────┬─────┘  │
  │  └────────┬───────────┘  │   │  ┌────┴──────┐              │   │        │        │
  │           │ .sdsl text   │   │  │  store.py │              │   │        ▼        │
  │           ▼              │   │  │  SQLite + │              │   │  ┌───────────┐  │
  │  agents/qa_agent.py      │   │  │  FTS5 +   │              │   │  │ format_   │  │
  │  ┌────────────────────┐  │   │  │  vectors  │              │   │  │ plugins   │  │
  │  │  QA Agent          │  │   │  └────┬──────┘              │   │  │ .py       │  │
  │  │  (visual inspect)  │  │   │       ▲                      │   │  └─────┬─────┘  │
  │  └────────────────────┘  │   │       │ chunks               │   │        │        │
  │                          │   │  ┌────┴──────┐              │   │        ▼        │
  │  agents/index_curator.py │   │  │ chunker   │              │   │   .pptx / .ee4p │
  │  ┌────────────────────┐  │   │  │ .py       │              │   │                 │
  │  │  Index Curator     │──┼──▶│  └───────────┘              │   └─────────────────┘
  │  │  (enrich chunks)   │  │   │                               │
  │  └────────────────────┘  │   └───────────────────────────────┘
  └──────────────────────────┘
              │
              │ DSL text
              ▼
  ┌──────────────────────────┐
  │   PHASE 1: CORE DSL      │
  │                          │
  │  src/dsl/                │
  │  ┌────────┐ ┌──────────┐│
  │  │models  │ │ parser   ││
  │  │.py     │ │ .py      ││
  │  │        │ │          ││
  │  │Pydantic│ │ .sdsl ──▶││──▶ PresentationNode
  │  │schemas │ │ text  ──▶││      ├── PresentationMeta
  │  └────────┘ └──────────┘│      │     ├── title, author, company
  │  ┌──────────┐           │      │     └── BrandConfig
  │  │serializer│           │      └── SlideNode[]
  │  │.py       │           │           ├── slide_type, background
  │  │          │           │           ├── heading, subheading
  │  │ Node ──▶ │──▶ .sdsl  │           ├── bullets[], stats[]
  │  │ text     │           │           ├── columns[], timeline[]
  │  └──────────┘           │           ├── compare, speaker_notes
  │                          │           └── image
  └──────────────────────────┘
```

## Data Flow

```
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │                           GENERATION FLOW (→)                               │
  │                                                                             │
  │  User NL ──▶ Agent ──▶ DSL text ──▶ Parser ──▶ Node ──▶ Renderer ──▶ .pptx │
  │                │                       │                                    │
  │                │                       │ validate                           │
  │                │                       ▼                                    │
  │                │               PresentationNode                             │
  │                │                       │                                    │
  │                │          ┌────────────┘                                    │
  │                │          ▼                                                 │
  │                │       Chunker ──▶ DeckChunk                                │
  │                │          │        SlideChunk[]                              │
  │                │          │        ElementChunk[]                            │
  │                │          ▼                                                 │
  │                │        Store ──▶ SQLite                                    │
  │                │          │                                                 │
  │                │          ▼                                                 │
  │                │      Retriever ◀── future queries                          │
  │                │                                                            │
  └────────────────┴────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────────────────────────────────────────┐
                    │                      FEEDBACK FLOW (←)                          │
                    │                                                                 │
                    │  User keeps slide  ──▶ feedback.py ──▶ keep_count++ on chunk    │
                    │  User edits slide  ──▶ feedback.py ──▶ edit_count++ + re-ingest │
                    │  User regens slide ──▶ feedback.py ──▶ regen_count++ (demote)   │
                    │                                                                 │
                    │  Quality score = keep / (keep + regen)                          │
                    │  Higher score = design surfaces more often in retrieval          │
                    └─────────────────────────────────────────────────────────────────┘
```

## Phase Build Map

### Phase 1: Core DSL — The Spine

Everything speaks this language. The DSL is the single contract
between all components.

```
  Files created:
  ├── src/dsl/models.py        Pydantic data models (PresentationNode, SlideNode, enums)
  ├── src/dsl/parser.py        .sdsl text → PresentationNode
  ├── src/dsl/serializer.py    PresentationNode → .sdsl text
  └── tests/test_parser.py     36 tests against sample.sdsl

  Depends on: nothing (foundation layer)
  Consumed by: every other phase
```

### Phase 2: Design Index — The Brain

Stores every slide ever produced or ingested. Learns which
designs work over time via feedback signals.

```
  Files created:
  ├── src/index/chunker.py     PresentationNode → DeckChunk + SlideChunk[] + ElementChunk[]
  ├── src/index/store.py       SQLite + FTS5 + vector BLOB storage
  ├── src/index/retriever.py   Hybrid search (semantic + structural + keyword)
  ├── scripts/ingest_deck.py   Ingest .sdsl files into the index
  ├── scripts/seed_index.py    Batch-ingest a directory of decks
  ├── tests/test_chunker.py    30 tests
  └── tests/test_index.py      34 tests (store CRUD, FTS, embeddings, retriever)

  Depends on: Phase 1 (parser, serializer, models)
  Consumed by: Phase 4 (agents query the retriever), Phase 5 (feedback loop)
```

### Phase 3: Renderer — The Hands

Turns validated PresentationNode into actual slide files.

```
  Files created:
  ├── src/renderer/pptx_renderer.py    SlideNode → python-pptx shapes
  ├── src/renderer/format_plugins.py   Plugin system for .ee4p, .pdf output
  └── tests/test_renderer.py

  Depends on: Phase 1 (reads SlideNode models)
  Consumed by: Phase 5 (orchestrator calls renderer after agent generates DSL)
```

### Phase 4: Agents — The Mouth

LLM-powered translation between human intent and structured DSL.

```
  Files created:
  ├── agents/prompts/nl_to_dsl.txt     System prompt for NL→DSL agent
  ├── agents/nl_to_dsl.py              NL → DSL translation (Claude)
  ├── agents/qa_agent.py               Visual QA inspection loop
  └── agents/index_curator.py          Background semantic enrichment

  Depends on: Phase 1 (generates DSL text), Phase 2 (retrieves examples from index)
  Consumed by: Phase 5 (orchestrator invokes agents)
```

### Phase 5: Orchestration — The Nervous System

Wires everything together. Closes the feedback loop.

```
  Files created:
  ├── src/services/orchestrator.py     End-to-end pipeline controller
  ├── src/services/feedback.py         User signals → index updates
  └── skills/                          Thin wrappers composing src modules

  Depends on: all previous phases
  Consumed by: end users (CLI, API)
```

## Three-Level Chunking Detail

```
  ┌─────────────────────────────────────────────────────────────────┐
  │  DECK CHUNK (1 per presentation)                                │
  │                                                                 │
  │  title, author, company, slide_count                            │
  │  slide_type_sequence: [title, section, stat, two_col, ...]      │
  │  narrative_summary (LLM), audience, purpose                     │
  │  brand_colors, template_used                                    │
  │  embedding → searchable by arc, audience, topic                 │
  │                                                                 │
  │  ┌───────────────────────────────────────────────────────────┐  │
  │  │  SLIDE CHUNK (1 per slide)                                │  │
  │  │                                                           │  │
  │  │  slide_name, slide_type, layout, background               │  │
  │  │  structural fingerprint:                                  │  │
  │  │    has_stats(3), has_bullets(0), has_columns(0), ...      │  │
  │  │  neighborhood: prev=section_divider, next=two_column      │  │
  │  │  deck_position: middle, section: "Platform Health"        │  │
  │  │  quality signals: keep=5, edit=1, regen=0 → score=0.83   │  │
  │  │  dsl_text (full DSL for this slide)                       │  │
  │  │  embedding → searchable by content, layout, shape         │  │
  │  │                                                           │  │
  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │  │
  │  │  │  ELEMENT     │ │  ELEMENT     │ │  ELEMENT     │        │  │
  │  │  │  stat        │ │  stat        │ │  stat        │        │  │
  │  │  │  "94%"       │ │  "3.2B"      │ │  "12"        │        │  │
  │  │  │  "Pipeline   │ │  "Events/    │ │  "Data       │        │  │
  │  │  │   Uptime"    │ │   Day"       │ │   Products"  │        │  │
  │  │  │  sibling: 3  │ │  sibling: 3  │ │  sibling: 3  │        │  │
  │  │  │  embedding → │ │  embedding → │ │  embedding → │        │  │
  │  │  │  searchable  │ │  searchable  │ │  searchable  │        │  │
  │  │  └─────────────┘ └─────────────┘ └─────────────┘        │  │
  │  └───────────────────────────────────────────────────────────┘  │
  └─────────────────────────────────────────────────────────────────┘
```

## File Tree by Phase

```
slidedsl/
│
├── PHASE 1 ─────────────────────────────────────
│   src/dsl/
│   ├── models.py              ◀ data models
│   ├── parser.py              ◀ .sdsl → PresentationNode
│   └── serializer.py          ◀ PresentationNode → .sdsl
│   tests/
│   └── test_parser.py         ◀ 36 tests
│
├── PHASE 2 ─────────────────────────────────────
│   src/index/
│   ├── chunker.py             ◀ 3-level chunking
│   ├── store.py               ◀ SQLite + FTS5 + vectors
│   └── retriever.py           ◀ hybrid search
│   scripts/
│   ├── ingest_deck.py         ◀ single deck ingestion
│   └── seed_index.py          ◀ batch ingestion
│   tests/
│   ├── test_chunker.py        ◀ 30 tests
│   └── test_index.py          ◀ 34 tests
│
├── PHASE 3 ─────────────────────────────────────
│   src/renderer/
│   ├── pptx_renderer.py       ◀ python-pptx output
│   └── format_plugins.py      ◀ .ee4p / .pdf converters
│   tests/
│   └── test_renderer.py
│
├── PHASE 4 ─────────────────────────────────────
│   agents/
│   ├── nl_to_dsl.py           ◀ NL → DSL agent
│   ├── qa_agent.py            ◀ visual QA loop
│   ├── index_curator.py       ◀ semantic enrichment
│   └── prompts/
│       ├── nl_to_dsl.txt
│       ├── qa_inspection.txt
│       └── index_curation.txt
│
├── PHASE 5 ─────────────────────────────────────
│   src/services/
│   ├── orchestrator.py        ◀ end-to-end pipeline
│   └── feedback.py            ◀ learning loop
│   skills/
│   ├── dsl_parse.py
│   ├── dsl_serialize.py
│   ├── chunk_slide.py
│   ├── embed.py
│   ├── index_search.py
│   ├── render_pptx.py
│   ├── template_analyze.py
│   └── format_convert.py
│
└── SHARED ──────────────────────────────────────
    docs/examples/sample.sdsl  ◀ test fixture (read-only)
    specs/*.md                 ◀ specifications (read-only)
    templates/                 ◀ company .pptx templates
```