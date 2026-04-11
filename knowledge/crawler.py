"""
URL 爬取模块：输入 URL，返回清洗后的纯文本。

优先使用 Crawl4AI（底层 Playwright，支持 JS 渲染）；若未安装则降级到
aiohttp + HTMLParser 的简单抓取（只能处理静态 HTML）。
"""
import logging
import re
from html.parser import HTMLParser

logger = logging.getLogger(__name__)


async def crawl_url(url: str, max_length: int = 50000) -> str:
    """
    爬取单个 URL，返回清洗后的纯文本。失败时抛 ValueError。
    """
    try:
        from crawl4ai import AsyncWebCrawler  # type: ignore
    except ImportError:
        logger.warning("crawl4ai not installed; falling back to simple fetch")
        return await _simple_fetch(url, max_length)

    try:
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url, word_count_threshold=10)
            if not getattr(result, "success", False):
                raise ValueError(
                    f"crawl4ai failed: {getattr(result, 'error_message', 'unknown')}"
                )
            text = result.markdown or result.cleaned_html or ""
            return _clean_text(text)[:max_length]
    except Exception as e:
        raise ValueError(f"Failed to crawl {url}: {e}")


def _clean_text(text: str) -> str:
    """清洗 markdown / HTML 残留"""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.strip()


class _TextExtractor(HTMLParser):
    _SKIP_TAGS = {"script", "style", "nav", "footer", "noscript"}

    def __init__(self) -> None:
        super().__init__()
        self.texts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            trimmed = data.strip()
            if trimmed:
                self.texts.append(trimmed)


async def _simple_fetch(url: str, max_length: int) -> str:
    """aiohttp 降级方案：只处理静态 HTML。"""
    import aiohttp

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise ValueError(f"HTTP {resp.status}")
            html = await resp.text()

    parser = _TextExtractor()
    parser.feed(html)
    combined = "\n".join(parser.texts)
    return _clean_text(combined)[:max_length]
