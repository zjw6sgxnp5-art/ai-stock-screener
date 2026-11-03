"""
Company Knowledge Base & Core Products Teardown Engine.
Breaks down hardware, software, ecosystem, technical barriers, market shares,
supply-chain dependency, and 1-3 year catalysts.
"""
from typing import Any, Dict, List, Optional
import json
import re
from backend.core.utils import normalize_symbol
from backend.db import get_cache, set_cache


# Pre-curated institutional teardown for core global technology and blue-chip leaders
PRESET_PRODUCT_KNOWLEDGE: Dict[str, Dict[str, Any]] = {
    "NVDA.US": {
        "essence": {
            "summary": "AI 时代底层算力军火商与全栈计算平台：以顶尖 GPU 架构与 NVLink 系统为硬件入口，以垄断级 CUDA 生态形成高转换壁垒，以全栈系统 (DGX/GB200) 变现全球 AI 资本开支。",
            "profit_engine": "【底层盈利真相】英伟达本质上不是单纯的半导体硬件销售商，而是‘软硬一体化的高毛利准垄断计算系统供应商’。通过长达 18 年沉淀的 CUDA 生态锁定全球数百万开发者，形成极高的软件替代成本，使硬件具备无与伦比的自主定价权 (Pricing Power)。数据中心 GPU 毛利率高达 75%~78%，净利率超 50%，将各大云巨头对算力的迫切需求转化为丰沛的自由现金流。",
            "flywheel": "先进制程与互联架构算力绝对领先 ➔ 垄断全球 AI 大模型首选训练平台 ➔ 全球数百万开发者代码深度绑定 CUDA 算力库 ➔ 锁定各大云厂商与主权 AI 的刚性预算 ➔ 产生天量现金流投入下一代 Blackwell/Rubin 架构 ➔ 巩固垄断优势。",
            "segments": [
                {"name": "数据中心与 AI 计算集群 (Data Center)", "ratio": "~85%~88% 营收", "role": "绝对增长核引擎：Hopper/Blackwell 架构 GPU 及 NVLink 网络系统，毛利率极高。"},
                {"name": "游戏与个人工作站 (Gaming & RTX)", "ratio": "~8%~10% 营收", "role": "现金流与图形基本盘：GeForce RTX 显卡，受益于端侧 AI PC 与游戏换代。"},
                {"name": "专业可视化与智能汽车 (ProViz & Auto)", "ratio": "~3%~5% 营收", "role": "长线战略期权：DRIVE Orin/Thor 自动驾驶芯片及 Omniverse 工业元宇宙孪生。"}
            ]
        },
        "industry": {
            "sector": "半导体前沿算力芯片与 AI 全栈计算集群 (AI Accelerators & Systems)",
            "macro_backdrop": "【宏观经济与周期研判】全球进入第四次工业革命与大模型军备竞赛，各大科技巨头 (Microsoft, Meta, Google, Amazon) 资本开支 (CapEx) 持续超预期爆发。尽管美联储利率高企，但 AI 基础设施投资具有刚性战略优先级，抗宏观周期下行能力极强。",
            "tam": "全球数据中心 AI 加速芯片与算力集群市场预计 2028 年超过 4,000 亿美元，复合年增长率 (CAGR) 高达 32%~38%。",
            "lifecycle": {
                "current_stage": "高速成长期 (Rapid Growth)",
                "stage_index": 1,
                "all_stages": [
                    {"name": "初创探索期", "desc": "3D 显卡图形渲染起步"},
                    {"name": "高速成长期", "desc": "生成式 AI 引爆数据中心算力狂飙"},
                    {"name": "成熟现金牛期", "desc": "全球算力装机饱和、进入存量维护更新"},
                    {"name": "转型再成长期", "desc": "全面切入主权 AI、工业具身智能与量子"},
                    {"name": "衰退防御期", "desc": "摩尔定律极限与技术替代"}
                ],
                "characteristics": "受全球大模型从训练走向千亿级推理的刚性驱动，业绩与自由现金流处于史上罕见的高斜率爆发期，在高端 AI 芯片市占率超过 85%~90%。",
                "is_good_or_bad": {
                    "pros": "好在全栈软硬件生态垄断力强劲，毛利率和资本回报率 (ROIC) 处于全球资本市场顶峰，拥有极高的订单锁定能见度。",
                    "cons": "坏在各大云巨头前五大客户集中度过高 (约 45%)，且各大客户均在加速研发自研 ASIC (TPU/Trainium) 试图摆脱‘英伟达税’；此外短期高基数下未来增速均值回归压力客观存在。"
                },
                "long_term_strategy": "适合成长型投资者在算力景气周期上行阶段重仓跟随，重点跟踪各大 CSP 资本开支指引及下一代架构供应链交付瓶颈。"
            },
            "competitors": [
                {
                    "symbol": "AMD.US",
                    "name": "AMD (超威半导体)",
                    "threat": "高",
                    "market_position": "全球唯二的通用高性能 GPU/CPU 挑战者",
                    "comparison": "MI300X/MI325X 在特定推理场景具备性价比优势，正在作为二供进入微软、Meta 等大客户供应链。",
                    "bj_differentiation": "【英伟达微观差异化突围】CUDA 18 年开发者软件生态护城河极深，代码迁移成本极高；NVLink 双向带宽与整机柜系统 (GB200 NVL72) 算力密度遥遥领先单一芯片拼装。"
                },
                {
                    "symbol": "GOOGL.US",
                    "name": "云巨头自研 ASIC (Google TPU / AWS Trainium)",
                    "threat": "中高",
                    "market_position": "超大规模云厂商内部降本与对冲手段",
                    "comparison": "云厂商通过自研芯片跑自有特定模型以降低对外采购成本，但对外部通用商业客户与前沿多模态大模型吸引力有限。",
                    "bj_differentiation": "【英伟达微观差异化突围】英伟达芯片具备通用性与灵活性，任何前沿算法变更无需重新流片；全行业绝大多数主流开源模型和初创公司默认第一适配英伟达。"
                },
                {
                    "symbol": "INTC.US",
                    "name": "Intel (英特尔)",
                    "threat": "弱",
                    "market_position": "传统 x86 霸主，算力转型挣扎中",
                    "comparison": "Gaudi 系列主打高性价比，但在大模型训练与开发者生态中市场占有率与存在感极度有限。",
                    "bj_differentiation": "【英伟达微观差异化突围】先进制程工艺迭代速度大幅领先，英伟达已经形成一年一迭代的摩尔定律超越节奏。"
                }
            ]
        },
        "products": [
            {
                "name": "Blackwell 架构 GPU 系统 (B200 / GB200 NVL72)",
                "category": "硬件终端 / 超级算力集群",
                "strategic_role": "核心增长引擎 (Growth Engine)",
                "revenue_ratio": "~85% 营收贡献",
                "gross_margin": "75%~78% 超高毛利",
                "s_curve_stage": "代际交替与产能爬坡爆发期 (S曲线陡峭段)",
                "switching_cost": "极高 (无平替方案 / 迁移即休克)",
                "barrier_type": "极限工程封装 + 独家 NVLink 互联协议",
                "barrier_detail": "台积电 4NP 定制工艺 + 双芯片晶圆级互联封装 (CoWoS-L) + 第五代 NVLink (1.8TB/s 双向互联带宽)，单机柜算力密度全球无竞品；竞品单卡拼装无法解决万卡集群通信墙与延迟。",
                "market_share": "全球高端 AI 训练加速芯片市占率约 85%~90%",
                "business_model": "高 ASP 单芯片及整机机柜销售，单台机柜售价数百万元，订单锁定度极高。",
                "prospect_and_catalysts": "未来 6~18 个月各大超大规模云厂商 (CSP) 与主权 AI 刚性采购基座，Blackwell 产能良率爬坡与下一代 Rubin (2026) 架构发布为核心催化剂。"
            },
            {
                "name": "CUDA 开发者并行计算平台 & cuDNN",
                "category": "平台与生态软件 (Ecosystem)",
                "strategic_role": "垄断级生态防御盾 (Moat Defense)",
                "revenue_ratio": "免费附赠绑定 + 衍生企业级订阅",
                "gross_margin": ">90% (纯软件极高毛利)",
                "s_curve_stage": "成熟统治级事实标准",
                "switching_cost": "极高 (代码迁移与调试隐性成本巨大)",
                "barrier_type": "代码生态与开发者网络效应 (Lock-in)",
                "barrier_detail": "长达 18 年技术沉淀，全球 450 万+ 开发者深度绑定；所有主流开源框架 (PyTorch, TensorFlow) 针对 CUDA 深度优化，将代码迁移至 AMD ROCm 存在难以逾越的调试成本与性能损耗风险。",
                "market_share": "AI 训练软件生态近乎 100% 事实标准",
                "business_model": "免费附赠构筑硬件护城河，同时通过 NVIDIA AI Enterprise 每年按 GPU 核心收取企业级订阅许可费 ($4500/GPU/年)。",
                "prospect_and_catalysts": "从底层库向生成式 AI 闭环 (NeMo / NIM 微服务) 延伸，软件高毛利 ARR 经常性收入持续提升。"
            },
            {
                "name": "Quantum-X InfiniBand & Spectrum-X 以太网",
                "category": "网络互联与集群系统 (Networking)",
                "strategic_role": "第二增长飞轮 (Synergy Flywheel)",
                "revenue_ratio": "~10%~12% 营收 (独立百亿美元体量)",
                "gross_margin": "65%~70% 硬件高毛利",
                "s_curve_stage": "以太网渗透爆发期",
                "switching_cost": "高 (系统拓扑深度绑定)",
                "barrier_type": "软硬结合低延迟互联通信协议",
                "barrier_detail": "独家收购 Mellanox 沉淀，解决万卡及十万卡算力集群网络延迟与丢包损耗痛点；Spectrum-X 打破传统以太网无法承载大模型通信的瓶颈，网络销售额已成为独立高增长板块。",
                "market_share": "万卡大模型集群网络市场份额超 75%",
                "business_model": "与 GPU 深度捆绑销售，极大提升单节点系统价值量 (ASP)。",
                "prospect_and_catalysts": "Spectrum-X 打入传统以太网数据中心市场，全面对冲纯 InfiniBand 局限，开辟企业级网络增量。"
            }
        ],
        "supply_chain": {
            "upstream_dependency": "高度依赖台积电 (TSMC) 先进封装 (CoWoS-L) 与先进晶圆代工，以及 SK海力士/美光的 HBM3e 高带宽内存供应。",
            "downstream_concentration": "前五大客户 (微软、Meta、亚马逊、Alphabet 等) 贡献约 40%~50% 营收，存在大客户自研芯片的潜在博弈。",
            "spof_bottlenecks": [
                {
                    "node": "台积电 CoWoS-L 晶圆级先进封装产能",
                    "threat_level": "高",
                    "impact": "全球唯一关键供应节点，封装产能排期直接决定英伟达单季度交付与营收上限。"
                },
                {
                    "node": "SK海力士 / 美光 HBM3E 内存堆叠良率与配额",
                    "threat_level": "中高",
                    "impact": "高带宽内存供应紧俏，任何厂商良率波动将波及整机柜出货节奏。"
                }
            ],
            "customer_bargaining": {
                "top_customers_share": "~45% 营收来自微软、Meta、亚马逊、Alphabet 四大超大规模云厂商",
                "in_house_threat": "中高：四大客户均在研发自研芯片 (Google TPU, AWS Trainium, 微软 Maia)，但目前仅能跑自有特定模型，对外部商业大模型训练仍 100% 依赖英伟达。",
                "pricing_power": "极高定价权：大客户暂无压价谈判筹码，订单排队周期超 6 个月。"
            },
            "geopolitical_and_resilience": "受美国对华先进芯片出口禁令限制，英伟达通过推出合规特供版 (H20) 维持市场份额，并大力拓展中东、欧洲及亚太主权 AI (Sovereign AI) 开辟新兴非美政府订单。"
        }
    },
    "AAPL.US": {
        "essence": {
            "summary": "全球消费电子与移动计算生态统治者：以极高忠诚度的高端硬件设备为锚点，以软硬件垂直整合为护城河，通过独家 iOS 数字服务生态持续收取高毛利订阅租金。",
            "profit_engine": "【底层盈利真相】苹果绝非普通硬件组装商。硬件（iPhone/Mac）主要负责在全球最富裕的中产与高净值人群中构筑难以割舍的数字生活底座；真正的超级造血利器是软件与服务业务 (Services)——毛利率高达 74% 以上，凭借全球超 22 亿台活跃设备基数，通过 App Store 佣金、iCloud 订阅、Apple Pay 等轻资产模式产生年超千亿美元的自由现金流，并全力用于股票注销式回购。",
            "flywheel": "极致工业设计与自研 A/M 芯片卓越体验 ➔ 扩大高净值活跃设备保有量 (Installed Base) ➔ 提升用户在 iOS 生态中的订阅与数字消费 ➔ 产生丰沛的高毛利自由现金流 ➔ 维持巨额研发与万亿回购拉升 EPS ➔ 巩固品牌神话。",
            "segments": [
                {"name": "iPhone 智能手机系列", "ratio": "~50%~52% 营收", "role": "生态核心锚点：高端市场绝对统治力，高频硬件换机入口。"},
                {"name": "数字服务生态 (Services: App Store/iCloud/Pay)", "ratio": "~24%~26% 营收", "role": "超级利润引擎：毛利率超 74%，抗周期经常性高毛利现金牛。"},
                {"name": "可穿戴及智能家居 (Apple Watch/AirPods)", "ratio": "~10% 营收", "role": "生态绑架器：多设备无缝流转，极大增加用户叛逃至安卓的成本。"},
                {"name": "Mac 电脑与 iPad 平板", "ratio": "~14% 营收", "role": "专业生产力工具：自研 M 系列芯片能效比无敌，锁定创作者与企业。"}
            ]
        },
        "industry": {
            "sector": "智能移动终端、边缘 AI 与高毛利数字平台服务 (Consumer Electronics & Ecosystem)",
            "macro_backdrop": "【宏观经济与周期研判】受全球高利率与消费周期放缓影响，智能手机大盘步入存量换机周期。但高收入阶层对高端旗舰机购买力坚韧，且端侧 Apple Intelligence 与隐私本地大模型正酝酿新一轮换机周期。",
            "tam": "全球个人智能计算终端与高端数字服务市场规模超过 1 万亿美元。",
            "lifecycle": {
                "current_stage": "成熟现金牛期 (Mature Cash Cow)",
                "stage_index": 2,
                "all_stages": [
                    {"name": "初创探索期", "desc": "个人电脑 Macintosh 时代"},
                    {"name": "高速成长期", "desc": "iPhone 问世颠覆全球移动互联网"},
                    {"name": "成熟现金牛期", "desc": "全球 22 亿设备基盘，充沛回购与服务变现"},
                    {"name": "转型再成长期", "desc": "端侧 Apple Intelligence 与空间计算 Vision Pro"},
                    {"name": "衰退防御期", "desc": "颠覆性硬件终端替代或生态被打破"}
                ],
                "characteristics": "商业模式登峰造极，客户转换成本极高，资产负债表极度健康，净现金充沛，每年超千亿美元股票回购注销，股东回报率极高。",
                "is_good_or_bad": {
                    "pros": "好在自由现金流几乎不受宏观衰退影响，拥有消费品级别的强大品牌定价权与护城河，是全球最具确定性的复利资产之一。",
                    "cons": "坏在硬件端在特定大市场（如大中华区）面临本土安卓及折叠屏分流竞争，且全球反垄断监管（欧盟 DMA 法案与美司法部调查）对 App Store 闭环生态形成持续压力。"
                },
                "long_term_strategy": "适合防御稳健型中长线资金在估值回调至历史合理分位时作为底仓长期持有，享受回购推动的 EPS 内生复合增长。"
            },
            "competitors": [
                {
                    "symbol": "Samsung",
                    "name": "Samsung (三星电子)",
                    "threat": "中",
                    "market_position": "全球出货量第一的安卓硬件巨头",
                    "comparison": "在折叠屏与硬件全产业链垂直整合（屏幕、存储）领先，但操作系统受制于 Google，生态粘性与单机利润池远逊于苹果。",
                    "bj_differentiation": "【苹果微观差异化突围】独家 iOS 软硬闭环与多设备互联体验无可匹敌，高端机利润份额霸占行业 80% 以上。"
                },
                {
                    "symbol": "GOOGL.US",
                    "name": "Alphabet (Google / Android)",
                    "threat": "中高",
                    "market_position": "全球移动操作系统底层盟主与 AI 前沿巨头",
                    "comparison": "掌控 Android 开源生态，Pixel 手机作为 AI 先锋不断试水，并在多模态模型能力上动作迅猛。",
                    "bj_differentiation": "【苹果微观差异化突围】主打端侧芯片隐私计算保护 (Private Cloud Compute)，对追求隐私安全的高净值用户形成绝对吸引力。"
                }
            ]
        },
        "products": [
            {
                "name": "iPhone 旗舰智能手机系列",
                "category": "硬件终端 / 移动计算入口",
                "strategic_role": "规模与现金流压舱石 (Cash Foundation)",
                "revenue_ratio": "~50%~52% 营收贡献",
                "gross_margin": "36%~39% 硬件稳健毛利",
                "s_curve_stage": "成熟存量平台期与端侧 AI 换机前夜",
                "switching_cost": "高 (生态依赖与数据迁移摩擦)",
                "barrier_type": "自研 A/M 芯片算力能效比 + 软硬件垂直整合闭环",
                "barrier_detail": "台积电 3nm 先进制程产能锁定，自研架构能效比超强；跨设备 AirDrop、iCloud 照片流协同把全球 10 亿+ 高净值中产死死锁在 iOS 围墙花园中。",
                "market_share": "全球高端机 ($800+) 市场占有率超 65%",
                "business_model": "硬件销售驱动，配合运营商合约分期与换新补贴计划。",
                "prospect_and_catalysts": "端侧 Apple Intelligence 与隐私本地混合模型驱动长达 2~3 年的存量超级换机潮。"
            },
            {
                "name": "数字服务生态 (Services: App Store / iCloud / Apple Pay)",
                "category": "平台服务与软件订阅 (Digital Ecosystem)",
                "strategic_role": "超级利润引擎 (Profit Engine)",
                "revenue_ratio": "~25% 营收贡献",
                "gross_margin": "74%~76% 超高毛利率",
                "s_curve_stage": "持续稳健收割期 (轻资产高确定性)",
                "switching_cost": "极高 (数字资产沉淀与支付习惯无法割舍)",
                "barrier_type": "双边网络效应 + 独家数字平台税",
                "barrier_detail": "坐拥全球超 22 亿台活跃设备基数，边际交付成本几乎为零；App Store 抽成、订阅佣金与金融手续费构成年超千亿美元自由现金流的核心缓冲垫。",
                "market_share": "iOS 生态拥有全球最高客单价与付费意愿群体",
                "business_model": "轻资产数字订阅与渠道抽成佣金，年化经常性收入 (ARR) 极高。",
                "prospect_and_catalysts": "全球反垄断监管为核心扰动，但总付费订阅量突破 10 亿大关，推动 ARPU 阶梯式跳升。"
            },
            {
                "name": "可穿戴与周边生态 (Apple Watch, AirPods, Mac, Vision Pro)",
                "category": "智能可穿戴与空间计算 (Wearables & Spatial)",
                "strategic_role": "生态绑架器与远期期权 (Ecosystem Binder)",
                "revenue_ratio": "~23% 营收贡献",
                "gross_margin": "34%~38% 硬件毛利",
                "s_curve_stage": "成熟配套 (Watch/AirPods) + 探索验证期 (Vision Pro)",
                "switching_cost": "高 (多设备协同无缝互联)",
                "barrier_type": "自研 M 系列芯片能效比 + 个人健康监测专利",
                "barrier_detail": "多设备无缝流转体验极大增加了用户换用安卓的隐性阻力；空间计算与微型传感器技术储备构筑下一代人机交互期权。",
                "market_share": "智能手表与真无线耳机全球出货量与利润第一",
                "business_model": "高频配件搭配硬件直销",
                "prospect_and_catalysts": "无创健康监测 (血糖/血压) 研发推进与平价版 Vision 空间头显为后续催化剂。"
            }
        ],
        "supply_chain": {
            "upstream_dependency": "高度依赖台积电代工独家 A/M 系列芯片，鸿海富士康组装整机，立讯精密/歌尔股份等精密零组件。",
            "downstream_concentration": "直面全球数十亿普通消费者及电信运营商渠道，无单一企业客户集中度违约风险。",
            "spof_bottlenecks": [
                {
                    "node": "台积电先进制程先发独占产能",
                    "threat_level": "中高",
                    "impact": "包揽台积电最新制程首发产能，虽然议价权极强，但制造节点高度依赖台湾单一地缘区域。"
                },
                {
                    "node": "组装代工厂产能地缘集中度",
                    "threat_level": "中",
                    "impact": "组装过去集中于中国大陆富士康工厂，当前正加速向印度、越南分散产能以分散关税与供应链风险。"
                }
            ],
            "customer_bargaining": {
                "top_customers_share": "客户为全球分散普通中产与高净值个人，零售定价权极高，通胀期提价能力稳健。",
                "in_house_threat": "无下游自研替代威胁，核心竞争来自安卓高端旗舰与折叠屏的局部分流。",
                "pricing_power": "极高消费品级品牌溢价与提价权。"
            },
            "geopolitical_and_resilience": "积极推进供应链多元化（印度产 iPhone 比例提升至 15%~20%），有效平抑单一制造基地的地缘冲击。"
        }
    },
    "TSLA.US": {
        "essence": {
            "summary": "智能电动车与物理世界具身智能先锋：以极致垂直整合与规模化制造降本为汽车底座，以 FSD 全自动驾驶算法、储能与人形机器人为长线颠覆性期权。",
            "profit_engine": "【底层盈利真相】特斯拉当前盈利基本盘依赖纯电动车 (EV) 的规模化制造成本优势（一体化压铸技术与精简供应链带来同业最高毛利空间之一）；但其长期估值模型与终局盈利引擎是‘自动驾驶 AI 软件订阅 (FSD) 与出行服务网络 (Robotaxi)’——由一次性造车卖铁，演化为近乎零边际成本的软件高毛利分成。",
            "flywheel": "领先的电驱三电与一体化压铸大幅降低单车成本 ➔ 降价抢占全球新能源市场保有量 ➔ 数百万在途车辆提供海量真实道路长尾数据 ➔ 自研超算训练并进化端到端 FSD 大模型 ➔ 引爆自动驾驶高毛利订阅与无人网约车出行 ➔ 巩固行业技术代差。",
            "segments": [
                {"name": "汽车制造与销售业务 (Automotive)", "ratio": "~80%~82% 营收", "role": "规模与现金流底座：Model 3/Y 全球爆款，毛利率受竞争影响在 16%~19% 波动。"},
                {"name": "电网级与分布式储能 (Energy Storage: Megapack)", "ratio": "~10%~12% 营收", "role": "高毛利爆发第二曲线：毛利率超 25%，受益于全球电网改造与 AI 数据中心电力短缺，增速远超汽车。"},
                {"name": "服务与 FSD 软件等 (Services & Other)", "ratio": "~8%~10% 营收", "role": "生态长期期权：超充补能网络、售后维修与 FSD 订阅收费。"}
            ]
        },
        "industry": {
            "sector": "智能纯电动车、分布式电网级储能与具身智能 (EV, Energy & Robotics)",
            "macro_backdrop": "【宏观经济与周期研判】受高利率环境下大额汽车分期贷款压力以及欧美电动化补贴政策扰动，传统汽车换购需求阶段性承压。但储能业务在全球能源转型与数据中心供电危机下呈现非线性高确定性爆发。",
            "tam": "全球智能汽车交通与移动出行市场超 3 万亿美元，工商业大储年化增速超 35%。",
            "lifecycle": {
                "current_stage": "转型再成长期 (Reinvention / Renewal)",
                "stage_index": 3,
                "all_stages": [
                    {"name": "初创探索期", "desc": "Roadster 验证纯电超跑可行性"},
                    {"name": "高速成长期", "desc": "Model 3/Y 规模量产并席卷全球"},
                    {"name": "成熟竞争期", "desc": "电动车主业面临全球激烈价格竞争"},
                    {"name": "转型再成长期", "desc": "从造车向 FSD / Robotaxi / 储能多元跃迁"},
                    {"name": "衰退防御期", "desc": "纯制造代工化与利润率全面降维"}
                ],
                "characteristics": "纯造车主业步入成熟竞争红海，公司正在全力跨越至第二曲线（FSD 无人驾驶牌照化运营、Megapack 规模爆发与 Optimus 机器人量产）。",
                "is_good_or_bad": {
                    "pros": "好在储能业务爆发力极强提供高毛利缓冲，现金储备超过 300 亿美元抗风险能力充沛，FSD 端到端纯视觉算力与真实数据飞轮全球无人能敌。",
                    "cons": "坏在短期汽车毛利率受行业价格战挤压，Robotaxi 商业化落地仍面临监管牌照与责任认定的时间不确定性，估值高度依赖未来期权兑现。"
                },
                "long_term_strategy": "适合高风险偏好的科技成长投资者关注，核心观察指标是 FSD 商业化拐点及储能业务对利润的平滑贡献。"
            },
            "competitors": [
                {
                    "symbol": "1211.HK",
                    "name": "BYD (比亚迪)",
                    "threat": "极高",
                    "market_position": "全球新能源汽车销量冠军，垂直产业链王者",
                    "comparison": "拥有电池、芯片、电机全产业链极致成本控制力，在 15-25 万元大众市场对特斯拉形成激烈挤压。",
                    "bj_differentiation": "【特斯拉微观差异化突围】全球化高端品牌溢价更强，欧美高购买力市场准入优势显著，且在端到端自动驾驶神经网络及车机软件生态上技术代差明显。"
                },
                {
                    "symbol": "GOOGL.US",
                    "name": "Waymo (Google 无人出行)",
                    "threat": "高",
                    "market_position": "Robotaxi 商业化落地先锋",
                    "comparison": "在旧金山、凤凰城等城市已开展商业收费运营，安全记录良好。",
                    "bj_differentiation": "【特斯拉微观差异化突围】Waymo 依赖昂贵的激光雷达与高精地图硬件单车成本极高且难跨区域快速复制；特斯拉纯视觉方案单车边际成本极低，拥有全球数百万量产车规模泛化能力。"
                }
            ]
        },
        "products": [
            {
                "name": "Model 3 / Model Y / Cybertruck 纯电汽车",
                "category": "硬件终端 / 新能源乘用车整车",
                "strategic_role": "规模与现金流底座 (Volume Foundation)",
                "revenue_ratio": "~80% 营收贡献",
                "gross_margin": "16%~19% 处于降价竞争磨底期",
                "s_curve_stage": "成熟存量平台期与次世代低成本平台切换期",
                "switching_cost": "中 (品牌好感度与超充体验锁定)",
                "barrier_type": "一体化大型压铸技术 + 极致垂直整合制造降本",
                "barrier_detail": "Gigacasting 一体化压铸大幅削减车身零部件与焊接工序，配合自研域控制器与精简线束，单车制造成本处于欧美同级最优水平；自有超充网络遍布全球打消里程焦虑。",
                "market_share": "全球纯电动车销量前两名，欧美主流市场占有率第一",
                "business_model": "新车直销 + 汽车租赁分期 + 超充补能服务费",
                "prospect_and_catalysts": "2.5 万美元下一代低成本小车平台 (Next-Gen) 的投产与爬坡，为激活大众下沉市场的关键催化剂。"
            },
            {
                "name": "FSD (Full Self-Driving) 端到端神经网络与无人出行 (Robotaxi)",
                "category": "算法模型与出行服务 (AI & Mobility)",
                "strategic_role": "颠覆性高估值期权 (Valuation Option)",
                "revenue_ratio": "~5% 营收但具备远期 80%+ 纯利潜力",
                "gross_margin": ">85% (高毛利软件与平台抽成)",
                "s_curve_stage": "端到端技术拐点突破与商业化前夜",
                "switching_cost": "极高 (出行生态与行车安全信任壁垒)",
                "barrier_type": "数百万量产车在途路测长尾数据闭环 + 纯视觉无图路线",
                "barrier_detail": "不同于依赖昂贵激光雷达与高精地图的竞品，特斯拉端到端纯视觉方案单车硬件边际成本极低；每天吞吐全球海量真实道路突发场景数据，在超级计算机群训练进化，实现技术代差。",
                "market_share": "全球高级辅助驾驶累计真实行驶里程与车队规模第一",
                "business_model": "一次性买断 ($8,000) 或按月订阅 ($99/月)，终局为 Cybercab 无人出行网络里程抽成。",
                "prospect_and_catalysts": "FSD v12+ 在欧洲/中国等核心区域监管牌照获批，以及 Cybercab 商业化示范运营。"
            },
            {
                "name": "Megapack (公用事业级大储) & Powerwall 储能系统",
                "category": "分布式储能与电网装备 (Energy Storage)",
                "strategic_role": "高毛利爆发第二曲线 (Growth Vector)",
                "revenue_ratio": "~12% 营收且复合增速 >60%",
                "gross_margin": "25%~28% 强劲拉升",
                "s_curve_stage": "产能爬坡与全球电网刚需爆发期",
                "switching_cost": "高 (电网系统集成与能源调度软件捆绑)",
                "barrier_type": "自研能源控制软件 Autobidder + 规模化储能超级工厂",
                "barrier_detail": "加州与上海储能超级工厂产能供不应求；Autobidder 自动化高频交易算法实现电网电力高抛低吸套利，软硬深度结合形成高壁垒。",
                "market_share": "全球电网级大型储能市场龙头地位",
                "business_model": "B2B 储能硬件系统交付 + 终身能源调度与运维软件订阅",
                "prospect_and_catalysts": "AI 数据中心爆发引发全球电网缺电危机，大储成为最确定、交付周期最长的业绩平滑器。"
            }
        ],
        "supply_chain": {
            "upstream_dependency": "依赖宁德时代、LG新能源供应磷酸铁锂 (LFP) 与三元电芯，部分自研 4680 电池爬坡；芯片依赖台积电代工 FSD 芯片及英伟达提供训练超算卡。",
            "downstream_concentration": "面向全球普通购车消费者及工商业公用事业电网客户，客户结构分散，无单一大客户违约风险。",
            "spof_bottlenecks": [
                {
                    "node": "动力与储能锂电芯供应链配套",
                    "threat_level": "中高",
                    "impact": "储能爆发高度依赖中国供应链电芯稳定出货，关税与原材料碳酸锂价格波动直接影响交付毛利率。"
                },
                {
                    "node": "自研 4680 电池干电极良率爬坡",
                    "threat_level": "中",
                    "impact": "干法电极工艺良率若持续滞后，将制约 Cybertruck 及次世代小车的降本速度。"
                }
            ],
            "customer_bargaining": {
                "top_customers_share": "面向全球 C 端大众消费者与分散电网客户，无单一客户依赖风险。",
                "in_house_threat": "无下游自研替代威胁，主要面临比亚迪等国内友商全产业链垂直整合的价格战竞争。",
                "pricing_power": "储能业务定价权极强，汽车业务受行业竞争加剧毛利弹性阶段性承压。"
            },
            "geopolitical_and_resilience": "上海、柏林、奥斯汀、弗里蒙特四大超级工厂布局全球三大洲，具备极高抗关税壁垒与本土化交付弹性。"
        }
    },
    "MSFT.US": {
        "essence": {
            "summary": "全球企业级数字化底座与生成式 AI 商业化领军者：以 Windows/Office 垄断桌面办公入口，以 Azure 云计算与企业数据中心作为基础设施，全面将 Copilot 深度嵌入企业业务流变现。",
            "profit_engine": "【底层盈利真相】微软拥有全球科技界最强的高毛利订阅护城河。Office 365 与 Windows 在财富 500 强企业中几乎达到 100% 渗透，拥有极高的客户转移成本（员工重新培训与 IT 架构迁移阻力）；通过向企业客户打包绑定销售 Azure 云与安全服务，实现强大的交叉销售效应 (Cross-Selling)，毛利率稳定在 69%~71%，自由现金流造血能力极度充沛。",
            "flywheel": "企业级办公软件与 Active Directory 强绑定 ➔ 企业首选 Azure 作为数据与应用云上托管 ➔ 深度整合 OpenAI 大模型并推出 Copilot 赋能 ➔ 提升企业客户每用户平均收入 (ARPU) ➔ 获得天量现金流投入全球数据中心与算力 ➔ 持续强化生态主导权。",
            "segments": [
                {"name": "智能云平台 (Intelligent Cloud / Azure)", "ratio": "~42%~45% 营收", "role": "绝对增长引擎：Azure 云平台与企业级 AI 模型调用，高增速高毛利。"},
                {"name": "生产力与业务流程 (Productivity / Office 365)", "ratio": "~32%~34% 营收", "role": "超强现金牛：M365 商业版、Teams、LinkedIn，抗周期经常性订阅。"},
                {"name": "更多个人计算 (Personal Computing / Windows & Gaming)", "ratio": "~22%~25% 营收", "role": "桌面基座与泛娱乐：Windows OEM 授权及动视暴雪游戏业务。"}
            ]
        },
        "industry": {
            "sector": "企业级云计算基础设施、企业软件 SaaS 与商用 AI (Cloud & Enterprise Software)",
            "macro_backdrop": "【宏观经济与周期研判】全球企业在降本增效的宏观压力下，优化零散软件采购，倾向于向微软等单一大型供应商整合采购，微软企业采购协议 (EA) 展现极强的抗衰退韧性。",
            "tam": "全球企业 IT 支出与云计算市场预计未来 5 年突破 1.5 万亿美元。",
            "lifecycle": {
                "current_stage": "成熟现金牛期 (Mature Cash Cow)",
                "stage_index": 2,
                "all_stages": [
                    {"name": "初创探索期", "desc": "MS-DOS 与早期 Windows 个人电脑普及"},
                    {"name": "高速成长期", "desc": "Windows + Office 统治全球办公桌面"},
                    {"name": "成熟现金牛期", "desc": "云转型成功，Azure 与 M365 经常性现金流充沛"},
                    {"name": "转型再成长期", "desc": "Copilot 与生成式 AI 全面改造生产力"},
                    {"name": "衰退防御期", "desc": "平台老化与新交互范式降维颠覆"}
                ],
                "characteristics": "商业模式稳如磐石，全球企业数字化刚需，拥有 AAA 顶级信用评级，高现金流与持续分红回购并进。",
                "is_good_or_bad": {
                    "pros": "好在客户黏性高如基础设施，提价能力极强，在企业级商业化落地大模型方面跑得最快最扎实。",
                    "cons": "坏在 AI 资本开支大幅推升短期折旧与数据中心成本，且 Copilot 企业端实际付费转化率需接受 ROI 检验。"
                },
                "long_term_strategy": "全球大资金核心压舱石标的，任何估值跟随宏观大盘的回调均为优质长期建仓窗口。"
            },
            "competitors": [
                {
                    "symbol": "AMZN.US",
                    "name": "Amazon AWS",
                    "threat": "高",
                    "market_position": "全球公有云 IaaS 市场份额第一霸主",
                    "comparison": "在基础云基础设施体量上仍居首位，拥有极深的技术生态与开发者基数。",
                    "bj_differentiation": "【微软微观差异化突围】微软在企业桌面端和 Office 办公套件上具备天然垄断入口，Azure 与企业内部 AD 账户体系天然无缝融合，在大模型商业化生态上借力 OpenAI 领先半个身位。"
                },
                {
                    "symbol": "GOOGL.US",
                    "name": "Alphabet (Google Cloud)",
                    "threat": "中",
                    "market_position": "前沿技术实力雄厚，数据与 AI 见长",
                    "comparison": "拥有极强的自研 TPU 与 Gemini 大模型矩阵，在初创企业与数据分析领域发力迅猛。",
                    "bj_differentiation": "【微软微观差异化突围】微软在大型政企、跨国 500 强的销售网络与信任度远深于 Google，企业合规与企业级落地更具口碑。"
                }
            ]
        },
        "products": [
            {
                "name": "Azure 智能云基础设施与商用 AI",
                "category": "云基础设施与 IaaS/PaaS",
                "strategic_role": "核心增长引擎 (Growth Engine)",
                "revenue_ratio": "~42%~45% 营收贡献",
                "gross_margin": "68%~72% 高毛利率",
                "s_curve_stage": "企业上云与大模型 API 规模化放量期",
                "switching_cost": "极高 (企业 IT 架构与数据迁移风险极高)",
                "barrier_type": "全球数据中心网络 + 深度绑定企业 Active Directory 体系",
                "barrier_detail": "与企业内部 Windows 域账户天然无缝融合，独家托管 OpenAI 前沿模型 API，企业采购协议 (EA) 交叉销售捆绑让政企客户无法割裂。",
                "market_share": "全球公有云市场份额约 24%~26% (稳居第二且持续追赶 AWS)",
                "business_model": "云算力、存储与 AI 模型 token 消耗按需计费 + 长期预留实例合约",
                "prospect_and_catalysts": "AI 贡献的云收入增量季度同比超 30%，财富 500 强上云与 Copilot 基础设施刚需拉动。"
            },
            {
                "name": "Microsoft 365 商业套件 & Copilot (Office 生态)",
                "category": "桌面生产力软件与企业 SaaS",
                "strategic_role": "超强高毛利现金牛 (Cash Cow)",
                "revenue_ratio": "~32%~34% 营收贡献",
                "gross_margin": ">85% (经典企业级软件纯利)",
                "s_curve_stage": "成熟统治级与 Copilot 提价渗透期",
                "switching_cost": "极高 (全球数亿白领 30 年办公肌肉记忆)",
                "barrier_type": "事实垄断级工作流习惯 + 格式标准协议壁垒",
                "barrier_detail": "Word、Excel、PowerPoint、Teams 统治全球办公桌面，任何竞品替代都面临全员重新培训的灾难性生产力损失。",
                "market_share": "全球企业办公生产力软件市占率超 80%",
                "business_model": "按企业员工人头按月/年订阅 (SaaS)，M365 Copilot 额外加收 $30/用户/月直接抬升 ARPU。",
                "prospect_and_catalysts": "Copilot 付费渗透率每提升 5%，直接带来数十亿美元高毛利纯增量利润。"
            }
        ],
        "supply_chain": {
            "upstream_dependency": "AI 服务器硬件高度依赖英伟达 GPU、AMD CPU，数据中心整机代工依赖台湾纬颖、广达，电力网络依赖各州电力公用事业公司。",
            "downstream_concentration": "覆盖全球财富 500 强中 95% 以上跨国企业与政府机构，客户高度分散且粘性极强，无坏账违约风险。",
            "spof_bottlenecks": [
                {
                    "node": "AI 算力芯片供应链与数据中心绿电供应",
                    "threat_level": "中高",
                    "impact": "高资本开支 (CapEx) 扩张下，英伟达 GPU 交付排期与北美数据中心电网并网审批是扩容上限瓶颈。"
                },
                {
                    "node": "与 OpenAI 的独家技术绑定依赖",
                    "threat_level": "中",
                    "impact": "双方合作存在博弈，微软正自研小模型 (Phi-3) 并引入多模型 (Mistral) 降低单点依赖。"
                }
            ],
            "customer_bargaining": {
                "top_customers_share": "跨行业、跨国界分散政企客户，单一客户占比不足 1%，大企业采购协议 (EA) 议价权极强。",
                "in_house_threat": "无下游自研替代威胁，主要面临 Google Workspace 和 AWS 的局部价格战竞标。",
                "pricing_power": "极高垄断性提价权，通胀期企业软件订阅费稳步上调。"
            },
            "geopolitical_and_resilience": "数据中心遍布全球 60+ 区域，主权云方案成熟，完美符合欧美各地严苛的数据隐私法案。"
        }
    },
    "AMD.US": {
        "essence": {
            "summary": "高性能计算与数据中心芯片二当家：以无晶圆厂灵活设计与台积电先进封装为依托，以 EPYC 服务器 CPU 持续蚕食英特尔利润池，以 Instinct GPU 充当云厂商对冲英伟达的高性价比第二选择。",
            "profit_engine": "【底层盈利真相】AMD 的底层盈利真相是‘无晶圆厂 (Fabless) 的高毛利架构价差’。数据中心 EPYC 处理器凭借 chiplet 小芯片模块化架构对英特尔形成持续的能效比压制，构成高毛利稳定基本盘；Instinct MI 系列 AI 加速卡则精准迎合各大云厂商‘对冲英伟达垄断与降低采购成本’的迫切心理，充当高弹性增量；PC 与主机半定制业务则提供基础现金流支撑。",
            "flywheel": "EPYC 高能效比抢占云厂商服务器机柜插槽 ➔ 同一客户顺理成章导入 MI 系列 AI 加速卡 ➔ 数据中心占比提升拉动整体毛利率与现金流 ➔ 巨额资金反哺 Zen/CDNA 架构与 ROCm 软件生态开发 ➔ 下一轮插槽争夺中继续扩大市场份额。",
            "segments": [
                {"name": "数据中心业务 (Data Center: EPYC / Instinct GPU)", "ratio": "~50%~55% 营收且持续提升", "role": "利润与估值核心引擎：毛利率超 65%，AI 加速卡放量拉动整体利润弹性。"},
                {"name": "客户端计算 (Client: Ryzen CPU)", "ratio": "~20%~25% 营收", "role": "消费与商用 PC 基本盘：AI PC 换代驱动，份额稳健。"},
                {"name": "嵌入式与工控 (Embedded: Xilinx FPGA)", "ratio": "~12%~15% 营收", "role": "高毛利缓冲器：赛灵思车规与工控芯片，提供高粘性经常性收入。"},
                {"name": "游戏与半定制 (Gaming: Radeon & PS5/Xbox 芯片)", "ratio": "~10% 营收", "role": "周期现金流补给：主机生命周期尾声，平抑日常开销。"}
            ]
        },
        "industry": {
            "sector": "高性能计算半导体芯片与 AI 加速器 (HPC, CPU & GPU Accelerators)",
            "macro_backdrop": "【宏观经济与周期研判】在生成式 AI 与通用算力共振背景下，云厂商算力采购需求极度旺盛。各大科技巨头为防止被单一供应商绑架，存在极强的‘多供应商采购策略’，AMD 成为全球最核心的承接者。",
            "tam": "全球数据中心 CPU 与 GPU 加速芯片总市场规模超 3,000 亿美元。",
            "lifecycle": {
                "current_stage": "高速成长期 (Rapid Growth)",
                "stage_index": 1,
                "all_stages": [
                    {"name": "初创探索期", "desc": "作为 x86 第二供应商艰难起步"},
                    {"name": "高速成长期", "desc": "Zen 架构崛起与数据中心份额爆发"},
                    {"name": "成熟现金牛期", "desc": "与英伟达、英特尔形成稳定寡头垄断"},
                    {"name": "转型再成长期", "desc": "全栈系统级异构计算与软件闭环"},
                    {"name": "衰退防御期", "desc": "架构落后与市场份额流失"}
                ],
                "characteristics": "受益于数据中心 EPYC 蚕食英特尔以及 MI300 系列 AI 芯片加速出货，数据中心收入占比创历史新高，利润结构发生质的跃升。",
                "is_good_or_bad": {
                    "pros": "好在公司卡位全球算力关键二供，各大云巨头主动扶持，产品兼具 CPU/GPU/FPGA 完整拼图，成长弹性巨大。",
                    "cons": "坏在软件生态 ROCm 与英伟达 CUDA 相比仍有明显代差，在顶级大模型训练领域难以撼动英伟达龙头地位，多受制于推理与二线集群。"
                },
                "long_term_strategy": "适合进取型成长投资者在半导体上行周期中持有，关注其季度 AI 芯片出货指引及毛利率爬坡进度。"
            },
            "competitors": [
                {
                    "symbol": "NVDA.US",
                    "name": "NVIDIA (英伟达)",
                    "threat": "极高",
                    "market_position": "全球 AI 算力无可动摇的行业龙头",
                    "comparison": "拥有统治级的软硬件全栈系统壁垒与极高客户锁定度。",
                    "bj_differentiation": "【AMD 微观差异化突围】主打更高显存容量 (HBM3E) 与更优性价比，并以开源 ROCm 拥抱 PyTorch 社区，成为云厂商不愿受制于英伟达时的唯一成熟备选项。"
                },
                {
                    "symbol": "INTC.US",
                    "name": "Intel (英特尔)",
                    "threat": "中",
                    "market_position": "传统 x86 服务器与 PC 存量巨头",
                    "comparison": "深陷代工亏损与制程延期泥潭，服务器市场份额持续被 AMD 蚕食。",
                    "bj_differentiation": "【AMD 微观差异化突围】绑定台积电顶尖制程与 Chiplet 创新架构，服务器 CPU 能效比与核心数长期压制英特尔至强处理器。"
                }
            ]
        },
        "products": [
            {
                "name": "Instinct MI300X / MI325X / MI350 AI 加速卡",
                "category": "硬件终端 / AI 算力加速卡",
                "strategic_role": "高弹性增长引擎 (Growth Driver)",
                "revenue_ratio": "~25%~30% 营收且持续飙升",
                "gross_margin": ">65% 数据中心高毛利",
                "s_curve_stage": "二供放量与客户验证突破期",
                "switching_cost": "中高 (PyTorch 原生支持降低门槛)",
                "barrier_type": "超大显存容量 + 台积电 3D 键合先进封装",
                "barrier_detail": "配备高达 192GB~256GB HBM3E 超大显存，单卡可承载更大参数量的大模型推理，总拥有成本 (TCO) 极具吸引力；云厂商采购其作为对冲英伟达绑架的唯一成熟替代方案。",
                "market_share": "AI 加速卡第二大商用供货商",
                "business_model": "高 ASP 芯片销售，微软、Meta、甲骨文大规模集中采购。",
                "prospect_and_catalysts": "MI325X/MI350 迭代出货与 ROCm 软件生态成熟度提升为关键股价催化剂。"
            },
            {
                "name": "EPYC (霄龙) 服务器 CPU 系列 (Turin / Genoa)",
                "category": "服务器与云计算核心芯片",
                "strategic_role": "超强现金牛基本盘 (Cash Anchor)",
                "revenue_ratio": "~30%~35% 营收贡献",
                "gross_margin": "62%~66% 稳健高毛利",
                "s_curve_stage": "份额扩张与成熟收割期",
                "switching_cost": "高 (数据中心机架插槽兼容壁垒)",
                "barrier_type": "Zen 核心高能效比 + Chiplet 模块化制造降本",
                "barrier_detail": "Zen 架构高能效比与先进制程红利长期压制英特尔至强处理器；云厂商每采购一台 EPYC 服务器即可显著降低电力与散热开支。",
                "market_share": "x86 服务器市场份额突破 30% 创历史新高",
                "business_model": "直接销售给各大云厂商与品牌服务器 OEM",
                "prospect_and_catalysts": "新一代 Turin 架构继续蚕食英特尔服务器份额，私有云与通用计算升级稳定变现。"
            },
            {
                "name": "Ryzen (锐龙) PC 处理器 & 赛灵思 FPGA 嵌入式",
                "category": "个人终端与工业嵌入式 (Client & Embedded)",
                "strategic_role": "现金流缓冲与高毛利屏障 (Cash & Margin Buffer)",
                "revenue_ratio": "~35%~40% 营收",
                "gross_margin": "48%~52% (消费端) / 65%+ (赛灵思)",
                "s_curve_stage": "AI PC 换代初期 + 工控周期筑底",
                "switching_cost": "中 (PC 消费端) / 极高 (车规与工控 Xilinx)",
                "barrier_type": "NPU 算力集成 + 赛灵思深厚专利壁垒",
                "barrier_detail": "锐龙 AI PC 处理器率先集成 NPU，卡位 Windows Copilot+ PC 生态；赛灵思在航天军工与通信领域具备高转换阻力。",
                "market_share": "全球高端 PC 处理器关键双寡头之一",
                "business_model": "芯片直接直销与授权",
                "prospect_and_catalysts": "PC 市场 AI 换机周期到来及工控去库存结束周期反转。"
            }
        ],
        "supply_chain": {
            "upstream_dependency": "高度依赖台积电 (TSMC) 先进制程及 CoWoS 封装代工，以及三星/美光的高带宽内存供应。",
            "downstream_concentration": "微软、Meta、亚马逊、Alphabet 等头部云厂商采购占比较高，客户集中度偏高。",
            "spof_bottlenecks": [
                {
                    "node": "台积电先进制程与封装产能配额博弈",
                    "threat_level": "高",
                    "impact": "AMD 与英伟达、苹果同时争夺台积电 3nm/4nm 及 CoWoS 产能，配额争取直接决定出货上限。"
                },
                {
                    "node": "HBM3E 供应优先级",
                    "threat_level": "中高",
                    "impact": "英伟达锁定大量海力士与美光 HBM 产能，AMD 需防范内存短缺风险。"
                }
            ],
            "customer_bargaining": {
                "top_customers_share": "超大规模云厂商贡献数据中心大头，大客户具备一定采购议价筹码。",
                "in_house_threat": "中高：云厂商自研芯片不仅替代英伟达，同样替代 AMD 增量份额。",
                "pricing_power": "依靠性价比与大显存突围，毛利率难以达到英伟达 75%+ 的极高溢价水平。"
            },
            "geopolitical_and_resilience": "无自建晶圆厂，依托台积电全球多地建厂分散制造风险，研发中心分布全球。"
        }
    },
    "BJ.US": {
        "essence": {
            "summary": "美东中产家庭的高频性价比粮仓：以微利或平价的优质大包装生鲜杂货为客流锚点，以高续费率的会员费作为真正的利润与现金流收割机。",
            "profit_engine": "【底层盈利真相】会员制零售的商业底牌不是赚取商品进销差价（商品零售毛利率仅约 14%~15%，基本刚好覆盖仓储折旧与门店人工）。其经营净利润的 75%~85% 实际上直接由高毛利的会员费收入 (Membership Fee Income) 贡献。只要会员池稳固、续费率高，每一次到店购物都在为会员费的确定性背书。",
            "flywheel": "精选 SKU + 适度大包装低加价率 ➔ 降低美东中产家庭一站式购物开支 ➔ 锁定 90%+ 超高会员续费率与充沛年费现金流 ➔ 庞大集采规模进一步压低进货成本与提高库存周转 ➔ 飞轮正向自我强化。",
            "segments": [
                {"name": "食品生鲜与日用杂货 (Grocery & Perishables)", "ratio": "~70% 营收", "role": "到店刚需抓手：锁定每周家庭消费频次，薄利多销打造性价比心智。"},
                {"name": "自有品牌 (Private Label: Wellsley Farms / Berkley Jensen)", "ratio": "~25% 杂货渗透率", "role": "利润率提升杠杆：毛利率较第三方品牌高 300~500 个基点，增强客户忠诚度。"},
                {"name": "会员专享加油站 (Gas Stations)", "ratio": "~15%~20% 营收", "role": "客流核武器：每加仑较周边低 10~25 美分，在高油价/通胀时期强力虹吸车流并促进进店消费。"},
                {"name": "核心会员费收入 (Membership Fees)", "ratio": "~2% 营收但贡献大头净利润", "role": "纯自由现金流引擎：预收年费沉淀无息运营资金，边际成本接近零。"}
            ]
        },
        "industry": {
            "sector": "会员制仓储零售与平价折扣超市 (Warehouse Clubs & Discount Retail)",
            "macro_backdrop": "【宏观经济大势与周期定位】当前美联储高利率与美国居民实际可支配收入承压背景下，中产阶层出现显著的‘消费降级与极致性价比偏好 (Trade-Down Effect)’。仓储会员店凭借比传统超市平均低 20%~25% 的商品价格，成为抗通胀与抗衰退的核心避风港。此外，高通胀推升的汽油与食品开支，反向强化了消费者办理会员卡的刚性动力。",
            "tam": "全美会员制仓储俱乐部市场规模超 3,200 亿美元，预计未来 5 年复合增长率 (CAGR) 为 5.5%~6.8%，持续跑赢传统大卖场与普通杂货超市。",
            "lifecycle": {
                "current_stage": "成熟现金牛期 (Mature Cash Cow)",
                "stage_index": 2,
                "all_stages": [
                    {"name": "初创探索期", "desc": "商业模式摸索与单店模型验证"},
                    {"name": "高速成长期", "desc": "跨区快速展店与规模狂飙"},
                    {"name": "成熟现金牛期", "desc": "现金流充沛、抗周期、增速平稳"},
                    {"name": "转型再成长期", "desc": "开辟全渠道或跨国第二曲线"},
                    {"name": "衰退防御期", "desc": "模式老化与市场份额萎缩"}
                ],
                "characteristics": "商业模式历经 40 年周期检验，美东根据地稳固，同店销售与会员数稳健爬坡，兼具高自由现金流与适度区域拓店能力。",
                "is_good_or_bad": {
                    "pros": "好在自由现金流极度健康，抗衰退韧性极强，90%+ 会员续费率构筑宽阔护城河，资本开支可控，回购与财务稳健度极佳。",
                    "cons": "坏在单店坪效与体量相比行业龙头 Costco 存在代差，向中西部和南部扩张面临 Sam's Club 与 Costco 严酷竞争，估值倍数存在天然上限。"
                },
                "long_term_strategy": "适合防御型中长线资金在估值处于历史中枢下方时买入作为‘稳定复利底仓’，不宜给予高成长科技股的高估值溢价。"
            },
            "competitors": [
                {
                    "symbol": "COST.US",
                    "name": "Costco (开市客)",
                    "threat": "极高",
                    "market_position": "全球仓储会员店绝对霸主，年营收超 2500 亿美元",
                    "comparison": "Costco 极致精选 SKU (约 4,000 个)，全球规模效应和 Kirkland 自营品牌号召力无敌，单店销售额远超 BJ。",
                    "bj_differentiation": "【BJ 微观差异化突围】BJ 提供约 7,000 个 SKU (比 Costco 多一倍)，涵盖更多知名消费品牌；商品包装为‘中等家庭装’而非超大巨型装，更贴合中小家庭；全美唯一支持厂商优惠券 (Manufacturer Coupons)，叠加折扣感知更强。"
                },
                {
                    "symbol": "WMT.US",
                    "name": "Sam's Club (山姆会员店 / 沃尔玛)",
                    "threat": "高",
                    "market_position": "全美第二大仓储俱乐部，背靠沃尔玛全球供应链",
                    "comparison": "拥有沃尔玛最强集采议价权，数字化‘即扫即走 (Scan & Go)’全渠道配送领跑，并在中西部/南部根基深厚，正在向美东渗透。",
                    "bj_differentiation": "【BJ 微观差异化突围】BJ 在美东（新英格兰、纽约大都会区）拥有长达 40 年先发优势，85% 以上门店扎根美东，网点密度和社区距离远胜 Sam's Club，地缘黏性极深。"
                },
                {
                    "symbol": "TGT.US",
                    "name": "Target (塔吉特) / 传统平价大卖场",
                    "threat": "中",
                    "market_position": "全美大众平价百货巨头",
                    "comparison": "非会员制无需购卡，商品主打中产生活方式与时尚杂货，分流部分日常零散购买需求。",
                    "bj_differentiation": "【BJ 微观差异化突围】BJ 在生鲜与日用必需品上具备大包装 20%+ 的绝对价格优势，高通胀环境下对 Target 形成强烈的性价比替代分流。"
                }
            ]
        },
        "products": [
            {
                "name": "核心会员俱乐部与年费体系 (Membership Program)",
                "category": "会员权益与数字服务",
                "strategic_role": "终极利润与自由现金流收割机 (Profit & Cash Harvesting Machine)",
                "revenue_ratio": "~2% 营收贡献 (但贡献 75%~85% 经营利润)",
                "gross_margin": "~100% (边际成本接近零的纯预收现金流)",
                "s_curve_stage": "成熟收割与精细运营期",
                "switching_cost": "高 (年费已沉淀且美东社区就近心智垄断)",
                "barrier_type": "美东 40 年密集网点渗透 + 90%+ 超高续费率护城河",
                "barrier_detail": "美东会员年费沉淀了庞大无息营运资金；会员只要每年在店消费数次，所省差价即远超 $55/$110 年费，形成极强的换店阻力与自动续订惯性。",
                "market_share": "美东仓储会员店网络密度第一",
                "business_model": "基础会员卡 ($55/年) 与高返现俱乐部卡 ($110/年) 预收款模式",
                "prospect_and_catalysts": "近期会员年费温和上调窗口、高返现高级会员渗透率提升与全渠道 App 续订率爬坡。"
            },
            {
                "name": "高周转民生生鲜肉禽与包装食品 (Grocery & Perishables)",
                "category": "食品生鲜与日用杂货",
                "strategic_role": "全店高频客流引流锚点 (High-Frequency Traffic Driver)",
                "revenue_ratio": "~70% 营收贡献",
                "gross_margin": "14%~15% (极致平价与极薄毛利让利)",
                "s_curve_stage": "成熟现金牛基本盘",
                "switching_cost": "中 (美东家庭每周固定刚需采购习惯)",
                "barrier_type": "冷链物流仓网 + 产地直采短链供应链",
                "barrier_detail": "相比传统商超损耗率低 30% 以上；精选 7,000 个高频 SKU 快速周转，单品采购规模庞大，牢牢锁住中产家庭每周‘餐桌开支’。",
                "market_share": "美东中产家庭高频生鲜食品采购核心目的地之一",
                "business_model": "低加价率快速周转走量，薄利多销沉淀客流",
                "prospect_and_catalysts": "通胀环境下中产‘向下换购 (Trade-down)’红利持续显现，同店生鲜销售额稳健攀升。"
            },
            {
                "name": "自有品牌矩阵 (Wellsley Farms & Berkley Jensen)",
                "category": "高性价比自营品牌 (Private Label)",
                "strategic_role": "综合毛利率扩张杠杆 (Margin Expansion Lever)",
                "revenue_ratio": "~25% 杂货品类渗透率 (目标 30%+)",
                "gross_margin": "19%~22% (较第三方全国品牌高 300~500 个基点)",
                "s_curve_stage": "份额扩张与溢价成长期",
                "switching_cost": "中高 (专属配方口碑与 20%+ 价格折扣深度绑定)",
                "barrier_type": "严格代工品控标准 + 独家专供心智沉淀",
                "barrier_detail": "Wellsley Farms 锁定优质健康食品，Berkley Jensen 覆盖高品质纸品洗护。品质媲美全国一线大牌而价格便宜 20%~30%，沉淀专属会员品牌忠诚度。",
                "market_share": "自有品牌占总商品销售比例稳步提升至 25% 以上",
                "business_model": "ODM 委托顶尖代工厂制造，省去中间品牌溢价与营销费用",
                "prospect_and_catalysts": "向 30% 渗透率迈进将直接每年增厚数千万美元营业利润，自营单品推陈出新。"
            },
            {
                "name": "会员专享平价加油站网络 (Club Gas Stations)",
                "category": "加油站与汽车生活配套",
                "strategic_role": "客流黑洞与抗通胀核武器 (Traffic Funnel & Gas Hook)",
                "revenue_ratio": "~15%~20% 营收 (受油价波动影响)",
                "gross_margin": "5%~8% (低毛利强引流)",
                "s_curve_stage": "稳健成长期 (新俱乐部标配)",
                "switching_cost": "中 (每加仑便宜 10~25 美分的即时价格诱惑)",
                "barrier_type": "大宗批发直采油品成本优势 + 门店动线无缝闭环",
                "barrier_detail": "利用庞大直采运力压低进油成本，每加仑价格常年低于周边加油站 15 美分以上；加油车主顺道进店购物转化率高达 40% 以上。",
                "market_share": "美东多数核心俱乐部标配加油站",
                "business_model": "会员专属加油通道，薄利引流联动店内消费",
                "prospect_and_catalysts": "新开门店 100% 配套加油站，在油价高位震荡周期内对周边散客具备极强虹吸效应。"
            }
        ],
        "supply_chain": {
            "upstream_dependency": "与宝洁、百事、泰森食品、联合利华等全球消费巨头建立直采合作，无单一供应商垄断卡脖子风险，具备全国基地直采短链运力。",
            "downstream_concentration": "直面美东数百万普通中产家庭会员，客户高度分散，现金流每日现付回笼，坏账风险为零。",
            "spof_bottlenecks": [
                {
                    "node": "美东冷链配送半径极限与跨区外拓物流成本",
                    "threat_level": "中",
                    "impact": "向东南部（佛罗里达等）异地展店需提前重金布局冷链分发中心，门店密度未饱和前可能阶段性摊薄整体营业利润率。"
                },
                {
                    "node": "食品供应链通胀向消费端顺价的时滞摩擦",
                    "threat_level": "中",
                    "impact": "若大宗农产品或包装材料短期急剧涨价，在极薄的 14% 商品毛利下，若顺价滞后可能短暂侵蚀季度毛利润。"
                }
            ],
            "customer_bargaining": {
                "top_customers_share": "会员散户高度分散，无单一客户议价权，会员卡普遍绑定自动扣款续费。",
                "in_house_threat": "极低：消费者无法自建供应链，仅存在 Costco、山姆与传统商超之间的流动转移。",
                "pricing_power": "由于商品价格比传统超市低 20%~25%，即使适度涨价仍保持显著平替优势，客户粘性高。"
            },
            "geopolitical_and_resilience": "100% 聚焦美国本土内需市场，无跨国关税、地缘政治与外汇波动风险，供应链全链条高度本土化。"
        }
    },
    "MU.US": {
        "essence": {
            "summary": "全球唯三的高端半导体存储巨头：深度受益于 AI 服务器高带宽内存 (HBM3E) 与 DDR5 升级浪潮的强周期成长股。",
            "profit_engine": "【底层盈利真相】存储芯片兼具‘周期大宗品’与‘定制技术护城河’双重属性。传统 DRAM/NAND 易受供需周期暴涨暴跌影响，但在 AI 时代，HBM3E 是英伟达 Blackwell 架构的刚性伴侣，具备‘产能预售锁死、高 ASP、高毛利 (>60%)’的特征，彻底重塑了美光的周期底线与盈利质量。",
            "flywheel": "先进制程 (1-beta/1-gamma) 研发领先 ➔ 率先通过英伟达验证锁定全年 HBM 产能 ➔ 享受高溢价现金流 ➔ 支撑下一代高资本开支 ➔ 巩固寡头地位。",
            "segments": [
                {"name": "DRAM / HBM3E 内存芯片", "ratio": "~70% 营收", "role": "核心王牌：HBM3E 供不应求，毛利率强劲扩张。"},
                {"name": "NAND 闪存与企业级 SSD", "ratio": "~30% 营收", "role": "周期复苏：AI 训练数据集需要海量高速企业级 SSD 存储，带动单价回升。"}
            ]
        },
        "industry": {
            "sector": "半导体存储芯片 (DRAM / NAND / HBM)",
            "macro_backdrop": "【宏观经济与半导体周期】全球半导体走出上一轮去库存低谷，叠加生成式 AI 数据中心资本开支爆炸式增长，行业正处于强劲的‘AI 算力拉动的超级存储周期’上升通道。",
            "tam": "全球存储芯片市场超 1,300 亿美元，其中 HBM 细分赛道未来 3 年年化增速超 50%。",
            "lifecycle": {
                "current_stage": "高速成长期 (Rapid Growth)",
                "stage_index": 1,
                "all_stages": [
                    {"name": "初创探索期", "desc": "技术研发与初期建厂"},
                    {"name": "高速成长期", "desc": "HBM 爆发驱动的周期上升主升浪"},
                    {"name": "成熟现金牛期", "desc": "供需平衡、稳健现金流"},
                    {"name": "转型再成长期", "desc": "从大宗存储向定制化 AI 存算一体演进"},
                    {"name": "衰退防御期", "desc": "行业下行周期与主动减产"}
                ],
                "characteristics": "受 AI 服务器 HBM3E 订单挤爆驱动，业绩与自由现金流正处于高斜率爆发期。",
                "is_good_or_bad": {
                    "pros": "好在行业寡头垄断格局极佳（三星、海力士、美光三家独大），HBM 产能被提前预定，议价权与毛利大幅反弹。",
                    "cons": "坏在半导体存储重资产属性极强，资本开支高昂，一旦 AI 算力投资降温或竞品大幅扩产，可能面临下一轮周期下行风险。"
                },
                "long_term_strategy": "在周期上行阶段充分享受业绩与估值戴维斯双击，但在市净率 (PB) 触及历史极高分位时需防范周期见顶。"
            },
            "competitors": [
                {"symbol": "SK Hynix", "name": "SK 海力士", "threat": "极高", "market_position": "HBM 市场先发龙头，深度绑定英伟达", "comparison": "海力士在 HBM3/HBM3E 先发优势明显，美光以 1-beta 低功耗优势快速追赶并分流份额。"},
                {"symbol": "Samsung", "name": "三星电子", "threat": "高", "market_position": "全球第一大存储芯片巨头", "comparison": "三星产能庞大但 HBM3E 早期送样认证稍滞后，目前正全力追赶。"}
            ]
        },
        "products": [
            {
                "name": "HBM3E (高带宽内存) 24GB/36GB 堆叠模块",
                "category": "AI 数据中心顶级算力加速内存",
                "strategic_role": "AI 算力超级爆发引擎 (Generative AI Growth Engine)",
                "revenue_ratio": "~20%~25% 营收 (高斜率暴增中)",
                "gross_margin": "60%~65%+ (极高溢价水平)",
                "s_curve_stage": "爆发渗透与产能爬坡期",
                "switching_cost": "极高 (GPU 严苛电气与热仿真认证锁定)",
                "barrier_type": "1-beta DRAM 能效优势 + 8层/12层 3D TSV 先进封装",
                "barrier_detail": "相比竞品功耗低 30%，在英伟达 Blackwell 架构散热严苛约束下具备核心优势；通过系统级严苛认证后客户难以替换供应商。",
                "market_share": "与海力士瓜分英伟达 B200/GB200 首批供货，产能已被提前 18 个月预订一空",
                "business_model": "长单定制直销英伟达、AMD 等顶级算力巨头，锁定产能与基准售价",
                "prospect_and_catalysts": "12层 36GB HBM3E 大规模出货与下一代 HBM4 研发流片，单机价值量持续提升。"
            },
            {
                "name": "DDR5 / LPDDR5X 服务器与终端高端内存芯片",
                "category": "企业级服务器与移动终端通用存储",
                "strategic_role": "周期复苏核心压舱石 (Core Server/PC Cash Anchor)",
                "revenue_ratio": "~45%~50% 营收贡献",
                "gross_margin": "35%~45% (周期上行通道中稳健扩张)",
                "s_curve_stage": "主流成熟与世代交替期 (DDR4 ➔ DDR5)",
                "switching_cost": "中 (符合 JEDEC 接口标准，但先进制程供不应求)",
                "barrier_type": "1-beta 领先制程良率 + 头部 CPU 厂商联合认证",
                "barrier_detail": "在英特尔 Xeon 与 AMD EPYC 平台完成深度兼容性调优，功耗更低、传输速率更高；全球仅三家厂商具备大规模供货能力。",
                "market_share": "全球 DRAM 市场前三强 (市占率约 23%~25%)",
                "business_model": "季度合约价与现货销售相结合，云厂商定期锁定大单采购",
                "prospect_and_catalysts": "AI PC 与 AI 手机本地运行大模型对 DRAM 容量需求翻倍（16GB➔32GB），推动单机价值量飙升。"
            },
            {
                "name": "企业级与数据中心高速 SSD (232层 3D NAND)",
                "category": "企业级固态硬盘与云端闪存存储",
                "strategic_role": "AI 训练检索存力第二曲线 (AI Enterprise Storage Curve)",
                "revenue_ratio": "~25%~30% 营收",
                "gross_margin": "25%~35% (摆脱周期低谷，毛利率回归正常)",
                "s_curve_stage": "周期筑底复苏与高端渗透期",
                "switching_cost": "中 (PCIe 5.0 高吞吐与定制固件深度集成)",
                "barrier_type": "232层超高堆叠 NAND 制造工艺 + 自研企业级主控",
                "barrier_detail": "海量 AI 训练语料与检索增强 (RAG) 需低延迟大容量存储，美光率先量产 232 层 3D NAND 提供极高存储密度与读写吞吐。",
                "market_share": "全球 NAND 闪存排名前五，企业级 PCIe 5.0 SSD 份额快速爬坡",
                "business_model": "直接供应头部数据中心运营商与 OEM 服务器集成商",
                "prospect_and_catalysts": "AI 数据中心对全闪存阵列 (AFA) 替代机械硬盘需求井喷，带动高密度企业级 SSD 价格持续反弹。"
            }
        ],
        "supply_chain": {
            "upstream_dependency": "极度依赖 ASML EUV/浸润式光刻机、应用材料/泛林半导体等核心机台，以及日本信越化学等高纯度大硅片、光刻胶与特种气体。",
            "downstream_concentration": "直供英伟达、AMD、微软、亚马逊 AWS、谷歌云、戴尔、惠普等全球前十大算力与终端 OEM，客户集中度偏高。",
            "spof_bottlenecks": [
                {
                    "node": "3D TSV 先进封装良率与产能爬坡瓶颈",
                    "threat_level": "极高",
                    "impact": "HBM3E 采用 8/12 层复杂垂直堆叠，若晶圆键合或散热工艺良率波动，将直接导致交货延迟并严重侵蚀高毛利。"
                },
                {
                    "node": "ASML 先进光刻机交付周期与重资产折旧周期",
                    "threat_level": "中高",
                    "impact": "扩产周期长达 18~24 个月，若行业周期突然反转，巨额折旧与机台维护费用将沉重施压营业利润率。"
                }
            ],
            "customer_bargaining": {
                "top_customers_share": "英伟达与超大规模云厂商采购量巨大，但在 HBM 产能紧缺时美光议价权显著增强，全产能已被预售锁定；",
                "in_house_threat": "极低：云厂商和芯片设计公司无法自研制造物理 DRAM/HBM 晶圆，制造门槛与资本壁垒极高；",
                "pricing_power": "HBM3E 享有高额技术垄断溢价，标准 DDR5/NAND 依然受季度供需合约价格周期博弈约束。"
            },
            "geopolitical_and_resilience": "获美国 CHIPS 法案超 60 亿美元直接资助，并在美国（爱达荷/纽约）、日本广岛、中国台湾和新加坡分散建厂，地缘政治韧性强于竞争对手。"
        }
    },
    "COST.US": {
        "essence": {
            "summary": "全球会员制仓储零售的绝对统治者与运营效率标杆：以极致精选 4,000 SKU 与近乎成本价销售构筑平价飞轮，以高粘性会员年费作为核心利润源泉。",
            "profit_engine": "【底层盈利真相】Costco 本质上不是赚取商品进销差价的传统超市，而是一家‘以平价高品质商品为介质收取会员订阅费的资产管理与服务机构’。全店商品综合毛利率被硬性限制在 11%~14% 以下（几乎仅能覆盖仓储、人工与运营折旧），而会员费 (Membership Fees) 收入贡献了公司营业利润的 70%+。凭借极高的会员忠诚度（北美续约率 93%，全球 90.5%）与天量单店坪效，构建了几乎不可被电商与同行复制的实体零售效率天花板。",
            "flywheel": "极致精选 4,000 SKU ➔ 超大单品全球天量集采压低进价 ➔ 以近乎成本价让利会员 ➔ 形成无与伦比的心智与极高续约率 (93%) ➔ 吸引更多会员办理 Executive 高级卡 ➔ 会员费源源不断注入带来确定性利润 ➔ 支撑进一步全球稳步扩店。",
            "segments": [
                {"name": "食品、生鲜与日常快消 (Foods & Fresh)", "ratio": "~55%~58% 营收", "role": "高频引流基石：高品质冷链肉禽、烘焙与包装食品，刚需抗通胀。"},
                {"name": "非食品百货与耐用品 (Non-Foods)", "ratio": "~26%~28% 营收", "role": "客单价拉升器：家电、服饰、珠宝与季节性商品，强化仓储淘宝感。"},
                {"name": "平价加油站、轮胎与视光中心 (Auxiliary)", "ratio": "~12%~14% 营收", "role": "会员粘性锁：全美最低油价与专业眼科配镜，形成一周一次进店习惯。"},
                {"name": "会员年费收入 (Membership Fees)", "ratio": "~2%~3% 营收", "role": "绝对纯利支柱：毛利率近 100%，贡献全公司 70%+ 营业利润。"}
            ]
        },
        "industry": {
            "sector": "全球会员制仓储零售与超级平价连锁 (Global Warehouse Clubs & Retail)",
            "macro_backdrop": "【宏观经济与周期研判】在高通胀与可支配收入承压环境下，中产及工薪家庭更倾向于大包装与高性价比商品，Costco 作为抗通胀平替第一心智极强；即便利率高企，其稳健现金流与防守属性深受长线主权资金青睐。",
            "tam": "全球仓储会员零售与大众批发市场规模超 8,000 亿美元，且在亚洲与欧洲成熟经济体渗透率仍有广阔扩张空间。",
            "lifecycle": {
                "current_stage": "成熟现金牛期 (Mature Cash Cow)",
                "stage_index": 2,
                "all_stages": [
                    {"name": "初创探索期", "desc": "西雅图首店与仓储会员制雏形"},
                    {"name": "高速成长期", "desc": "全美快速圈地与会员规模爆发"},
                    {"name": "成熟现金牛期", "desc": "全球稳步拓店、极高续约率与充沛现金流"},
                    {"name": "转型再成长期", "desc": "数字化电商履约与新兴国际市场扩张"},
                    {"name": "衰退防御期", "desc": "人口老龄化与竞争饱和"}
                ],
                "characteristics": "业务模式历经四十年周期检验，全球会员规模超 1.3 亿人，单店销售额超过沃尔玛两倍，处于极度稳健的现金牛阶段。",
                "is_good_or_bad": {
                    "pros": "好在会员续约率超 93%，具备类 SaaS 的经常性年费造血能力，且自有品牌 Kirkland 构筑了极高品牌忠诚度与毛利缓冲。",
                    "cons": "坏在估值市盈率长期位于 45x~52x 极高历史分位，市场对其赋予了近乎奢侈品的高估值溢价，短期对同店销售额增速放缓极为敏感。"
                },
                "long_term_strategy": "适合主权财富基金作为底仓长线配置，享受每年 25~30 家稳健扩店带来的内含复利，但需防范估值极端高位带来的均值回归风险。"
            },
            "competitors": [
                {
                    "symbol": "BJ.US",
                    "name": "BJ's Wholesale Club",
                    "threat": "中",
                    "market_position": "美东高密度社区会员店区域霸主",
                    "comparison": "SKU 数量约 7,000 个（包装较小更适合普通家庭），深耕美东居民生活半径。",
                    "bj_differentiation": "【Costco 压倒性壁垒】全球集采议价权与 Kirkland 自有品牌声誉具备压倒性优势，单店坪效与会员续约率显著领先。"
                },
                {
                    "symbol": "WMT.US",
                    "name": "Sam's Club (山姆会员店)",
                    "threat": "高",
                    "market_position": "背靠沃尔玛全球供应链的头号挑战者",
                    "comparison": "全美网点众多，数字化扫码购体验领先，且在中国等国际市场扩张迅猛。",
                    "bj_differentiation": "【Costco 压倒性壁垒】高端中产客群心智占有率极高，Executive 高级会员忠诚度与单客年均消费额远超山姆。"
                },
                {
                    "symbol": "AMZN.US",
                    "name": "Amazon Prime (亚马逊线上会员)",
                    "threat": "中高",
                    "market_position": "全球线上电商与数字会员巨无霸",
                    "comparison": "次日达甚至当日达极速履约，线上选品无限长尾。",
                    "bj_differentiation": "【Costco 压倒性壁垒】线下实体大包装批发的单位重量物流成本远低于快递履约，生鲜与即时试吃体验线上无法替代。"
                }
            ]
        },
        "products": [
            {
                "name": "Kirkland Signature (柯克兰) 自有品牌金字塔",
                "category": "自营核心消费品牌 (Private Label)",
                "strategic_role": "利润护城河与毛利杠杆 (Margin Expansion Lever)",
                "revenue_ratio": "~28%~30% 营收贡献 (年销超 580 亿美元)",
                "gross_margin": "16%~18% (显著高于外采知名品牌)",
                "s_curve_stage": "全球顶级消费品心智统治期",
                "switching_cost": "高 (无可替代的极致品质与平价心智)",
                "barrier_type": "无形资产 + 反向定制供应链规模优势",
                "barrier_detail": "品质对标甚至超越一线大牌（如绿标牛肉、坚果、纸巾、婴儿用品），但售价至少便宜 20%；单品牌年销售额超过绝大多数全球消费品巨头。",
                "market_share": "全美自营品牌认知度第一",
                "business_model": "ODM 深度反向定制与大规模直采，将省下的渠道差价全额让渡给会员。",
                "prospect_and_catalysts": "持续渗透更多高附加值品类，成为抵御通胀和提高综合毛利的定海神针。"
            },
            {
                "name": "Executive (高级黑卡) 会员年费体系 ($130/年)",
                "category": "订阅会员服务 (Membership Program)",
                "strategic_role": "绝对纯利造血机 (Core Profit Engine)",
                "revenue_ratio": "~3% 营收贡献但贡献 70%+ 营业利润",
                "gross_margin": ">95% (纯会员年费边际成本极低)",
                "s_curve_stage": "成熟稳健提升期",
                "switching_cost": "极高 (每年 2% 返现覆盖年费有余，极难退订)",
                "barrier_type": "高转换壁垒与财务沉没成本效应",
                "barrier_detail": "全球超 3,400 万 Executive 持卡人，享有每年高达 $1,250 的 2% 消费返现，这部分高价值中产会员贡献了 Costco 全球超 73% 的销售额。",
                "market_share": "全球会员续约率超 90.5%，北美超 93%",
                "business_model": "每年一次性预付年费，产生充沛的零利息营运资本与营运现金流沉淀。",
                "prospect_and_catalysts": "新一轮会员年费提价平稳落地，单会员毛利贡献直接阶梯式提升。"
            }
        ],
        "supply_chain": {
            "upstream_dependency": "与全球数千家一线品牌商及农业基地直接合作，采购体量极大，账期周转极快（甚至先收会员现金后付供应商货款），具备极致议价权。",
            "downstream_concentration": "面向全球 1.3 亿+ 注册会员，无任何单一客户集中度风险，现金流极度分散稳健。",
            "spof_bottlenecks": [
                {
                    "node": "全球物流干线运力与集装箱港口拥堵",
                    "threat_level": "中",
                    "impact": "若国际海运运价飙升或港口停工，可能造成部分季节性非食品 SKU 货期延迟。"
                },
                {
                    "node": "核心农产品与生鲜冷链价格通胀",
                    "threat_level": "低中",
                    "impact": "为维持‘平价心智’，Costco 倾向于推迟涨价（如标志性烤鸡与热狗始终坚持亏本引流），短期轻微压制商品端毛利。"
                }
            ],
            "customer_bargaining": {
                "top_customers_share": "会员群体极度分散，前万名客户占比不足 0.1%；",
                "in_house_threat": "无替代可能，实体大件采购生活方式根深蒂固；",
                "pricing_power": "对供应商拥有极限压价权，但主动对消费者实施微利承诺。"
            },
            "geopolitical_and_resilience": "业务高度集中于美国与加拿大（占比近 85%），并在日本、英国、韩国、中国等高消费力市场稳步开辟增量，地缘风险极低。"
        }
    },
    "AMZN.US": {
        "essence": {
            "summary": "全球电子商务履约巨无霸与云计算基础设施绝对领导者：以电商与 Prime 会员构筑高频流量飞轮，以 AWS 云计算与高毛利站内广告变现充沛自由现金流。",
            "profit_engine": "【底层盈利真相】亚马逊以微利甚至阶段性亏损的全球自营电商和 FBA 智能物流为高频流量入口，真正的高毛利印钞机是 AWS 云计算（营业利润率 35%+）和站内高毛利数字广告（年销超 500 亿美元，毛利率 >75%）。电商业务提供充沛的营运资本负周期现金流，AWS 提供科技护城河与战略利润，两大引擎互哺构成反脆弱体系。",
            "flywheel": "海量选品与极致低价 ➔ 吸引全球超 2 亿 Prime 会员高频消费 ➔ 吸引数百万第三方卖家入驻使用 FBA 履约 ➔ 产生巨额站内高毛利广告收入 ➔ 输送充沛自由现金流投入 AWS 云基础设施与自研 AI 算力 ➔ 持续构筑技术壁垒。",
            "segments": [
                {"name": "北美及国际电商零售 (North America & Intl)", "ratio": "~64%~66% 营收", "role": "高频流量基石：全球最大的线上零售与第三方卖家服务平台。"},
                {"name": "AWS 云计算与生成式 AI 基础设施", "ratio": "~16%~18% 营收", "role": "绝对利润支柱：全球公有云龙头，贡献全公司 60%+ 营业利润。"},
                {"name": "站内高毛利数字广告 (Advertising Services)", "ratio": "~8%~10% 营收", "role": "高弹性现金奶牛：精准基于购物意图的 Sponsored Ads，利润率极高。"},
                {"name": "Prime 会员订阅与流媒体服务", "ratio": "~7%~8% 营收", "role": "用户留存锁：提供次日达物流特权与 Prime Video 视听娱乐生态。"}
            ]
        },
        "industry": {
            "sector": "全球电子商务、数字物流与公有云基础设施 (Global eCommerce & Cloud)",
            "macro_backdrop": "【宏观经济与周期研判】受益于企业云上工作流向生成式 AI 迁移的强劲需求，AWS 迎来第二增长加速曲线；同时电商通过区域化履约网络重组大幅压缩履约成本，利润率持续超预期修复。",
            "tam": "全球企业公有云市场预计 2028 年超 1 万亿美元；全球电商渗透率仍有长尾提升空间。",
            "lifecycle": {
                "current_stage": "成熟现金牛期 (Mature Cash Cow)",
                "stage_index": 2,
                "all_stages": [
                    {"name": "初创探索期", "desc": "线上书店与网络零售起步"},
                    {"name": "高速成长期", "desc": "Prime 会员爆发与 AWS 开创公有云"},
                    {"name": "成熟现金牛期", "desc": "电商履约优化、AWS 高毛利放量与广告印钞"},
                    {"name": "转型再成长期", "desc": "自研 Trainium/Inferentia 芯片与 Bedrock AI 全面重塑"},
                    {"name": "衰退防御期", "desc": "增长天花板与反垄断分拆"}
                ],
                "characteristics": "业务规模超 6,000 亿美元，电商履约效率大幅优化，AWS 与广告两大利润引擎进入成熟收获期。",
                "is_good_or_bad": {
                    "pros": "好在自研 AI 芯片（Trainium 2）与云计算软硬件全栈闭环，自由现金流处于史上最佳修复周期。",
                    "cons": "坏在各大公有云竞品（微软 Azure、谷歌云 GCP）在 OpenAI/Gemini 催化下激烈竞争，AWS 市场份额面临阶段性防守压力。"
                },
                "long_term_strategy": "适合长线投资者作为数字经济与云计算核心压舱石配置，重点关注 AWS 季报同比增速与自研 AI 芯片落地进展。"
            },
            "competitors": [
                {
                    "symbol": "MSFT.US",
                    "name": "Microsoft Azure",
                    "threat": "极高",
                    "market_position": "全球公有云二当家，企业级 AI 落地先锋",
                    "comparison": "凭借 OpenAI 深度绑定与 Office 365 渠道，在企业大模型部署上势头迅猛。",
                    "bj_differentiation": "【AWS 微观突围】基础设施成熟度、API 丰富度及 Bedrock 多模型路由中立性依然处于行业领头羊地位。"
                },
                {
                    "symbol": "GOOGL.US",
                    "name": "Google Cloud (GCP)",
                    "threat": "高",
                    "market_position": "数据分析与多模态大模型技术强者",
                    "comparison": "凭借自研 TPU 算力与开源生态吸引了众多 AI 原生独角兽客户。",
                    "bj_differentiation": "【AWS 微观突围】全球可用区网络与跨国企业关键任务运维 SLA 稳定性显著更成熟。"
                },
                {
                    "symbol": "WMT.US",
                    "name": "Walmart (沃尔玛)",
                    "threat": "中",
                    "market_position": "全球全渠道实体零售巨头",
                    "comparison": "依托数千家线下门店提供路边提货与即时生鲜配送。",
                    "bj_differentiation": "【亚马逊电商突围】第三方卖家长尾选品生态与全美次日达/当日达履约网络规模无人能及。"
                }
            ]
        },
        "products": [
            {
                "name": "AWS 云计算与 Amazon Bedrock 企业 AI 平台",
                "category": "云基础设施与企业级 AI (Cloud & AI)",
                "strategic_role": "绝对利润支柱与技术护城河 (Core Profit Engine)",
                "revenue_ratio": "~17%~18% 营收贡献 (贡献 60%+ 营业利润)",
                "gross_margin": "35%~38% 营业利润率",
                "s_curve_stage": "生成式 AI 重构下的第二加速期",
                "switching_cost": "极高 (数据库与底层 IT 架构迁移阻力巨大)",
                "barrier_type": "规模效应 + 极深软件生态与 SLA 稳定性",
                "barrier_detail": "涵盖 200+ 项全功能云服务，自研 Graviton4 CPU 及 Trainium2 芯片显著压低计算成本；Bedrock 聚合全球顶尖大模型（Anthropic Claude, Meta Llama 等），提供企业级数据隐私安全保障。",
                "market_share": "全球公有云基础设施市占率约 31%~33% (稳居第一)",
                "business_model": "基于用量的计费模式 (Pay-as-you-go) 与 1~3 年企业承诺采购合约 (Reserved Instances)。",
                "prospect_and_catalysts": "自研 AI 算力芯片大规模商用与百亿级大模型企业工作流上云带来持续高毛利经常性收入。"
            },
            {
                "name": "Prime 会员生态与 FBA 全球极速履约网络",
                "category": "会员生态与智慧物流 (Membership & Logistics)",
                "strategic_role": "全网流量底座与高频粘性锁 (Moat Defense)",
                "revenue_ratio": "~65% 综合零售及履约营收",
                "gross_margin": "履约成本率降至历史低位",
                "s_curve_stage": "区域化网络精细化运营期",
                "switching_cost": "高 (习惯次日达与 Prime 视听权益后极难流失)",
                "barrier_type": "天量重资产实体物流与分拣中心网络",
                "barrier_detail": "全美建立 8 大区域化仓储网络，当日达/次日达履约时效遥遥领先同行；第三方卖家深度依赖 FBA 获得黄金购物车 (Buy Box) 曝光。",
                "market_share": "全美电商零售市场份额超 38%",
                "business_model": "Prime 年费订阅 ($139/年) + 第三方卖家佣金与仓储配送费。",
                "prospect_and_catalysts": "无人机送货与仓储机器人自动化持续压低单件履约成本，释放零售端利润弹性。"
            }
        ],
        "supply_chain": {
            "upstream_dependency": "AWS 依赖英伟达高端 GPU 与台积电先进封装代工自研 Trainium 芯片；电商零售依赖全球数百万独立品牌与制造供应商。",
            "downstream_concentration": "面向全球数亿终端消费者与数十万企业级政企云客户，无单一客户集中度风险。",
            "spof_bottlenecks": [
                {
                    "node": "数据中心电力容量与电网变压器供给瓶颈",
                    "threat_level": "高",
                    "impact": "北美 AI 数据中心扩张面临当地电网负荷审查，清洁能源与核能供电接入周期成为 AWS 算力交付最大硬约束。"
                },
                {
                    "node": "自研 AI 芯片制程良率与软硬件配套迁移",
                    "threat_level": "中",
                    "impact": "开发者对英伟达 CUDA 依赖度高，AWS 需持续投入 Neuron SDK 建设以推动客户拥抱 Trainium。"
                }
            ],
            "customer_bargaining": {
                "top_customers_share": "云业务客户分散度极高，消费端客群全覆盖；",
                "in_house_threat": "企业自行搭建私有云成本极其昂贵，上云趋势不可逆；",
                "pricing_power": "广告业务与 AWS 具备强定价权，电商自营保持亲民低价。"
            },
            "geopolitical_and_resilience": "全球各大数据中心区域实行多可用区冗余备份，业务遍及全球核心主流国家，具备极强的抗风险底座。"
        }
    },
    "META.US": {
        "essence": {
            "summary": "全球社交网络帝国与开源 AI 领军者：手握 32 亿+ 日活用户池，以 Advantage+ AI 广告引擎实现极致变现，以 Llama 开放生态破除闭源垄断。",
            "profit_engine": "【底层盈利真相】Meta 拥有人类商业历史上最庞大的去中心化社交关系链与数字日活入口（Facebook, Instagram, WhatsApp, Messenger）。其核心盈利引擎是‘基于用户行为数据的高毛利精准数字广告’（毛利率 80%+，营业利润率 40%+）。通过率先落地 AI 广告推荐引擎 (Advantage+)，成功克服了苹果 ATT 隐私新规冲击，大幅提升广告主投产比 (ROAS)；同时开源 Llama 大模型重构全球开发者生态，倒逼全行业算力与开发成本下行。",
            "flywheel": "全球 32 亿+ 用户高频使用社交产品 ➔ 沉淀万亿级多模态社交互动数据 ➔ 训练顶尖 AI 推荐与广告算法 ➔ 广告投放 ROI 显著超越同行 ➔ 吸引全球数千万广告主刚性预算 ➔ 产生丰沛现金流投入万卡 AI 集群 ➔ 打造最强开源模型 Llama 进一步赋能主营业务。",
            "segments": [
                {"name": "核心应用家族数字广告 (Family of Apps Ads)", "ratio": "~97%~98% 营收", "role": "绝对现金流引擎：Instagram Reels 与 Facebook 信息流精准展示广告。"},
                {"name": "Reality Labs (元宇宙与智能硬件)", "ratio": "~1%~2% 营收", "role": "长线战略期权：Quest VR 头显与 Ray-Ban Meta 智能眼镜，短期处于高额研发投入阶段。"}
            ]
        },
        "industry": {
            "sector": "全球移动社交网络、程序化广告与通用 AI (Social Media & AI)",
            "macro_backdrop": "【宏观经济与周期研判】全球数字广告支出全面回暖，跨境电商出海（Shein, Temu 等）及本土零售广告投放极其强劲；生成式 AI 工具全面赋能广告素材自动生成，大幅拉升广告单价与展示量。",
            "tam": "全球数字广告市场超 6,000 亿美元，Meta 与 Google 双寡头垄断优势稳固。",
            "lifecycle": {
                "current_stage": "成熟现金牛期 (Mature Cash Cow)",
                "stage_index": 2,
                "all_stages": [
                    {"name": "初创探索期", "desc": "大学校园社交网络诞生"},
                    {"name": "高速成长期", "desc": "收购 Instagram/WhatsApp 与移动端广告爆发"},
                    {"name": "成熟现金牛期", "desc": "效率之年 (Year of Efficiency)、AI 广告狂飙与万卡集群"},
                    {"name": "转型再成长期", "desc": "智能眼镜/端侧 AI 与元宇宙空间计算突破"},
                    {"name": "衰退防御期", "desc": "用户时长被新兴短视频彻底分流"}
                ],
                "characteristics": "经历组织扁平化与成本压缩后，盈利能力达到历史峰值，年自由现金流超 400 亿美元，同时在开源 AI 领域确立统治级领导地位。",
                "is_good_or_bad": {
                    "pros": "好在 WhatsApp 商业化提速、Reels 变现率追平主信息流，Ray-Ban 智能眼镜爆火打开端侧 AI 硬件想象空间。",
                    "cons": "坏在每年超 350~400 亿美元的算力 CapEx 开支高企，且 Reality Labs 每年亏损超百亿美元，若广告景气度回调将引发利润承压。"
                },
                "long_term_strategy": "适合偏重高 ROIC 与充沛自由现金流的价值成长型投资者持有，重点关注 Advantage+ 广告单价改善与 Ray-Ban 硬件销量数据。"
            },
            "competitors": [
                {
                    "symbol": "GOOGL.US",
                    "name": "Google / YouTube",
                    "threat": "极高",
                    "market_position": "全球数字广告第一大霸主",
                    "comparison": "拥有搜索意图与 YouTube 长视频流量护城河。",
                    "bj_differentiation": "【Meta 微观突围】基于人际关系链与兴趣推荐的信息流广告转化更原生，Reels 短视频日均播放量高速攀升。"
                },
                {
                    "symbol": "SNAP.US",
                    "name": "Snapchat",
                    "threat": "中",
                    "market_position": "年轻世代熟人社交与 AR 滤镜平台",
                    "comparison": "在欧美年轻人群体中具备粘性，但广告变现基础设施与算法能力远弱于 Meta。",
                    "bj_differentiation": "【Meta 微观突围】拥有数以万计高端 GPU 组成的算法训练集群，广告投放自动化水平降维打击竞品。"
                }
            ]
        },
        "products": [
            {
                "name": "Advantage+ AI 驱动程序化广告投放引擎",
                "category": "算法平台与广告系统 (AI Advertising Engine)",
                "strategic_role": "绝对现金流引擎 (Core Cash Cow)",
                "revenue_ratio": "~97% 营收贡献",
                "gross_margin": "80%+ 超高毛利",
                "s_curve_stage": "AI 全自动化广告成熟收获期",
                "switching_cost": "高 (中小商家依赖其获得直接销售转化，ROI 无可替代)",
                "barrier_type": "32 亿日活社交数据飞轮 + 顶级 GPU 算力推荐集群",
                "barrier_detail": "广告主只需上传预算和商品链接，系统通过大模型全自动生成多版文案、图片与背景音乐，并在数毫秒内完成精准受众定向出价，转化率显著高于传统广告。",
                "market_share": "全球移动社交广告市场份额超 60%",
                "business_model": "基于展示千次成本 (CPM) 与点击成本 (CPC) 的竞价拍卖模式。",
                "prospect_and_catalysts": "生成式 AI 原生广告创意生成普及与 WhatsApp 商务对话点击广告 (Click-to-Message) 快速放量。"
            },
            {
                "name": "Ray-Ban Meta 智能 AI 眼镜与 Quest 空间生态",
                "category": "下一代端侧智能硬件 (Next-Gen AI Hardware)",
                "strategic_role": "长线战略期权 (Strategic Growth Option)",
                "revenue_ratio": "~1%~2% 营收",
                "gross_margin": "硬件接近盈亏平衡，旨在抢占端侧入口",
                "s_curve_stage": "消费级智能眼镜爆发放量期",
                "switching_cost": "中 (穿戴式设备生态与个人数字助理绑定)",
                "barrier_type": "时尚奢侈品品牌声誉 (EssilorLuxottica) + 多模态端侧大模型",
                "barrier_detail": "成功打破科技产品傻大黑粗魔咒，融合第一视角高清拍摄、开放式音频与 Meta AI 实时视觉问答，销量远超市场预期，成为端侧 AI 第一落地形态。",
                "market_share": "全球智能拍摄与语音眼镜市占率第一",
                "business_model": "硬件销售与未来潜在软件订阅、增值应用商店分成分成。",
                "prospect_and_catalysts": "搭载微型显示光机 (HUD) 的下一代真 AR 眼镜研发落地与全球出货量破千万。"
            }
        ],
        "supply_chain": {
            "upstream_dependency": "极度依赖英伟达提供高端 Hopper/Blackwell 算力芯片及台积电先进制程；硬件代工依赖歌尔股份及依视路陆逊梯卡制造合作。",
            "downstream_concentration": "直面全球超 1,000 万活跃广告主（涵盖大型跨国企业及海量独立电商卖家），客户集中度极度分散。",
            "spof_bottlenecks": [
                {
                    "node": "算力基础设施 CapEx 资本开支折旧压力",
                    "threat_level": "中高",
                    "impact": "万卡 GPU 集群投资巨大，若未来 12~24 个月宏观广告需求疲软，巨额固定资产折旧将侵蚀营业利润率。"
                },
                {
                    "node": "欧盟与欧美监管机构对数据隐私与未成年人保护审查",
                    "threat_level": "中",
                    "impact": "DMA (数字市场法案) 等反垄断调查可能要求剥离数据协同，增加合规摩擦成本。"
                }
            ],
            "customer_bargaining": {
                "top_customers_share": "前百大广告主占比低于 20%，抗单一客户流失能力极强；",
                "in_house_threat": "企业不可能自建 30 亿日活的社交网络；",
                "pricing_power": "AI 赋能下的广告单价具备强劲自主提价权。"
            },
            "geopolitical_and_resilience": "研发与算力集群全部扎根美国本土与欧美盟国，资产负债表现金储备充沛（近 600 亿美元），抗周期韧性极佳。"
        }
    },
    "GOOGL.US": {
        "essence": {
            "summary": "全球商业信息检索垄断者与全栈 AI 原生科技帝国：以 Google 搜索与 YouTube 构筑高毛利广告现金流，以 GCP 公有云与自研 TPU、Gemini 基础模型引领下一代计算范式。",
            "profit_engine": "【底层盈利真相】谷歌掌控着全球 90%+ 桌面与移动搜索市场份额，是全球互联网最底层的意图分发入口。搜索与 YouTube 构筑了年入数千亿美元、毛利率极高的广告印钞机；同时谷歌是全球唯一一家具备‘自研张量芯片 TPU + 自研前沿大模型 Gemini + 全球前三公有云 GCP + 垄断级十亿日活应用矩阵 (Search/YouTube/Maps/Android)’全栈闭环的科技巨无霸。",
            "flywheel": "全球用户在 Google 发起百亿次搜索请求 ➔ 捕获最真实的商业购买意图 ➔ 广告竞价机制最大化单次点击商业价值 ➔ 输送数百亿美元现金流自研 TPU 算力与前沿 AI 算法 ➔ 打造最强 Gemini 多模态原生大模型 ➔ 重塑 AI Overviews 搜索体验防守护城河。",
            "segments": [
                {"name": "Google 核心搜索与相关广告 (Google Search & other)", "ratio": "~56%~58% 营收", "role": "绝对利润底座：极高毛利的意图竞价搜索广告，全网商业入口。"},
                {"name": "YouTube 视频广告与流媒体订阅", "ratio": "~10%~11% 营收", "role": "流媒体之王：全球最大中长视频与短视频 (Shorts) 创作者生态。"},
                {"name": "Google Cloud (GCP) 云计算与 AI 算力服务", "ratio": "~11%~13% 营收", "role": "高速增长引擎：营业利润率快速转正扩张，企业级 AI 核心载体。"},
                {"name": "Google 订阅、平台与硬件设备 (Subscriptions & Devices)", "ratio": "~10%~12% 营收", "role": "生态协同：Google One 云存储、Play 应用商店及 Pixel 手机。"}
            ]
        },
        "industry": {
            "sector": "全球商业搜索、数字广告与全栈云计算基础设施 (Search & Cloud)",
            "macro_backdrop": "【宏观经济与生成式 AI 冲击研判】市场曾担忧 ChatGPT 等生成式对话工具颠覆传统搜索框，但随着 AI Overviews 快速铺开及 Gemini 2.0 原生多模态能力突破，谷歌成功证明了其分发入口与算力基础设施的坚韧性，搜索广告营收再创历史新高。",
            "tam": "全球信息检索、公有云与企业级 AI 软件市场空间超 1.2 万亿美元。",
            "lifecycle": {
                "current_stage": "成熟现金牛期 (Mature Cash Cow)",
                "stage_index": 2,
                "all_stages": [
                    {"name": "初创探索期", "desc": "PageRank 算法破局与硅谷传奇诞生"},
                    {"name": "高速成长期", "desc": "收购 Android/YouTube 与搜索广告全球垄断"},
                    {"name": "成熟现金牛期", "desc": "千亿级自由现金流、GCP 盈利爆发与全栈 AI 落地"},
                    {"name": "转型再成长期", "desc": "Waymo 自动驾驶商业化与量子计算/具身智能前沿探索"},
                    {"name": "衰退防御期", "desc": "反垄断分拆与生成式 AI 替代"}
                ],
                "characteristics": "业务模式成熟度极高，资产负债表拥有超 1,000 亿美元现金等价物，年自由现金流超 700 亿美元，同时在基础前沿科学领域持续引领全球。",
                "is_good_or_bad": {
                    "pros": "好在自研 TPU 芯片历经六代迭代，相比同行自建算力成本优势显著，且 Waymo 商业化无人出租车落地遥遥领先。",
                    "cons": "坏在美国司法部 (DOJ) 针对搜索反垄断及广告技术栈的世纪诉讼裁决面临分拆或限制默认搜索引擎协议 (如每年支付给苹果的 200 亿美金 TAC 协议) 的潜在监管冲击。"
                },
                "long_term_strategy": "适合长线价值投资者在反垄断诉讼恐慌或 AI 替代情绪打压估值倍数时果断买入，享受其深厚的科研资产与现金流复利。"
            },
            "competitors": [
                {
                    "symbol": "MSFT.US",
                    "name": "Microsoft / OpenAI",
                    "threat": "高",
                    "market_position": "企业生产力与前沿大模型先行者",
                    "comparison": "ChatGPT 改变了部分问答习惯，Bing 试图切入搜索市场但份额撼动有限。",
                    "bj_differentiation": "【谷歌微观突围】原生多模态实时检索、全网实时爬虫索引能力与十亿级产品分发渠道具有无法撼动的系统级黏性。"
                },
                {
                    "symbol": "AMZN.US",
                    "name": "Amazon AWS",
                    "threat": "高",
                    "market_position": "全球公有云龙头",
                    "comparison": "在企业 IT 基础设施托管上体量依然大于 GCP。",
                    "bj_differentiation": "【GCP 微观突围】在大数据分析 (BigQuery) 与自研 TPU 算力集群性价比上对 AI 原生企业具备独特吸引力。"
                }
            ]
        },
        "products": [
            {
                "name": "Google 搜索网络与 AI Overviews 智能检索系统",
                "category": "商业意图搜索与广告网络 (Search & Ads)",
                "strategic_role": "绝对现金流压舱石 (Core Cash Cow)",
                "revenue_ratio": "~57% 营收贡献",
                "gross_margin": "75%~80% 极高毛利",
                "s_curve_stage": "生成式 AI 赋能下的成熟焕新期",
                "switching_cost": "极高 (全球用户‘Google 一下’的行为习惯已成为认知本能)",
                "barrier_type": "全球唯一实时全网网页爬取索引库 + 商业意图精准匹配",
                "barrier_detail": "每天处理数十亿次搜索，拥有全球最庞大的商业广告主竞价生态与高质量点击数据闭环；AI Overviews 直接在搜索结果顶部生成结构化摘要并自然嵌入广告，用户满意度与点击率不降反升。",
                "market_share": "全球通用搜索引擎市占率超过 90%",
                "business_model": "基于商业广告主实时竞价排名的 CPC (Cost-per-click) 付费模式。",
                "prospect_and_catalysts": "Gemini 2.0 多模态代理 (Project Astra) 深度整合进手机桌面与搜索框，引领智能体交互新时代。"
            },
            {
                "name": "Google Cloud Platform (GCP) & 自研 TPU 算力架构",
                "category": "企业公有云与专有 AI 算力 (Cloud & Custom Silicon)",
                "strategic_role": "核心高增长引擎 (Growth Engine)",
                "revenue_ratio": "~12% 营收贡献 (营业利润率快速攀升至 10%~12%)",
                "gross_margin": "规模效应驱动利润率连续超预期扩张",
                "s_curve_stage": "企业级 AI 基础设施红利爆发期",
                "switching_cost": "高 (企业核心业务数据与机器学习管线深度绑定 Vertex AI)",
                "barrier_type": "自研 TPU 算力成本壁垒 + 顶尖多模态基础模型 API",
                "barrier_detail": "历经十余年研发自研 TPU v5e/v6 芯片，单芯片训练与推理成本比采购外采 GPU 显著更优；Vertex AI 平台提供全托管大模型微调部署环境，深受全球开发者青睐。",
                "market_share": "全球公有云排名前三，AI 算力增速领跑行业",
                "business_model": "按需付费与长期企业承诺折扣合约 (Committed Use Discounts)。",
                "prospect_and_catalysts": "企业级生成式 AI 订阅落地与全球前百大企业客户渗透率持续提升。"
            }
        ],
        "supply_chain": {
            "upstream_dependency": "TPU 自研芯片由博通 (Broadcom) 协助设计并由台积电代工；同时大规模采购英伟达 GPU 保障外部客户多元生态需求。",
            "downstream_concentration": "直面全球数十亿普通消费者、数百万广告主及数万家大中型政企客户，收入结构极度多元健康。",
            "spof_bottlenecks": [
                {
                    "node": "反垄断司法审查与苹果默认搜索引擎流量分成 (TAC) 协议风险",
                    "threat_level": "高",
                    "impact": "若法院裁决禁止独家默认分销协议，谷歌需向用户提供搜索选择屏，可能面临极小比例的搜索流量分流。"
                },
                {
                    "node": "AI 搜索算力单次查询推理成本上升",
                    "threat_level": "中",
                    "impact": "大模型生成摘要的单次计算成本高于传统倒排索引，需通过自研 TPU 架构持续优化能耗比。"
                }
            ],
            "customer_bargaining": {
                "top_customers_share": "客户集中度极低，无任何单一客户话语权过高；",
                "in_house_threat": "普通企业无法自建具备全球实时网页索引的搜索系统；",
                "pricing_power": "核心商业搜索关键词具备无与伦比的自主定价权。"
            },
            "geopolitical_and_resilience": "全球布局数百座大型绿色数据中心，拥有超千亿美元自由现金流与极高信用评级，抗宏观金融风暴韧性无与伦比。"
        }
    },
    "PLTR.US": {
        "essence": {
            "summary": "全球国防军工与企业级大数据 AI 操作系统霸主：以极端工程能力打破异构数据孤岛，以 AIP 智能体平台抢占全球政府与跨国企业落地生成式 AI 的神经中枢。",
            "profit_engine": "【底层盈利真相】Palantir 绝非普通通用 SaaS 软件公司，而是‘关键任务型 (Mission-Critical) 国防军工与企业级神经操作系统提供商’。其软件深入渗透美国国防部、情报机构、特种作战司令部以及全球 500 强核心运营工作流，客户替换成本极其高昂（无替代方案 / 迁移即瘫痪）。通过颠覆性的 AIP Bootcamp（实战训练营）模式，将传统数月的软件销售与实施周期压缩至数天，实现净收入留存率 (NDR) 与营业利润率跨越式双升。",
            "flywheel": "军方极严苛战地任务锤炼出无敌的本体 (Ontology) 数据融合架构 ➔ 降维打击民用商业领域痛点 ➔ 推出 AIP 平台让客户在数天内见证 AI 解决实际业务价值 ➔ 推动商业客户签约狂飙 ➔ 产生高黏性经常性收入 ➔ 持续反哺下一代军工自主智能体研发。",
            "segments": [
                {"name": "美国及盟国政府国防业务 (Government)", "ratio": "~54%~56% 营收", "role": "极高确定性压舱石：美国国防部与陆海空三军长期战略级独家订单。"},
                {"name": "全球商业企业级 AI 软件 (Commercial)", "ratio": "~44%~46% 营收", "role": "高斜率增长核引擎：AIP 驱动下北美商业营收同比增速超过 50%+。"}
            ]
        },
        "industry": {
            "sector": "国防军工特种软件、企业级大数据本体与 AI 操作系统 (Defense & Enterprise AI)",
            "macro_backdrop": "【地缘政治与宏观周期研判】俄乌冲突、中东动荡与全球地缘对抗常态化，促使美国与北约盟国军费开支刚性增长，无人机作战与联合全域指挥控制 (JADC2) 急需软件赋能；同时全球企业急需将大模型与自身专有数据合规结合，Palantir 成为唯一的成熟工程化载体。",
            "tam": "全球国防软件、情报分析与企业级 AI 操作决策市场空间超 2,000 亿美元。",
            "lifecycle": {
                "current_stage": "高速成长期 (Rapid Growth)",
                "stage_index": 1,
                "all_stages": [
                    {"name": "初创探索期", "desc": "反恐情报分析与 CIA/In-Q-Tel 早期天使扶持"},
                    {"name": "产品成型期", "desc": "Gotham 与 Foundry 确立军民双轮驱动"},
                    {"name": "高速成长期", "desc": "AIP 爆发引发商业化质变、正式纳入标普500"},
                    {"name": "成熟现金牛期", "desc": "全球跨国企业标配操作系统与高分红回购"},
                    {"name": "衰退防御期", "desc": "政府预算紧缩与竞品低价替代"}
                ],
                "characteristics": "受全球军费刚性开支与企业 AIP 爆发式采纳双重驱动，连续多个季度实现 GAAP 净利润强劲增长，营业利润率突破 35%+，已成为全球增长最迅猛的基础软件巨头。",
                "is_good_or_bad": {
                    "pros": "好在产品护城河极其深厚，进入美国军方最高级别保密认证 (IL6 级安全合规)，在西方盟国内部享有近乎独家的准入垄断权。",
                    "cons": "坏在估值市销率 (PS) 与市盈率 (PE) 处于行业极端高位，市场已将未来 3~5 年的高速增长预期打得极满，任何季度指引微幅不及预期都可能引发股价大幅震荡。"
                },
                "long_term_strategy": "适合认可国防科技与工业软件长期壁垒的高成长型投资者顺势持有，跟踪美国国防部 TITAN 项目及商业新签合同总价值 (TCV)。"
            },
            "competitors": [
                {
                    "symbol": "MSFT.US",
                    "name": "Microsoft Defense & Azure Gov",
                    "threat": "中",
                    "market_position": "全球企业 IT 与国防云基础设施重要供应商",
                    "comparison": "提供底层云主机与基础办公套件，但在复杂战地异构数据深度融合与决策本体上与 Palantir 形成上下游合作而非直接替代。",
                    "bj_differentiation": "【Palantir 专有壁垒】专注于‘本体模型构建’与战场实时作战推演，极端复杂场景下的工程实施能力无竞品可比拟。"
                },
                {
                    "symbol": "SNOW.US",
                    "name": "Snowflake",
                    "threat": "中低",
                    "market_position": "云原生数据仓库领军者",
                    "comparison": "擅长数据存储与 SQL 分析，缺乏将数据流直接转化为前线行动指南的操作层逻辑。",
                    "bj_differentiation": "【Palantir 专有壁垒】Foundry 是真正闭环的操作决策系统 (Operational System)，能直接向物理设备与业务流回写指令。"
                }
            ]
        },
        "products": [
            {
                "name": "AIP (Artificial Intelligence Platform) 智能体与决策中枢",
                "category": "商业级大模型操作系统 (Enterprise AI OS)",
                "strategic_role": "绝对增长核引擎 (Growth Engine)",
                "revenue_ratio": "~40%~45% 商业营收拉动主力",
                "gross_margin": "82%~84% 极高毛利",
                "s_curve_stage": "企业级普及爆发主升浪 (S曲线极陡峭段)",
                "switching_cost": "极高 (业务逻辑与决策流程沉淀后几乎无法剥离)",
                "barrier_type": "专有本体架构 (Ontology) + 严格权限审计与防幻觉护栏",
                "barrier_detail": "允许企业将任何大语言模型直接接入实时企业数据中枢，大模型在受严格权限控制的本体模型上运行，执行真实的物理业务操作（如自动调整排产计划、自动化供应链调度），彻底解决大模型在企业落地中的‘幻觉与失控’痛点。",
                "market_share": "企业级生产环境 AI 落地标杆产品",
                "business_model": "按年度订阅与席位/计算单元阶梯收费，客户加购扩展倍率极高。",
                "prospect_and_catalysts": "AIP Bootcamp 客户转化率超预期，签约商业客户数持续呈现三位数同比爆发增长。"
            },
            {
                "name": "Gotham 国防情报与战场态势指挥系统",
                "category": "国防军工战地指挥平台 (Defense & Intelligence OS)",
                "strategic_role": "军工国防基本盘与信誉图腾 (Moat Anchor)",
                "revenue_ratio": "~50%~55% 营收贡献",
                "gross_margin": "长期稳定高毛利",
                "s_curve_stage": "成熟统治级刚性列装期",
                "switching_cost": "近乎无穷大 (涉及国防机密、战备态势与军令系统，无可替代)",
                "barrier_type": "最高安全准入合规壁垒 (DoD IL6 认证) + 战火检验可靠性",
                "barrier_detail": "融合卫星遥感、雷达信号、无人机侦察及地面特工情报，在电子沙盘上实时呈现敌我态势并辅助打击决策；美军陆军 TITAN (下一代战术情报目标地面站) 核心软件承包商。",
                "market_share": "美国防部及西方五眼联盟首选特种软件提供商",
                "business_model": "政府多年期大额固定采办合同与研发追加预算拨款。",
                "prospect_and_catalysts": "无人协同作战与自主智能体在防务领域的全面列装预算下发。"
            }
        ],
        "supply_chain": {
            "upstream_dependency": "纯软件架构，运行于各大商业公有云（AWS GovCloud, Microsoft Azure Government）及军方私有涉密服务器上，无物理原材料采购瓶颈。",
            "downstream_concentration": "政府端高度依赖美国联邦政府部门，商业端客户正快速多元化扩展至医疗、金融、制造、能源等上千家企业。",
            "spof_bottlenecks": [
                {
                    "node": "美国联邦政府预算审批与国防授权法案 (NDAA) 拨款节奏",
                    "threat_level": "中",
                    "impact": "若美国国会预算僵局或政府停摆，可能导致部分特种防务新合同签署审批周期推迟数月。"
                },
                {
                    "node": "高级工程人才（前沿算法与拥有绝密安全许可的安全工程师）流失",
                    "threat_level": "低中",
                    "impact": "高要求涉密项目需要极高政治背景审查与工程素质，人才招聘壁垒高。"
                }
            ],
            "customer_bargaining": {
                "top_customers_share": "美军等前五大政府客户占比较高，但合作紧密度处于不可替代状态；",
                "in_house_threat": "政府曾试图自研竞品均告失败，外包给 Palantir 成为最经济高效途径；",
                "pricing_power": "由于无可替代性，公司具备极强的商业合同溢价权与净扩张率。"
            },
            "geopolitical_and_resilience": "坚定站在西方自由民主世界盟友阵营，资产全部位于美国及五眼联盟本土，无任何来自非友好国家的地缘供应链风险。"
        }
    },
    "KO.US": {
        "essence": {
            "summary": "全球软饮料百年传奇与轻资产特许装瓶商业帝国：以全球第一品牌心智构筑宽阔护城河，以重资产装瓶外包实现极高 ROIC 与超长跨期高股息回报。",
            "profit_engine": "【底层盈利真相】可口可乐真正的商业模式是‘高毛利浓缩液销售与全球品牌特许授权商’。公司将重资产、低毛利的罐装制造、卡车运输与区域物理配送大部分剥离给全球独立装瓶伙伴（如太古、中粮、Coca-Cola FEMSA），自身仅保留高毛利的浓缩液生产和全球品牌营销，享有 60%+ 的毛利率和极高的资本回报率 (ROIC 16%~20%)，连续 62 年增加股息，堪称巴菲特式长钱复利典范。",
            "flywheel": "百年积淀的无敌品牌心智 ➔ 全球消费者极高频日常解渴复购 ➔ 特许装瓶商竞相加盟分销网络 ➔ 形成遍布全球 200+ 国家的终极渠道壁垒 ➔ 产生丰沛可预测的自由现金流 ➔ 支撑持续品牌营销与每年增加现金分红 ➔ 进一步强化全球第一饮料地位。",
            "segments": [
                {"name": "含气碳酸饮料系列 (Sparkling Soft Drinks)", "ratio": "~65%~68% 营收", "role": "绝对现金流基石：可口可乐经典款与零度无糖系列，全球第一认知度。"},
                {"name": "水、运动饮料、咖啡与茶 (Hydration, Sports, Coffee & Tea)", "ratio": "~20%~22% 营收", "role": "健康转型护城河：Sprite, Fanta, Dasani, BodyArmor, Costa 咖啡。"},
                {"name": "果汁、价值乳品与植物基饮品 (Juice, Value-Added Dairy & Plant)", "ratio": "~10%~12% 营收", "role": "高客单价营养消费：美汁源 (Minute Maid), Fairlife 超滤牛奶。"}
            ]
        },
        "industry": {
            "sector": "全球无酒精即饮饮料与快消特许品牌 (Non-Alcoholic Ready-to-Drink Beverages)",
            "macro_backdrop": "【宏观经济与周期研判】抗通胀韧性极强，单罐单瓶饮料单价低（属于‘口红效应’大众微型消费），消费者对数美分的小幅提价极不敏感，在滞胀或经济衰退期具备无与伦比的防守属性。",
            "tam": "全球无酒精即饮饮料市场规模超 1.3 万亿美元，随着发展中国家城市化进程每年稳健增长 4%~6%。",
            "lifecycle": {
                "current_stage": "成熟现金牛期 (Mature Cash Cow)",
                "stage_index": 2,
                "all_stages": [
                    {"name": "初创探索期", "desc": "药剂师彭伯顿发明可口可乐配方与首杯汽水售出"},
                    {"name": "高速成长期", "desc": "二战军需补给走向全球与装瓶系统成熟"},
                    {"name": "成熟现金牛期", "desc": "全球 200+ 国家渗透、轻资产重组与连续半世纪分红增长"},
                    {"name": "转型再成长期", "desc": "全面去糖化、全品类饮料公司 (Total Beverage Company) 演进"},
                    {"name": "衰退防御期", "desc": "碳酸饮料彻底被替代与品牌老化"}
                ],
                "characteristics": "历经百年一战二战、冷战及多次全球经济危机考验，现金流确定性极高，资本开支需求极低，处于经典的成熟期现金奶牛皇冠位置。",
                "is_good_or_bad": {
                    "pros": "好在商业模式抗周期、定价权极强（输入性通胀可轻松顺畅传导至终端），股息收益率常年维持在 3.0%~3.5% 且具备 62 年连续增长信用。",
                    "cons": "坏在碳酸饮料整体品类面临全球健康控糖趋势的长期逆风，内生销量增长中枢维持在 2%~4% 的低个位数区间，缺乏爆发式科技期权。"
                },
                "long_term_strategy": "适合低风险偏好、养老基金与长线长钱作为抗通胀高股息复利底仓配置，在股息率突破 3.5% 或估值回调至 20x PE 以下时布局性价比极高。"
            },
            "competitors": [
                {
                    "symbol": "PEP.US",
                    "name": "PepsiCo (百事公司)",
                    "threat": "高",
                    "market_position": "全球饮料与休闲零食双巨头",
                    "comparison": "拥有乐事 (Lay's)、多力多滋等高毛利休闲零食业务，食品抗风险更多元化。",
                    "bj_differentiation": "【可口可乐微观突围】在纯即饮饮料赛道可口可乐品牌心智占有率与全球特许装瓶商专注度更高，轻资产纯利润率更丰厚。"
                },
                {
                    "symbol": "KDP.US",
                    "name": "Keurig Dr Pepper",
                    "threat": "中",
                    "market_position": "北美胶囊咖啡与特色碳酸饮料挑战者",
                    "comparison": "在北美特定区域与胡椒博士品类具备忠诚拥趸，但缺乏全球性分销网络。",
                    "bj_differentiation": "【可口可乐微观突围】全球 200 余个国家的密集冰柜陈列与即时可得性是区域竞品难以逾越的高墙。"
                }
            ]
        },
        "products": [
            {
                "name": "可口可乐经典旗舰与无糖系列 (Coca-Cola Original & Zero Sugar)",
                "category": "核心碳酸饮料旗舰 (Core Trademark)",
                "strategic_role": "绝对现金流与心智图腾 (Core Cash Anchor)",
                "revenue_ratio": "~46%~48% 营收贡献",
                "gross_margin": "62%~65% 高毛利",
                "s_curve_stage": "全球百年统治级长青产品",
                "switching_cost": "中高 (独特的神秘配方口感与终身饮用习惯锁定)",
                "barrier_type": "全球第一饮料品牌无形资产 + 终极渠道触达网络",
                "barrier_detail": "每天全球消费超 22 亿杯可口可乐产品；Zero Sugar 无糖系列成功承接健康消费升级，销量连续多年双位数稳步增长。",
                "market_share": "全球碳酸软饮料市场份额超 48%",
                "business_model": "向特许装瓶厂销售浓缩原浆 (Syrup/Concentrate) 并收取品牌授权分成。",
                "prospect_and_catalysts": "新包装规格迷你化 (Mini-cans) 提升单毫升售价与发展中国家即饮渗透率提升。"
            },
            {
                "name": "全球独立特许装瓶商专营系统 (The Bottling System Network)",
                "category": "轻资产专营网络与分销渠道 (Bottling Franchise System)",
                "strategic_role": "护城河承载底座与轻资产转型成果 (Moat Delivery Mechanism)",
                "revenue_ratio": "重资产剥离后的高 ROIC 商业模式基石",
                "gross_margin": "自身仅承担轻资产环节，推升 ROIC 超 16%~20%",
                "s_curve_stage": "成熟高效全球协同网络",
                "switching_cost": "极高 (特许装瓶商投入数百亿美元工厂与车队，与可口可乐休戚与共)",
                "barrier_type": "不可复制的物理分销与终端冰柜网点壁垒",
                "barrier_detail": "全球数百万个销售终端、数千万台专有红白冰柜，任何潜在挑战者想把饮料摆上全球便利店货架都需要付出不可承受的进场费与物流成本。",
                "market_share": "全球最大的饮料分销实体物流系统",
                "business_model": "装瓶商负责重资产罐装与落地配送，可口可乐总部输出品牌营销与技术支持。",
                "prospect_and_catalysts": "数字化供应链管理与智能售货机网络进一步提升单机坪效与补货效率。"
            }
        ],
        "supply_chain": {
            "upstream_dependency": "浓缩液主要原材料包括糖/高果糖浆、水、咖啡因及专有香精原料；由于采购规模全球最大，对大宗农产品具备极强对冲锁价能力。",
            "downstream_concentration": "通过数十家大型特许装瓶集团将产品铺向全球 200 多个国家上千万个零售小店、超市及餐饮影院，无单一终端依赖风险。",
            "spof_bottlenecks": [
                {
                    "node": "核心装瓶原材料（铝罐、PET 塑料粒子及原糖）通胀波动",
                    "threat_level": "中",
                    "impact": "虽然可口可乐可顺畅提价，但大宗包装材料大幅波动会短期增加特许装瓶商的经营现金流压力。"
                },
                {
                    "node": "部分地区水资源保护与地方环保法规限制",
                    "threat_level": "低中",
                    "impact": "装瓶工厂水资源消耗受到关注，可口可乐推行 100% 水回馈生态计划以规避环境合规风险。"
                }
            ],
            "customer_bargaining": {
                "top_customers_share": "终端客户为全球数十亿普通民众，分散度达到极致；",
                "in_house_threat": "家庭或竞品无法复制经典配方口感与品牌情感连接；",
                "pricing_power": "百年品牌带来的强定价权，每年可平稳跑赢通胀 2%~3%。"
            },
            "geopolitical_and_resilience": "业务横跨全球五大洲，没有任何单一国家能动摇其基本盘；资产负债表拥有充沛现金流与顶尖债务信用评级，是穿越任何战争与经济危机的避风港标杆。"
        }
    },
    "WM.US": {
        "essence": {
            "summary": "北美固废危废处理与环保公用事业绝对霸主：坐拥全美最庞大的不可再生垃圾填埋场网络，以独占性环卫牌照与特许收集路线构筑几乎不可攻破的准市政垄断壁垒。",
            "profit_engine": "【底层盈利真相】Waste Management 本质上不是简单的环卫卡车清洁队，而是一家‘拥有稀缺特许物理不动产（填埋场）并按吨收费的公用事业级收费站’。由于极其严苛的环保法规 (EPA) 与邻避效应 (NIMBY)，在北美新建垃圾填埋场几乎完全不可能获得审批。WM 拥有全美近 260 座活跃填埋场，占全美总容量近 30%，掌握终极终端处理权。其在商业与市政清运合同中普遍绑定‘CPI 通胀调整与燃料附加费联动条款’，具备极强的抗通胀自动提价权，提供类市政债券般高确定性的自由现金流。",
            "flywheel": "垄断核心城市不可再生的填埋场物理资产 ➔ 控制终端垃圾倒包定价权 (Tipping Fees) ➔ 支撑高密度专用垃圾车队实现最低单箱清运成本 ➔ 赢得市政与商业客户 3~10 年长期排他性长约 ➔ 产生丰沛可预测现金流 ➔ 投资垃圾填埋气制可再生天然气 (RNG) 增厚收益 ➔ 进一步抬高环保准入门槛。",
            "segments": [
                {"name": "商业与工业固废清运 (Commercial & Industrial)", "ratio": "~42%~45% 营收", "role": "绝对现金流引擎：商业楼宇、工矿企业长期定期清运，毛利最高。"},
                {"name": "居民生活垃圾特许清运 (Residential Collection)", "ratio": "~28%~30% 营收", "role": "市政刚需基石：各城市独家特许经营权合约，抗经济危机属性极强。"},
                {"name": "垃圾填埋场处置与倒包费 (Landfill Tipping Fees)", "ratio": "~18%~20% 营收", "role": "垄断利润源泉：按入场吨位收取高额处置费，甚至向第三方竞品卡车收费。"},
                {"name": "可再生天然气 (RNG) 与资源循环利用", "ratio": "~8%~10% 营收", "role": "高收益增长期权：将填埋场沼气提纯为绿色车用燃料，享受政府清洁能源补贴。"}
            ]
        },
        "industry": {
            "sector": "北美固废环境治理与特许市政公用事业 (Waste Management & Environmental Services)",
            "macro_backdrop": "【宏观经济与抗衰退研判】无论宏观经济繁荣还是萧条、无论利率高企还是通胀飙升，居民和企业每天都必须产生并清理垃圾；其服务需求具有零价格弹性与极强刚需性，是全球主权长钱与低风险资本最顶级的防御避风港。",
            "tam": "北美固废危废处置与循环经济市场超 1,100 亿美元，每年伴随人口与城市化平稳内生扩张 3%~5%。",
            "lifecycle": {
                "current_stage": "成熟现金牛期 (Mature Cash Cow)",
                "stage_index": 2,
                "all_stages": [
                    {"name": "初创探索期", "desc": "地方性垃圾清运散户整合"},
                    {"name": "高速并购期", "desc": "全美跑马圈地收购私营填埋场"},
                    {"name": "成熟现金牛期", "desc": "双寡头格局稳固、自动通胀提价与持续分红回购"},
                    {"name": "转型再成长期", "desc": "填埋场全面加装 RNG 沼气发电与自动化分拣中心"},
                    {"name": "衰退防御期", "desc": "零废弃社会模式与替代清运技术冲击"}
                ],
                "characteristics": "行业格局高度成熟且呈现 WM 与 Republic Services 双寡头垄断，资本开支稳定可预测，连续 20 余年保持股息稳定增长。",
                "is_good_or_bad": {
                    "pros": "好在填埋场资源具有物理不可替代性与极强排他性，提价完全跑赢核心通胀，自由现金流转换率极高。",
                    "cons": "坏在估值常年处于公用事业板块估值上限 (PE 30x+)，高估值隐含了极低风险溢价，若基建并购整合迟缓将压制股价弹性。"
                },
                "long_term_strategy": "适合追求稳定抗通胀现金流的长期价值投资者作为压舱底仓，在防御情绪退潮估值回调时吸纳复利收益最佳。"
            },
            "competitors": [
                {
                    "symbol": "RSG.US",
                    "name": "Republic Services",
                    "threat": "高",
                    "market_position": "北美固废环保第二大巨头 (与 WM 瓜分近半市场)",
                    "comparison": "网络覆盖与商业模式极其相似，在特定美南美西区域路线密度略高。",
                    "bj_differentiation": "【WM 规模与填埋场壁垒】拥有更多战略级不可替代的巨型填埋场资产，且 RNG 可再生天然气商业化开发进度领先同行。"
                },
                {
                    "symbol": "WCN.US",
                    "name": "Waste Connections",
                    "threat": "中高",
                    "market_position": "聚焦北美非高密度二三线与排他性市场的第三大玩家",
                    "comparison": "在中小城镇独家垄断协议占比高，净利润率优秀。",
                    "bj_differentiation": "【WM 规模与填埋场壁垒】在特大都市圈及跨国工业企业全国性打包招标中综合服务能力绝对占优。"
                }
            ]
        },
        "products": [
            {
                "name": "全美特许商业与市政固废清运服务网络",
                "category": "特许清运运营网络 (Collection Operations)",
                "strategic_role": "绝对现金流压舱石 (Cash Cow Anchor)",
                "revenue_ratio": "~70% 营收贡献",
                "gross_margin": "38%~42% 稳定运营毛利",
                "s_curve_stage": "成熟统治级刚需服务期",
                "switching_cost": "高 (市政 5~10 年排他协议与商业客户合同自动续约机制)",
                "barrier_type": "特许市政准入牌照 + 车队高密度路线规模效应",
                "barrier_detail": "在特定街区拥有最高的垃圾桶密度，使得单车单程清运成本远低于任何外来新进入者；合同自带 CPI 自动上浮条款，确保抗通胀收益锁定。",
                "market_share": "全美最大的固废清运车队 (超 26,000 辆特种收集车)",
                "business_model": "按月收取固定清运月费，附加燃料与环保合规附加费。",
                "prospect_and_catalysts": "压缩天然气 (CNG) 车队全面替代柴油卡车，燃料成本节约与环保 ESG 评级提升。"
            },
            {
                "name": "战略级垃圾填埋场 (Tipping Fees) 与 RNG 绿色能源",
                "category": "物理不动产与可再生能源 (Landfill & RNG Assets)",
                "strategic_role": "核心护城河与高毛利杠杆 (Moat Anchor & Margin Lever)",
                "revenue_ratio": "~25% 营收贡献但贡献极高营业利润",
                "gross_margin": "55%~60% 极高资产运营毛利",
                "s_curve_stage": "环保升级与绿色能源高收益收获期",
                "switching_cost": "极高 (跨区域运输垃圾成本高昂，周边 50 英里无平替填埋场)",
                "barrier_type": "严苛 EPA 环保审批特许权与物理土地排他性",
                "barrier_detail": "拥有 250 余座活跃填埋场，第三方竞品车队倾倒垃圾必须支付高昂‘倒包费’；填埋气捕集制成车用天然气，享受美国联邦 RFS (可再生燃料标准) RINs 信用积分变现。",
                "market_share": "北美最大的垃圾填埋容积拥有者",
                "business_model": "按进场吨位收取入场费 + 清洁天然气管网并网销售收益。",
                "prospect_and_catalysts": "新一代多座百兆瓦级 RNG 工厂投产，年增数亿美元高边际现金流。"
            }
        ],
        "supply_chain": {
            "upstream_dependency": "主要采购重型环卫卡车底盘 (Mack/Peterbilt)、柴油/天然气燃料及垃圾分类机械；受单一供应商制约极小。",
            "downstream_concentration": "面向全美超 2,000 万居民家庭及数百万商业工商机构，客户群极度分散无单一风险。",
            "spof_bottlenecks": [
                {
                    "node": "环境保护署 (EPA) 与各州对 PFAS (永久化学品) 渗滤液处置法规收紧",
                    "threat_level": "中",
                    "impact": "若各州要求对填埋场渗滤液中的微量化学品进行深度催化处理，可能短期增加资本性改造成本。"
                },
                {
                    "node": "重卡专业持照驾驶员 (CDL) 薪资上涨与劳工谈判",
                    "threat_level": "中",
                    "impact": "司机工会调薪可能增加人力成本，需通过自动化侧装机械臂车队普及来对冲。"
                }
            ],
            "customer_bargaining": {
                "top_customers_share": "客户集中度极低，前十大客户占比不足 5%；",
                "in_house_threat": "市政当局由于预算紧缩和环保问责，普遍倾向于外包给专业龙头；",
                "pricing_power": "无可争辩的区域垄断提价权，历史年均核心提价率达 4%~6.5%。"
            },
            "geopolitical_and_resilience": "业务 100% 根植于美国与加拿大本土，无任何海外地缘政治或外汇风险，是穿越任何战争与经济危机的超级堡垒。"
        }
    },
    "CAT.US": {
        "essence": {
            "summary": "全球工程机械、采矿装备与工业柴油动力系统的终极霸主：以极端可靠的黄牌重型装备奠定全球基建标准，以后市场零部件与经销商网络形成极强飞轮效应。",
            "profit_engine": "【底层盈利真相】卡特彼勒不仅是制造重型挖掘机和矿卡的设备商，更是一家‘以全球庞大设备装机保有量为基础收取高毛利零部件与维护后市场服务的工业帝国’。公司在长达一个世纪里构建了全球最密不可分的独立经销商网络（Cat Dealers，平均合作超 50 年），新机销售虽受全球矿业与基建宏观周期波动，但后市场零部件与维修服务 (Services & Parts) 毛利率高达 35%+，且贡献了近半营业利润，大幅平滑了制造业周期底线。",
            "flywheel": "顶尖材料与液压工程制造最抗造的重型装备 ➔ 绑定全球独家独立专属经销商网络 (Cat Dealers) ➔ 沉淀全球数百万台在役设备保有量 ➔ 形成终身绑定的专有高毛利零备件更换需求 ➔ 产生充沛现金流投入新一代低碳混动与无人驾驶矿卡 ➔ 进一步拉开与二线竞品的代际差距。",
            "segments": [
                {"name": "建筑工程与城市基建机械 (Construction Industries)", "ratio": "~40%~42% 营收", "role": "规模基本盘：挖掘机、装载机与推土机，直接受益于全球基建开支。"},
                {"name": "资源与大型矿山开采机械 (Resource Industries)", "ratio": "~20%~22% 营收", "role": "高利润弹性：超大型露天矿卡与地下采矿机械，直接挂钩全球铜金矿资本开支。"},
                {"name": "能源与交通动力系统 (Energy & Transportation)", "ratio": "~30%~32% 营收", "role": "抗周期第二曲线：石油钻机柴油机、数据中心备用发电机组及机车动力。"},
                {"name": "卡特彼勒金融服务 (Cat Financial)", "ratio": "~6%~8% 营收", "role": "销售催化杠杆：为全球买家提供设备按揭贷款与经营租赁支持。"}
            ]
        },
        "industry": {
            "sector": "全球重型工程机械、矿山装备与工业动力设备 (Construction & Heavy Machinery)",
            "macro_backdrop": "【宏观经济与大宗商品超级周期研判】受益于美国万亿《跨党派基建法案》实物落地、全球能源转型下铜/锂等关键金属矿山扩产，以及 AI 数据中心对超大型备用柴油发电机组的饥渴采购，卡特彼勒正在享受罕见的‘跨周期结构性景气拉动’。",
            "tam": "全球重型工业与工程机械市场超 2,200 亿美元，伴随全球基建与能源转型保持稳步提升。",
            "lifecycle": {
                "current_stage": "成熟现金牛期 (Mature Cash Cow)",
                "stage_index": 2,
                "all_stages": [
                    {"name": "初创探索期", "desc": "履带拖拉机发明与一战战地支援"},
                    {"name": "全球扩张期", "desc": "二战后伴随全球重建建立独立经销商网络"},
                    {"name": "成熟现金牛期", "desc": "全球保有量统治、后市场零部件变现与强现金分红"},
                    {"name": "转型再成长期", "desc": "矿卡全面自动驾驶 (MineStar) 与氢能/电动工程机械迭代"},
                    {"name": "衰退防御期", "desc": "全球重资产基建彻底饱和与竞品低价替代"}
                ],
                "characteristics": "历经百年全球多轮经济周期洗礼，抗风险与供应链垂直整合能力极强，拥有极其深厚的品牌溢价与二手设备保值率。",
                "is_good_or_bad": {
                    "pros": "好在经销商网络壁垒无可复制，且后市场服务经常性收入占比超 30%，自由现金流与资本回报率 (ROIC 25%+) 处于工业制造企业顶尖水平。",
                    "cons": "坏在重工业天然受到宏观利率与基建投资周期的脉冲式影响，若全球主要经济体陷入深度衰退，新机出货量可能面临周期性回落。"
                },
                "long_term_strategy": "适合周期价值与机械成长型投资者在采矿与基建周期启动阶段超配，在估值处于历史中枢下方时布局享受戴维斯双击。"
            },
            "competitors": [
                {
                    "symbol": "DE.US",
                    "name": "Deere & Company (迪尔股份)",
                    "threat": "中高",
                    "market_position": "全球农机绝对霸主，建筑机械领域主要挑战者",
                    "comparison": "在农业机械领域具有统治地位，精准农业软件领先，但在巨型露天矿卡与动力发电机组领域不及卡特。",
                    "bj_differentiation": "【卡特彼勒壁垒】全球重型矿山装备与跨国特许经销商服务体系无敌，超大型露天矿卡市场份额超 60%。"
                },
                {
                    "symbol": "6301.T",
                    "name": "Komatsu (小松制作所)",
                    "threat": "高",
                    "market_position": "全球第二大工程机械日本巨头",
                    "comparison": "拥有成熟的 KOMTRAX 远程监控系统，在亚洲与矿山机械领域技术底蕴深厚。",
                    "bj_differentiation": "【卡特彼勒壁垒】在北美成熟市场拥有压倒性品牌心智，且在北美二手设备残值率与转售流动性最高。"
                }
            ]
        },
        "products": [
            {
                "name": "Cat 核心建筑重型工程装备系列 (Excavators & Dozers)",
                "category": "重型机械设备制造 (Earthmoving Equipment)",
                "strategic_role": "营收主力与品牌图腾 (Core Equipment Anchor)",
                "revenue_ratio": "~41% 营收贡献",
                "gross_margin": "28%~32% 制造高毛利",
                "s_curve_stage": "全球经典工业标杆长青期",
                "switching_cost": "高 (机手操作习惯锁定、施工现场车队互联与二手高保值率)",
                "barrier_type": "极限制造工程品质 + 覆盖全球的 160+ 独立独家经销商网络",
                "barrier_detail": "一台卡特大型挖掘机即使在极寒与沙漠环境下连续作业数千小时依然具备极高出勤率；遍布全球的独立经销商承诺‘24 小时内送达任何急需配件’，确保施工不延期。",
                "market_share": "全美工程机械第一，全球市占率领先",
                "business_model": "通过独家经销商批发销售新机，并通过按揭租赁促进去化。",
                "prospect_and_catalysts": "美国联邦基础设施与就业法案资金持续拨付形成刚性采购排单。"
            },
            {
                "name": "Cat 原厂专用零部件与后市场全生命周期服务 (Services & Parts)",
                "category": "高毛利后市场运维与数字化 (Aftermarket Services)",
                "strategic_role": "高毛利利润奶牛与周期平滑器 (Margin Expansion & Cyclical Buffer)",
                "revenue_ratio": "~30% 营收但贡献超 45% 营业利润",
                "gross_margin": "45%~50% 纯零部件极高毛利",
                "s_curve_stage": "联网设备数字化增厚期",
                "switching_cost": "极高 (非原厂配件将失去质保并承担高昂停机停产损失风险)",
                "barrier_type": "物理装机保有量垄断 + 专有零件公差与专利绑定",
                "barrier_detail": "全球超过 150 万台联网设备将实时工况数据传回云端，提前预警零部件磨损并在计划保养期自动派发原厂配件；矿山重卡停工一小时损失数万美元，客户绝不敢使用廉价副厂件。",
                "market_share": "卡特原厂保有量配件份额绝对统治",
                "business_model": "高频易损件更换、核心发动机再制造 (Cat Reman) 与年度维保服务合同。",
                "prospect_and_catalysts": "后市场经常性服务收入复合年增长率达双位数，持续降低全公司周期波动。"
            }
        ],
        "supply_chain": {
            "upstream_dependency": "主要采购特殊高强度特种合金钢材、大型液压铸锻件及动力总成零部件；具备自研自产核心柴油机与传动系统能力。",
            "downstream_concentration": "直面全球多元矿业巨头 (如 BHP, Rio Tinto)、跨国工程承包商及租赁公司，客户高度分散。",
            "spof_bottlenecks": [
                {
                    "node": "高品质大型特种钢铸件与特种工程轮胎供应链产能波动",
                    "threat_level": "中",
                    "impact": "大型矿用巨型轮胎 (如 63 英寸特种轮胎) 偶发短缺可能阶段性拉长超重型矿卡整车交付周期。"
                },
                {
                    "node": "全球利率与矿产大宗商品价格深幅回调",
                    "threat_level": "中高",
                    "impact": "若大宗商品价格暴跌导致矿企削减 CapEx，客户新设备采购决策周期将显著拉长。"
                }
            ],
            "customer_bargaining": {
                "top_customers_share": "客户分散度极高，无任何单一矿企或建筑公司能主导设备定价；",
                "in_house_threat": "任何工程公司绝无可能自行研发重型挖掘机或矿卡；",
                "pricing_power": "由于无可替代的二手保值率与低停机率，卡特彼勒具备极强自主定价权与抗通胀传导力。"
            },
            "geopolitical_and_resilience": "制造工厂与供应链分散布局于美国、欧洲、拉美和亚太地区，资产负债表拥有极强投资级信用评级，抗金融动荡能力极强。"
        }
    },
    "UNP.US": {
        "essence": {
            "summary": "北美一级干线铁路运输与陆路物流动脉绝对垄断者：手握贯通美西与中西部的独家铁轨路权资产，以几乎不可复制的重资产物理网络构筑终极地理特许垄断。",
            "profit_engine": "【底层盈利真相】联合太平洋铁路不是普通的卡车运输公司，而是一家‘拥有不可复制的私有铁路物理路权、按吨英里收费的陆运特许基础设施垄断巨头’。在现代美国，任何人都绝不可能重新征地、审批并铺设一条平行的新干线铁路网络（征地成本与环保审批堪称天文数字）。UNP 与伯克希尔哈撒韦旗下的 BNSF 构成了美西横跨二十余个州的双寡头垄断，长距离大宗物资（谷物、煤炭、化工品、海运集装箱）的单位重量运输成本仅为公路卡车的四分之一，拥有无与伦比的能耗经济性与定价权。",
            "flywheel": "垄断美西 32,000 英里核心铁路走廊与美墨边境所有口岸 ➔ 享受跨洲大宗长途货运最低吨公里成本 ➔ 锁定跨国化工、粮食、汽车及零售巨头数年排他性运力合同 ➔ 实施精准定期铁路运营 (PSR) 持续压降营业费用率 (Operating Ratio) ➔ 产生天量自由现金流进行股票回购与分红 ➔ 进一步拉高重置成本壁垒。",
            "segments": [
                {"name": "工业特种品与能源化工运输 (Industrial)", "ratio": "~34%~36% 营收", "role": "高毛利核心支柱：塑料、原油、精炼化学品及建筑建材，运价高且粘性强。"},
                {"name": "超大散装大宗品与农业粮食 (Bulk)", "ratio": "~32%~34% 营收", "role": "刚需运输压舱石：美国中西部粮食谷物、化肥、饲料与煤炭，抗宏观周期。"},
                {"name": "海铁联运多式集装箱与整车 (Premium/Intermodal)", "ratio": "~30%~32% 营收", "role": "消费与贸易风向标：国际海运集装箱内陆分拨与底特律汽车整车运输。"}
            ]
        },
        "industry": {
            "sector": "北美一级铁路干线、多式联运与基础设施运输 (Class I Railroads & Freight Logistics)",
            "macro_backdrop": "【宏观经济与近岸外包研判】受益于美墨加协定 (USMCA) 推动的墨西哥制造业‘近岸外包 (Nearshoring)’爆发，UNP 是全美唯一一家连接所有 6 个美墨主要铁路过境口岸的一级铁路，墨西哥对美工业品出口为其提供了坚实的长期增量；同时铁路能耗与碳排放仅为卡车的 25%，深度受益于大型企业绿色 ESG 供应链采购导向。",
            "tam": "北美一级干线铁路货运市场超 900 亿美元，牢牢占据全美内陆大宗货运周转量近 40%。",
            "lifecycle": {
                "current_stage": "成熟现金牛期 (Mature Cash Cow)",
                "stage_index": 2,
                "all_stages": [
                    {"name": "初创修路期", "desc": "1862 年林肯总统签署法案修建第一条跨美大陆铁路"},
                    {"name": "并购成网期", "desc": "整合密苏里太平洋与南方太平洋铁路奠定西部霸主"},
                    {"name": "成熟现金牛期", "desc": "双寡头垄断、实施 PSR 压缩营业比率与极高资本回报"},
                    {"name": "绿色智能化再成长期", "desc": "自动化调度调车场与替代能源内燃机车迭代"},
                    {"name": "衰退防御期", "desc": "内陆大宗工业需求萎缩与管道/自主货运卡车颠覆"}
                ],
                "characteristics": "业务历经 160 余年沧桑变迁，资产重置成本近乎无穷大，营业利润率常年维持在 38%~40% 的极高水平，资本配置极其慷慨（自由现金流近 100% 用于分红与回购）。",
                "is_good_or_bad": {
                    "pros": "好在私有路权具备绝对物理排他性，大宗货物运输无平替方案，长途重载运输成本相比公路有压倒性优势。",
                    "cons": "坏在铁路工人工会劳工协议谈判每隔几年会带来罢工威胁或工资上涨压力，且运营比率 (OR) 进一步压缩的边际空间逐步收窄。"
                },
                "long_term_strategy": "适合主权财富基金与极度重视确定性复利的价值投资者作为百年核心资产配置，在宏观衰退引发货运量短期回落时逢低买入。"
            },
            "competitors": [
                {
                    "symbol": "BRK.B",
                    "name": "BNSF Railway (伯克希尔哈撒韦旗下)",
                    "threat": "高",
                    "market_position": "美西另一大铁路霸主 (与 UNP 瓜分美西干线)",
                    "comparison": "网络布局同样庞大，但隶属于伯克希尔非上市公司，考核更偏长线资本开支。",
                    "bj_differentiation": "【UNP 专有口岸与运营效率】独家独占所有 6 个美墨边境铁路大门，且精准定期铁路 (PSR) 考核使营业利润率常年领先 BNSF。"
                },
                {
                    "symbol": "CP.US",
                    "name": "Canadian Pacific Kansas City (CPKC)",
                    "threat": "中高",
                    "market_position": "横跨加拿大-美国-墨西哥的唯一纵贯南北单一铁路网",
                    "comparison": "拥有南北纵向直通墨西哥优势，但东西向横跨北美大陆货运能力与港口腹地远不及 UNP。",
                    "bj_differentiation": "【UNP 专有口岸与运营效率】掌控洛杉矶港与长滩港（全美第一大集装箱海运港群）向美国中西部的关键货运铁路大动脉。"
                }
            ]
        },
        "products": [
            {
                "name": "美西及美墨干线重载铁路特许货运网 (32,000 英里私有铁路网)",
                "category": "物理铁路干线运输服务 (Network Freight Rail)",
                "strategic_role": "绝对垄断资产与现金流护城河 (Monopoly Asset Anchor)",
                "revenue_ratio": "~100% 营收来源",
                "gross_margin": "38%~42% 极高营业利润率 (Operating Ratio ~60%)",
                "s_curve_stage": "百年成熟不可替代物理动脉",
                "switching_cost": "极高 (大宗散货改走卡车运费将暴涨 3~4 倍且运力根本无法承接)",
                "barrier_type": "不可复制的地理地役权 (Right-of-Way) + 极端重资产重置壁垒",
                "barrier_detail": "跨越 23 个州连接西海岸所有主要港口与芝加哥等核心枢纽；任何新企业重建这套路网所需资金与土地审批在现代社会已无任何可能。",
                "market_share": "美西干线铁路货运市占率超 50%",
                "business_model": "按货物重量与行驶里程 (吨英里) 收取基础运费，绑定燃料附加费自动调价条款。",
                "prospect_and_catalysts": "美墨近岸外包贸易量持续增长及自动化信号系统提升列车运行编组效率。"
            }
        ],
        "supply_chain": {
            "upstream_dependency": "主要采购重载柴油机车 (Wabtec / Progress Rail)、钢轨、枕木及柴油燃料；燃油成本可通过燃料附加费顺畅传导给货主。",
            "downstream_concentration": "直面全美数千家农业合作社、能源矿企、跨国化工集团与全球海运班轮公司，无单一客户依赖风险。",
            "spof_bottlenecks": [
                {
                    "node": "铁路工人工会劳资集体谈判与罢工法案审查",
                    "threat_level": "中高",
                    "impact": "若劳资谈判陷入僵局面临铁路罢工风险（通常由美国总统与国会紧急介入调停），调薪会温和增加人员营运开支。"
                },
                {
                    "node": "恶劣极端天气 (暴雪、洪水、泥石流) 导致的干线暂时阻断",
                    "threat_level": "中",
                    "impact": "可能导致特定铁路线路临时降速或绕行，短期轻微压制单季度周转率。"
                }
            ],
            "customer_bargaining": {
                "top_customers_share": "客户集中度极低，前十大货主占比低于 15%；",
                "in_house_threat": "货主无法自建跨州铁路，必须依赖双寡头之一承运；",
                "pricing_power": "由于无可替代的成本优势，UNP 享有强劲的合同自主提价权，长期跑赢美国 CPI。"
            },
            "geopolitical_and_resilience": "全部资产扎根美国内陆核心基础设施，资产负债表极度健康，是穿越一切经济风暴的顶级国宝级资产。"
        }
    },
    "MCD.US": {
        "essence": {
            "summary": "全球快餐连锁传奇与商业地产特许经营帝国：以极致标准化的汉堡炸鸡构筑高频大众消费心智，以优质黄金地段商业地产所有权与特许加盟抽成变现永续复利。",
            "profit_engine": "【底层盈利真相】麦当劳本质上不是一家自己卖汉堡的餐厅，而是一家‘拥有全球核心地段商业地产、并向加盟商收取双重特许租金的资产管理巨头’。全球超过 95% 的麦当劳门店为加盟店，麦当劳买下或长期承租几乎所有核心店址的土地与建筑物，加盟商不仅必须向总部支付基于销售额的特许加盟权使用费 (Royalty Fees, ~4%~5%)，更必须向麦当劳总部支付高额的‘场地租金’ (Rent Fees, 通常为销售额的 8%~15% 或最低保底租金)。加盟业务毛利率高达 80%~85%，将通胀与餐厅人工食品成本全部转嫁给加盟商，总部坐收旱涝保收的纯现金流。",
            "flywheel": "全球最强快餐品牌知名度 ➔ 天量顾客高频进店消费 ➔ 吸引全球最优秀的加盟商投入资本开店 ➔ 麦当劳总部挑选并掌控黄金地段地产产权 ➔ 向加盟商稳定收取与通胀联动的租金与特许权使用费 ➔ 产生充沛现金流投入全球品牌营销与数字化 App ➔ 进一步巩固单店坪效第一地位。",
            "segments": [
                {"name": "特许加盟门店租金与特许权收益 (Franchised Revenues)", "ratio": "~60%~62% 营收", "role": "绝对利润印钞机：毛利率超 82%，贡献全公司近 90% 营业利润。"},
                {"name": "直营示范餐厅销售收入 (Company-operated Sales)", "ratio": "~38%~40% 营收", "role": "运营标准试验田：保留极少比例直营店测试新菜单与自动化运营流程。"}
            ]
        },
        "industry": {
            "sector": "全球连锁快餐餐饮、特许经营与商业地产 (Fast Food Restaurants & Franchising)",
            "macro_backdrop": "【宏观经济与消费降级研判】在通胀高企与消费者钱包缩水时期，麦当劳拥有无可比拟的‘超值平价菜单 (Value Menu)’吸引力；从中产聚餐向下兼并大众日常刚需，历史上在多次经济衰退期同店销售额 (SSS) 逆势飘红，具备极强的逆周期防御护盾。",
            "tam": "全球快餐与大众休闲餐饮市场超 9,000 亿美元，连锁化率在发展中国家持续攀升。",
            "lifecycle": {
                "current_stage": "成熟现金牛期 (Mature Cash Cow)",
                "stage_index": 2,
                "all_stages": [
                    {"name": "初创标准化期", "desc": "麦当劳兄弟快餐厨房与雷·克洛克加盟扩张"},
                    {"name": "全球黄金期", "desc": "开拓地产租金模式并走向全球 100+ 国家"},
                    {"name": "成熟现金牛期", "desc": "轻资产重组至 95% 加盟、得来速 (Drive-thru) 普及与高分红"},
                    {"name": "数字化再成长期", "desc": "自营 App 会员忠诚度计划与智能点餐全面渗透"},
                    {"name": "衰退防御期", "desc": "健康饮食风潮彻底普及与垃圾食品标签冲击"}
                ],
                "characteristics": "业务遍布全球 40,000 余家餐厅，历经七十年品牌积累，资产负债表拥有数百亿美元核心商业地产公允价值，连续 48 年保持股息增长。",
                "is_good_or_bad": {
                    "pros": "好在商业模式轻资产化彻底，90% 利润来自免受通胀波动的加盟特许费与租金，抗宏观经济衰退韧性极佳。",
                    "cons": "坏在资产负债表由于长期大幅回购股票导致账面股东权益为负 (会计净资产为负但实际资产极其丰厚)，对全球利率长期高位再融资成本较为敏感。"
                },
                "long_term_strategy": "适合偏好稳定派息与防御型资产的长期投资者作为核心消费底仓，在估值回调至历史 PE 低分位时买入享受稳健复利。"
            },
            "competitors": [
                {
                    "symbol": "YUM.US",
                    "name": "百胜餐饮 (Yum! Brands: 肯德基/必胜客/塔可钟)",
                    "threat": "高",
                    "market_position": "全球多品牌特许餐饮巨头",
                    "comparison": "多品牌协同能力强，但直控核心商业地产的比例远低于麦当劳，租金收益护城河不及麦当劳。",
                    "bj_differentiation": "【麦当劳核心壁垒】拥有自持黄金商业地产所有权，单品牌全球日活客流量第一，得来速车道效率行业天花板。"
                },
                {
                    "symbol": "QSR.US",
                    "name": "餐饮品牌国际 (Restaurant Brands Intl: 汉堡王/Popeyes)",
                    "threat": "中高",
                    "market_position": "汉堡王与炸鸡连锁挑战者",
                    "comparison": "深耕美南与国际市场，但在全美单店销售额 (AUV) 与品牌心智上与麦当劳差距明显。",
                    "bj_differentiation": "【麦当劳核心壁垒】单店平均年销售额超 360 万美元，远高于汉堡王，加盟商投资回报率更高且资金实力雄厚。"
                }
            ]
        },
        "products": [
            {
                "name": "全球 40,000 家特许加盟商业地产与特许经营管理体系",
                "category": "商业地产租赁与品牌授权 (Real Estate & Franchising)",
                "strategic_role": "绝对利润支柱与现金流皇冠 (Crown Jewel)",
                "revenue_ratio": "~62% 营收贡献 (贡献近 90% 营业利润)",
                "gross_margin": "82%~85% 极高毛利率",
                "s_curve_stage": "全球极度成熟高效网络",
                "switching_cost": "极高 (加盟商投入数百万美元装潢与设备，绑定 20 年长期排他加盟协议)",
                "barrier_type": "不可复制的全球黄金地段地产产权 + 终极品牌心智",
                "barrier_detail": "麦当劳是全球最大的商业地产自持机构之一，在纽约、伦敦、东京等全球核心路口拥有独家产权；无论汉堡成本如何涨跌，加盟商都必须按月缴纳租金。",
                "market_share": "全球连锁快餐餐饮市场份额第一",
                "business_model": "按加盟店销售额固定百分比收取特许权使用费 + 商业地产租赁分成费。",
                "prospect_and_catalysts": "新一代‘CosMc’s’概念店探索与数字化会员点餐提升客单价。"
            }
        ],
        "supply_chain": {
            "upstream_dependency": "由独立第三方专用供应链伙伴 (如 Keystone, Martin-Brower) 负责牛肉、土豆、面包胚胎采购与配送，麦当劳总部不承担库存跌价风险。",
            "downstream_concentration": "直面全球每天数千万大众日常消费者，无任何单一客户集中度。",
            "spof_bottlenecks": [
                {
                    "node": "极端食品安全卫生与大肠杆菌感染突发偶发事件",
                    "threat_level": "中",
                    "impact": "若个别食材供应商污染导致食品安全丑闻，短期可能引发区域门店客流冲击（但历史证明通常在数周内修复）。"
                },
                {
                    "node": "大众低收入客群对快餐整体提价的抵触与价格弹性反弹",
                    "threat_level": "中",
                    "impact": "若连续提价过猛可能抑制部分底层客群进店频次，需适度加大超值 5 美元套餐引流力度。"
                }
            ],
            "customer_bargaining": {
                "top_customers_share": "消费者极度分散，日常小额快消；",
                "in_house_threat": "家庭自制汉堡费时费力，得来速 3 分钟即得性不可替代；",
                "pricing_power": "由于强劲的品牌忠诚度，在通胀周期中具备领先行业的自主平稳调价权。"
            },
            "geopolitical_and_resilience": "品牌渗透全球超百个国家，业务极度分散稳健，即使面对地缘冲突与区域危机，全球其他大区现金流也能提供强力支撑。"
        }
    },
    "ISRG.US": {
        "essence": {
            "summary": "全球软组织微创外科手术机器人绝对垄断者：以达芬奇 (da Vinci) 手术系统构筑极高装机壁垒，以‘高毛利耗材与单次手术配件’构建印钞机级的剃刀与刀片商业模式。",
            "profit_engine": "【底层盈利真相】直观外科绝非单纯靠卖几百万美元的达芬奇手术台为生的医疗器械厂商，而是一家‘拥有全球最高临床装机保有量、按手术台次消耗高毛利专有耗材的医疗垄断科技巨头’。全球顶尖外科医生必须在达芬奇模拟器上接受数百小时严格临床培训才能获得微创手术认证，形成终身极高的操作习惯锁定。更关键的是，其专有 EndoWrist 机械臂手术器械被设定为‘使用固定次数（如 10 次）后由芯片强制锁死报废’，单次手术必须消耗 $1,500~$3,000 美元的专用无菌耗材。其经常性收入（耗材 + 维保）占比超过 83%，毛利率近 70%，把医生的每一台手术转化为源源不断的高毛利现金流。",
            "flywheel": "顶尖 3D 高清视觉与防抖颤多自由度机械手腕 ➔ 培训认证全球数万名顶级外科专家 ➔ 医院斥巨资采购装机达芬奇系统 ➔ 医生推动更多病种手术使用达芬奇 ➔ 单机手术量激增推动天量专有耗材持续消耗 ➔ 产生丰沛可预测现金流 ➔ 投入下一代 da Vinci 5 触觉反馈与单孔手术研发 ➔ 持续构筑医疗准入与专利高墙。",
            "segments": [
                {"name": "专有手术耗材与配件 (Instruments & Accessories)", "ratio": "~60%~62% 营收", "role": "绝对纯利印钞机：高频消耗的 EndoWrist 机械腕与吻合器，毛利率极高。"},
                {"name": "系统装机与整机销售/租赁 (Systems)", "ratio": "~22%~24% 营收", "role": "未来耗材播种机：单台售价 150 万~250 万美元的新一代整机系统。"},
                {"name": "年度高可用维保与技术服务 (Services)", "ratio": "~15%~16% 营收", "role": "高粘性服务锁定：每台装机收取数万美元/年的专职工程师保障年费。"}
            ]
        },
        "industry": {
            "sector": "全球医疗器械、微创软组织手术机器人与耗材 (Robotic Surgical Systems & Medical Devices)",
            "macro_backdrop": "【宏观经济与老龄化研判】不受宏观加息与普通消费周期影响，全球人口老龄化加剧促使泌尿科、妇科、普通外科（疝气修复、结直肠、减重）手术量保持刚性高增长；微创手术相比传统开腹手术大幅降低患者住院天数与感染率，医院采购意愿极强。",
            "tam": "全球软组织与腔镜手术机器人市场预计 2030 年超 200 亿美元，达芬奇在软组织微创领域市占率超 80%。",
            "lifecycle": {
                "current_stage": "高速成长期 (Rapid Growth)",
                "stage_index": 1,
                "all_stages": [
                    {"name": "初创破局期", "desc": "DARPA 战地远程手术研发与前列腺癌手术切入"},
                    {"name": "适应症爆发期", "desc": "全面拓展妇科、疝气修补与结直肠普通外科"},
                    {"name": "全球高速成长期", "desc": "da Vinci 5 推出、耗材经常性收入破 80% 与国际化放量"},
                    {"name": "成熟现金牛期", "desc": "全球三甲医院装机渗透饱和、平稳收取耗材年金"},
                    {"name": "衰退防御期", "desc": "核心专利群完全到期与廉价国产机器人平替"}
                ],
                "characteristics": "业务模式处于极佳的高速增长主升浪，全球装机超 9,000 台，年手术量超 220 万台，兼具科技成长股的高增速与高壁垒医疗器械的高确定性。",
                "is_good_or_bad": {
                    "pros": "好在商业模式拥有全球顶尖的剃刀与刀片经常性收入结构，资产负债表零负债且手握数十亿美元现金，医生习惯迁移阻力近乎无限大。",
                    "cons": "坏在估值市盈率长期处于 55x~65x 极高估值区间，对单季度全球手术量增速由于极端天气或公共卫生事件导致的暂时放缓极度敏感。"
                },
                "long_term_strategy": "适合高质量成长型医疗科技投资者在每一次市场系统性回调或医疗设备招标偶发递延时坚定买入作为长线核心底仓。"
            },
            "competitors": [
                {
                    "symbol": "MDT.US",
                    "name": "Medtronic (美敦力: Hugo 机器人系统)",
                    "threat": "中",
                    "market_position": "全球传统医疗器械霸主",
                    "comparison": "拥有成熟的手术器械分销渠道，Hugo 正在欧洲扩展装机，但在复杂临床数据沉淀与医生培训壁垒上远落后于达芬奇。",
                    "bj_differentiation": "【直观外科压倒性壁垒】25 年临床数据积累与超 1,400 万台累计临床手术验证，顶尖外科医生肌肉记忆完全绑定达芬奇系统。"
                },
                {
                    "symbol": "JNJ.US",
                    "name": "Johnson & Johnson (强生: Ottava 机器人项目)",
                    "threat": "中",
                    "market_position": "全球医疗健康与外科手术巨无霸",
                    "comparison": "研发预算雄厚，但手术机器人项目屡次推迟，距离大规模商业化装机仍需数年时间。",
                    "bj_differentiation": "【直观外科压倒性壁垒】下一代 da Vinci 5 系统具备独家力反馈技术与 10,000 倍计算能力提升，代际优势持续拉大。"
                }
            ]
        },
        "products": [
            {
                "name": "达芬奇 EndoWrist 专用手术器械与一次性配件 (Instruments & Accessories)",
                "category": "高毛利核心医疗耗材 (Consumables Razor Blades)",
                "strategic_role": "绝对利润源泉与经常性现金牛 (Core Profit Engine)",
                "revenue_ratio": "~61% 营收贡献",
                "gross_margin": "72%~75% 极高毛利",
                "s_curve_stage": "手术量持续爆发的高斜率主升浪",
                "switching_cost": "近乎绝对锁定 (第三方器械无法通过达芬奇系统的射频 RFID 芯片安全认证)",
                "barrier_type": "严苛 FDA 临床准入认证 + 专有机械芯片加密与专利高墙",
                "barrier_detail": "包括微型手术剪、双极电凝钳、吻合器及缝线器；机械手腕具备 7 个自由度与比人手更小的震颤控制，每次手术消耗数件，使用寿命由芯片强制倒计时归零。",
                "market_share": "全球腔镜手术机器人专用耗材绝对垄断",
                "business_model": "按支销售，医院根据每日手术排期高频重复采购。",
                "prospect_and_catalysts": "普通外科（腹股沟疝、胆囊切除、结直肠）年手术量渗透率持续超预期增长。"
            },
            {
                "name": "da Vinci 5 (第五代) 旗舰多孔手术机器人系统",
                "category": "高端医疗装备制造 (Advanced Surgical System Platform)",
                "strategic_role": "技术壁垒与耗材播种机 (Platform Moat Anchor)",
                "revenue_ratio": "~23% 营收贡献",
                "gross_margin": "65%~68% 高毛利",
                "s_curve_stage": "代际换代与全球三甲医院全面升级期",
                "switching_cost": "极高 (单台造价数百万美元，医院采购经过极严谨的管委会论证)",
                "barrier_type": "颠覆性力反馈传感工程 (Force Sensing) + 3D 4K 超高清内窥镜集成",
                "barrier_detail": "不仅消除手部微震颤，更是全球首款让主刀医生‘在手指手柄上真实感知缝合组织张力与硬度’的商用系统，手术精细度大幅跃升，竞品无任何同类产品可匹敌。",
                "market_share": "高端腔镜手术机器人全球第一",
                "business_model": "直销、融资租赁 (Lease) 与按手术量浮动计费多元商业模式。",
                "prospect_and_catalysts": "新系统在全美和欧洲顶级教学医院替代老旧 Xi 系统的换机潮全面启动。"
            }
        ],
        "supply_chain": {
            "upstream_dependency": "主要采购医用特种不锈钢合金、精密微型伺服电机 (瑞士 Maxon 等)、光纤高清传感镜头及专有芯片；具备多源采购与严格质量认证体系。",
            "downstream_concentration": "直面全球数千家顶级公立大学医院、私立医疗集团与区域医疗中心，客户信用评级极高，坏账率接近于零。",
            "spof_bottlenecks": [
                {
                    "node": "医院资本开支预算受宏观信贷或医保报销政策调整的暂时紧缩",
                    "threat_level": "中",
                    "impact": "可能导致个别医院延后整机全款采购时间，但直观外科通过提供经营性租赁模式有效化解了预算门槛。"
                },
                {
                    "node": "专利池部分早期基础机械结构专利逐步到期",
                    "threat_level": "低中",
                    "impact": "直观外科通过数十层重叠的外观、软件控制算法、芯片加密与第五代力反馈新专利构筑了持续保护圈。"
                }
            ],
            "customer_bargaining": {
                "top_customers_share": "单一医院客户占比极低，无任何采购方具备实质压价权；",
                "in_house_threat": "医院无法自行研发医疗机器人，替代成本涉及人命安全与医疗事故法律风险；",
                "pricing_power": "无可替代的临床疗效使得达芬奇系统与耗材具备极高自主定价权与抗通胀转移能力。"
            },
            "geopolitical_and_resilience": "研发与核心制造立足于美国本土，资产负债表极度纯净，无任何长期有息负债，拥有超 80 亿美元现金等价物，抗风险底座坚如磐石。"
        }
    }

}


