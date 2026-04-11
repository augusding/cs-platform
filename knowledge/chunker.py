"""
语义分块模块。
中文按字符数分块，英文按词数分块，保留重叠。
"""
import re

from config import settings


def _detect_language(text: str) -> str:
    """简单语言检测：中文字符占比 > 20% 视为中文"""
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    return "zh" if chinese / max(len(text), 1) > 0.2 else "en"


def _split_zh(text: str, chunk_size: int, overlap: int) -> list[str]:
    """中文按字符数分块"""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]


def _split_en(text: str, chunk_size: int, overlap: int) -> list[str]:
    """英文按词数分块"""
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]


def chunk_text(text: str) -> list[str]:
    """将文本分块，自动检测语言"""
    lang = _detect_language(text)
    overlap = 50
    if lang == "zh":
        return _split_zh(text, settings.CHUNK_SIZE_ZH, overlap)
    return _split_en(text, settings.CHUNK_SIZE_EN, overlap)


def chunk_pages(pages: list[str]) -> list[dict]:
    """将多页/多段文本全部分块，返回带元数据的 chunk 列表"""
    chunks: list[dict] = []
    for page_idx, page_text in enumerate(pages):
        for piece in chunk_text(page_text):
            chunks.append({
                "content": piece,
                "page": page_idx,
                "char_count": len(piece),
            })
    return chunks
