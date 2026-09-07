# -*- coding: utf-8 -*-
"""CNFO V0.5/V0.5.3 构建数据：语义基础层 + 属性关系契约 + 代码表关联（单一数据源）。

生成内容（追加到 ontology/cnfo-fund.ttl）：
1) 新增抽象类：基础业务对象、跨境互认基金、基金代理主体/角色、业绩、费率、法规、指数及资产类概念
2) 新增对象/数据属性声明（含中文定义）
3) 全部既有属性（91 对象 + 40 数据）的 skos:definition 中文定义
4) 类 ↔ 标准代码概念 skos:closeMatch 关联
5) 兼容属性 skos:changeNote（isOpenEnded/isPrivate 等）
"""
from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "artifacts" / "cnfo_v05_block.ttl"

# ---------------------------------------------------------------- 新增类
NEW_CLASSES = [
    dict(name="FundBusinessObject", label="基金业务对象", parent="FundObject",
         def_="基金领域内代表基金业务标的或业务结果的核心对象，包括基金、基金产品、基金份额、基金财产、投资组合、持仓和投资资产等。"),
    dict(name="CrossBorderFund", label="跨境基金", parent="Fund",
         def_="设立、注册、募集销售、投资运作或监管安排跨越一个以上法域的基金产品或基金对象。"),
    dict(name="MainlandHongKongMutualRecognitionFund", label="内地与香港互认基金", parent="CrossBorderFund",
         def_="受内地与香港基金互认安排约束、可在两地跨境销售的基金产品统称；不等同于合格境内机构投资者基金。"),
    dict(name="HongKongMutualRecognitionFund", label="香港互认基金", parent="MainlandHongKongMutualRecognitionFund",
         def_="依香港法律设立并经中国证监会注册后在内地公开销售的境外互认基金。",
         annotate=(("standardRef", "《香港互认基金管理规定》；JR/T 0304.2-2024 DBD00107（香港互认基金类别）"),)),
    dict(name="MainlandMutualRecognitionFund", label="内地互认基金", parent="MainlandHongKongMutualRecognitionFund",
         def_="依内地法律设立并经香港认可后在香港公开销售的内地互认基金。",
         annotate=(("standardRef", "《香港互认基金管理规定》"),)),
    dict(name="FundAgent", label="基金代理人", parent="FundParty",
         def_="在特定基金或跨境基金安排中，依据委托协议承担基金代理事务的机构主体；主体身份与其承担的基金代理人角色分开建模。",
         annotate=(("standardRef", "《公开募集证券投资基金信息披露管理办法》；《香港互认基金管理规定》"),)),
    dict(name="FundAgentRole", label="基金代理人角色", parent="FundServiceProviderRole",
         def_="由基金代理机构或其他被委托主体承担，表示其在特定基金中负责登记、信息披露、销售协同、数据交换、资金清算等约定代理事务的基金服务机构角色；具体职责以适用监管规则和委托协议为准。",
         annotate=(("standardRef", "《公开募集证券投资基金信息披露管理办法》；《香港互认基金管理规定》"),)),
    dict(name="FundPositionRecord", label="基金持仓记录", parent="FundBusinessObject",
         def_="基金领域中描述某一持仓主体对基金份额或投资资产持有数量、币种及其他持仓事实的抽象业务记录；其具体类型包括基金份额持仓和投资组合持仓。"),
    dict(name="FundAccount", label="基金账户", parent="FundObject",
         def_="基金注册登记机构或基金销售机构为基金投资者设立的、用于记录和保存其基金份额持有与变动情况的账户。",
         annotate=(("standardName", "FUND_ACCT"), ("standardRef", "JR/T 0304.1-2024 §6.3.3.1 BD000235"))),
    dict(name="FundOperationModeValue", label="基金运作方式取值", parent="FundObject",
         def_="基金运作方式代码表的取值类型，实例为 JR/T 0304.2-2024 DBD00029 的代码值。",
         annotate=(("standardRef", "JR/T 0304.2-2024 §5.2.4 DBD00029"),)),
    dict(name="FundOrganizationFormValue", label="基金组织形式取值", parent="FundObject",
         def_="基金组织形式代码表的取值类型，实例为 JR/T 0304.2-2024 DBD00120 的代码值。",
         annotate=(("standardRef", "JR/T 0304.2-2024 §5.2.25 DBD00120"),)),
    dict(name="FundDistributionModeValue", label="基金分红方式取值", parent="FundObject",
         def_="基金分红方式代码表的取值类型，实例为 JR/T 0304.2-2024 DBD00036 的代码值。",
         annotate=(("standardRef", "JR/T 0304.2-2024 §5.4.1 DBD00036"),)),
    dict(name="FundRiskLevelValue", label="产品风险等级取值", parent="FundObject",
         def_="产品风险等级代码表的取值类型，实例为 JR/T 0304.2-2024 DBD00028 的代码值（R1-R5）。",
         annotate=(("standardRef", "JR/T 0304.2-2024 §5.2.3 DBD00028"),)),
    dict(name="PrivateFundTypeValue", label="私募基金类型取值", parent="FundObject",
         def_="私募基金类型代码表的取值类型，实例为 JR/T 0304.2-2024 DBD00126 的代码值。",
         annotate=(("standardRef", "JR/T 0304.2-2024 §5.2.31 DBD00126"),)),
    dict(name="FundFeeModeValue", label="基金收费方式取值", parent="FundObject",
         def_="基金收费方式代码表的取值类型，实例为 JR/T 0304.2-2024 DBD00030 的代码值。",
         annotate=(("standardRef", "JR/T 0304.2-2024 §5.2.5 DBD00030"),)),
    dict(name="FundPerformanceRecord", label="基金业绩记录", parent="FundTemporalRecord",
         def_="在特定期间记录基金或基金份额收益表现、回撤、超额收益或跟踪误差等业绩事实的时态业务记录。"),
    dict(name="FundFee", label="基金费率", parent="FundBusinessObject",
         def_="描述基金或基金份额类别适用的管理费、托管费、销售服务费、申赎费或业绩报酬等收费事实。"),
    dict(name="Regulation", label="法律法规与监管规范", parent="FundObject",
         def_="可被基金业务事实、投资限制或信息披露义务引用的法律、行政法规、部门规章及监管规范。"),
    dict(name="FundManagerPerson", label="基金经理", parent="FundParty",
         def_="以自然人身份承担基金经理职责的基金参与主体；其任职事实通过基金经理角色及任职记录表达。"),
    dict(name="MarketIndex", label="市场指数", parent="FundObject",
         def_="由指数编制机构定义并可被业绩比较基准或指数跟踪策略引用的市场指数对象。"),
    dict(name="DerivativeInvestmentAsset", label="衍生品投资资产", parent="FundInvestmentAsset",
         def_="基金投资组合中用于投资、套期保值或风险管理的期货、期权、互换等衍生金融工具。"),
    dict(name="CashAndDepositAsset", label="现金与存款类投资资产", parent="FundInvestmentAsset",
         def_="基金持有的现金、银行存款及其他具有现金管理属性的投资资产。"),
    dict(name="MoneyMarketInstrument", label="货币市场工具", parent="FundInvestmentAsset",
         def_="期限较短、流动性较高并用于货币市场投资的债券、票据、回购等金融工具。"),
    dict(name="AssetBackedSecurity", label="资产支持证券", parent="FundInvestmentAsset",
         def_="以基础资产产生的现金流为支持发行、可作为基金投资标的的资产支持证券。"),
    dict(name="InvestorRiskRating", label="投资者风险承受评级", parent="FundClassifier",
         def_="用于表示投资者风险承受能力或风险承受等级的分类概念，支持投资者适当性匹配。"),
]

