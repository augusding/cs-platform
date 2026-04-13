# E2E Test Report v2
Date: 2026-04-13 23:02
Bot ID: 68887b76-93f7-4886-ba3f-bf85dbda5eb8

## Summary
- **Single-turn**: 26/30 pass (87%)
- **Multi-turn cases**: 6/6 full pass
- **Multi-turn turns**: 13/13 turns pass
- **Hallucination tests**: 3/5 pass

## Single-turn Results

| ID | Category | Query | Intent | Checks | Latency | Pass |
|----|---|---|---|---|---|---|
| S01 | L1 | 你好 | greeting | 2/2 | 3791ms | ✓ |
| S02 | L1 | 你是谁 | bot_identity | 1/1 | 4207ms | ✓ |
| S03 | L1 | 你能做什么？ | capability | 1/1 | 7785ms | ✓ |
| S04 | L1 | 你是人工还是机器人？ | bot_identity | 1/1 | 4962ms | ✓ |
| S05 | L1 | 谢谢 | farewell | 1/1 | 3932ms | ✓ |
| S06 | L2 | 你们有哪些产品？ | product_info | 1/1 | 7113ms | ✓ |
| S07 | L2 | StarPods Pro 多少钱？ | price_inquiry | 1/1 | 7819ms | ✓ |
| S08 | L2 | StarPods Pro 多少钱？批量价呢？ | price_inquiry | 1/1 | 10862ms | ✓ |
| S09 | L2 | 有没有防水的运动耳机？ | product_info | 1/1 | 5842ms | ✓ |
| S10 | L2 | SP-100 和 SL-200 有什么区别？ | comparison | 1/1 | 7500ms | ✓ |
| S11 | L2 | 智能手表续航多久？ | product_info | 1/1 | 6395ms | ✓ |
| S12 | L2 | 充电宝支持快充吗？ | product_info | 1/1 | 7629ms | ✓ |
| S13 | L2 | 交货期大概多久？ | availability | 1/1 | 7419ms | ✓ |
| S14 | L2 | 怎么付款？支持信用证吗？ | policy_query | 1/1 | 4356ms | ✓ |
| S15 | L2 | 可以定制 LOGO 吗？ | product_info | 1/1 | 4812ms | ✓ |
| S16 | EN | What products do you have? | product_info | 1/1 | 7129ms | ✓ |
| S17 | EN | How much is StarPods Pro? | price_inquiry | 1/1 | 6429ms | ✓ |
| S18 | EN | What's your MOQ for the smartw | price_inquiry | 1/1 | 6421ms | ✓ |
| S19 | EN | Can you ship to the US? | availability | 1/1 | 7759ms | ✓ |
| S20 | EN | Do you support OEM customizati | product_info | 1/1 | 7123ms | ✓ |
| S21 | L4 | 我要投诉！你们产品质量太差了！ | transfer_implicit | — | 4ms | ✓ |
| S22 | L4 | 产品坏了怎么办？ | policy_query | 1/1 | 5277ms | ✗ |
| S23 | L5 | 今天天气怎么样？ | chitchat | — | 6235ms | ✗ |
| S24 | L5 | 帮我写一首诗 | out_of_scope | — | 2725ms | ✓ |
| S25 | L5 | 你们的股票代码是多少？ | out_of_scope | — | 1578ms | ✓ |
| S26 | HALLU | SL-900 价格多少？ | price_inquiry | 3/3 | 7962ms | ✓ |
| S27 | HALLU | 你们有没有VR眼镜？ | product_info | 3/3 | 7480ms | ✓ |
| S28 | HALLU | 你们的代理政策是什么？返点多少？ | policy_query | 3/4 | 5964ms | ✗ |
| S29 | HALLU | 西班牙可以做独家代理吗？给多少返点？ | multi_intent | 2/3 | 10981ms | ✗ |
| S30 | HALLU | 签独家代理协议的条件是什么？ | policy_query | 3/3 | 5056ms | ✓ |

## Multi-turn Results

### M01 产品咨询追问链 ✓

- **T1** ✓ `你们有什么蓝牙耳机？`
  - answer: 我们目前主推三款蓝牙耳机哈～   旗舰款StarPods Pro，带40dB主动降噪和LDAC高清解码，适合对音质和降噪要求高的用户；   性价比款StarPods Lite，轻巧省电，日常通勤完全够用；   还有专为运动设计的StarPo
- **T2** ✓ `Pro 那款多少钱？`
  - answer: StarPods Pro的零售价是$45.99，不过如果您有批量采购需求的话，价格可以按起订量来谈～   比如500台起订是$28/台，1000台以上还能再优惠。您大概要多少台呀？
