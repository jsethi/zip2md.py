"""
zip2md.py - A simple context compiler for LLM ingestion.
Transforms raw zip archives into structured, semantic "Cognition Packages".

Usage:
    python zip2md.py <path_to_zip_file> [output_file] [--exclude pattern]
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

# --- Configuration & Styling ---

@dataclass
class Config:
    max_file_size: int = 10 * 1024 * 1024  # 10 MB
    max_path_display: int = 50
    ignore_dirs: Set[str] = field(default_factory=lambda: {
        '.git', '.svn', 'node_modules', 'venv', '.venv', '__pycache__',
        '.idea', '.vscode', 'build', 'dist', 'out', 'target', 'vendor', '.next'
    })
    config_exts: Set[str] = field(default_factory=lambda: {
        '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.env', 
        '.gitignore', '.dockerignore', '.editorconfig', '.prettierrc', '.eslintrc'
    })
    code_extensions: Set[str] = field(default_factory=lambda: {
        '.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.scss',
        '.md', '.txt', '.csv', '.java', '.c', '.cpp', '.h', '.hpp', '.cs',
        '.go', '.rs', '.rb', '.php', '.sh', '.mk', '.kt', '.swift',
        '.lua', '.tf', '.vue', '.dart', '.scala', '.bash', '.proto', '.graphql'
    })
    filename_whitelist: Set[str] = field(default_factory=lambda: {
        'dockerfile', 'makefile', 'gemfile', 'package.json', 'procfile'
    })
    entry_points: Set[str] = field(default_factory=lambda: {
        'main.py', 'app.py', 'index.ts', 'index.js', 'main.go', 'app.ts', 'cli.py',
        'server.ts', 'server.js', 'main.rs', 'lib.rs', 'manage.py', 'handler.py'
    })
    # Keywords that suggest a file is a utility or supporting asset
    utility_keywords: Set[str] = field(default_factory=lambda: {
        'util', 'helper', 'tool', 'test', 'spec', 'mock', 'stub', 'bench', 'example'
    })

# ANSI Colors
G = "\033[92m"
B = "\033[94m"
Y = "\033[93m"
R = "\033[0m"
BOLD = "\033[1m"

def init_terminal():
    if os.name == 'nt':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            try:
                os.system('')
            except Exception:
                pass

init_terminal()

# --- Core Logic ---

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
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type and (mime_type.startswith('text/') or mime_type in {'application/json', 'application/javascript'})

    def should_ignore(self, filepath: str, custom_exclude: Optional[str] = None) -> bool:
        parts = filepath.replace('\\', '/').split('/')
        if any(p.lower() in self.config.ignore_dirs for p in parts):
            return True
        if custom_exclude:
            try:
                if re.search(custom_exclude, filepath):
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
        
        # Check for utility keywords in path or filename
        filepath_lower = filepath.lower()
        if any(kw in filepath_lower for kw in self.config.utility_keywords):
            return "3. Support & Utilities"
            
        return "2. Core Logic & Implementation"

    def get_language(self, filename: str) -> str:
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

    def get_safe_fence(self, content: str) -> str:
        matches = re.findall(r"`{3,}", content)
        max_len = max((len(m) for m in matches), default=3)
        return "`" * (max_len + 1)

class MarkdownEmitter:
    def __init__(self, analyzer: FileAnalyzer):
        self.analyzer = analyzer

    def emit_package_header(self, zip_name: str, file_hash: str, stats: Dict) -> str:
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""# LLM Context Package | {zip_name}
> **Generated:** {date_str} | **Source Hash:** {file_hash}
> **Intent:** This artifact is a compiled semantic representation of a codebase, optimized for high-context AI reasoning.

## [0] System Overview & Metrics
| Metric | Value |
| :--- | :--- |
| **Files Processed** | {stats['processed']} |
| **Total Context Size** | {stats['size_mb']:.2f} MB |
| **Filtering Delta** | {stats['ignored']} items removed |
| **Architecture Tree** | See Section [1] |

---
"""

    def emit_tree(self, file_paths: List[str]) -> str:
        tree = ["## [1] Repository Structure (Context Map)\n\n```text"]
        nodes = {}
        for path in file_paths:
            parts = path.split('/')
            curr = nodes
            for part in parts:
                if part not in curr:
                    curr[part] = {}
                curr = curr[part]
        
        def render(node, indent=""):
            lines = []
            sorted_keys = sorted(node.keys(), key=lambda k: (not bool(node[k]), k))
            for i, key in enumerate(sorted_keys):
                is_last = i == len(sorted_keys) - 1
                prefix = "└── " if is_last else "├── "
                lines.append(f"{indent}{prefix}{key}")
                new_indent = indent + ("    " if is_last else "│   ")
                lines.extend(render(node[key], new_indent))
            return lines

        tree.extend(render(nodes))
        tree.append("```\n\n---")
        return "\n".join(tree)

    def emit_file_block(self, path: str, content: str, size: int) -> str:
        size_kb = size / 1024
        fence = self.analyzer.get_safe_fence(content)
        lang = self.analyzer.get_language(path)
        return f"### File: `{path}` ({size_kb:.1f} KB)\n{fence}{lang}\n{content}\n{fence}\n\n"

