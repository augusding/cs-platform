# 端到端测试报告
日期：2026-04-13 12:09
Bot ID：68887b76-93f7-4886-ba3f-bf85dbda5eb8
知识库：test_product_kb.txt + 5 条 FAQ

## 总体指标
- 测试用例数：30
- 意图分类准确数：29/30 (97%)
- 错误/超时数：0
- L2 平均 Grader 分数：0.568
- 平均延迟：6776ms
- 缓存命中：0
- 总 Token 消耗：2913

## 按类别统计
- **L1**: 5/5 准确, 平均 2275ms
- **L2**: 10/10 准确, 平均 9096ms
- **L3**: 3/3 准确, 平均 3086ms
- **L4**: 3/3 准确, 平均 5473ms
- **L5**: 4/4 准确, 平均 5494ms
- **EN**: 4/5 准确, 平均 10661ms

## 详细记录

| # | 类别 | 问题 | 期望意图 | 实际意图 | 匹配 | 置信度 | Grader | 延迟 | Exit | 备注 |
|---|------|------|---------|---------|------|--------|--------|------|------|------|
| 1 | L1 | 你好 | greeting | greeting | ✓ | 0.95 | 0.000 | 1066ms | skip_retrieval | 您好！请问有什么可以帮您？ |
| 2 | L1 | Hi, good morning | greeting | greeting | ✓ | 0.99 | 0.000 | 3187ms | skip_retrieval | Good morning! How can I assist you today |
| 3 | L1 | 谢谢，没问题了 | farewell | farewell | ✓ | 0.99 | 0.000 | 3014ms | skip_retrieval | 不客气！如有其他问题，随时欢迎咨询。 |
| 4 | L1 | 你是人工还是机器人？ | bot_identity | bot_identity | ✓ | 0.92 | 0.000 | 1305ms | skip_retrieval | 我是智能客服助手，由系统自动提供服务。 |
| 5 | L1 | 你能做什么？ | capability | capability | ✓ | 0.99 | 0.000 | 2803ms | skip_retrieval | 这个问题我需要为您转接人工确认。 |
| 6 | L2 | 你们有哪些蓝牙耳机？ | product_info | product_info | ✓ | 0.97 | 0.649 | 10838ms | full_rag | 我们目前提供三款蓝牙耳机，分别是：  1. **StarPods Pro（旗舰款 |
| 7 | L2 | StarPods Pro 多少钱？批量价呢？ | price_inquiry | price_inquiry | ✓ | 0.92 | 0.703 | 8296ms | full_rag | StarPods Pro 零售价为 $45.99。  批量采购价格如下：   - |
| 8 | L2 | SP-100 和 SL-200 有什么区别？ | comparison | comparison | ✓ | 0.97 | 0.532 | 13566ms | full_rag | 参考资料中未提及型号 SP-100，仅详细列出了 SL-200（StarPods |
| 9 | L2 | 有没有防水的运动耳机？ | product_info | product_info | ✓ | 0.92 | 0.546 | 8205ms | full_rag | 有，StarPods Sport（运动款，型号SS-300）是专为运动设计的防水 |
| 10 | L2 | 智能手表的续航多长时间？ | product_info | product_info | ✓ | 0.92 | 0.566 | 6188ms | full_rag | 智能手表（StarWatch Ultra，型号SW-500）的续航为：   -  |
| 11 | L2 | 充电宝支持快充吗？最大输出多少瓦？ | product_info | product_info | ✓ | 0.92 | 0.595 | 10156ms | full_rag | 是的，StarPower 20000充电宝支持快充。   最大输出为：USB-C |
| 12 | L2 | 你们的产品有什么认证？ | product_info | product_info | ✓ | 0.92 | 0.460 | 7915ms | full_rag | 我们的产品已通过以下认证：  - ISO9001质量管理体系认证   - CE认 |
| 13 | L2 | 怎么付款？支持信用证吗？ | policy_query | policy_query | ✓ | 0.85 | 0.583 | 7054ms | full_rag | 付款方式支持T/T（30%预付+70%发货前付清）、L/C（信用证）和PayPa |
| 14 | L2 | 交货期大概多久？ | availability | availability | ✓ | 0.92 | 0.583 | 10650ms | full_rag | 交货期根据产品和订单数量不同，具体如下：  - 常规订单（如充电宝、部分耳机等） |
| 15 | L2 | 退换货政策是什么？ | policy_query | policy_query | ✓ | 0.99 | 0.467 | 8090ms | full_rag | 退换货政策如下：   - 仅接受质量问题导致的退换货；   - 非质量问题（如规 |
| 16 | L3 | 我想采购一批蓝牙耳机 | purchase_intent | purchase_intent | ✓ | 0.97 | 0.000 | 2385ms | lead_capture | 请问大概的采购数量是多少？ |
| 17 | L3 | 我们公司需要定制5000个耳机，能打我们的LOGO | custom_request | custom_request | ✓ | 0.97 | 0.000 | 3350ms | lead_capture | 请问大概的采购数量是多少？ |
| 18 | L3 | I want to order 2000 unit... | bulk_inquiry | purchase_intent | ✓ | 0.99 | 0.000 | 3524ms | lead_capture | 请问大概的采购数量是多少？ |
| 19 | L4 | 我要投诉，上次买的耳机全是坏的 | complaint | complaint | ✓ | 0.99 | 0.483 | 9531ms | full_rag | 您好，很抱歉给您带来不便。关于您购买的耳机出现全部故障的情况，请您通过以下方式联 |
| 20 | L4 | 转人工客服 | transfer_explicit | transfer_explicit | ✓ | 0.98 | 0.000 | 2ms | transfer | 我来帮您转接人工客服，请稍候。 |
| 21 | L4 | 很急！明天就要发货 | urgent | urgent | ✓ | 0.97 | 0.395 | 6886ms | full_rag | 很抱歉，所有产品线的最短交货期均为下单后10-15个工作日（如StarPower |
| 22 | L5 | 帮我写一段Python代码 | out_of_scope | out_of_scope | ✓ | 0.99 | 0.000 | 1575ms | out_of_scope | 抱歉，这个问题超出了我的服务范围，请咨询相关专业人士。 |
| 23 | L5 | 今天股票怎么样？ | out_of_scope | out_of_scope | ✓ | 0.99 | 0.000 | 1659ms | out_of_scope | 抱歉，这个问题超出了我的服务范围，请咨询相关专业人士。 |
| 24 | L5 | 嗯 | acknowledgment | acknowledgment | ✓ | 0.99 | 0.000 | 2499ms | skip_retrieval | 您好！请问有什么可以帮您的？ |
| 25 | L5 | 那价格呢？ | follow_up | price_inquiry | ✓ | 0.97 | 0.536 | 16242ms | full_rag | 请问您具体咨询的是哪款产品？目前资料中包含以下几款产品的价格信息：  - **S |
| 26 | EN | What Bluetooth earbuds do... | product_info | product_info | ✓ | 0.97 | 0.521 | 14391ms | full_rag | 我们目前提供三款蓝牙真无线耳塞（TWS），均来自StarPods系列：  1.  |
| 27 | EN | How much is StarPods Pro ... | price_inquiry | price_inquiry | ✓ | 0.92 | 0.707 | 7912ms | full_rag | StarPods Pro 的批量价格如下：   - 500–999台：$28/台 |
| 28 | EN | Do you support OEM custom... | product_info | product_info | ✓ | 0.92 | 0.523 | 9813ms | full_rag | Yes, we support OEM/ODM customization. S |
| 29 | EN | What's your MOQ for the s... | bulk_inquiry | price_inquiry | ✗ | 0.92 | 0.524 | 9085ms | full_rag | 智能手表的起订量（MOQ）为5000台。 |
| 30 | EN | Can you ship to the US? W... | policy_query | availability | ✓ | 0.92 | 0.531 | 12103ms | full_rag | 是的，我们可以发货到美国。   提供的运输方式包括：快递（DHL/FedEx/U |

## 意图分类偏差分析

- **#29** "What's your MOQ for the smartwatch?" → 期望 `bulk_inquiry`，实际 `price_inquiry` (置信度 0.92)