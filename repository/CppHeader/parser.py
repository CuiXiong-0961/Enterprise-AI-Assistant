"""
从 C++ 头文件中抽取可检索片段（声明 + 紧邻 Doxygen 块），供 ``CppHeaderMetadata`` 与向量入库。

规则为启发式，面向本仓库 ``RAG-corpus/Bugs`` 风格；不保证覆盖所有 ISO C++ 语法。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .constants import MAX_EMBED_CHARS


@dataclass
class HeaderChunk:
    """单条入库单元：一段用于 embedding 的正文 + 符号信息。"""

    text: str
    symbol_name: str
    symbol_kind: str
    signature: str | None
    chunk_index: int


def _strip_include_guard(text: str) -> str:
    """去掉最外层 #ifndef/#define/#endif，保留中间内容。"""
    lines = text.splitlines()
    if not lines:
        return text
    if lines[0].strip().startswith("#ifndef"):
        depth = 0
        out: list[str] = []
        for line in lines[1:]:
            s = line.strip()
            if s.startswith("#if"):
                depth += 1
            elif s.startswith("#endif"):
                if depth == 0:
                    break
                depth -= 1
            out.append(line)
        return "\n".join(out).strip()
    return text


def _find_matching_brace(text: str, open_idx: int) -> int | None:
    """``open_idx`` 指向 ``{``，返回匹配的 ``}`` 下标；失败返回 None。"""
    depth = 0
    i = open_idx
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def _preceding_block_comment(text: str, start: int, max_scan: int = 800) -> str:
    """取 start 之前最近的 ``/** ... */``（不含）。"""
    window = text[max(0, start - max_scan) : start]
    m = None
    for m in re.finditer(r"/\*\*(.*?)\*/", window, re.DOTALL):
        pass
    if m:
        return m.group(0).strip()
    return ""


def _truncate(s: str) -> str:
    s = s.strip()
    if len(s) <= MAX_EMBED_CHARS:
        return s
    return s[: MAX_EMBED_CHARS - 3] + "..."


def parse_header_file(path: Path, *, rel_file_name: str) -> list[HeaderChunk]:
    raw = path.read_text(encoding="utf-8")
    body = _strip_include_guard(raw)
    chunks: list[HeaderChunk] = []
    idx = 0

    def push(
        text: str,
        symbol_name: str,
        symbol_kind: str,
        signature: str | None,
    ) -> None:
        nonlocal idx
        t = _truncate(text)
        if len(t) < 8:
            return
        chunks.append(
            HeaderChunk(
                text=t,
                symbol_name=symbol_name,
                symbol_kind=symbol_kind,
                signature=signature,
                chunk_index=idx,
            )
        )
        idx += 1

    # --- enum class Name ... { ... };
    for m in re.finditer(
        r"\benum\s+class\s+(\w+)\s*(?::\s*[\w\s]+)?\s*\{",
        body,
    ):
        name = m.group(1)
        brace_open = m.end() - 1
        close = _find_matching_brace(body, brace_open)
        if close is None:
            continue
        block_end = body.find(";", close)
        if block_end == -1:
            block_end = close + 1
        else:
            block_end += 1
        snippet = body[m.start() : block_end]
        comment = _preceding_block_comment(body, m.start())
        full = f"{comment}\n{snippet}".strip() if comment else snippet
        push(full, name, "enum_class", f"enum class {name}")

    # --- struct Name { ... };
    for m in re.finditer(r"\bstruct\s+(\w+)\s*\{", body):
        name = m.group(1)
        brace_open = m.end() - 1
        close = _find_matching_brace(body, brace_open)
        if close is None:
            continue
        block_end = close + 1
        if block_end < len(body) and body[block_end] == ";":
            block_end += 1
        snippet = body[m.start() : block_end]
        comment = _preceding_block_comment(body, m.start())
        full = f"{comment}\n{snippet}".strip() if comment else snippet
        push(full, name, "struct", f"struct {name}")

    # --- typedef ... ;
    for m in re.finditer(r"\btypedef\b[^;]+;", body, re.DOTALL):
        snippet = m.group(0).strip()
        inner = re.search(r"\btypedef\b(.+);", snippet, re.DOTALL)
        sym = "typedef"
        if inner:
            tail = inner.group(1).strip().split()
            if tail:
                sym = tail[-1].rstrip("*&[]") or "typedef"
        comment = _preceding_block_comment(body, m.start())
        full = f"{comment}\n{snippet}".strip() if comment else snippet
        push(full, sym, "typedef", snippet.replace("\n", " ")[:500])

    # --- using Alias = ...;
    for m in re.finditer(r"\busing\s+(\w+)\s*=[^;]+;", body):
        name = m.group(1)
        snippet = m.group(0).strip()
        comment = _preceding_block_comment(body, m.start())
        full = f"{comment}\n{snippet}".strip() if comment else snippet
        push(full, name, "using", snippet)

    # --- 函数声明：返回类型 + 名(参数) ; （含前置 Doxygen）
    fn_pat = re.compile(
        r"(/\*\*.*?\*/\s*)?"
        r"(?P<sig>[\w:<>,\s\*&]+)\s+"
        r"(?P<name>\w+)\s*"
        r"\((?P<params>[^)]*)\)\s*;",
        re.DOTALL,
    )
    for m in fn_pat.finditer(body):
        name = m.group("name")
        sig = f"{m.group('sig').strip()} {name}({m.group('params').strip()});"
        snippet = m.group(0).strip()
        if "typedef" in snippet or "using" in snippet.split(";")[0]:
            continue
        push(snippet, name, "function", sig.replace("\n", " ")[:500])

    # --- 若未抽到任何符号，整文件一条（仍便于检索）
    if not chunks:
        fb = _truncate(body)
        if fb:
            base = Path(rel_file_name).stem
            push(fb, base or "header", "file", None)

    return chunks


def iter_corpus_files(corpus_dir: Path) -> list[Path]:
    corpus_dir = corpus_dir.resolve()
    if not corpus_dir.is_dir():
        return []
    files: list[Path] = []
    for p in sorted(corpus_dir.rglob("*")):
        if p.is_file() and p.suffix.lower() in (".hxx", ".hpp", ".hh", ".h"):
            files.append(p)
    return files
