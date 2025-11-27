# 🚀 Astro — Phase One Implementation Plan (Star Foundry Core)

## 1. Vision

Astro enables AI agents to intelligently navigate, retrieve, assemble, and execute modular prompts.  
In this universe:

- **Stars** = individual prompts
- **Star Foundry** = the registry where stars are loaded, validated, stored, and discovered
- **Probes** = tools Stars may reference to perform actions
- **Astro** = the full system including Foundry, Probes, agent interface, and future UI

### Phase One Goal

Create the **foundational backend architecture** for Astro:

✅ Load Stars from disk  
✅ Validate graph structure (no cycles, no missing references)  
✅ Store Stars in an in-memory registry with O(1) lookup  
✅ Enable retrieval by id, name, and tags  
✅ Support metadata and file-backed evolution  
✅ Provide a clean developer API and test suite

This phase does **not** include:
❌ Probes registry  
❌ UI, dashboards, visualization  
❌ SaaS hosting  
❌ Multi-user collaboration  
❌ Agent framework integrations

Phase One is about building the **Sky**, not flying through it.

---

## 2. Naming Scheme & Definitions

### Core Terms

| Term | Definition |
|------|-------------|
| Astro | The entire product ecosystem |
| Star Foundry | The prompt registry engine |
| Star | A single modular prompt node |
| Metadata | Human + machine-readable information about a Star |
| References | Directed edges to other Stars |
| Parents | Reverse edges computed by Foundry |
| Constellation *(future)* | A curated collection of Stars |
| Probe *(future)* | A callable tool referenced by Stars |

---

### Star ID Naming Standard



astro.{domain}.{topic}.{version}



Examples:


astro.ic.base.v1
astro.research.market.v2
astro.realestate.noi_calc.v1



Rules:
- globally unique
- semantic & descriptive
- version must increment when Star content changes

---

### Allowed File Formats

| Format | Purpose |
|--------|---------|
| `.md` | Markdown content with frontmatter metadata |
| `.xml` | Structured prompt formats |
| `.txt` | Raw text prompts (optional early support) |

---

## 3. Phase One File & Directory Structure

Develop repo like this:



astro/
star_foundry/
**init**.py
models/
star.py               # Star & StarMetadata models
loader/
star_loader.py        # Loads Stars from filesystem
parsers/
markdown_parser.py
xml_parser.py
registry/
star_registry.py      # In-memory registry
validator/
star_validator.py     # Missing refs, cycles, integrity
exceptions.py           # Custom exceptions
config.py               # Optional config defaults
tests/
unit/
test_star_model.py
test_loader.py
test_registry.py
test_validator.py
fixtures/
sample_stars/
base_star.md
financial_star.md
broken_star_missing_ref.md
cyclic_star_a.md
cyclic_star_b.md
examples/
load_and_query_foundry.py
scripts/
generate_star_graph.py  # optional future
pyproject.toml
README.md
CONTRIBUTING.md



---

## 4. Development Requirements

### ✅ Implement These Core Components

#### 1. `Star` and `StarMetadata` Models
- strict validation
- datetimes, tags, versioning, content type
- forbid extra fields to prevent drift

#### 2. `StarLoader`
- recursively scan a directory
- read `.md` & `.xml`
- return `list[Star]`

#### 3. Parsers
- Markdown frontmatter → metadata + content
- XML structured fields → metadata + content

#### 4. `StarRegistry`
- indexes:
  - id → Star
  - name → id
  - tag → set(ids)
- O(1) lookup
- public API:
  - `get_by_id`
  - `get_by_name`
  - `search_by_tag`
  - `all_metadata`

#### 5. `StarValidator`
- detect:
  - missing references
  - cyclic references
  - duplicate IDs
- populate `parents` on Stars

---

## 5. Testing Requirements

### Required Coverage
✅ **≥ 95% line coverage**  
✅ **100% coverage for critical logic:**
- validation
- registry indexing
- missing reference detection
- cycle detection

### Required Test Types

#### Unit Tests
- Star model validation
- metadata parsing
- loader behavior
- registry insertions, lookups
- validator logic
- tag indexing behavior

#### Edge Case Tests
- empty Foundry directory
- malformed metadata
- duplicate star IDs
- cyclic graph detection
- non-existent referenced star IDs
- mixed markdown + XML batch loading

#### Negative Tests
- missing required metadata fields
- invalid content_type values
- invalid datetime formats

---

## 6. GitHub Actions / CI Pipeline Setup

Create `.github/workflows/ci.yml`

### Required Steps

✅ Run `pytest`  
✅ Enforce 95% minimum coverage  
✅ Run `ruff` or `black` formatting  
✅ Run `mypy` for typing validation  
✅ Cache dependencies  
✅ Fail PR if coverage drops below threshold

Example pipeline stages:



jobs:
lint:
typecheck:
test:
coverage:

`

### Branch Protection Rules

- require passing tests before merge
- require 1 reviewer approval
- block merge if coverage < threshold

---

## 7. Config Setup (Phase One — Minimal)

Create `astro/star_foundry/config.py`

python
from pathlib import Path

DEFAULT_STAR_DIRECTORY = Path("./stars")
SUPPORTED_EXTENSIONS = {".md", ".xml"}
`

Allow overrides via environment variable:


STAR_FOUNDRY_PATH=./my_prompts


Later phases:

* TOML/YAML config support
* multiple sources
* remote registries

---

## 8. Deliverables Checklist (Developer Must Complete)

✅ Star & StarMetadata models
✅ Markdown & XML parsing utilities
✅ StarLoader implementation
✅ StarRegistry with indexing
✅ StarValidator with cycle + missing ref detection
✅ 95%+ tested codebase
✅ GitHub Actions pipeline
✅ Example usage script
✅ Documentation updates in README

---

## 9. Definition of Done (Phase One)

✅ Can run:

python
from astro.star_foundry import StarFoundry

foundry = StarFoundry("./stars")

foundry.get_by_id("astro.ic.base.v1")


✅ No missing or cyclic references
✅ Code fully typed + formatted
✅ Tests passing & ≥ 95% coverage
✅ Pipeline active + blocking PRs
✅ Developer onboarding requires < 10 min

---

## 10. Handoff Notes for Developer

* Optimize for clarity and maintainability — NOT speed
* Document function signatures with docstrings
* Avoid premature abstraction — v1 should be simple
* Expect that Probes, Constellations, Graph UI, SaaS hosting will follow later
* Communicate uncertainties before implementing assumptions

---

# ⭐️ Phase One Ends Here — Build the Sky

Once this foundation exists, Phase Two will focus on:

* Probe model + Probe Dock
* LangGraph tool integration
* CLI
* visualization
* packaging & publish to PyPI



---

If you'd like, I can also generate:

✅ onboarding instructions for new engineers  
✅ GitHub issues & task breakdown  
✅ first Stars directory w/ example files  
✅ fully written CI pipeline YAML  
✅ pytest config + coverage enforcement script  
✅ architectural diagram

Just tell me what you want.

