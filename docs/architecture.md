# SlideDSL -- Architecture

## Phase Dependency Graph

```
  PHASE 1                 PHASE 2                PHASE 3
  Core DSL                Design Index            Renderer
  ────────                ────────────            ────────
  models.py ─────────────▶ chunker.py             pptx_renderer.py
  parser.py ─────────────▶ chunker.py             pptx_renderer.py
  serializer.py ─────────▶ chunker.py             format_plugins.py
       │                      │                        │
       │  PresentationNode    │  DeckChunk             │  .pptx
       │  SlideNode           │  SlideChunk[]           │
       │                      │  ElementChunk[]         │
       │                      ▼                        │
       │                  store.py                     │
       │                      │                        │
       │                      ▼                        │
       │                  retriever.py                 │
       │                      │                        │
       │                      │ SearchResult            │
       ▼                      ▼                        ▼
  ┌─────────────────────────────────────────────────────────┐
  │                     PHASE 4: AGENTS                      │
  │                                                          │
  │  nl_to_dsl.py                                            │
  │    reads: retriever (Phase 2) for example slides         │
  │    writes: DSL text validated by parser (Phase 1)        │
  │                                                          │
  │  qa_agent.py                                             │
  │    reads: rendered .pptx (Phase 3)                       │
  │    writes: pass/fail + revision DSL (Phase 1)            │
  │                                                          │
  │  index_curator.py                                        │
  │    reads: raw chunks from chunker (Phase 2)              │
  │    writes: semantic summaries back to store (Phase 2)    │
  └──────────────────────────┬───────────────────────────────┘
                             │
                             ▼
  ┌──────────────────────────────────────────────────────────┐
  │                  PHASE 5: ORCHESTRATION                   │
  │                                                          │
  │  orchestrator.py                                         │
  │    calls: retriever (P2) -> nl_to_dsl (P4) ->            │
  │           parser (P1) -> renderer (P3) -> qa_agent (P4)  │
  │                                                          │
  │  feedback.py                                             │
  │    reads: user signals (keep / edit / regen)             │
  │    writes: back to store (Phase 2) to close the loop     │
  │                                                          │
  │  skills/                                                 │
  │    thin wrappers over all src/ modules                   │
  └──────────────────────────────────────────────────────────┘
```

## How Phases Connect at Runtime

```
  User: "Q3 data platform update for leadership"
    │
    │                         ┌──────────────────────────────────────────┐
    │  STEP 1: Retrieve       │           PHASE 2                       │
    ├────────────────────────▶│  retriever.py queries store.py          │
    │                         │  returns: proven slide DSL examples      │
    │                         └─────────────────┬────────────────────────┘
    │                                           │
    │                                           │ examples
    │                                           ▼
    │  STEP 2: Generate       ┌──────────────────────────────────────────┐
    ├────────────────────────▶│           PHASE 4                       │
    │                         │  nl_to_dsl.py sends prompt + examples   │
    │                         │  to Claude, receives .sdsl text          │
    │                         └─────────────────┬────────────────────────┘
    │                                           │
    │                                           │ .sdsl text
    │                                           ▼
    │  STEP 3: Validate       ┌──────────────────────────────────────────┐
    ├────────────────────────▶│           PHASE 1                       │
    │                         │  parser.py validates DSL syntax          │
    │                         │  returns: PresentationNode               │
    │                         └─────────────────┬────────────────────────┘
    │                                           │
    │                                           │ PresentationNode
    │                                           ▼
    │  STEP 4: Render         ┌──────────────────────────────────────────┐
    ├────────────────────────▶│           PHASE 3                       │
    │                         │  pptx_renderer.py maps SlideNodes to     │
    │                         │  python-pptx shapes, outputs .pptx       │
    │                         └─────────────────┬────────────────────────┘
    │                                           │
    │                                           │ .pptx file
    │                                           ▼
    │  STEP 5: QA             ┌──────────────────────────────────────────┐
    ├────────────────────────▶│           PHASE 4                       │
    │                         │  qa_agent.py inspects rendered output    │
    │                         │  pass → deliver, fail → revise DSL      │
    │                         └─────────────────┬────────────────────────┘
    │                                           │
    │                                           │ delivered .pptx
    │                                           ▼
    │  STEP 6: Learn          ┌──────────────────────────────────────────┐
    └────────────────────────▶│           PHASE 5                       │
                              │  feedback.py records user signal         │
                              │  keep → boost in index (Phase 2)        │
                              │  edit → re-ingest edited version (P2)   │
                              │  regen → demote in index (Phase 2)      │
                              └──────────────────────────────────────────┘
```

## Phase Dependency Summary

```
  Phase 1 ◀── foundation, no dependencies
    │
    ├──▶ Phase 2 uses parser + serializer + models
    │       │
    ├──▶ Phase 3 uses models (SlideNode, BrandConfig)
    │       │
    │       ▼
    │    Phase 4 uses Phase 1 (parser validates output)
    │              uses Phase 2 (retriever provides examples)
    │              uses Phase 3 (qa_agent inspects rendered output)
    │       │
    │       ▼
    └──▶ Phase 5 calls all phases in sequence
                  and feeds signals back into Phase 2
```

