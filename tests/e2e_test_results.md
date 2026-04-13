# E2E Test Report v2
Date: 2026-04-14 07:36
Bot ID: 68887b76-93f7-4886-ba3f-bf85dbda5eb8

## Summary
- **Single-turn**: 28/30 pass (93%)
- **Multi-turn cases**: 6/6 full pass
- **Multi-turn turns**: 13/13 turns pass
- **Hallucination tests**: 3/5 pass

## Single-turn Results

| ID | Category | Query | Intent | Checks | Latency | Pass |
|----|---|---|---|---|---|---|
| S01 | L1 | 你好 | greeting | 2/2 | 3382ms | ✓ |
| S02 | L1 | 你是谁 | bot_identity | 1/1 | 4064ms | ✓ |
| S03 | L1 | 你能做什么？ | capability | 1/1 | 8292ms | ✓ |
| S04 | L1 | 你是人工还是机器人？ | bot_identity | 1/1 | 5186ms | ✓ |
| S05 | L1 | 谢谢 | farewell | 1/1 | 5284ms | ✓ |
| S06 | L2 | 你们有哪些产品？ | product_info | 1/1 | 6617ms | ✓ |
| S07 | L2 | StarPods Pro 多少钱？ | price_inquiry | 1/1 | 8217ms | ✓ |
| S08 | L2 | StarPods Pro 多少钱？批量价呢？ | price_inquiry | 1/1 | 10524ms | ✓ |
| S09 | L2 | 有没有防水的运动耳机？ | product_info | 1/1 | 6235ms | ✓ |
| S10 | L2 | SP-100 和 SL-200 有什么区别？ | comparison | 1/1 | 6228ms | ✓ |
| S11 | L2 | 智能手表续航多久？ | product_info | 1/1 | 6141ms | ✓ |
| S12 | L2 | 充电宝支持快充吗？ | product_info | 1/1 | 6590ms | ✓ |
| S13 | L2 | 交货期大概多久？ | availability | 1/1 | 8963ms | ✓ |
| S14 | L2 | 怎么付款？支持信用证吗？ | price_inquiry | 1/1 | 7540ms | ✓ |
| S15 | L2 | 可以定制 LOGO 吗？ | product_info | 1/1 | 5411ms | ✓ |
| S16 | EN | What products do you have? | product_info | 1/1 | 7272ms | ✓ |
| S17 | EN | How much is StarPods Pro? | price_inquiry | 1/1 | 7863ms | ✓ |
| S18 | EN | What's your MOQ for the smartw | price_inquiry | 1/1 | 7588ms | ✓ |
| S19 | EN | Can you ship to the US? | availability | 1/1 | 7659ms | ✓ |
| S20 | EN | Do you support OEM customizati | product_info | 1/1 | 7769ms | ✓ |
| S21 | L4 | 我要投诉！你们产品质量太差了！ | transfer_implicit | — | 2ms | ✓ |
| S22 | L4 | 我订单号 2024001 物流到哪了？ | availability | — | 7712ms | ✓ |
| S23 | L4 | 产品坏了怎么办？ | policy_query | 1/1 | 6002ms | ✓ |
| S24 | L5 | 帮我写一首诗 | out_of_scope | — | 3202ms | ✓ |
| S25 | L5 | 你们的股票代码是多少？ | out_of_scope | — | 1876ms | ✓ |
| S26 | HALLU | SL-900 价格多少？ | price_inquiry | 3/3 | 7793ms | ✓ |
| S27 | HALLU | 你们有没有VR眼镜？ | product_info | 3/3 | 8176ms | ✓ |
| S28 | HALLU | 你们的代理政策是什么？返点多少？ | policy_query | 3/4 | 6745ms | ✗ |
| S29 | HALLU | 西班牙可以做独家代理吗？给多少返点？ | multi_intent | 2/3 | 11605ms | ✗ |
| S30 | HALLU | 签独家代理协议的条件是什么？ | policy_query | 3/3 | 4765ms | ✓ |

## Multi-turn Results

### M01 产品咨询追问链 ✓

- **T1** ✓ `你们有什么蓝牙耳机？`
  - answer: 我们目前主推三款蓝牙耳机哈～   旗舰款StarPods Pro，带主动降噪和LDAC高清解码，音质和续航都挺不错的；性价比款StarPods Lite，轻巧省电，适合日常通勤用；还有专为运动设计的StarPods Sport，耳挂式+IP
