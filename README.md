# zip2md.py

A simple context compiler for LLM ingestion. Transforms raw zip archives into structured, semantic "Cognition Packages" optimized for AI reasoning.

## What It Does

`zip2md.py` takes messy source code repositories (typically in ZIP format) and produces a single, carefully curated Markdown document containing:

- **Architecture-aware categorization** – Files organized by semantic role (entry points, core logic, utilities, config)
- **Deterministic output** – Same input always produces identical output (useful for reproducibility)
- **Noise filtering** – Automatically excludes common cruft (node_modules, .git, __pycache__, etc.)
- **Multi-language support** – Handles code in Python, JavaScript, TypeScript, Go, Rust, Java, C++, and 20+ other languages
- **Markdown-friendly** – Safe handling of edge cases (nested code fences, special characters, large files)

## Why?

LLMs work best with structured, semantically organized context. This tool bridges the gap between raw archives and AI-friendly input by:

1. **Reducing noise** – Filters ignored directories and non-code files
2. **Organizing by intent** – Groups files by architectural role, not just alphabetically
3. **Preserving portability** – Single-file output (easy to version, share, or feed to any LLM API)
4. **Enabling reproducibility** – Includes source hash and processing stats

## Installation

Simply download or clone the repository:

```bash
git clone https://github.com/jsethi/zip2md.py.git
cd zip2md.py
```

No external dependencies required—uses only Python's standard library.

## Usage

### Basic Usage

```bash
python zip2md.py myproject.zip
```

This generates `myproject.md` in the current directory.

### Custom Output Path

```bash
python zip2md.py myproject.zip output.md
```

### Exclude Files by Pattern

Use a regex pattern to exclude additional files:

```bash
python zip2md.py myproject.zip output.md --exclude "test_|__pycache__|\.min\.js"
```

This excludes files matching the pattern (e.g., test files, minified JS).

## How It Works

### 1. **Configuration Layer**

The `Config` dataclass defines:
- **Ignored directories** – Set of folder names always excluded (.git, node_modules, etc.)
- **Code extensions** – File types to include (.py, .js, .ts, etc.)
- **Config files** – Special metadata files (package.json, Dockerfile, etc.)
- **Entry points** – Files signifying system boundaries (main.py, app.ts, etc.)
- **Utility keywords** – Heuristics for secondary categorization (test, util, helper, etc.)

### 2. **File Analysis Engine**

The `FileAnalyzer` class determines:
- **Is it text?** – Multi-layer detection (whitelist → extension → MIME type)
- **Should we ignore it?** – Directory checks + optional regex exclusion
- **What category?** – Entry Points → Config → Utilities → Core Logic
- **What language?** – Maps file extensions to Markdown syntax highlighting

### 3. **Markdown Emission**

The `MarkdownEmitter` class produces:
- **Package header** – Timestamp, source hash, processing stats
- **Repository tree** – Hierarchical directory structure for quick navigation
- **File blocks** – Syntax-highlighted code sections with metadata

### 4. **Main Pipeline**

The `zip_to_md()` orchestration function:
1. Validates the ZIP archive
2. Discovers and filters files
3. Categorizes by semantic role
4. Sorts deterministically (by file size, reversed)
5. Writes single Markdown output with stats

## Output Format

Each generated Markdown document includes:

```
# LLM Context Package | myproject.zip
> Generated: 2026-04-25 14:32:15 | Source Hash: a1b2c3d4e5f6

## [0] System Overview & Metrics
| Metric | Value |
| Files Processed | 42 |
| Context Size | 2.34 MB |
| Filtered Items | 156 |

---

## [1] Repository Structure
```text
├── src/
│   ├── main.py
│   └── app.py
├── config/
│   └── settings.json
...
```

## [1] Entry Points
### File: `src/main.py` (5.2 KB)
```python
...code content...
```

## [2] Core Logic & Implementation
...

## [3] Support & Utilities
...

## [4] Configuration & Metadata
...
```

## Configuration Reference

Edit the `Config()` dataclass in the code to customize behavior:

| Setting | Default | Purpose |
| --- | --- | --- |
| `max_file_size` | 10 MB | Skip files larger than this |
| `ignore_dirs` | `.git, node_modules, ...` | Directories to always exclude |
| `code_extensions` | `.py, .js, .ts, ...` | File types considered "code" |
| `config_exts` | `.json, .yaml, .toml, ...` | Config/metadata file patterns |
| `entry_points` | `main.py, app.ts, ...` | Files marking system roots |
| `utility_keywords` | `test, util, helper, ...` | Keywords triggering utility categorization |

## Design Principles

- **Single file output** – No directory structures; one Markdown file for portability
- **Deterministic** – SHA256 hash ensures reproducibility; stable sorting prevents randomness
- **Extensible config** – All behavior controlled by centralized `Config` object
- **Semantic organization** – Files grouped by architectural role, not lexical order
- **Safe encoding** – Handles UTF-8 errors gracefully; auto-adjusts code fence length
- **Cross-platform** – Windows, macOS, Linux support (ANSI color handling included)

## Example Workflow

```bash
# Create a ZIP of your project
zip -r myproject.zip ./src ./config README.md package.json

# Compile to LLM context
python zip2md.py myproject.zip

# Feed to Claude/GPT/etc.
# (The generated myproject.md is now ready for LLM ingestion)
```

## Features

✅ Multi-language syntax highlighting  
✅ Automatic noise filtering  
✅ Semantic file categorization  
✅ Deterministic, reproducible output  
✅ Source hash for integrity verification  
✅ Hierarchical repository tree  
✅ Safe handling of edge cases (encoding, special chars)  
✅ Cross-platform color output  
✅ Zero external dependencies  

## License

MIT

## Contributing

Contributions welcome! Feel free to fork, modify, and submit improvements.

## Contact

For questions or feedback, open an issue on the GitHub repository.
