# E2E Test Report v2
Date: 2026-04-14 15:55
Bot ID: 68887b76-93f7-4886-ba3f-bf85dbda5eb8

## Summary
- **Single-turn**: 28/30 pass (93%)
- **Multi-turn cases**: 8/9 full pass
- **Multi-turn turns**: 19/20 turns pass
- **Hallucination tests**: 3/5 pass

## Single-turn Results

| ID | Category | Query | Intent | Checks | Latency | Pass |
|----|---|---|---|---|---|---|
| S01 | L1 | 你好 | greeting | 2/2 | 4072ms | ✓ |
| S02 | L1 | 你是谁 | bot_identity | 1/1 | 4214ms | ✓ |
| S03 | L1 | 你能做什么？ | capability | 1/1 | 7981ms | ✓ |
| S04 | L1 | 你是人工还是机器人？ | bot_identity | 1/1 | 5736ms | ✓ |
| S05 | L1 | 谢谢 | farewell | 1/1 | 5062ms | ✓ |
| S06 | L2 | 你们有哪些产品？ | product_info | 1/1 | 11758ms | ✓ |
| S07 | L2 | StarPods Pro 多少钱？ | price_inquiry | 1/1 | 9054ms | ✓ |
| S08 | L2 | StarPods Pro 多少钱？批量价呢？ | price_inquiry | 1/1 | 10329ms | ✓ |
| S09 | L2 | 有没有防水的运动耳机？ | product_info | 1/1 | 4898ms | ✓ |
| S10 | L2 | SP-100 和 SL-200 有什么区别？ | comparison | 1/1 | 5561ms | ✓ |
| S11 | L2 | 智能手表续航多久？ | product_info | 1/1 | 5574ms | ✓ |
| S12 | L2 | 充电宝支持快充吗？ | product_info | 1/1 | 5894ms | ✓ |
| S13 | L2 | 交货期大概多久？ | availability | 1/1 | 8096ms | ✓ |
| S14 | L2 | 怎么付款？支持信用证吗？ | price_inquiry | 1/1 | 7636ms | ✓ |
| S15 | L2 | 可以定制 LOGO 吗？ | product_info | 1/1 | 4075ms | ✓ |
| S16 | EN | What products do you have? | product_info | 1/1 | 7124ms | ✓ |
| S17 | EN | How much is StarPods Pro? | price_inquiry | 1/1 | 6901ms | ✓ |
| S18 | EN | What's your MOQ for the smartw | price_inquiry | 1/1 | 7010ms | ✓ |
| S19 | EN | Can you ship to the US? | availability | 1/1 | 7002ms | ✓ |
| S20 | EN | Do you support OEM customizati | product_info | 1/1 | 6592ms | ✓ |
| S21 | L4 | 我要投诉！你们产品质量太差了！ | transfer_implicit | — | 2ms | ✓ |
| S22 | L4 | 我订单号 2024001 物流到哪了？ | follow_up | — | 8013ms | ✓ |
| S23 | L4 | 产品坏了怎么办？ | policy_query | 1/1 | 6446ms | ✓ |
| S24 | L5 | 帮我写一首诗 | out_of_scope | — | 2651ms | ✓ |
| S25 | L5 | 你们的股票代码是多少？ | out_of_scope | — | 1725ms | ✓ |
| S26 | HALLU | SL-900 价格多少？ | price_inquiry | 3/3 | 9416ms | ✓ |
| S27 | HALLU | 你们有没有VR眼镜？ | availability | 3/3 | 8375ms | ✓ |
| S28 | HALLU | 你们的代理政策是什么？返点多少？ | policy_query | 3/4 | 6319ms | ✗ |
| S29 | HALLU | 西班牙可以做独家代理吗？给多少返点？ | multi_intent | 2/3 | 10961ms | ✗ |
| S30 | HALLU | 签独家代理协议的条件是什么？ | policy_query | 3/3 | 4370ms | ✓ |

## Multi-turn Results

### M01 产品咨询追问链 ✓

- **T1** ✓ `你们有什么蓝牙耳机？`
  - answer: 我们目前主推三款蓝牙耳机：旗舰款StarPods Pro，主打主动降噪和高音质；性价比款StarPods Lite，轻便实惠，适合入门级需求；还有专为运动设计的StarPods Sport，耳挂式+IP67防水，跑步出汗也不怕。您更关注音质
- **T2** ✓ `Pro 那款多少钱？`
  - answer: StarPods Pro的零售价是$45.99，如果您有批量采购需求的话，500台起订，价格可以谈到$28/台；1000台以上还能再优惠，最低到$21/台。您大概要多少台呀？
- **T3** ✓ `那运动款呢？`
  - answer: StarPods Sport运动款的零售价是$35.99，批量采购的话，500台起订，价格可以谈到$22/台；1000台以上还能再优惠，最低到$16/台。您是打算做分销还是贴牌合作呀？
