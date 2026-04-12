"""
知识库路由：文档上传 + 进度查询 + FAQ CRUD
"""
import logging
import os
import uuid
from pathlib import Path

from aiohttp import web

from config import settings
from store.base import fetch_one, fetch_all, execute_returning, execute

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()

ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".docx", ".doc"}
ADMIN_ROLES = {"super_admin", "admin"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


def _require_admin(request: web.Request) -> None:
    if request.get("role") not in ADMIN_ROLES:
        raise web.HTTPForbidden(reason="Admin role required")


async def _get_bot_or_403(db, bot_id: str, tenant_id: str) -> dict:
    from store.bot_store import get_bot
    bot = await get_bot(db, bot_id, tenant_id)
    if not bot:
        raise web.HTTPForbidden(reason="Bot not found or access denied")
    return bot


# ── POST /api/bots/{bot_id}/knowledge ───────────────────
@routes.post("/api/bots/{bot_id}/knowledge")
async def upload_knowledge(request: web.Request) -> web.Response:
    _require_admin(request)
    db = request.app["db"]
    bot_id = request.match_info["bot_id"]
    tenant_id = request["tenant_id"]

    await _get_bot_or_403(db, bot_id, tenant_id)

    reader = await request.multipart()
    field = await reader.next()
    if field is None or field.name != "file":
        raise web.HTTPBadRequest(reason="Expected multipart field 'file'")

    filename = field.filename or "upload"
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise web.HTTPBadRequest(
            reason=f"Unsupported file type. Allowed: {sorted(ALLOWED_EXTENSIONS)}"
        )

    # 统一使用正斜杠，确保 Docker Worker（Linux）可以正确读取
    upload_dir = settings.UPLOAD_DIR.replace("\\", "/")
    os.makedirs(upload_dir, exist_ok=True)
    file_id = str(uuid.uuid4())
    save_path = f"{upload_dir}/{file_id}{suffix}"
    total_size = 0
    with open(save_path, "wb") as f:
        while chunk := await field.read_chunk(8192):
            total_size += len(chunk)
            if total_size > MAX_FILE_SIZE:
                f.close()
                try:
                    os.remove(save_path)
                except OSError:
                    pass
                raise web.HTTPRequestEntityTooLarge(
                    max_size=MAX_FILE_SIZE,
                    actual_size=total_size,
                )
            f.write(chunk)

    display_name = filename

    row = await execute_returning(
        db,
        """
        INSERT INTO knowledge_sources
            (tenant_id, bot_id, type, name, file_path, created_by)
        VALUES ($1, $2, 'doc', $3, $4, $5)
        RETURNING id, status, created_at
        """,
        tenant_id, bot_id, display_name, save_path, request["user_id"],
    )
    source_id = str(row["id"])

    job_id = None
    try:
        import redis as redis_lib
        from rq import Queue as RQueue

        from knowledge.ingestion import run_ingestion

        r = redis_lib.from_url(settings.REDIS_URL)
        q = RQueue("ingestion", connection=r)
        worker_db_url = settings.DATABASE_URL.replace(
            "localhost", "postgres"
        ).replace(
            "127.0.0.1", "postgres"
        )
        job = q.enqueue(
            run_ingestion,
            source_id, bot_id, tenant_id, worker_db_url,
            job_timeout=600,
        )
        job_id = job.id
    except Exception as e:
        logger.warning(
            f"RQ enqueue failed, ingestion remains pending: {e}"
        )

    return web.json_response({
        "data": {
            "id": source_id,
            "status": "pending",
            "job_id": job_id,
            "name": display_name,
        }
    }, status=201)


# ── POST /api/bots/{bot_id}/knowledge/url ───────────────
@routes.post("/api/bots/{bot_id}/knowledge/url")
async def submit_url(request: web.Request) -> web.Response:
    _require_admin(request)
    db = request.app["db"]
    bot_id = request.match_info["bot_id"]
    tenant_id = request["tenant_id"]

    await _get_bot_or_403(db, bot_id, tenant_id)

    data = await request.json()
    url = (data.get("url") or "").strip()
    name = (data.get("name") or url[:60]).strip()

    if not url or not url.startswith(("http://", "https://")):
        raise web.HTTPBadRequest(
            reason="Valid URL (http/https) is required"
        )

    row = await execute_returning(
        db,
        """
        INSERT INTO knowledge_sources
            (tenant_id, bot_id, type, name, url, created_by)
        VALUES ($1, $2, 'url', $3, $4, $5)
        RETURNING id, status, created_at
        """,
        tenant_id, bot_id, name, url, request["user_id"],
    )
    source_id = str(row["id"])

    job_id = None
    try:
        import redis as redis_lib
        from rq import Queue as RQueue

        from knowledge.ingestion import run_ingestion

        r = redis_lib.from_url(settings.REDIS_URL)
        q = RQueue("ingestion", connection=r)
        worker_db_url = settings.DATABASE_URL.replace(
            "localhost", "postgres"
        ).replace(
            "127.0.0.1", "postgres"
        )
        job = q.enqueue(
            run_ingestion,
            source_id, bot_id, tenant_id, worker_db_url,
            job_timeout=300,
        )
        job_id = job.id
    except Exception as e:
        logger.warning(
            f"RQ enqueue failed for URL ingestion: {e}"
        )

    return web.json_response({
        "data": {
            "id": source_id,
            "status": "pending",
            "job_id": job_id,
            "url": url,
            "name": name,
        }
    }, status=201)


# ── GET /api/bots/{bot_id}/knowledge ────────────────────
@routes.get("/api/bots/{bot_id}/knowledge")
async def list_knowledge(request: web.Request) -> web.Response:
    db = request.app["db"]
    bot_id = request.match_info["bot_id"]
    tenant_id = request["tenant_id"]

    await _get_bot_or_403(db, bot_id, tenant_id)

    rows = await fetch_all(
        db,
        """
        SELECT id, type, name, status, chunk_count, error_msg, created_at
        FROM knowledge_sources
        WHERE bot_id = $1 AND tenant_id = $2
        ORDER BY created_at DESC
        """,
        bot_id, tenant_id,
    )
    return web.json_response({
        "data": [
            {
                **dict(r),
                "id": str(r["id"]),
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows
        ],
        "meta": {"total": len(rows)},
    })


# ── GET /api/bots/{bot_id}/knowledge/{source_id} ────────
@routes.get("/api/bots/{bot_id}/knowledge/{source_id}")
async def get_knowledge_source(request: web.Request) -> web.Response:
    db = request.app["db"]
    tenant_id = request["tenant_id"]
    bot_id = request.match_info["bot_id"]
    source_id = request.match_info["source_id"]

    await _get_bot_or_403(db, bot_id, tenant_id)

    row = await fetch_one(
        db,
        """
        SELECT id, type, name, status, chunk_count, error_msg, created_at, updated_at
        FROM knowledge_sources
        WHERE id = $1 AND bot_id = $2 AND tenant_id = $3
        """,
        source_id, bot_id, tenant_id,
    )
    if not row:
        raise web.HTTPForbidden(reason="Source not found or access denied")

    return web.json_response({
        "data": {
            **dict(row),
            "id": str(row["id"]),
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }
    })


# ── DELETE /api/bots/{bot_id}/knowledge/{source_id} ─────
@routes.delete("/api/bots/{bot_id}/knowledge/{source_id}")
async def delete_knowledge_source(request: web.Request) -> web.Response:
    _require_admin(request)
    db = request.app["db"]
    tenant_id = request["tenant_id"]
    bot_id = request.match_info["bot_id"]
    source_id = request.match_info["source_id"]

    await _get_bot_or_403(db, bot_id, tenant_id)

    result = await execute(
        db,
        "DELETE FROM knowledge_sources WHERE id = $1 AND bot_id = $2 AND tenant_id = $3",
        source_id, bot_id, tenant_id,
    )
    if result == "DELETE 0":
        raise web.HTTPForbidden(reason="Source not found or access denied")

    try:
        from knowledge.vector_store import delete_by_source
        delete_by_source(bot_id, source_id)
    except Exception as e:
        logger.warning(f"Milvus cleanup failed for source {source_id}: {e}")

    return web.json_response({"data": None, "meta": {"affected": 1}})


# ── POST /api/bots/{bot_id}/faq ─────────────────────────
@routes.post("/api/bots/{bot_id}/faq")
async def create_faq(request: web.Request) -> web.Response:
    _require_admin(request)
    db = request.app["db"]
    bot_id = request.match_info["bot_id"]
    tenant_id = request["tenant_id"]

    await _get_bot_or_403(db, bot_id, tenant_id)

    data = await request.json()
    question = (data.get("question") or "").strip()
    answer = (data.get("answer") or "").strip()
    if not question or not answer:
        raise web.HTTPBadRequest(reason="question and answer are required")

    row = await execute_returning(
        db,
        """
        INSERT INTO faq_items (tenant_id, bot_id, question, answer, priority, created_by)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, question, answer, priority, is_active, created_at
        """,
        tenant_id, bot_id, question, answer,
        int(data.get("priority", 0)), request["user_id"],
    )
    return web.json_response({
        "data": {
            **dict(row),
            "id": str(row["id"]),
            "created_at": row["created_at"].isoformat(),
        }
    }, status=201)


# ── GET /api/bots/{bot_id}/faq ──────────────────────────
@routes.get("/api/bots/{bot_id}/faq")
async def list_faq(request: web.Request) -> web.Response:
    db = request.app["db"]
    bot_id = request.match_info["bot_id"]
    tenant_id = request["tenant_id"]

    await _get_bot_or_403(db, bot_id, tenant_id)

    rows = await fetch_all(
        db,
        """
        SELECT id, question, answer, priority, is_active, created_at
        FROM faq_items
        WHERE bot_id = $1 AND tenant_id = $2 AND is_active = TRUE
        ORDER BY priority DESC, created_at DESC
        """,
        bot_id, tenant_id,
    )
    return web.json_response({
        "data": [
            {
                **dict(r),
                "id": str(r["id"]),
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows
        ],
        "meta": {"total": len(rows)},
    })


# ── DELETE /api/bots/{bot_id}/faq/{faq_id} ──────────────
@routes.delete("/api/bots/{bot_id}/faq/{faq_id}")
async def delete_faq(request: web.Request) -> web.Response:
    _require_admin(request)
    db = request.app["db"]
    bot_id = request.match_info["bot_id"]
    faq_id = request.match_info["faq_id"]
    tenant_id = request["tenant_id"]

    await _get_bot_or_403(db, bot_id, tenant_id)
    result = await execute(
        db,
        """
        DELETE FROM faq_items
        WHERE id = $1 AND bot_id = $2 AND tenant_id = $3
        """,
        faq_id, bot_id, tenant_id,
    )
    if result == "DELETE 0":
        raise web.HTTPForbidden(reason="FAQ not found or access denied")
    return web.json_response({"data": None, "meta": {"affected": 1}})


# ── PUT /api/bots/{bot_id}/faq/{faq_id} ─────────────────
@routes.put("/api/bots/{bot_id}/faq/{faq_id}")
async def update_faq(request: web.Request) -> web.Response:
    _require_admin(request)
    db = request.app["db"]
    bot_id = request.match_info["bot_id"]
    faq_id = request.match_info["faq_id"]
    tenant_id = request["tenant_id"]

    await _get_bot_or_403(db, bot_id, tenant_id)

    data = await request.json()
    question = (data.get("question") or "").strip()
    answer = (data.get("answer") or "").strip()
    if not question or not answer:
        raise web.HTTPBadRequest(reason="question and answer are required")

    row = await execute_returning(
        db,
        """
        UPDATE faq_items
        SET question = $1, answer = $2, priority = $3
        WHERE id = $4 AND bot_id = $5 AND tenant_id = $6
        RETURNING id, question, answer, priority, is_active
        """,
        question, answer, int(data.get("priority", 0)),
        faq_id, bot_id, tenant_id,
    )
    if not row:
        raise web.HTTPForbidden(reason="FAQ not found or access denied")
    return web.json_response({
        "data": {**dict(row), "id": str(row["id"])}
    })


# ── GET /api/bots/{bot_id}/knowledge/{source_id}/chunks ─
@routes.get("/api/bots/{bot_id}/knowledge/{source_id}/chunks")
async def get_source_chunks(request: web.Request) -> web.Response:
    db = request.app["db"]
    tenant_id = request["tenant_id"]
    bot_id    = request.match_info["bot_id"]
    source_id = request.match_info["source_id"]

    await _get_bot_or_403(db, bot_id, tenant_id)

    row = await fetch_one(
        db,
        "SELECT id, name, type, status, chunk_count FROM knowledge_sources "
        "WHERE id=$1 AND bot_id=$2 AND tenant_id=$3",
        source_id, bot_id, tenant_id,
    )
    if not row:
        raise web.HTTPForbidden(reason="Source not found or access denied")

    chunks = []
    try:
        from knowledge.vector_store import _connect, _collection_name
        from pymilvus import Collection, utility
        _connect()
        col_name = _collection_name(bot_id)
        if utility.has_collection(col_name):
            col = Collection(col_name)
            col.load()
            results = col.query(
                expr=f'source_id == "{source_id}"',
                output_fields=["chunk_id", "content", "page"],
                limit=200,
            )
            chunks = [
                {
                    "chunk_id": r.get("chunk_id", ""),
                    "content":  r.get("content", ""),
                    "page":     r.get("page", 0),
                }
                for r in results
            ]
            chunks.sort(key=lambda x: x["page"])
    except Exception as e:
        logger.warning(f"Failed to query chunks from Milvus: {e}")

    return web.json_response({
        "data": {
            "source": {
                **dict(row),
                "id": str(row["id"]),
            },
            "chunks": chunks,
            "total": len(chunks),
        }
    })


def register(app: web.Application) -> None:
    app.router.add_routes(routes)
