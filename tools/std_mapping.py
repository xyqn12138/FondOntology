# -*- coding: utf-8 -*-
"""CNFO 命名标准化：标准映射数据（单一数据源）。

为每个 CNFO 概念记录：
- name    : 当前 IRI 本地名
- label   : 当前中文标签（rdfs:label）
- std_zh  : 标准化中文名称（按国内数据标准术语）
- std_en  : 标准英文名称/代码（JR/T 0304.1 英文名称或按词根规则推导；无则空）
- ref     : 标准出处（JR/T 0304.1-2024 / JR/T 0304.2-2024 / JR/T 0176.4-2022 / 基金法 等）
- note    : 处理建议
- new_label: 若标准化中文名与当前标签不同，此处给出新标签
- alt     : 建议补充的 skos:altLabel 列表
- annotate: 是否在 TTL 中补充 cnfom:standardName / cnfom:standardRef 标注

生成：
1) artifacts/cnfo_std_mapping.md   —— 完整对照表（供方案文档引用）
2) artifacts/cnfo_std_annotations.ttl —— 追加到本体 TTL 的标准标注块
"""
from __future__ import annotations

import json
from pathlib import Path

# 标准出处缩写
R3041 = "JR/T 0304.1-2024"   # 基础数据元规范 第1部分
R3042 = "JR/T 0304.2-2024"   # 基础数据元规范 第2部分：基础代码
R1764 = "JR/T 0176.4-2022"   # 证券期货业数据模型 第4部分：基金公司逻辑模型
FUND_LAW = "《证券投资基金法》"
INFO = "《公开募集证券投资基金信息披露管理办法》"
SALE = "《公开募集证券投资基金销售机构监督管理办法》"
SUIT = "《证券期货投资者适当性管理办法》"
PRIV = "《私募投资基金监督管理暂行办法》"


# ---------------------------------------------------------------- 数据属性（40）
DATAPROPS = [
    # name, label, std_zh, std_en, ref, note, new_label, alt, annotate
    dict(name="baseCurrency", label="基础币种", std_zh="币种", std_en="", ref=f"{R3041} §6.2.1 BD000146", note="标准术语为“币种”（品种公用信息，DBD00027）；当前标签“基础币种”可保留作语境限定。", new_label=None, alt=["币种"], annotate=True),
    dict(name="benchmarkName", label="业绩比较基准名称", std_zh="业绩比较基准名称", std_en="", ref="《证券投资基金评价业务管理暂行办法》", note="名称类数据元，符合“对象词+特性词+表示词(名称)”规则。", new_label=None, alt=[], annotate=False),
    dict(name="classificationCode", label="分类代码", std_zh="分类代码", std_en="", ref="行业惯例", note="代码类数据元，符合“以代码为表示词”规则。", new_label=None, alt=[], annotate=False),
    dict(name="distributionWithReinvestment", label="是否收益再投资", std_zh="收益再投资标志", std_en="", ref=f"{R3042} §5.4.1 DBD00036（基金分红方式：1红利转投/2现金分红）", note="布尔型；按 JR/T 0304.1 §4.4 j）是否类数据元以“标志”为表示词（0否/1是）。标签保留“是否收益再投资”，A-BOX/SHACL 层建议用“收益再投资标志”。", new_label=None, alt=["收益再投资标志"], annotate=True),
    dict(name="effectiveFrom", label="生效日期", std_zh="生效日期", std_en="", ref="行业惯例", note="日期类数据元。", new_label=None, alt=[], annotate=False),
    dict(name="effectiveTo", label="失效日期", std_zh="失效日期", std_en="", ref="行业惯例", note="日期类数据元。", new_label=None, alt=[], annotate=False),
    dict(name="filingDate", label="备案日期", std_zh="备案日期", std_en="", ref=f"{PRIV}（私募基金备案）", note="日期类数据元；与“备案标志 FLNG_INDC”（BD000161）配套。", new_label=None, alt=[], annotate=True),
    dict(name="filingNumber", label="备案编号", std_zh="备案编号", std_en="", ref=f"{R3041} §4.4 表3（以“编号”为表示词）", note="编号类数据元。", new_label=None, alt=[], annotate=False),
    dict(name="fundCode", label="基金代码", std_zh="基金代码", std_en="FUND_CDE", ref=f"{R3041} §6.2.2.15 BD000162；{R1764} 品种数据域", note="标准数据元“基金代码 FUND_CDE”，GB/T 39595。当前标签与标准一致。", new_label=None, alt=[], annotate=True),
    dict(name="fundName", label="基金名称", std_zh="基金名称", std_en="FUND_NAME", ref=f"{R3041} §6.2.2.16 BD000163", note="标准数据元“基金名称 FUND_NAME”。", new_label=None, alt=[], annotate=True),
    dict(name="fundNetAssetValue", label="基金资产净值", std_zh="基金资产净值", std_en="FUND_ASET_NV", ref=f"{R3041} §6.2.2.30 BD000177", note="标准数据元“基金资产净值 FUND_ASET_NV”。", new_label=None, alt=[], annotate=True),
    dict(name="fundShortName", label="基金简称", std_zh="基金简称", std_en="FUND_ABBR", ref=f"{R3041} §6.2.2.17 BD000164", note="标准数据元“基金简称 FUND_ABBR”。", new_label=None, alt=[], annotate=True),
    dict(name="fundTypeCode", label="基金类型代码", std_zh="基金类型代码", std_en="FUND_TYPE_CDE", ref=f"{R3041} §4.3.6（英文名称规则推导）", note="标准无同名数据元；基金类型概念对应“基金运作方式 FUND_OPRT_MODE”（BD000165）与“私募基金类型”（DBD00126）等代码表，A-BOX 落地时应映射到具体代码表。", new_label=None, alt=["基金类型"], annotate=True),
    dict(name="fundUnitCode", label="基金份额代码", std_zh="基金份额代码", std_en="FUND_SHR_CDE", ref=f"{R3041} §4.3.6（英文名称规则推导）", note="标准以“基金代码 FUND_CDE”区分基金产品；份额类别代码为基金代码下的细分标识。", new_label=None, alt=[], annotate=True),
    dict(name="fundUnitNetAssetValue", label="基金份额净值", std_zh="基金份额净值", std_en="FUND_SHR_NV", ref=f"{R3041} §6.2.2.31 BD000178", note="标准数据元“基金份额净值 FUND_SHR_NV”，又称“基金单位资产净值”。", new_label=None, alt=["基金单位净值"], annotate=True),
    dict(name="inceptionDate", label="成立日期", std_zh="成立日期", std_en="", ref=f"{R3041} §6.1.1 BD000061", note="标准数据元“成立日期”。", new_label=None, alt=[], annotate=True),
    dict(name="investmentAssetTypeCode", label="投资资产类型代码", std_zh="投资资产类型代码", std_en="INVMT_ASSET_TYPE_CDE", ref=f"{R3041} §6.2.1 BD000139 品种类别（GB/T 35964 CFI 编码）", note="投资资产类型对应标准“品种类别”（DBD00026，GB/T 35964 金融工具分类 CFI 编码）。", new_label=None, alt=["品种类别代码"], annotate=True),
    dict(name="investmentFocus", label="投资重点", std_zh="投资重点", std_en="", ref="行业惯例", note="特性词+对象词结构，可保留。", new_label=None, alt=[], annotate=False),
    dict(name="isExchangeTraded", label="是否交易所交易", std_zh="交易所交易标志", std_en="EXCH_TRAD_INDC", ref=f"{R3041} §4.4 j）（是否类以“标志”为表示词）", note="布尔型；标签保留“是否交易所交易”，落地为数据元时用“交易所交易标志”。", new_label=None, alt=["交易所交易标志"], annotate=True),
    dict(name="isOpenEnded", label="是否开放式", std_zh="开放式标志", std_en="OPEN_END_INDC", ref=f"{R3042} §5.2.4 DBD00029（基金运作方式：1封闭式/2开放式/9其他）", note="对应标准“基金运作方式”代码表；布尔标签保留“是否开放式”。", new_label=None, alt=["开放式运作标志"], annotate=True),
    dict(name="isPrivate", label="是否私募", std_zh="私募标志", std_en="PRIV_INDC", ref=f"{R3041} §4.4 j）；{FUND_LAW}（公开募集/非公开募集）", note="对应公募/私募划分；布尔标签保留“是否私募”。", new_label=None, alt=["私募标志"], annotate=True),
    dict(name="jurisdictionCode", label="法域代码", std_zh="法域代码", std_en="", ref="行业惯例", note="代码类数据元。", new_label=None, alt=[], annotate=False),
    dict(name="maximumInvestmentPercentage", label="最高投资比例", std_zh="最高投资比例", std_en="", ref=f"{R1764} 表3 TLF0000140（产品投资比例限制）", note="投资比例限制类；与“基金组合投资限制”配套。", new_label=None, alt=["投资比例上限"], annotate=True),
    dict(name="minimumInvestmentPercentage", label="最低投资比例", std_zh="最低投资比例", std_en="", ref=f"{R1764} 表3 TLF0000140（产品投资比例限制）", note="投资比例限制类；与“基金组合投资限制”配套。", new_label=None, alt=["投资比例下限"], annotate=True),
    dict(name="positionAsOfDate", label="持仓日期", std_zh="持仓日期", std_en="", ref="行业惯例", note="日期类数据元。", new_label=None, alt=[], annotate=False),
    dict(name="positionCurrency", label="持仓币种", std_zh="持仓币种", std_en="", ref=f"{R3041} §6.2.1 BD000146（币种）", note="币种类数据元，参考“币种 DBD00027”。", new_label=None, alt=["币种"], annotate=True),
    dict(name="positionMarketValue", label="持仓市值", std_zh="持仓市值", std_en="HOLD_MKT_VAL", ref=f"{R1764} §5.5（组合市值）", note="标准模型“组合市值”概念；英文按词根规则推导。", new_label=None, alt=["组合市值"], annotate=True),
    dict(name="positionQuantity", label="持仓数量", std_zh="持有份额", std_en="HOLD_SHR", ref=f"{R3041} §6.5.2.1 BD000308（持有份额 HOLD_SHR）", note="基金份额持仓数量对应标准“持有份额 HOLD_SHR”。", new_label=None, alt=["持有份额"], annotate=True),
    dict(name="redemptionInAmountAllowed", label="是否允许按金额赎回", std_zh="按金额赎回标志", std_en="REDEM_AMT_INDC", ref=f"{R3041} §4.4 j）（是否类以“标志”为表示词）", note="布尔型；标签保留“是否允许按金额赎回”。", new_label=None, alt=["按金额赎回标志"], annotate=True),
    dict(name="redemptionMinimumUnits", label="最低赎回份额", std_zh="最低赎回份额", std_en="", ref=f"{R3041} §6.4.3.6 BD000293（赎回份额 REDEM_SHR）", note="与标准“赎回份额 REDEM_SHR”同源；“最低”为特性限定。", new_label=None, alt=["赎回份额"], annotate=True),
    dict(name="registrationNumber", label="注册编号", std_zh="注册编号", std_en="", ref=f"{R3041} §4.4 表3（以“编号”为表示词）", note="编号类数据元。", new_label=None, alt=[], annotate=False),
    dict(name="riskLevelCode", label="风险等级代码", std_zh="产品风险等级", std_en="RISK_LEVEL", ref=f"{R3042} §5.2.3 DBD00028（产品风险等级：R1-R5）", note="对应标准代码表“产品风险等级”（R1低风险~R5高风险），值域应对齐。", new_label=None, alt=["产品风险等级"], annotate=True),
    dict(name="sourceIdentifier", label="来源标识", std_zh="来源标识", std_en="", ref="行业惯例", note="标识类数据元，可保留。", new_label=None, alt=[], annotate=False),
    dict(name="subscriptionMinimumAmount", label="最低认购金额", std_zh="最低认购金额", std_en="", ref=f"{R3041} §4.4 表3（以“金额”为表示词）", note="金额类数据元；与“认购”行为（基金法）对应。", new_label=None, alt=["认购金额"], annotate=True),
    dict(name="subscriptionMinimumUnits", label="最低认购份额", std_zh="最低认购份额", std_en="", ref=f"{R3041} §4.4 表3", note="份额类数据元。", new_label=None, alt=["认购份额"], annotate=True),
    dict(name="terminationDate", label="终止日期", std_zh="终止日期", std_en="CNL_D", ref=f"{R3041} §6.4.1.3 BD000241（终止日期 CNL_D）", note="标准数据元“终止日期 CNL_D”。", new_label=None, alt=[], annotate=True),
    dict(name="unitCurrency", label="基金份额币种", std_zh="基金份额币种", std_en="", ref=f"{R3041} §6.2.1 BD000146（币种）", note="币种类数据元。", new_label=None, alt=["币种"], annotate=True),
    dict(name="unitQuantity", label="份额数量", std_zh="基金份额", std_en="FUND_SHR", ref=f"{R3041} §6.2.2.29 BD000176（基金份额 FUND_SHR）", note="标准统计指标“基金份额 FUND_SHR”；当前“份额数量”为实体属性视角。", new_label=None, alt=["基金份额"], annotate=True),
    dict(name="valuationCurrency", label="估值币种", std_zh="估值币种", std_en="", ref=f"{R3041} §6.2.1 BD000146（币种）", note="币种类数据元。", new_label=None, alt=["币种"], annotate=True),
    dict(name="valuationDate", label="估值日期", std_zh="估值日期", std_en="", ref="《公开募集证券投资基金信息披露管理办法》", note="日期类数据元，净值披露口径。", new_label=None, alt=[], annotate=False),
]

