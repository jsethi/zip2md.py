# zip2md.py

A lightweight, dependency-free tool that converts ZIP archives of
codebases into structured, LLM-optimized Markdown "context packages".

It is designed for deterministic, high-signal ingestion into LLMs (GPT,
Claude, local models), preserving full source fidelity while organizing
content by architectural role.

------------------------------------------------------------------------

## What it does

`zip2md.py` transforms a ZIP archive into a single Markdown document
containing:

-   Semantic code organization (entry points, core logic, utilities,
    configuration)
-   Repository structure tree for navigation
-   Full file contents with syntax highlighting
-   Noise filtering (e.g. node_modules, .git, build artifacts)
-   Deterministic output (stable ordering for reproducibility)
-   Source metadata (file count, size, SHA256 hash)

The output is optimized for LLM context ingestion rather than human
browsing.

------------------------------------------------------------------------

## Why this exists

LLMs perform better when context is:

-   Structured (not flat file dumps)
-   Filtered (no irrelevant noise)
-   Semantically grouped (not alphabetically ordered)
-   Deterministic (reproducible across runs)

This tool bridges raw code archives → LLM-ready context in a single
step.

------------------------------------------------------------------------

## Features

-   Single-file Markdown output (portable context artifact)
-   Semantic grouping of files by architectural role
-   Multi-language syntax highlighting (30+ languages)
-   Built-in ignore rules for common noise directories
-   Optional regex-based exclusion
-   Safe handling of encoding and large files
-   Repository tree visualization
-   SHA256 source fingerprinting
-   Zero external dependencies (stdlib only)

------------------------------------------------------------------------

## Installation

``` bash
git clone https://github.com/jsethi/zip2md.py.git
cd zip2md.py
```

No external dependencies required.

------------------------------------------------------------------------

## Usage

### Basic usage

``` bash
python zip2md.py myproject.zip
```

Output:

``` text
myproject.md
```

------------------------------------------------------------------------

### Custom output file

``` bash
python zip2md.py myproject.zip output.md
```

------------------------------------------------------------------------

### Exclude files by pattern

``` bash
python zip2md.py myproject.zip output.md --exclude "test_|__pycache__|\\.min\\.js"
```

------------------------------------------------------------------------

## Output structure

### Metadata header

-   Timestamp
-   Source hash (SHA256)
-   File statistics

### Repository tree

``` text
src/
├── main.py
├── app.py
config/
└── settings.json
```

### Categorized file sections

#### Entry Points

Core application entry files

#### Core Logic & Implementation

Primary business logic and system functionality

#### Support & Utilities

Helpers, tests, utilities, and scaffolding code

#### Configuration & Metadata

Config files and environment definitions

### File blocks

``` python
### File: src/main.py (5.2 KB)

def main():
    print("hello world")
```

------------------------------------------------------------------------

## Configuration

  Setting            Purpose
  ------------------ --------------------------------------
  ignore_dirs        Directories excluded from processing
  code_extensions    Recognized source code file types
  config_exts        Configuration / metadata file types
  entry_points       System entry files
  utility_keywords   Utility classification heuristics
  max_file_size      Maximum file size (default 10MB)

------------------------------------------------------------------------

## Design principles

-   Deterministic output
-   No external dependencies
-   Full fidelity preservation
-   LLM-first structure
-   Semantic organization

------------------------------------------------------------------------

## Limitations

-   Does not analyze or execute code
-   Binary files are ignored
-   Large repos may generate large outputs
-   Optimized for LLM consumption, not human reading

------------------------------------------------------------------------

## Example workflow

``` bash
zip -r project.zip ./src ./config package.json README.md
python zip2md.py project.zip
```

Feed output into:

-   LLM APIs (GPT, Claude)
-   RAG pipelines
-   Local models

------------------------------------------------------------------------

## License

MIT

------------------------------------------------------------------------

## Contributing

-   Add language support
-   Improve categorization
-   Optimize performance
-   Extend output formats