# ---------------------------------------------------------------- 新增属性
# type: obj/data；domain/range；inverse/subPropertyOf；def
NEW_PROPS = [
    dict(name="hasFundAccount", type="obj", label="具有基金账户", domain="Investor", range="FundAccount",
         inverse="accountHeldBy",
         def_="表示基金投资者在基金注册登记机构或基金销售机构开立并持有基金账户。"),
    dict(name="hasFundAgentRole", type="obj", label="具有基金代理人角色", domain="Fund", range="FundAgentRole",
         inverse="agentRoleForFund", subproperty="hasFundServiceProviderRole",
         def_="表示基金具有承担基金代理事务的基金代理人角色；具体代理范围由适用规则和委托协议确定。"),
    dict(name="agentRoleForFund", type="obj", label="基金代理人角色适用于基金", domain="FundAgentRole", range="Fund",
         inverse="hasFundAgentRole",
         def_="表示基金代理人角色所适用的基金，与 hasFundAgentRole 互逆。"),
    dict(name="accountHeldBy", type="obj", label="基金账户由投资者持有", domain="FundAccount", range="Investor",
         inverse="hasFundAccount",
         def_="表示基金账户由某基金投资者持有。"),
    dict(name="hasFundOperationMode", type="obj", label="具有基金运作方式", domain="Fund", range="FundOperationModeValue",
         def_="表示基金采用的标准基金运作方式代码（封闭式/开放式/其他，JR/T 0304.2 DBD00029），为基金运作方式的权威事实来源。"),
    dict(name="hasFundOrganizationForm", type="obj", label="具有基金组织形式", domain="Fund", range="FundOrganizationFormValue",
         def_="表示基金采用的标准基金组织形式代码（契约型/公司型/合伙型/其他，JR/T 0304.2 DBD00120），为基金组织形式的权威代码来源。"),
    dict(name="hasFundDistributionMode", type="obj", label="具有基金分红方式", domain="FundUnitClass", range="FundDistributionModeValue",
         def_="表示基金份额类别适用的标准基金分红方式代码（JR/T 0304.2 DBD00036），为分红处理的权威代码来源。"),
    dict(name="hasFundRiskLevel", type="obj", label="具有基金风险等级", domain="Fund", range="FundRiskLevelValue",
         def_="表示基金适用的标准产品风险等级代码（R1-R5，JR/T 0304.2 DBD00028）。"),
    dict(name="hasPrivateFundType", type="obj", label="具有私募基金类型", domain="PrivateFund", range="PrivateFundTypeValue",
         def_="表示私募基金适用的标准私募基金类型代码（JR/T 0304.2 DBD00126）。"),
    dict(name="hasFundFeeMode", type="obj", label="具有基金收费方式", domain="FundUnitClass", range="FundFeeModeValue",
         def_="表示基金份额类别适用的标准基金收费方式代码（JR/T 0304.2 DBD00030）。"),
    dict(name="accountNumber", type="data", label="账户号码", domain="FundAccount", range="string",
         def_="基金账户的账户号码。"),
    dict(name="accountOpeningDate", type="data", label="开户日期", domain="FundAccount", range="date",
         def_="基金账户的开户日期。"),
    dict(name="hasFundManager", type="obj", label="具有基金管理人", domain="Fund", range="FundParty",
         subproperty="hasFundParty",
         def_="通过基金管理人角色及其承担主体派生基金管理人与基金的直接关联。"),
    dict(name="hasFundDepositary", type="obj", label="具有基金托管人", domain="Fund", range="FundParty",
         subproperty="hasFundParty",
         def_="通过基金托管人角色及其承担主体派生基金托管人与基金的直接关联。"),
    dict(name="hasFundAccountFor", type="obj", label="基金具有账户", domain="Fund", range="FundAccount",
         def_="表示基金登记体系具有对应的基金账户，与 accountForFund 互逆。"),
    dict(name="accountForFund", type="obj", label="账户对应基金", domain="FundAccount", range="Fund",
         inverse="hasFundAccountFor",
         def_="表示基金账户所属或服务于哪一只基金，与 hasFundAccountFor 互逆。"),
    dict(name="accountRecordsPosition", type="obj", label="账户记录持仓", domain="FundAccount", range="FundPosition",
         inverse="positionRecordedInAccount",
         def_="表示基金账户记录相应的基金份额持仓，与 positionRecordedInAccount 互逆。"),
    dict(name="positionRecordedInAccount", type="obj", label="持仓记录于账户", domain="FundPosition", range="FundAccount",
         inverse="accountRecordsPosition",
         def_="表示基金份额持仓登记在相应的基金账户中，与 accountRecordsPosition 互逆。"),
    dict(name="recordForFundUnit", type="obj", label="净值记录对应基金份额", domain="NetAssetValueRecord", range="FundUnit",
         inverse="hasNetAssetValueRecordForFundUnit",
         def_="表示净值记录对应特定基金份额或份额类别，用于表达 A 类、C 类等份额级净值。"),
    dict(name="hasNetAssetValueRecordForFundUnit", type="obj", label="基金份额具有净值记录", domain="FundUnit", range="NetAssetValueRecord",
         inverse="recordForFundUnit",
         def_="表示基金份额具有相应的份额级净值记录，与 recordForFundUnit 互逆。"),
    dict(name="hasFundPerformanceRecord", type="obj", label="具有基金业绩记录", domain="Fund", range="FundPerformanceRecord",
         inverse="performanceForFund", subproperty="hasFundRecord",
         def_="表示基金具有描述特定期间业绩表现的基金业绩记录，与 performanceForFund 互逆。"),
    dict(name="performanceForFund", type="obj", label="业绩记录对应基金", domain="FundPerformanceRecord", range="Fund",
         inverse="hasFundPerformanceRecord",
         def_="表示基金业绩记录对应的基金，与 hasFundPerformanceRecord 互逆。"),
    dict(name="performanceUsesBenchmark", type="obj", label="业绩记录采用基准", domain="FundPerformanceRecord", range="FundBenchmark",
         inverse="benchmarkUsedForPerformance",
         def_="表示基金业绩记录采用的业绩比较基准，与 benchmarkUsedForPerformance 互逆。"),
    dict(name="benchmarkUsedForPerformance", type="obj", label="基准用于业绩记录", domain="FundBenchmark", range="FundPerformanceRecord",
         inverse="performanceUsesBenchmark",
         def_="表示业绩比较基准用于评价相应的基金业绩记录，与 performanceUsesBenchmark 互逆。"),
    dict(name="hasFundFee", type="obj", label="具有基金费率", domain="Fund", range="FundFee",
         inverse="feeForFund", subproperty="hasFundObject",
         def_="表示基金具有适用于基金产品层面的收费事实，与 feeForFund 互逆。"),
    dict(name="feeForFund", type="obj", label="费率对应基金", domain="FundFee", range="Fund",
         inverse="hasFundFee",
         def_="表示基金费率对应的基金，与 hasFundFee 互逆。"),
    dict(name="hasFundUnitFee", type="obj", label="份额类别具有费率", domain="FundUnitClass", range="FundFee",
         inverse="feeForFundUnitClass",
         def_="表示基金费率适用于特定基金份额类别，与 feeForFundUnitClass 互逆。"),
    dict(name="feeForFundUnitClass", type="obj", label="费率对应份额类别", domain="FundFee", range="FundUnitClass",
         inverse="hasFundUnitFee",
         def_="表示基金费率对应的基金份额类别，与 hasFundUnitFee 互逆。"),
    dict(name="issuedByAuthority", type="obj", label="法规发布机构", domain="Regulation", range="FundSupervisor",
         inverse="authorityForRegulation",
         def_="表示法律法规或监管规范由相应监管机构发布或制定，与 authorityForRegulation 互逆。"),
    dict(name="authorityForRegulation", type="obj", label="监管机构发布法规", domain="FundSupervisor", range="Regulation",
         inverse="issuedByAuthority",
         def_="表示监管机构发布或制定相应法律法规与监管规范，与 issuedByAuthority 互逆。"),
    dict(name="regulationGovernsFund", type="obj", label="法规规范基金", domain="Regulation", range="Fund",
         inverse="governedByRegulation",
         def_="表示法律法规或监管规范适用于并规范基金业务，与 governedByRegulation 互逆。"),
    dict(name="governedByRegulation", type="obj", label="基金受法规规范", domain="Fund", range="Regulation",
         inverse="regulationGovernsFund",
         def_="表示基金受到相应法律法规或监管规范的约束，与 regulationGovernsFund 互逆。"),
    dict(name="restrictionBasisIn", type="obj", label="投资限制依据法规", domain="FundInvestmentRestriction", range="Regulation",
         inverse="basisForRestriction",
         def_="表示基金投资限制所依据的法律法规或监管规范，与 basisForRestriction 互逆。"),
    dict(name="basisForRestriction", type="obj", label="法规规定投资限制", domain="Regulation", range="FundInvestmentRestriction",
         inverse="restrictionBasisIn",
         def_="表示法律法规或监管规范规定的基金投资限制，与 restrictionBasisIn 互逆。"),
    dict(name="disclosureObligationUnder", type="obj", label="信息披露依据法规", domain="InformationDisclosureActivity", range="Regulation",
         inverse="governsDisclosureActivity",
         def_="表示信息披露活动依据的法律法规或监管规范，与 governsDisclosureActivity 互逆。"),
    dict(name="governsDisclosureActivity", type="obj", label="法规规定披露活动", domain="Regulation", range="InformationDisclosureActivity",
         inverse="disclosureObligationUnder",
         def_="表示法律法规或监管规范规定相应的信息披露活动，与 disclosureObligationUnder 互逆。"),
    dict(name="benchmarkIndex", type="obj", label="基准对应市场指数", domain="FundBenchmark", range="MarketIndex",
         inverse="indexUsedAsBenchmark",
         def_="表示业绩比较基准引用的市场指数，与 indexUsedAsBenchmark 互逆。"),
    dict(name="indexUsedAsBenchmark", type="obj", label="市场指数作为基准", domain="MarketIndex", range="FundBenchmark",
         inverse="benchmarkIndex",
         def_="表示市场指数被用作基金业绩比较基准，与 benchmarkIndex 互逆。"),
    dict(name="trackingTargetIndex", type="obj", label="策略跟踪市场指数", domain="IndexTrackingStrategy", range="MarketIndex",
         inverse="indexTrackedByStrategy",
         def_="表示指数跟踪策略所跟踪的市场指数，与 indexTrackedByStrategy 互逆。"),
    dict(name="indexTrackedByStrategy", type="obj", label="市场指数被策略跟踪", domain="MarketIndex", range="IndexTrackingStrategy",
         inverse="trackingTargetIndex",
         def_="表示市场指数被相应指数跟踪策略跟踪，与 trackingTargetIndex 互逆。"),
    dict(name="hasInvestorRiskRating", type="obj", label="具有投资者风险评级", domain="Investor", range="InvestorRiskRating",
         inverse="ratingForInvestor",
         def_="表示投资者具有相应的风险承受评级，用于适当性匹配，与 ratingForInvestor 互逆。"),
    dict(name="ratingForInvestor", type="obj", label="风险评级对应投资者", domain="InvestorRiskRating", range="Investor",
         inverse="hasInvestorRiskRating",
         def_="表示投资者风险承受评级对应的投资者，与 hasInvestorRiskRating 互逆。"),
    dict(name="compiledBy", type="obj", label="指数编制机构", domain="MarketIndex", range="FundParty",
         inverse="compilesIndex",
         def_="表示市场指数由相应指数编制机构编制，与 compilesIndex 互逆。"),
    dict(name="compilesIndex", type="obj", label="编制市场指数", domain="FundParty", range="MarketIndex",
         inverse="compiledBy",
         def_="表示基金参与主体编制相应市场指数，与 compiledBy 互逆。"),
    dict(name="contractParty", type="obj", label="合同当事人", domain="FundContract", range="FundParty",
         inverse="partyToContract",
         def_="表示基金合同的当事人或签署主体，与 partyToContract 互逆。"),
    dict(name="partyToContract", type="obj", label="主体参与合同", domain="FundParty", range="FundContract",
         inverse="contractParty",
         def_="表示基金参与主体作为当事人参与的基金合同，与 contractParty 互逆。"),
    dict(name="activityPerformedBy", type="obj", label="活动实施主体", domain="FundActivity", range="FundParty",
         inverse="performsFundActivity",
         def_="表示基金业务活动由哪个基金参与主体实施或发起，与 performsFundActivity 互逆。"),
    dict(name="performsFundActivity", type="obj", label="主体实施基金活动", domain="FundParty", range="FundActivity",
         inverse="activityPerformedBy",
         def_="表示基金参与主体实施或发起相应基金业务活动，与 activityPerformedBy 互逆。"),
    dict(name="investorRiskRatingForFund", type="obj", label="投资者评级适用于基金", domain="InvestorRiskRating", range="Fund",
         def_="表示投资者风险承受评级在特定基金适当性判断中的适用范围。"),
    dict(name="fundBenchmark", type="obj", label="基金具有业绩比较基准", domain="Fund", range="FundBenchmark",
         def_="表示基金适用相应业绩比较基准的便捷关联。"),
    dict(name="fundPerformanceForUnit", type="obj", label="业绩记录对应基金份额", domain="FundPerformanceRecord", range="FundUnit",
         inverse="unitPerformanceRecord",
         def_="表示基金业绩记录对应特定基金份额或份额类别，与 unitPerformanceRecord 互逆。"),
    dict(name="unitPerformanceRecord", type="obj", label="基金份额具有业绩记录", domain="FundUnit", range="FundPerformanceRecord",
         inverse="fundPerformanceForUnit",
         def_="表示基金份额具有相应的业绩记录，与 fundPerformanceForUnit 互逆。"),
    dict(name="activityUnderRegulation", type="obj", label="活动适用监管规范", domain="FundActivity", range="Regulation",
         inverse="regulationForActivity",
         def_="表示基金业务活动适用的法律法规或监管规范，与 regulationForActivity 互逆。"),
    dict(name="regulationForActivity", type="obj", label="监管规范适用活动", domain="Regulation", range="FundActivity",
         inverse="activityUnderRegulation",
         def_="表示法律法规或监管规范适用的基金业务活动，与 activityUnderRegulation 互逆。"),
    dict(name="accumulatedUnitNetAssetValue", type="data", label="累计单位净值", domain="NetAssetValueRecord", range="decimal",
         def_="基金份额累计单位净值，用于收益计算、分红复权与业绩分析。"),
    dict(name="performancePeriodStart", type="data", label="业绩期间起始日", domain="FundPerformanceRecord", range="date",
         def_="基金业绩记录统计期间的起始日期。"),
    dict(name="performancePeriodEnd", type="data", label="业绩期间结束日", domain="FundPerformanceRecord", range="date",
         def_="基金业绩记录统计期间的结束日期。"),
    dict(name="cumulativeReturn", type="data", label="累计收益率", domain="FundPerformanceRecord", range="decimal",
         def_="基金在业绩统计期间内的累计收益率。"),
    dict(name="annualizedReturn", type="data", label="年化收益率", domain="FundPerformanceRecord", range="decimal",
         def_="基金在业绩统计期间内按年化口径计算的收益率。"),
    dict(name="excessReturn", type="data", label="超额收益率", domain="FundPerformanceRecord", range="decimal",
         def_="基金收益率相对于对应业绩比较基准收益率的超额部分。"),
    dict(name="maximumDrawdown", type="data", label="最大回撤", domain="FundPerformanceRecord", range="decimal",
         def_="基金业绩统计期间内从峰值到随后低点的最大跌幅。"),
    dict(name="trackingError", type="data", label="跟踪误差", domain="FundPerformanceRecord", range="decimal",
         def_="指数跟踪策略或基金收益相对于跟踪目标指数偏离程度的统计指标。"),
    dict(name="feeName", type="data", label="费率名称", domain="FundFee", range="string",
         def_="基金收费事实的名称，如管理费、托管费、销售服务费或业绩报酬。"),
    dict(name="feeRate", type="data", label="费率", domain="FundFee", range="decimal",
         def_="基金收费事实对应的费率数值。"),
    dict(name="feeAmount", type="data", label="收费金额", domain="FundFee", range="decimal",
         def_="基金收费事实对应的金额数值。"),
    dict(name="feeBasis", type="data", label="收费计提基础", domain="FundFee", range="string",
         def_="基金费率或收费金额的计提基础说明。"),
    dict(name="indexCode", type="data", label="指数代码", domain="MarketIndex", range="string",
         def_="市场指数的唯一或行业识别代码。"),
    dict(name="indexName", type="data", label="指数名称", domain="MarketIndex", range="string",
         def_="市场指数的正式名称。"),
    dict(name="indexCurrency", type="data", label="指数币种", domain="MarketIndex", range="string",
         def_="市场指数计价或计算采用的币种。"),
    dict(name="regulationCode", type="data", label="法规规范代码", domain="Regulation", range="string",
         def_="法律法规或监管规范的编号、文号或其他识别代码。"),
    dict(name="regulationTitle", type="data", label="法规规范名称", domain="Regulation", range="string",
         def_="法律法规或监管规范的正式名称。"),
    dict(name="articleReference", type="data", label="条文引用", domain="Regulation", range="string",
         def_="投资限制、披露义务或其他业务事实所引用的法规条文位置。"),
    dict(name="investorRiskRatingCode", type="data", label="投资者风险评级代码", domain="InvestorRiskRating", range="string",
         def_="投资者风险承受评级的代码值，例如 C1 至 C5。"),
]

