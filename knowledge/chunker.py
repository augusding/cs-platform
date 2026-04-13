"""
语义分块模块。
多级 fallback 策略：
  1. 显式标记（【】/ ## / === 分隔线）→ 按标记分段
  2. 连续空行（\\n\\n\\n+）→ 按空行分段
  3. 段落换行（\\n\\n）→ 按段落分段
  4. 兜底：固定字符数切割 + 重叠
每个段落保持完整，只有超过 MAX_CHUNK_SIZE 才做固定切割。
"""
import re
import logging

from config import settings  # noqa: F401 (imported for future use)

logger = logging.getLogger(__name__)

MAX_CHUNK_SIZE = 600
OVERLAP = 100
MIN_CHUNK_SIZE = 50


def _detect_language(text: str) -> str:
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    return "zh" if chinese / max(len(text), 1) > 0.2 else "en"


def _split_by_markers(text: str) -> list[str] | None:
    """策略 1：显式标记（【】/ ## / === / ---）"""
    pattern = r'(?=(?:^|\n)(?:【[^】]+】|#{1,3}\s+\S|={3,}|-{3,}))'
    parts = re.split(pattern, text)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) <= 1:
        return None
    return parts


def _split_by_blank_lines(text: str) -> list[str] | None:
    """策略 2：连续空行（\\n\\n\\n+）"""
    parts = re.split(r'\n{3,}', text)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) <= 1:
        return None
    return parts


def _split_by_paragraphs(text: str) -> list[str] | None:
    """策略 3：段落（\\n\\n）"""
    parts = re.split(r'\n\n+', text)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) <= 1:
        return None
    return parts


def _split_fixed(text: str, chunk_size: int = MAX_CHUNK_SIZE,
                 overlap: int = OVERLAP) -> list[str]:
    """策略 4 兜底：固定字符数切割 + 句子边界对齐 + 重叠"""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            best_break = -1
            for sep in ['。', '！', '？', '\n', '. ', '! ', '? ']:
                pos = text.rfind(sep, start + chunk_size // 2, end)
                if pos > best_break:
                    best_break = pos + len(sep)
            if best_break > start:
                end = best_break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def _merge_short_chunks(chunks: list[str], min_size: int = MIN_CHUNK_SIZE) -> list[str]:
    if not chunks:
        return chunks
    merged = [chunks[0]]
    for chunk in chunks[1:]:
        if len(chunk) < min_size and merged:
            merged[-1] = merged[-1] + "\n\n" + chunk
        else:
            merged.append(chunk)
    return merged


def _ensure_max_size(chunks: list[str], max_size: int = MAX_CHUNK_SIZE) -> list[str]:
    result = []
    for chunk in chunks:
        if len(chunk) > max_size:
            result.extend(_split_fixed(chunk, max_size))
        else:
            result.append(chunk)
    return result


def chunk_text(text: str) -> list[str]:
    """将文本智能分块，多级策略自动 fallback"""
    text = text.strip()
    if not text:
        return []

    chunks = _split_by_markers(text)
    strategy = "markers"

    if chunks is None:
        chunks = _split_by_blank_lines(text)
        strategy = "blank_lines"

    if chunks is None:
        chunks = _split_by_paragraphs(text)
        strategy = "paragraphs"

    if chunks is None:
        chunks = _split_fixed(text)
        strategy = "fixed"

    chunks = _merge_short_chunks(chunks)
    chunks = _ensure_max_size(chunks)

    logger.info(
        f"Chunker: strategy={strategy}, input={len(text)} chars, "
        f"output={len(chunks)} chunks"
    )
    return chunks


def chunk_pages(pages: list[str]) -> list[dict]:
    """多页文本 → 带元数据的 chunk 列表"""
    chunks: list[dict] = []
    for page_idx, page_text in enumerate(pages):
        for piece in chunk_text(page_text):
            chunks.append({
                "content": piece,
                "page": page_idx,
                "char_count": len(piece),
            })
    return chunks
