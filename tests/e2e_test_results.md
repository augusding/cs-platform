# 端到端测试报告

日期：2026-04-13
Bot：星辰电子客服
知识库：test_product_kb.txt (1个文档 + 5条 FAQ)

## 总体指标

- 测试用例数：30
- 正确回答数：__/30
- L2 平均 Grader 分数：__
- L2 平均延迟：__ms
- 幻觉案例数：__
- 意图分类准确数：__/30

## 详细记录

| # | 问题 | 期望意图 | 实际意图 | 置信度 | Grader | 延迟 | 通过 | 备注 |
|---|------|---------|---------|--------|--------|------|------|------|
| 1 | 你好 | greeting | | | | | | |
| 2 | Hi, good morning | greeting | | | | | | |
| 3 | 谢谢，没问题了 | farewell | | | | | | |
| 4 | 你是人工还是机器人？ | bot_identity | | | | | | |
| 5 | 你能做什么？ | capability | | | | | | |
| 6 | 你们有哪些蓝牙耳机？ | product_info | | | | | | |
| 7 | StarPods Pro 多少钱？批量价呢？ | price_inquiry | | | | | | |
| 8 | SP-100 和 SL-200 有什么区别？ | comparison | | | | | | |
| 9 | 有没有防水的运动耳机？ | product_info | | | | | | |
| 10 | 智能手表的续航多长时间？ | product_info | | | | | | |
| 11 | 充电宝支持快充吗？最大输出多少瓦？ | product_info | | | | | | |
| 12 | 你们的产品有什么认证？ | policy_query | | | | | | |
| 13 | 怎么付款？支持信用证吗？ | policy_query | | | | | | |
| 14 | 交货期大概多久？ | availability | | | | | | |
| 15 | 退换货政策是什么？ | policy_query | | | | | | FAQ 命中 |
| 16 | 我想采购一批蓝牙耳机 | purchase_intent | | | | | | |
| 17 | 我们公司需要定制 5000 个耳机，能打我们的 LOGO | bulk_inquiry | | | | | | |
| 18 | I want to order 2000 units of SP-100 | purchase_intent | | | | | | |
| 19 | 我要投诉，上次买的耳机全是坏的 | complaint | | | | | | |
| 20 | 转人工客服 | transfer_explicit | | | | | | |
| 21 | 很急！明天就要发货 | urgent | | | | | | |
| 22 | 帮我写一段 Python 代码 | out_of_scope | | | | | | |
| 23 | 今天股票怎么样？ | out_of_scope | | | | | | |
| 24 | 嗯 | acknowledgment | | | | | | |
| 25 | 那价格呢？（追问） | follow_up | | | | | | |
| 26 | What Bluetooth earbuds do you have? | product_info | | | | | | |
| 27 | How much is StarPods Pro in bulk? | price_inquiry | | | | | | |
| 28 | Do you support OEM customization? | custom_request | | | | | | |
| 29 | What's your MOQ for the smartwatch? | bulk_inquiry | | | | | | |
| 30 | Can you ship to the US? | policy_query | | | | | | |

## 发现的问题

（测试过程中的 bug / 改进点）

## 结论

（整体评估）