# ---------------------------------------------------------------- 既有属性中文定义（91 对象属性）
OBJ_DEFS = {
    "activityOfFund": "将基金业务活动关联到其所属基金，与 hasFundActivity（基金开展活动）方向互逆。",
    "appliesToFundUnit": "表示基金运作条款适用于特定的基金份额或份额类别。",
    "assetHasPortfolioPosition": "表示投资资产作为组合成分被投资组合持仓记录，与 positionInAsset（持仓对应投资资产）互逆。",
    "assignmentForFund": "将基金角色任职记录关联到任职所属的基金。",
    "assignmentPlayedBy": "将基金角色任职记录关联到实际承担该角色的基金参与主体。",
    "assignsFundRole": "将基金角色任职记录关联到被任命的基金角色。",
    "classifiesFund": "表示基金分类概念对基金进行标识、区分或分类，与 hasFundClassifier 互逆。",
    "definedInProspectus": "表示基金投资限制在基金招募说明书中载明，与 hasInvestmentRestriction 互逆。",
    "definesClassification": "表示基金分类体系定义具体的基金分类。",
    "definesInvestmentRestriction": "表示基金投资政策定义相应的基金投资限制。",
    "describedBy": "表示基金由基金文件（如招募说明书）所描述，与 describesFund 互逆。",
    "describesFund": "表示基金文件描述其对应的基金。",
    "fundEstateOf": "将基金财产关联到其所属基金，与 hasFundEstate 互逆。",
    "fundProductOf": "将基金产品关联到其对应的基金，与 hasFundProduct 互逆。",
    "fundUnitClassOf": "将基金份额类别关联到其所属基金，与 hasFundUnitClass 互逆。",
    "governedBy": "表示基金受其基金合同的约束，与 governsFund 互逆。",
    "governsFund": "表示基金合同约束相应的基金。",
    "governsInvestmentStrategy": "表示基金投资政策约束基金投资策略的选择与执行。",
    "hasApplicableJurisdiction": "表示基金法律结构（组织形式）适用特定的基金法域。",
    "hasConceptNature": "表示基金具有法定、监管产品分类或市场惯用的概念性质。",
    "hasDistributionMethod": "表示基金份额分配政策采用具体的基金分红方式。",
    "hasDistributionPolicy": "表示基金份额类别具有对应的基金份额分配政策。",
    "hasFundAccountantRole": "表示基金具有承担基金会计核算职责的基金会计机构角色。",
    "hasFundActivity": "表示基金开展或具有相应的基金业务活动。",
    "hasFundAdministratorRole": "表示基金具有承担行政管理职责的基金服务机构角色。",
    "hasFundClassifier": "表示基金具有对应的基金分类概念（分类、风险等级等），与 classifiesFund 互逆。",
    "hasFundDepositaryRole": "表示基金具有承担基金财产保管与监督职责的基金托管人角色。",
    "hasFundDistributorRole": "表示基金具有承担销售职责的基金销售机构角色。",
    "hasFundDocument": "表示基金具有对应的基金文件（基金合同、招募说明书、定期报告等）。",
    "hasFundEstate": "表示基金具有独立的基金财产，与 fundEstateOf 互逆。",
    "hasFundManagerRole": "表示基金具有承担投资管理职责的基金管理人角色，与 roleInFund/hasFundRole 构成子属性链。",
    "hasFundObject": "基金与基金领域对象之间的一般性关联，作为所有 具有X 关系的顶层父属性。",
    "hasFundParty": "表示基金具有参与基金设立、募集、运作或服务的参与主体。",
    "hasFundPortfolio": "表示基金具有按投资目标和政策组织的投资组合。",
    "hasFundPortfolioPosition": "表示基金投资组合具有组合持仓记录，与 positionOfPortfolio 互逆。",
    "hasFundPosition": "表示基金份额具有对应的基金份额持仓记录。",
    "hasFundProduct": "表示基金具有落地的基金产品，与 fundProductOf 互逆。",
    "hasFundRecord": "表示基金具有对应的基金业务记录（净值、状态、任职等），为记录类关系的顶层子属性。",
    "hasFundRedemptionTerms": "表示基金具有规定赎回条件与流程的赎回条款。",
    "hasFundRegistrarRole": "表示基金具有承担基金份额登记职责的登记机构角色。",
    "hasFundRole": "表示基金具有对应的基金角色，与 roleInFund 互逆。",
    "hasFundRoleAssignment": "表示基金具有角色任职的时态记录。",
    "hasFundServiceProviderRole": "表示基金具有承担专业服务职责的基金服务机构角色。",
    "hasFundStatus": "表示基金具有当前的生命周期状态，与 statusOfFund 互逆。",
    "hasFundStatusRecord": "表示基金具有状态变更的时态记录，与 statusRecordForFund 互逆。",
    "hasFundSubscriptionTerms": "表示基金具有规定认购条件与流程的认购条款。",
    "hasFundSupervisor": "表示基金受到特定基金监管机构的监督管理，与 supervisesFund 互逆。",
    "hasFundTransferAgentRole": "表示基金具有承担基金份额登记代理职责的机构角色。",
    "hasFundUnit": "表示基金发行并具有对应的基金份额，与 issuedByFund 互逆。",
    "hasFundUnitClass": "表示基金具有对应的基金份额类别（A 类、B 类等）。",
    "hasIntendedRiskLevel": "表示基金投资目标设定对应的目标风险等级。",
    "hasInvestmentObjective": "表示基金具有投资目标，与 objectiveOfFund 互逆。",
    "hasInvestmentPolicy": "表示基金具有投资政策，与 policyOfFund 互逆。",
    "hasInvestmentRestriction": "表示基金招募说明书载明相应的基金投资限制，与 definedInProspectus 互逆。",
    "hasInvestmentSpecification": "表示基金具有由投资目标、政策、策略等组成的投资说明体系。",
    "hasInvestor": "表示基金面向或具有特定的基金投资者。",
    "hasLegalStructure": "表示基金具有相应的基金组织形式（法律结构），与 legalStructureOf 互逆。",
    "hasNetAssetValueRecord": "表示基金具有净值事实记录，与 recordForFund 互逆。",
    "hasPortfolioInvestmentStrategy": "表示基金投资组合采用特定的基金投资策略。",
    "hasStatusValue": "表示基金状态记录记录的是某个基金生命周期状态。",
    "hasUnderlyingFund": "表示基金中基金具有投资标的的底层基金，与 underlyingFundOf 互逆。",
    "heldByInvestor": "表示基金份额持仓由某基金投资者持有，与 holdsFundPosition 互逆。",
    "holdsFundPosition": "表示基金投资者持有相应的基金份额持仓。",
    "implementsInvestmentPolicy": "表示基金投资组合执行相应的基金投资组合政策。",
    "isClassifiedBy": "表示基金被某基金分类概念所分类。",
    "issuedByFund": "表示基金份额由其发行基金所发行，与 hasFundUnit 互逆。",
    "issuesFundUnit": "表示基金发行相应的基金份额。",
    "legalStructureOf": "将基金组织形式关联到采用该组织形式的基金，与 hasLegalStructure 互逆。",
    "objectiveOfFund": "将基金投资目标关联到其所属基金。",
    "outlinesObjective": "表示基金招募说明书载明基金投资目标。",
    "playsFundRole": "表示基金参与主体承担相应的基金角色，与 rolePlayedBy 互逆。",
    "policyOfFund": "将基金投资政策关联到其所属基金。",
    "portfolioOfFund": "将基金投资组合关联到其所属基金。",
    "positionInAsset": "表示组合持仓记录所对应的投资资产，与 assetHasPortfolioPosition 互逆。",
    "positionInFundUnit": "表示基金份额持仓所对应的基金份额。",
    "positionOfPortfolio": "表示组合持仓所属的投资组合，与 hasFundPortfolioPosition 互逆。",
    "providesCustodyForFundUnit": "表示基金托管人角色为特定基金份额提供财产托管服务。",
    "realizesFundProduct": "表示基金落地为具体业务形态的基金产品，与 fundProductOf 构成产品化关系。",
    "recordForFund": "将基金净值记录关联到其对应的基金。",
    "redemptionTermsForFund": "将基金赎回条款关联到其所属基金，与 hasFundRedemptionTerms 互逆。",
    "roleInFund": "表示基金角色适用于其所属基金，与 hasFundRole 互逆。",
    "rolePlayedBy": "表示基金角色由某基金参与主体承担，与 playsFundRole 互逆。",
    "statedIn": "表示基金投资目标载明于基金招募说明书。",
    "statusOfFund": "将基金生命周期状态关联到处于该状态的基金，与 hasFundStatus 互逆。",
    "statusRecordForFund": "将基金状态记录关联到其对应的基金。",
    "stipulatesBenchmark": "表示基金投资组合政策规定对应的业绩比较基准。",
    "strategyOfFund": "将基金投资策略关联到其所属基金。",
    "subscriptionTermsForFund": "将基金认购条款关联到其所属基金，与 hasFundSubscriptionTerms 互逆。",
    "supervisesFund": "表示基金监管机构对基金实施监督管理，与 hasFundSupervisor 互逆。",
    "underlyingFundOf": "表示某基金作为底层基金属于某基金中基金，与 hasUnderlyingFund 互逆。",
    "usesInvestmentStrategy": "表示基金采用相应的投资策略。",
}

