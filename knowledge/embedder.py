"""
Embedding 模块。
调用通义千问 text-embedding-v3，批量处理。
"""
import logging

from openai import AsyncOpenAI

from config import settings

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.EMBEDDING_API_KEY or settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
        )
    return _client


async def embed_texts(
    texts: list[str], batch_size: int = 25
) -> list[list[float]]:
    """批量生成 embedding，返回向量列表（顺序与输入一致）"""
    client = _get_client()
    all_vectors: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            resp = await client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=batch,
            )
            vectors = [item.embedding for item in resp.data]
            all_vectors.extend(vectors)
            logger.debug(
                f"Embedded {len(batch)} texts (batch {i // batch_size + 1})"
            )
        except Exception as e:
            logger.error(
                f"Embedding failed for batch {i // batch_size + 1}: {e}"
            )
            raise

    return all_vectors


async def embed_single(text: str) -> list[float]:
    """单条文本 embedding"""
    results = await embed_texts([text])
    return results[0]
