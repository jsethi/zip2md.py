# zip2md.py

**v4.1**  Advanced semantic token-budgeted LLM context compiler for ZIP archives.

A lightweight, dependency-free tool that converts codebases (packaged as ZIP) into clean, structured, high-signal Markdown files optimized for LLMs like Claude, Grok, GPT, and Gemini.

------------------------------------------------------------------------

## What it does

`zip2md.py` takes a ZIP archive and produces a single Markdown document that is:

- Semantically organized by architectural importance
- Token-budget aware with smart truncation
- Enriched with priority comments and a navigable Table of Contents
- Filtered from common noise (build dirs, caches, etc.)
- Reproducible via source hash and stable ordering

Perfect for feeding large projects into LLMs without wasting context tokens.

------------------------------------------------------------------------

## Key Features (v4.1)

- **Smart Truncation**: Keeps the beginning (imports/structure) + end (main logic) of files when hitting token limits
- **Priority Comments**: Control inclusion order and force full files with:
  - `# zip2md-priority: 450`
  - `// zip2md-include: full`
- **Improved Table of Contents** with direct links to every file
- Semantic grouping: Entry Points → Core Logic → Utilities → Configuration
- Repository tree visualization
- `.zip2mdignore` support (like .gitignore)
- Safe code fences and multi-language syntax highlighting
- Detailed statistics and SHA256 source hash
- Zero external dependencies (optional `tiktoken` for better token counting)

------------------------------------------------------------------------

## Installation

```bash
git clone https://github.com/jsethi/zip2md.py.git
cd zip2md.py
```

No dependencies required (Python 3.8+).

------------------------------------------------------------------------

## Usage

### Basic

```bash
python zip2md.py myproject.zip
```

Creates: `myproject_v4.md`

### Custom output

```bash
python zip2md.py myproject.zip mycontext.md
```

### Advanced options

```bash
python zip2md.py project.zip --max-tokens 200000 --exclude "test_|\\.min\\."
```

------------------------------------------------------------------------

## Priority Comments (New in v4)

Add near the top of important files:

```python
# zip2md-priority: 500        # Higher number = stronger priority
```

```typescript
// zip2md-include: full        # Try to keep this file completely
```

------------------------------------------------------------------------

## Output Structure

1. **System Overview & Metrics** – token usage, file count, hash
2. **Table of Contents** – clickable links
3. **Repository Structure** – tree view of included files
4. Categorized sections with helpful summaries
5. Individual file blocks with syntax highlighting and truncation indicators

------------------------------------------------------------------------

## Example Workflow

```bash
# Package your project
zip -r project.zip ./src ./app config/ package.json

# Generate LLM-ready context
python zip2md.py project.zip

# Paste the resulting .md into your LLM
```

------------------------------------------------------------------------

## Design Principles

- Maximum reasoning value per token
- Semantic importance over file name order
- Graceful degradation when hitting context limits
- Reproducible and deterministic output
- LLM-first, human-readable when needed

------------------------------------------------------------------------

## Limitations

- Binary files are ignored
- Does not execute or analyze code logic
- Very large repositories may still require manual token tuning
- Optimized primarily for LLM ingestion

------------------------------------------------------------------------

## License

MIT

------------------------------------------------------------------------

## Contributing

Welcome! Possible improvements:
- Directory input support (no zip needed)
- Auto-generated file summaries
- More intelligent truncation strategies
- Additional output formats

---

**Created to make feeding real codebases into LLMs fast and effective.**