# ---------------------------------------------------------------- 既有数据属性中文定义（40）
DATA_DEFS = {
    "baseCurrency": "基金记账与净值计算采用的基础币种（如 CNY）。",
    "benchmarkName": "业绩比较基准的名称或描述。",
    "classificationCode": "基金分类概念对应的分类代码值（对应标准品种类别/CFI 编码体系）。",
    "distributionWithReinvestment": "布尔标志：基金分红是否采用红利再投资处理。兼容属性，权威事实由 hasFundDistributionMode（基金分红方式代码）表达。",
    "effectiveFrom": "时态记录（角色任职、状态变更等）的生效日期。",
    "effectiveTo": "时态记录（角色任职、状态变更等）的失效日期，晚于或等于生效日期。",
    "filingDate": "基金完成备案的日期，与备案标志（FLNG_INDC，BD000161）配套。",
    "filingNumber": "基金备案的唯一编号。",
    "fundCode": "唯一区分基金的代码，是以基金合同为基准、代表基金产品法律主体的基金产品编码（标准数据元 FUND_CDE，BD000162）。",
    "fundName": "基金的名称（标准数据元 FUND_NAME，BD000163）。",
    "fundNetAssetValue": "基金资产总值扣除基金负债后的余额，即基金资产净值（标准数据元 FUND_ASET_NV，BD000177）。",
    "fundShortName": "基金的简称（标准数据元 FUND_ABBR，BD000164）。",
    "fundTypeCode": "基金类型的代码值；A-BOX 落地时应映射到基金运作方式、私募基金类型等标准代码表。",
    "fundUnitCode": "基金份额类别的代码，为基金代码下的细分标识。",
    "fundUnitNetAssetValue": "每一份基金份额代表的基金资产净值，又称基金单位资产净值（标准数据元 FUND_SHR_NV，BD000178）。",
    "inceptionDate": "基金成立的日期（标准数据元 BD000061）。",
    "investmentAssetTypeCode": "基金投资资产的类型代码，对应标准品种类别（DBD00026，GB/T 35964 CFI 编码）。",
    "investmentFocus": "基金投资的重点方向、主题或风格描述。",
    "isExchangeTraded": "布尔标志：基金份额是否在交易所上市交易。兼容属性，保留用于数据接入。",
    "isOpenEnded": "布尔标志：基金是否为开放式运作。兼容属性，权威事实由 hasFundOperationMode（基金运作方式代码）表达。",
    "isPrivate": "布尔标志：基金是否为私募（非公开募集）基金。兼容属性，权威事实由基金类（PrivateFund/PublicFund）与 hasPrivateFundType 表达。",
    "jurisdictionCode": "基金适用法域的代码。",
    "maximumInvestmentPercentage": "基金组合投资限制中规定的最高投资比例（对应产品投资比例限制 TLF0000140）。",
    "minimumInvestmentPercentage": "基金组合投资限制中规定的最低投资比例（对应产品投资比例限制 TLF0000140）。",
    "positionAsOfDate": "组合持仓记录对应的统计日期。",
    "positionCurrency": "持仓记录采用的币种。",
    "positionMarketValue": "持仓对应投资资产的市值（对应标准模型组合市值概念）。",
    "positionQuantity": "持仓对应的持有份额数量（对应标准数据元持有份额 HOLD_SHR，BD000308）。",
    "redemptionInAmountAllowed": "布尔标志：基金是否允许按金额（而非份额）赎回。兼容属性，保留用于数据接入。",
    "redemptionMinimumUnits": "基金赎回条款规定的最低赎回份额（与标准赎回份额 REDEM_SHR，BD000293 同源）。",
    "registrationNumber": "基金注册的编号。",
    "riskLevelCode": "基金风险等级代码，值域对应产品风险等级代码表（R1-R5，DBD00028）。",
    "sourceIdentifier": "数据记录来源的标识。",
    "subscriptionMinimumAmount": "基金认购条款规定的最低认购金额。",
    "subscriptionMinimumUnits": "基金认购条款规定的最低认购份额。",
    "terminationDate": "基金终止的日期（标准数据元 CNL_D，BD000241）。",
    "unitCurrency": "基金份额计价采用的币种。",
    "unitQuantity": "基金份额的数量（对应标准统计指标基金份额 FUND_SHR，BD000176）。",
    "valuationCurrency": "基金净值计算采用的估值币种。",
    "valuationDate": "基金净值的估值日期。",
}