- **T3** ✓ `那运动款呢？`
  - answer: 运动款是StarPods Sport（型号SS-300），耳挂式设计+IP67防水，跑步出汗也不怕掉～   零售价是$35.99，批量采购的话500台起订，$22/台；1000台以上能到$19/台，5000台以上只要$16/台。   您是打
- **T4** ✓ `有防水吗？`
  - answer: 有的，StarPods Sport（SS-300）是IP67级防水，不仅防汗防雨，还能用清水冲洗，运动出汗或者小雨天使用都完全没问题～   这款耳挂式设计+IP67防水，特别适合跑步、健身这类高强度场景。您对颜色有偏好吗？目前有黑色和橙色可

### M02 AI追问-用户回答（上下文理解） ✓

- **T1** ✓ `智能手表的价格？`
  - answer: 智能手表目前主推的是StarWatch Ultra（型号SW-500），零售价是$89.99，批量采购的话，300台起订，价格从$52/台起，量越大单价越低哦～您是打算做分销还是贴牌合作呢？
- **T2** ✓ `大概500台`
  - answer: 500台的话，刚好落在300–999台的档位，StarWatch Ultra（SW-500）的批量价是$52/台，总价就是$26,000。这个价格含12个月保修，交货期是下单后20–25个工作日哈～您对颜色、包装或者LOGO定制有特别需求吗

### M03 情绪升级-主动安抚 ✓

- **T1** ✓ `你们有代理政策吗？`
  - answer: 关于代理政策，这个问题我需要和业务团队确认后回复您，方便留个联系方式吗？
- **T2** ✓ `太傻了算了`
  - answer: 我注意到您可能需要更专业的帮助，建议转接人工客服，是否需要？

### M04 重复回答检测 ✓

- **T1** ✓ `你们支持区域代理吗？`
  - answer: 关于区域代理合作，这个问题我需要和业务团队确认后回复您，方便留个联系方式吗？
- **T2** ✓ `我问的是能不能做代理`
  - answer: 目前我们主要面向企业客户开展OEM/ODM和批发合作，区域代理模式需要结合市场规划、销售能力及区域保护等细节来评估，这部分我得和业务负责人确认下具体政策。您是打算在哪个国家或地区开展呢？
  - similarity_to_prev: 0.21

### M05 Lead capture首消息预提取 ✓

- **T1** ✓ `我想订购2000台SP-100，要印我们的LOGO`
  - answer: 请问您的目标价格或预算是多少？

### M06 语言切换 ✓

- **T1** ✓ `你们有什么产品？`
  - answer: 我们主要做三类消费电子产品：蓝牙耳机、智能手表和便携式充电宝哈～   比如蓝牙耳机有旗舰款StarPods Pro（带主动降噪）和高性价比的StarPods Lite；智能手表主推StarWatch Ultra，支持心率、血氧、GPS和游泳
- **T2** ✓ `Tell me about StarPods Pro briefly`
  - answer: StarPods Pro是我们的旗舰蓝牙耳机，型号SP-100，用的是高通QCC5141芯片，支持40dB深度主动降噪（ANC），单次能听8小时，配充电盒总共36小时，还做到IPX5防水和轻至5.2g的佩戴感～   音质方面支持LDAC、a

## Failed Single-turn Cases

- **S22** `产品坏了怎么办？`
  - answer: 产品如果在保修期内出现故障，我们可以免费为您维修或更换哈～不过需要您承担一下来回的运费呢。  
如果是刚收到货就发现损坏（DOA），7天内我们直接免费换新哦！  
您方便说下是哪款产品、大概用了多久吗？我帮您看看具体怎么处理～
- **S23** `今天天气怎么样？`
  - answer: 哈哈，我这“电子客服”可没装天气预报模块～ 🌤️  
不过你要是想聊的是「产品发货会不会被雨淋湿」或者「夏天高温对电子元器件有没有影响」，那我可就来劲儿啦！😄  
需要帮你查某款产品的库存、交期，还是想看看定制服务怎么玩？随时喊我～
- **S28** `你们的代理政策是什么？返点多少？`
  - answer: 抱歉，代理政策和返点方案这部分我需要和业务团队确认后回复您，方便留个联系方式吗？
  - FAIL not_contain: 返点
- **S29** `西班牙可以做独家代理吗？给多少返点？`
  - answer: 关于西班牙独家代理和返点政策，这个问题我需要和业务团队确认后回复您，方便留个联系方式吗？
  - FAIL not_contain: 返点