# ---------------------------------------------------------------- 类（118）
CLASSES = [
    dict(name="ActiveInvestmentStrategy", label="主动投资策略", std_zh="主动投资策略", std_en="", ref="基金从业教材/行业惯例", note="投资策略分类，术语稳定。", new_label=None, alt=[], annotate=False),
    dict(name="AssetValuationActivity", label="基金资产估值活动", std_zh="基金资产估值活动", std_en="", ref=f"{FUND_LAW}（估值）", note="活动类，对应估值核算业务条线（{R1764} 表3）。", new_label=None, alt=["估值活动"], annotate=True),
    dict(name="BondFund", label="债券基金", std_zh="债券型基金", std_en="", ref="GB/T 39595 基金分类", note="国内分类惯称“债券型基金”；当前“债券基金”亦通用，保留并补充别名。", new_label=None, alt=["债券型基金"], annotate=True),
    dict(name="ClosedEndedFund", label="封闭式基金", std_zh="封闭式基金", std_en="", ref=f"{R3042} §5.2.4 DBD00029（基金运作方式：1封闭式）", note="对应标准“基金运作方式=封闭式”。", new_label=None, alt=["封闭式"], annotate=True),
    dict(name="ConceptNature", label="概念性质", std_zh="概念性质", std_en="", ref="CNFO 架构抽象", note="区分法定/监管/市场惯用性质的技术抽象，保留。", new_label=None, alt=[], annotate=False),
    dict(name="ContractualFundStructure", label="契约型基金结构", std_zh="契约型", std_en="", ref=f"{R3042} §5.2.25 DBD00120（基金组织形式：1契约型）", note="对应标准“基金组织形式=契约型”。", new_label=None, alt=["契约型"], annotate=True),
    dict(name="CorporateFundStructure", label="公司型基金结构", std_zh="公司型", std_en="", ref=f"{R3042} §5.2.25 DBD00120（基金组织形式：2公司型）", note="对应标准“基金组织形式=公司型”。", new_label=None, alt=["公司型"], annotate=True),
    dict(name="DebtInvestmentAsset", label="债务类投资资产", std_zh="债券类投资资产", std_en="", ref=f"{R1764} §5.3（外部金融工具：债券）", note="标准以“债券/固定收益”表述；标签标准化为“债券类投资资产”。", new_label="债券类投资资产", alt=["债务类投资资产", "固定收益类投资资产"], annotate=True),
    dict(name="DesignedStatus", label="已设计", std_zh="已设计", std_en="", ref="CNFO 生命周期状态", note="产品生命周期状态，保留。", new_label=None, alt=[], annotate=False),
    dict(name="EquityFund", label="股票基金", std_zh="股票型基金", std_en="", ref="GB/T 39595 基金分类", note="国内分类惯称“股票型基金”。", new_label="股票型基金", alt=["股票基金"], annotate=True),
    dict(name="EquityInvestmentAsset", label="权益类投资资产", std_zh="权益类投资资产", std_en="", ref=f"{R1764} §5.3（外部金融工具：权益；GB/T 35964 CFI）", note="对应标准“权益”品种类别。", new_label=None, alt=["权益类资产"], annotate=True),
    dict(name="ExchangeTradedFund", label="交易型开放式指数基金", std_zh="交易型开放式指数基金", std_en="ETF", ref=f"{R3041} §6.4.3.7（交易型开放式证券投资基金）；{R3042} 现金替代类型", note="标准术语“交易型开放式指数基金（ETF）”，当前标签一致。", new_label=None, alt=["交易型开放式证券投资基金"], annotate=True),
    dict(name="FiledStatus", label="已备案", std_zh="已备案", std_en="", ref=f"{PRIV}（私募基金备案）", note="生命周期状态；与“备案标志 FLNG_INDC”（BD000161）对应。", new_label=None, alt=[], annotate=True),
    dict(name="Fund", label="基金", std_zh="基金", std_en="", ref=f"{FUND_LAW}", note="核心类，术语稳定。", new_label=None, alt=[], annotate=False),
    dict(name="FundAccountantRole", label="基金会计服务机构角色", std_zh="基金会计机构角色", std_en="", ref="行业惯例（基金会计核算）", note="服务机构角色；国内通常表述为“基金会计”。", new_label=None, alt=["基金会计机构角色"], annotate=True),
    dict(name="FundActivity", label="基金业务活动", std_zh="基金业务活动", std_en="", ref=f"{R1764} §5.4（交易数据域）；{R3041} 行为数据域", note="对应标准“行为/交易”数据域。", new_label=None, alt=["基金行为"], annotate=True),
    dict(name="FundAdministratorRole", label="基金行政管理机构角色", std_zh="基金行政管理机构角色", std_en="", ref="境外基金行政服务概念（fund administrator）", note="国内法规无直接对应；保留并注明为服务角色抽象。", new_label=None, alt=[], annotate=False),
    dict(name="FundBenchmark", label="基金业绩比较基准", std_zh="业绩比较基准", std_en="", ref="《证券投资基金评价业务管理暂行办法》；{INFO}", note="标准术语为“业绩比较基准”。", new_label="业绩比较基准", alt=["基金业绩比较基准"], annotate=True),
    dict(name="FundCashDistributionPolicy", label="基金现金分红政策", std_zh="现金分红", std_en="", ref=f"{R3042} §5.4.1 DBD00036（基金分红方式：2现金分红）", note="对应标准“基金分红方式=现金分红”。", new_label=None, alt=["现金分红"], annotate=True),
    dict(name="FundClassification", label="基金分类", std_zh="基金分类", std_en="", ref=f"{R3041} §6.2.1 品种类别；行业分类惯例", note="分类概念，保留。", new_label=None, alt=[], annotate=False),
    dict(name="FundClassificationScheme", label="基金分类体系", std_zh="基金分类体系", std_en="", ref="行业惯例", note="分类体系概念，保留。", new_label=None, alt=[], annotate=False),
    dict(name="FundClassifier", label="基金分类器", std_zh="基金分类概念", std_en="", ref="CNFO 架构抽象", note="“分类器”为生造词；标准语境为“分类/分类概念”。", new_label="基金分类概念", alt=["基金分类器"], annotate=True),
    dict(name="FundContract", label="基金合同", std_zh="基金合同", std_en="", ref=f"{FUND_LAW}；{R1764} §5.6（销售类合同：基金合同）", note="标准术语“基金合同”，保留。", new_label=None, alt=[], annotate=True),
    dict(name="FundDepositaryRole", label="基金托管人角色", std_zh="基金托管人", std_en="", ref=f"{FUND_LAW}；{R3041} §6.1 BD000100（基金托管人代码）", note="对应标准“基金托管人”。", new_label=None, alt=["基金托管人"], annotate=True),
    dict(name="FundDistributionMethod", label="基金收益分配方式", std_zh="基金分红方式", std_en="FUND_DIVD_MODE", ref=f"{R3041} §6.4.3.1 BD000288（基金分红方式 FUND_DIVD_MODE）；{R3042} §5.4.1 DBD00036", note="标准数据元术语为“基金分红方式”；“收益分配”为基金法表述，保留为别名。", new_label="基金分红方式", alt=["基金收益分配方式"], annotate=True),
    dict(name="FundDistributionPolicy", label="基金收益分配政策", std_zh="基金收益分配政策", std_en="", ref=f"{FUND_LAW}（收益分配）", note="法律术语“收益分配”，保留。", new_label=None, alt=[], annotate=False),
    dict(name="FundDistributorRole", label="基金销售机构角色", std_zh="基金销售机构", std_en="", ref=f"{SALE}；{R3041} §6.1 BD000074（基金销售机构代码）", note="对应标准“基金销售机构”。", new_label=None, alt=["基金销售机构"], annotate=True),
    dict(name="FundDocument", label="基金文件", std_zh="基金文件", std_en="", ref=f"{INFO}（披露文件）", note="文件抽象类，保留。", new_label=None, alt=[], annotate=False),
    dict(name="FundEstate", label="基金财产", std_zh="基金财产", std_en="", ref=f"{FUND_LAW}（基金财产独立）", note="法律术语“基金财产”，保留。", new_label=None, alt=[], annotate=True),
    dict(name="FundFilingActivity", label="基金备案活动", std_zh="基金备案活动", std_en="", ref=f"{PRIV}", note="活动类；对应私募基金备案业务。", new_label=None, alt=["备案活动"], annotate=True),
    dict(name="FundFilingDocument", label="基金备案文件", std_zh="基金备案文件", std_en="", ref=f"{PRIV}", note="文件类，保留。", new_label=None, alt=[], annotate=False),
    dict(name="FundHolderRole", label="基金份额持有人角色", std_zh="基金份额持有人", std_en="", ref=f"{FUND_LAW}（基金份额持有人）", note="对应标准/法律术语“基金份额持有人”。", new_label=None, alt=["基金份额持有人"], annotate=True),
    dict(name="FundInvestmentAsset", label="基金投资资产", std_zh="基金投资资产", std_en="", ref=f"{R1764} §5.5（资产数据域：基金投资资产）", note="标准模型“基金投资资产”，保留。", new_label=None, alt=[], annotate=True),
    dict(name="FundInvestmentObjective", label="基金投资目标", std_zh="基金投资目标", std_en="", ref=f"{FUND_LAW}；{INFO}", note="法律/披露术语“投资目标”，保留。", new_label=None, alt=["投资目标"], annotate=True),
    dict(name="FundInvestmentPolicy", label="基金投资政策", std_zh="基金投资政策", std_en="", ref=f"{R1764}（产品投资比例限制等）", note="“投资政策”为英文 investment policy 直译；国内语境多用“投资范围与限制/投资策略”。保留并补充别名。", new_label=None, alt=["投资范围与限制"], annotate=True),
    dict(name="FundInvestmentRestriction", label="基金投资限制", std_zh="基金投资限制", std_en="", ref=f"{R1764} 表3 TLF0000140（产品投资比例限制）", note="对应标准“产品投资比例限制”。", new_label=None, alt=["投资限制"], annotate=True),
    dict(name="FundInvestmentSpecification", label="基金投资说明", std_zh="基金投资说明", std_en="", ref="CNFO 架构抽象", note="投资目标/政策/策略的抽象父类，保留。", new_label=None, alt=[], annotate=False),
    dict(name="FundInvestmentStrategy", label="基金投资策略", std_zh="基金投资策略", std_en="", ref=f"{INFO}（投资策略披露）", note="法律/披露术语“投资策略”，保留。", new_label=None, alt=["投资策略"], annotate=True),
    dict(name="FundJurisdiction", label="基金适用法域", std_zh="基金适用法域", std_en="", ref="行业惯例", note="法域概念，保留。", new_label=None, alt=[], annotate=False),
    dict(name="FundLegalStructure", label="基金法律结构", std_zh="基金组织形式", std_en="", ref=f"{R3042} §5.2.25 DBD00120（基金组织形式：契约型/公司型/合伙型）", note="标准术语为“基金组织形式”，子类与代码值一一对应；标签标准化。", new_label="基金组织形式", alt=["基金法律结构"], annotate=True),
    dict(name="FundLifecycleStatus", label="基金生命周期状态", std_zh="基金生命周期状态", std_en="", ref="CNFO 生命周期状态；{R3041} 机构状态 DBD00014", note="状态抽象类，保留。", new_label=None, alt=[], annotate=False),
    dict(name="FundLiquidationActivity", label="基金清算活动", std_zh="基金清算活动", std_en="", ref=f"{FUND_LAW}（基金财产清算）", note="活动类；对应基金终止后的清算业务。", new_label=None, alt=["清算活动"], annotate=True),
    dict(name="FundManagementCompany", label="基金管理公司", std_zh="基金管理公司", std_en="", ref=f"{FUND_LAW}；{R3041} §6.1 BD000095（基金公司名称）", note="标准/法律术语“基金管理公司”，保留。", new_label=None, alt=["基金公司"], annotate=True),
    dict(name="FundManagerRole", label="基金管理人角色", std_zh="基金管理人", std_en="", ref=f"{FUND_LAW}；{R3041} §6.1 BD000096（基金管理人代码）", note="对应标准“基金管理人”。", new_label=None, alt=["基金管理人"], annotate=True),
    dict(name="FundObject", label="基金领域对象", std_zh="基金领域对象", std_en="", ref="CNFO 架构抽象", note="领域顶层抽象，保留。", new_label=None, alt=[], annotate=False),
    dict(name="FundOfFunds", label="基金中基金", std_zh="基金中基金", std_en="FOF", ref="《基金中基金（FOF）指引》", note="标准/监管术语“基金中基金（FOF）”。", new_label=None, alt=["FOF"], annotate=True),
    dict(name="FundParty", label="基金参与主体", std_zh="基金参与主体", std_en="", ref=f"{R3041} §5.1（主体数据域）；{R1764} §3.1（主体）", note="对应标准“主体”。", new_label=None, alt=["主体"], annotate=True),
    dict(name="FundPeriodicReport", label="基金定期报告", std_zh="基金定期报告", std_en="", ref=f"{INFO}（年度报告、中期报告、季度报告）", note="披露术语“基金定期报告”，保留。", new_label=None, alt=["定期报告"], annotate=True),
    dict(name="FundPortfolio", label="基金投资组合", std_zh="基金投资组合", std_en="", ref=f"{R1764} §5.3（产品数据域：组合）", note="标准模型“组合”，保留。", new_label=None, alt=["组合"], annotate=True),
    dict(name="FundPortfolioInvestmentLimitation", label="基金组合投资限制", std_zh="基金组合投资限制", std_en="", ref=f"{R1764} 表3 TLF0000140（产品投资比例限制）", note="对应标准“产品投资比例限制”。", new_label=None, alt=["产品投资比例限制"], annotate=True),
    dict(name="FundPortfolioInvestmentPolicy", label="基金投资组合政策", std_zh="基金投资组合政策", std_en="", ref="CNFO 业务抽象", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="FundPosition", label="基金份额持仓", std_zh="基金份额持仓", std_en="", ref=f"{R3041} §6.5.2.1（持有份额 HOLD_SHR）", note="对应标准“持有份额”；当前标签保留。", new_label=None, alt=["持有份额"], annotate=True),
    dict(name="FundProcessingTerms", label="基金运作条款", std_zh="基金运作条款", std_en="", ref="CNFO 业务抽象", note="认购/赎回条款的抽象父类，保留。", new_label=None, alt=[], annotate=False),
    dict(name="FundProduct", label="基金产品", std_zh="基金产品", std_en="", ref=f"{R1764} §5.3（产品数据域）；资管新规（资管产品）", note="对应标准“产品/资管产品”。", new_label=None, alt=["产品"], annotate=True),
    dict(name="FundProspectus", label="基金招募说明书", std_zh="基金招募说明书", std_en="", ref=f"{INFO}（招募说明书）", note="标准/披露术语“基金招募说明书”，保留。", new_label=None, alt=["招募说明书"], annotate=True),
    dict(name="FundPurchaseActivity", label="基金申购活动", std_zh="基金申购", std_en="", ref=f"{FUND_LAW}（开放式基金申购）", note="对应标准/法律术语“申购”。", new_label=None, alt=["申购"], annotate=True),
    dict(name="FundRaisingActivity", label="基金募集活动", std_zh="基金募集", std_en="", ref=f"{FUND_LAW}（公开募集/非公开募集）", note="对应标准/法律术语“募集”。", new_label=None, alt=["募集"], annotate=True),
    dict(name="FundRecord", label="基金业务记录", std_zh="基金业务记录", std_en="", ref="CNFO 架构抽象", note="记录抽象类，保留。", new_label=None, alt=[], annotate=False),
    dict(name="FundRedemptionActivity", label="基金赎回活动", std_zh="基金赎回", std_en="", ref=f"{FUND_LAW}（赎回）", note="对应标准/法律术语“赎回”。", new_label=None, alt=["赎回"], annotate=True),
    dict(name="FundRedemptionTerms", label="基金赎回条款", std_zh="基金赎回条款", std_en="", ref=f"{R1764} 表3 TLF0000141（产品申赎限额）", note="对应标准“产品申赎限额”相关条款。", new_label=None, alt=["赎回条款"], annotate=True),
    dict(name="FundRegistrarRole", label="基金份额登记机构角色", std_zh="基金份额登记机构", std_en="", ref=f"{FUND_LAW}（基金份额登记机构）；{R3041} §6.1 BD000117（基金注册登记机构代码）", note="法律表述“基金份额登记机构”，标准数据元“基金注册登记机构”，两者一致。", new_label=None, alt=["基金注册登记机构"], annotate=True),
    dict(name="FundRegistrationActivity", label="基金注册活动", std_zh="基金注册", std_en="", ref=f"{FUND_LAW}（注册）", note="对应法律术语“注册”。", new_label=None, alt=["注册"], annotate=True),
    dict(name="FundReinvestmentPolicy", label="基金收益再投资政策", std_zh="基金收益再投资政策", std_en="", ref=f"{R3042} §5.4.1 DBD00036（基金分红方式：1红利转投）", note="对应标准“红利转投”分红方式；当前标签保留。", new_label=None, alt=["红利再投资", "红利转投"], annotate=True),
    dict(name="FundRiskLevel", label="基金风险等级", std_zh="基金风险等级", std_en="", ref=f"{R3042} §5.2.3 DBD00028（产品风险等级：R1-R5）；{SUIT}", note="对应标准“产品风险等级”，值域 R1~R5。", new_label=None, alt=["产品风险等级"], annotate=True),
    dict(name="FundRole", label="基金角色", std_zh="基金角色", std_en="", ref="CNFO 架构抽象", note="角色抽象类，保留。", new_label=None, alt=[], annotate=False),
    dict(name="FundRoleAssignment", label="基金角色任职记录", std_zh="基金角色任职记录", std_en="", ref="CNFO 业务抽象", note="记录类，保留。", new_label=None, alt=[], annotate=False),
    dict(name="FundServiceProviderRole", label="基金服务机构角色", std_zh="基金服务机构角色", std_en="", ref=f"{R1764}（中介服务机构/商业组织）", note="服务机构角色抽象，保留。", new_label=None, alt=[], annotate=False),
    dict(name="FundStatusRecord", label="基金状态记录", std_zh="基金状态记录", std_en="", ref="CNFO 业务抽象", note="记录类，保留。", new_label=None, alt=[], annotate=False),
    dict(name="FundSubscriptionActivity", label="基金认购活动", std_zh="基金认购", std_en="", ref=f"{FUND_LAW}（认购）", note="对应标准/法律术语“认购”。", new_label=None, alt=["认购"], annotate=True),
    dict(name="FundSubscriptionTerms", label="基金认购条款", std_zh="基金认购条款", std_en="", ref=f"{R1764} 表3 TLF0000141（产品申赎限额）", note="对应标准“产品申赎限额”相关条款。", new_label=None, alt=["认购条款"], annotate=True),
    dict(name="FundSupervisor", label="基金监管机构", std_zh="基金监管机构", std_en="", ref=f"{R1764} §5.1（监管组织）", note="对应标准“监管组织”。", new_label=None, alt=["监管机构"], annotate=True),
    dict(name="FundTemporalRecord", label="基金时态记录", std_zh="基金时态记录", std_en="", ref="CNFO 架构抽象", note="带生效期的记录抽象，保留。", new_label=None, alt=[], annotate=False),
    dict(name="FundTransferAgentRole", label="基金过户登记代理角色", std_zh="基金份额登记代理角色", std_en="", ref=f"{FUND_LAW}（基金份额登记机构）", note="“过户登记代理”（transfer agent）为境外概念；国内对应“基金份额登记”。建议别名对齐。", new_label=None, alt=["基金份额登记代理角色"], annotate=True),
    dict(name="FundUnit", label="基金份额", std_zh="基金份额", std_en="", ref=f"{FUND_LAW}（基金份额）；{R3041} §6.2.2.29 BD000176（基金份额 FUND_SHR）", note="核心类，标准/法律术语“基金份额”，保留。", new_label=None, alt=[], annotate=True),
    dict(name="FundUnitClass", label="基金份额类别", std_zh="基金份额类别", std_en="", ref="行业惯例（份额类别/分类）", note="份额类别概念，保留。", new_label=None, alt=["份额类别"], annotate=True),
    dict(name="FundUnitDistributionPolicy", label="基金份额分配政策", std_zh="基金份额分配政策", std_en="", ref=f"{R3042} §5.4.1 DBD00036（基金分红方式）", note="份额分配政策抽象，保留。", new_label=None, alt=[], annotate=False),
    dict(name="FundUnitInvestmentAsset", label="基金份额类投资资产", std_zh="基金份额类投资资产", std_en="", ref=f"{R1764} §5.3（集合投资工具）", note="FOF 投资标的，对应“集合投资工具”品种类别。", new_label=None, alt=["集合投资工具"], annotate=True),
    dict(name="FundValuationServiceProviderRole", label="基金估值服务机构角色", std_zh="基金估值服务机构角色", std_en="", ref="行业惯例（估值核算）", note="服务机构角色，保留。", new_label=None, alt=[], annotate=False),
    dict(name="GovernmentGuidanceFund", label="政府引导基金", std_zh="政府引导基金", std_en="", ref="《政府投资基金暂行管理办法》", note="监管术语“政府引导基金”，保留。", new_label=None, alt=[], annotate=False),
    dict(name="GovernmentInvestmentFund", label="政府投资基金", std_zh="政府投资基金", std_en="", ref="《政府投资基金暂行管理办法》", note="监管术语“政府投资基金”，保留。", new_label=None, alt=[], annotate=False),
    dict(name="GrowthObjective", label="增长型投资目标", std_zh="增长型投资目标", std_en="", ref="行业惯例", note="投资目标类型，保留。", new_label=None, alt=[], annotate=False),
    dict(name="HybridFund", label="混合基金", std_zh="混合型基金", std_en="", ref="GB/T 39595 基金分类", note="国内分类惯称“混合型基金”。", new_label=None, alt=["混合型基金"], annotate=True),
    dict(name="IncomeDistributionActivity", label="基金收益分配活动", std_zh="基金收益分配活动", std_en="", ref=f"{FUND_LAW}（收益分配）；{R3041} §6.4.3.1（基金分红方式）", note="法律术语“收益分配”/标准“分红”，保留。", new_label=None, alt=["基金分红活动"], annotate=True),
    dict(name="IncomeObjective", label="收入型投资目标", std_zh="收入型投资目标", std_en="", ref="行业惯例", note="投资目标类型，保留。", new_label=None, alt=[], annotate=False),
    dict(name="IndexTrackingStrategy", label="指数跟踪策略", std_zh="指数跟踪策略", std_en="", ref="行业惯例（指数化投资）", note="被动策略子类，保留。", new_label=None, alt=[], annotate=False),
    dict(name="InformationDisclosureActivity", label="基金信息披露活动", std_zh="基金信息披露活动", std_en="", ref=f"{INFO}", note="监管术语“信息披露”，保留。", new_label=None, alt=["信息披露"], annotate=True),
    dict(name="InfrastructurePublicREIT", label="基础设施公募 REIT", std_zh="公开募集基础设施证券投资基金", std_en="REIT", ref="《公开募集基础设施证券投资基金指引（试行）》", note="标准/监管全称“公开募集基础设施证券投资基金”；惯称“基础设施公募REITs”。", new_label=None, alt=["公开募集基础设施证券投资基金", "基础设施公募REITs"], annotate=True),
    dict(name="Investor", label="基金投资者", std_zh="基金投资者", std_en="", ref=f"{FUND_LAW}；{R3041} §6.1.4（投资者信息）", note="对应标准“投资者”。", new_label=None, alt=["投资者"], annotate=True),
    dict(name="LiquidatingStatus", label="清算中", std_zh="清算中", std_en="", ref=f"{FUND_LAW}（基金财产清算）", note="生命周期状态，保留。", new_label=None, alt=[], annotate=False),
    dict(name="ListedOpenEndedFund", label="上市开放式基金", std_zh="上市开放式基金", std_en="LOF", ref="《上海证券交易所上市开放式基金业务指引》", note="监管术语“上市开放式基金（LOF）”，LOF 别名已存在。", new_label=None, alt=[], annotate=True),
    dict(name="MarketConventionType", label="市场惯用类型", std_zh="市场惯用类型", std_en="", ref="CNFO 架构抽象", note="概念性质子类，保留。", new_label=None, alt=[], annotate=False),
    dict(name="MoneyMarketFund", label="货币市场基金", std_zh="货币市场基金", std_en="", ref="《货币市场基金监督管理办法》", note="监管术语“货币市场基金”，保留。", new_label=None, alt=[], annotate=True),
    dict(name="NetAssetValueCalculationActivity", label="基金净值计算活动", std_zh="基金净值计算活动", std_en="", ref=f"{INFO}（净值披露）；{R1764}（估值核算）", note="活动类，保留。", new_label=None, alt=["净值计算"], annotate=True),
    dict(name="NetAssetValueRecord", label="基金净值记录", std_zh="基金净值记录", std_en="", ref=f"{R3041} §6.2.2.30-31（基金资产净值/基金份额净值）", note="净值事实记录，保留。", new_label=None, alt=["净值记录"], annotate=True),
    dict(name="OpenEndedFund", label="开放式基金", std_zh="开放式基金", std_en="", ref=f"{R3042} §5.2.4 DBD00029（基金运作方式：2开放式）", note="对应标准“基金运作方式=开放式”。", new_label=None, alt=["开放式"], annotate=True),
    dict(name="OperatingStatus", label="运作中", std_zh="运作中", std_en="", ref="CNFO 生命周期状态", note="生命周期状态，保留。", new_label=None, alt=[], annotate=False),
    dict(name="PartnershipFundStructure", label="合伙型基金结构", std_zh="合伙型", std_en="", ref=f"{R3042} §5.2.25 DBD00120（基金组织形式：3合伙型）", note="对应标准“基金组织形式=合伙型”。", new_label=None, alt=["合伙型"], annotate=True),
    dict(name="PassiveInvestmentStrategy", label="被动投资策略", std_zh="被动投资策略", std_en="", ref="行业惯例", note="投资策略分类，保留。", new_label=None, alt=[], annotate=False),
    dict(name="PensionTargetFund", label="养老目标基金", std_zh="养老目标基金", std_en="", ref="《养老目标证券投资基金指引（试行）》", note="监管术语“养老目标基金”，保留。", new_label=None, alt=[], annotate=True),
    dict(name="PeriodicOpenEndedFund", label="定期开放式基金", std_zh="定期开放式基金", std_en="", ref="行业惯例（定开基金）", note="保留。", new_label=None, alt=["定开基金"], annotate=True),
    dict(name="PortfolioPosition", label="投资组合持仓", std_zh="组合持仓", std_en="", ref=f"{R1764} §5.5（组合头寸、组合市值、组合持仓、组合变动）", note="标准模型“组合持仓”；当前标签保留。", new_label=None, alt=["组合持仓"], annotate=True),
    dict(name="PrivateEquityFund", label="私募股权投资基金", std_zh="私募股权投资基金", std_en="", ref=f"{R3042} §5.2.31 DBD00126（私募基金类型：2私募股权、创业投资基金）", note="对应标准“私募股权投资基金”。", new_label=None, alt=["私募股权基金"], annotate=True),
    dict(name="PrivateFund", label="私募基金", std_zh="私募基金", std_en="", ref=f"{PRIV}；{FUND_LAW}（非公开募集）", note="监管术语“私募基金”，保留。", new_label=None, alt=[], annotate=True),
    dict(name="PrivateRealEstateInvestmentFund", label="不动产私募投资基金", std_zh="不动产私募投资基金", std_en="", ref="《不动产私募投资基金试点备案指引（试行）》", note="监管术语“不动产私募投资基金”，保留。", new_label=None, alt=[], annotate=False),
    dict(name="PrivateSecuritiesInvestmentFund", label="私募证券投资基金", std_zh="私募证券投资基金", std_en="", ref=f"{R3042} §5.2.31 DBD00126（私募基金类型：1私募证券投资基金）", note="对应标准“私募证券投资基金”。", new_label=None, alt=[], annotate=True),
    dict(name="PublicFund", label="公募基金", std_zh="公募基金", std_en="", ref=f"{FUND_LAW}（公开募集基金）", note="法律术语“公募基金”，保留。", new_label=None, alt=[], annotate=True),
    dict(name="PublicSecuritiesInvestmentFund", label="公募证券投资基金", std_zh="公募证券投资基金", std_en="", ref=f"{FUND_LAW}（公开募集证券投资基金）", note="法律术语“公开募集证券投资基金”，保留。", new_label=None, alt=["公开募集证券投资基金"], annotate=True),
    dict(name="QDIIFund", label="合格境内机构投资者基金", std_zh="合格境内机构投资者基金", std_en="QDII", ref="《合格境内机构投资者境外证券投资管理试行办法》", note="监管术语“合格境内机构投资者（QDII）基金”。", new_label=None, alt=["QDII基金"], annotate=True),
    dict(name="QualifiedInvestor", label="合格投资者", std_zh="合格投资者", std_en="", ref=f"{PRIV}；{SUIT}", note="监管术语“合格投资者”，保留。", new_label=None, alt=[], annotate=True),
    dict(name="RaisingStatus", label="募集期", std_zh="募集期", std_en="", ref="CNFO 生命周期状态", note="生命周期状态，保留。", new_label=None, alt=[], annotate=False),
    dict(name="RegisteredStatus", label="已注册", std_zh="已注册", std_en="", ref=f"{FUND_LAW}（注册）", note="生命周期状态，保留。", new_label=None, alt=[], annotate=False),
    dict(name="RegistrationPendingStatus", label="待注册", std_zh="待注册", std_en="", ref=f"{FUND_LAW}（注册）", note="生命周期状态，保留。", new_label=None, alt=[], annotate=False),
    dict(name="RegulatoryProductType", label="监管产品类型", std_zh="监管产品类型", std_en="", ref=f"{R1764} §10（基金监管范围）", note="概念性质子类，保留。", new_label=None, alt=[], annotate=False),
    dict(name="SecuritiesInvestmentFund", label="证券投资基金", std_zh="证券投资基金", std_en="", ref=f"{FUND_LAW}", note="法律术语“证券投资基金”，保留。", new_label=None, alt=[], annotate=True),
    dict(name="StatutoryFundType", label="法定基金类型", std_zh="法定基金类型", std_en="", ref=f"{FUND_LAW}", note="概念性质子类，保留。", new_label=None, alt=[], annotate=False),
    dict(name="SuspendedStatus", label="暂停运作", std_zh="暂停运作", std_en="", ref="CNFO 生命周期状态", note="生命周期状态，保留。", new_label=None, alt=[], annotate=False),
    dict(name="TerminatedStatus", label="已终止", std_zh="已终止", std_en="", ref="CNFO 生命周期状态", note="生命周期状态，保留。", new_label=None, alt=[], annotate=False),
    dict(name="VentureCapitalFund", label="创业投资基金", std_zh="创业投资基金", std_en="", ref=f"{R3042} §5.2.31 DBD00126（私募基金类型：2私募股权、创业投资基金）", note="监管术语“创业投资基金”，保留。", new_label=None, alt=["创投基金"], annotate=True),
]

