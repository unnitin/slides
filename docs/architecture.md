# SlideDSL -- Architecture

## Phase Dependency Graph

```mermaid
flowchart TD
    subgraph P1["**Phase 1: Core DSL**"]
        models["models.py"]
        parser["parser.py"]
        serializer["serializer.py"]
    end

    subgraph P2["**Phase 2: Design Index**"]
        chunker["chunker.py"]
        store["store.py"]
        retriever["retriever.py"]
    end

    subgraph P3["**Phase 3: Renderer**"]
        pptx_renderer["pptx_renderer.py"]
        format_plugins["format_plugins.py"]
    end

    subgraph P4["**Phase 4: Agents**"]
        direction TB
        nl_to_dsl["nl_to_dsl.py\n_reads: retriever for examples_\n_writes: DSL validated by parser_"]
        qa_agent["qa_agent.py\n_reads: rendered .pptx_\n_writes: QAReport pass/fail_\n_loop: inspect→fix→re-render (max 3)_"]
        index_curator["index_curator.py\n_reads: raw chunks from chunker_\n_writes: summaries back to store_\n_batches: one API call (Haiku)_"]
    end

    subgraph P5["**Phase 5: Orchestration**"]
        orchestrator["orchestrator.py\n_retriever→nl_to_dsl→parser→renderer→qa_agent_"]
        feedback["feedback.py\n_keep / edit / regen → store_"]
        skills["skills/\n_thin wrappers over all src/ modules_"]
    end

    models -->|"PresentationNode\nSlideNode"| chunker
    parser -->|"PresentationNode"| chunker
    serializer -->|"DSL text"| chunker
    chunker -->|"DeckChunk\nSlideChunk[]\nElementChunk[]"| store
    store --> retriever
    retriever -->|"SearchResult"| P4
    pptx_renderer -->|".pptx"| P4
    P4 --> P5
    feedback --> store
```

## User Flow (End-to-End)

```mermaid
flowchart TD
    user_input["👤 User: 'Q3 data platform update for leadership'"]

    subgraph orch["**ORCHESTRATOR** (src/services/orchestrator.py)"]
        direction TB
        step1["**Step 1: RETRIEVE**\nQuery design index at 3 granularities\n• Deck search → past quarterly structures\n• Slide search → proven stat/timeline slides\n• Element search → KPI presentations"]
        step2["**Step 2: GENERATE** (nl_to_dsl.py)\nBuild prompt: input + examples + brand\nCall Claude Sonnet → raw .sdsl\nRetry on parse failure (max 2)"]
        step3["**Step 3: VALIDATE** (parser.py)\nParse DSL → PresentationNode\nIf invalid after retries → partial result"]
        step4["**Step 4: RENDER** (pptx_renderer.py)\nMap SlideNodes to python-pptx shapes\nApply brand colors, fonts, backgrounds\nTemplate-based if available → .pptx"]
        step5["**Step 5: QA LOOP** (qa_agent.py)\n.pptx → PDF → JPEG (soffice + pdftoppm)\nSend images + DSL to Claude Sonnet (vision)\nCRITICAL: overlap, overflow, missing\nWARNING: alignment, contrast, spacing\nMINOR: monotony, excess whitespace"]
        step6["**Step 6: INGEST**\nChunk deck at 3 levels\nStore in design index (SQLite + vectors)\nRecord phrase triggers"]
        step7["**Step 7: DELIVER**\nReturn PipelineResult:\n.pptx path, .sdsl source,\nconfidence, QA status, deck_chunk_id"]

        step1 --> step2 --> step3 --> step4 --> step5
        step5 -->|PASS| step6 --> step7
        step5 -->|FAIL max 3x| step2
    end

    user_input --> orch

    step7 --> user_review["👤 User reviews slides"]

    user_review -->|"Keep as-is"| keep["feedback.record_keep(chunk_id)\n✅ Boost quality score"]
    user_review -->|"Edit then keep"| edit["feedback.record_edit(chunk_id, new_dsl)\n📝 Demote original, ingest edited"]
    user_review -->|"Reject / regenerate"| regen["feedback.record_regen(chunk_id)\n⬇️ Demote quality score"]
```

## QA Loop Detail

```mermaid
flowchart TD
    pptx[".pptx file"]
    convert["**pptx_to_images()**\nsoffice --headless --convert-to pdf\npdftoppm -jpeg -r 150"]
    images["slide-1.jpg, slide-2.jpg, ..."]
    inspect["**QAAgent.inspect()**\nBuild multi-modal message:\n• DSL source per slide\n• Base64-encoded image per slide\nSend to Claude Sonnet (vision)\nParse → QAReport"]
    report["QAReport\n• issues: [{slide_index, severity, category}]\n• passed: bool\n• summary: PASS or FAIL: N critical"]

    pptx --> convert --> images --> inspect --> report

    report -->|PASS| deliver["✅ Deliver"]
    report -->|FAIL| fix["Build fix prompt"]
    fix --> nl_to_dsl["NL-to-DSL Agent\n(with existing_dsl)"]
    nl_to_dsl --> rerender["Re-render .pptx"]
    rerender --> reinspect["Re-inspect (cycle++)\nmax 3 cycles"]
    reinspect --> inspect
```

