# CLAUDE.md — Instructions for Claude Code

## Project Overview

You are building **SlideDSL**, an agentic slide generation platform. Read ALL spec
files in `specs/` before writing any code. The specs are the source of truth.

## Build Order

Follow this order strictly. Each step depends on the previous.

### Phase 1: Core DSL (do this first)
1. Read `specs/DSL_SPEC.md` — understand the grammar
2. Build `src/dsl/models.py` — Pydantic data models
3. Build `src/dsl/parser.py` — DSL text → PresentationNode
4. Build `src/dsl/serializer.py` — PresentationNode → DSL text
5. Write `tests/test_parser.py` — parse the sample in `docs/examples/sample.sdsl`
6. Verify: `pytest tests/test_parser.py` must pass

### Phase 2: Design Index
1. Read `specs/INDEX_SPEC.md` — understand multi-granularity chunking
2. Build `src/index/chunker.py` — chunk slides at 3 granularities
3. Build `src/index/store.py` — SQLite metadata + vector embeddings
4. Build `src/index/retriever.py` — semantic + structural search
5. Write `tests/test_chunker.py` and `tests/test_index.py`
6. Build `scripts/ingest_deck.py` — ingest existing .pptx into the index
7. Build `scripts/seed_index.py` — bootstrap from a directory of decks

### Phase 3: Renderer
1. Read `specs/RENDERER_SPEC.md` — understand rendering rules
2. Build `src/renderer/pptx_renderer.py` — SlideNode → .pptx
3. Build `src/renderer/format_plugins.py` — plugin system for .ee4p etc.
4. Write `tests/test_renderer.py`

### Phase 4: Agents
1. Read `specs/AGENT_SPEC.md` — understand agent contracts
2. Build `agents/prompts/nl_to_dsl.txt` — system prompt
3. Build `agents/nl_to_dsl.py` — NL → DSL translation agent
4. Build `agents/qa_agent.py` — visual QA loop
5. Build `agents/index_curator.py` — background index enrichment

### Phase 5: Orchestration
1. Build `src/services/orchestrator.py` — end-to-end pipeline
2. Build `src/services/feedback.py` — feedback loop to index
3. Build `skills/` wrappers — thin skill files that compose src modules

## Key Technical Decisions

- **Python 3.11+** — use modern typing, dataclasses, match statements
- **Pydantic v2** for all data models
- **SQLite** for the design index metadata (portable, zero-config)
- **numpy** for vector operations; no heavy vector DB dependency yet
- **python-pptx** for rendering (not pptxgenjs — keep it pure Python)
- **Anthropic SDK** for LLM calls (Claude claude-sonnet-4-5-20250514 for agents)
- **No frameworks** for orchestration yet — simple Python async, no LangChain/LangGraph

## Code Style

- Type hints on everything
- Docstrings on all public methods (Google style)
- `dataclass` for simple data, `pydantic.BaseModel` for validated/serialized data
- Keep files under 400 lines — split if longer
- Tests use `pytest` with descriptive names: `test_parser_handles_missing_frontmatter`

## Environment

```bash
pip install -e ".[dev]"
pytest                    # run all tests
python -m slidedsl parse docs/examples/sample.sdsl   # smoke test
```

## Critical Patterns

### The DSL is the contract
Everything flows through SlideDSL text. The LLM generates DSL, the parser validates it,
the renderer consumes it. Never bypass the DSL with direct LLM→PPTX generation.

### Multi-granularity chunking
The design index chunks at THREE levels (see INDEX_SPEC.md):
  1. **Deck-level** — narrative arc, audience, purpose
  2. **Slide-level** — individual slide semantics, layout, content type
  3. **Element-level** — specific charts, stats, visual treatments

All three levels get embedded and are searchable independently.

### Feedback loop
Every generated deck produces feedback signals:
  - User kept slide as-is → boost that design in the index
  - User regenerated → demote
  - User edited then kept → index the edited version as a new entry

### Template awareness
The renderer never generates slides from scratch if a company template exists.
It always maps content to template layouts first, falling back to generation only
for content types the template doesn't cover.

## Files You Should NOT Modify

- `specs/*.md` — these are the specs, treat as read-only requirements
- `docs/examples/sample.sdsl` — this is the test fixture
- `CLAUDE.md` — this file

## When In Doubt

1. Re-read the relevant spec file
2. Write a test first
3. Keep it simple — this is a v1, not a final product
4. Prefer explicit over clever
