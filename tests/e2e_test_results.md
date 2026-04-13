# 端到端测试报告
日期：2026-04-13 11:20
Bot ID：68887b76-93f7-4886-ba3f-bf85dbda5eb8
知识库：test_product_kb.txt + 5 条 FAQ

## 总体指标
- 测试用例数：30
- 意图分类准确数：23/30 (77%)
- 错误/超时数：0
- L2 平均 Grader 分数：0.571
- 平均延迟：7350ms
- 缓存命中：0
- 总 Token 消耗：2816

## 按类别统计
- **L1**: 4/5 准确, 平均 3076ms
- **L2**: 7/10 准确, 平均 11561ms
- **L3**: 3/3 准确, 平均 2789ms
- **L4**: 3/3 准确, 平均 8361ms
- **L5**: 4/4 准确, 平均 5010ms
- **EN**: 2/5 准确, 平均 7205ms

## 详细记录

| # | 类别 | 问题 | 期望意图 | 实际意图 | 匹配 | 置信度 | Grader | 延迟 | Exit | 备注 |
|---|------|------|---------|---------|------|--------|--------|------|------|------|
| 1 | L1 | 你好 | greeting | greeting | ✓ | 0.99 | 0.000 | 3559ms | skip_retrieval | 您好！请问有什么可以帮您？ |
| 2 | L1 | Hi, good morning | greeting | greeting | ✓ | 0.98 | 0.000 | 3071ms | skip_retrieval | Good morning! How can I help you today? |
| 3 | L1 | 谢谢，没问题了 | farewell | farewell | ✓ | 0.99 | 0.000 | 3193ms | skip_retrieval | 不客气！如有其他问题，随时欢迎咨询。 |
| 4 | L1 | 你是人工还是机器人？ | bot_identity | transfer_explicit | ✗ | 0.99 | 0.000 | 1666ms | transfer | 我来帮您转接人工客服，请稍候。 |
| 5 | L1 | 你能做什么？ | capability | capability | ✓ | 0.99 | 0.000 | 3892ms | skip_retrieval | 这个问题我需要为您转接人工确认。 |
| 6 | L2 | 你们有哪些蓝牙耳机？ | product_info | product_info | ✓ | 0.97 | 0.672 | 14820ms | full_rag | 我们目前提供三款蓝牙耳机，分别是：  1. **StarPods Pro（旗舰款 |
| 7 | L2 | StarPods Pro 多少钱？批量价呢？ | price_inquiry | multi_intent | ✗ | 0.92 | 0.709 | 9702ms | full_rag | StarPods Pro 零售价为 $45.99。  批量采购价格如下：   - |
| 8 | L2 | SP-100 和 SL-200 有什么区别？ | comparison | comparison | ✓ | 0.97 | 0.532 | 14945ms | full_rag | 参考资料中未提及型号 SP-100，仅详细列出了 SL-200（StarPods |
| 9 | L2 | 有没有防水的运动耳机？ | product_info | product_info | ✓ | 0.92 | 0.547 | 10656ms | full_rag | 有，StarPods Sport（运动款）是专为运动设计的防水耳机，型号SS-3 |
| 10 | L2 | 智能手表的续航多长时间？ | product_info | product_info | ✓ | 0.92 | 0.566 | 10633ms | full_rag | StarWatch Ultra智能手表的续航为：典型使用7天，待机15天。 |
| 11 | L2 | 充电宝支持快充吗？最大输出多少瓦？ | product_info | multi_intent | ✗ | 0.92 | 0.595 | 11882ms | full_rag | 是的，StarPower 20000充电宝支持快充。   最大输出为：USB-C |
| 12 | L2 | 你们的产品有什么认证？ | product_info | product_info | ✓ | 0.92 | 0.460 | 10536ms | full_rag | 我们的产品已通过以下认证：  - ISO9001质量管理体系认证   - CE认 |
| 13 | L2 | 怎么付款？支持信用证吗？ | policy_query | multi_intent | ✗ | 0.92 | 0.583 | 9684ms | full_rag | 付款方式支持T/T（30%预付+70%发货前付清）、L/C（信用证）和PayPa |
| 14 | L2 | 交货期大概多久？ | availability | availability | ✓ | 0.92 | 0.583 | 10657ms | full_rag | 交货期根据产品和订单数量不同，具体如下：  - 常规产品（如充电宝、部分耳机等） |
| 15 | L2 | 退换货政策是什么？ | policy_query | policy_query | ✓ | 0.98 | 0.467 | 12091ms | full_rag | 退换货政策如下：   - 仅接受质量问题导致的退换货；   - 非质量问题（如选 |
| 16 | L3 | 我想采购一批蓝牙耳机 | purchase_intent | purchase_intent | ✓ | 0.92 | 0.000 | 2635ms | lead_capture | 请问大概的采购数量是多少？ |
| 17 | L3 | 我们公司需要定制5000个耳机，能打我们的LOGO | custom_request | custom_request | ✓ | 0.97 | 0.000 | 3030ms | lead_capture | 请问大概的采购数量是多少？ |
| 18 | L3 | I want to order 2000 unit... | bulk_inquiry | bulk_inquiry | ✓ | 0.97 | 0.000 | 2701ms | lead_capture | 请问大概的采购数量是多少？ |
| 19 | L4 | 我要投诉，上次买的耳机全是坏的 | complaint | complaint | ✓ | 0.98 | 0.483 | 14488ms | full_rag | 您好，很抱歉给您带来不便。关于您购买的耳机出现全部故障的情况，请您提供订单号及收 |
| 20 | L4 | 转人工客服 | transfer_explicit | transfer_explicit | ✓ | 0.99 | 0.000 | 1517ms | transfer | 我来帮您转接人工客服，请稍候。 |
| 21 | L4 | 很急！明天就要发货 | urgent | urgent | ✓ | 0.97 | 0.395 | 9077ms | full_rag | 很抱歉，根据现有生产安排，最快交货期为下单后10-15个工作日（如StarPow |
| 22 | L5 | 帮我写一段Python代码 | out_of_scope | out_of_scope | ✓ | 0.99 | 0.000 | 1494ms | out_of_scope | 抱歉，这个问题超出了我的服务范围，请咨询相关专业人士。 |
| 23 | L5 | 今天股票怎么样？ | out_of_scope | out_of_scope | ✓ | 0.99 | 0.000 | 1695ms | out_of_scope | 抱歉，这个问题超出了我的服务范围，请咨询相关专业人士。 |
| 24 | L5 | 嗯 | acknowledgment | acknowledgment | ✓ | 0.97 | 0.000 | 2647ms | skip_retrieval | 您好！请问有什么可以帮您的？ |
| 25 | L5 | 那价格呢？ | follow_up | price_inquiry | ✓ | 0.98 | 0.562 | 14204ms | full_rag | 请问您具体咨询的是哪款产品？目前我们有以下几款产品的批量价格供参考：  - ** |
| 26 | EN | What Bluetooth earbuds do... | product_info | product_info | ✓ | 0.97 | 0.521 | 15597ms | full_rag | 我们提供以下三款蓝牙耳塞（Bluetooth earbuds）：  1. **S |
| 27 | EN | How much is StarPods Pro ... | price_inquiry | bulk_inquiry | ✗ | 0.95 | 0.000 | 2764ms | lead_capture | 请问大概的采购数量是多少？ |
| 28 | EN | Do you support OEM custom... | product_info | custom_request | ✗ | 0.97 | 0.000 | 2916ms | lead_capture | 请问大概的采购数量是多少？ |
| 29 | EN | What's your MOQ for the s... | bulk_inquiry | bulk_inquiry | ✓ | 0.97 | 0.000 | 2993ms | lead_capture | 请问大概的采购数量是多少？ |
| 30 | EN | Can you ship to the US? W... | policy_query | multi_intent | ✗ | 0.92 | 0.531 | 11756ms | full_rag | 是的，我们可以发货到美国。   提供的运输方式包括：   - 快递（DHL、Fe |

## 意图分类偏差分析

- **#4** "你是人工还是机器人？" → 期望 `bot_identity`，实际 `transfer_explicit` (置信度 0.99)
- **#7** "StarPods Pro 多少钱？批量价呢？" → 期望 `price_inquiry`，实际 `multi_intent` (置信度 0.92)
- **#11** "充电宝支持快充吗？最大输出多少瓦？" → 期望 `product_info`，实际 `multi_intent` (置信度 0.92)
- **#13** "怎么付款？支持信用证吗？" → 期望 `policy_query`，实际 `multi_intent` (置信度 0.92)
- **#27** "How much is StarPods Pro in bulk?" → 期望 `price_inquiry`，实际 `bulk_inquiry` (置信度 0.95)
- **#28** "Do you support OEM customization?" → 期望 `product_info`，实际 `custom_request` (置信度 0.97)
- **#30** "Can you ship to the US? What are the shipping options?" → 期望 `policy_query`，实际 `multi_intent` (置信度 0.92)