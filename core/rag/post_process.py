"""
PostProcess 节点：LLM 输出的最后安全过滤层。
1. 敏感词过滤（政治 / 竞品 / 人身攻击）
2. PII 检测（手机号 / 身份证 / 银行卡）
3. 输出长度截断
"""
import logging
import re

logger = logging.getLogger(__name__)

# 默认敏感词库为空。各 Bot 可通过配置附加业务词表。
DEFAULT_SENSITIVE_WORDS: list[str] = []

# PII 正则（留意精度 / 误报权衡，仅用于 WARN 上报）
_PHONE_RE = re.compile(r"1[3-9]\d{9}")
_ID_CARD_RE = re.compile(r"\d{17}[\dXx]")
_BANK_CARD_RE = re.compile(r"\d{16,19}")

MAX_OUTPUT_LENGTH = 2000


def filter_sensitive_words(
    text: str, extra_words: list[str] | None = None
) -> str:
    """过滤敏感词，替换为 ***"""
    words = list(DEFAULT_SENSITIVE_WORDS) + (extra_words or [])
    for word in words:
        if word and word.lower() in text.lower():
            text = re.sub(re.escape(word), "***", text, flags=re.IGNORECASE)
    return text


def detect_pii(text: str) -> list[dict]:
    """检测 PII 信息，返回命中列表（不修改文本，仅供日志/告警）"""
    findings: list[dict] = []
    for m in _PHONE_RE.finditer(text):
        findings.append(
            {"type": "phone", "value": m.group(), "start": m.start()}
        )
    for m in _ID_CARD_RE.finditer(text):
        findings.append(
            {
                "type": "id_card",
                "value": m.group()[:6] + "****",
                "start": m.start(),
            }
        )
    for m in _BANK_CARD_RE.finditer(text):
        findings.append(
            {
                "type": "bank_card",
                "value": m.group()[:6] + "****",
                "start": m.start(),
            }
        )
    return findings


def truncate_output(
    text: str, max_len: int = MAX_OUTPUT_LENGTH
) -> tuple[str, bool]:
    """超长截断，追加提示语。返回 (text, was_truncated)。"""
    if len(text) <= max_len:
        return text, False
    suffix = "…（内容较长，如需完整信息请联系人工客服）"
    return text[:max_len] + suffix, True


async def run(
    text: str, bot_sensitive_words: list[str] | None = None
) -> dict:
    """
    对 LLM 输出执行所有安全过滤。
    返回 {"text": filtered, "pii_detected": [...], "truncated": bool}
    """
    filtered = filter_sensitive_words(text, bot_sensitive_words)
    pii_findings = detect_pii(filtered)
    if pii_findings:
        logger.warning(
            f"PII detected in LLM output: {[f['type'] for f in pii_findings]}"
        )
    final_text, was_truncated = truncate_output(filtered)
    return {
        "text": final_text,
        "pii_detected": pii_findings,
        "truncated": was_truncated,
    }
