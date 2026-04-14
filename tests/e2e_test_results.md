# E2E Test Report v2
Date: 2026-04-14 16:43
Bot ID: 68887b76-93f7-4886-ba3f-bf85dbda5eb8

## Summary
- **Single-turn**: 28/30 pass (93%)
- **Multi-turn cases**: 9/9 full pass
- **Multi-turn turns**: 20/20 turns pass
- **Hallucination tests**: 3/5 pass

## Single-turn Results

| ID | Category | Query | Intent | Checks | Latency | Pass |
|----|---|---|---|---|---|---|
| S01 | L1 | 你好 | greeting | 2/2 | 4134ms | ✓ |
| S02 | L1 | 你是谁 | bot_identity | 1/1 | 4691ms | ✓ |
| S03 | L1 | 你能做什么？ | capability | 1/1 | 9210ms | ✓ |
| S04 | L1 | 你是人工还是机器人？ | bot_identity | 1/1 | 5562ms | ✓ |
| S05 | L1 | 谢谢 | farewell | 1/1 | 5267ms | ✓ |
| S06 | L2 | 你们有哪些产品？ | product_info | 1/1 | 8056ms | ✓ |
| S07 | L2 | StarPods Pro 多少钱？ | price_inquiry | 1/1 | 10253ms | ✓ |
| S08 | L2 | StarPods Pro 多少钱？批量价呢？ | price_inquiry | 1/1 | 13090ms | ✓ |
| S09 | L2 | 有没有防水的运动耳机？ | product_info | 1/1 | 4983ms | ✓ |
| S10 | L2 | SP-100 和 SL-200 有什么区别？ | comparison | 1/1 | 6541ms | ✓ |
| S11 | L2 | 智能手表续航多久？ | product_info | 1/1 | 6222ms | ✓ |
| S12 | L2 | 充电宝支持快充吗？ | product_info | 1/1 | 7281ms | ✓ |
| S13 | L2 | 交货期大概多久？ | availability | 1/1 | 9763ms | ✓ |
| S14 | L2 | 怎么付款？支持信用证吗？ | policy_query | 1/1 | 5081ms | ✓ |
| S15 | L2 | 可以定制 LOGO 吗？ | product_info | 1/1 | 5318ms | ✓ |
| S16 | EN | What products do you have? | product_info | 1/1 | 7761ms | ✓ |
| S17 | EN | How much is StarPods Pro? | price_inquiry | 1/1 | 7975ms | ✓ |
| S18 | EN | What's your MOQ for the smartw | price_inquiry | 1/1 | 10515ms | ✓ |
| S19 | EN | Can you ship to the US? | availability | 1/1 | 9374ms | ✓ |
| S20 | EN | Do you support OEM customizati | product_info | 1/1 | 9297ms | ✓ |
| S21 | L4 | 我要投诉！你们产品质量太差了！ | transfer_implicit | — | 4ms | ✓ |
| S22 | L4 | 我订单号 2024001 物流到哪了？ | follow_up | — | 9155ms | ✓ |
| S23 | L4 | 产品坏了怎么办？ | policy_query | 1/1 | 6693ms | ✓ |
| S24 | L5 | 帮我写一首诗 | out_of_scope | — | 2610ms | ✓ |
| S25 | L5 | 你们的股票代码是多少？ | out_of_scope | — | 1762ms | ✓ |
| S26 | HALLU | SL-900 价格多少？ | price_inquiry | 3/3 | 9700ms | ✓ |
| S27 | HALLU | 你们有没有VR眼镜？ | availability | 3/3 | 9735ms | ✓ |
| S28 | HALLU | 你们的代理政策是什么？返点多少？ | policy_query | 3/4 | 6600ms | ✗ |
| S29 | HALLU | 西班牙可以做独家代理吗？给多少返点？ | multi_intent | 2/3 | 14054ms | ✗ |
| S30 | HALLU | 签独家代理协议的条件是什么？ | policy_query | 3/3 | 5350ms | ✓ |

## Multi-turn Results

### M01 产品咨询追问链 ✓

- **T1** ✓ `你们有什么蓝牙耳机？`
  - answer: 我们目前主推三款蓝牙耳机哈～   旗舰款StarPods Pro，带40dB主动降噪和LDAC高清解码，音质和体验都很稳；   性价比款StarPods Lite，轻巧省电，适合日常通勤用；   还有专为运动设计的StarPods Spor
- **T2** ✓ `Pro 那款多少钱？`
  - answer: StarPods Pro的零售价是$45.99，不过如果您有批量采购需求的话，价格可以按起订量来谈～   比如订500台是$28/台，1000台起降到$24/台，5000台以上还能到$21/台。   您这边大概需要多少台呀？我帮您算个具体报