# ---------------------------------------------------------------- 类 ↔ 标准代码概念 closeMatch
CLOSE_MATCH = [
    ("OpenEndedFund", "FundOperationModeOpenEnded"),
    ("ClosedEndedFund", "FundOperationModeClosedEnded"),
    ("ContractualFundStructure", "FundOrganizationFormContractual"),
    ("CorporateFundStructure", "FundOrganizationFormCorporate"),
    ("PartnershipFundStructure", "FundOrganizationFormPartnership"),
    ("FundCashDistributionPolicy", "FundDistributionModeCashDividend"),
    ("FundReinvestmentPolicy", "FundDistributionModeReinvestment"),
]

# ---------------------------------------------------------------- 兼容属性 changeNote
COMPAT_NOTES = {
    "isOpenEnded": "v0.5 兼容属性：基金运作方式的权威事实由 hasFundOperationMode（基金运作方式代码，JR/T 0304.2 DBD00029）表达；本布尔属性保留用于数据接入与旧数据兼容。",
    "isPrivate": "v0.5 兼容属性：基金是否私募的权威事实由基金类（PrivateFund/PublicFund）与 hasPrivateFundType（私募基金类型代码）表达；本布尔属性保留用于数据接入与旧数据兼容。",
    "isExchangeTraded": "v0.5 兼容属性：保留用于数据接入；交易所交易属性建议通过基金份额类别与交易所上市信息表达。",
    "distributionWithReinvestment": "v0.5 兼容属性：分红处理方式的权威事实由 hasFundDistributionMode（基金分红方式代码，JR/T 0304.2 DBD00036）表达。",
    "redemptionInAmountAllowed": "v0.5 兼容属性：保留用于数据接入；按金额赎回能力建议由基金份额类别的申赎条款（FundRedemptionTerms）表达。",
}

