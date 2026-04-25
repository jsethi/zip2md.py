#!/usr/bin/env python3
"""
zip2md.py - v4
Advanced semantic, token-budgeted LLM context compiler with smart truncation and priority comments.
"""

import zipfile
import argparse
import os
import mimetypes
import sys
import re
import hashlib
import math
from datetime import datetime
from dataclasses import dataclass, field
from typing import Set, List, Dict, Optional, Tuple, Any

# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class Config:
    max_file_size: int = 10 * 1024 * 1024

    max_tokens: int = 120_000
    reserve_tokens: int = 8_000

    ignore_dirs: Set[str] = field(default_factory=lambda: {
        '.git', '.svn', 'node_modules', 'venv', '.venv', '__pycache__',
        '.idea', '.vscode', 'build', 'dist', 'out', 'target', 'vendor', '.next'
    })

    core_dirs: Set[str] = field(default_factory=lambda: {
        'src', 'app', 'apps', 'services', 'lib', 'core', 'internal', 'cmd', 'cmdline'
    })
    config_exts: Set[str] = field(default_factory=lambda: {
        '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.env',
        '.gitignore', '.dockerignore', '.editorconfig', '.prettierrc', '.eslintrc'
    })
    code_extensions: Set[str] = field(default_factory=lambda: {
        '.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.scss', '.md', '.txt',
        '.csv', '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.go', '.rs', '.rb',
        '.php', '.sh', '.mk', '.kt', '.swift', '.lua', '.tf', '.vue', '.dart',
        '.scala', '.bash', '.proto', '.graphql'
    })
    filename_whitelist: Set[str] = field(default_factory=lambda: {
        'dockerfile', 'makefile', 'gemfile', 'package.json', 'procfile'
    })
    entry_points: Set[str] = field(default_factory=lambda: {
        'main.py', 'app.py', 'index.ts', 'index.js', 'main.go', 'app.ts', 'cli.py',
        'server.ts', 'server.js', 'main.rs', 'lib.rs', 'manage.py', 'handler.py'
    })
    utility_keywords: Set[str] = field(default_factory=lambda: {
        'util', 'helper', 'tool', 'test', 'spec', 'mock', 'stub', 'bench', 'example'
    })

    section_summaries: Dict[str, str] = field(default_factory=lambda: {
        "1. Entry Points": "System entry and bootstrap files defining execution flow and initialization logic.",
        "2. Core Logic & Implementation": "Primary business logic, domain models, services, and runtime behavior. Highest reasoning value.",
        "3. Support & Utilities": "Helper functions, shared utilities, and supporting code.",
        "4. Configuration & Metadata": "Environment configuration, system descriptors, and build metadata."
    })

    section_order: List[str] = field(default_factory=lambda: [
        "1. Entry Points",
        "2. Core Logic & Implementation",
        "3. Support & Utilities",
        "4. Configuration & Metadata"
    ])


# ============================================================
# TERMINAL + HELPERS
# ============================================================

G = "\033[92m"; B = "\033[94m"; Y = "\033[93m"; R = "\033[0m"; BOLD = "\033[1m"

def init_terminal():
    if os.name == 'nt':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            try: os.system('')
            except Exception: pass

init_terminal()

def estimate_tokens(text: str) -> int:
    """Improved estimation (~3.6 chars per token for code-heavy text)."""
    return math.ceil(len(text) * 0.28)

# Optional: much more accurate if tiktoken is installed
try:
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    def estimate_tokens(text: str) -> int:
        return len(enc.encode(text, disallowed_special=()))
    print(f"{B}✓ Using tiktoken for precise token counting{R}")
except ImportError:
    pass