## Index Curator Flow (Background)

```mermaid
flowchart TD
    ingest["New deck ingested\nchunker → DeckChunk + SlideChunks + ElementChunks"]

    subgraph curator["**IndexCuratorAgent** (Claude Haiku)"]
        direction TB
        enrich_deck["**enrich_deck(presentation)**\nnarrative_summary, audience,\npurpose, topic_tags"]
        enrich_slides["**enrich_slides_batch(slides, deck_context)**\nAll slides in ONE API call\nReturns JSON array of enrichments\nEach: semantic_summary + topic_tags + domain"]
        enrich_elements["**enrich_elements_batch(elements, slide_context)**\nAll elements in ONE API call\nEach: semantic_summary + topic_tags"]

        enrich_deck --> enrich_slides --> enrich_elements
    end

    store["**store.py** updates chunk metadata\n→ enables richer semantic search"]

    ingest --> curator --> store
```

## Phase Dependency Summary

```mermaid
flowchart TD
    P1["**Phase 1: Core DSL**\n_foundation, no dependencies_"]
    P2["**Phase 2: Design Index**\n_uses parser + serializer + models_"]
    P3["**Phase 3: Renderer**\n_uses models (SlideNode, BrandConfig)_"]
    P4["**Phase 4: Agents**\n_uses P1 (parser validates output)_\n_uses P2 (retriever provides examples)_\n_uses P3 (qa_agent inspects renders)_"]
    P5["**Phase 5: Orchestration**\n_calls all phases in sequence_"]

    P1 --> P2
    P1 --> P3
    P1 --> P4
    P2 --> P4
    P3 --> P4
    P4 --> P5
    P5 -->|"feedback signals"| P2
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
| Phase 4 | Phase 5 | DSL text + QAReport consumed by orchestrator pipeline |
| Phase 5 | Phase 2 | feedback loop: keep/edit/regen signals update chunk quality scores |

## Agent Contracts

| Agent | Model | Input | Output | API Calls |
|-------|-------|-------|--------|-----------|
| NL-to-DSL | claude-sonnet-4-5 | user text + retrieved examples | valid .sdsl text | 1 + up to 2 retries |
| QA Agent | claude-sonnet-4-5 | slide images + DSL source | QAReport (issues + pass/fail) | 1 per QA cycle (max 3) |
| Index Curator | claude-haiku-4-5 | chunk DSL text | JSON enrichments (summary, tags, domain) | 1 per deck (batched) |

Total per generation: ~4-7 API calls. Total per ingestion: ~1-2 API calls.

## Three-Level Chunking (Phase 2 Detail)

```mermaid
block-beta
    columns 1

    block:deck["DECK CHUNK (1 per presentation)"]
        columns 1
        deck_meta["title, author, company, slide_count\nslide_type_sequence: [title, section, stat, two_col, ...]\nnarrative_summary (LLM), audience, purpose\nembedding — searchable by arc, audience, topic"]

        block:slide["SLIDE CHUNK (1 per slide)"]
            columns 1
            slide_meta["slide_name, slide_type, layout, background\nstructural: has_stats(3), has_columns(2), ...\nneighborhood: prev=section_divider, next=two_column\nquality: keep=5, edit=1, regen=0 — score=0.83\ndsl_text, embedding — searchable by content, layout, shape"]

            block:elements
                columns 3
                e1["ELEMENT\nstat '94%'\nPipeline Uptime\nsibling: 3"]
                e2["ELEMENT\nstat '3.2B'\nEvents/Day\nsibling: 3"]
                e3["ELEMENT\nstat '12'\nData Products\nsibling: 3"]
            end
        end
    end
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
│   ├── nl_to_dsl.py           NL --> DSL agent (Claude Sonnet)
│   ├── qa_agent.py            visual QA loop (Claude Sonnet + vision)
│   ├── index_curator.py       semantic enrichment (Claude Haiku)
│   └── prompts/
│       ├── nl_to_dsl.txt      generation system prompt
│       ├── qa_inspection.txt  QA inspection system prompt
│       └── index_curation.txt curation system prompt
│   tests/
│   └── test_agents.py         25 tests
│
├── PHASE 5 ─────────────────────────────────────
│   src/services/
│   ├── orchestrator.py        end-to-end pipeline with QA loop
│   └── feedback.py            learning loop (keep/edit/regen)
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