# ---------------------------------------------------------------- 评审升级公理
EXTRA_AXIOMS = """
# 概念层边界
cnfo:FundObject owl:disjointWith cnfo:FundParty .
cnfo:ConceptNature rdfs:comment "元概念层分类，不作为基金业务主体或业务对象实例化；用于说明基金概念的法定、监管或市场惯用性质。"@zh .
cnfo:FundUnitInvestmentAsset skos:scopeNote "本类实例是被投基金份额的引用性投资资产代理；其发行基金与份额币种仍应通过 issuedByFund、unitCurrency 保持可追溯。"@zh .

# 关键分类轴的等价定义：代码事实可以反向推导基金分类
cnfo:OpenEndedFund owl:equivalentClass [
    a owl:Class ;
    owl:intersectionOf (
        cnfo:Fund
        [ a owl:Restriction ; owl:onProperty cnfo:hasFundOperationMode ; owl:hasValue cnfc:FundOperationModeOpenEnded ]
    )
] .
cnfo:ClosedEndedFund owl:equivalentClass [
    a owl:Class ;
    owl:intersectionOf (
        cnfo:Fund
        [ a owl:Restriction ; owl:onProperty cnfo:hasFundOperationMode ; owl:hasValue cnfc:FundOperationModeClosedEnded ]
    )
] .
cnfo:PublicFund owl:equivalentClass [
    a owl:Class ;
    owl:intersectionOf (
        cnfo:Fund
        [ a owl:Restriction ; owl:onProperty cnfo:isPrivate ; owl:hasValue false ]
    )
] .
cnfo:PrivateFund owl:equivalentClass [
    a owl:Class ;
    owl:intersectionOf (
        cnfo:Fund
        [ a owl:Restriction ; owl:onProperty cnfo:isPrivate ; owl:hasValue true ]
    )
] .
cnfo:ExchangeTradedFund owl:equivalentClass [
    a owl:Class ;
    owl:intersectionOf (
        cnfo:OpenEndedFund
        [ a owl:Restriction ; owl:onProperty cnfo:isExchangeTraded ; owl:hasValue true ]
    )
] .
cnfo:FundOfFunds owl:equivalentClass [
    a owl:Class ;
    owl:intersectionOf (
        cnfo:Fund
        [ a owl:Restriction ; owl:onProperty cnfo:hasUnderlyingFund ; owl:someValuesFrom cnfo:Fund ]
    )
] .

# 角色承担主体与基金的快捷属性链
cnfo:hasFundParty owl:propertyChainAxiom ( cnfo:hasFundRole cnfo:rolePlayedBy ) .
cnfo:hasFundManager owl:propertyChainAxiom ( cnfo:hasFundManagerRole cnfo:rolePlayedBy ) .
cnfo:hasFundDepositary owl:propertyChainAxiom ( cnfo:hasFundDepositaryRole cnfo:rolePlayedBy ) .

# 份额级净值向基金级净值关系的可推导链接；避免把 recordForFundUnit 错当成 recordForFund 的子属性
cnfo:recordForFund owl:propertyChainAxiom ( cnfo:recordForFundUnit cnfo:issuedByFund ) .

# 单值业务事实的 OWL 声明，与 SHACL maxCount 1 对齐
cnfo:baseCurrency a owl:FunctionalProperty .
cnfo:unitCurrency a owl:FunctionalProperty .
cnfo:fundCode a owl:FunctionalProperty .
cnfo:fundUnitCode a owl:FunctionalProperty .
cnfo:accountNumber a owl:FunctionalProperty .
cnfo:hasFundStatus a owl:FunctionalProperty .

# 业务对象的标识键；强合并风险由数据质量层和发布前检查承担
cnfo:Fund owl:hasKey ( cnfo:fundCode ) .
cnfo:FundUnit owl:hasKey ( cnfo:fundUnitCode cnfo:issuedByFund ) .
cnfo:FundAccount owl:hasKey ( cnfo:accountNumber ) .

# 正交分类轴与文档/角色类型互斥
[] a owl:AllDisjointClasses ;
   owl:members ( cnfo:EquityFund cnfo:BondFund cnfo:HybridFund cnfo:MoneyMarketFund ) .
[] a owl:AllDisjointClasses ;
   owl:members ( cnfo:FundContract cnfo:FundProspectus cnfo:FundPeriodicReport cnfo:FundFilingDocument ) .
[] a owl:AllDisjointClasses ;
   owl:members ( cnfo:FundManagerRole cnfo:FundDepositaryRole cnfo:FundDistributorRole cnfo:FundRegistrarRole ) .

# 业绩记录的锚定约束，指标完整性仍由 SHACL 根据数据场景校验
cnfo:FundPerformanceRecord rdfs:subClassOf
    [ a owl:Restriction ; owl:onClass cnfo:Fund ; owl:onProperty cnfo:performanceForFund ; owl:qualifiedCardinality 1 ],
    [ a owl:Restriction ; owl:onProperty cnfo:performancePeriodStart ; owl:cardinality 1 ],
    [ a owl:Restriction ; owl:onProperty cnfo:performancePeriodEnd ; owl:cardinality 1 ] .
"""


