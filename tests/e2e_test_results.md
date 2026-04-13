# 端到端测试报告
日期：2026-04-13 22:21
Bot ID：68887b76-93f7-4886-ba3f-bf85dbda5eb8
知识库：test_product_kb.txt + 5 条 FAQ

## 总体指标
- 测试用例数：30
- 意图分类准确数：29/30 (97%)
- 错误/超时数：0
- L2 平均 Grader 分数：0.586
- 平均延迟：8108ms
- 缓存命中：0
- 总 Token 消耗：5233

## 按类别统计
- **L1**: 5/5 准确, 平均 4788ms
- **L2**: 10/10 准确, 平均 10532ms
- **L3**: 3/3 准确, 平均 3470ms
- **L4**: 3/3 准确, 平均 6500ms
- **L5**: 4/4 准确, 平均 6838ms
- **EN**: 4/5 准确, 平均 11343ms

## 详细记录

| # | 类别 | 问题 | 期望意图 | 实际意图 | 匹配 | 置信度 | Grader | 延迟 | Exit | 备注 |
|---|------|------|---------|---------|------|--------|--------|------|------|------|
| 1 | L1 | 你好 | greeting | greeting | ✓ | 0.95 | 0.000 | 3978ms | l1_direct | 您好！欢迎联系星辰电子客服，我是您的AI助手。请问有什么可以帮您？😊 |
| 2 | L1 | Hi, good morning | greeting | greeting | ✓ | 0.99 | 0.000 | 3604ms | l1_direct | Good morning! 🌞 How can I assist you wit |
| 3 | L1 | 谢谢，没问题了 | farewell | farewell | ✓ | 0.99 | 0.000 | 4748ms | l1_direct | 不客气！如有任何采购需求或疑问，随时欢迎联系星辰电子客服～祝您工作顺利，生意兴隆 |
| 4 | L1 | 你是人工还是机器人？ | bot_identity | bot_identity | ✓ | 0.92 | 0.000 | 3420ms | l1_direct | 您好，我是星辰电子的AI智能客服助手，不是人工客服，但能为您提供专业、高效的产品 |
| 5 | L1 | 你能做什么？ | capability | capability | ✓ | 0.99 | 0.000 | 8191ms | l1_direct | 您好！我是星辰电子客服，专注为您提供以下服务：  ✅ 产品咨询：芯片、模组、传感 |
| 6 | L2 | 你们有哪些蓝牙耳机？ | product_info | product_info | ✓ | 0.97 | 0.642 | 22783ms | full_rag | 我们目前提供以下三款蓝牙耳机，分别针对不同使用场景和需求：  **1. Star |
| 7 | L2 | StarPods Pro 多少钱？批量价呢？ | price_inquiry | price_inquiry | ✓ | 0.97 | 0.659 | 12389ms | full_rag | StarPods Pro（型号：SP-100）价格如下：  - **零售价**： |
| 8 | L2 | SP-100 和 SL-200 有什么区别？ | comparison | comparison | ✓ | 0.97 | 0.463 | 14929ms | full_rag | SP-100（StarPods Pro 旗舰款）与 SL-200（StarPod |
| 9 | L2 | 有没有防水的运动耳机？ | product_info | product_info | ✓ | 0.97 | 0.606 | 9679ms | full_rag | 有，以下是专为运动设计且具备防水功能的耳机型号：  **StarPods Spo |
| 10 | L2 | 智能手表的续航多长时间？ | product_info | product_info | ✓ | 0.92 | 0.739 | 6974ms | full_rag | 根据现有信息，智能手表的续航时间因型号而异。以 StarWatch Ultra（ |
| 11 | L2 | 充电宝支持快充吗？最大输出多少瓦？ | product_info | product_info | ✓ | 0.92 | 0.559 | 9689ms | full_rag | 是的，该充电宝支持快充。  以 StarPower 20000（型号：PB-80 |
| 12 | L2 | 你们的产品有什么认证？ | product_info | product_info | ✓ | 0.92 | 0.532 | 6602ms | full_rag | 我们的产品已通过以下认证：  - ISO9001 质量管理体系认证   - CE |
| 13 | L2 | 怎么付款？支持信用证吗？ | policy_query | policy_query | ✓ | 0.85 | 0.572 | 5100ms | full_rag | 付款方式如下：  - **T/T（电汇）**：30%预付款，70%在发货前付清  |
| 14 | L2 | 交货期大概多久？ | availability | availability | ✓ | 0.92 | 0.496 | 10188ms | full_rag | 交货期根据具体产品如下：  - **StarWatch Ultra（SW-500 |
| 15 | L2 | 退换货政策是什么？ | policy_query | policy_query | ✓ | 0.99 | 0.588 | 6987ms | full_rag | 退换货政策如下：  - **DOA（到货损坏）**：收货后7天内确认为到货即损的 |
| 16 | L3 | 我想采购一批蓝牙耳机 | purchase_intent | purchase_intent | ✓ | 0.97 | 0.000 | 3924ms | lead_capture | 请问大概的采购数量是多少？ |
| 17 | L3 | 我们公司需要定制5000个耳机，能打我们的LOGO | custom_request | custom_request | ✓ | 0.97 | 0.000 | 3328ms | lead_capture | 请问大概的采购数量是多少？ |
| 18 | L3 | I want to order 2000 unit... | bulk_inquiry | purchase_intent | ✓ | 0.99 | 0.000 | 3158ms | lead_capture | 请问大概的采购数量是多少？ |
| 19 | L4 | 我要投诉，上次买的耳机全是坏的 | complaint | complaint | ✓ | 0.99 | 0.565 | 7989ms | full_rag | 您好，针对您反馈的“上次购买的耳机全是坏的”问题，我们提供以下处理方案：  -  |
| 20 | L4 | 转人工客服 | transfer_explicit | transfer_explicit | ✓ | 0.98 | 0.000 | 1056ms | transfer | 我来帮您转接人工客服，请稍候。 |
| 21 | L4 | 很急！明天就要发货 | urgent | urgent | ✓ | 0.97 | 0.552 | 10455ms | full_rag | 根据当前资料，最快可明天发货的产品是 **StarPower 20000 充电宝 |
| 22 | L5 | 帮我写一段Python代码 | out_of_scope | out_of_scope | ✓ | 0.99 | 0.000 | 2014ms | out_of_scope | 抱歉，这个问题超出了我的服务范围，请咨询相关专业人士。 |
| 23 | L5 | 今天股票怎么样？ | out_of_scope | out_of_scope | ✓ | 0.99 | 0.000 | 2986ms | out_of_scope | 抱歉，这个问题超出了我的服务范围，请咨询相关专业人士。 |
| 24 | L5 | 嗯 | acknowledgment | acknowledgment | ✓ | 0.99 | 0.000 | 5104ms | l1_direct | 您好！我是星辰电子客服，很高兴为您服务～   请问您是想了解哪款电子产品？比如芯 |
| 25 | L5 | 那价格呢？ | follow_up | price_inquiry | ✓ | 0.97 | 0.496 | 17246ms | full_rag | 商品价格根据具体产品型号和采购数量有所不同，以下是各款产品的零售价及批量采购价格 |
| 26 | EN | What Bluetooth earbuds do... | product_info | product_info | ✓ | 0.97 | 0.582 | 15188ms | full_rag | We offer three models of Bluetooth earbu |
| 27 | EN | How much is StarPods Pro ... | price_inquiry | price_inquiry | ✓ | 0.92 | 0.663 | 9621ms | full_rag | StarPods Pro (SP-100) bulk pricing is as |
| 28 | EN | Do you support OEM custom... | product_info | product_info | ✓ | 0.92 | 0.559 | 12785ms | full_rag | Yes, we support OEM/ODM customization. T |
| 29 | EN | What's your MOQ for the s... | bulk_inquiry | price_inquiry | ✗ | 0.92 | 0.547 | 9748ms | full_rag | The MOQ (Minimum Order Quantity) for the |
| 30 | EN | Can you ship to the US? W... | policy_query | availability | ✓ | 0.92 | 0.546 | 9375ms | full_rag | Yes, we can ship to the US.    **Shippin |

## 意图分类偏差分析

- **#29** "What's your MOQ for the smartwatch?" → 期望 `bulk_inquiry`，实际 `price_inquiry` (置信度 0.92)