def get_zip_hash(zip_path: str) -> str:
    with open(zip_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def smart_truncate(content: str, max_chars: int, path: str) -> Tuple[str, bool]:
    """Keep beginning + end of file. Better for code (imports + main logic)."""
    if len(content) <= max_chars:
        return content, False

    lines = content.splitlines(keepends=True)
    total_lines = len(lines)

    if total_lines < 20:
        return content[:max_chars] + "\n\n... [TRUNCATED] ...", True

    keep_chars = max_chars - 120  # reserve space for marker
    half = keep_chars // 2

    head = ''.join(lines[:max(10, half // 80)])   # at least some lines
    tail = ''.join(lines[-max(10, half // 80):])

    # Fill remaining space proportionally
    remaining = keep_chars - len(head) - len(tail)
    if remaining > 100:
        mid_start = len(head) // 80 + 5
        mid = ''.join(lines[mid_start:mid_start + remaining // 80])
    else:
        mid = ""

    marker = f"\n\n... [TRUNCATED: token budget reached — kept ~{len(head)+len(tail)+len(mid)} chars of {len(content)}] ...\n\n"

    return head + marker + mid + tail, True


def extract_priority(content: str, filename: str) -> Tuple[Optional[int], bool]:
    """Look for # zip2md-priority: 300 or // zip2md-priority: 300 etc."""
    ext = os.path.splitext(filename)[1].lower()
    patterns = [
        r'(?i)#\s*zip2md-priority:\s*(\d+)',
        r'(?i)//\s*zip2md-priority:\s*(\d+)',
        r'(?i)/\*\s*zip2md-priority:\s*(\d+)\s*\*/',
        r'(?i)<!--\s*zip2md-priority:\s*(\d+)\s*-->',
    ]

    for pat in patterns:
        match = re.search(pat, content)
        if match:
            try:
                return int(match.group(1)), False
            except ValueError:
                pass

    # Check for full include
    full_pat = r'(?i)(zip2md-include:\s*full|zip2md-full)'
    if re.search(full_pat, content):
        return 1000, True  # very high priority + force full

    return None, False


# ============================================================
# FILE ANALYZER
# ============================================================

class FileAnalyzer:
    def __init__(self, config: Config):
        self.config = config

    def is_text_file(self, filename: str) -> bool:
        basename = os.path.basename(filename).lower()
        if basename in self.config.filename_whitelist or basename in self.config.entry_points:
            return True
        ext = os.path.splitext(filename)[1].lower()
        if ext in self.config.code_extensions or ext in self.config.config_exts:
            return True
        mime, _ = mimetypes.guess_type(filename)
        return mime and (mime.startswith('text/') or mime in {'application/json', 'application/javascript'})

    def should_ignore(self, filepath: str, exclude_pattern: Optional[str] = None, ignore_rules: Set[str] = None) -> bool:
        parts = filepath.replace('\\', '/').split('/')
        if any(p.lower() in self.config.ignore_dirs for p in parts):
            return True
        if ignore_rules and any(re.search(rule, filepath, re.IGNORECASE) for rule in ignore_rules):
            return True
        if exclude_pattern:
            try:
                if re.search(exclude_pattern, filepath, re.IGNORECASE):
                    return True
            except re.error:
                pass
        return False

    def get_category(self, filepath: str) -> str:
        basename = os.path.basename(filepath).lower()
        if basename in self.config.entry_points:
            return "1. Entry Points"
        ext = os.path.splitext(filepath)[1].lower()
        if ext in self.config.config_exts or basename in self.config.filename_whitelist:
            return "4. Configuration & Metadata"
        if any(kw in filepath.lower() for kw in self.config.utility_keywords):
            return "3. Support & Utilities"
        return "2. Core Logic & Implementation"

    def score_file(self, filepath: str, size: int, priority: Optional[int] = None) -> float:
        if priority is not None:
            return float(priority) + 1000.0  # manual priority dominates

        basename = os.path.basename(filepath).lower()
        filepath_lower = filepath.lower()
        parts = filepath_lower.replace('\\', '/').split('/')

        score = 0.0
        if basename in self.config.entry_points:
            score += 200.0
        if any(d in parts for d in self.config.core_dirs):
            score += 80.0
        ext = os.path.splitext(filepath)[1].lower()
        if ext in self.config.config_exts or basename in self.config.filename_whitelist:
            score += 30.0
        if any(kw in filepath_lower for kw in self.config.utility_keywords):
            score -= 40.0
        score += 20 * math.log(max(size, 1))
        return max(score, 0.0)


# ============================================================
# MARKDOWN EMITTER
# ============================================================

class MarkdownEmitter:
    def __init__(self, analyzer: FileAnalyzer, config: Config):
        self.analyzer = analyzer
        self.config = config

    def emit_package_header(self, zip_name: str, file_hash: str, stats: Dict[str, Any]) -> str:
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""# LLM Context Package | {zip_name} (v4)
> **Generated:** {date_str} | **Source Hash:** {file_hash}
> **Intent:** Token-budgeted, semantically ranked + priority-aware compilation for LLM reasoning.

## [0] System Overview & Metrics
| Metric | Value |
| :--- | :--- |
| Files Processed | {stats['processed']} |
| Total Raw Size | {stats['size_mb']:.2f} MB |
| Estimated Tokens | {stats['tokens_used']:,} / {stats['max_tokens']:,} ({stats['token_pct']:.1f}%) |
| Filtered / Ignored | {stats['ignored']} |
| Truncated Files | {stats.get('truncated_count', 0)} |

---

## [TOC] Table of Contents
"""

    def emit_toc(self, categories: Dict[str, List[Tuple]]) -> str:
        toc = ["### Sections & Files\n"]
        for cat_name in self.config.section_order:
            entries = categories.get(cat_name, [])
            if not entries:
                continue
            toc.append(f"**{cat_name}**")
            for entry, _ in entries:
                safe_path = entry.filename.replace(' ', '%20')
                toc.append(f"- [{entry.filename}](#file-{safe_path.replace('/', '-').replace('.', '-')})")
            toc.append("")
        toc.append("---\n")
        return "\n".join(toc)

    def emit_tree(self, file_paths: List[str]) -> str:
        tree = ["## [1] Included Repository Structure\n\n```text"]
        nodes: Dict[str, Any] = {}
        for path in file_paths:
            parts = path.split('/')
            curr = nodes
            for part in parts:
                curr = curr.setdefault(part, {})

        def render(node: Dict, indent: str = "") -> List[str]:
            lines = []
            keys = sorted(node.keys())
            for i, key in enumerate(keys):
                is_last = i == len(keys) - 1
                prefix = "└── " if is_last else "├── "
                lines.append(f"{indent}{prefix}{key}")
                if node[key]:
                    lines.extend(render(node[key], indent + ("    " if is_last else "│   ")))
            return lines

        tree.extend(render(nodes))
        tree.append("```\n\n---")
        return "\n".join(tree)

    def emit_section_header(self, category: str) -> str:
        summary = self.config.section_summaries.get(category, "")
        return f"## {category}\n\n> {summary}\n\n" if summary else f"## {category}\n\n"

    def emit_file_block(self, path: str, content: str, size: int, was_truncated: bool) -> str:
        size_kb = size / 1024
        fence = self.analyzer.get_safe_fence(content) if hasattr(self.analyzer, 'get_safe_fence') else "```"
        lang = self.analyzer.get_language(path) if hasattr(self.analyzer, 'get_language') else ""
        anchor = f"id=\"file-{path.replace('/', '-').replace('.', '-')}\""
        truncated_note = " *(truncated)*" if was_truncated else ""
        return f"### File: `{path}` ({size_kb:.1f} KB){truncated_note} <a {anchor}></a>\n{fence}{lang}\n{content}\n{fence}\n\n"


# ============================================================
# MAIN PIPELINE
# ============================================================

def zip_to_md(zip_path: str, output_md_path: str, config: Config, exclude_pattern: Optional[str] = None) -> None:
    analyzer = FileAnalyzer(config)
    emitter = MarkdownEmitter(analyzer, config)

    print(f"{B}{BOLD}📦 Compiling Context Package v4...{R}")

    if not zipfile.is_zipfile(zip_path):
        print(f"{Y}❌ Invalid zip file{R}", file=sys.stderr)
        sys.exit(1)

    try:
        file_hash = get_zip_hash(zip_path)

        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Load optional .zip2mdignore
            ignore_rules: Set[str] = set()
            try:
                ignore_info = zf.getinfo('.zip2mdignore')
                with zf.open(ignore_info) as f:
                    ignore_rules = {line.strip() for line in f.read().decode('utf-8', errors='replace').splitlines()
                                    if line.strip() and not line.startswith('#')}
            except KeyError:
                pass

            # Phase 1: Collect eligible files
            eligible = []
            total_raw_size = 0
            ignored_count = 0

            for entry in zf.infolist():
                if entry.is_dir(): 
                    continue
                if analyzer.should_ignore(entry.filename, exclude_pattern, ignore_rules):
                    ignored_count += 1
                    continue
                if not analyzer.is_text_file(entry.filename):
                    ignored_count += 1
                    continue
                if entry.file_size > config.max_file_size:
                    ignored_count += 1
                    continue
                eligible.append(entry)
                total_raw_size += entry.file_size

            if not eligible:
                print(f"{Y}⚠️ No eligible text files found{R}")
                return

            # Phase 2: Score with priority parsing
            scored_eligible = []
            for entry in eligible:
                with zf.open(entry) as f:
                    content = f.read().decode('utf-8', errors='replace')
                priority, force_full = extract_priority(content, entry.filename)
                score = analyzer.score_file(entry.filename, entry.file_size, priority)
                scored_eligible.append((score, entry, content, priority, force_full))

            scored_eligible.sort(key=lambda x: x[0], reverse=True)

            # Phase 3: Token-budgeted selection + smart truncation
            effective_budget = config.max_tokens - config.reserve_tokens
            selected = []
            used_tokens = 0
            truncated_count = 0
            forced_full = []

            for _, entry, content, priority, force_full in scored_eligible:
                if force_full and used_tokens + estimate_tokens(content) < config.max_tokens * 0.95:
                    selected.append((entry, content, False))
                    used_tokens += estimate_tokens(content)
                    forced_full.append(entry.filename)
                    continue

                tokens_needed = estimate_tokens(content)

                if used_tokens + tokens_needed <= effective_budget:
                    selected.append((entry, content, False))
                    used_tokens += tokens_needed
                else:
                    remaining = effective_budget - used_tokens
                    if remaining > 500:  # reasonable minimum
                        trunc_chars = int(remaining * 3.6)
                        truncated_content, was_truncated = smart_truncate(content, trunc_chars, entry.filename)
                        selected.append((entry, truncated_content, was_truncated))
                        used_tokens += estimate_tokens(truncated_content)
                        if was_truncated:
                            truncated_count += 1
                    break

            # Phase 4: Group by category (preserve section order)
            categories: Dict[str, List[Tuple]] = {cat: [] for cat in config.section_order}
            for entry, content, was_truncated in selected:
                cat = analyzer.get_category(entry.filename)
                categories[cat].append((entry, content, was_truncated))

            # Stats
            stats: Dict[str, Any] = {
                'processed': len(selected),
                'ignored': ignored_count,
                'size_mb': total_raw_size / (1024 * 1024),
                'tokens_used': used_tokens + config.reserve_tokens,
                'max_tokens': config.max_tokens,
                'token_pct': ((used_tokens + config.reserve_tokens) / config.max_tokens) * 100,
                'truncated_count': truncated_count
            }

        # Phase 5: Write output
        with open(output_md_path, 'w', encoding='utf-8') as md:
            md.write(emitter.emit_package_header(os.path.basename(zip_path), file_hash, stats))
            md.write(emitter.emit_toc(categories))
            md.write(emitter.emit_tree([e.filename for e, _, _ in selected]))

            for cat_name in config.section_order:
                entries = categories.get(cat_name, [])
                if not entries:
                    continue
                md.write(emitter.emit_section_header(cat_name))
                for entry, content, was_truncated in entries:
                    md.write(emitter.emit_file_block(entry.filename, content, entry.file_size, was_truncated))
                md.write("\n---\n")

        print(f"\n{G}{BOLD}✨ Done: {output_md_path}{R}")
        print(f"   → {stats['processed']} files | ~{stats['tokens_used']:,} tokens")
        if truncated_count:
            print(f"   → {truncated_count} file(s) smart-truncated")
        if forced_full:
            print(f"   → {len(forced_full)} file(s) forced full via priority comment")

    except Exception as e:
        print(f"\n{Y}❌ Error: {e}{R}", file=sys.stderr)
        sys.exit(1)


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="zip2md v4 — Advanced semantic LLM context compiler")
    parser.add_argument("zip_file")
    parser.add_argument("output", nargs="?")
    parser.add_argument("--exclude", help="Regex to exclude files")
    parser.add_argument("--max-tokens", type=int, default=120000)
    parser.add_argument("--reserve-tokens", type=int, default=8000)

    args = parser.parse_args()

    if not os.path.exists(args.zip_file):
        print(f"{Y}❌ Zip not found{R}", file=sys.stderr)
        sys.exit(1)

    config = Config(max_tokens=args.max_tokens, reserve_tokens=args.reserve_tokens)
    out_path = args.output or f"{os.path.splitext(os.path.basename(args.zip_file))[0]}_v4.md"

    zip_to_md(args.zip_file, out_path, config, args.exclude)