# ---------------------------------------------------------------- 对象属性（91）
OBJPROPS = [
    dict(name="activityOfFund", label="业务活动对应基金", std_zh="业务活动对应基金", std_en="", ref=f"{R1764} §6（IBR：主体-行为-关系）", note="活动→基金 方向，与 hasFundActivity 互逆，保留。", new_label=None, alt=[], annotate=False),
    dict(name="appliesToFundUnit", label="适用于基金份额", std_zh="适用于基金份额", std_en="", ref="行业惯例", note="条款→份额，保留。", new_label=None, alt=[], annotate=False),
    dict(name="assetHasPortfolioPosition", label="投资资产具有组合持仓", std_zh="投资资产具有组合持仓", std_en="", ref=f"{R1764} §5.5（资产数据域）", note="资产→持仓，与 positionInAsset 互逆，保留。", new_label=None, alt=[], annotate=False),
    dict(name="assignmentForFund", label="任职记录对应基金", std_zh="任职记录对应基金", std_en="", ref="CNFO 业务抽象", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="assignmentPlayedBy", label="任职记录由主体承担", std_zh="任职记录由主体承担", std_en="", ref="CNFO 业务抽象", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="assignsFundRole", label="任职记录指定角色", std_zh="任职记录指定角色", std_en="", ref="CNFO 业务抽象", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="classifiesFund", label="分类标识基金", std_zh="分类标识基金", std_en="", ref="行业惯例", note="分类概念→基金，保留。", new_label=None, alt=[], annotate=False),
    dict(name="definedInProspectus", label="投资限制载明于招募说明书", std_zh="投资限制载明于招募说明书", std_en="", ref=f"{INFO}", note="限制→招募说明书，保留。", new_label=None, alt=[], annotate=False),
    dict(name="definesClassification", label="分类体系定义分类", std_zh="分类体系定义分类", std_en="", ref="行业惯例", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="definesInvestmentRestriction", label="定义投资限制", std_zh="定义投资限制", std_en="", ref=f"{R1764}（产品投资比例限制）", note="投资政策→投资限制，保留。", new_label=None, alt=[], annotate=False),
    dict(name="describedBy", label="由基金文件描述", std_zh="由基金文件描述", std_en="", ref=f"{INFO}", note="基金→招募说明书，保留。", new_label=None, alt=[], annotate=False),
    dict(name="describesFund", label="基金文件描述基金", std_zh="基金文件描述基金", std_en="", ref=f"{INFO}", note="招募说明书→基金，保留。", new_label=None, alt=[], annotate=False),
    dict(name="fundEstateOf", label="基金财产对应基金", std_zh="基金财产对应基金", std_en="", ref=f"{FUND_LAW}", note="财产→基金，保留。", new_label=None, alt=[], annotate=False),
    dict(name="fundProductOf", label="基金产品对应基金", std_zh="基金产品对应基金", std_en="", ref=f"{R1764}（产品数据域）", note="产品→基金，保留。", new_label=None, alt=[], annotate=False),
    dict(name="fundUnitClassOf", label="基金份额类别对应基金", std_zh="基金份额类别对应基金", std_en="", ref="行业惯例", note="份额类别→基金，保留。", new_label=None, alt=[], annotate=False),
    dict(name="governedBy", label="受基金合同约束", std_zh="受基金合同约束", std_en="", ref=f"{FUND_LAW}", note="基金→合同，保留。", new_label=None, alt=[], annotate=False),
    dict(name="governsFund", label="基金合同约束基金", std_zh="基金合同约束基金", std_en="", ref=f"{FUND_LAW}", note="合同→基金，保留。", new_label=None, alt=[], annotate=False),
    dict(name="governsInvestmentStrategy", label="约束投资策略", std_zh="约束投资策略", std_en="", ref="行业惯例", note="投资政策→策略，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasApplicableJurisdiction", label="适用基金法域", std_zh="适用基金法域", std_en="", ref="行业惯例", note="法律结构→法域，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasConceptNature", label="具有概念性质", std_zh="具有概念性质", std_en="", ref="CNFO 架构抽象", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasDistributionMethod", label="采用收益分配方式", std_zh="采用基金分红方式", std_en="", ref=f"{R3041} §6.4.3.1（基金分红方式）", note="标签随 FundDistributionMethod 标准化为“基金分红方式”。", new_label="采用基金分红方式", alt=["采用收益分配方式"], annotate=True),
    dict(name="hasDistributionPolicy", label="具有份额分配政策", std_zh="具有份额分配政策", std_en="", ref=f"{R3042} §5.4.1 DBD00036", note="份额类别→分配政策，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundAccountantRole", label="具有基金会计服务机构角色", std_zh="具有基金会计机构角色", std_en="", ref="行业惯例", note="随 FundAccountantRole 别名对齐；标签保留。", new_label=None, alt=["具有基金会计机构角色"], annotate=False),
    dict(name="hasFundActivity", label="具有基金业务活动", std_zh="具有基金业务活动", std_en="", ref=f"{R1764} §6（IBR）", note="基金→活动，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundAdministratorRole", label="具有基金行政管理机构角色", std_zh="具有基金行政管理机构角色", std_en="", ref="CNFO 业务抽象", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundClassifier", label="具有基金分类器", std_zh="具有基金分类概念", std_en="", ref="CNFO 架构抽象", note="标签随 FundClassifier 标准化为“基金分类概念”。", new_label="具有基金分类概念", alt=["具有基金分类器"], annotate=True),
    dict(name="hasFundDepositaryRole", label="具有基金托管人角色", std_zh="具有基金托管人角色", std_en="", ref=f"{FUND_LAW}", note="基金→托管人角色，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundDistributorRole", label="具有基金销售机构角色", std_zh="具有基金销售机构角色", std_en="", ref=f"{SALE}", note="基金→销售机构角色，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundDocument", label="具有基金文件", std_zh="具有基金文件", std_en="", ref=f"{INFO}", note="基金→文件，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundEstate", label="具有基金财产", std_zh="具有基金财产", std_en="", ref=f"{FUND_LAW}", note="基金→财产，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundManagerRole", label="具有基金管理人角色", std_zh="具有基金管理人角色", std_en="", ref=f"{FUND_LAW}", note="基金→管理人角色，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundObject", label="具有基金对象", std_zh="具有基金对象", std_en="", ref="CNFO 架构抽象", note="顶层关联，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundParty", label="具有基金参与主体", std_zh="具有基金参与主体", std_en="", ref=f"{R3041} §5.1（主体）", note="基金→主体，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundPortfolio", label="具有基金投资组合", std_zh="具有基金投资组合", std_en="", ref=f"{R1764}（组合）", note="基金→组合，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundPortfolioPosition", label="具有投资组合持仓", std_zh="具有组合持仓", std_en="", ref=f"{R1764} §5.5（组合持仓）", note="组合→持仓，标签可简化为“具有组合持仓”。", new_label=None, alt=["具有组合持仓"], annotate=False),
    dict(name="hasFundPosition", label="基金份额具有持仓", std_zh="基金份额具有持仓", std_en="", ref=f"{R3041} §6.5.2（持有）", note="份额→持仓，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundProduct", label="具有基金产品", std_zh="具有基金产品", std_en="", ref=f"{R1764}（产品）", note="基金→产品，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundRecord", label="具有基金记录", std_zh="具有基金记录", std_en="", ref="CNFO 架构抽象", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundRedemptionTerms", label="具有赎回条款", std_zh="具有赎回条款", std_en="", ref=f"{R1764} TLF0000141（产品申赎限额）", note="基金→赎回条款，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundRegistrarRole", label="具有基金份额登记机构角色", std_zh="具有基金份额登记机构角色", std_en="", ref=f"{FUND_LAW}", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundRole", label="具有基金角色", std_zh="具有基金角色", std_en="", ref="CNFO 架构抽象", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundRoleAssignment", label="具有基金角色任职记录", std_zh="具有基金角色任职记录", std_en="", ref="CNFO 业务抽象", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundServiceProviderRole", label="具有基金服务机构角色", std_zh="具有基金服务机构角色", std_en="", ref="CNFO 架构抽象", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundStatus", label="具有基金状态", std_zh="具有基金状态", std_en="", ref="CNFO 业务抽象", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundStatusRecord", label="具有基金状态记录", std_zh="具有基金状态记录", std_en="", ref="CNFO 业务抽象", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundSubscriptionTerms", label="具有认购条款", std_zh="具有认购条款", std_en="", ref=f"{R1764} TLF0000141", note="基金→认购条款，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundSupervisor", label="具有基金监管机构", std_zh="具有基金监管机构", std_en="", ref=f"{R1764}（监管组织）", note="基金→监管机构，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundTransferAgentRole", label="具有基金过户登记代理角色", std_zh="具有基金份额登记代理角色", std_en="", ref=f"{FUND_LAW}（基金份额登记机构）", note="随 FundTransferAgentRole 别名对齐；标签保留。", new_label=None, alt=["具有基金份额登记代理角色"], annotate=False),
    dict(name="hasFundUnit", label="具有基金份额", std_zh="具有基金份额", std_en="", ref=f"{FUND_LAW}", note="基金→份额，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasFundUnitClass", label="具有基金份额类别", std_zh="具有基金份额类别", std_en="", ref="行业惯例", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasIntendedRiskLevel", label="具有目标风险等级", std_zh="具有目标风险等级", std_en="", ref=f"{SUIT}；{R3042} DBD00028", note="投资目标→风险等级，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasInvestmentObjective", label="具有投资目标", std_zh="具有投资目标", std_en="", ref=f"{FUND_LAW}", note="基金→投资目标，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasInvestmentPolicy", label="具有投资政策", std_zh="具有投资政策", std_en="", ref="行业惯例", note="基金→投资政策，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasInvestmentRestriction", label="招募说明书载明投资限制", std_zh="招募说明书载明投资限制", std_en="", ref=f"{INFO}", note="招募说明书→投资限制，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasInvestmentSpecification", label="具有投资说明", std_zh="具有投资说明", std_en="", ref="CNFO 架构抽象", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasInvestor", label="具有投资者", std_zh="具有投资者", std_en="", ref=f"{R3041} §6.1.4（投资者信息）", note="基金→投资者，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasLegalStructure", label="具有法律结构", std_zh="具有基金组织形式", std_en="", ref=f"{R3042} §5.2.25 DBD00120", note="标签随 FundLegalStructure 标准化为“基金组织形式”。", new_label="具有基金组织形式", alt=["具有法律结构"], annotate=True),
    dict(name="hasNetAssetValueRecord", label="具有净值记录", std_zh="具有净值记录", std_en="", ref=f"{INFO}（净值披露）", note="基金→净值记录，保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasPortfolioInvestmentStrategy", label="投资组合采用策略", std_zh="投资组合采用策略", std_en="", ref="行业惯例", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasStatusValue", label="状态记录的状态值", std_zh="状态记录的状态值", std_en="", ref="CNFO 业务抽象", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="hasUnderlyingFund", label="具有底层基金", std_zh="具有底层基金", std_en="", ref="《基金中基金（FOF）指引》", note="FOF→底层基金，保留。", new_label=None, alt=["投资标的基金"], annotate=False),
    dict(name="heldByInvestor", label="基金份额头寸由投资者持有", std_zh="基金份额头寸由投资者持有", std_en="", ref=f"{R3041} §6.5.2（持有）", note="头寸→投资者，保留。", new_label=None, alt=[], annotate=False),
    dict(name="holdsFundPosition", label="持有基金份额头寸", std_zh="持有基金份额头寸", std_en="", ref=f"{R3041} §6.5.2（持有份额）", note="投资者→头寸，保留。", new_label=None, alt=[], annotate=False),
    dict(name="implementsInvestmentPolicy", label="投资组合执行政策", std_zh="投资组合执行政策", std_en="", ref="行业惯例", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="isClassifiedBy", label="被分类为", std_zh="被分类为", std_en="", ref="行业惯例", note="与 hasFundClassifier 关联，保留。", new_label=None, alt=[], annotate=False),
    dict(name="issuedByFund", label="基金份额由基金发行", std_zh="基金份额由基金发行", std_en="", ref=f"{R1764} §6（主体-产品：发行）", note="份额→基金（发行关系），保留。", new_label=None, alt=[], annotate=False),
    dict(name="issuesFundUnit", label="发行基金份额", std_zh="发行基金份额", std_en="", ref=f"{R1764} §6（发行）", note="基金→份额（发行关系），保留。", new_label=None, alt=[], annotate=False),
    dict(name="legalStructureOf", label="法律结构对应基金", std_zh="基金组织形式对应基金", std_en="", ref=f"{R3042} §5.2.25 DBD00120", note="标签随 FundLegalStructure 标准化。", new_label="基金组织形式对应基金", alt=["法律结构对应基金"], annotate=True),
    dict(name="objectiveOfFund", label="投资目标对应基金", std_zh="投资目标对应基金", std_en="", ref=f"{FUND_LAW}", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="outlinesObjective", label="基金招募说明书载明投资目标", std_zh="基金招募说明书载明投资目标", std_en="", ref=f"{INFO}", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="playsFundRole", label="主体承担基金角色", std_zh="主体承担基金角色", std_en="", ref="CNFO 架构抽象", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="policyOfFund", label="投资政策对应基金", std_zh="投资政策对应基金", std_en="", ref="行业惯例", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="portfolioOfFund", label="投资组合对应基金", std_zh="投资组合对应基金", std_en="", ref=f"{R1764}（组合）", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="positionInAsset", label="持仓对应投资资产", std_zh="持仓对应投资资产", std_en="", ref=f"{R1764} §5.5", note="持仓→资产，保留。", new_label=None, alt=[], annotate=False),
    dict(name="positionInFundUnit", label="头寸对应基金份额", std_zh="头寸对应基金份额", std_en="", ref=f"{R3041} §6.5.2", note="头寸→份额，保留。", new_label=None, alt=[], annotate=False),
    dict(name="positionOfPortfolio", label="持仓对应投资组合", std_zh="持仓对应投资组合", std_en="", ref=f"{R1764} §5.5（组合持仓）", note="持仓→组合，保留。", new_label=None, alt=[], annotate=False),
    dict(name="providesCustodyForFundUnit", label="托管基金份额", std_zh="托管基金份额", std_en="", ref=f"{FUND_LAW}（托管）", note="托管人角色→份额，保留。", new_label=None, alt=[], annotate=False),
    dict(name="realizesFundProduct", label="实现基金产品", std_zh="实现基金产品", std_en="", ref=f"{R1764}（产品）", note="“实现”为 FIBO 风格；国内可理解为“产品落地/产品化”。保留。", new_label=None, alt=["落地为基金产品"], annotate=False),
    dict(name="recordForFund", label="净值记录对应基金", std_zh="净值记录对应基金", std_en="", ref=f"{INFO}", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="redemptionTermsForFund", label="赎回条款对应基金", std_zh="赎回条款对应基金", std_en="", ref=f"{R1764} TLF0000141", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="roleInFund", label="角色适用于基金", std_zh="角色适用于基金", std_en="", ref="CNFO 架构抽象", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="rolePlayedBy", label="角色由主体承担", std_zh="角色由主体承担", std_en="", ref="CNFO 架构抽象", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="statedIn", label="载明于基金招募说明书", std_zh="载明于基金招募说明书", std_en="", ref=f"{INFO}", note="投资目标→招募说明书，保留。", new_label=None, alt=[], annotate=False),
    dict(name="statusOfFund", label="生命周期状态对应基金", std_zh="生命周期状态对应基金", std_en="", ref="CNFO 业务抽象", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="statusRecordForFund", label="状态记录对应基金", std_zh="状态记录对应基金", std_en="", ref="CNFO 业务抽象", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="stipulatesBenchmark", label="规定业绩比较基准", std_zh="规定业绩比较基准", std_en="", ref="《证券投资基金评价业务管理暂行办法》", note="投资政策→业绩比较基准，保留。", new_label=None, alt=[], annotate=False),
    dict(name="strategyOfFund", label="投资策略对应基金", std_zh="投资策略对应基金", std_en="", ref=f"{INFO}", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="subscriptionTermsForFund", label="认购条款对应基金", std_zh="认购条款对应基金", std_en="", ref=f"{R1764} TLF0000141", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="supervisesFund", label="监管基金", std_zh="监管基金", std_en="", ref=f"{R1764}（监管组织）", note="监管机构→基金，保留。", new_label=None, alt=[], annotate=False),
    dict(name="underlyingFundOf", label="作为底层基金属于", std_zh="作为底层基金属于", std_en="", ref="《基金中基金（FOF）指引》", note="保留。", new_label=None, alt=[], annotate=False),
    dict(name="usesInvestmentStrategy", label="使用投资策略", std_zh="使用投资策略", std_en="", ref=f"{INFO}", note="基金→策略，保留。", new_label=None, alt=[], annotate=False),
]

# ---------------------------------------------------------------- 生成器
OUT_DIR = Path(__file__).resolve().parents[1] / "artifacts"


def _row(item: dict) -> str:
    new_label = item.get("new_label") or ""
    alt = "；".join(item.get("alt") or [])
    return "|".join([
        item["name"], item["label"], new_label, item["std_zh"],
        item.get("std_en") or "", item["ref"], alt, item["note"],
    ])


def gen_markdown() -> str:
    lines = ["# CNFO 命名标准化对照表（生成数据，勿手改）", ""]
    lines.append("## 数据属性（40）")
    lines.append("| 当前 IRI | 当前中文标签 | 标准化中文标签 | 标准中文名称 | 标准英文名称/代码 | 标准出处 | 建议别名 | 说明 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for item in DATAPROPS:
        lines.append("|" + _row(item).replace("|", "｜") + "|")
    lines.append("")
    lines.append("## 类（118）")
    lines.append("| 当前 IRI | 当前中文标签 | 标准化中文标签 | 标准中文名称 | 标准英文名称/代码 | 标准出处 | 建议别名 | 说明 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for item in CLASSES:
        lines.append("|" + _row(item).replace("|", "｜") + "|")
    lines.append("")
    lines.append("## 对象属性（91）")
    lines.append("| 当前 IRI | 当前中文标签 | 标准化中文标签 | 标准中文名称 | 标准英文名称/代码 | 标准出处 | 建议别名 | 说明 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for item in OBJPROPS:
        lines.append("|" + _row(item).replace("|", "｜") + "|")
    return "\n".join(lines)


def gen_turtle_annotations() -> str:
    blocks = []
    # 1) 建议别名（skos:altLabel），与已有别名合并去重
    alt_items = [it for it in (CLASSES + OBJPROPS + DATAPROPS) if it.get("alt")]
    blocks.append(f"# ===== 建议别名 skos:altLabel（共 {len(alt_items)} 项） =====")
    for item in alt_items:
        for alt in item.get("alt") or []:
            blocks.append(f"cnfo:{item['name']} skos:altLabel \"{alt}\"@zh .")
    blocks.append("")
    # 2) 标准名称/标准出处标注
    for kind, items in (("数据属性", DATAPROPS), ("类", CLASSES), ("对象属性", OBJPROPS)):
        annotated = [it for it in items if it.get("annotate")]
        blocks.append(f"# ===== {kind}：标准名称/标准出处标注（共 {len(annotated)} 项） =====")
        for item in annotated:
            std_en = item.get("std_en") or ""
            if std_en:
                blocks.append(f"cnfo:{item['name']} cnfom:standardName \"{std_en}\" ;")
                blocks.append(f"    cnfom:standardRef \"{item['ref']}\" .")
            else:
                blocks.append(f"cnfo:{item['name']} cnfom:standardRef \"{item['ref']}\" .")
        blocks.append("")
    return "\n".join(blocks)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "cnfo_std_mapping.md").write_text(gen_markdown(), encoding="utf-8")
    (OUT_DIR / "cnfo_std_annotations.ttl").write_text(gen_turtle_annotations(), encoding="utf-8")
    print(f"classes={len(CLASSES)} objprops={len(OBJPROPS)} dataprops={len(DATAPROPS)}")
    print(f"annotated: data={sum(1 for i in DATAPROPS if i.get('annotate'))} "
          f"class={sum(1 for i in CLASSES if i.get('annotate'))} "
          f"obj={sum(1 for i in OBJPROPS if i.get('annotate'))}")
    print(f"label changes: class={sum(1 for i in CLASSES if i.get('new_label'))} "
          f"obj={sum(1 for i in OBJPROPS if i.get('new_label'))}")


if __name__ == "__main__":
    main()