- **T4** ✓ `有防水吗？`
  - answer: 有的，StarPods Sport运动款支持IP67级防水，不仅防汗防雨，还能用水直接冲洗，运动后清洁特别方便。耳挂式设计+IP67防护，跑步、健身完全不用担心。您是打算自己用，还是有渠道要铺货呀？

### M02 AI追问-用户回答（上下文理解） ✓

- **T1** ✓ `智能手表的价格？`
  - answer: 智能手表目前主推的是 StarWatch Ultra（型号 SW-500），零售价是 $89.99，批量采购的话，300台起订，价格从 $52/台起，量越大单价越低，3000台以上能做到 $38/台。您是打算做分销还是贴牌合作呢？
- **T2** ✓ `大概500台`
  - answer: 500台的话，刚好落在300–999台的区间，单价是 $52/台，含12个月保修和IP68防水，交货期20–25个工作日。您看是需要我们安排样品先确认下品质，还是直接推进订单呢？

### M03 情绪升级-主动安抚 ✓

- **T1** ✓ `你们有代理政策吗？`
  - answer: 关于代理合作，我们目前没有统一的代理政策框架，但非常欢迎有实力的合作伙伴开展深度合作。您可以选择分销、贴牌（OEM/ODM）或区域联合推广等多种方式，具体权益我们会根据您的市场定位、订单规模和合作模式来灵活协商。  您这边是更倾向于做品牌分
- **T2** ✓ `太傻了算了`
  - answer: 我注意到您可能需要更专业的帮助，建议转接人工客服，是否需要？

### M04 重复回答检测 ✓

- **T1** ✓ `你们支持区域代理吗？`
  - answer: 关于区域代理合作，这个问题我需要和业务团队确认后回复您，方便留个联系方式吗？
- **T2** ✓ `我问的是能不能做代理`
  - answer: 目前我们主要面向企业客户开展OEM/ODM和批量采购合作，区域代理模式需要结合市场规划、销售能力、资金实力等综合评估，这部分政策我得和业务负责人确认下细节。您是打算在哪个国家或地区开展呢？方便我帮您对接对应区域的负责人哈～
  - similarity_to_prev: 0.22

### M05 Lead capture首消息预提取 ✓

- **T1** ✓ `我想订购2000台SP-100，要印我们的LOGO`
  - answer: 请问您的目标价格或预算是多少？

### M06 语言切换 ✓

- **T1** ✓ `你们有什么产品？`
  - answer: 我们主要做三类消费电子产品：蓝牙耳机、智能手表和便携式充电宝哈～   比如蓝牙耳机有旗舰款StarPods Pro（带主动降噪）和高性价比的StarPods Lite；智能手表主打健康监测的StarWatch Ultra，支持血氧、心率、G
- **T2** ✓ `Tell me about StarPods Pro briefly`
  - answer: StarPods Pro是我们的旗舰蓝牙耳机，型号SP-100，用的是高通QCC5141芯片，支持40dB深度主动降噪（ANC），单次续航8小时、配合充电盒能用36小时，IPX5防水，蓝牙5.3，还支持LDAC高清解码～   重量很轻，单耳

### M07 Lead capture - 用户反问价格 ✗

- **T1** ✓ `我想订购 SP-100`
  - answer: 请问大概的采购数量是多少？
- **T2** ✗ `20000`
  - answer: 好的，联系方式方面，方便留个邮箱或 WhatsApp 吗？我们安排业务同事给您发正式报价。
  - FAIL contain_any: ['价格', '预算', '目标价', 'price']
- **T3** ✓ `你们能给什么价格`
  - answer: SP-100（StarPods Pro）采购20000台，适用批量价：**$21/台**（5000台以上档位）。   该价格含标准包装、基础LOGO丝印（如需UV印或激光雕刻可免费升级）。   这个价位您觉得合适吗？方便留个邮箱或 What

### M08 Lead capture - 用户拒绝回答 ✓

- **T1** ✓ `我想采购蓝牙耳机`
  - answer: 请问大概的采购数量是多少？
- **T2** ✓ `数量还没定`
  - answer: 没问题，那关于目标价格，请问您的目标价格或预算是多少？

### M09 Lead capture - 用户不耐烦 ✓

- **T1** ✓ `我想做区域代理`
  - answer: 请问大概的采购数量是多少？
- **T2** ✓ `问这么多干嘛`
  - answer: 抱歉问多了！最后一个问题——方便留个联系方式吗？邮箱或 WhatsApp 就行，我们直接给您发报价，就不用再这样来回了。

## Failed Single-turn Cases

- **S28** `你们的代理政策是什么？返点多少？`
  - answer: 哈，关于代理政策和返点方案，这个问题我需要和业务团队确认后回复您，方便留个联系方式吗？
  - FAIL not_contain: 返点
- **S29** `西班牙可以做独家代理吗？给多少返点？`
  - answer: 关于西班牙独家代理和返点政策，这个问题我需要和业务团队确认后回复您，方便留个联系方式吗？
  - FAIL not_contain: 返点