- **T2** ✓ `Pro 那款多少钱？`
  - answer: StarPods Pro的零售价是$45.99，不过如果您有批量采购需求的话，价格可以按档位往下走～比如订500台起，单价是$28；订到1000台以上，能到$24/台；5000台以上就只要$21啦。   您大概要多少台呀？我帮您算个具体报价
- **T3** ✓ `那运动款呢？`
  - answer: StarPods Sport运动款的零售价是$35.99，批量采购的话，500台起订——   500到999台是$22/台，1000到4999台降到$19/台，5000台以上只要$16/台。   您这次大概想订多少台呀？我帮您看看能不能安排
- **T4** ✓ `有防水吗？`
  - answer: 有的哈～StarPods Sport运动款支持IP67级防水，意思是不仅能防汗防雨，还能用清水冲洗，日常运动出汗、淋小雨完全没问题。不过要注意的是，它不建议泡水或游泳使用哦。   您是打算在跑步、健身这类场景用吗？

### M02 AI追问-用户回答（上下文理解） ✓

- **T1** ✓ `智能手表的价格？`
  - answer: 智能手表目前主推的是 StarWatch Ultra（型号 SW-500），零售价是 $89.99，如果是批量采购的话，300台起订，价格从 $52/台起，订得越多单价越低，3000台以上能做到 $38/台。您是打算做分销还是贴牌合作呢？
- **T2** ✓ `大概500台`
  - answer: 500台的话，刚好落在300–999台的档位，单价是 $52/台，含12个月保修和IP68防水，交货期是下单后20–25个工作日。您看是需要安排打样确认，还是直接推进订单呢？

### M03 情绪升级-主动安抚 ✓

- **T1** ✓ `你们有代理政策吗？`
  - answer: 关于代理政策，目前我们更侧重于OEM/ODM贴牌合作和批量分销，暂未设立传统意义上的区域代理体系呢。不过如果您有稳定的销售渠道或想长期合作，我们可以根据您的体量和规划，定制专属的合作方案哈～   您是打算做品牌贴牌，还是想走分销模式呀？
- **T2** ✓ `太傻了算了`
  - answer: 我注意到您可能需要更专业的帮助，建议转接人工客服，是否需要？

### M04 重复回答检测 ✓

- **T1** ✓ `你们支持区域代理吗？`
  - answer: 关于区域代理合作，这个问题我需要和业务团队确认后回复您，方便留个联系方式吗？
- **T2** ✓ `我问的是能不能做代理`
  - answer: 目前我们主要面向企业客户开展OEM/ODM和批量采购合作，区域代理模式需要结合当地市场情况、销售能力及合作规模来综合评估。您是打算在哪个国家或地区开展代理呢？这样我帮您初步看看是否符合我们的合作方向～
  - similarity_to_prev: 0.19

### M05 Lead capture首消息预提取 ✓

- **T1** ✓ `我想订购2000台SP-100，要印我们的LOGO`
  - answer: 请问您的目标价格或预算是多少？

### M06 语言切换 ✓

- **T1** ✓ `你们有什么产品？`
  - answer: 哈，我们主要做三类消费电子产品：蓝牙耳机、智能手表和便携式充电宝呢～   比如蓝牙耳机有旗舰款StarPods Pro（带主动降噪）和高性价比的StarPods Lite；智能手表主打健康监测的StarWatch Ultra，支持血氧、心率
- **T2** ✓ `Tell me about StarPods Pro briefly`
  - answer: StarPods Pro是我们的旗舰蓝牙耳机，型号SP-100，用的是高通QCC5141芯片，支持40dB深度主动降噪（ANC），单次听歌8小时、配合充电盒能用36小时，还具备IPX5防水和蓝牙5.3，音质上兼容LDAC高清编码，单耳才5.

## Failed Single-turn Cases

- **S28** `你们的代理政策是什么？返点多少？`
  - answer: 哈，关于代理政策和返点方案，这个问题我需要和业务团队确认后回复您，方便留个联系方式吗？
  - FAIL not_contain: 返点
- **S29** `西班牙可以做独家代理吗？给多少返点？`
  - answer: 关于西班牙独家代理和返点政策，这个问题我需要和业务团队确认后回复您，方便留个联系方式吗？
  - FAIL not_contain: 返点
