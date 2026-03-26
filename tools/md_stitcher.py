"""Markdown 拼接工具：按 jsonl 页序拼接多页 md，并处理跨页表格合并与空单元格填充。"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class StitchOptions:
    """拼接参数。"""

    merge_tables_across_pages: bool = True
    fill_empty_table_cells: bool = True
    extract_data_images: bool = True
    images_subdir: str = "_assets"
    encoding: str = "utf-8"


_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")
_MD_DATA_IMAGE_RE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\(\s*(?P<data>data:image/(?P<fmt>png|jpe?g|gif|webp);base64,(?P<b64>[A-Za-z0-9+/=\s]+))\s*\)",
    re.IGNORECASE,
)
_HTML_TABLE_END_RE = re.compile(r"(?is)(<table\\b[\\s\\S]*?</table>)\\s*\\Z")
_HTML_TABLE_START_RE = re.compile(r"(?is)\\A\\s*(<table\\b[\\s\\S]*?</table>)")


def stitch_md_folder(folder: str | Path, *, opts: StitchOptions | None = None) -> Path:
    """
    将文件夹内的 `*.jsonl` 作为页序索引，把 `*_page_{n}.md` 按顺序拼接为一个 md。

    规则：
    - 若前一页末尾与后一页开头紧贴着都是表格，且列数一致，则合并为一个表格。
    - 表格内若出现空单元格（空/全空白），则用同列上一行的值填充。

    输出：
    - 生成的 md 文件放在该文件夹内，文件名为：`<文件夹名>.md`
    """
    opts = opts or StitchOptions()
    folder = Path(folder).resolve()
    if not folder.is_dir():
        raise FileNotFoundError(f"folder 不存在: {folder}")

    jsonl_files = sorted(folder.glob("*.jsonl"))
    if not jsonl_files:
        raise FileNotFoundError(f"未找到 jsonl 索引文件: {folder}")
    if len(jsonl_files) > 1:
        # 避免不确定性：多个 jsonl 时选择与 md 前缀匹配最多的那个
        jsonl_path = _pick_best_jsonl(folder, jsonl_files)
    else:
        jsonl_path = jsonl_files[0]

    page_nos = _load_page_nos(jsonl_path)
    stem = jsonl_path.stem
    md_paths = [folder / f"{stem}_page_{n}.md" for n in page_nos]
    missing = [p for p in md_paths if not p.exists()]
    if missing:
        raise FileNotFoundError(f"缺少 md 页面文件: {[str(p) for p in missing[:10]]}")

    pages = [p.read_text(encoding=opts.encoding, errors="ignore") for p in md_paths]
    merged = _merge_pages(pages, merge_tables=opts.merge_tables_across_pages)

    if opts.fill_empty_table_cells:
        merged = _fill_tables_empty_cells(merged)

    out_path = folder / f"{folder.name}.md"

    if opts.extract_data_images:
        assets_dir = folder / opts.images_subdir
        merged = _extract_data_uri_images(merged, assets_dir)

    out_path.write_text(merged, encoding=opts.encoding)
    return out_path


def _pick_best_jsonl(folder: Path, jsonl_files: list[Path]) -> Path:
    md_files = list(folder.glob("*_page_*.md"))
    if not md_files:
        return jsonl_files[0]
    best = jsonl_files[0]
    best_score = -1
    for j in jsonl_files:
        stem = j.stem
        score = sum(1 for m in md_files if m.name.startswith(stem + "_page_"))
        if score > best_score:
            best_score = score
            best = j
    return best


def _load_page_nos(jsonl_path: Path) -> list[int]:
    out: list[int] = []
    with jsonl_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            n = obj.get("page_no")
            if isinstance(n, int):
                out.append(n)
            elif isinstance(n, str) and n.isdigit():
                out.append(int(n))
    if not out:
        raise ValueError(f"jsonl 中未解析到 page_no: {jsonl_path}")
    return sorted(set(out))


def _merge_pages(pages: list[str], *, merge_tables: bool) -> str:
    if not pages:
        return ""

    acc = pages[0].rstrip() + "\n"
    for nxt in pages[1:]:
        left = acc
        right = (nxt or "").lstrip("\n")
        if merge_tables:
            merged = _merge_adjacent_tables(left, right)
            if merged is not None:
                acc = merged
                continue
        # 默认用一个空行分隔，避免段落粘连
        acc = left.rstrip() + "\n\n" + right.lstrip()
        if not acc.endswith("\n"):
            acc += "\n"
    return acc


def _merge_adjacent_tables(left: str, right: str) -> str | None:
    """
    若 left 末尾是表格块且 right 开头是表格块，且列数一致，则合并。
    返回合并后的全文；否则返回 None。
    """
    # 1) 先尝试 HTML table（你当前语料是这种）
    html_merged = _merge_adjacent_html_tables(left, right)
    if html_merged is not None:
        return html_merged

    # 2) 再尝试 markdown pipe table
    left_lines = left.splitlines()
    right_lines = right.splitlines()

    l_block = _extract_table_block_from_end(left_lines)
    r_block = _extract_table_block_from_start(right_lines)
    if l_block is None or r_block is None:
        return None

    l_start, l_end, l_tbl = l_block
    r_start, r_end, r_tbl = r_block

    l_cols = _table_column_count(l_tbl)
    r_cols = _table_column_count(r_tbl)
    if l_cols <= 0 or r_cols <= 0 or l_cols != r_cols:
        return None

    # 合并策略：保留左表头（若有），右表若也带表头则去掉其表头两行（header+sep）
    r_tbl_body = _drop_table_header_if_present(r_tbl)
    merged_tbl = l_tbl + r_tbl_body

    new_left = left_lines[:l_start] + merged_tbl
    new_right = right_lines[r_end + 1 :]
    out_lines = new_left + [""] + new_right
    return "\n".join(out_lines).rstrip() + "\n"


def _merge_adjacent_html_tables(left: str, right: str) -> str | None:
    """
    若 left 末尾与 right 开头紧贴为 HTML table（允许仅空白分隔），且列数一致，则合并。
    """
    m_left = _HTML_TABLE_END_RE.search(left)
    m_right = _HTML_TABLE_START_RE.search(right)
    if not m_left or not m_right:
        return None

    left_tbl = m_left.group(1)
    right_tbl = m_right.group(1)

    l_cols = _html_table_column_count(left_tbl)
    r_cols = _html_table_column_count(right_tbl)
    if l_cols <= 0 or r_cols <= 0 or l_cols != r_cols:
        return None

    merged_tbl = _merge_html_table_blocks(left_tbl, right_tbl)

    new_left = left[: m_left.start(1)] + merged_tbl
    new_right = right[m_right.end(1) :]
    out = (new_left.rstrip() + "\n\n" + new_right.lstrip()).rstrip() + "\n"
    return out


def _html_table_column_count(table_html: str) -> int:
    # 取第一行 tr 的 th/td 个数作为列数（忽略 colspan 的复杂情况）
    m = re.search(r"(?is)<tr\\b[^>]*>([\\s\\S]*?)</tr>", table_html)
    if not m:
        return 0
    row = m.group(1)
    cells = re.findall(r"(?is)<t[dh]\\b[^>]*>.*?</t[dh]>", row)
    return len(cells)


def _extract_thead(table_html: str) -> str | None:
    m = re.search(r"(?is)<thead\\b[^>]*>[\\s\\S]*?</thead>", table_html)
    return m.group(0) if m else None


def _extract_tr_rows(table_html: str) -> list[str]:
    # 优先 tbody 内的 tr，否则退化到全表的 tr（会包含 header 行，后续会去重处理）
    m_tbody = re.search(r"(?is)<tbody\\b[^>]*>([\\s\\S]*?)</tbody>", table_html)
    scope = m_tbody.group(1) if m_tbody else table_html
    return re.findall(r"(?is)<tr\\b[^>]*>[\\s\\S]*?</tr>", scope)


def _merge_html_table_blocks(left_tbl: str, right_tbl: str) -> str:
    """
    合并两个 HTML table：
    - 保留左表的 thead（若存在）
    - 右表若存在 thead，则不重复拼接其 header 行
    - 合并 tbody 行
    """
    thead = _extract_thead(left_tbl) or _extract_thead(right_tbl)

    left_rows = _extract_tr_rows(left_tbl)
    right_rows = _extract_tr_rows(right_tbl)

    # 如果右表包含 thead，我们尽量去掉其第一行 header（防止重复）
    if _extract_thead(right_tbl) and right_rows:
        # 右表 tbody 常常不含 header；但若 OCR 把 header 放进 tbody，则粗暴跳过首行
        right_rows = right_rows[1:]

    body = "<tbody>" + "".join(left_rows + right_rows) + "</tbody>"
    if thead:
        return "<table>" + thead + body + "</table>"
    return "<table>" + body + "</table>"


def _extract_table_block_from_end(lines: list[str]) -> tuple[int, int, list[str]] | None:
    i = len(lines) - 1
    while i >= 0 and not lines[i].strip():
        i -= 1
    if i < 0:
        return None

    end = i
    while i >= 0 and _looks_like_table_line(lines[i]):
        i -= 1
    start = i + 1
    tbl = lines[start : end + 1]
    if not _is_markdown_table(tbl):
        return None
    return start, end, tbl


def _extract_table_block_from_start(lines: list[str]) -> tuple[int, int, list[str]] | None:
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines):
        return None

    start = i
    while i < len(lines) and _looks_like_table_line(lines[i]):
        i += 1
    end = i - 1
    tbl = lines[start : end + 1]
    if not _is_markdown_table(tbl):
        return None
    return start, end, tbl


def _looks_like_table_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    # 典型 pipe table 行：包含 | 且不是纯分隔线以外的奇怪内容
    return "|" in s


def _is_markdown_table(tbl_lines: list[str]) -> bool:
    if len(tbl_lines) < 2:
        return False
    # 必须包含分隔线（第二行常见）
    return any(_TABLE_SEP_RE.match(x) for x in tbl_lines[:3])


def _table_column_count(tbl_lines: list[str]) -> int:
    # 找 header 行（分隔线之前的第一行）
    if not tbl_lines:
        return 0
    # 找到分隔线索引
    sep_idx = None
    for i, ln in enumerate(tbl_lines[:5]):
        if _TABLE_SEP_RE.match(ln):
            sep_idx = i
            break
    if sep_idx is None or sep_idx == 0:
        return 0
    header = tbl_lines[sep_idx - 1]
    return len(_split_table_row(header))


def _drop_table_header_if_present(tbl_lines: list[str]) -> list[str]:
    """
    若表格前两行是 header+sep，则返回去掉这两行后的表体；否则返回原表格行。
    """
    if len(tbl_lines) >= 2 and _TABLE_SEP_RE.match(tbl_lines[1]):
        return tbl_lines[2:]
    # 也兼容：第一行空、第二行 header、第三行 sep（极少见）
    if len(tbl_lines) >= 3 and _TABLE_SEP_RE.match(tbl_lines[2]):
        return tbl_lines[3:]
    return tbl_lines


def _split_table_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _join_table_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _fill_tables_empty_cells(text: str) -> str:
    """
    遍历全文，找到 markdown 表格块，对表体行做“空单元格按同列向上填充”。不改表头与分隔线。
    """
    # 先处理 HTML table（通常一整行一个 table，逐行扫描不可靠）
    text = _fill_html_tables_empty_cells(text)

    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        # 尝试识别从 i 开始的表格
        if _looks_like_table_line(lines[i]):
            j = i
            while j < len(lines) and _looks_like_table_line(lines[j]):
                j += 1
            block = lines[i:j]
            if _is_markdown_table(block):
                out.extend(_fill_table_block(block))
                i = j
                continue
        out.append(lines[i])
        i += 1
    return "\n".join(out).rstrip() + "\n"


def _fill_html_tables_empty_cells(text: str) -> str:
    """
    对 HTML table 执行空单元格向上填充：<td></td> / <td>   </td> 会继承同列上一行的内容。

    说明：
    - 仅对 <td> 生效（<th> 不改）
    - 不处理 rowspan/colspan 的精确网格展开；若行列数不一致则跳过该行以避免错填
    """

    def table_repl(m: re.Match[str]) -> str:
        table_html = m.group(0)
        col_count = _html_table_column_count(table_html)
        if col_count <= 0:
            return table_html

        rows = re.findall(r"(?is)<tr\\b[^>]*>[\\s\\S]*?</tr>", table_html)
        last_seen: list[str] = [""] * col_count
        new_rows: list[str] = []

        for tr in rows:
            # 只改 td，保留原有属性
            cells = re.findall(r"(?is)(<td\\b[^>]*>)([\\s\\S]*?)(</td>)", tr)
            if not cells:
                new_rows.append(tr)
                continue
            if len(cells) != col_count:
                new_rows.append(tr)
                last_seen = [""] * col_count
                continue

            rebuilt = tr
            for idx, (open_tag, inner, close_tag) in enumerate(cells):
                inner_text = re.sub(r"(?is)<[^>]+>", "", inner).strip()
                if inner_text == "":
                    fill = last_seen[idx]
                    new_inner = fill
                else:
                    last_seen[idx] = inner_text
                    new_inner = inner
                # 逐个替换第一次出现的该 cell
                rebuilt = re.sub(
                    r"(?is)" + re.escape(open_tag) + r"[\\s\\S]*?" + re.escape(close_tag),
                    open_tag + new_inner + close_tag,
                    rebuilt,
                    count=1,
                )
            new_rows.append(rebuilt)

        # 把原来的 rows 替换为 new_rows（保留 thead/tbody 结构）
        # 简化：直接按顺序替换所有 <tr>...</tr>
        out = table_html
        for old_tr, new_tr in zip(rows, new_rows):
            out = out.replace(old_tr, new_tr, 1)
        return out

    return re.sub(r"(?is)<table\\b[\\s\\S]*?</table>", table_repl, text)


def _fill_table_block(block: list[str]) -> list[str]:
    # 定位分隔线
    sep_idx = None
    for i, ln in enumerate(block[:5]):
        if _TABLE_SEP_RE.match(ln):
            sep_idx = i
            break
    if sep_idx is None or sep_idx == 0:
        return block

    header = block[sep_idx - 1]
    sep = block[sep_idx]
    body = block[sep_idx + 1 :]

    col_count = len(_split_table_row(header))
    if col_count <= 0:
        return block

    filled_body: list[str] = []
    last_seen: list[str] = [""] * col_count
    for ln in body:
        if _TABLE_SEP_RE.match(ln):
            filled_body.append(ln)
            continue
        cells = _split_table_row(ln)
        # 列数不一致时不强行修复，直接原样输出并重置 last_seen（避免错填）
        if len(cells) != col_count:
            filled_body.append(ln)
            last_seen = [""] * col_count
            continue
        new_cells: list[str] = []
        for idx, c in enumerate(cells):
            if c.strip() == "":
                new_cells.append(last_seen[idx])
            else:
                new_cells.append(c)
                last_seen[idx] = c
        filled_body.append(_join_table_row(new_cells))

    return block[: sep_idx - 1] + [_join_table_row(_split_table_row(header)), sep] + filled_body


def _extract_data_uri_images(text: str, assets_dir: Path) -> str:
    """
    将 markdown 中的 data:image/...;base64,... 提取为图片文件，并替换为相对路径引用。

    - 图片写入 `assets_dir`（如 `<folder>/_assets/`）
    - 同一 base64 内容按 sha256 去重，避免重复写文件
    """
    assets_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}

    def repl(m: re.Match[str]) -> str:
        alt = m.group("alt") or ""
        fmt = (m.group("fmt") or "png").lower()
        b64 = (m.group("b64") or "").strip()
        if not b64:
            return m.group(0)

        # 去掉 base64 中的空白（有些工具会插入换行）
        b64_clean = re.sub(r"\s+", "", b64)
        digest = hashlib.sha256(b64_clean.encode("utf-8")).hexdigest()[:16]
        key = f"{fmt}:{digest}"
        if key in written:
            rel = written[key]
            return f"![{alt}]({rel})"

        try:
            data = base64.b64decode(b64_clean, validate=False)
        except Exception:
            return m.group(0)

        # 极端情况兜底：空数据不写
        if not data:
            return m.group(0)

        filename = f"img_{digest}.{ 'jpg' if fmt in {'jpg','jpeg'} else fmt }"
        out_path = assets_dir / filename
        if not out_path.exists():
            out_path.write_bytes(data)

        rel = f"{assets_dir.name}/{filename}"
        written[key] = rel
        return f"![{alt}]({rel})"

    return _MD_DATA_IMAGE_RE.sub(repl, text)


__all__ = ["StitchOptions", "stitch_md_folder"]

