# 端到端测试报告
日期：2026-04-13 18:39
Bot ID：68887b76-93f7-4886-ba3f-bf85dbda5eb8
知识库：test_product_kb.txt + 5 条 FAQ

## 总体指标
- 测试用例数：30
- 意图分类准确数：29/30 (97%)
- 错误/超时数：0
- L2 平均 Grader 分数：0.571
- 平均延迟：6084ms
- 缓存命中：0
- 总 Token 消耗：3230

## 按类别统计
- **L1**: 5/5 准确, 平均 4714ms
- **L2**: 10/10 准确, 平均 7288ms
- **L3**: 3/3 准确, 平均 3529ms
- **L4**: 3/3 准确, 平均 5320ms
- **L5**: 4/4 准确, 平均 5744ms
- **EN**: 4/5 准确, 平均 7306ms

## 详细记录

| # | 类别 | 问题 | 期望意图 | 实际意图 | 匹配 | 置信度 | Grader | 延迟 | Exit | 备注 |
|---|------|------|---------|---------|------|--------|--------|------|------|------|
| 1 | L1 | 你好 | greeting | greeting | ✓ | 0.95 | 0.000 | 3631ms | l1_direct | 您好！欢迎联系星辰电子客服～😊   请问有什么可以帮您？比如产品咨询、报价、定制 |
| 2 | L1 | Hi, good morning | greeting | greeting | ✓ | 0.99 | 0.000 | 3460ms | l1_direct | Good morning! 🌞   How can I assist you t |
| 3 | L1 | 谢谢，没问题了 | farewell | farewell | ✓ | 0.99 | 0.000 | 4670ms | l1_direct | 不客气！😊 如有任何后续问题，或需要协助下单、查询产品信息，随时欢迎联系星辰电子 |
| 4 | L1 | 你是人工还是机器人？ | bot_identity | bot_identity | ✓ | 0.92 | 0.000 | 4539ms | l1_direct | 您好，我是星辰电子的AI智能客服助手——专业、高效、7×24小时在线为您提供服务 |
| 5 | L1 | 你能做什么？ | capability | capability | ✓ | 0.99 | 0.000 | 7268ms | l1_direct | 您好！我是星辰电子客服，专注于为您提供专业、高效的电子元器件及智能硬件相关服务。 |
| 6 | L2 | 你们有哪些蓝牙耳机？ | product_info | product_info | ✓ | 0.97 | 0.642 | 12646ms | full_rag | 我们目前提供以下三款蓝牙耳机：  1. **StarPods Pro（旗舰款）* |
| 7 | L2 | StarPods Pro 多少钱？批量价呢？ | price_inquiry | price_inquiry | ✓ | 0.97 | 0.659 | 9654ms | full_rag | StarPods Pro 零售价为 $45.99/台。   批量采购价格如下：  |
| 8 | L2 | SP-100 和 SL-200 有什么区别？ | comparison | comparison | ✓ | 0.97 | 0.463 | 12256ms | full_rag | SP-100（StarPods Pro 旗舰款）与 SL-200（StarPod |
| 9 | L2 | 有没有防水的运动耳机？ | product_info | product_info | ✓ | 0.92 | 0.606 | 4409ms | full_rag | 有，StarPods Sport（运动款）是专为运动设计的防水耳机，具备IP67 |
| 10 | L2 | 智能手表的续航多长时间？ | product_info | product_info | ✓ | 0.92 | 0.583 | 3511ms | full_rag | 智能手表（StarWatch Ultra，型号SW-500）的续航为：典型使用7 |
| 11 | L2 | 充电宝支持快充吗？最大输出多少瓦？ | product_info | product_info | ✓ | 0.92 | 0.569 | 7335ms | full_rag | 是的，充电宝支持快充。以StarPower 20000（型号PB-800）为例： |
| 12 | L2 | 你们的产品有什么认证？ | product_info | product_info | ✓ | 0.92 | 0.532 | 4782ms | full_rag | 我们的产品已通过以下认证：   - ISO9001质量管理体系认证   - CE |
| 13 | L2 | 怎么付款？支持信用证吗？ | policy_query | policy_query | ✓ | 0.85 | 0.572 | 3897ms | full_rag | 支持信用证（L/C）付款。   其他付款方式还包括：   - T/T（30%预付 |
| 14 | L2 | 交货期大概多久？ | availability | availability | ✓ | 0.92 | 0.496 | 7948ms | full_rag | 交货期取决于具体产品：  - StarWatch Ultra（SW-500）：下 |
| 15 | L2 | 退换货政策是什么？ | policy_query | policy_query | ✓ | 0.99 | 0.588 | 6446ms | full_rag | 退换货政策如下：   - DOA（到货损坏）：签收后7天内可免费换新；   -  |
| 16 | L3 | 我想采购一批蓝牙耳机 | purchase_intent | purchase_intent | ✓ | 0.97 | 0.000 | 4292ms | lead_capture | 请问大概的采购数量是多少？ |
| 17 | L3 | 我们公司需要定制5000个耳机，能打我们的LOGO | custom_request | custom_request | ✓ | 0.97 | 0.000 | 2770ms | lead_capture | 请问大概的采购数量是多少？ |
| 18 | L3 | I want to order 2000 unit... | bulk_inquiry | purchase_intent | ✓ | 0.99 | 0.000 | 3526ms | lead_capture | 请问大概的采购数量是多少？ |
| 19 | L4 | 我要投诉，上次买的耳机全是坏的 | complaint | complaint | ✓ | 0.99 | 0.565 | 6491ms | full_rag | 您好，很抱歉给您带来不便。根据售后政策，若耳机属于到货损坏（DOA），您可在收货 |
| 20 | L4 | 转人工客服 | transfer_explicit | transfer_explicit | ✓ | 0.98 | 0.000 | 1411ms | transfer | 我来帮您转接人工客服，请稍候。 |
| 21 | L4 | 很急！明天就要发货 | urgent | urgent | ✓ | 0.97 | 0.552 | 8057ms | full_rag | 明天发货需满足以下条件：   - 订单已确认且全款付清（T/T需70%尾款到账， |
| 22 | L5 | 帮我写一段Python代码 | out_of_scope | out_of_scope | ✓ | 0.99 | 0.000 | 1698ms | out_of_scope | 抱歉，这个问题超出了我的服务范围，请咨询相关专业人士。 |
| 23 | L5 | 今天股票怎么样？ | out_of_scope | out_of_scope | ✓ | 0.99 | 0.000 | 3071ms | out_of_scope | 抱歉，这个问题超出了我的服务范围，请咨询相关专业人士。 |
| 24 | L5 | 嗯 | acknowledgment | acknowledgment | ✓ | 0.99 | 0.000 | 4480ms | l1_direct | 您好！欢迎联系星辰电子客服～😊   请问您是想了解哪款电子产品？比如芯片、模组、 |
| 25 | L5 | 那价格呢？ | follow_up | price_inquiry | ✓ | 0.95 | 0.496 | 13726ms | full_rag | 商品价格取决于具体型号和采购数量，以下是各产品线的批量价参考：  - **Sta |
| 26 | EN | What Bluetooth earbuds do... | product_info | product_info | ✓ | 0.97 | 0.605 | 10247ms | full_rag | 我们提供三款蓝牙耳机：  1. **StarPods Pro（旗舰款）**    |
| 27 | EN | How much is StarPods Pro ... | price_inquiry | price_inquiry | ✓ | 0.92 | 0.663 | 6768ms | full_rag | StarPods Pro 的批量价格如下：   - 500–999台：$28/台 |
| 28 | EN | Do you support OEM custom... | product_info | product_info | ✓ | 0.92 | 0.559 | 6755ms | full_rag | Yes, we support OEM/ODM customization. S |
| 29 | EN | What's your MOQ for the s... | bulk_inquiry | price_inquiry | ✗ | 0.92 | 0.547 | 5308ms | full_rag | The MOQ for the smartwatch (StarWatch Ul |
| 30 | EN | Can you ship to the US? W... | policy_query | availability | ✓ | 0.92 | 0.546 | 7454ms | full_rag | 是的，我们可以发货到美国。    shipping options 包括：    |

## 意图分类偏差分析

- **#29** "What's your MOQ for the smartwatch?" → 期望 `bulk_inquiry`，实际 `price_inquiry` (置信度 0.92)