# ---------------------------------------------------------------- 生成器
def _q(name: str) -> str:
    return f"cnfo:{name}"


def gen_block() -> str:
    lines = []
    lines.append("# ============================================================")
    lines.append("# V0.5.3 评审升级：语义基础层 + 属性关系契约 + 分类公理（生成自 tools/v05_defs.py，勿手改）")
    lines.append("# 新增抽象类")
    lines.append("# ============================================================")
    for c in NEW_CLASSES:
        annot = c.get("annotate", ())
        lines.append(f"{_q(c['name'])} a owl:Class ;")
        lines.append(f'    rdfs:label "{c["label"]}"@zh ;')
        lines.append(f"    rdfs:subClassOf cnfo:{c['parent']} ;")
        if annot:
            lines.append(f'    skos:definition "{c["def_"]}"@zh ;')
            for i, (prop, val) in enumerate(annot):
                tail = " ;" if i < len(annot) - 1 else ""
                lines.append(f'    cnfom:{prop} "{val}"{tail}')
        else:
            lines.append(f'    skos:definition "{c["def_"]}"@zh')
        lines.append(" .")
        lines.append("")

    lines.append("# 新增对象/数据属性")
    for p in NEW_PROPS:
        lines.append(f"{_q(p['name'])} a owl:{'ObjectProperty' if p['type'] == 'obj' else 'DatatypeProperty'} ;")
        lines.append(f'    rdfs:label "{p["label"]}"@zh ;')
        lines.append(f"    rdfs:domain cnfo:{p['domain']} ;")
        rng = p["range"]
        if rng in ("string", "date", "decimal", "boolean", "integer"):
            lines.append(f"    rdfs:range xsd:{rng} ;")
        else:
            lines.append(f"    rdfs:range cnfo:{rng} ;")
        if p.get("inverse"):
            lines.append(f"    owl:inverseOf cnfo:{p['inverse']} ;")
        if p.get("subproperty"):
            lines.append(f"    rdfs:subPropertyOf cnfo:{p['subproperty']} ;")
        lines.append(f'    skos:definition "{p["def_"]}"@zh .')
        lines.append("")

    lines.append("# 既有对象属性中文定义（91）")
    for name in sorted(OBJ_DEFS):
        lines.append(f'{_q(name)} skos:definition "{OBJ_DEFS[name]}"@zh .')
    lines.append("")
    lines.append("# 既有数据属性中文定义（40）")
    for name in sorted(DATA_DEFS):
        lines.append(f'{_q(name)} skos:definition "{DATA_DEFS[name]}"@zh .')
    lines.append("")

    lines.append("# 类 ↔ 标准代码概念 closeMatch")
    for cls, concept in CLOSE_MATCH:
        lines.append(f"cnfo:{cls} skos:closeMatch cnfc:{concept} .")
    lines.append("")

    lines.append("# 兼容属性 changeNote")
    for name in sorted(COMPAT_NOTES):
        lines.append(f'{_q(name)} skos:changeNote "{COMPAT_NOTES[name]}"@zh .')
    lines.append("")
    lines.append("# 评审升级：等价类、属性链、键约束与不相交公理")
    lines.append(EXTRA_AXIOMS.rstrip())
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(gen_block(), encoding="utf-8")
    print(f"new classes={len(NEW_CLASSES)} new props={len(NEW_PROPS)}")
    print(f"object defs={len(OBJ_DEFS)} data defs={len(DATA_DEFS)} closeMatch={len(CLOSE_MATCH)} compat={len(COMPAT_NOTES)}")


if __name__ == "__main__":
    main()