def infer_dynamic_institutional_dossier(symbol: str, company: Optional[Dict[str, Any]], financials: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Intelligent sector inference and structured 5-stage lifecycle generation for long-tail stocks.
    Never falls back to exchange name or placeholder '同行业龙头企业'.
    """
    sym = symbol.upper()
    cname = (company or {}).get("name") or (company or {}).get("company_name") or sym
    profile_text = (company or {}).get("profile") or ""
    txt = (profile_text + " " + cname).lower()

    # 1. Broad Sector recognition & Real Peer Mapping (Never falls back to exchange name)
    sector = "美股全球化行业核心领军企业 (Global Core Industry Leader)"
    competitors = []
    
    if any(k in txt for k in ["仓储", "会员", "批发", "club", "warehouse", "wholesale"]):
        sector = "会员制仓储零售与平价折扣超市 (Warehouse Clubs & Discount Retail)"
        competitors = [
            {"symbol": "COST.US", "name": "Costco (开市客)", "threat": "极高", "market_position": "全球会员仓储店绝对霸主，规模与自营品牌号召力无敌", "comparison": "极致精选 SKU，全球集采议价权最强。", "bj_differentiation": "【差异化突围】提供更多知名品牌 SKU 与中等包装，距离社区生活半径更亲民。"},
            {"symbol": "WMT.US", "name": "Sam's Club (山姆会员店)", "threat": "高", "market_position": "背靠沃尔玛全球供应链与数字化即时配送", "comparison": "全国性网络庞大，数字化体验领先。", "bj_differentiation": "【差异化突围】深耕特定核心区域社区网络，客户忠诚度与网点密度高。"},
            {"symbol": "TGT.US", "name": "Target (塔吉特)", "threat": "中", "market_position": "大众平价百货大卖场", "comparison": "非会员制分流中产零散杂货开支。", "bj_differentiation": "【差异化突围】大包装具备 20%+ 价格折扣优势，抗通胀平替感知强。"}
        ]
    elif any(k in txt for k in ["芯片", "半导体", "集成电路", "semiconductor", "chip", "gpu", "cpu", "wafer"]):
        sector = "半导体核心芯片与硬科技硬件 (Semiconductor & Advanced Hardware)"
        competitors = [
            {"symbol": "NVDA.US", "name": "NVIDIA (英伟达)", "threat": "极高", "market_position": "全球 AI 算力与 GPU 全栈生态绝对霸主", "comparison": "CUDA 开发者粘性与软硬协同系统无敌。", "bj_differentiation": "【差异化突围】在特定细分制程、特定架构或高性价比二供方案中寻求突破。"},
            {"symbol": "AMD.US", "name": "AMD (超威半导体)", "threat": "高", "market_position": "全球高性能 CPU/GPU 核心创新者", "comparison": "多产品线成熟，深度卡位云厂商供应链。", "bj_differentiation": "【差异化突围】聚焦专用细分场景或自研定制化芯片。"},
            {"symbol": "TSM.US", "name": "TSMC (台积电)", "threat": "中", "market_position": "全球先进制程晶圆代工制造底座", "comparison": "掌控先进制程关键产能。", "bj_differentiation": "【差异化突围】专注于设计端知识产权 (IP) 与算法绑定。"}
        ]
    elif any(k in txt for k in ["软件", "云", "saas", "software", "cloud", "ai", "人工智能", "database"]):
        sector = "企业级软件 SaaS、云基础设施与商用 AI (Enterprise Software & Cloud)"
        competitors = [
            {"symbol": "MSFT.US", "name": "Microsoft (微软)", "threat": "高", "market_position": "企业数字化与大模型 Copilot 平台巨无霸", "comparison": "桌面与云协同垄断，分销网络全球最密。", "bj_differentiation": "【差异化突围】在垂直工作流、细分垂直领域数据深度与灵活性上构建壁垒。"},
            {"symbol": "ORCL.US", "name": "Oracle (甲骨文)", "threat": "中", "market_position": "企业核心数据库与算力云基础设施", "comparison": "大型政企关键任务负载极深锁定。", "bj_differentiation": "【差异化突围】新一代云原生架构更轻量，客户接入摩擦成本更低。"},
            {"symbol": "CRM.US", "name": "Salesforce (赛富时)", "threat": "中", "market_position": "全球 CRM 与企业业务流自动化领军者", "comparison": "企业客户关系管理事实标准。", "bj_differentiation": "【差异化突围】通过差异化定价模型与生成式 AI 原生工作流切入存量市场。"}
        ]
    elif any(k in txt for k in ["汽车", "电动车", "auto", "car", "ev", "vehicle"]):
        sector = "智能电动汽车与未来出行 (Smart Electric Vehicles & Mobility)"
        competitors = [
            {"symbol": "TSLA.US", "name": "Tesla (特斯拉)", "threat": "极高", "market_position": "全球纯电动汽车与端到端 FSD 技术标杆", "comparison": "制造成本与全自动驾驶数据飞轮领先。", "bj_differentiation": "【差异化突围】主打差异化细分车身造型、豪华质感或特定区域本土化服务优势。"},
            {"symbol": "1211.HK", "name": "BYD (比亚迪)", "threat": "高", "market_position": "全球新能源汽车全产业链垂直整合冠军", "comparison": "电池与零部件垂直一体化成本极致。", "bj_differentiation": "【差异化突围】专注欧美高端成熟市场品牌心智塑造。"}
        ]
    elif any(k in txt for k in ["零售", "电商", "超市", "retail", "ecommerce", "store"]):
        sector = "全渠道消费零售与商业网络 (Omnichannel Retail & Commerce)"
        competitors = [
            {"symbol": "AMZN.US", "name": "Amazon (亚马逊)", "threat": "极高", "market_position": "全球电商与云履约基础设施绝对霸主", "comparison": "Prime 会员生态与极速物流次日达。", "bj_differentiation": "【差异化突围】依托实体门店提供即时体验、线下即提与特定品类专业服务。"},
            {"symbol": "WMT.US", "name": "Walmart (沃尔玛)", "threat": "高", "market_position": "全球线下零售航空母舰", "comparison": "供应链规模与门店数量全球第一。", "bj_differentiation": "【差异化突围】精细化特色商品选品与差异化客群体验。"}
        ]
    elif any(k in txt for k in ["生物", "医药", "制药", "pharma", "biotech", "drug", "healthcare"]):
        sector = "生物制药与现代生命健康 (Biopharmaceuticals & Healthcare)"
        competitors = [
            {"symbol": "LLY.US", "name": "Eli Lilly (礼来)", "threat": "高", "market_position": "全球 GLP-1 与代谢重磅药领导者", "comparison": "研发管线深厚，商业化放量强劲。", "bj_differentiation": "【差异化突围】布局具有专利壁垒的独家靶点或差异化适应症组合。"},
            {"symbol": "NVO.US", "name": "Novo Nordisk (诺和诺德)", "threat": "高", "market_position": "减重与降糖疗法全球先锋", "comparison": "多肽药物产能与全球学术推广占优。", "bj_differentiation": "【差异化突围】在递送技术或长效化改良上寻求后发优势。"}
        ]
    elif any(k in txt for k in ["机械", "工程机械", "重工", "制造", "拖拉机", "收割机", "农机", "林业", "machinery", "industrial", "equipment", "caterpillar", "deere"]):
        sector = "全球重型工程机械、农机装备与工业动力制造 (Heavy Industrial Machinery & Equipment)"
        competitors = [
            {"symbol": "CAT.US", "name": "Caterpillar (卡特彼勒)", "threat": "极高", "market_position": "全球矿山与工程机械黄牌霸主", "comparison": "独立独家经销商体系与后市场零部件服务护城河极深。", "bj_differentiation": "【差异化突围】在特定轻型农林场景、电动化微挖或细分特种工况设备寻求突破。"},
            {"symbol": "DE.US", "name": "Deere & Company (迪尔股份)", "threat": "高", "market_position": "全球智慧农机与重卡制造龙头", "comparison": "绿色精准农业软件算法与农机高粘性生态垄断。", "bj_differentiation": "【差异化突围】深耕非农基建机械或特种市政养护工程专用车辆。"}
        ]
    elif any(k in txt for k in ["固废", "环保", "垃圾", "水务", "公用事业", "waste", "utility", "recycling", "environmental"]):
        sector = "固废环保治理、危险废弃物处置与特许公用事业 (Waste & Environmental Services)"
        competitors = [
            {"symbol": "WM.US", "name": "Waste Management (废品管理)", "threat": "极高", "market_position": "全美不可再生垃圾填埋场与市政清运绝对霸主", "comparison": "填埋场资源不可复制，CPI 联动提价权极强。", "bj_differentiation": "【差异化突围】聚焦区域特许清运高密度路线或危废专有处置细分资质。"},
            {"symbol": "RSG.US", "name": "Republic Services", "threat": "高", "market_position": "北美固废第二大巨头，双寡头垄断者", "comparison": "网络庞大，数字化车队管理领先。", "bj_differentiation": "【差异化突围】深耕特定细分危废回收或可再生能源转化。"}
        ]
    elif any(k in txt for k in ["铁路", "轨道", "货运", "物流", "运输", "rail", "freight", "transport", "logistics"]):
        sector = "干线铁路大宗运输、多式联运与国家级物流基础设施 (Freight Rail & Logistics)"
        competitors = [
            {"symbol": "UNP.US", "name": "Union Pacific (联合太平洋)", "threat": "极高", "market_position": "美西干线铁路地役权私有垄断霸主", "comparison": "独占所有美墨过境口岸，重载吨公里成本无敌。", "bj_differentiation": "【差异化突围】提供区域短途毛细铁路接驳或高附加值冷链拼箱专业服务。"},
            {"symbol": "CSX.US", "name": "CSX 铁路", "threat": "高", "market_position": "美东干线铁路核心承运人", "comparison": "深耕美东工业走廊与大西洋沿岸港口腹地。", "bj_differentiation": "【差异化突围】避开大宗干线直接竞争，专注特定枢纽港站综合仓配联运。"}
        ]
    elif any(k in txt for k in ["支付通道", "清算网络", "信用卡", "商业银行", "金融科技", "payment gateway", "fintech", "credit card", "banking"]):
        sector = "全球数字支付与金融科技基础设施 (Digital Payments & Financial Services)"
        competitors = [
            {"symbol": "V.US", "name": "Visa", "threat": "极高", "market_position": "全球清算与双寡头支付通道霸主", "comparison": "拥有全球最庞大的持卡人与商户收单双边网络。", "bj_differentiation": "【差异化突围】在跨境小额支付、新兴嵌入式金融或先买后付 (BNPL) 领域差异化渗透。"},
            {"symbol": "MA.US", "name": "Mastercard (万事达卡)", "threat": "高", "market_position": "全球清算网络二当家", "comparison": "全球认可度极高，增值服务占比稳步提升。", "bj_differentiation": "【差异化突围】提供更灵活的企业端 API 接口与定制化数字钱包支持。"}
        ]
    elif any(k in txt for k in ["涂料", "油漆", "建材", "化学品", "coating", "paint", "building materials"]):
        sector = "建筑特种涂料、家装化学建材与专业专卖店分销 (Specialty Coatings & Materials)"
        competitors = [
            {"symbol": "SHW.US", "name": "Sherwin-Williams (宣伟涂料)", "threat": "极高", "market_position": "北美专业涂料与直营专卖店绝对霸主", "comparison": "全美近 5,000 家直营门店牢牢绑定专业油漆承包商。", "bj_differentiation": "【差异化突围】深耕特定工业防腐、汽车修补漆或大众零售大卖场批发渠道。"},
            {"symbol": "PPG.US", "name": "PPG 工业", "threat": "高", "market_position": "全球工业涂料与航空航天特种涂层龙头", "comparison": "工业应用与汽车 OEM 涂料技术积累深厚。", "bj_differentiation": "【差异化突围】强化民用住宅建筑与商业物业重涂的高频现金流。"}
        ]
    elif any(k in txt for k in ["家居", "家装", "五金", "home improvement", "hardware"]):
        sector = "全美家居建材改善、专业工程承包与仓储零售 (Home Improvement Retail)"
        competitors = [
            {"symbol": "HD.US", "name": "Home Depot (家得宝)", "threat": "极高", "market_position": "北美专业建筑承包商与家装零售绝对一哥", "comparison": "Pro 客户黏性强，单店坪效与供应链周转无敌。", "bj_differentiation": "【差异化突围】聚焦大众 DIY 个人家庭装饰与特定园艺细分需求。"},
            {"symbol": "LOW.US", "name": "Lowe's (劳氏)", "threat": "高", "market_position": "北美第二大家居建材零售巨头", "comparison": "在 DIY 个人消费者心智中认知度极高。", "bj_differentiation": "【差异化突围】抢占大型复杂工程订单的高壁垒配送交付。"}
        ]
    elif any(k in txt for k in ["工业气体", "空分", "气体", "linde", "industrial gas"]):
        sector = "全球特种工业气体、现场管道供气与尖端材料 (Industrial Gases & Engineering)"
        competitors = [
            {"symbol": "LIN.US", "name": "Linde (林德气体)", "threat": "极高", "market_position": "全球工业气体绝对霸主，现场管网照付不议合同壁垒", "comparison": "15~20 年长期 Take-or-Pay 锁定客户现金流，定价权无敌。", "bj_differentiation": "【差异化突围】聚焦特定高纯电子特气、氢能绿色能源或区域槽车分销。"},
            {"symbol": "APD.US", "name": "Air Products (空气化工)", "threat": "高", "market_position": "全球大型氢能与特种工业气体领军者", "comparison": "巨型能源项目工程能力突出。", "bj_differentiation": "【差异化突围】深耕电子芯片制造与高端医疗用气高毛利长协。"}
        ]
    elif any(k in txt for k in ["餐饮", "快餐", "连锁", "餐厅", "restaurant", "food", "dining", "fast food"]):
        sector = "全球连锁快餐餐饮、商业地产与特许经营管理 (Fast Food & Restaurant Franchising)"
        competitors = [
            {"symbol": "MCD.US", "name": "McDonald's (麦当劳)", "threat": "极高", "market_position": "商业地产自持与快餐特许经营全球霸主", "comparison": "得来速车道效率与黄金地段自持租金模式不可撼动。", "bj_differentiation": "【差异化突围】主打特定异域风味、健康有机食材定制或更高客单价休闲正餐场景。"},
            {"symbol": "YUM.US", "name": "Yum! Brands (百胜餐饮)", "threat": "高", "market_position": "多品牌快餐巨头 (肯德基/必胜客/塔可钟)", "comparison": "品类多元互补，国际市场渗透极深。", "bj_differentiation": "【差异化突围】聚焦单一核心单品的极致打磨与年轻潮流社群运营。"}
        ]
    elif any(k in txt for k in ["医疗器械", "手术", "机器人", "器械", "surgical", "medical device", "robotic"]):
        sector = "微创外科手术系统、医疗器械与专有耗材 (Robotic Surgery & Medical Devices)"
        competitors = [
            {"symbol": "ISRG.US", "name": "Intuitive Surgical (直观外科)", "threat": "极高", "market_position": "达芬奇微创手术机器人与专有耗材垄断者", "comparison": "全球软组织微创手术事实标准，耗材剃刀刀片模式极度吸金。", "bj_differentiation": "【差异化突围】布局骨科、血管介入或经皮穿刺等达芬奇尚未垄断的细分手术专科。"},
            {"symbol": "MDT.US", "name": "Medtronic (美敦力)", "threat": "高", "market_position": "全球全品类医疗器械航母", "comparison": "心血管、神经与外科产品线全球最全。", "bj_differentiation": "【差异化突围】在单一前沿细分术式上打造代际领先的专科专用器械。"}
        ]
    elif any(k in txt for k in ["石油", "天然气", "能源", "炼化", "油气", "oil", "gas", "energy", "petroleum"]):
        sector = "传统综合石油天然气、上游勘探与下游炼化一体化 (Integrated Oil & Gas)"
        competitors = [
            {"symbol": "XOM.US", "name": "ExxonMobil (埃克森美孚)", "threat": "极高", "market_position": "西方最大综合石油公司，深水与页岩低成本开采一哥", "comparison": "一体化炼化抗周期能力与巨额自由现金流回购极强。", "bj_differentiation": "【差异化突围】聚焦纯上游低成本优质区块开发或轻资产中游储运管网。"},
            {"symbol": "CVX.US", "name": "Chevron (雪佛龙)", "threat": "高", "market_position": "全美第二大石油巨头", "comparison": "二叠纪盆地页岩油资产优质，资产负债表极稳健。", "bj_differentiation": "【差异化突围】灵活利用衍生品对冲锁价，保持更高股息分红弹性。"}
        ]

    else:
        sector = "未从公司简介归类"

    # 上面的关键词同业名单是模板，没有核对过，页面不把它们当成事实。
    competitors = []

    rev_growth = None
    if financials and financials.get("indicators"):
        for ind in financials["indicators"]:
            field_name = (ind.get("name") or ind.get("field") or "").lower()
            if any(k in field_name for k in ["营业收入", "营收", "revenue", "operating_revenue"]):
                yoy_val = ind.get("yoy")
                if yoy_val is not None:
                    try:
                        rev_growth = float(yoy_val)
                        break
                    except Exception:
                        pass

    limit_text = "未取得现金流、分部毛利与多期序列，不据此判断经营质量。"
    if rev_growth is None:
        yoy_text = "长桥单期快照未披露营收同比。"
        current_stage_name = "生命周期未定（未披露营收同比）"
    else:
        g_pct = rev_growth * 100.0 if abs(rev_growth) <= 5.0 else rev_growth
        yoy_text = f"长桥单期快照营收同比 {g_pct:+.1f}%。"
        current_stage_name = f"营收同比 {g_pct:+.1f}%"

    summary = ""
    cleaned_profile = (profile_text or "").strip()
    if cleaned_profile:
        for sep in ("。", "."):
            if sep in cleaned_profile:
                head = cleaned_profile.split(sep, 1)[0].strip()
                if head:
                    summary = head + sep
                    break
        if not summary:
            summary = cleaned_profile
    if not summary:
        summary = "长桥未返回公司简介"

    essence_obj = {
        "summary": summary,
        "profit_engine": "",
        "flywheel": "",
        "segments": [],
        "source_tag": "长桥官方客观资料 · 未取得分部财务审计",
    }

    lifecycle_obj = {
        "current_stage": current_stage_name,
        "stage_index": None,
        "all_stages": [],
        "characteristics": f"{yoy_text}{limit_text}",
        "is_good_or_bad": {
            "pros": yoy_text,
            "cons": limit_text,
        },
        "long_term_strategy": "单期快照不足以给出配置建议。",
    }

    desc_clean = cleaned_profile
    if len(desc_clean) > 300:
        desc_clean = desc_clean[:300] + "..."

    products = [
        {
            "name": f"{cname} 官方公开主营描述",
            "category": "公开披露主营",
            "strategic_role": "未做人工笔记",
            "revenue_ratio": "未披露分项拆解 (单期接口未包含分部报告)",
            "gross_margin": "未取得 (长桥单期未单独披露分部毛利)",
            "s_curve_stage": current_stage_name,
            "switching_cost": "未做人工笔记整理",
            "barrier_type": "未做人工笔记",
            "barrier_detail": desc_clean or "长桥未返回公司简介。",
            "market_share": "未取得官方市占拆解",
            "business_model": "未披露",
            "prospect_and_catalysts": "未从单期快照得出催化结论。",
        }
    ]

    return {
        "symbol": sym,
        "company_name": cname,
        "essence": essence_obj,
        "industry": {
            "sector": sector,
            "macro_backdrop": None,
            "tam": None,
            "lifecycle": lifecycle_obj,
            "competitors": [],
        },
        "products": products,
        "supply_chain": None,
        "is_preset": False,
        "source_tag": "非预置库标的 · 仅展示长桥官方公司简介与单期财务同比",
    }


def build_company_and_product_dossier(symbol: str, company: Optional[Dict[str, Any]], financials: Optional[Dict[str, Any]], force_refresh: bool = False) -> Dict[str, Any]:
    """
    Construct rich business profile and core products teardown.
    """
    sym = normalize_symbol(symbol)
    cache_key = f"product_kb_v6:{sym}"
    if not force_refresh:
        cached = get_cache(cache_key)
        if cached is not None:
            # If current symbol now has a preset, but cache does not have is_preset, bypass old cache!
            if sym in PRESET_PRODUCT_KNOWLEDGE and not cached.get("is_preset"):
                pass
            else:
                return cached

    preset = PRESET_PRODUCT_KNOWLEDGE.get(sym)
    if preset:
        result = {
            "symbol": sym,
            "company_name": (company or {}).get("name") or (company or {}).get("company_name") or sym,
            "essence": preset["essence"],
            "industry": preset["industry"],
            "products": preset["products"],
            "supply_chain": preset["supply_chain"],
            "is_preset": True,
            "source_tag": "人工投研整理预置库 · 未与本期官方审计财报核对"
        }
        set_cache(cache_key, result, 86400 * 7)
        return result

    result = infer_dynamic_institutional_dossier(sym, company, financials)
    set_cache(cache_key, result, 86400 * 3)
    return result


