"""
Milvus 向量存储封装。
每个 Bot 独立 collection：bot_{bot_id}（下划线替换连字符）。
"""
import logging
import uuid

from pymilvus import (
    connections, Collection, CollectionSchema,
    FieldSchema, DataType, utility,
)

from config import settings

logger = logging.getLogger(__name__)

_EMBEDDING_DIM = 1536  # text-embedding-v3 维度
_connected = False


def _connect() -> None:
    global _connected
    if not _connected:
        connections.connect(
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT,
        )
        _connected = True


def _collection_name(bot_id: str) -> str:
    return "bot_" + bot_id.replace("-", "_")


def _get_or_create_collection(bot_id: str) -> Collection:
    _connect()
    name = _collection_name(bot_id)

    if utility.has_collection(name):
        return Collection(name)

    fields = [
        FieldSchema("chunk_id",  DataType.VARCHAR, max_length=64, is_primary=True),
        FieldSchema("content",   DataType.VARCHAR, max_length=4096),
        FieldSchema("source_id", DataType.VARCHAR, max_length=64),
        FieldSchema("page",      DataType.INT64),
        FieldSchema("vector",    DataType.FLOAT_VECTOR, dim=_EMBEDDING_DIM),
    ]
    schema = CollectionSchema(fields, description=f"Bot {bot_id} knowledge base")
    col = Collection(name, schema)

    col.create_index(
        "vector",
        {"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {"nlist": 128}},
    )
    col.load()
    logger.info(f"Created Milvus collection: {name}")
    return col


def insert_chunks(
    bot_id: str,
    source_id: str,
    chunks: list[dict],
    vectors: list[list[float]],
) -> int:
    """插入 chunk + vector，返回插入数量"""
    col = _get_or_create_collection(bot_id)

    chunk_ids  = [uuid.uuid4().hex for _ in chunks]
    contents   = [c["content"][:4000] for c in chunks]
    source_ids = [source_id] * len(chunks)
    pages      = [int(c.get("page", 0)) for c in chunks]

    col.insert([chunk_ids, contents, source_ids, pages, vectors])
    col.flush()
    logger.info(
        f"Inserted {len(chunks)} chunks into {_collection_name(bot_id)}"
    )
    return len(chunks)


def search(
    bot_id: str,
    query_vector: list[float],
    top_k: int = 10,
) -> list[dict]:
    """向量检索，返回 top_k 结果"""
    _connect()
    name = _collection_name(bot_id)
    if not utility.has_collection(name):
        return []

    col = Collection(name)
    if not col.is_loaded:
        col.load()

    results = col.search(
        data=[query_vector],
        anns_field="vector",
        param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=top_k,
        output_fields=["content", "source_id", "page"],
    )

    hits: list[dict] = []
    for hit in results[0]:
        hits.append({
            "content":   hit.entity.get("content"),
            "score":     float(hit.score),
            "chunk_id":  hit.id,
            "source_id": hit.entity.get("source_id"),
            "page":      hit.entity.get("page"),
        })
    return hits


def delete_by_source(bot_id: str, source_id: str) -> None:
    """删除某个知识来源的所有 chunks"""
    _connect()
    name = _collection_name(bot_id)
    if not utility.has_collection(name):
        return
    col = Collection(name)
    col.delete(f'source_id == "{source_id}"')
    col.flush()


def drop_collection(bot_id: str) -> None:
    """删除 Bot 时清理整个 collection"""
    _connect()
    name = _collection_name(bot_id)
    if utility.has_collection(name):
        utility.drop_collection(name)
        logger.info(f"Dropped Milvus collection: {name}")
