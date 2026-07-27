# Skills System

## Overview

A skill represents WHAT an agent can do. Skills are modular, self-contained capabilities
that can be registered, discovered, selected, and executed by the agent runtime.

## Architecture

The skills system consists of five core components:

### 1. BaseSkill (Abstract Base Class)

All skills inherit from `BaseSkill` and must implement the `execute()` method.

```python
class BaseSkill(ABC):
    @property
    def metadata(self) -> SkillMetadata: ...
    async def execute(self, input_data: SkillInput) -> SkillOutput: ...
```

### 2. SkillMetadata

Each skill carries metadata describing its capabilities:

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Unique identifier |
| `description` | `str` | Human-readable description |
| `version` | `str` | Semantic version |
| `instructions` | `str` | System prompt for the skill |
| `input_schema` | `dict` | JSON Schema for input validation |
| `output_schema` | `dict` | JSON Schema for output validation |
| `allowed_tools` | `list[str]` | Tools this skill is permitted to use |
| `metadata` | `dict` | Free-form additional metadata |
| `enabled` | `bool` | Whether the skill is active |

### 3. SkillRegistry

In-memory registry that stores and retrieves skills by ID or name.
Supports register, get, list, enable/disable, and remove operations.

### 4. SkillLoader

Discovers and loads skills from built-in definitions and external packages.
- `load_builtins()` — loads the three built-in skills
- `discover_package(package_name)` — scans a Python package for BaseSkill subclasses

### 5. SkillSelector

Selects the most appropriate skill for a given task using a three-tier strategy:

1. **LLM-based selection** (requires LLM provider) — asks the LLM to choose
2. **Embedding similarity** (requires embedding provider) — cosine similarity matching
3. **Keyword fallback** — description similarity + keyword scoring

### 6. SkillExecutor

Executes a skill by name with lifecycle event emission and hook integration.
- Validates skill exists and is enabled
- Emits `skill_started` / `skill_completed` events
- Calls before/after hooks if hook manager is provided
- Returns `SkillOutput` with result, summary, and metadata

## Built-in Skills

### ResearchSkill
- **Purpose:** Research a topic and produce a structured summary
- **Allowed tools:** `web_search`
- **Input:** Research topic/question
- **Output:** Summary, key findings, source URLs

### DataAnalysisSkill
- **Purpose:** Analyze CSV/JSON data using safe Python execution
- **Allowed tools:** `python_executor`, `file_reader`
- **Input:** Analysis request + data path
- **Output:** Statistics, insights, visualizations

### CodeReviewSkill
- **Purpose:** Review source code for quality, bugs, and security
- **Allowed tools:** `file_reader`
- **Input:** File path, language, focus area
- **Output:** Issues list, quality score, recommendations

## API Endpoints

See [API Reference](api.md) for skills endpoints.

## Adding a New Skill

1. Create a new class inheriting from `BaseSkill`
2. Define `SkillMetadata` with name, description, version, and instructions
3. Implement the `execute()` method
4. Add the class to `BUILTIN_SKILLS` in `app/skills/loader.py`
5. Or register at runtime via `POST /api/v1/skills`
