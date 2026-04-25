"""
zip2md.py - A simple context compiler for LLM ingestion.
Transforms raw zip archives into structured, semantic "Cognition Packages".

DESIGN GOAL:
- Convert unstructured code archives into deterministic, LLM-friendly context
- Preserve architectural signal while filtering noise
- Maintain single-file output for maximum portability
"""

import zipfile
import argparse
import os
import mimetypes
import sys
import re
import hashlib
from datetime import datetime
from dataclasses import dataclass, field
from typing import Set, List, Dict, Optional, Tuple


# ============================================================
# CONFIGURATION LAYER (SYSTEM BEHAVIOR DEFINITION)
# ============================================================

@dataclass
class Config:
    """
    Central configuration object controlling:
    - filtering behavior
    - classification rules
    - structural heuristics

    This acts as a "context policy layer" for the compiler.
    """

    max_file_size: int = 10 * 1024 * 1024  # Hard safety cap (10MB per file)

    max_path_display: int = 50  # (currently unused but reserved for UI truncation)

    # Directories that are ALWAYS excluded (noise reduction layer)
    ignore_dirs: Set[str] = field(default_factory=lambda: {
        '.git', '.svn', 'node_modules', 'venv', '.venv', '__pycache__',
        '.idea', '.vscode', 'build', 'dist', 'out', 'target', 'vendor', '.next'
    })

    # Configuration / metadata file detection (high signal config surfaces)
    config_exts: Set[str] = field(default_factory=lambda: {
        '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.env',
        '.gitignore', '.dockerignore', '.editorconfig', '.prettierrc', '.eslintrc'
    })

    # Core code detection layer
    code_extensions: Set[str] = field(default_factory=lambda: {
        '.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.scss',
        '.md', '.txt', '.csv', '.java', '.c', '.cpp', '.h', '.hpp', '.cs',
        '.go', '.rs', '.rb', '.php', '.sh', '.mk', '.kt', '.swift',
        '.lua', '.tf', '.vue', '.dart', '.scala', '.bash', '.proto', '.graphql'
    })

    # Special-case file recognition (no extension but high semantic value)
    filename_whitelist: Set[str] = field(default_factory=lambda: {
        'dockerfile', 'makefile', 'gemfile', 'package.json', 'procfile'
    })

    # Entry points define system boundaries (highest architectural importance)
    entry_points: Set[str] = field(default_factory=lambda: {
        'main.py', 'app.py', 'index.ts', 'index.js', 'main.go', 'app.ts', 'cli.py',
        'server.ts', 'server.js', 'main.rs', 'lib.rs', 'manage.py', 'handler.py'
    })

    # Utility detection heuristics (used for secondary prioritization)
    utility_keywords: Set[str] = field(default_factory=lambda: {
        'util', 'helper', 'tool', 'test', 'spec', 'mock', 'stub', 'bench', 'example'
    })


# ============================================================
# TERMINAL INITIALIZATION (CROSS-PLATFORM SAFETY LAYER)
# ============================================================

G = "\033[92m"
B = "\033[94m"
Y = "\033[93m"
R = "\033[0m"
BOLD = "\033[1m"


def init_terminal():
    """
    Enables ANSI escape codes on Windows terminals.

    WHY:
    - Windows CMD does not always support ANSI colors by default
    - This ensures consistent UX across environments
    """
    if os.name == 'nt':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            # fallback: attempt shell mode enable
            try:
                os.system('')
            except Exception:
                pass


init_terminal()


# ============================================================
# FILE ANALYSIS ENGINE (SEMANTIC CLASSIFICATION LAYER)
# ============================================================

