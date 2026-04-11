"""
知识库摄取入口。
被 RQ Worker 异步调用，处理完成后更新 DB 状态。
"""
import asyncio
import logging

logger = logging.getLogger(__name__)


def run_ingestion(
    source_id: str, bot_id: str, tenant_id: str, db_url: str
) -> None:
    """
    RQ Worker 同步入口（RQ 不支持 async task）。
    内部通过 asyncio.run 调用异步逻辑。
    """
    asyncio.run(_ingest(source_id, bot_id, tenant_id, db_url))


async def _ingest(
    source_id: str, bot_id: str, tenant_id: str, db_url: str
) -> None:
    import asyncpg

    from config import settings
    from knowledge.chunker import chunk_pages
    from knowledge.embedder import embed_texts
    from knowledge.vector_store import insert_chunks

    # 优先使用 Worker 自身 env 的 DATABASE_URL：无论 Worker 跑在 Windows
    # 主机（localhost）还是 docker-compose worker service（postgres 主机名），
    # 都用它自己的视角，不依赖入队方的 db_url 参数。
    effective_url = settings.DATABASE_URL or db_url
    pool = await asyncpg.create_pool(
        dsn=effective_url, min_size=1, max_size=3
    )

    try:
        row = await pool.fetchrow(
            "SELECT * FROM knowledge_sources WHERE id = $1 AND tenant_id = $2",
            source_id, tenant_id,
        )
        if not row:
            logger.error(f"Source {source_id} not found")
            return

        await pool.execute(
            "UPDATE knowledge_sources SET status = 'processing', updated_at = NOW() WHERE id = $1",
            source_id,
        )

        source_type = row["type"]
        if source_type == "url":
            from knowledge.crawler import crawl_url
            url = row["url"]
            if not url:
                raise ValueError("URL is empty")
            logger.info(f"Crawling URL: {url}")
            try:
                raw_text = await asyncio.wait_for(crawl_url(url), timeout=60.0)
            except asyncio.TimeoutError:
                raise ValueError(f"URL 爬取超时（60s）: {url}")
            except Exception as ce:
                raise ValueError(f"URL 爬取失败: {ce}")
            if not raw_text or len(raw_text.strip()) < 50:
                raise ValueError(f"页面内容为空或过短（{len(raw_text) if raw_text else 0} 字符）")
            pages = [raw_text]
        else:
            from knowledge.parser import parse_file
            file_path = row["file_path"]
            logger.info(f"Parsing file: {file_path}")
            pages = parse_file(file_path)

        if not pages:
            raise ValueError("No content extracted")

        chunks = chunk_pages(pages)
        logger.info(f"Created {len(chunks)} chunks")

        texts = [c["content"] for c in chunks]
        vectors = await embed_texts(texts)

        count = insert_chunks(bot_id, source_id, chunks, vectors)

        await pool.execute(
            """
            UPDATE knowledge_sources
            SET status = 'ready', chunk_count = $1, updated_at = NOW()
            WHERE id = $2
            """,
            count, source_id,
        )
        logger.info(f"Ingestion complete: source={source_id} chunks={count}")

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(
            f"Ingestion FAILED for source={source_id}: {e}\n{tb}"
        )
        try:
            await pool.execute(
                """
                UPDATE knowledge_sources
                SET status = 'failed', error_msg = $1, updated_at = NOW()
                WHERE id = $2
                """,
                str(e)[:500], source_id,
            )
        except Exception as db_err:
            logger.error(f"Failed to update error status: {db_err}")
    finally:
        await pool.close()