- **T3** ✓ `那运动款呢？`
  - answer: StarPods Sport运动款的零售价是$35.99，不过批量采购的话价格很灵活～   起订500台是$22/台，1000台起降到$19/台，5000台以上能做到$16/台。   交货期是下单后15–20个工作日，还带12个月保修哈～ 
- **T4** ✓ `有防水吗？`
  - answer: 有的，StarPods Sport运动款是IP67级防水，不仅防汗防雨，还能用水直接冲洗，运动后冲一冲完全没问题～   而且耳挂式设计+单耳7.8g的轻量化，跑步、跳操都稳稳不掉。   您是打算用在什么场景呀？比如健身房、户外跑步，还是团队

### M02 AI追问-用户回答（上下文理解） ✓

- **T1** ✓ `智能手表的价格？`
  - answer: 智能手表目前主推的是StarWatch Ultra（型号SW-500），零售价是$89.99，批量采购的话，300台起订，价格从$52/台起，量越大单价越低哦～您是打算做分销还是贴牌合作呢？
- **T2** ✓ `大概500台`
  - answer: 500台的话，刚好落在300–999台的批量区间，StarWatch Ultra（SW-500）单价是$52/台，总价就是$26,000。这个价格含12个月保修和标准包装，支持LOGO丝印哦～您对颜色或包装有特别需求吗？

### M03 情绪升级-主动安抚 ✓

- **T1** ✓ `你们有代理政策吗？`
  - answer: 关于代理政策，这个问题我需要和业务团队确认后回复您，方便留个联系方式吗？
- **T2** ✓ `太傻了算了`
  - answer: 我注意到您可能需要更专业的帮助，建议转接人工客服，是否需要？

### M04 重复回答检测 ✓

- **T1** ✓ `你们支持区域代理吗？`
  - answer: 关于区域代理合作，这个问题我需要和业务团队确认后回复您，方便留个联系方式吗？
- **T2** ✓ `我问的是能不能做代理`
  - answer: 目前我们主要面向批发客户和品牌合作，区域代理需要结合当地市场情况、销售能力及合作规模来综合评估呢。您是打算在哪个地区开展业务呀？方便我帮您看看适配方案～
  - similarity_to_prev: 0.22

### M05 Lead capture首消息预提取 ✓

- **T1** ✓ `我想订购2000台SP-100，要印我们的LOGO`
  - answer: 请问您的目标价格或预算是多少？

### M06 语言切换 ✓

- **T1** ✓ `你们有什么产品？`
  - answer: 我们主要做三类消费电子产品：蓝牙耳机、智能手表和便携式充电宝哈～   比如蓝牙耳机有旗舰款StarPods Pro（带主动降噪）和高性价比的StarPods Lite；智能手表主打健康监测的StarWatch Ultra，支持血氧、心率、G
- **T2** ✓ `Tell me about StarPods Pro briefly`
  - answer: StarPods Pro是我们的旗舰蓝牙耳机，型号SP-100，用的是高通QCC5141芯片，支持40dB深度主动降噪（ANC）和LDAC高清音频解码，单次续航8小时、配合充电盒能用36小时，IPX5防水，单耳才5.2克，戴起来挺轻的～  

### M07 Lead capture - 用户反问价格 ✓

- **T1** ✓ `我想订购 SP-100`
  - answer: 请问大概的采购数量是多少？
- **T2** ✓ `20000`
  - answer: 好的，目标价格方面，请问您的目标价格或预算是多少？
- **T3** ✓ `你们能给什么价格`
  - answer: SP-100（StarPods Pro）采购20000台，按批量价表，5000台以上为$21/台，您这个数量可享该档位价格。   此外，支持OEM/ODM定制（如LOGO印刷、包装等），起订量不受影响。   这个价位您觉得是否符合预期？方便

### M08 Lead capture - 用户拒绝回答 ✓

- **T1** ✓ `我想采购蓝牙耳机`
  - answer: 请问大概的采购数量是多少？
- **T2** ✓ `数量还没定`
  - answer: 没问题，那关于目标价格，请问您的目标价格或预算是多少？

### M09 Lead capture - 用户不耐烦 ✓

- **T1** ✓ `我想做区域代理`
  - answer: 请问您需要什么产品或有什么具体要求？
- **T2** ✓ `问这么多干嘛`
  - answer: 抱歉问多了！最后一个问题——方便留个联系方式吗？邮箱或 WhatsApp 就行，我们直接给您发报价，就不用再这样来回了。

## Failed Single-turn Cases

- **S28** `你们的代理政策是什么？返点多少？`
  - answer: 关于代理政策和返点方案，这个问题我需要和业务团队确认后回复您，方便留个联系方式吗？
  - FAIL not_contain: 返点
- **S29** `西班牙可以做独家代理吗？给多少返点？`
  - answer: 关于西班牙独家代理和返点政策，这个问题我需要和业务团队确认后回复您，方便留个联系方式吗？
  - FAIL not_contain: 返点