class FileAnalyzer:
    """
    Responsible for:
    - determining file relevance
    - categorizing semantic role
    - identifying encoding/language metadata
    """

    def __init__(self, config: Config):
        self.config = config

    # ------------------------------------------------------------
    # TEXT DETECTION (FILTERING GATE #1)
    # ------------------------------------------------------------
    def is_text_file(self, filename: str) -> bool:
        """
        Determines whether a file is safe/meaningful to include.

        Strategy:
        1. whitelist entry points / critical files
        2. extension-based classification
        3. MIME fallback detection
        """

        basename = os.path.basename(filename).lower()

        if basename in self.config.filename_whitelist or basename in self.config.entry_points:
            return True

        ext = os.path.splitext(filename)[1].lower()

        if ext in self.config.code_extensions or ext in self.config.config_exts:
            return True

        mime_type, _ = mimetypes.guess_type(filename)

        return mime_type and (
            mime_type.startswith('text/') or
            mime_type in {'application/json', 'application/javascript'}
        )

    # ------------------------------------------------------------
    # IGNORE LOGIC (NOISE FILTERING LAYER)
    # ------------------------------------------------------------
    def should_ignore(self, filepath: str, custom_exclude: Optional[str] = None) -> bool:
        """
        Determines whether file should be excluded.

        Applies:
        - directory-level exclusion
        - regex-based user exclusion
        """

        parts = filepath.replace('\\', '/').split('/')

        # Hard ignore directories (system-level noise)
        if any(p.lower() in self.config.ignore_dirs for p in parts):
            return True

        # User-defined exclusion (optional regex layer)
        if custom_exclude:
            try:
                if re.search(custom_exclude, filepath):
                    return True
            except re.error:
                pass  # invalid regex ignored safely

        return False

    # ------------------------------------------------------------
    # SEMANTIC CATEGORIZATION (ARCHITECTURAL LAYERING)
    # ------------------------------------------------------------
    def get_category(self, filepath: str) -> str:
        """
        Assigns file to semantic group for structured output.

        Priority:
        1. Entry Points (system roots)
        2. Config / Metadata
        3. Utilities (support logic)
        4. Core Logic (default)
        """

        basename = os.path.basename(filepath).lower()

        if basename in self.config.entry_points:
            return "1. Entry Points"

        ext = os.path.splitext(filepath)[1].lower()

        if ext in self.config.config_exts or basename in self.config.filename_whitelist:
            return "4. Configuration & Metadata"

        filepath_lower = filepath.lower()

        if any(kw in filepath_lower for kw in self.config.utility_keywords):
            return "3. Support & Utilities"

        return "2. Core Logic & Implementation"

    # ------------------------------------------------------------
    # LANGUAGE DETECTION (SYNTAX HINTING)
    # ------------------------------------------------------------
    def get_language(self, filename: str) -> str:
        """
        Maps file extension → Markdown code block language tag
        """

        ext = os.path.splitext(filename)[1].lower()

        ext_map = {
            '.py': 'python', '.js': 'javascript', '.jsx': 'jsx', '.ts': 'typescript',
            '.tsx': 'tsx', '.html': 'html', '.css': 'css', '.scss': 'scss',
            '.json': 'json', '.md': 'markdown', '.java': 'java', '.c': 'c',
            '.cpp': 'cpp', '.h': 'c', '.hpp': 'cpp', '.cs': 'csharp',
            '.go': 'go', '.rs': 'rust', '.rb': 'ruby', '.php': 'php',
            '.sh': 'bash', '.bash': 'bash', '.yaml': 'yaml', '.yml': 'yaml',
            '.xml': 'xml', '.sql': 'sql', '.bat': 'bat', '.ps1': 'powershell',
            '.kt': 'kotlin', '.swift': 'swift', '.lua': 'lua', '.tf': 'terraform',
            '.vue': 'vue', '.dart': 'dart', '.scala': 'scala', '.proto': 'protobuf',
            '.graphql': 'graphql'
        }

        return ext_map.get(ext, '')

    # ------------------------------------------------------------
    # SAFE CODE FENCE GENERATION
    # ------------------------------------------------------------
    def get_safe_fence(self, content: str) -> str:
        """
        Prevents Markdown breakage by ensuring code fences
        are longer than any existing backtick sequence.
        """

        matches = re.findall(r"`{3,}", content)
        max_len = max((len(m) for m in matches), default=3)

        return "`" * (max_len + 1)


# ============================================================
# MARKDOWN EMISSION LAYER (OUTPUT FORMATTING ENGINE)
# ============================================================

class MarkdownEmitter:
    """
    Responsible for transforming structured analysis
    into deterministic Markdown output.
    """

    def __init__(self, analyzer: FileAnalyzer):
        self.analyzer = analyzer

    # ------------------------------------------------------------
    # PACKAGE HEADER (GLOBAL CONTEXT METADATA)
    # ------------------------------------------------------------
    def emit_package_header(self, zip_name: str, file_hash: str, stats: Dict) -> str:
        """
        Generates top-level cognitive summary header.
        """

        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return f"""# LLM Context Package | {zip_name}
> **Generated:** {date_str} | **Source Hash:** {file_hash}
> **Intent:** Semantic compilation optimized for LLM reasoning.

## [0] System Overview & Metrics
| Metric | Value |
| :--- | :--- |
| Files Processed | {stats['processed']} |
| Context Size | {stats['size_mb']:.2f} MB |
| Filtered Items | {stats['ignored']} |

---
"""

    # ------------------------------------------------------------
    # REPOSITORY TREE (STRUCTURAL MAP)
    # ------------------------------------------------------------
    def emit_tree(self, file_paths: List[str]) -> str:
        """
        Builds hierarchical tree representation of archive.
        """

        tree = ["## [1] Repository Structure\n\n```text"]

        nodes = {}

        # Build nested dictionary tree
        for path in file_paths:
            parts = path.split('/')
            curr = nodes
            for part in parts:
                curr = curr.setdefault(part, {})

        def render(node, indent=""):
            lines = []
            for i, key in enumerate(sorted(node.keys())):
                is_last = i == len(node) - 1
                prefix = "└── " if is_last else "├── "
                lines.append(f"{indent}{prefix}{key}")
                lines.extend(render(node[key], indent + ("    " if is_last else "│   ")))
            return lines

        tree.extend(render(nodes))
        tree.append("```\n\n---")

        return "\n".join(tree)

    # ------------------------------------------------------------
    # FILE BLOCK EMISSION (CORE OUTPUT UNIT)
    # ------------------------------------------------------------
    def emit_file_block(self, path: str, content: str, size: int) -> str:
        """
        Converts a single file into structured Markdown block.
        """

        size_kb = size / 1024
        fence = self.analyzer.get_safe_fence(content)
        lang = self.analyzer.get_language(path)

        return (
            f"### File: `{path}` ({size_kb:.1f} KB)\n"
            f"{fence}{lang}\n"
            f"{content}\n"
            f"{fence}\n\n"
        )


