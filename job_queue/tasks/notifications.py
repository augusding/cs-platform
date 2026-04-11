"""
通知推送任务（RQ 异步执行）。
当前实现：SMTP 邮件。微信通知预留接口。
"""
import asyncio
import json
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_lead_notification(
    lead_id: str, tenant_id: str, bot_id: str
) -> None:
    """Lead capture 完成时通知业务员（RQ sync entrypoint）"""
    asyncio.run(_send_lead_notification(lead_id, tenant_id, bot_id))


async def _send_lead_notification(
    lead_id: str, tenant_id: str, bot_id: str
) -> None:
    import asyncpg
    from config import settings

    pool = await asyncpg.create_pool(
        dsn=settings.DATABASE_URL, min_size=1, max_size=2
    )
    try:
        lead = await pool.fetchrow(
            "SELECT * FROM leads WHERE id = $1", lead_id
        )
        if not lead:
            logger.warning(f"send_lead_notification: lead {lead_id} not found")
            return

        bot = await pool.fetchrow(
            "SELECT name FROM bots WHERE id = $1", bot_id
        )

        raw = lead["lead_info"]
        lead_info = json.loads(raw) if isinstance(raw, str) else dict(raw)

        bot_name = bot["name"] if bot else "Bot"
        subject = f"【新询盘】{bot_name} 收到新线索"
        body = (
            f"您好，\n\n"
            f"{bot_name} 收到一条新询盘：\n\n"
            f"产品需求：{lead_info.get('product_requirement', '未填写')}\n"
            f"采购数量：{lead_info.get('quantity', '未填写')}\n"
            f"目标价格：{lead_info.get('target_price', '未填写')}\n"
            f"联系方式：{lead_info.get('contact', '未填写')}\n"
            f"意向分数：{lead['intent_score']}\n\n"
            f"请登录控制台查看详情并及时跟进。\n\n"
            f"---\nCS Platform 智能客服系统"
        )

        await _send_email(subject, body, settings)
        logger.info(f"Lead notification dispatched for lead={lead_id}")
    finally:
        await pool.close()


async def _send_email(subject: str, body: str, settings) -> None:
    """发送 SMTP 邮件；未配置 SMTP 时静默跳过。"""
    if not settings.SMTP_HOST or not settings.SMTP_USERNAME:
        logger.warning("SMTP not configured, skipping email notification")
        return

    msg = MIMEMultipart()
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USERNAME}>"
    msg["To"] = settings.SMTP_USERNAME
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        logger.error(f"Email send failed: {e}")


def send_human_transfer_notification(
    session_id: str, tenant_id: str
) -> None:
    """人工接管请求通知（当前仅日志，后续接入微信推送）"""
    logger.info(
        f"Human transfer requested: session={session_id} tenant={tenant_id}"
    )