What each phase gives to the others:

| Producer | Consumer | What flows between them |
|----------|----------|------------------------|
| Phase 1 | Phase 2 | `PresentationNode` for chunking, `serializer` for DSL text in chunks |
| Phase 1 | Phase 3 | `SlideNode`, `BrandConfig` drive rendering decisions |
| Phase 1 | Phase 4 | `parser` validates agent-generated DSL |
| Phase 2 | Phase 4 | `SearchResult` with proven DSL examples for few-shot prompts |
| Phase 2 | Phase 5 | `store` receives feedback signals from `feedback.py` |
| Phase 3 | Phase 4 | rendered `.pptx` for `qa_agent` visual inspection |
| Phase 4 | Phase 5 | DSL text output consumed by orchestrator pipeline |
| Phase 5 | Phase 2 | feedback loop: keep/edit/regen signals update chunk quality scores |

## Three-Level Chunking (Phase 2 Detail)

```
  ┌──────────────────────────────────────────────────────────────┐
  │  DECK CHUNK (1 per presentation)                              │
  │                                                               │
  │  title, author, company, slide_count                          │
  │  slide_type_sequence: [title, section, stat, two_col, ...]    │
  │  narrative_summary (LLM), audience, purpose                   │
  │  embedding -- searchable by arc, audience, topic              │
  │                                                               │
  │  ┌────────────────────────────────────────────────────────┐   │
  │  │  SLIDE CHUNK (1 per slide)                             │   │
  │  │                                                        │   │
  │  │  slide_name, slide_type, layout, background            │   │
  │  │  structural: has_stats(3), has_columns(2), ...         │   │
  │  │  neighborhood: prev=section_divider, next=two_column   │   │
  │  │  quality: keep=5, edit=1, regen=0 -- score=0.83        │   │
  │  │  dsl_text (full DSL for this slide)                    │   │
  │  │  embedding -- searchable by content, layout, shape     │   │
  │  │                                                        │   │
  │  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │   │
  │  │  │ ELEMENT      │ │ ELEMENT      │ │ ELEMENT      │   │   │
  │  │  │ stat "94%"   │ │ stat "3.2B"  │ │ stat "12"    │   │   │
  │  │  │ "Pipeline    │ │ "Events/Day" │ │ "Data        │   │   │
  │  │  │  Uptime"     │ │              │ │  Products"   │   │   │
  │  │  │ sibling: 3   │ │ sibling: 3   │ │ sibling: 3   │   │   │
  │  │  └──────────────┘ └──────────────┘ └──────────────┘   │   │
  │  └────────────────────────────────────────────────────────┘   │
  └──────────────────────────────────────────────────────────────┘
```

## File Tree by Phase

```
slidedsl/
│
├── PHASE 1 ─────────────────────────────────────
│   src/dsl/
│   ├── models.py              data models (PresentationNode, SlideNode)
│   ├── parser.py              .sdsl text --> PresentationNode
│   └── serializer.py          PresentationNode --> .sdsl text
│   tests/
│   └── test_parser.py         36 tests
│
├── PHASE 2 ─────────────────────────────────────
│   src/index/
│   ├── chunker.py             3-level chunking
│   ├── store.py               SQLite + FTS5 + vector BLOBs
│   └── retriever.py           hybrid search
│   scripts/
│   ├── ingest_deck.py         single deck ingestion
│   └── seed_index.py          batch ingestion
│   tests/
│   ├── test_chunker.py        30 tests
│   └── test_index.py          34 tests
│
├── PHASE 3 ─────────────────────────────────────
│   src/renderer/
│   ├── pptx_renderer.py       SlideNode --> python-pptx shapes
│   └── format_plugins.py      .pptx --> .ee4p / .pdf converters
│   tests/
│   └── test_renderer.py
│
├── PHASE 4 ─────────────────────────────────────
│   agents/
│   ├── nl_to_dsl.py           NL --> DSL agent (Claude)
│   ├── qa_agent.py            visual QA loop
│   ├── index_curator.py       semantic enrichment
│   └── prompts/
│       ├── nl_to_dsl.txt
│       ├── qa_inspection.txt
│       └── index_curation.txt
│
├── PHASE 5 ─────────────────────────────────────
│   src/services/
│   ├── orchestrator.py        end-to-end pipeline
│   └── feedback.py            learning loop
│   skills/
│   ├── dsl_parse.py           wraps parser
│   ├── dsl_serialize.py       wraps serializer
│   ├── chunk_slide.py         wraps chunker
│   ├── embed.py               embedding text generation
│   ├── index_search.py        wraps retriever + store
│   ├── render_pptx.py         wraps pptx_renderer
│   ├── template_analyze.py    .pptx template introspection
│   └── format_convert.py      wraps format_plugins
│
└── SHARED ──────────────────────────────────────
    docs/examples/sample.sdsl  test fixture (read-only)
    specs/*.md                 specifications (read-only)
    templates/                 company .pptx templates
```
