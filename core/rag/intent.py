"""意图枚举定义 — 单一来源，所有模块从此导入"""


class Intent:
    # L1 对话层（skip_retrieval=True）
    GREETING       = "greeting"
    FAREWELL       = "farewell"
    ACKNOWLEDGMENT = "acknowledgment"
    BOT_IDENTITY   = "bot_identity"
    CAPABILITY     = "capability"
    CHITCHAT       = "chitchat"
    # L2 咨询层（走完整 RAG）
    PRODUCT_INFO   = "product_info"
    PRICE_INQUIRY  = "price_inquiry"
    AVAILABILITY   = "availability"
    HOW_TO_USE     = "how_to_use"
    POLICY_QUERY   = "policy_query"
    COMPARISON     = "comparison"
    # L3 销售层（触发 Lead Capture）
    PURCHASE_INTENT = "purchase_intent"
    BULK_INQUIRY    = "bulk_inquiry"
    CUSTOM_REQUEST  = "custom_request"
    # L4 异常层（特殊处理）
    COMPLAINT          = "complaint"
    URGENT             = "urgent"
    TRANSFER_EXPLICIT  = "transfer_explicit"
    TRANSFER_IMPLICIT  = "transfer_implicit"
    # L5 边界层
    CLARIFICATION  = "clarification"
    FOLLOW_UP      = "follow_up"
    MULTI_INTENT   = "multi_intent"
    OUT_OF_SCOPE   = "out_of_scope"

    # 旧版兼容别名
    KNOWLEDGE_QA   = "product_info"
    TRANSFER       = "transfer_explicit"

    # 按层分组（供 engine.py 路由判断）
    L1_NO_RETRIEVAL = {GREETING, FAREWELL, ACKNOWLEDGMENT,
                       BOT_IDENTITY, CAPABILITY, CHITCHAT}
    L2_RAG          = {PRODUCT_INFO, PRICE_INQUIRY, AVAILABILITY,
                       HOW_TO_USE, POLICY_QUERY, COMPARISON}
    L3_LEAD         = {PURCHASE_INTENT, BULK_INQUIRY, CUSTOM_REQUEST}
    L4_EXCEPTION    = {COMPLAINT, URGENT, TRANSFER_EXPLICIT, TRANSFER_IMPLICIT}
    L5_BOUNDARY     = {CLARIFICATION, FOLLOW_UP, MULTI_INTENT, OUT_OF_SCOPE}