def zip_to_md(zip_path: str, output_md_path: str, config: Config, exclude_pattern: Optional[str] = None) -> None:
    analyzer = FileAnalyzer(config)
    emitter = MarkdownEmitter(analyzer)
    
    print(f"{B}{BOLD}📦 Compiling Context Package from {zip_path}...{R}")
    
    if not zipfile.is_zipfile(zip_path):
        print(f"\n{Y}❌ Error: {zip_path} is not a valid zip file.{R}", file=sys.stderr)
        sys.exit(1)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            all_entries = [f for f in zip_ref.infolist() if not f.is_dir()]
            valid_entries = []
            total_size = 0
            
            for entry in all_entries:
                if not analyzer.should_ignore(entry.filename, exclude_pattern) and analyzer.is_text_file(entry.filename):
                    if entry.file_size <= config.max_file_size:
                        valid_entries.append(entry)
                        total_size += entry.file_size
            
            # Semantic Grouping
            categories = {
                "1. Entry Points": [],
                "2. Core Logic & Implementation": [],
                "3. Support & Utilities": [],
                "4. Configuration & Metadata": []
            }
            
            for entry in valid_entries:
                cat = analyzer.get_category(entry.filename)
                categories[cat].append(entry)
            
            # Ranking within categories (Anchor files first - largest size)
            for cat in categories:
                categories[cat].sort(key=lambda e: e.file_size, reverse=True)

            # Metadata
            with open(zip_path, 'rb') as f_zip:
                file_hash = hashlib.sha256(f_zip.read()).hexdigest()[:12]
            
            stats = {
                'processed': len(valid_entries),
                'ignored': len(all_entries) - len(valid_entries),
                'size_mb': total_size / (1024 * 1024)
            }

            with open(output_md_path, 'w', encoding='utf-8') as md_file:
                md_file.write(emitter.emit_package_header(os.path.basename(zip_path), file_hash, stats))
                md_file.write(emitter.emit_tree([e.filename for e in valid_entries]))
                
                for cat_name in sorted(categories.keys()):
                    entries = categories[cat_name]
                    if not entries: continue
                    
                    # Clean title for Markdown
                    clean_title = cat_name.split('. ', 1)[1] if '. ' in cat_name else cat_name
                    section_num = cat_name.split('. ', 1)[0] if '. ' in cat_name else "X"
                    
                    md_file.write(f"\n## [{section_num}] {clean_title}\n")
                    md_file.write(f"> This section contains {len(entries)} sorted by importance (file size).\n\n")
                    
                    for i, entry in enumerate(entries):
                        filepath = entry.filename
                        print(f"\r{B}Analysing {clean_title}: {i+1}/{len(entries)}{R} ...", end="", flush=True)
                        
                        with zip_ref.open(entry) as f:
                            raw_data = f.read()
                            content = raw_data.decode('utf-8', errors='replace')
                            md_file.write(emitter.emit_file_block(filepath, content, entry.file_size))
                    
                    md_file.write("\n---\n")
                        
        print(f"\n\n{G}{BOLD}✨ Context Compiler Finished: {output_md_path}{R}")

    except Exception as e:
        print(f"\n{Y}❌ Critical Error: {e}{R}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compile zip into a semantic context package for LLMs.")
    parser.add_argument("zip_file", help="Path to input zip")
    parser.add_argument("output", nargs="?", help="Optional: Output path")
    parser.add_argument("--exclude", help="Regex pattern to exclude files")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.zip_file):
        print(f"{Y}❌ Error: Zip not found.{R}", file=sys.stderr)
        sys.exit(1)
        
    out_path = args.output or f"{os.path.splitext(os.path.basename(args.zip_file))[0]}.md"
    zip_to_md(args.zip_file, out_path, Config(), args.exclude)