# ============================================================
# MAIN COMPILATION PIPELINE (ORCHESTRATION LAYER)
# ============================================================

def zip_to_md(zip_path: str, output_md_path: str, config: Config, exclude_pattern: Optional[str] = None) -> None:
    """
    Primary orchestration function.

    Flow:
    1. Validate zip
    2. Scan files
    3. Filter noise
    4. Categorize
    5. Emit structured Markdown
    """

    analyzer = FileAnalyzer(config)
    emitter = MarkdownEmitter(analyzer)

    print(f"{B}{BOLD}📦 Compiling Context Package...{R}")

    if not zipfile.is_zipfile(zip_path):
        print(f"\n{Y}❌ Invalid zip file{R}", file=sys.stderr)
        sys.exit(1)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:

            # ------------------------------------------------------------
            # FILE DISCOVERY PHASE
            # ------------------------------------------------------------
            all_entries = [f for f in zip_ref.infolist() if not f.is_dir()]
            valid_entries = []
            total_size = 0

            for entry in all_entries:

                if analyzer.should_ignore(entry.filename, exclude_pattern):
                    continue

                if not analyzer.is_text_file(entry.filename):
                    continue

                if entry.file_size <= config.max_file_size:
                    valid_entries.append(entry)
                    total_size += entry.file_size

            # ------------------------------------------------------------
            # SEMANTIC GROUPING PHASE
            # ------------------------------------------------------------
            categories = {
                "1. Entry Points": [],
                "2. Core Logic & Implementation": [],
                "3. Support & Utilities": [],
                "4. Configuration & Metadata": []
            }

            for entry in valid_entries:
                categories[analyzer.get_category(entry.filename)].append(entry)

            # ------------------------------------------------------------
            # STABLE SORTING (DETERMINISM)
            # ------------------------------------------------------------
            for cat in categories:
                categories[cat].sort(key=lambda e: e.file_size, reverse=True)

            # ------------------------------------------------------------
            # FILE HASHING (REPRODUCIBILITY METADATA)
            # ------------------------------------------------------------
            with open(zip_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()[:12]

            stats = {
                'processed': len(valid_entries),
                'ignored': len(all_entries) - len(valid_entries),
                'size_mb': total_size / (1024 * 1024)
            }

            # ------------------------------------------------------------
            # OUTPUT WRITING PHASE (SINGLE FILE GUARANTEE)
            # ------------------------------------------------------------
            with open(output_md_path, 'w', encoding='utf-8') as md_file:

                md_file.write(emitter.emit_package_header(
                    os.path.basename(zip_path),
                    file_hash,
                    stats
                ))

                md_file.write(emitter.emit_tree([e.filename for e in valid_entries]))

                # SECTION EMISSION LOOP
                for cat_name, entries in categories.items():

                    if not entries:
                        continue

                    md_file.write(f"\n## {cat_name}\n\n")

                    for i, entry in enumerate(entries):

                        print(f"\rProcessing {cat_name}: {i+1}/{len(entries)}", end="", flush=True)

                        with zip_ref.open(entry) as f:
                            content = f.read().decode('utf-8', errors='replace')

                        md_file.write(
                            emitter.emit_file_block(
                                entry.filename,
                                content,
                                entry.file_size
                            )
                        )

                    md_file.write("\n---\n")

        print(f"\n\n{G}{BOLD}✨ Done: {output_md_path}{R}")

    except Exception as e:
        print(f"\n{Y}❌ Error: {e}{R}", file=sys.stderr)
        sys.exit(1)


# ============================================================
# CLI ENTRYPOINT
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Compile zip into LLM context package")

    parser.add_argument("zip_file")
    parser.add_argument("output", nargs="?")
    parser.add_argument("--exclude")

    args = parser.parse_args()

    if not os.path.exists(args.zip_file):
        print(f"{Y}❌ Zip not found{R}", file=sys.stderr)
        sys.exit(1)

    out_path = args.output or f"{os.path.splitext(os.path.basename(args.zip_file))[0]}.md"

    zip_to_md(args.zip_file, out_path, Config(), args.exclude)
