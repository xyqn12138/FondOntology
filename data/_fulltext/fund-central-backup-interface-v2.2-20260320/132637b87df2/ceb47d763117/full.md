基金行业数据

集中备份接口规范

（Ver2.2）

# 目录

目录	2

修订说明	4

1. 总则	6

2. 术语定义	6

3. 基本要求	9

4. 数据接口	10

4.1. 信息格式	10

4.2. 数据报送机制	11

4.3. 接口文件名定义	13

4.4. TA业务代码	15

4.5. 业务数据项	16

4.5.1. 开户确认业务101	16

4.5.2. 销户确认业务102	18

4.5.3. 账户资料修改确认业务103	19

4.5.4. 增加交易账户确认108、撤销交易账户确认109	21

4.5.5. 变更交易账户确认158	22

4.5.6. 认购业务数据项120	22

4.5.7. 认购结果业务数据项130	23

4.5.8. 申购业务数据项122	25

4.5.9. 定期定额申购业务数据项139	27

4.5.10. ETF一次申购业务数据项191	29

4.5.11. ETF二次申购业务数据项192	30

4.5.12. 赎回业务数据项124/定时定额赎回163	32

4.5.13. 强制赎回业务数据项142、基金清盘150、基金终止151	35

4.5.14. ETF一次赎回业务数据项193	38

4.5.15. ETF二次赎回业务数据项194	40

4.5.16. 预约赎回业务数据项125	42

4.5.17. 转托管业务数据项126	44

4.5.18. 转托管入业务数据项127	46

4.5.19. 转托管出业务数据项128	47

4.5.20. 设置分红方式业务数据项129	49

4.5.21. 份额冻结业务数据项131（包含质押业务）	50

4.5.22. 份额解冻业务数据项132（包含解质押业务）	51

4.5.23. 非交易过户133（包含份额转让业务）、快速过户198、非交易过户出135、非交易过户入134	52

4.5.24. 基金转换业务数据项136	53

4.5.25. 基金转换出业务数据项138	55

4.5.26. 基金转换入业务数据项137	57

4.5.27. 分红业务数据项143	58

4.5.28. 强增业务数据项144	60

4.5.29. 强减业务数据项145	61

4.5.30. 开通定期定额协议业务数据项159	62

4.5.31. 撤销定期定额协议业务数据项160	64

4.5.32. 变更定期定额协议业务数据项161	64

4.5.33. 募集失败149	65

4.6. 文件汇总数据项	67

4.6.1. 账户确认92/Z2、账户增量对账D2/U2、账户全量对账Q2/S2	67

4.6.2. 交易确认94(Z4)	70

4.6.3. 份额对帐95(Z5/Q5/S5)	76

4.6.4. 分红信息96(Z6)	78

4.6.5. 基金TA参数(T1/TM)	80

4.6.6. 基金运作信息(T2/TN)	84

4.6.7. 个人反洗钱信息(X1/XA/X6/XB)	85

4.6.8. 机构反洗钱信息(X3/XC/X8/XD)	88

4.6.9. 跨境基金计税参数(G1)	93

5. 附录A接口文件规范数据类型定义	94

6. 附录B数据字典	95

# 修订说明

<table>
<tr><td><p>日期</p></td><td><p>变更说明</p></td><td><p>修订者</p></td></tr>
<tr><td><p>2016-08-08</p></td><td><p>在原《开放式基金TA数据集中备份接口规范（TXT）》基础上增加了基金TA参数、基金运作信息、跨境基金计税参数文件。</p></td><td><p>陈鸿鹄</p></td></tr>
<tr><td><p>2024-02-01</p></td><td><p>根据交换协议新版本修订内容更新。</p><p>1、数据字典修订：增加证件类型“港澳台居民居住证”，修改证件类型“护照”为“中国护照”。分红类型“专户到期处理”改名“清盘资产分配”。“强行赎回原因”字段值域增加“到期清盘”。“机构类型”扩长并增加银行子公司、保险子公司,修改产品类投资者“209、210、211”的中文描述。扩长“通信地址、投资人户名、投资人户名简称、（法人、经办人）姓名、证件类型（含法人、经办人）、证件号码（含法人、经办人）、工作单位名称、投资人手机号码、单位电话、住址电话、传真号码、职业代码、电话号码、年收入、投资者产品代码、投资人收款银行账户（户名、账号、开户行)、投资人在销售人处用于交易的资金账号、控股股东、实际控制人、注册登记人代码、对方TA代码、托管人代码、基金管理人、管理人代码、基金发起人、基金名称、基金简称、注册登记人名称、基金管理人名称、基金管理人网站网址、基金公司客服电话、销售人名称”。“手续费、代理费、过户费、其它费用1、交易确认费用合计、最少收费、基金账户利息金额、分红费用合计、分红手续费、经手费”扩长为N（16,2）。将“（原）申请单编号、（对方）交易账号、（原）TA确认流水号、业务代码、明细标志、目标基金代码”改为字符型。将“（目标）基金单位净值、（目标基金）交易价格、基金面值、累计基金单位净值、保本净值、成本价、累计单位分红、配售比例、赎回费归基金资产比例”扩为N（16,8）。</p><p>2、92文件中增加“证件有效日期、机构经办人身份证件有效日期、机构法人身份证件有效日期、客户风险等级、辅助身份证明文件类型、号码、有效期”，增加“IP地址、MAC地址、国际移动设备识别码、通用唯一识别码、最后修改日期、投顾机构代码、账户特征值、开户日期、详细信息”。</p><p>3、交易确认94文件增加说明，并增加“违约金、违约金归基金资产金额、惩罚性费用、后端收费总额、业绩补偿、退款金额、带走收益标志、强制赎回类型、过户原因、IP地址、MAC地址、国际移动设备识别码、通用唯一识别码、投资人收款银行账户户名、投资人收款银行账户账号、投资人收款银行账户开户行、详细信息”字段，删除“业绩报酬正负、后收手续费”字段。</p><p>3、份额对账95文件增加“明细标志”等说明，增加“新增收益”、“新增收益正负”、“最后修改日期”字段。</p><p>4、分红信息中增加计费人、分红单位、是否注册登记人发起业务标志、业绩补偿、分红类型，删除业绩报酬正负。</p><p>5、T1文件增加“赎回封闭方式、封闭期长度、封闭期单位、侧袋标志、侧袋原代码、收费类别、基金面值、基金特征值、内地代理人代码、净值发送模式、基金状态2、后收费代码、批文号、非公募产品投向分类”字段，删除“是否QDII基金”，调整“基金类型”选项。T2文件增加“收费类别”字段。</p><p>6、增加108业务数据项。</p><p>7、149业务名称修改为“募集失败”。</p><p>8、92文件改名为账户确认，新增账户增量对账文件D2，并对114业务及新增的115业务进行说明。新增账户柜台修改（ZGT）业务,删除基金账户冻结/解冻、基金账户卡挂失/解挂、预约认购、预约申购、认购配售业务。</p><p>9、报送机制章节进行了补充说明。</p><p>10、业务代码194/126/131/136/137/138增加“TA的原确认日期”字段，业务代码125/126/127/128/131/136/137/138增加“原TA确认流水号”字段，业务代码126/131/132/133/136增加“总TA确认流水号”字段，业务代码144/145增加“明细标志”字段。</p><p>11、增加反洗钱信息文件。</p><p>12、各文件增加预留字段。</p></td><td><p>陈鸿鹄</p></td></tr>
<tr><td><p>2026-01-09</p></td><td><p>数据处理规则要求数值型数据不允许出现负数。赎回业务（124）增加“强制赎回类型”字段，并扩展字典项‘个人养老金提前赎回’。使用‘其它费2’表示返还的销售服务费。</p></td><td><p>陈鸿鹄</p></td></tr>
</table>

# 1. 总则

为实现基金行业数据（含公募、私募产品）的集中备份，促进基金业整体数据安全与行业发展，制定此规范。

本规范包含信息格式、接口文件名定义、业务数据项、文件汇总数据项等章节。基金TA（或管理人）按照“文件汇总数据项”章节报送TXT文件，其中针对不同业务各字段是否必填，参照“业务数据项”章节。各字段的含义，除专门说明的以外，均参照《中央数据交换平台开放式基金业务数据交换协议》。

本规范适用对象包括基金TA、管理人和其他相关参与人。

# 2. 术语定义

2.1基金业务当事人

基金管理人—基金管理人是指依法从事投资基金管理的基金管理公司。

基金托管人—基金托管人是指依法保管基金资产、监督管理人投资活动的机构。

注册（过户）登记人（或称TA）—负责基金投资人账户保管、交易记录保存、代理分红、投资人账户报告、登记基金份额等服务的机构。

基金持有人—基金持有人是指持有证券投资基金份额的投资人。

基金销售人—销售基金的法人，包括基金管理人（直销商）以及经中国证监会及其派出机构注册的其他机构（代销商）。

2.2业务种类

开户—基金投资人申请设立基金数量账户和资金账户的业务。

注册（过户）登记基金账号（或称TA基金账号）—注册登记人为基金投资人设立的基金账户，用于记录和保存持有人的基金单位数量。

直销—基金管理人直接面向基金投资人销售基金。

代销—基金管理人通过协议委托另一方销售其所管理的基金。

认购—投资人在基金募集期间申请购买该基金的行为。

申购—指基金合同生效后的开放期内，投资人根据基金合同和招募说明书（如有）的规定申请购买基金份额的行为。基金管理人接到投资人的购买申请时，应按当日基金份额净资产加减必要费用予以成交，基金托管人按规定与基金管理人办理交割与清算手续，注册登记人增加投资人账户的基金数量和基金的资产。

赎回—指基金合同生效后的开放期内，基金持有人按基金合同和招募说明书（如有）规定的条件要求将基金份额兑换为现金的行为。接到基金持有人赎回请求时，基金管理人应按当日基金份额净资产加减必要费用予以成交，基金托管人按规定与基金管理人办理交割与清算手续，在规定期限内向基金持有人支付赎回资金，注册登记人减少基金持有人账户基金数量和基金的资产。

巨额赎回—在基金的单个开放日，基金净赎回申请超过该基金总份额的一定比例时，就是巨额赎回。根据《公开募集证券投资基金运作管理办法》（2014年7月7日证监会令第104号）的规定，这一比例为10%。

预约赎回—基金持有人为给基金管理人一定的时间办理赎回业务而提前发出的在未来某日赎回的申请。

分红—按基金契约的规定，基金管理人在每个会计年度将基金运作所得收益按一定的比例分配给基金持有人的行为。

登记日—登记基金持有人按其所持基金享受基金分红权力的时点。

红利发放日—向基金持有人拨付红利款项的日期。

红利再投资—基金持有人可以将所持基金分得的现金红利自动申请转为持有该基金单位的投资活动，基金管理人一般愿意提供这种服务，鼓励投资人继续持有基金资产。

非交易过户—基金赠与、继承、协助执行司法判决等有双方参与且涉及基金单位数量变化的过户业务。

基金转换—基金管理人向基金持有人提供的一种服务，即将基金持有人的某种基金转换为同一基金管理人管理的另一种基金的服务。

2.3基金信息

基金单位资产净值—基金单位资产净值应当按照开放日闭市后基金资产净值除以当日基金单位的余额数量计算。具体计算方法在基金契约和招募说明书中载明。

申购费—指投资人申购基金单位所需支付的费用。申购费可在投资人申购基金单位时收取，即前收申购费；或在投资人卖出基金单位时收取，即后收申购费。

赎回费—指投资人卖出基金单位时所支付的费用。

账户管理费—账户管理费指基金管理人向投资人收取的用于管理维护投资人基金账户的费用。

注册（过户）登记费—注册（过户）登记费用由基金管理人根据“注册登记代理协议”向注册登记代理人支付。注册（过户）登记代理人可对以下业务内容进行收费：开户、认购、申购、赎回的基金单位登记、过户和其他有关投资人账户活动的业务项目。

尾随佣金—是基金管理人给与基金的代理销售人的销售业绩报酬，尾随佣金一般在第13个月起按所其管理的基金资产的季度平均余额计算，按季支付。

手续费—代理销售人向基金投资人、持有人收取的业务经办费用。

# 3. 基本要求

3.1数据类型定义

本规范使用的数据类型定义如下：

<table>
<tr><td><p>标识符</p></td><td><p>类型</p></td></tr>
<tr><td><p>C</p></td><td><p>字符型</p></td></tr>
<tr><td><p>A</p></td><td><p>数字字符型，限于0—9</p></td></tr>
<tr><td><p>N</p></td><td><p>数值型，并可参与数值计算</p></td></tr>
<tr><td><p>TEXT</p></td><td><p>不定长文本</p></td></tr>
</table>

3.2数据填写要求

（1）

采用文本文件定长记录方式，每行一条完整记录，换行必须用回车（ODH）及换行（OAH）字符。

（2）对于数值型数据，左补零右对齐，不得填写负数。带有小数点的数值型数据，填写时仅填写数字，不填写小数点。

（3）对于字符型和数字字符型数据，右补空格左对齐。字符型数据不区分大小写。

3.3加密

对通过公网进行传输的敏感数据进行加密是非常必要的，本规范强烈建议对这些数据进行加密处理。

加密方法的选择由进行数据交换的各方协商确定。

# 4. 数据接口

## 4.1. 信息格式

每个（次）交换的信息包括三个部分：信息头，信息体，信息尾。采用文件交换方式的详细约定采用附件A中的格式。

信息头：表示一次数据交换的开始，它给出本次数据交换的信息提要。其内容列如下：

<table>
<tr><td><p>名称</p></td><td><p>说明</p></td></tr>
<tr><td><p>信息头标识</p></td><td><p>用以标明该文件的格式类型</p></td></tr>
<tr><td><p>协议版本号</p></td><td></td></tr>
<tr><td><p>信息创建人</p></td><td><p>TA/基金管理人的代码</p></td></tr>
<tr><td><p>信息接收人</p></td><td><p>00</p></td></tr>
<tr><td><p>传送发生日期</p></td><td><p>传送发生日期</p></td></tr>
</table>

信息体：包括数据交换的内容。

<table>
<tr><td><p>名称</p></td><td><p>说明</p></td></tr>
<tr><td><p>汇总表号</p></td><td><p>000</p></td></tr>
<tr><td><p>文件类型代码</p></td><td></td></tr>
<tr><td><p>发送人</p></td><td></td></tr>
<tr><td><p>接收人</p></td><td></td></tr>
<tr><td><p>字段数</p></td><td><p>表示该数据文件的构成字段数</p></td></tr>
<tr><td><p>字段名1</p></td><td></td></tr>
<tr><td><p>…</p></td><td></td></tr>
<tr><td><p>字段名n</p></td><td></td></tr>
<tr><td><p>记录数</p></td><td><p>该数据文件包含的数据记录数</p></td></tr>
<tr><td><p>记录1</p></td><td></td></tr>
<tr><td><p>记录２</p></td><td></td></tr>
<tr><td><p>记录３</p></td><td></td></tr>
<tr><td><p>…</p></td><td></td></tr>
<tr><td><p>记录M</p></td><td></td></tr>
</table>

信息尾：表示一次数据交换的结束。

## 4.2. 数据报送机制

1. 	公募基金（含证券公司大集合）报送数据说明：

1） 每日报送增量数据（92/D2/94/95/96/X1/X3文件）和全量数据（T1/T2文件），如有跨境销售的基金，还需报送全量G1文件。增量指当日新增或变动的数据信息。

2） 定期报送全量数据（Q2/Q5/X6/X8文件，格式同92/95/X1/X3，内容为全量，这些文件须全部同时报送，不能只报其中几个），且当日需同时报送92/D2/94/95/96/X1/X3增量数据和T1/T2全量数据。

2. 	私募基金报送数据说明：

1） 每日报送增量数据（Z2/U2/Z4/Z5/Z6/XA/XC文件，格式同92/D2/94/95/96/X1/X3文件）和全量数据（TM/TN，格式同T1/T2）。增量指自上次报送数据之后新增或变动的数据信息。

2） 定期报送全量数据（S2/S5/XB/XD文件，格式同92/95/X1/X3，内容为全量，这些文件须同时报送，不能只报其中几个），且当日需同时报送Z2/U2/Z4/Z5/Z6/XA/XC增量数据和TM/TN全量数据。

3. 	说明：

1） 	若TA既有公募也有私募基金，且某日需同时报送时，可在同一批次数据（同一索引文件）中包含92/D2/94/95/96/X1/X3/T1/T2/Q2/Q5/X6/X8和Z2/U2/Z4/Z5/Z6/XA/XC/TM/TN/S2/S5/XB/XD文件。

2） 	若TA公募和私募基金使用同一套账户体系，则仅报送公募账户数据，私募账户报送空文件（同样适用于反洗钱信息）。

3） 	每个数据申报日，参与人即使当日无数据，也应报送索引文件，表示当日已报送。

4） 	管理人自建TA需报送数据，但分TA无需报送（由中国结算TA代为报送）。若存在一个产品部分由自建TA登记、部分由中国结算TA登记的情况，自建TA应报送其登记的那部分数据。

5） 	TA要保证先上传数据文件，然后再上传索引文件，要保证索引文件中文件列表与实际上传文件个数相同。

6） 	若TA报送的文件通过格式检查，集中备份系统即时返回“文件名.ACC”文件；若未通过格式检查，返回“文件名.ERR”文件，并在文件内容中说明原因。若TA报送了未约定的文件,集中备份系统返回“文件名.DEN”文件。TA每日报送数据后，若未收到“文件名.ACC”文件，应及时进行检查。

7） 	单个数据文件过大时，应拆为多个文件发送，并在“.TXT”前面增加“\_顺序号”，顺序号为三位长度。索引文件名不变，但内容中的数据文件名，也应有“顺序号”。

8） 	单个文件若大于100M，要求采用ZIP（或BZ2）格式进行压缩,不支持其他压缩格式，不允许分卷压缩。压缩文件名称应保持与原文件名称一致，后缀由原TXT改为ZIP（或BZ2）。注意索引文件中列出的文件名仍使用原‘TXT’文件名。

## 4.3. 接口文件名定义

接口文件名中存在下列变量：

1. gg为证监会分配的TA编码, 对于中国结算TA为“98”或“99”，“98”代表深市，“99”代表沪市; 00为集中备份系统代码。

2. 92/D2/94/95/96/T1/T2/X1/X3文件，要求每交易日21点前传送上一交易日的登记数据（举例：T日申请，T+1中午确认，T+2日21点前报送T+1确认后的数据），yyyymmdd赋值为上一交易日。 私募基金报送时间要求相同。

3. G1文件，要求每日早上9点前传送上一交易日份额登记完成后的计税参数信息，yyyymmdd赋值为上一交易日。

4. 接口文件名如下：

<table>
<tr><td><p>接口</p></td><td><p>发送方</p></td><td><p>文件名</p></td><td><p>说明</p></td></tr>
<tr><td><p>账户确认、账户对账（增量、全量）</p></td><td><p>TA</p></td><td><p>OFD_gg_00_yyyymmdd_92.TXT(公募增量，账户确认)</p><p>OFD_gg_00_yyyymmdd_D2.TXT(公募增量，账户对账)</p><p>OFD_gg_00_yyyymmdd_Z2.TXT(私募增量，账户确认)</p><p>OFD_gg_00_yyyymmdd_U2.TXT(私募增量，账户对账)</p><p>OFD_gg_00_yyyymmdd_Q2.TXT(公募全量，账户对账)</p><p>OFD_gg_00_yyyymmdd_S2.TXT(私募全量，账户对账)</p></td><td></td></tr>
<tr><td><p>交易确认</p></td><td><p>TA</p></td><td><p>OFD_gg_00_yyyymmdd_94.TXT(公募增量)</p><p>OFD_gg_00_yyyymmdd_Z4.TXT(私募增量)</p></td><td></td></tr>
<tr><td><p>份额对账</p></td><td><p>TA </p></td><td><p>OFD_gg_00_yyyymmdd_95.TXT(公募增量)</p><p>OFD_gg_00_yyyymmdd_Z5.TXT(私募增量)</p><p>OFD_gg_00_yyyymmdd_Q5.TXT(公募全量)</p><p>OFD_gg_00_yyyymmdd_S5.TXT(私募全量)</p></td><td></td></tr>
<tr><td><p>分红信息</p></td><td><p>TA</p></td><td><p>OFD_gg_00_yyyymmdd_96.TXT(公募增量)</p><p>OFD_gg_00_yyyymmdd_Z6.TXT(私募增量)</p></td><td></td></tr>
<tr><td><p>基金TA参数</p></td><td><p>TA</p></td><td><p>OFD_gg_00_yyyymmdd_T1.TXT(公募全量)</p><p>OFD_gg_00_yyyymmdd_TM.TXT(私募全量)</p></td><td></td></tr>
<tr><td><p>基金运作信息</p></td><td><p>TA</p></td><td><p>OFD_gg_00_yyyymmdd_T2.TXT(公募全量)</p><p>OFD_gg_00_yyyymmdd_TN.TXT(私募全量)</p></td><td></td></tr>
<tr><td><p>个人反洗钱信息</p></td><td><p>TA</p></td><td><p>OFD_gg_00_yyyymmdd_X1.TXT(公募增量)</p><p>OFD_gg_00_yyyymmdd_XA.TXT(私募增量)</p><p>OFD_gg_00_yyyymmdd_X6.TXT(公募全量)</p><p>OFD_gg_00_yyyymmdd_XB.TXT(私募全量)</p></td><td></td></tr>
<tr><td><p>机构反洗钱信息</p></td><td><p>TA</p></td><td><p>OFD_gg_00_yyyymmdd_X3.TXT(公募增量)</p><p>OFD_gg_00_yyyymmdd_XC.TXT(私募增量)</p><p>OFD_gg_00_yyyymmdd_X8.TXT(公募全量)</p><p>OFD_gg_00_yyyymmdd_XD.TXT(私募全量)</p></td><td></td></tr>
<tr><td><p>索引文件</p></td><td><p>TA</p></td><td><p>OFI_gg_00_yyyymmdd.TXT</p></td><td></td></tr>
<tr><td><p>跨境基金计税参数</p></td><td><p>TA或管理人</p></td><td><p>OFD_gg_00_yyyymmdd_G1.TXT</p></td><td></td></tr>
<tr><td><p>索引文件</p></td><td><p>TA或管理人</p></td><td><p>OFB_gg_00_yyyymmdd.TXT</p></td><td></td></tr>
</table>

## 4.4. TA业务代码

每日报送的数据是以上日申请数据为基础的确认数据，对于账户和交易类文件，涉及的业务代码都填写确认业务代码。

对于接口文档中无法填写和提供的字段，可以填写为空。

表1　 TA支持业务表

<table>
<tr><td><p>业务名称</p></td><td><p>申请业务代码</p></td><td><p>确认业务代码</p></td></tr>
<tr><td><p>开户</p></td><td><p>001</p></td><td><p>101</p></td></tr>
<tr><td><p>销户</p></td><td><p>002</p></td><td><p>102</p></td></tr>
<tr><td><p>账户资料修改</p></td><td><p>003</p></td><td><p>103</p></td></tr>
<tr><td><p>增加交易账户</p></td><td><p>008</p></td><td><p>108</p></td></tr>
<tr><td><p>撤销交易账户</p></td><td><p>009</p></td><td><p>109</p></td></tr>
<tr><td><p>变更交易账户</p></td><td><p>058</p></td><td><p>158</p></td></tr>
<tr><td><p>增量、全量账户对账</p></td><td></td><td><p>114（基金账户对账）、115（交易账户对账）</p></td></tr>
<tr><td><p>账户柜台修改</p></td><td></td><td><p>ZGT</p></td></tr>
<tr><td><p>认购</p></td><td><p>020</p></td><td><p>120</p></td></tr>
<tr><td><p>申购</p></td><td><p>022</p></td><td><p>122</p></td></tr>
<tr><td><p>赎回</p></td><td><p>024</p></td><td><p>124</p></td></tr>
<tr><td><p>定时定额赎回</p></td><td><p>063</p></td><td><p>163</p></td></tr>
<tr><td><p>预约赎回</p></td><td><p>025</p></td><td><p>125</p></td></tr>
<tr><td><p>转销售人/机构</p></td><td><p>026</p></td><td><p>126</p></td></tr>
<tr><td><p>转销售人/机构转入</p></td><td><p>027</p></td><td><p>127</p></td></tr>
<tr><td><p>转销售人/机构转出</p></td><td><p>028</p></td><td><p>128</p></td></tr>
<tr><td><p>设置分红方式</p></td><td><p>029</p></td><td><p>129</p></td></tr>
<tr><td><p>认购结果</p></td><td></td><td><p>130</p></td></tr>
<tr><td><p>基金份数冻结</p></td><td><p>031</p></td><td><p>131</p></td></tr>
<tr><td><p>基金份数解冻</p></td><td><p>032</p></td><td><p>132</p></td></tr>
<tr><td><p>非交易过户</p></td><td><p>033</p></td><td><p>133</p></td></tr>
<tr><td><p>非交易过户入</p></td><td><p>034</p></td><td><p>134</p></td></tr>
<tr><td><p>非交易过户出</p></td><td><p>035</p></td><td><p>135</p></td></tr>
<tr><td><p>基金转换</p></td><td><p>036</p></td><td><p>136</p></td></tr>
<tr><td><p>基金转换转入</p></td><td><p>037</p></td><td><p>137</p></td></tr>
<tr><td><p>基金转换转出</p></td><td><p>038</p></td><td><p>138</p></td></tr>
<tr><td><p>定时定额申购</p></td><td><p>039</p></td><td><p>139</p></td></tr>
<tr><td><p>强制赎回</p></td><td><p>142</p></td><td><p>142</p></td></tr>
<tr><td><p>红利发放</p></td><td><p>143</p></td><td><p>143</p></td></tr>
<tr><td><p>强行调增</p></td><td><p>044</p></td><td><p>144</p></td></tr>
<tr><td><p>强行调减</p></td><td><p>045</p></td><td><p>145</p></td></tr>
<tr><td><p>募集失败</p></td><td><p>149</p></td><td><p>149</p></td></tr>
<tr><td><p>基金清盘</p></td><td><p>150</p></td><td><p>150</p></td></tr>
<tr><td><p>基金终止</p></td><td><p>151</p></td><td><p>151</p></td></tr>
<tr><td><p>定时定额申购开通</p></td><td><p>059</p></td><td><p>159</p></td></tr>
<tr><td><p>定时定额申购撤销</p></td><td><p>060</p></td><td><p>160</p></td></tr>
<tr><td><p>定时定额申购修改</p></td><td><p>061</p></td><td><p>161</p></td></tr>
<tr><td><p>ETF申购</p></td><td><p>091</p></td><td><p>191、192</p></td></tr>
<tr><td><p>ETF赎回</p></td><td><p>093</p></td><td><p>193、194</p></td></tr>
<tr><td><p>快速过户</p></td><td><p>098</p></td><td><p>198</p></td></tr>
</table>

## 4.5. 业务数据项

业务数据文件中，对于各项业务所需要的字段。该字段“是否必需”如果为‘Y’，表示在该业务中该字段为关键字段，必须赋值；如果为‘N’表示该字段允许为空。

### 4.5.1. 开户确认业务101

若销售机构申报的是基金账户开户业务，则对应报送101业务（无论该基金账户是否已经开立过）。若销售机构申报的是新增交易账户业务，则对应报送108业务，不能报送101业务。

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否必需</p></td></tr>
<tr><td><p>4</p></td><td><p>Address</p></td><td><p>C</p></td><td><p>300</p></td><td><p>通讯地址</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>5</p></td><td><p>InstReprIDCode</p></td><td><p>C</p></td><td><p>40</p></td><td><p>法人代表身份证件代码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>6</p></td><td><p>InstReprIDType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>法人代表证件类型</p></td><td><p>参考数据字典“证件类型”中的个人部分</p></td><td><p>N</p></td></tr>
<tr><td><p>7</p></td><td><p>InstReprName</p></td><td><p>C</p></td><td><p>60</p></td><td><p>法人代表姓名</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>23</p></td><td><p>InvestorsBirthday</p></td><td><p>A</p></td><td><p>8</p></td><td><p>投资人出生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>24</p></td><td><p>DefDividendMethod</p></td><td><p>A</p></td><td><p>1</p></td><td><p>默认分红方式</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>27</p></td><td><p>CertificateType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>证件类型</p></td><td><p>参考数据字典</p></td><td><p>Y</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>48</p></td><td><p>EducationLevel</p></td><td><p>C</p></td><td><p>3</p></td><td><p>投资人学历</p></td><td><p>参考数据字典</p></td><td><p>N</p></td></tr>
<tr><td><p>49</p></td><td><p>EmailAddress</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人E-MAIL地址</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>51</p></td><td><p>FaxNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人传真号码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>65</p></td><td><p>VocationCode</p></td><td><p>C</p></td><td><p>5</p></td><td><p>投资人职业代码</p></td><td><p>参考数据字典</p></td><td><p>N</p></td></tr>
<tr><td><p>69</p></td><td><p>HomeTelNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人住址电话</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>72</p></td><td><p>CertificateNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人证件号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>73</p></td><td><p>AnnualIncome</p></td><td><p>N</p></td><td><p>16</p></td><td><p>投资人年收入</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>83</p></td><td><p>MobileTelNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人手机号码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>85</p></td><td><p>InvestorName</p></td><td><p>C</p></td><td><p>200</p></td><td><p>投资人户名</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td><p>托管网点号码。对大集中方式的销售人，此字段与销售人代码相同。</p></td><td><p>Y</p></td></tr>
<tr><td><p>88</p></td><td><p>OfficeTelNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人单位电话号码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td><p>参考数据字典</p></td><td><p>Y</p></td></tr>
<tr><td><p>101</p></td><td><p>PostCode</p></td><td><p>A</p></td><td><p>6</p></td><td><p>投资人邮政编码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>106</p></td><td><p>TransactorCertNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>经办人证件号码</p></td><td><p>对机构和产品必填</p></td><td><p>N</p></td></tr>
<tr><td><p>107</p></td><td><p>TransactorCertType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>经办人证件类型</p></td><td><p>参考数据字典“证件类型”中的个人部分。</p><p>对机构和产品必填</p></td><td><p>N</p></td></tr>
<tr><td><p>108</p></td><td><p>TransactorName</p></td><td><p>C</p></td><td><p>60</p></td><td><p>经办人姓名</p></td><td><p>对机构和产品必填</p></td><td><p>N</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>124</p></td><td><p>ConfidentialDocumentCode</p></td><td><p>C</p></td><td><p>8</p></td><td><p>密函编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>126</p></td><td><p>Sex</p></td><td><p>A</p></td><td><p>1</p></td><td><p>投资人性别</p></td><td><p>参考数据字典</p></td><td><p>N</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>140</p></td><td><p>TelNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人电话号码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>164</p></td><td><p>TradingMethod</p></td><td><p>C</p></td><td><p>8</p></td><td><p>使用的交易手段</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>167</p></td><td><p>MinorFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>未成年人标志</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>168</p></td><td><p>MinorID</p></td><td><p>C</p></td><td><p>18</p></td><td><p>未成年人ID号</p></td><td><p>原身份证字段在未成人开户时代表监护人的身份证号</p></td><td><p>N</p></td></tr>
<tr><td><p>169</p></td><td><p>DeliverType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>对帐单寄送选择</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>170</p></td><td><p>TransactorIDType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>经办人识别方式</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>256</p></td><td><p>Fromtaflag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>265</p></td><td><p>DeliverWay</p></td><td><p>C</p></td><td><p>8</p></td><td><p>对帐单寄送方式</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>325</p></td><td><p>InstitutionType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>机构类型</p></td><td><p>表示投资者类型，对机构和产品要求必填</p></td><td><p>N</p></td></tr>
<tr><td><p>665</p></td><td><p>InvestorProCode</p></td><td><p>C</p></td><td><p>30</p></td><td><p>投资者产品代码</p></td><td><p>投资者为公募基金产品或基金业协会备案产品时必填，填写行业编码中心分配的编码或协会备案产品编码</p></td><td><p>N</p></td></tr>
<tr><td><p>522</p></td><td><p>Nationality</p></td><td><p>C</p></td><td><p>3</p></td><td><p>投资者国家或地区</p></td><td><p>参考数据字典</p></td><td><p>N</p></td></tr>
<tr><td><p>286</p></td><td><p>CertValidDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>证件有效日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>287</p></td><td><p>InstTranCertValidDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>机构经办人身份证件有效日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>288</p></td><td><p>InstReprCertValidDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>机构法人身份证件有效日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>289</p></td><td><p>ClientRiskRate</p></td><td><p>C</p></td><td><p>1</p></td><td><p>客户风险等级</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>715</p></td><td><p>AuxCertType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>辅助身份证明文件类型</p></td><td><p>若有辅助证件则必填</p></td><td><p>N</p></td></tr>
<tr><td><p>716</p></td><td><p>AuxCertCode</p></td><td><p>C</p></td><td><p>40</p></td><td><p>辅助身份证明文件号码</p></td><td><p>若有辅助证件则必填</p></td><td><p>N</p></td></tr>
<tr><td><p>717</p></td><td><p>AuxCertValidDate</p></td><td><p>C</p></td><td><p>8</p></td><td><p>辅助身份证明文件有效日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>732</p></td><td><p>IPAddress</p></td><td><p>C</p></td><td><p>40</p></td><td><p>IP地址</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>735</p></td><td><p>MACAddress</p></td><td><p>C</p></td><td><p>20</p></td><td><p>MAC地址</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>739</p></td><td><p>IMEI</p></td><td><p>C</p></td><td><p>20</p></td><td><p>国际移动设备识别码</p></td><td><p>用于移动终端为Android操作系统版本时</p></td><td><p>N</p></td></tr>
<tr><td><p>740</p></td><td><p>UUID</p></td><td><p>C</p></td><td><p>32</p></td><td><p>通用唯一识别码</p></td><td><p>用于移动终端为iOS操作系统版本时</p></td><td><p>N</p></td></tr>
<tr><td><p>755</p></td><td><p>InvestAdviserCode</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投顾机构代码</p></td><td><p>对投顾账户，如有投顾机构代码则必填</p></td><td><p>N</p></td></tr>
<tr><td><p>756</p></td><td><p>AccChar</p></td><td><p>C</p></td><td><p>30</p></td><td><p>账户特征值</p></td><td><p>指出账户是否为投顾账户等</p></td><td><p>Y</p></td></tr>
</table>

### 4.5.2. 销户确认业务102

此业务表示基金账户实际被销户。若销售机构申报销户业务，但TA仅做撤销交易账户处理、并未销基金账户，则应报送109业务，不能报送102业务。

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>27</p></td><td><p>CertificateType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>证件类型</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>72</p></td><td><p>CertificateNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人证件号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>85</p></td><td><p>InvestorName</p></td><td><p>C</p></td><td><p>200</p></td><td><p>投资人户名</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>256</p></td><td><p>Fromtaflag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
</table>

### 4.5.3. 账户资料修改确认业务103

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>4</p></td><td><p>Address</p></td><td><p>C</p></td><td><p>300</p></td><td><p>通讯地址</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>5</p></td><td><p>InstReprIDCode</p></td><td><p>C</p></td><td><p>40</p></td><td><p>法人代表身份证件代码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>6</p></td><td><p>InstReprIDType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>法人代表证件类型</p></td><td><p>参考数据字典“证件类型”中的个人部分</p></td><td><p>N</p></td></tr>
<tr><td><p>7</p></td><td><p>InstReprName</p></td><td><p>C</p></td><td><p>60</p></td><td><p>法人代表姓名</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>23</p></td><td><p>InvestorsBirthday</p></td><td><p>A</p></td><td><p>8</p></td><td><p>投资人出生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>24</p></td><td><p>DefDividendMethod</p></td><td><p>A</p></td><td><p>1</p></td><td><p>默认分红方式</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>27</p></td><td><p>CertificateType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>证件类型</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>48</p></td><td><p>EducationLevel</p></td><td><p>C</p></td><td><p>3</p></td><td><p>投资人学历</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>49</p></td><td><p>EmailAddress</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人E-MAIL地址</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>51</p></td><td><p>FaxNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人传真号码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>65</p></td><td><p>VocationCode</p></td><td><p>C</p></td><td><p>5</p></td><td><p>投资人职业代码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>69</p></td><td><p>HomeTelNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人住址电话</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>72</p></td><td><p>CertificateNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人证件号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>73</p></td><td><p>AnnualIncome</p></td><td><p>N</p></td><td><p>16</p></td><td><p>投资人年收入</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>83</p></td><td><p>MobileTelNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人手机号码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>85</p></td><td><p>InvestorName</p></td><td><p>C</p></td><td><p>200</p></td><td><p>投资人户名</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>88</p></td><td><p>OfficeTelNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人单位电话号码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>101</p></td><td><p>PostCode</p></td><td><p>A</p></td><td><p>6</p></td><td><p>投资人邮政编码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>106</p></td><td><p>TransactorCertNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>经办人证件号码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>107</p></td><td><p>TransactorCertType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>经办人证件类型</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>108</p></td><td><p>TransactorName</p></td><td><p>C</p></td><td><p>60</p></td><td><p>经办人姓名</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>124</p></td><td><p>ConfidentialDocumentCode</p></td><td><p>C</p></td><td><p>8</p></td><td><p>密函编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>126</p></td><td><p>Sex</p></td><td><p>A</p></td><td><p>1</p></td><td><p>投资人性别</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>140</p></td><td><p>TelNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人电话号码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>164</p></td><td><p>TradingMethod</p></td><td><p>C</p></td><td><p>8</p></td><td><p>使用的交易手段</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>167</p></td><td><p>MinorFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>未成年人标志</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>168</p></td><td><p>MinorID</p></td><td><p>C</p></td><td><p>18</p></td><td><p>未成年人ID号</p></td><td><p>原身份证字段在未成人开户时代表监护人的身份证号</p></td><td><p>N</p></td></tr>
<tr><td><p>169</p></td><td><p>DeliverType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>对帐单寄送选择</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>170</p></td><td><p>TransactorIDType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>经办人识别方式</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>256</p></td><td><p>Fromtaflag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>265</p></td><td><p>DeliverWay</p></td><td><p>C</p></td><td><p>8</p></td><td><p>对帐单寄送方式</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>325</p></td><td><p> InstitutionType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>机构类型</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>665</p></td><td><p>InvestorProCode</p></td><td><p>C</p></td><td><p>30</p></td><td><p>投资者产品代码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>522</p></td><td><p>Nationality</p></td><td><p>C</p></td><td><p>3</p></td><td><p>投资者国家或地区</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>286</p></td><td><p>CertValidDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>证件有效日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>287</p></td><td><p>InstTranCertValidDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>机构经办人身份证件有效日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>288</p></td><td><p>InstReprCertValidDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>机构法人身份证件有效日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>289</p></td><td><p>ClientRiskRate</p></td><td><p>C</p></td><td><p>1</p></td><td><p>客户风险等级</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>715</p></td><td><p>AuxCertType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>辅助身份证明文件类型</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>716</p></td><td><p>AuxCertCode</p></td><td><p>C</p></td><td><p>40</p></td><td><p>辅助身份证明文件号码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>717</p></td><td><p>AuxCertValidDate</p></td><td><p>C</p></td><td><p>8</p></td><td><p>辅助身份证明文件有效日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>732</p></td><td><p>IPAddress</p></td><td><p>C</p></td><td><p>40</p></td><td><p>IP地址</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>735</p></td><td><p>MACAddress</p></td><td><p>C</p></td><td><p>20</p></td><td><p>MAC地址</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>739</p></td><td><p>IMEI</p></td><td><p>C</p></td><td><p>20</p></td><td><p>国际移动设备识别码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>740</p></td><td><p>UUID</p></td><td><p>C</p></td><td><p>32</p></td><td><p>通用唯一识别码</p></td><td></td><td><p>N</p></td></tr>
</table>

### 4.5.4. 增加交易账户确认108、撤销交易账户确认109

若销售机构申报撤销交易账户业务，但TA同时注销了基金账户和交易账户，应同时报送102和109业务。

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>27</p></td><td><p>CertificateType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>证件类型</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>72</p></td><td><p>CertificateNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人证件号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>85</p></td><td><p>InvestorName</p></td><td><p>C</p></td><td><p>200</p></td><td><p>投资人户名</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>256</p></td><td><p>Fromtaflag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>755</p></td><td><p>InvestAdviserCode</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投顾机构代码</p></td><td><p>对投顾账户，如有投顾机构代码则必填</p></td><td><p>N</p></td></tr>
<tr><td><p>756</p></td><td><p>AccChar</p></td><td><p>C</p></td><td><p>30</p></td><td><p>账户特征值</p></td><td><p>指出账户是否为投顾账户等</p></td><td><p>Y</p></td></tr>
</table>

### 4.5.5. 变更交易账户确认158

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>旧交易账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>142</p></td><td><p>TargetTransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>对方销售人处投资人交易账号</p></td><td><p>新交易账号</p></td><td><p>Y</p></td></tr>
</table>

### 4.5.6. 认购业务数据项120

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>28</p></td><td><p>DepositAcct</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人在销售人处用于交易的资金账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>64</p></td><td><p>ConfirmedAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认金额</p></td><td><p>含所有费用的总金额</p></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>133</p></td><td><p>TradingPrice</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>交易价格</p></td><td><p>投资者的单位交易成本</p></td><td><p>N</p></td></tr>
<tr><td><p>134</p></td><td><p>ApplicationAmount</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>申请金额</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
</table>

### 4.5.7. 认购结果业务数据项130

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>28</p></td><td><p>DepositAcct</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人在销售人处用于交易的资金账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>52</p></td><td><p>Charge</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>手续费</p></td><td><p>投资人应付总手续费</p></td><td><p>Y</p></td></tr>
<tr><td><p>53</p></td><td><p>AgencyFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>代理费</p></td><td><p>手续费中划归销售人的部分</p></td><td><p>Y</p></td></tr>
<tr><td><p>55</p></td><td><p>TotalTransFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认费用合计</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认份数</p></td><td><p>包括利息折算的份额</p></td><td><p>Y</p></td></tr>
<tr><td><p>64</p></td><td><p>ConfirmedAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认金额</p></td><td><p>含所有费用的总金额。不含利息。</p></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>76</p></td><td><p>Interest</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>基金账户利息金额</p></td><td><p>认购一次确认的金额在整个计息周期中产生的利息</p></td><td><p>Y</p></td></tr>
<tr><td><p>86</p></td><td><p>NAV</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>基金单位净值</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>指认购交易申请日期</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>133</p></td><td><p>TradingPrice</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>交易价格</p></td><td><p>投资者的单位交易成本</p></td><td><p>N</p></td></tr>
<tr><td><p>134</p></td><td><p>ApplicationAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请金额</p></td><td><p>经认购一次确认后的金额，非原始申请金额</p></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>138</p></td><td><p>StampDuty</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>印花税</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>225</p></td><td><p>RaiseInterest</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>认购期间利息</p></td><td><p>因认购二次确认失败而退还给投资人的利息</p></td><td><p>Y</p></td></tr>
<tr><td><p>560</p></td><td><p>ManagerRealRatio</p></td><td><p>N</p></td><td><p>7(四位小数)</p></td><td><p>实际计算折扣</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>255</p></td><td><p>TransferFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>过户费</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>266</p></td><td><p>VolumeByInterest</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>基金账户利息金额转份额</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>276</p></td><td><p>FeeCalculator</p></td><td><p>A</p></td><td><p>1</p></td><td><p>计费人</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>156</p></td><td><p>InterestTax</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>利息税</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>283</p></td><td><p>RefundAmount</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>退款金额</p></td><td><p>销售人应退还给投资人的金额（认购原始申请金额和认购二次确认金额的差值）</p></td><td><p>N</p></td></tr>
</table>

### 4.5.8. 申购业务数据项122

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>28</p></td><td><p>DepositAcct</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人在销售人处用于交易的资金账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>52</p></td><td><p>Charge</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>手续费</p></td><td><p>投资人应付总手续费</p></td><td><p>Y</p></td></tr>
<tr><td><p>53</p></td><td><p>AgencyFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>代理费</p></td><td><p>手续费中划归销售人的部分</p></td><td><p>Y</p></td></tr>
<tr><td><p>55</p></td><td><p>TotalTransFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认费用合计</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>64</p></td><td><p>ConfirmedAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认金额</p></td><td><p>含所有费用的总金额</p></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>86</p></td><td><p>NAV</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>基金单位净值</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>94</p></td><td><p>OtherFee1</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>其它费1</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>95</p></td><td><p>OtherFee2</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其它费2</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>96</p></td><td><p>OtherFee3</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其它费3</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>133</p></td><td><p>TradingPrice</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>交易价格</p></td><td><p>投资者的单位交易成本</p></td><td><p>N</p></td></tr>
<tr><td><p>134</p></td><td><p>ApplicationAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请金额</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>138</p></td><td><p>StampDuty</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>印花税</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>150</p></td><td><p>ValidPeriod</p></td><td><p>N</p></td><td><p>2</p></td><td><p>交易申请有效天数</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>177</p></td><td><p>BusinessFinishFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>业务过程完全结束标识</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>560</p></td><td><p>ManagerRealRatio</p></td><td><p>N</p></td><td><p>7(四位小数)</p></td><td><p>实际计算折扣</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>255</p></td><td><p>TransferFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>过户费</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>276</p></td><td><p>FeeCalculator</p></td><td><p>A</p></td><td><p>1</p></td><td><p>计费人</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>506</p></td><td><p>HandleCharge</p></td><td><p>N</p></td><td><p>16（两位小数）　</p></td><td><p>经手费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
</table>

### 4.5.9. 定期定额申购业务数据项139

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>28</p></td><td><p>DepositAcct</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人在销售人处用于交易的资金账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>40</p></td><td><p>DateOfPeriodicSubs</p></td><td><p>A</p></td><td><p>8</p></td><td><p>定时定额申购日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>52</p></td><td><p>Charge</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>手续费</p></td><td><p>投资人应付总手续费</p></td><td><p>Y</p></td></tr>
<tr><td><p>53</p></td><td><p>AgencyFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>代理费</p></td><td><p>手续费中划归销售人的部分</p></td><td><p>Y</p></td></tr>
<tr><td><p>55</p></td><td><p>TotalTransFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>交易确认费用合计</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>64</p></td><td><p>ConfirmedAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认金额</p></td><td><p>含所有费用的总金额</p></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>86</p></td><td><p>NAV</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>基金单位净值</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>94</p></td><td><p>OtherFee1</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>其它费1</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>95</p></td><td><p>OtherFee2</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其它费2</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>96</p></td><td><p>OtherFee3</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其它费3</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>133</p></td><td><p>TradingPrice</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>交易价格</p></td><td><p>投资者的单位交易成本</p></td><td><p>N</p></td></tr>
<tr><td><p>134</p></td><td><p>ApplicationAmount</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>申请金额</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>138</p></td><td><p>StampDuty</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>印花税</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>150</p></td><td><p>ValidPeriod</p></td><td><p>N</p></td><td><p>2</p></td><td><p>交易申请有效天数</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>177</p></td><td><p>BusinessFinishFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>业务过程完全结束标识</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>560</p></td><td><p>ManagerRealRatio</p></td><td><p>N</p></td><td><p>7(四位小数)</p></td><td><p>实际计算折扣</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>255</p></td><td><p>TransferFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>过户费</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>276</p></td><td><p>FeeCalculator</p></td><td><p>A</p></td><td><p>1</p></td><td><p>计费人</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>506</p></td><td><p>HandleCharge</p></td><td><p>N</p></td><td><p>16（两位小数）　</p></td><td><p>经手费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>538</p></td><td><p>RationKind</p></td><td><p>C</p></td><td><p>3</p></td><td><p>定期定额品种代码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>607</p></td><td><p>RationNo</p></td><td><p>C</p></td><td><p>3</p></td><td><p>定期定额序号</p></td><td></td><td><p>N</p></td></tr>
</table>

### 4.5.10. ETF一次申购业务数据项191

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>28</p></td><td><p>DepositAcct</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人在销售人处用于交易的资金账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>52</p></td><td><p>Charge</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>手续费</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>53</p></td><td><p>AgencyFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>代理费</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>55</p></td><td><p>TotalTransFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>交易确认费用合计</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>64</p></td><td><p>ConfirmedAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认金额</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>94</p></td><td><p>OtherFee1</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>其它费1</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>95</p></td><td><p>OtherFee2</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其它费2</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>96</p></td><td><p>OtherFee3</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其它费3</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>134</p></td><td><p>ApplicationAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请金额</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>138</p></td><td><p>StampDuty</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>印花税</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>150</p></td><td><p>ValidPeriod</p></td><td><p>N</p></td><td><p>2</p></td><td><p>交易申请有效天数</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>560</p></td><td><p>ManagerRealRatio</p></td><td><p>N</p></td><td><p>7(四位小数)</p></td><td><p>实际计算折扣</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>255</p></td><td><p>TransferFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>过户费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>276</p></td><td><p>FeeCalculator</p></td><td><p>A</p></td><td><p>1</p></td><td><p>计费人</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>506</p></td><td><p>HandleCharge</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>经手费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
</table>

### 4.5.11. ETF二次申购业务数据项192

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>28</p></td><td><p>DepositAcct</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人在销售人处用于交易的资金账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>52</p></td><td><p>Charge</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>手续费</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>53</p></td><td><p>AgencyFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>代理费</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>55</p></td><td><p>TotalTransFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>交易确认费用合计</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>64</p></td><td><p>ConfirmedAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认金额</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>86</p></td><td><p>NAV</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>基金单位净值</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p><p>义</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>94</p></td><td><p>OtherFee1</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>其它费1</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>95</p></td><td><p>OtherFee2</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其它费2</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>96</p></td><td><p>OtherFee3</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其它费3</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>132</p></td><td><p>ApplicationVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请基金份数</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>133</p></td><td><p>TradingPrice</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>交易价格</p></td><td><p>投资者的单位交易成本</p></td><td><p>N</p></td></tr>
<tr><td><p>134</p></td><td><p>ApplicationAmount</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>申请金额</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>138</p></td><td><p>StampDuty</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>印花税</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>150</p></td><td><p>ValidPeriod</p></td><td><p>N</p></td><td><p>2</p></td><td><p>交易申请有效天数</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>177</p></td><td><p>BusinessFinishFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>业务过程完全结束标识</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>560</p></td><td><p>ManagerRealRatio</p></td><td><p>N</p></td><td><p>7(四位小数)</p></td><td><p>实际计算折扣</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>255</p></td><td><p>TransferFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>过户费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>276</p></td><td><p>FeeCalculator</p></td><td><p>A</p></td><td><p>1</p></td><td><p>计费人</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>506</p></td><td><p>HandleCharge</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>经手费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
</table>

### 4.5.12. 赎回业务数据项124/定时定额赎回163

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>28</p></td><td><p>DepositAcct</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人在销售人处用于交易的资金账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>52</p></td><td><p>Charge</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>手续费</p></td><td><p>投资人应付总手续费。含违约金、惩罚性费用、业绩报酬等。含后收手续费。</p></td><td><p>Y</p></td></tr>
<tr><td><p>53</p></td><td><p>AgencyFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>代理费</p></td><td><p>手续费中划归销售人的部分</p></td><td><p>Y</p></td></tr>
<tr><td><p>55</p></td><td><p>TotalTransFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>交易确认费用合计</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>64</p></td><td><p>ConfirmedAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认金额</p></td><td><p>为投资者实得金额。不含手续费。含业绩补偿。对货币基金，含已兑付的收益。</p></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>80</p></td><td><p>LargeRedemptionFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>巨额赎回处理标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>86</p></td><td><p>NAV</p></td><td><p>N</p></td><td><p>16（八位小数）　</p></td><td><p>基金单位净值</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>89</p></td><td><p>OriginalSerialNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA的原确认流水号</p></td><td><p>指定赎回时指明针对哪一笔的原确认流水号</p></td><td><p>N</p></td></tr>
<tr><td><p>90</p></td><td><p>OriginalAppSheetNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>原申请单编号</p></td><td><p>预约赎回到期后的024业务有值</p></td><td><p>N</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>对巨额赎回顺延，此处填写原始申请日期。</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>94</p></td><td><p>OtherFee1</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>其它费1</p></td><td><p>赎回手续费中划归基金资产的部分</p></td><td><p>Y</p></td></tr>
<tr><td><p>95</p></td><td><p>OtherFee2</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其它费2</p></td><td><p>返还的销售服务费</p></td><td><p>Y</p></td></tr>
<tr><td><p>96</p></td><td><p>OtherFee3</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其它费3</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>132</p></td><td><p>ApplicationVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请基金份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>133</p></td><td><p>TradingPrice</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>交易价格</p></td><td><p>投资者的单位交易成本</p></td><td><p>N</p></td></tr>
<tr><td><p>134</p></td><td><p>ApplicationAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请金额</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>138</p></td><td><p>StampDuty</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>印花税</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>150</p></td><td><p>ValidPeriod</p></td><td><p>N</p></td><td><p>2</p></td><td><p>交易申请有效天数</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>177</p></td><td><p>BusinessFinishFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>业务过程完全结束标识</p></td><td><p>0-中间过程</p><p>1-业务过程结束</p><p>比如因巨额赎回导致顺延，存在中间过程。</p></td><td><p>Y</p></td></tr>
<tr><td><p>193</p></td><td><p>RateFee</p></td><td><p>N</p></td><td><p>9(八位小数)</p></td><td><p>费率</p></td><td><p>分段收费考虑</p></td><td><p>N</p></td></tr>
<tr><td><p>560</p></td><td><p>ManagerRealRatio</p></td><td><p>N</p></td><td><p>7(四位小数)</p></td><td><p>实际计算折扣</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>255</p></td><td><p>TransferFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>过户费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>261</p></td><td><p>OriginalCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>TA的原确认日期</p></td><td><p>指定赎回时指明针对哪一个过户日的赎回</p></td><td><p>N</p></td></tr>
<tr><td><p>262</p></td><td><p>RedemptionInAdvanceFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>预约赎回标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>276</p></td><td><p>FeeCalculator</p></td><td><p>A</p></td><td><p>1</p></td><td><p>计费人</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>506</p></td><td><p>HandleCharge</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>经手费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>300</p></td><td><p>BreachFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>违约金</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>306</p></td><td><p>BreachFeeBackToFund</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>违约金归基金资产金额</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>305</p></td><td><p>PunishFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>惩罚性费用</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>507</p></td><td><p>UndistributeMonetaryIncome</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>货币基金未付收益金额</p></td><td><p>货币基金必填，指赎回业务带走的收益</p></td><td><p>N</p></td></tr>
<tr><td><p>510</p></td><td><p>UndistributeMonetaryIncomeFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>货币基金未付收益金额正负</p></td><td><p>货币基金必填</p></td><td><p>N</p></td></tr>
<tr><td><p>173</p></td><td><p>TotalBackendLoad</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易后端收费总额</p></td><td><p>收费方式为后收费时必填，即后收手续费</p></td><td><p>Y</p></td></tr>
<tr><td><p>543</p></td><td><p>AchievementPay</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>业绩报酬</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>544</p></td><td><p>AchievementCompen</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>业绩补偿</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>264</p></td><td><p>DetailFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>明细标志</p></td><td><p>对一笔赎回，可以返回一笔非明细确认，或一笔非明细确认和多笔明细确认。明细确认是针对过户日或TA确认流水号的确认记录。</p></td><td><p>Y</p></td></tr>
<tr><td><p>562</p></td><td><p>GeneralTASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>总TA确认流水号</p></td><td><p>用于发送交易明细确认。非明细确认和明细确认应当具有相同的总TA确认流水号。</p></td><td><p>N</p></td></tr>
<tr><td><p>327</p></td><td><p>TakeIncomeFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>带走收益标志</p></td><td><p>货币基金必填</p><p>0-不带走，1-带走</p></td><td><p>N</p></td></tr>
<tr><td><p>303</p></td><td><p>ForceRedemptionType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>强制赎回类型</p></td><td></td><td><p>N</p></td></tr>
</table>

### 4.5.13. 强制赎回业务数据项142、基金清盘150、基金终止151

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>28</p></td><td><p>DepositAcct</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人在销售人处用于交易的资金账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>52</p></td><td><p>Charge</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>手续费</p></td><td><p>投资人应付总手续费。含违约金、惩罚性费用、业绩报酬等。含后收手续费。</p></td><td><p>Y</p></td></tr>
<tr><td><p>53</p></td><td><p>AgencyFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>代理费</p></td><td><p>手续费中划归销售人的部分</p></td><td><p>Y</p></td></tr>
<tr><td><p>55</p></td><td><p>TotalTransFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>交易确认费用合计</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>64</p></td><td><p>ConfirmedAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认金额</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>80</p></td><td><p>LargeRedemptionFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>巨额赎回处理标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>86</p></td><td><p>NAV</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>基金单位净值</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>89</p></td><td><p>OriginalSerialNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA的原确认流水号</p></td><td><p>指定赎回用</p></td><td><p>N</p></td></tr>
<tr><td><p>90</p></td><td><p>OriginalAppSheetNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>原申请单编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>对强制赎回，此处填写交易确认日期的上一交易日。</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>94</p></td><td><p>OtherFee1</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>其它费1</p></td><td><p>赎回手续费中划归基金资产的部分</p></td><td><p>Y</p></td></tr>
<tr><td><p>95</p></td><td><p>OtherFee2</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其它费2</p></td><td><p>返还的销售服务费</p></td><td><p>Y</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>132</p></td><td><p>ApplicationVol</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>申请基金份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>133</p></td><td><p>TradingPrice</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>交易价格</p></td><td><p>投资者的单位交易成本</p></td><td><p>N</p></td></tr>
<tr><td><p>134</p></td><td><p>ApplicationAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请金额</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>138</p></td><td><p>StampDuty</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>印花税</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>150</p></td><td><p>ValidPeriod</p></td><td><p>N</p></td><td><p>2</p></td><td><p>交易申请有效天数</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>177</p></td><td><p>BusinessFinishFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>业务过程完全结束标识</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>560</p></td><td><p>ManagerRealRatio</p></td><td><p>N</p></td><td><p>7(四位小数)</p></td><td><p>实际计算折扣</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>254</p></td><td><p>Specification</p></td><td><p>C</p></td><td><p>60</p></td><td><p>摘要说明</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>255</p></td><td><p>TransferFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>过户费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>261</p></td><td><p>OriginalCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>TA的原确认日期</p></td><td><p>指定赎回用</p></td><td><p>N</p></td></tr>
<tr><td><p>262</p></td><td><p>RedemptionInAdvanceFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>预约赎回标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>263</p></td><td><p>RedemptionReason</p></td><td><p>A</p></td><td><p>1</p></td><td><p>强行赎回原因</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>264</p></td><td><p>DetailFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>明细标志</p></td><td><p>对一笔赎回申请，可以返回一笔非明细确认，或一笔非明细确认和多笔明细确认。明细确认是针对过户日或TA确认流水号的确认记录。</p></td><td><p>Y</p></td></tr>
<tr><td><p>276</p></td><td><p>FeeCalculator</p></td><td><p>A</p></td><td><p>1</p></td><td><p>计费人</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>506</p></td><td><p>HandleCharge</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>经手费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>300</p></td><td><p>BreachFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>违约金</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>306</p></td><td><p>BreachFeeBackToFund</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>违约金归基金资产金额</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>305</p></td><td><p>PunishFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>惩罚性费用</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>507</p></td><td><p>UndistributeMonetaryIncome</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>货币基金未付收益金额</p></td><td><p>货币基金必填</p></td><td><p>N</p></td></tr>
<tr><td><p>510</p></td><td><p>UndistributeMonetaryIncomeFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>货币基金未付收益金额正负</p></td><td><p>货币基金必填</p></td><td><p>N</p></td></tr>
<tr><td><p>173</p></td><td><p>TotalBackendLoad</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易后端收费总额</p></td><td><p>收费方式为后收费时必填，即后收手续费</p></td><td><p>Y</p></td></tr>
<tr><td><p>543</p></td><td><p>AchievementPay</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>业绩报酬</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>544</p></td><td><p>AchievementCompen</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>业绩补偿</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>562</p></td><td><p>GeneralTASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>总TA确认流水号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>327</p></td><td><p>TakeIncomeFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>带走收益标志</p></td><td><p>货币基金必填</p></td><td><p>N</p></td></tr>
<tr><td><p>303</p></td><td><p>ForceRedemptionType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>强制赎回类型</p></td><td></td><td><p>N</p></td></tr>
</table>

### 4.5.14. ETF一次赎回业务数据项193

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否</p><p>必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>28</p></td><td><p>DepositAcct</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人在销售人处用于交易的资金账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>80</p></td><td><p>LargeRedemptionFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>巨额赎回处理标志</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>89</p></td><td><p>OriginalSerialNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA的原确认流水号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>90</p></td><td><p>OriginalAppSheetNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>原申请单编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>132</p></td><td><p>ApplicationVol</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>申请基金份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>150</p></td><td><p>ValidPeriod</p></td><td><p>N</p></td><td><p>2</p></td><td><p>交易申请有效天数</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>261</p></td><td><p>OriginalCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>TA的原确认日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>262</p></td><td><p>RedemptionInAdvanceFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>预约赎回标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>276</p></td><td><p>FeeCalculator</p></td><td><p>A</p></td><td><p>1</p></td><td><p>计费人</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>264</p></td><td><p>DetailFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>明细标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>560</p></td><td><p>ManagerRealRatio</p></td><td><p>N</p></td><td><p>7(四位小数)</p></td><td><p>实际计算折扣</p></td><td></td><td><p>Y</p></td></tr>
</table>

### 4.5.15. ETF二次赎回业务数据项194

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否</p><p>必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>28</p></td><td><p>DepositAcct</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人在销售人处用于交易的资金账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>52</p></td><td><p>Charge</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>手续费</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>53</p></td><td><p>AgencyFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>代理费</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>55</p></td><td><p>TotalTransFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>交易确认费用合计</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>64</p></td><td><p>ConfirmedAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认金额</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>80</p></td><td><p>LargeRedemptionFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>巨额赎回处理标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>86</p></td><td><p>NAV</p></td><td><p>N</p></td><td><p>16（八位小数）　</p></td><td><p>基金单位净值</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>89</p></td><td><p>OriginalSerialNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA的原确认流水号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>90</p></td><td><p>OriginalAppSheetNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>原申请单编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>94</p></td><td><p>OtherFee1</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其它费1</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>132</p></td><td><p>ApplicationVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请基金份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>133</p></td><td><p>TradingPrice</p></td><td><p>N</p></td><td><p>16（八位小数）　</p></td><td><p>交易价格</p></td><td><p>投资者的单位交易成本</p></td><td><p>N</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>138</p></td><td><p>StampDuty</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>印花税</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>255</p></td><td><p>TransferFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>过户费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>261</p></td><td><p>OriginalCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>TA的原确认日期</p></td><td><p>指定赎回时指明针对哪一个过户日的赎回</p></td><td><p>N</p></td></tr>
<tr><td><p>262</p></td><td><p>RedemptionInAdvanceFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>预约赎回标志</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>276</p></td><td><p>FeeCalculator</p></td><td><p>A</p></td><td><p>1</p></td><td><p>计费人</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>150</p></td><td><p>ValidPeriod</p></td><td><p>N</p></td><td><p>2</p></td><td><p>交易申请有效天数</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>264</p></td><td><p>DetailFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>明细标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>506</p></td><td><p>HandleCharge</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>经手费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>173</p></td><td><p>TotalBackendLoad</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易后端收费总额</p></td><td><p>后收手续费</p></td><td><p>Y</p></td></tr>
<tr><td><p>560</p></td><td><p>ManagerRealRatio</p></td><td><p>N</p></td><td><p>7(四位小数)</p></td><td><p>实际计算折扣</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>562</p></td><td><p>GeneralTASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>总TA确认流水号</p></td><td><p>用于发送交易明细</p></td><td><p>N</p></td></tr>
</table>

### 4.5.16. 预约赎回业务数据项125

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否</p><p>必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>28</p></td><td><p>DepositAcct</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人在销售人处用于交易的资金账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>52</p></td><td><p>Charge</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>手续费</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>53</p></td><td><p>AgencyFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>代理费</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>55</p></td><td><p>TotalTransFee</p></td><td><p>N</p></td><td><p>16（两位小数）)</p></td><td><p>交易确认费用合计</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>64</p></td><td><p>ConfirmedAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认金额</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>80</p></td><td><p>LargeRedemptionFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>巨额赎回处理标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>86</p></td><td><p>NAV</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>基金单位净值</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>89</p></td><td><p>OriginalSerialNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA的原确认流水号</p></td><td><p>指定赎回时指明针对哪一笔的原确认流水号</p></td><td><p>N</p></td></tr>
<tr><td><p>90</p></td><td><p>OriginalAppSheetNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>原申请单编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>94</p></td><td><p>OtherFee1</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>其它费1</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>95</p></td><td><p>OtherFee2</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其它费2</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>96</p></td><td><p>OtherFee3</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其它费3</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>102</p></td><td><p>RedemptionDateInAdvance</p></td><td><p>A</p></td><td><p>8</p></td><td><p>预约赎回日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>132</p></td><td><p>ApplicationVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请基金份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>133</p></td><td><p>TradingPrice</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>交易价格</p></td><td><p>投资者的单位交易成本</p></td><td><p>N</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>138</p></td><td><p>StampDuty</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>印花税</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>150</p></td><td><p>ValidPeriod</p></td><td><p>N</p></td><td><p>2</p></td><td><p>交易申请有效天数</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>193</p></td><td><p>RateFee</p></td><td><p>N</p></td><td><p>9(八位小数)</p></td><td><p>费率</p></td><td><p>分段收费考虑</p></td><td><p>N</p></td></tr>
<tr><td><p>560</p></td><td><p>ManagerRealRatio</p></td><td><p>N</p></td><td><p>7(四位小数)</p></td><td><p>实际计算折扣</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>255</p></td><td><p>TransferFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>过户费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>261</p></td><td><p>OriginalCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>TA的原确认日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>264</p></td><td><p>DetailFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>明细标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>276</p></td><td><p>FeeCalculator</p></td><td><p>A</p></td><td><p>1</p></td><td><p>计费人</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>506</p></td><td><p>HandleCharge</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>经手费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>173</p></td><td><p>TotalBackendLoad</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易后端收费总额</p></td><td><p>后收手续费</p></td><td><p>N</p></td></tr>
</table>

### 4.5.17. 转托管业务数据项126

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否</p><p>必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>28</p></td><td><p>DepositAcct</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人在销售人处用于交易的资金账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>交易确认份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>89</p></td><td><p>OriginalSerialNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA的原确认流水号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>97</p></td><td><p>TargetDistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>对方销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>132</p></td><td><p>ApplicationVol</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>申请基金份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>141</p></td><td><p>TargetBranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>对方网点号</p></td><td><p>转销售人/机构、非交易过户时使用</p></td><td><p>Y</p></td></tr>
<tr><td><p>142</p></td><td><p>TargetTransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>对方销售人处投资人交易账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>152</p></td><td><p>TargetRegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>对方所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>177</p></td><td><p>BusinessFinishFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>业务过程完全结束标识</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass	</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>261</p></td><td><p>OriginalCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>TA的原确认日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>264</p></td><td><p>DetailFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>明细标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>507</p></td><td><p>UndistributeMonetaryIncome</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>货币基金未付收益金额</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>510</p></td><td><p>UndistributeMonetaryIncomeFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>货币基金未付收益金额正负</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>562</p></td><td><p>GeneralTASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>总TA确认流水号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>147</p></td><td><p>TargetTAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>对方基金账号</p></td><td><p>跨市场转托管必填</p></td><td><p>N</p></td></tr>
</table>

### 4.5.18. 转托管入业务数据项127

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否</p><p>必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>28</p></td><td><p>DepositAcct</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人在销售人处用于交易的资金账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>交易确认份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>89</p></td><td><p>OriginalSerialNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA的原确认流水号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>90</p></td><td><p>OriginalAppSheetNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>原申请单编号</p></td><td><p>127业务使用，表示转出时的申请单编号</p></td><td><p>Y</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>97</p></td><td><p>TargetDistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>对方销售人代码</p></td><td><p>指转出销售机构</p></td><td><p>Y</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>132</p></td><td><p>ApplicationVol</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>申请基金份数</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>176</p></td><td><p>TransferDirection</p></td><td><p>A</p></td><td><p>1</p></td><td><p>转入/转出标识</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>177</p></td><td><p>BusinessFinishFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>业务过程完全结束标识</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>258</p></td><td><p>OriginalAppDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>原申请日期</p></td><td><p>127业务使用，表示转出时的申请日期</p></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass	</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>261</p></td><td><p>OriginalCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>TA的原确认日期</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>264</p></td><td><p>DetailFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>明细标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>507</p></td><td><p>UndistributeMonetaryIncome</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>货币基金未付收益金额</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>510</p></td><td><p>UndistributeMonetaryIncomeFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>货币基金未付收益金额正负</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>562</p></td><td><p>GeneralTASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>总TA确认流水号</p></td><td><p>用于发送交易明细</p></td><td><p>N</p></td></tr>
</table>

### 4.5.19. 转托管出业务数据项128

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>管理人是否</p><p>必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>28</p></td><td><p>DepositAcct</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人在销售人处用于交易的资金账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>交易确认份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>89</p></td><td><p>OriginalSerialNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA的原确认流水号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>97</p></td><td><p>TargetDistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>对方销售人代码</p></td><td><p>指转入销售机构</p></td><td><p>Y</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>132</p></td><td><p>ApplicationVol</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>申请基金份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>176</p></td><td><p>TransferDirection</p></td><td><p>A</p></td><td><p>1</p></td><td><p>转入/转出标识</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>177</p></td><td><p>BusinessFinishFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>业务过程完全结束标识</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass	</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>261</p></td><td><p>OriginalCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>TA的原确认日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>264</p></td><td><p>DetailFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>明细标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>507</p></td><td><p>UndistributeMonetaryIncome</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>货币基金未付收益金额</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>510</p></td><td><p>UndistributeMonetaryIncomeFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>货币基金未付收益金额正负</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>562</p></td><td><p>GeneralTASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>总TA确认流水号</p></td><td><p>用于发送交易明细</p></td><td><p>N</p></td></tr>
</table>

### 4.5.20. 设置分红方式业务数据项129

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否</p><p>必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>24</p></td><td><p>DefDividendMethod</p></td><td><p>A</p></td><td><p>1</p></td><td><p>默认分红方式</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
</table>

### 4.5.21. 份额冻结业务数据项131（包含质押业务）

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否</p><p>必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>58</p></td><td><p>FreezingDeadline</p></td><td><p>A</p></td><td><p>8</p></td><td><p>冻结截止日期</p></td><td><p>格式为：YYYYMMDD</p><p>不确定日期为00010101</p></td><td><p>Y</p></td></tr>
<tr><td><p>60</p></td><td><p>FrozenCause</p></td><td><p>A</p></td><td><p>1</p></td><td><p>冻结原因</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>交易确认份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>89</p></td><td><p>OriginalSerialNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA的原确认流水号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>132</p></td><td><p>ApplicationVol</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>申请基金份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>150</p></td><td><p>ValidPeriod</p></td><td><p>N</p></td><td><p>2</p></td><td><p>交易申请有效天数</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>165</p></td><td><p>ContractNo</p></td><td><p>A</p></td><td><p>20</p></td><td><p>合约编号</p></td><td><p>冻结的法律文书编号等</p></td><td><p>N</p></td></tr>
<tr><td><p>254</p></td><td><p>Specification</p></td><td><p>C</p></td><td><p>60</p></td><td><p>摘要说明</p></td><td><p>质押冻结说明</p></td><td><p>N</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>257</p></td><td><p>FrozenMethod</p></td><td><p>A</p></td><td><p>1</p></td><td><p>冻结方式</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>261</p></td><td><p>OriginalCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>TA的原确认日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>264</p></td><td><p>DetailFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>明细标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>562</p></td><td><p>GeneralTASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>总TA确认流水号</p></td><td></td><td><p>N</p></td></tr>
</table>

### 4.5.22. 份额解冻业务数据项132（包含解质押业务）

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否</p><p>必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>60</p></td><td><p>FrozenCause</p></td><td><p>A</p></td><td><p>1</p></td><td><p>冻结原因</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>交易确认份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>89</p></td><td><p>OriginalSerialNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA的原确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>90</p></td><td><p>OriginalAppSheetNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>原申请单编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>132</p></td><td><p>ApplicationVol</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>申请基金份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>150</p></td><td><p>ValidPeriod</p></td><td><p>N</p></td><td><p>2</p></td><td><p>交易申请有效天数</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>165</p></td><td><p>ContractNo</p></td><td><p>A</p></td><td><p>20</p></td><td><p>合约编号</p></td><td><p>冻结的法律文书编号等</p></td><td><p>N</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>261</p></td><td><p>OriginalCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>TA的原确认日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>264</p></td><td><p>DetailFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>明细标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>562</p></td><td><p>GeneralTASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>总TA确认流水号</p></td><td></td><td><p>N</p></td></tr>
</table>

### 4.5.23. 非交易过户133（包含份额转让业务）、快速过户198、非交易过户出135、非交易过户入134

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否</p><p>必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>89</p></td><td><p>OriginalSerialNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA的原确认流水号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>97</p></td><td><p>TargetDistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>对方销售人代码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>132</p></td><td><p>ApplicationVol</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>申请基金份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>141</p></td><td><p>TargetBranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>对方网点号</p></td><td><p>转销售人/机构、非交易过户时使用</p></td><td><p>Y</p></td></tr>
<tr><td><p>142</p></td><td><p>TargetTransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>对方销售人处投资人交易账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>147</p></td><td><p>TargetTAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>对方基金账号</p></td><td><p>非交易过户时</p></td><td><p>Y</p></td></tr>
<tr><td><p>152</p></td><td><p>TargetRegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>对方所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>165</p></td><td><p>ContractNo</p></td><td><p>A</p></td><td><p>20</p></td><td><p>合约编号</p></td><td><p>冻结的法律文书编号等</p></td><td><p>N</p></td></tr>
<tr><td><p>177</p></td><td><p>BusinessFinishFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>业务过程完全结束标识</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>254</p></td><td><p>Specification</p></td><td><p>C</p></td><td><p>60</p></td><td><p>摘要说明</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>261</p></td><td><p>OriginalCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>TA的原确认日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>264</p></td><td><p>DetailFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>明细标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>507</p></td><td><p>UndistributeMonetaryIncome</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>货币基金未付收益金额</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>510</p></td><td><p>UndistributeMonetaryIncomeFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>货币基金未付收益金额正负</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>562</p></td><td><p>GeneralTASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>总TA确认流水号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>730</p></td><td><p>TransferReason</p></td><td><p>C</p></td><td><p>3</p></td><td><p>过户原因</p></td><td></td><td><p>Y</p></td></tr>
</table>

### 4.5.24. 基金转换业务数据项136

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否</p><p>必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>34</p></td><td><p>CodeOfTargetFund</p></td><td><p>C</p></td><td><p>6</p></td><td><p>转换时的目标基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>52</p></td><td><p>Charge</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>手续费</p></td><td><p>投资人应付总手续费。等于转换费+补差费。</p></td><td><p>Y</p></td></tr>
<tr><td><p>53</p></td><td><p>AgencyFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>代理费</p></td><td><p>手续费中划归销售人的部分</p></td><td><p>Y</p></td></tr>
<tr><td><p>55</p></td><td><p>TotalTransFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>交易确认费用合计</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认份数</p></td><td><p>确认的转出基金份数</p></td><td><p>Y</p></td></tr>
<tr><td><p>64</p></td><td><p>ConfirmedAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认金额</p></td><td><p>转出金额总额, 包含各种费用</p></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>86</p></td><td><p>NAV</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>基金单位净值</p></td><td><p>转出基金净值</p></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>89</p></td><td><p>OriginalSerialNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA的原确认流水号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>94</p></td><td><p>OtherFee1</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>其它费1</p></td><td><p>归基金资产费　</p></td><td><p>Y</p></td></tr>
<tr><td><p>95</p></td><td><p>OtherFee2</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其它费2</p></td><td><p>份额转出时，返还的销售服务费</p></td><td><p>Y</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>132</p></td><td><p>ApplicationVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请基金份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>133</p></td><td><p>TradingPrice</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>交易价格</p></td><td><p>投资者的单位交易成本</p></td><td><p>N</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>138</p></td><td><p>StampDuty</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>印花税</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>147</p></td><td><p>TargetTAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>对方基金账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>161</p></td><td><p>CfmVolOfTargetFund</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>目标基金的确认份数</p></td><td><p>确认的转入基金份数</p></td><td><p>Y</p></td></tr>
<tr><td><p>162</p></td><td><p>TargetNAV</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>目标基金的单位净值</p></td><td><p>转入基金净值　</p></td><td><p>N</p></td></tr>
<tr><td><p>173</p></td><td><p>TotalBackendLoad</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>交易后端收费总额</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>176</p></td><td><p>TransferDirection</p></td><td><p>A</p></td><td><p>1</p></td><td><p>转入/转出标识</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>560</p></td><td><p>ManagerRealRatio</p></td><td><p>N</p></td><td><p>7(四位小数)</p></td><td><p>实际计算折扣</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>255</p></td><td><p>TransferFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>过户费</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>261</p></td><td><p>OriginalCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>TA的原确认日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>264</p></td><td><p>DetailFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>明细标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>276</p></td><td><p>FeeCalculator</p></td><td><p>A</p></td><td><p>1</p></td><td><p>计费人</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>526</p></td><td><p>TargetShareType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>对方基金份额类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>541</p></td><td><p>RecuperateFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>补差费</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>617</p></td><td><p>TargetRegistrarCode</p></td><td><p>C</p></td><td><p>18</p></td><td><p>对方TA代码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>543</p></td><td><p>AchievementPay</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>业绩报酬</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>544</p></td><td><p>AchievementCompen</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>业绩补偿</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>386</p></td><td><p>ChangeAgencyFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>转换代理费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>387</p></td><td><p>RecuperateAgencyFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>补差代理费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>562</p></td><td><p>GeneralTASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>总TA确认流水号</p></td><td></td><td><p>N</p></td></tr>
</table>

### 4.5.25. 基金转换出业务数据项138

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否</p><p>必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认份数</p></td><td><p>确认的转出基金份数　</p></td><td><p>Y</p></td></tr>
<tr><td><p>64</p></td><td><p>ConfirmedAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认金额</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>86</p></td><td><p>NAV</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>基金单位净值</p></td><td><p>转出基金净值</p></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>89</p></td><td><p>OriginalSerialNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA的原确认流水号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>132</p></td><td><p>ApplicationVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请基金份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>176</p></td><td><p>TransferDirection</p></td><td><p>A</p></td><td><p>1</p></td><td><p>转入/转出标识</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>261</p></td><td><p>OriginalCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>TA的原确认日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>264</p></td><td><p>DetailFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>明细标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>562</p></td><td><p>GeneralTASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>总TA确认流水号</p></td><td><p>用于发送交易明细</p></td><td><p>N</p></td></tr>
<tr><td><p>543</p></td><td><p>AchievementPay</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>业绩报酬</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>544</p></td><td><p>AchievementCompen</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>业绩补偿</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>34</p></td><td><p>CodeOfTargetFund</p></td><td><p>C</p></td><td><p>6</p></td><td><p>转换时的目标基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>526</p></td><td><p>TargetShareType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>对方基金份额类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>617</p></td><td><p>TargetRegistrarCode</p></td><td><p>C</p></td><td><p>18</p></td><td><p>对方TA代码</p></td><td><p>跨TA基金转换时必填</p></td><td><p>N</p></td></tr>
<tr><td><p>95</p></td><td><p>OtherFee2</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其它费2</p></td><td><p>份额转出时，返还的销售服务费</p></td><td><p>Y</p></td></tr>
</table>

### 4.5.26. 基金转换入业务数据项137

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否</p><p>必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认份数</p></td><td><p>确认的转入份额　</p></td><td><p>Y</p></td></tr>
<tr><td><p>64</p></td><td><p>ConfirmedAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认金额</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>86</p></td><td><p>NAV</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>基金单位净值</p></td><td><p>转入基金净值</p></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>89</p></td><td><p>OriginalSerialNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA的原确认流水号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>132</p></td><td><p>ApplicationVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请基金份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>176</p></td><td><p>TransferDirection</p></td><td><p>A</p></td><td><p>1</p></td><td><p>转入/转出标识</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td><p>0-由销售人发起，1-由注册登记人发起</p></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>261</p></td><td><p>OriginalCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>TA的原确认日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>264</p></td><td><p>DetailFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>明细标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>526</p></td><td><p>TargetShareType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>对方基金份额类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>562</p></td><td><p>GeneralTASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>总TA确认流水号</p></td><td><p>用于发送交易明细</p></td><td><p>N</p></td></tr>
<tr><td><p>543</p></td><td><p>AchievementPay</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>业绩报酬</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>544</p></td><td><p>AchievementCompen</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>业绩补偿</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>34</p></td><td><p>CodeOfTargetFund</p></td><td><p>C</p></td><td><p>6</p></td><td><p>转换时的目标基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>617</p></td><td><p>TargetRegistrarCode</p></td><td><p>C</p></td><td><p>18</p></td><td><p>对方TA代码</p></td><td><p>跨TA基金转换时必填</p></td><td><p>N</p></td></tr>
</table>

### 4.5.27. 分红业务数据项143

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否</p><p>必需</p></td></tr>
<tr><td><p>22</p></td><td><p>BasisforCalculatingDividend</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>红利/红股基数</p></td><td><p>登记日基金持有人的基金份数</p></td><td><p>Y</p></td></tr>
<tr><td><p>24</p></td><td><p>DefDividendMethod</p></td><td><p>A</p></td><td><p>1</p></td><td><p>默认分红方式</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>28</p></td><td><p>DepositAcct</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人在销售人处用于交易的资金账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>41</p></td><td><p>VolOfDividendforReinvestment</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金账户红利再投资基金份数</p></td><td><p>投资人实得红股，含被续冻的红股　</p></td><td><p>Y</p></td></tr>
<tr><td><p>42</p></td><td><p>DividentDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>分红日/发放日</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>43</p></td><td><p>DividendAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金账户红利资金</p></td><td><p>红利总金额,含冻结红利及再投资的红利</p></td><td><p>Y</p></td></tr>
<tr><td><p>46</p></td><td><p>XRDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>除权日</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>52</p></td><td><p>Charge</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>手续费</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>53</p></td><td><p>AgencyFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>代理费</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>59</p></td><td><p>TotalFrozenVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金冻结总份数</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>64</p></td><td><p>ConfirmedAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>每笔交易确认金额</p></td><td><p>实发现金红利，不含冻结红利及再投资的红利</p></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>86</p></td><td><p>NAV</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>分红再投资基金净值</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>94</p></td><td><p>OtherFee1</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>其他费用1</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>95</p></td><td><p>OtherFee2</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其他费用2</p></td><td><p>货币基金收益结转时必填，填写返还的销售服务费</p></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>113</p></td><td><p>RegistrationDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>权益登记日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>138</p></td><td><p>StampDuty</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>印花税</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>155</p></td><td><p>DividendPerUnit</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>单位基金分红金额(含税)</p></td><td><p>举例：每千份分两元，则此处填2。</p></td><td><p>Y</p></td></tr>
<tr><td><p>187</p></td><td><p>FrozenBalance</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>冻结金额</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>255</p></td><td><p>TransferFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>过户费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>260</p></td><td><p>	ShareClass	</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>276</p></td><td><p>FeeCalculator</p></td><td><p>A</p></td><td><p>1</p></td><td><p>计费人</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>601</p></td><td><p>DrawBonusUnit</p></td><td><p>N</p></td><td><p>10</p></td><td><p>分红单位</p></td><td><p>举例：每千份分多少，则分红单位就为一千</p></td><td><p>Y</p></td></tr>
<tr><td><p>602</p></td><td><p>FrozenSharesforReinvest</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>冻结再投资份额</p></td><td><p>再投资份额中被续冻的部分</p></td><td><p>Y</p></td></tr>
<tr><td><p>256</p></td><td><p>Fromtaflag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>543</p></td><td><p>AchievementPay</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>业绩报酬</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>544</p></td><td><p>AchievementCompen</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>业绩补偿</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>354</p></td><td><p>DividendType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>分红类型</p></td><td></td><td><p>Y</p></td></tr>
</table>

### 4.5.28. 强增业务数据项144

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>89</p></td><td><p>OriginalSerialNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA的原确认流水号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>132</p></td><td><p>ApplicationVol</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>申请基金份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>150</p></td><td><p>ValidPeriod</p></td><td><p>N</p></td><td><p>2</p></td><td><p>交易申请有效天数</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>261</p></td><td><p>OriginalCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>TA的原确认日期</p></td><td><p>指定赎回、指定份额明细的柜台业务（如强制调整、强制赎回、非交易过户出）时指定的过户日期</p></td><td><p>N</p></td></tr>
<tr><td><p>264</p></td><td><p>DetailFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>明细标志</p></td><td><p>对一笔业务，可以返回一笔非明细确认，或一笔非明细确认和多笔明细确认。明细确认是针对过户日或TA确认流水号的确认记录。</p></td><td><p>Y</p></td></tr>
<tr><td><p>603</p></td><td><p>SharesAdjustmentFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>份额强制调整标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>562</p></td><td><p>GeneralTASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>总TA确认流水号</p></td><td><p>用于发送交易明细</p></td><td><p>N</p></td></tr>
<tr><td><p>95</p></td><td><p>OtherFee2</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其它费2</p></td><td><p>货币基金收益结转时必填，填写返还的销售服务费</p></td><td><p>N</p></td></tr>
</table>

### 4.5.29. 强减业务数据项145

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>交易确认份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>89</p></td><td><p>OriginalSerialNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA的原确认流水号</p></td><td><p>指定赎回、指定份额明细的柜台业务（如强制调整、强制赎回、非交易过户出）时该值有意义</p></td><td><p>N</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>132</p></td><td><p>ApplicationVol</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>申请基金份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>150</p></td><td><p>ValidPeriod</p></td><td><p>N</p></td><td><p>2</p></td><td><p>交易申请有效天数</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>261</p></td><td><p>OriginalCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>TA的原确认日期</p></td><td><p>指定赎回、指定份额明细的柜台业务（如强制调整、强制赎回、非交易过户出）时指定的过户日期</p></td><td><p>N</p></td></tr>
<tr><td><p>264</p></td><td><p>DetailFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>明细标志</p></td><td><p>对一笔业务，可以返回一笔非明细确认，或一笔非明细确认和多笔明细确认。明细确认是针对过户日或TA确认流水号的确认记录。</p></td><td><p>Y</p></td></tr>
<tr><td><p>603</p></td><td><p>SharesAdjustmentFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>份额强制调整标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>562</p></td><td><p>GeneralTASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>总TA确认流水号</p></td><td><p>用于发送交易明细</p></td><td><p>N</p></td></tr>
</table>

### 4.5.30. 开通定期定额协议业务数据项159

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>40</p></td><td><p>DateOfPeriodicSubs</p></td><td><p>A</p></td><td><p>8</p></td><td><p>定时定额申购日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>134</p></td><td><p>ApplicationAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请金额</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>A</p></td><td><p>20</p></td><td><p>TA确认交易流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>165</p></td><td><p>ContractNo</p></td><td><p>A</p></td><td><p>20</p></td><td><p>合约编号</p></td><td><p>冻结的法律文书编号等</p></td><td><p>N</p></td></tr>
<tr><td><p>191</p></td><td><p>TermOfPeriodicSubs</p></td><td><p>N</p></td><td><p>5</p></td><td><p>定时定额申购期限</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>269</p></td><td><p>BeginDateOfPeriodicSubs</p></td><td><p>A</p></td><td><p>8</p></td><td><p>定时定额申购起始日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>270</p></td><td><p>EndDateOfPeriodicSubs</p></td><td><p>A</p></td><td><p>8</p></td><td><p>定时定额申购终止日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>271</p></td><td><p>SendDayOfPeriodicSubs</p></td><td><p>N</p></td><td><p>2</p></td><td><p>定时定额申购每月发送日</p></td><td><p>如果遇非交易日，则顺延到下一交易日。考虑到闰月，尽量设在28号以前的日期</p></td><td><p>N</p></td></tr>
<tr><td><p>538</p></td><td><p>RationKind</p></td><td><p>C</p></td><td><p>3</p></td><td><p>定期定额品种号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>607</p></td><td><p>RationNo</p></td><td><p>C</p></td><td><p>3</p></td><td><p>定期定额序号</p></td><td></td><td><p>N</p></td></tr>
</table>

### 4.5.31. 撤销定期定额协议业务数据项160

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>134</p></td><td><p>ApplicationAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请金额</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认交易流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>165</p></td><td><p>ContractNo</p></td><td><p>A</p></td><td><p>20</p></td><td><p>合约编号</p></td><td><p>冻结的法律文书编号等</p></td><td><p>N</p></td></tr>
<tr><td><p>538</p></td><td><p>RationKind</p></td><td><p>C</p></td><td><p>3</p></td><td><p>定期定额品种号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>607</p></td><td><p>RationNo</p></td><td><p>C</p></td><td><p>3</p></td><td><p>定期定额序号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
</table>

### 4.5.32. 变更定期定额协议业务数据项161

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>40</p></td><td><p>DateOfPeriodicSubs</p></td><td><p>A</p></td><td><p>8</p></td><td><p>定时定额申购日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>134</p></td><td><p>ApplicationAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请金额</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>165</p></td><td><p>ContractNo</p></td><td><p>A</p></td><td><p>20</p></td><td><p>合约编号</p></td><td><p>冻结的法律文书编号等</p></td><td><p>N</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>269</p></td><td><p>BeginDateOfPeriodicSubs</p></td><td><p>A</p></td><td><p>8</p></td><td><p>定时定额申购起始日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>270</p></td><td><p>EndDateOfPeriodicSubs</p></td><td><p>A</p></td><td><p>8</p></td><td><p>定时定额申购终止日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>271</p></td><td><p>SendDayOfPeriodicSubs</p></td><td><p>N</p></td><td><p>2</p></td><td><p>定时定额申购每月发送日</p></td><td><p>如果遇非交易日，则顺延到下一交易日。考虑到闰月，尽量设在28号以前的日期</p></td><td><p>N</p></td></tr>
<tr><td><p>538</p></td><td><p>RationKind</p></td><td><p>C</p></td><td><p>3</p></td><td><p>定期定额品种号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>607</p></td><td><p>RationNo</p></td><td><p>C</p></td><td><p>3</p></td><td><p>定期定额序号</p></td><td></td><td><p>N</p></td></tr>
</table>

### 4.5.33. 募集失败149

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售机构不能重复</p></td><td><p>Y</p></td></tr>
<tr><td><p>28</p></td><td><p>DepositAcct</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人在销售人处用于交易的资金账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>64</p></td><td><p>ConfirmedAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认金额</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>76</p></td><td><p>Interest</p></td><td><p>N</p></td><td><p>16（两位小数）　</p></td><td><p>基金账户利息金额</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD指认购交易申请日期</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>134</p></td><td><p>ApplicationAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请金额</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>225</p></td><td><p>RaiseInterest</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>认购期间利息</p></td><td><p>因认购二次确认失败而退还给投资人的利息</p></td><td><p>Y</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>276</p></td><td><p>FeeCalculator</p></td><td><p>A</p></td><td><p>1</p></td><td><p>计费人</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>156</p></td><td><p>InterestTax</p></td><td><p>N</p></td><td><p>16(两位小数)　</p></td><td><p>利息税</p></td><td></td><td><p>Y</p></td></tr>
</table>

## 4.6. 文件汇总数据项

### 4.6.1. 账户确认92/Z2、账户增量对账D2/U2、账户全量对账Q2/S2

1) 账户确认文件报送每日TA确认给销售机构的所有账户业务,只报送成功业务，成功业务返回代码为‘0000’。

2) 账户确认文件业务代码包括101/102/103/108/109/158/ZGT。各业务必填字段参照‘业务数据项’章节。对账户柜台修改业务（业务代码ZGT，指TA发起的柜台修改账户信息业务），除92文件要求的必填字段外，还应包括所有修改的字段（指改后的内容），比如账户资料、账户状态，若不涉及销售人代码、网点号码、交易账号，这些字段可赋值为空(若涉及则需赋值)。若修改交易账户状态，应填写‘销售人代码+网点号码+投资人交易账号’。

3) 账户增量对账指每日基金账户资料或基金账户状态（新开、销户等）发生变化后，报送这些基金账户最终的账户资料及状态，每个基金账户一条记录，业务代码‘114’；交易账户状态（新开、销户等）发生变化后，报送这些交易账户最终的状态（每个‘基金账户+销售人代码+网点号码+投资人交易账号’一条记录，业务代码‘115’）。当变更交易账户（158）业务成功后，增量对账中应包含两条115业务记录，即‘旧交易账号’（状态为注销）、‘新交易账号’（如为新开，应有一条状态为‘正常’的记录），新旧交易账号都填写在‘投资人交易账号’字段中。

4) 114业务填写基金账户层面的内容，必填完整的基金账户资料及‘基金账户状态/最后修改日期/开户日期/’，‘销售人代码/网点号码/投资人交易账号/交易账户状态’字段置空。 若TA对同一基金账户存有多套账户资料，报送最后修改的那一套账户资料。

115业务填写交易账户层面的内容，必填‘基金账户/销售人代码/网点号码/投资人交易账号/交易账户状态/最后修改日期/开户日期/账户特征值’，不填账户资料和‘基金账户状态’。

5) 账户全量对账包括基金账户对账（业务代码‘114’）、交易账户对账（业务代码‘115’）。基金账户全量对账应包含所有基金账户，包括‘基金账户状态’为‘注销’的账户；交易账户全量对账应包含所有交易账户，包括（基金账户+销售人代码+网点号码+投资人交易账号）状态为‘注销’的记录。

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否</p><p>必需</p></td></tr>
<tr><td><p>4</p></td><td><p>Address</p></td><td><p>C</p></td><td><p>300</p></td><td><p>通讯地址</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>5</p></td><td><p>InstReprIDCode</p></td><td><p>C</p></td><td><p>40</p></td><td><p>法人代表身份证件代码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>6</p></td><td><p>InstReprIDType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>法人代表证件类型</p></td><td><p>参考数据字典“证件类型”中的个人部分</p></td><td><p>N</p></td></tr>
<tr><td><p>7</p></td><td><p>InstReprName</p></td><td><p>C</p></td><td><p>60</p></td><td><p>法人代表姓名</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>源自代销机构的申请单编号</p></td><td><p>N</p></td></tr>
<tr><td><p>19</p></td><td><p>AcctNoOfFMInClearingAgency</p></td><td><p>C</p></td><td><p>28</p></td><td><p>基金管理人在资金清算机构的交收账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>20</p></td><td><p>AcctNameOfFMInClearingAgency</p></td><td><p>C</p></td><td><p>60</p></td><td><p>基金管理人在资金清算机构的交收账户名</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>21</p></td><td><p>ClearingAgencyCode</p></td><td><p>A</p></td><td><p>9</p></td><td><p>基金资金清算机构代码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>23</p></td><td><p>InvestorsBirthday</p></td><td><p>A</p></td><td><p>8</p></td><td><p>投资人出生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>24</p></td><td><p>DefDividendMethod</p></td><td><p>A</p></td><td><p>1</p></td><td><p>默认分红方式</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>26</p></td><td><p>PagerNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>投资人传呼机号码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>27</p></td><td><p>CertificateType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>证件类型</p></td><td><p>基金账户资料必填信息</p></td><td><p>N</p></td></tr>
<tr><td><p>28</p></td><td><p>DepositAcct</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人在销售人处用于交易的资金账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>48</p></td><td><p>EducationLevel</p></td><td><p>C</p></td><td><p>3</p></td><td><p>投资人学历</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>49</p></td><td><p>EmailAddress</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人E-MAIL地址</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>51</p></td><td><p>FaxNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人传真号码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>58</p></td><td><p>FreezingDeadline</p></td><td><p>A</p></td><td><p>8</p></td><td><p>冻结截止日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>60</p></td><td><p>FrozenCause</p></td><td><p>A</p></td><td><p>1</p></td><td><p>冻结原因</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>65</p></td><td><p>VocationCode</p></td><td><p>C</p></td><td><p>5</p></td><td><p>投资人职业代码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>69</p></td><td><p>HomeTelNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人住址电话</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>72</p></td><td><p>CertificateNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人证件号码</p></td><td><p>基金账户资料必填信息</p></td><td><p>N</p></td></tr>
<tr><td><p>73</p></td><td><p>AnnualIncome</p></td><td><p>N</p></td><td><p>16</p></td><td><p>投资人年收入</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>83</p></td><td><p>MobileTelNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人手机号码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>84</p></td><td><p>MultiAcctFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>多渠道开户标志</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>85</p></td><td><p>InvestorName</p></td><td><p>C</p></td><td><p>200</p></td><td><p>投资人户名</p></td><td><p>基金账户资料必填信息</p></td><td><p>N</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>88</p></td><td><p>OfficeTelNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人单位电话号码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>89</p></td><td><p>OriginalSerialNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA的原确认流水号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>90</p></td><td><p>OriginalAppSheetNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>原申请单编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td><p>基金账户资料必填信息</p></td><td><p>N</p></td></tr>
<tr><td><p>101</p></td><td><p>PostCode</p></td><td><p>A</p></td><td><p>6</p></td><td><p>投资人邮政编码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>106</p></td><td><p>TransactorCertNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>经办人证件号码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>107</p></td><td><p>TransactorCertType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>经办人证件类型</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>108</p></td><td><p>TransactorName</p></td><td><p>C</p></td><td><p>60</p></td><td><p>经办人姓名</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td><p>销售机构有代码则必填，若无填写基金业协会登记的管理人编码；若无则填写组织机构代码</p></td><td><p>N</p></td></tr>
<tr><td><p>122</p></td><td><p>AccountAbbr</p></td><td><p>C</p></td><td><p>20</p></td><td><p>投资人户名简称</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>124</p></td><td><p>ConfidentialDocumentCode</p></td><td><p>C</p></td><td><p>8</p></td><td><p>密函编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>126</p></td><td><p>Sex</p></td><td><p>A</p></td><td><p>1</p></td><td><p>投资人性别</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>127</p></td><td><p>SHSecuritiesAccountID</p></td><td><p>C</p></td><td><p>10</p></td><td><p>上海证券账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>128</p></td><td><p>SZSecuritiesAccountID</p></td><td><p>C</p></td><td><p>10</p></td><td><p>深圳证券账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td><p>TA确认给销售机构的业务必填。</p><p>TA对每笔确认的唯一标识，同一日不能重复，</p><p>与交易确认日期TransactionCfmDate一起组成TA中一笔确认的唯一键</p></td><td><p>N</p></td></tr>
<tr><td><p>140</p></td><td><p>TelNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人电话号码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>142</p></td><td><p>TargetTransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>对方销售人处投资人交易账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>164</p></td><td><p>TradingMethod</p></td><td><p>C</p></td><td><p>8</p></td><td><p>使用的交易手段</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>167</p></td><td><p>MinorFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>未成年人标志</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>168</p></td><td><p>MinorID</p></td><td><p>C</p></td><td><p>18</p></td><td><p>未成年人ID号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>169</p></td><td><p>DeliverType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>对帐单寄送选择</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>170</p></td><td><p>TransactorIDType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>经办人识别方式</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>171</p></td><td><p>AccountCardID</p></td><td><p>C</p></td><td><p>8</p></td><td><p>基金账户卡的凭证号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>256</p></td><td><p>Fromtaflag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>261</p></td><td><p>OriginalCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>TA的原确认日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>265</p></td><td><p>DeliverWay</p></td><td><p>C</p></td><td><p>8</p></td><td><p>对帐单寄送方式</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>268</p></td><td><p>AccountStatus</p></td><td><p>A</p></td><td><p>1</p></td><td><p>基金账户状态</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>524</p></td><td><p>NetNo</p></td><td><p>C</p></td><td><p>9</p></td><td><p>操作网点编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>606</p></td><td><p>TransactionAccountStatus</p></td><td><p>C</p></td><td><p>1</p></td><td><p>交易账户状态</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>325</p></td><td><p>InstitutionType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>机构类型</p></td><td><p>对开户业务，机构和产品要求必填</p></td><td><p>N</p></td></tr>
<tr><td><p>665</p></td><td><p>InvestorProCode</p></td><td><p>C</p></td><td><p>30</p></td><td><p>投资者产品代码</p></td><td><p>对开户业务，投资者为公募基金产品或基金业协会备案产品时必填，填写行业编码中心分配的编码或协会备案产品编码</p></td><td><p>N</p></td></tr>
<tr><td><p>522</p></td><td><p>Nationality</p></td><td><p>C</p></td><td><p>3</p></td><td><p>投资者国家或地区</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>286</p></td><td><p>CertValidDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>证件有效日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>287</p></td><td><p>InstTranCertValidDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>机构经办人身份证件有效日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>288</p></td><td><p>InstReprCertValidDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>机构法人身份证件有效日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>289</p></td><td><p>ClientRiskRate</p></td><td><p>C</p></td><td><p>1</p></td><td><p>客户风险等级</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>715</p></td><td><p>AuxCertType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>辅助身份证明文件类型</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>716</p></td><td><p>AuxCertCode</p></td><td><p>C</p></td><td><p>40</p></td><td><p>辅助身份证明文件号码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>717</p></td><td><p>AuxCertValidDate</p></td><td><p>C</p></td><td><p>8</p></td><td><p>辅助身份证明文件有效日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>732</p></td><td><p>IPAddress</p></td><td><p>C</p></td><td><p>40</p></td><td><p>IP地址</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>735</p></td><td><p>MACAddress</p></td><td><p>C</p></td><td><p>20</p></td><td><p>MAC地址</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>739</p></td><td><p>IMEI</p></td><td><p>C</p></td><td><p>20</p></td><td><p>国际移动设备识别码</p></td><td><p>用于移动终端为Android操作系统版本时</p></td><td><p>N</p></td></tr>
<tr><td><p>740</p></td><td><p>UUID</p></td><td><p>C</p></td><td><p>32</p></td><td><p>通用唯一识别码</p></td><td><p>用于移动终端为iOS操作系统版本时</p></td><td><p>N</p></td></tr>
<tr><td><p>752</p></td><td><p>LastChangeDate</p></td><td><p>C</p></td><td><p>8</p></td><td><p>最后修改日期</p></td><td><p>最后一次修改账户资料或状态的日期</p></td><td><p>N</p></td></tr>
<tr><td><p>755</p></td><td><p>InvestAdviserCode</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投顾机构代码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>756</p></td><td><p>AccChar</p></td><td><p>C</p></td><td><p>30</p></td><td><p>账户特征值</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>753</p></td><td><p>OpenAccDate</p></td><td><p>C</p></td><td><p>8</p></td><td><p>开户日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>2418</p></td><td><p>Detail</p></td><td><p>C</p></td><td><p>200</p></td><td><p>详细信息</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>635</p></td><td><p>ReservedField1</p></td><td><p>C</p></td><td><p>20</p></td><td><p>预留字段1</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>636</p></td><td><p>ReservedField2</p></td><td><p>C</p></td><td><p>20</p></td><td><p>预留字段2</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>637</p></td><td><p>ReservedField3</p></td><td><p>C</p></td><td><p>30</p></td><td><p>预留字段3</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>638</p></td><td><p>ReservedField4</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>预留字段4</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>639</p></td><td><p>ReservedField5</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>预留字段5</p></td><td></td><td><p>N</p></td></tr>
</table>

### 4.6.2. 交易确认94(Z4)

1) 只报送成功业务和募集失败‘149’，成功业务返回代码为‘0000’。

2) ‘明细标志’为‘非明细’的记录必须报送。不报送‘明细标志’为‘明细’的记录。

3) 对一步转托管业务（含跨市场转托管），拆分为三笔业务（126/127/128）报送，三笔业务的‘申请单编号’、‘TA确认流水号’应相同。对两步转托管业务，第一步视为转出方销售机构转至虚拟销售机构(销售人代码‘000’)，拆分为三笔业务（126/127/128）报送，三笔业务的‘申请单编号’、‘TA确认流水号’应相同；第二步视为虚拟销售机构(销售人代码‘000’)转至转入方销售机构，拆分为三笔业务（126/127/128）报送，三笔业务的‘申请单编号’、‘TA确认流水号’应相同，且第二步的‘原申请单编号’、‘TA的原确认流水号’字段应填写第一步的‘申请单编号’、‘TA确认流水号’。对非交易过户业务，报送一笔‘133’（对跨销售人的非交易过户，必填‘对方销售人代码’。无论一步还是两步完成，TA应在整个业务完成后再报送。对业务未完成的，视为业务尚未发生，即对账95文件中的份额保持不变）。对快速过户业务，报送一笔‘198’（注意：若由198业务引发赎回业务，要报送124）。对同一TA的基金转换业务，拆分为三笔业务（136/137/138）报送,三笔业务的‘申请单编号’、‘TA确认流水号’应相同；若为不同TA的基金之间的转换，业务代码应根据TA为转出方或转入方分别填写138（基金转换出）或137（基金转换入），转出方TA和转入方TA各自报送一笔。对销售机构为方便投资者设置的“超级转换”（实际上两只基金并无转换关系），不应报送136，仍按一笔申购和一笔赎回业务申报。

4) 各业务必填字段参照‘业务数据项’章节。

5) 投资者的同一笔业务，不能以多种形式重复出现。货币基金收益按份额结转，须在94文件中以“144-强增”、“145-强减”业务进行报送（“份额强制调整标志”填写“4-货币基金收益结转”）,不允许在96分红文件中以‘143分红’业务进行报送。货币基金收益以现金方式下发，须在96分红文件中以‘143分红’业务进行报送，“分红类型”填写“2-货币基金收益结转”。

6) 对于交换数据中出现的“收费方式”字段取值为‘2-前后收费共用（基金代码）’的，报送备份时应根据TA实际处理情况报送，比如拆解到前、后收费基金代码上报送两条，不允许出现‘2-前后收费共用（基金代码）’。

7) 对首发产品，从TA系统中生成认购业务120（或认购结果业务130）开始，就应报送。

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否</p><p>必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>24</p></td><td><p>DefDividendMethod</p></td><td><p>A</p></td><td><p>1</p></td><td><p>默认分红方式</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>25</p></td><td><p>DiscountRateOfCommission</p></td><td><p>N</p></td><td><p>5(四位小数)</p></td><td><p>销售佣金折扣率</p></td><td><p>代销机构上传的折扣率</p></td><td><p>N</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>34</p></td><td><p>CodeOfTargetFund</p></td><td><p>C</p></td><td><p>6</p></td><td><p>转换时的目标基金代码</p></td><td><p>基金转换业务必填</p></td><td><p>N</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>52</p></td><td><p>Charge</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>手续费</p></td><td><p>不含后收费和补差费</p></td><td><p>Y</p></td></tr>
<tr><td><p>53</p></td><td><p>AgencyFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>代理费</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>55</p></td><td><p>TotalTransFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>交易确认费用合计</p></td><td><p>投资者应付费用总和</p></td><td><p>Y</p></td></tr>
<tr><td><p>58</p></td><td><p>FreezingDeadline</p></td><td><p>A</p></td><td><p>8</p></td><td><p>冻结截止日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>60</p></td><td><p>FrozenCause</p></td><td><p>A</p></td><td><p>1</p></td><td><p>冻结原因</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认份数</p></td><td><p>对需要份额确认的业务必填</p></td><td><p>N</p></td></tr>
<tr><td><p>64</p></td><td><p>ConfirmedAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易确认金额</p></td><td><p>对需要金额确认的业务必填</p></td><td><p>N</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>76</p></td><td><p>Interest</p></td><td><p>N</p></td><td><p>16（两位小数）)</p></td><td><p>基金账户利息金额</p></td><td><p>对于130和149业务必填</p></td><td><p>N</p></td></tr>
<tr><td><p>80</p></td><td><p>LargeRedemptionFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>巨额赎回处理标志</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>86</p></td><td><p>NAV</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>基金单位净值</p></td><td><p>净值单位与币种单位一致</p></td><td><p>N</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>89</p></td><td><p>OriginalSerialNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA的原确认流水号</p></td><td><p>指定份额明细的份额减少类业务时该值有意义</p></td><td><p>N</p></td></tr>
<tr><td><p>90</p></td><td><p>OriginalAppSheetNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>原申请单编号</p></td><td><p>1、 	两步转托管的转入时填写原来转出的申请单号。</p><p>2、 	解冻时填写原来的冻结申请单号</p><p>3、 	取消协议时填写原来申请协议的申请单号</p></td><td><p>N</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>格式为：HHMMSS</p></td><td><p>N</p></td></tr>
<tr><td><p>94</p></td><td><p>OtherFee1</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>其它费1</p></td><td><p>归基金资产费　</p></td><td><p>N</p></td></tr>
<tr><td><p>95</p></td><td><p>OtherFee2</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其它费2</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>96</p></td><td><p>OtherFee3</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其它费3</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>97</p></td><td><p>TargetDistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>对方销售人代码</p></td><td><p>对方销售机构有代码则必填，若无填写基金业协会登记的管理人编码；若无则填写组织机构代码</p></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>102</p></td><td><p>RedemptionDateInAdvance</p></td><td><p>A</p></td><td><p>8</p></td><td><p>预约赎回日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td><p>销售机构有代码则必填，若无填写基金业协会登记的管理人编码；若无则填写组织机构代码</p></td><td><p>Y</p></td></tr>
<tr><td><p>132</p></td><td><p>ApplicationVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请基金份数</p></td><td><p>份额申请类业务必填</p></td><td><p>N</p></td></tr>
<tr><td><p>134</p></td><td><p>ApplicationAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请金额</p></td><td><p>金额申请类业务必填</p></td><td><p>N</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>编码见表1</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>138</p></td><td><p>StampDuty</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>印花税</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>141</p></td><td><p>TargetBranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>对方网点号</p></td><td><p>非交易过户和转托管时使用</p></td><td><p>N</p></td></tr>
<tr><td><p>142</p></td><td><p>TargetTransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>对方销售人处投资人交易账号</p></td><td><p>非交易过户和转托管时使用</p></td><td><p>N</p></td></tr>
<tr><td><p>147</p></td><td><p>TargetTAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>对方基金账号</p></td><td><p>非交易过户和跨市场转托管时使用</p></td><td><p>N</p></td></tr>
<tr><td><p>152</p></td><td><p>TargetRegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>对方所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>161</p></td><td><p>CfmVolOfTargetFund</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>目标基金的确认份数</p></td><td><p>基金转换业务必填</p></td><td><p>N</p></td></tr>
<tr><td><p>162</p></td><td><p>TargetNAV</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>目标基金的单位净值</p></td><td><p>基金转换业务必填</p></td><td><p>N</p></td></tr>
<tr><td><p>560</p></td><td><p>ManagerRealRatio</p></td><td><p>N</p></td><td><p>7,4</p></td><td><p>实际计算折扣</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>254</p></td><td><p>Specification</p></td><td><p>C</p></td><td><p>60</p></td><td><p>摘要说明</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>255</p></td><td><p>TransferFee</p></td><td><p>N</p></td><td><p>16（两位小数）)</p></td><td><p>过户费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>257</p></td><td><p>FrozenMethod</p></td><td><p>A</p></td><td><p>1</p></td><td><p>冻结方式</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>258</p></td><td><p>OriginalAppDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>原申请日期</p></td><td><p>格式为：YYYYMMDD</p><p>预约赎回到期后的024业务有值</p></td><td><p>N</p></td></tr>
<tr><td><p>260</p></td><td><p>	ShareClass	</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>261</p></td><td><p>OriginalCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>TA的原确认日期</p></td><td><p>指定份额明细的份额减少类业务时该值有意义</p></td><td><p>N</p></td></tr>
<tr><td><p>262</p></td><td><p>RedemptionInAdvanceFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>预约赎回标志</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>263</p></td><td><p>RedemptionReason</p></td><td><p>A</p></td><td><p>1</p></td><td><p>强制赎回原因</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>264</p></td><td><p>DetailFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>明细标志</p></td><td><p>0-非明细，1-明细</p></td><td><p>Y</p></td></tr>
<tr><td><p>266</p></td><td><p>VolumeByInterest</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金账户利息金额转份额</p></td><td><p>若有则必填</p></td><td><p>N</p></td></tr>
<tr><td><p>507</p></td><td><p>UndistributeMonetaryIncome</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>货币基金未付收益金额</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>510</p></td><td><p>UndistributeMonetaryIncomeFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>货币基金未付收益金额正负</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>300</p></td><td><p>BreachFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>违约金</p></td><td><p>若有则必填</p></td><td><p>N</p></td></tr>
<tr><td><p>306</p></td><td><p>BreachFeeBackToFund</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>违约金归基金资产金额</p></td><td><p>若有则必填</p></td><td><p>N</p></td></tr>
<tr><td><p>305</p></td><td><p>PunishFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>惩罚性费用</p></td><td><p>若有则必填</p></td><td><p>N</p></td></tr>
<tr><td><p>526</p></td><td><p>TargetShareType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>对方基金份额类别</p></td><td><p>基金转换业务必填</p></td><td><p>N</p></td></tr>
<tr><td><p>541</p></td><td><p>RecuperateFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>补差费</p></td><td><p>若有则必填</p></td><td><p>N</p></td></tr>
<tr><td><p>543</p></td><td><p>AchievementPay</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>业绩报酬</p></td><td><p>若有则必填</p></td><td><p>N</p></td></tr>
<tr><td><p>544</p></td><td><p>AchievementCompen</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>业绩补偿</p></td><td><p>若有则必填</p></td><td><p>N</p></td></tr>
<tr><td><p>617</p></td><td><p>TargetRegistrarCode</p></td><td><p>C</p></td><td><p>18</p></td><td><p>对方TA代码</p></td><td><p>跨TA基金转换时必填</p></td><td><p>N</p></td></tr>
<tr><td><p>28</p></td><td><p>DepositAcct</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人在销售人处用于交易的资金账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>133</p></td><td><p>TradingPrice</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>交易价格</p></td><td><p>投资者的单位交易成本</p></td><td><p>N</p></td></tr>
<tr><td><p>225</p></td><td><p>RaiseInterest</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>认购期间利息</p></td><td><p>对于130和149业务必填</p></td><td><p>N</p></td></tr>
<tr><td><p>603</p></td><td><p>SharesAdjustmentFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>份额强制调整标志</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>150</p></td><td><p>ValidPeriod</p></td><td><p>N</p></td><td><p>2</p></td><td><p>交易申请有效天数</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>177</p></td><td><p>BusinessFinishFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>业务过程完全结束标识</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>276</p></td><td><p>FeeCalculator</p></td><td><p>A</p></td><td><p>1</p></td><td><p>计费人</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>506</p></td><td><p>HandleCharge</p></td><td><p>N</p></td><td><p>16（两位小数）　</p></td><td><p>经手费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>193</p></td><td><p>RateFee</p></td><td><p>N</p></td><td><p>9(八位小数)</p></td><td><p>费率</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>156</p></td><td><p>InterestTax</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>利息税</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>562</p></td><td><p>GeneralTASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>总TA确认流水号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>165</p></td><td><p>ContractNo</p></td><td><p>A</p></td><td><p>20</p></td><td><p>合约编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>173</p></td><td><p>TotalBackendLoad</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>交易后端收费总额</p></td><td><p>后收手续费，若有则必填</p></td><td><p>N</p></td></tr>
<tr><td><p>176</p></td><td><p>TransferDirection</p></td><td><p>A</p></td><td><p>1</p></td><td><p>转入/转出标识</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>538</p></td><td><p>RationKind</p></td><td><p>C</p></td><td><p>3</p></td><td><p>定期定额品种代码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>607</p></td><td><p>RationNo</p></td><td><p>C</p></td><td><p>3</p></td><td><p>定期定额序号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>40</p></td><td><p>DateOfPeriodicSubs</p></td><td><p>A</p></td><td><p>8</p></td><td><p>定时定额申购日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>271</p></td><td><p>SendDayOfPeriodicSubs</p></td><td><p>N</p></td><td><p>2</p></td><td><p>定时定额申购每月发送日</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>191</p></td><td><p>TermOfPeriodicSubs</p></td><td><p>N</p></td><td><p>5</p></td><td><p>定时定额申购期限</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>269</p></td><td><p>BeginDateOfPeriodicSubs</p></td><td><p>A</p></td><td><p>8</p></td><td><p>定时定额申购起始日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>270</p></td><td><p>EndDateOfPeriodicSubs</p></td><td><p>A</p></td><td><p>8</p></td><td><p>定时定额申购终止日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>386</p></td><td><p>ChangeAgencyFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>转换代理费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>387</p></td><td><p>RecuperateAgencyFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>补差代理费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>283</p></td><td><p>RefundAmount</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>退款金额</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>327</p></td><td><p>TakeIncomeFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>带走收益标志</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>303</p></td><td><p>ForceRedemptionType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>强制赎回类型</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>730</p></td><td><p>TransferReason</p></td><td><p>C</p></td><td><p>3</p></td><td><p>过户原因</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>732</p></td><td><p>IPAddress</p></td><td><p>C</p></td><td><p>40</p></td><td><p>IP地址</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>735</p></td><td><p>MACAddress</p></td><td><p>C</p></td><td><p>20</p></td><td><p>MAC地址</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>739</p></td><td><p>IMEI</p></td><td><p>C</p></td><td><p>20</p></td><td><p>国际移动设备识别码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>740</p></td><td><p>UUID</p></td><td><p>C</p></td><td><p>32</p></td><td><p>通用唯一识别码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>181</p></td><td><p>AcctNameOfInvestorInClearingAgency</p></td><td><p>C</p></td><td><p>200</p></td><td><p>投资人收款银行账户户名</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>182</p></td><td><p>AcctNoOfInvestorInClearingAgency</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人收款银行账户账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>183</p></td><td><p>ClearingAgency</p></td><td><p>C</p></td><td><p>20</p></td><td><p>投资人收款银行账户开户行</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>2418</p></td><td><p>Detail</p></td><td><p>C</p></td><td><p>200</p></td><td><p>详细信息</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>635</p></td><td><p>ReservedField1</p></td><td><p>C</p></td><td><p>20</p></td><td><p>预留字段1</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>636</p></td><td><p>ReservedField2</p></td><td><p>C</p></td><td><p>20</p></td><td><p>预留字段2</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>637</p></td><td><p>ReservedField3</p></td><td><p>C</p></td><td><p>30</p></td><td><p>预留字段3</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>638</p></td><td><p>ReservedField4</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>预留字段4</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>639</p></td><td><p>ReservedField5</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>预留字段5</p></td><td></td><td><p>N</p></td></tr>
</table>

### 4.6.3. 份额对帐95(Z5/Q5/S5)

1) 增量对账报送时注意：若投资者上日份额不为零但当日清零（包括因变更交易账号导致的原交易账号份额清零），也需报送。由于网点号码变更导致份额转移到新的网点号码，应报送两条记录，原网点号码下份额为零的记录、以及新网点号码下的份额记录。

2) ‘明细标志’为‘1-按投资者汇总’、‘0-按基金汇总’、‘3-按（基金+销售机构）汇总’的记录，要求必须报送。‘明细标志’为‘2-按投资者明细’的不报送。

‘0’指按基金代码、收费类别汇总的数据（此方式下销售人代码、网点号码、基金账号、交易账号不填）；‘3’指按基金代码、收费类别、销售机构汇总的数据（此方式下网点号码、基金账号、交易账号不填）；‘1’指按投资者汇总（按登记六要素即基金账号、交易账号、基金代码、收费类别、销售人代码、网点号码）对账；‘2’指按投资者明细（在登记六要素基础上，增加份额注册日期或TA确认流水号）对账。

3) 对‘明细标志’为‘1-按投资者汇总’的记录，‘基金总份数’、‘持有人可用基金份数’、‘基金冻结总份数’指该（基金账户+交易账户）持有的基金份数、可用份数、冻结份数。

按基金汇总的记录（明细标志‘0’）：无论增量或全量，每基金代码、收费类别都应有一条记录。‘基金总份数’、‘持有人可用基金份数’、‘基金冻结总份数’指该（基金代码+收费类别）的总份数、可用份数、冻结份数。

按（基金+销售机构）汇总的记录（明细标志‘3’）：无论增量或全量，每基金代码、收费类别、销售人代码都应有一条记录（该记录若份额为零也要报），	‘基金总份数’、‘持有人可用基金份数’、‘基金冻结总份数’指该（基金代码+收费类别+销售人代码）的总份数、可用份数、冻结份数。

4) 对于没有记在任何销售机构名下的挂账份额（比如两步转托管已转出但未转入的份额），销售人代码填写‘000’（表示虚拟）。

5) 发送全量份额对账时，应包含所有曾持有份额的基金账户，包括当前份额已清零的基金账户。

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否</p><p>必需</p></td></tr>
<tr><td><p>13</p></td><td><p>AvailableVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>持有人可用基金份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>18</p></td><td><p>TotalVolOfDistributorInTA</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金总份数(含冻结)</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>24</p></td><td><p>DefDividendMethod</p></td><td><p>A</p></td><td><p>1</p></td><td><p>分红方式</p></td><td><p>‘明细标志’为‘1-按投资者汇总’时必填</p></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>59</p></td><td><p>TotalFrozenVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金冻结总份数</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td><p>销售机构有代码则必填，若无填写基金业协会登记的管理人编码；若无则填写组织机构代码</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td><p>份额明细对账时必填</p></td><td><p>N</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>264</p></td><td><p>DetailFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>明细标志</p></td><td><p>0-按基金汇总</p><p>1-按投资者汇总</p><p>2-按投资者明细</p><p>3-按（基金+销售机构）汇总</p></td><td><p>Y</p></td></tr>
<tr><td><p>274</p></td><td><p>ShareRegisterDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>份额注册日期</p></td><td><p>份额明细对账时必填</p></td><td><p>N</p></td></tr>
<tr><td><p>507</p></td><td><p>UndistributeMonetaryIncome</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>货币基金未付收益金额</p></td><td><p>货币基金必填</p></td><td><p>N</p></td></tr>
<tr><td><p>508</p></td><td><p>GuaranteedAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>剩余保本金额</p></td><td><p>对保本基金</p></td><td><p>N</p></td></tr>
<tr><td><p>510</p></td><td><p>UndistributeMonetaryIncomeFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>货币基金未付收益金额正负</p></td><td><p>货币基金必填</p></td><td><p>N</p></td></tr>
<tr><td><p>527</p></td><td><p>SourceType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>份额来源</p></td><td><p>发送明细对账时必填</p></td><td><p>N</p></td></tr>
<tr><td><p>733</p></td><td><p>NewIncome</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>新增收益</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>734</p></td><td><p>NewIncomeFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>新增收益正负</p></td><td><p>0-正  1-负</p></td><td><p>N</p></td></tr>
<tr><td><p>752</p></td><td><p>LastChangeDate</p></td><td><p>C</p></td><td><p>8</p></td><td><p>最后修改日期</p></td><td><p>‘明细标志’为‘1-按投资者汇总’时必填，填写最后一次修改份额或分红方式的日期</p></td><td><p>N</p></td></tr>
<tr><td><p>635</p></td><td><p>ReservedField1</p></td><td><p>C</p></td><td><p>20</p></td><td><p>预留字段1</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>636</p></td><td><p>ReservedField2</p></td><td><p>C</p></td><td><p>20</p></td><td><p>预留字段2</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>637</p></td><td><p>ReservedField3</p></td><td><p>C</p></td><td><p>30</p></td><td><p>预留字段3</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>638</p></td><td><p>ReservedField4</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>预留字段4</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>639</p></td><td><p>ReservedField5</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>预留字段5</p></td><td></td><td><p>N</p></td></tr>
</table>

### 4.6.4. 分红信息96(Z6)

只报送成功业务，成功业务返回代码为‘0000’。

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否必需</p></td></tr>
<tr><td><p>22</p></td><td><p>BasisforCalculatingDividend</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>红利/红股基数</p></td><td><p>登记日基金持有人的基金份数，允许为0</p></td><td><p>N</p></td></tr>
<tr><td><p>24</p></td><td><p>DefDividendMethod</p></td><td><p>A</p></td><td><p>1</p></td><td><p>默认分红方式</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>28</p></td><td><p>DepositAcct</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人在销售人处用于交易的资金账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>41</p></td><td><p>VolOfDividendforReinvestment</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金账户红利再投资基金份数</p></td><td><p>投资人实得红股，含被续冻的红股</p></td><td><p>Y</p></td></tr>
<tr><td><p>42</p></td><td><p>DividentDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>分红日/发放日</p></td><td><p>现金分红时必填</p></td><td><p>N</p></td></tr>
<tr><td><p>43</p></td><td><p>DividendAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金账户红利资金</p></td><td><p>分红的总金额,含冻结红利及再投资的红利</p></td><td><p>Y</p></td></tr>
<tr><td><p>46</p></td><td><p>XRDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>除权日</p></td><td><p>再投资时必填</p></td><td><p>N</p></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>52</p></td><td><p>Charge</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>手续费</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>53</p></td><td><p>AgencyFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>代理费</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>59</p></td><td><p>TotalFrozenVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金冻结总份数</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>64</p></td><td><p>ConfirmedAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>每笔交易确认金额</p></td><td><p>实发的现金分红金额，不含冻结红利及再投资的红利</p></td><td><p>Y</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>86</p></td><td><p>NAV</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>分红再投资基金净值</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>94</p></td><td><p>OtherFee1</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>其他费用1</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>95</p></td><td><p>OtherFee2</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其他费用2</p></td><td><p>货币基金收益结转时必填，填写返还的销售服务费</p></td><td><p>N</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>113</p></td><td><p>RegistrationDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>权益登记日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>N</p></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构内开设的用于交易的账号</p></td><td><p>Y</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td><p>143</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认流水号</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>138</p></td><td><p>StampDuty</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>印花税</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>155</p></td><td><p>DividendPerUnit</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>单位基金分红金额(含税)</p></td><td><p>举例：每千份分两元，则此处填2。</p></td><td><p>Y</p></td></tr>
<tr><td><p>187</p></td><td><p>FrozenBalance</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>冻结金额</p></td><td><p>冻结的现金分红金额</p></td><td><p>Y</p></td></tr>
<tr><td><p>255</p></td><td><p>TransferFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>过户费</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>276</p></td><td><p>FeeCalculator</p></td><td><p>A</p></td><td><p>1</p></td><td><p>计费人</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>601</p></td><td><p>DrawBonusUnit</p></td><td><p>N</p></td><td><p>10</p></td><td><p>分红单位</p></td><td><p>举例：每千份分多少，则分红单位就为一千</p></td><td><p>Y</p></td></tr>
<tr><td><p>602</p></td><td><p>FrozenSharesforReinvest</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>冻结再投资份额</p></td><td><p>再投资份额中被续冻的部分</p></td><td><p>Y</p></td></tr>
<tr><td><p>256</p></td><td><p>Fromtaflag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>543</p></td><td><p>AchievementPay</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>业绩报酬</p></td><td><p>若有则必填</p></td><td><p>N</p></td></tr>
<tr><td><p>544</p></td><td><p>AchievementCompen</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>业绩补偿</p></td><td><p>若有则必填</p></td><td><p>N</p></td></tr>
<tr><td><p>354</p></td><td><p>DividendType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>分红类型</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>635</p></td><td><p>ReservedField1</p></td><td><p>C</p></td><td><p>20</p></td><td><p>预留字段1</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>636</p></td><td><p>ReservedField2</p></td><td><p>C</p></td><td><p>20</p></td><td><p>预留字段2</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>637</p></td><td><p>ReservedField3</p></td><td><p>C</p></td><td><p>30</p></td><td><p>预留字段3</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>638</p></td><td><p>ReservedField4</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>预留字段4</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>639</p></td><td><p>ReservedField5</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>预留字段5</p></td><td></td><td><p>N</p></td></tr>
</table>

### 4.6.5. 基金TA参数(T1/TM)

本表要求TA报送其系统中全量数据，包括已清盘的基金。

1) 对私募产品，因不同机构对基金代码分配规则不同导致同一产品代码不一致的情况，要求基金正式代码采用基金业协会备案编码。

2) 主基金代码含义：同一基金产品可能有一个或多个编码（因费率水平不同、前后收费、币种不同等会有多个编码），若仅有一个编码，其自身即为主基金代码；若有多个编码，基金管理人选择其一作为主基金代码（主基金代码只能有一个，且不允许变更）。若多个编码分别登记在多个TA，基金管理人需保证各TA填写的主基金代码一致。各TA不得重复报送各编码，比如自建TA不要报送已委托中国结算TA登记的基金代码。数据统计时，归拢同一主基金代码下所有基金代码，作为该产品的数据。

3) 正式代码：基金业协会备案编码或行业编码中心分配的编码，非公募产品仅允许填报基金业协会备案编码。产品获得正式代码之后必须填报此字段，用于将TA系统内使用的基金代码与正式代码建立关联。比如TA系统内使用分级基金代码A和B，管理人选择A作为主基金代码。后获得基金业协会备案编码C和D，其中A对应C，B对应D，则A代码其主基金代码为A，正式代码为C；B代码其主基金代码为A，正式代码为D。

4) 基金类型、基金特征值：对公募基金和证券公司大集合产品，应填写公开信息披露的内容（与产品资料概要文件一致，注意与TA实际运作采用的取值可能不同）。

5) 关于前后收费基金产品数据报送的说明：

a）对同时包含前收费、后收费两种份额类别的基金产品，应为TA系统中实际登记的每个“基金代码+份额类别”报送一条T1文件记录，确保备份数据中所有业务数据均有对应的T1文件记录。

b)如TA系统中后收费份额使用与前收费份额不同的代码登记，应将后收费代码填写在相应的前收费代码报送的T1文件记录的“后收费代码”字段中。

c）如TA系统中后收费份额与前收费份额使用相同的代码登记，但在与销售机构进行数据交换时将后收费份额转换为一个未在TA系统中实际登记的后收费代码，该后收费代码无需单独报送一条T1文件记录，但需将该后收费代码填写在相应的前收费代码报送的T1文件记录的“后收费代码”字段中，确保所有交换数据中涉及的基金代码均在T1文件中的“基金代码”或“后收费代码”字段中有所体现。

d）T2文件按照T1文件中的“基金代码+收费类别”对应报送。

举例一：TA系统登记时，使用基金代码A同时表示前收费和后收费，与销售机构交换数据时只出现了A代码、备份的交易数据为A代码，则T1文件中报送两条记录：（基金代码A、收费类别“前收费”）和（基金代码A、收费类别“后收费”）。

举例二：TA系统登记时，使用基金代码A同时表示前收费和后收费，与销售机构交换数据时出现了A代码（收费类别既有“前收费”也有“后收费”）和B代码（“后收费”）、备份的交易数据应只有A代码（按TA实际登记情况报送），则T1文件中报送两条记录：（基金代码A、收费类别“前收费”,“后收费代码”字段填写B）、（基金代码A、收费类别“后收费”）。

此情况下，T2文件按TA实际登记情况，报送两条记录：（基金代码A、收费类别“前收费”）和（基金代码A、收费类别“后收费”）。

举例三：TA系统登记时，使用基金代码A表示前收费、基金代码B表示后收费，与销售机构交换数据时出现了A和B、备份的交易数据包含A和B，则T1文件中报送两条记录：（基金代码A、收费类别“前收费”,“后收费代码”字段填写B）、（基金代码B、收费类别“后收费”）。

6) 对历史上被清盘的基金代码，且该基金代码份额已为零，则“基金状态2”填写“8-基金终止”。

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否</p><p>必需</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td><p>TA系统中实际使用的基金代码</p></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>63</p></td><td><p>FundName</p></td><td><p>C</p></td><td><p>200</p></td><td><p>基金名称</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>367</p></td><td><p>FundNameAbbr</p></td><td><p>C</p></td><td><p>80</p></td><td><p>基金简称</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>662</p></td><td><p>PublicFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>公募标识</p></td><td><p>对证券公司大集合，填写“1：公募”</p></td><td><p>Y</p></td></tr>
<tr><td><p>646</p></td><td><p>FundManagerCode2</p></td><td><p>C</p></td><td><p>18</p></td><td><p>基金管理人</p></td><td><p>若基金管理人有行业编码中心分配的TA代码，则填写TA代码（子公司只能填自身独立TA代码，不允许填母公司TA代码）；若无则填写基金业协会登记的管理人编码；上述均无则填写组织机构代码或社会信用代码。</p></td><td><p>Y</p></td></tr>
<tr><td><p>647</p></td><td><p>CustodianCode2</p></td><td><p>C</p></td><td><p>18</p></td><td><p>托管人代码</p></td><td><p>若有境内托管人则必填。填写托管人的三位销售机构代码，若无则填写组织机构代码或社会信用代码。</p></td><td><p>N</p></td></tr>
<tr><td><p>648</p></td><td><p>RegistrarCode2</p></td><td><p>C</p></td><td><p>18</p></td><td><p>注册登记人代码</p></td><td><p>若有行业编码中心分配的TA代码，则填写TA代码；若无则填写基金业协会登记的管理人编码；上述均无则填写组织机构代码或社会信用代码。</p></td><td><p>Y</p></td></tr>
<tr><td><p>641</p></td><td><p>FundCode2</p></td><td><p>C</p></td><td><p>12</p></td><td><p>基金代码</p></td><td><p>ISIN编码，跨境销售的基金代码必填</p></td><td><p>N</p></td></tr>
<tr><td><p>649</p></td><td><p>RegRegionCode</p></td><td><p>C</p></td><td><p>2</p></td><td><p>注册地国家或地区代码</p></td><td><p>用于跨境销售的基金代码必填，非跨境销售的基金代码填空。</p><p>举例：大陆某只基金有000001/000002/000003三个代码，其中000003代码用于在香港销售，则000003代码需要填报注册地和销售地，注册地为中国，销售地为香港。</p></td><td><p>N</p></td></tr>
<tr><td><p>650</p></td><td><p>SaleRegionCode</p></td><td><p>C</p></td><td><p>2</p></td><td><p>销售地国家或地区代码</p></td><td><p>用于跨境销售的基金代码必填，非跨境销售的基金代码填空</p></td><td><p>N</p></td></tr>
<tr><td><p>651</p></td><td><p>MainFundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>主基金代码</p></td><td><p>用于为同一产品下的多个基金代码建立关联关系</p></td><td><p>Y</p></td></tr>
<tr><td><p>669</p></td><td><p>FormalFundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>正式代码</p></td><td><p>获得正式编码后必填此字段</p></td><td><p>N</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>24</p></td><td><p>DefDividendMethod</p></td><td><p>A</p></td><td><p>1</p></td><td><p>默认分红方式</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>661</p></td><td><p>DestinationCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金资金全部投向产品代码</p></td><td><p>资金全部投向某只产品时必填，填写被投产品代码</p></td><td><p>N</p></td></tr>
<tr><td><p>310</p></td><td><p>FundType</p></td><td><p>C</p></td><td><p>2</p></td><td><p>基金类型</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>652</p></td><td><p>ClassFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>分级标识</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>653</p></td><td><p>PriorFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>优先劣后标识</p></td><td><p>优先劣后分级产品必填</p></td><td><p>N</p></td></tr>
<tr><td><p>666</p></td><td><p>PriorSequence</p></td><td><p>A</p></td><td><p>2</p></td><td><p>分级优先顺序</p></td><td><p>填写两位数值用于区分不同的优先顺序，从01起开始分配，数字越小优先级越高，数字相同则优先级相同。</p><p>优先顺序分级产品必填</p></td><td><p>N</p></td></tr>
<tr><td><p>668</p></td><td><p>LeverageMultiple</p></td><td><p>N</p></td><td><p>10(四位小数)</p></td><td><p>杠杆倍数</p></td><td><p>结构化产品必填，填写初始杠杆倍数。杠杆倍数＝优先级份额/劣后级份额。若存在中间级份额，应当在计算杠杆倍数时计入优先级份额。</p></td><td><p>N</p></td></tr>
<tr><td><p>373</p></td><td><p>FundEstablishDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>基金成立日期</p></td><td><p>合同生效日，不确定时填写99991231</p></td><td><p>Y</p></td></tr>
<tr><td><p>654</p></td><td><p>FundEndDate</p></td><td><p>C</p></td><td><p>8</p></td><td><p>到期日</p></td><td><p>不确定时填写99991231</p></td><td><p>Y</p></td></tr>
<tr><td><p>670</p></td><td><p>InvestAdName</p></td><td><p>C</p></td><td><p>80</p></td><td><p>投资顾问名称</p></td><td><p>若有投资顾问则必填</p></td><td><p>N</p></td></tr>
<tr><td><p>671</p></td><td><p>InvestAdBusCode</p></td><td><p>C</p></td><td><p>18</p></td><td><p>投资顾问代码</p></td><td><p>若有投资顾问则必填。填写行业编码中心分配的编码，若无则填写组织机构代码或社会信用代码。</p></td><td><p>N</p></td></tr>
<tr><td><p>672</p></td><td><p>InvestAdManCode</p></td><td><p>C</p></td><td><p>18</p></td><td><p>投资顾问私募管理人编码</p></td><td><p>投资顾问为私募基金管理人时必填</p></td><td><p>N</p></td></tr>
<tr><td><p>655</p></td><td><p>RelationUsage</p></td><td><p>C</p></td><td><p>2</p></td><td><p>关系用途</p></td><td><p>01：统计</p><p>指基金代码与主基金代码的关系用于哪些场景，目前均用于统计，填写‘01’。</p></td><td><p>Y</p></td></tr>
<tr><td><p>741</p></td><td><p>RedeemCloseMode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>赎回封闭方式</p></td><td><p>0不封闭；1周期封闭；2封闭固定期限（买入后封闭）；3封闭固定期限（产品封闭）</p></td><td><p>Y</p></td></tr>
<tr><td><p>742</p></td><td><p>CloseLength</p></td><td><p>N</p></td><td><p>8</p></td><td><p>封闭期长度</p></td><td><p>“周期封闭”或“封闭固定期限”产品必填</p></td><td><p>N</p></td></tr>
<tr><td><p>743</p></td><td><p>CloseUnit</p></td><td><p>C</p></td><td><p>3</p></td><td><p>封闭期单位</p></td><td><p>“周期封闭”或“封闭固定期限”产品必填</p></td><td><p>N</p></td></tr>
<tr><td><p>744</p></td><td><p>SideBagFlag</p></td><td><p>C</p></td><td><p>3</p></td><td><p>侧袋标志</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>749</p></td><td><p>SideBagOriCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>侧袋原代码</p></td><td><p>填写侧袋代码的原始基金代码，对侧袋代码要求必填</p></td><td><p>N</p></td></tr>
<tr><td><p>151</p></td><td><p>FaceValue</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>基金面值</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>759</p></td><td><p>FundChar</p></td><td><p>C</p></td><td><p>80</p></td><td><p>基金特征值</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>750</p></td><td><p>InlandAgencyCode</p></td><td><p>C</p></td><td><p>18</p></td><td><p>内地代理人代码</p></td><td><p>境外注册的基金必填。内地代理人如为基金管理人填写其TA编码；如为托管人填写托管人的三位销售机构代码；非上述情况填写社会信用代码或组织机构代码。</p></td><td><p>N</p></td></tr>
<tr><td><p>748</p></td><td><p>NAVSendMode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>净值发送模式</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>751</p></td><td><p>FundStatus2</p></td><td><p>C</p></td><td><p>3</p></td><td><p>基金状态2</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>758</p></td><td><p>BackFareCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>后收费代码</p></td><td><p>若基金代码（ID67）为前收费代码，且有对应的后收费基金代码（与前收费代码不同），则必填。</p></td><td><p>N</p></td></tr>
<tr><td><p>757</p></td><td><p>ApprovalNum</p></td><td><p>C</p></td><td><p>100</p></td><td><p>批文号</p></td><td><p>证监会同意基金设立的批文号，公募基金必填。 </p><p>格式举例：(2021)325</p></td><td><p>N</p></td></tr>
<tr><td><p>760</p></td><td><p>NonPubFundInvType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>非公募产品投向分类</p></td><td><p>非公募产品必填</p></td><td><p>N</p></td></tr>
<tr><td><p>635</p></td><td><p>ReservedField1</p></td><td><p>C</p></td><td><p>20</p></td><td><p>预留字段1</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>636</p></td><td><p>ReservedField2</p></td><td><p>C</p></td><td><p>20</p></td><td><p>预留字段2</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>637</p></td><td><p>ReservedField3</p></td><td><p>C</p></td><td><p>30</p></td><td><p>预留字段3</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>638</p></td><td><p>ReservedField4</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>预留字段4</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>639</p></td><td><p>ReservedField5</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>预留字段5</p></td><td></td><td><p>N</p></td></tr>
</table>

### 4.6.6. 基金运作信息(T2/TN)

本表要求TA全量报送。

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否</p><p>必需</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td><p>TA系统中实际使用的基金代码</p></td><td><p>Y</p></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>66</p></td><td><p>TotalFundVol</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>基金总份数</p></td><td><p>该基金代码、收费类别的场外当日总份数（非整个产品总份数），含冻结份数</p></td><td><p>Y</p></td></tr>
<tr><td><p>68</p></td><td><p>FundStatus</p></td><td><p>C</p></td><td><p>1</p></td><td><p>基金状态</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>86</p></td><td><p>NAV</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>基金单位净值</p></td><td><p>揭示净值</p></td><td><p>Y</p></td></tr>
<tr><td><p>149</p></td><td><p>UpdateDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>基金净值日期</p></td><td><p>格式为：YYYYMMDD</p></td><td><p>Y</p></td></tr>
<tr><td><p>273</p></td><td><p>AccumulativeNAV</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>累计基金单位净值</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>308</p></td><td><p>TotalDivident</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>累计单位分红</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>129</p></td><td><p>FundSize</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>基金规模</p></td><td><p>该基金代码、收费类别的场外当日金额总规模（非整个产品总金额）</p></td><td><p>Y</p></td></tr>
<tr><td><p>673</p></td><td><p>LeverageRate</p></td><td><p>N</p></td><td><p>16(四位小数)</p></td><td><p>杠杆率</p></td><td><p>总资产/净资产（动态）</p></td><td><p>N</p></td></tr>
<tr><td><p>668</p></td><td><p>LeverageMultiple</p></td><td><p>N</p></td><td><p>10(四位小数)</p></td><td><p>杠杆倍数</p></td><td><p>动态杠杆倍数</p></td><td><p>N</p></td></tr>
<tr><td><p>635</p></td><td><p>ReservedField1</p></td><td><p>C</p></td><td><p>20</p></td><td><p>预留字段1</p></td><td><p>左起第一位、第二位分别填写‘基金单位净值’、‘累计基金单位净值’的正负号。‘0’表示正数，‘1’表示负数。若上述字段存在负数情况，则此字段必填。</p><p>举例：‘10’表示基金单位净值为负数，累计基金单位净值为正数。</p></td><td><p>N</p></td></tr>
<tr><td><p>636</p></td><td><p>ReservedField2</p></td><td><p>C</p></td><td><p>20</p></td><td><p>预留字段2</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>637</p></td><td><p>ReservedField3</p></td><td><p>C</p></td><td><p>30</p></td><td><p>预留字段3</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>638</p></td><td><p>ReservedField4</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>预留字段4</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>639</p></td><td><p>ReservedField5</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>预留字段5</p></td><td></td><td><p>N</p></td></tr>
</table>

### 4.6.7. 个人反洗钱信息(X1/XA/X6/XB)

对增量数据，若要修改反洗钱信息，也按新增方式报送，即报送该基金账户的全部反洗钱信息，不允许仅报送修改的内容。

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否</p><p>必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>增量数据报送必填</p></td><td><p>N</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>增量数据报送必填</p></td><td><p>N</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>增量数据报送必填</p></td><td><p>N</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td><p>场内填写席位代码</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金帐号</p></td><td><p>场内填写证券账号。</p></td><td><p>Y</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td><p>0-机构，1-个人，2-产品</p></td><td><p>Y</p></td></tr>
<tr><td><p>258</p></td><td><p>OriginalAppDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>原申请日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>90</p></td><td><p>OriginalAppSheetNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>原申请单编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>85</p></td><td><p>InvestorName</p></td><td><p>C</p></td><td><p>200</p></td><td><p>投资人户名</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>27</p></td><td><p>CertificateType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>个人证件类型及机构证件类型</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>72</p></td><td><p>CertificateNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人证件号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>286</p></td><td><p>CertValidDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>证件有效日期</p></td><td><p>证件到期日。长期有效填写99991231。</p></td><td><p>Y</p></td></tr>
<tr><td><p>126</p></td><td><p>Sex</p></td><td><p>A</p></td><td><p>1</p></td><td><p>投资人性别</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>23</p></td><td><p>InvestorsBirthday</p></td><td><p>A</p></td><td><p>8</p></td><td><p>投资人出生日期</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>522</p></td><td><p>Nationality</p></td><td><p>C</p></td><td><p>3</p></td><td><p>投资者国家或地区</p></td><td><p>持港澳通行证、台胞证、港澳台居民居住证的，对应填写香港、澳门或台湾；持外国人永居证的，填写其主要国籍。</p><p>采用ISO 3166两位字母。</p></td><td><p>Y</p></td></tr>
<tr><td><p>65</p></td><td><p>VocationCode</p></td><td><p>C</p></td><td><p>5</p></td><td><p>投资人职业代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>83</p></td><td><p>MobileTelNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人手机号码</p></td><td><p>手机号码、住址电话、单位电话至少必填其一。</p><p>格式为：国家码|手机号码，比如86|13601223345。</p></td><td><p>N</p></td></tr>
<tr><td><p>69</p></td><td><p>HomeTelNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人住址电话</p></td><td><p>格式：国家码|地区码|电话号码</p><p>举例：86|10|61235567</p></td><td><p>N</p></td></tr>
<tr><td><p>88</p></td><td><p>OfficeTelNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人单位电话号码</p></td><td><p>格式同‘投资人住址电话’</p></td><td><p>N</p></td></tr>
<tr><td><p>49</p></td><td><p>EmailAddress</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人E-MAIL地址</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>51</p></td><td><p>FaxNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人传真号码</p></td><td><p>格式同‘投资人住址电话’</p></td><td><p>N</p></td></tr>
<tr><td><p>101</p></td><td><p>PostCode</p></td><td><p>A</p></td><td><p>6</p></td><td><p>投资人邮政编码</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>73</p></td><td><p>AnnualIncome</p></td><td><p>N</p></td><td><p>16</p></td><td><p>投资人年收入</p></td><td><p>单位：元。</p><p>如果按区间采集，则填写区间上限。举例：‘0-10万’，则填写100000；‘10-50万’，则填写500000，‘50万以上’则填写具体数字。</p></td><td><p>Y</p></td></tr>
<tr><td><p>681</p></td><td><p>LivingCountry</p></td><td><p>C</p></td><td><p>3</p></td><td><p>现居国家或地区</p></td><td><p>‘现居国家或地区和现居地址’和‘注册地国家代码和现居地址2’至少必填其中一套。</p><p>采用ISO 3166两位字母。</p><p>填写住所地国家或地区。</p></td><td><p>N</p></td></tr>
<tr><td><p>682</p></td><td><p>LivingAddress</p></td><td><p>C</p></td><td><p>300</p></td><td><p>现居地址</p></td><td><p>填写住所地。</p><p>固定格式：省|市|县|街道及单元及门牌号。境内地址所有栏位均必填。</p><p>1）“省、市、县”填写每年12月民政部发布的最新“中华人民共和国县以上行政区划代码”(六位数字)的省级、地市级、县级行政区区划代码。</p><p>2）若为境外地址，“省、市、县”不填,‘街道及单元及门牌号’填写完整地址。</p></td><td><p>N</p></td></tr>
<tr><td><p>649</p></td><td><p>RegRegionCode</p></td><td><p>C</p></td><td><p>2</p></td><td><p>注册地国家或地区代码</p></td><td><p>采用ISO 3166两位字母。</p><p>填写工作单位所在国家或地区。</p></td><td><p>N</p></td></tr>
<tr><td><p>683</p></td><td><p>LivingAddress2</p></td><td><p>C</p></td><td><p>300</p></td><td><p>现居地址2</p></td><td><p>填写工作单位地址。</p><p>格式同‘现居地址’。</p></td><td><p>N</p></td></tr>
<tr><td><p>282</p></td><td><p>CorpName</p></td><td><p>C</p></td><td><p>200</p></td><td><p>工作单位名称</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>736</p></td><td><p>SpecialPersonFlag</p></td><td><p>C</p></td><td><p>3</p></td><td><p>特定自然人标识</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>737</p></td><td><p>RelatedPerson</p></td><td><p>C</p></td><td><p>500</p></td><td><p>关联人</p></td><td><p>若存在代理人、或非本人的实控人、或非本人的受益人，则必填。</p><p>对未成年（或存在代理交易）的投资者，要填写代理的自然人信息。</p><p>实控人、受益人填写穿透后的自然人信息。</p><p>格式：类型|名称|证件类型|证件号码|证件有效期|性别|出生日期|国家或地区|职业|地址|电话号码|电子邮箱|邮编|#END#|类型|名称|证件类型|证件号码|证件有效期|性别|出生日期|国家或地区|职业|地址|电话号码|电子邮箱|邮编|#END#|……（最后以字符串|#END#|结尾）</p><p>1）各栏位均必填。</p><p>2)类型：0：代理人 1：实控人 2：受益人</p><p>3）“证件类型、证件有效期、性别、出生日期、国家或地区、职业、电话号码”格式和取值参照前述“个人证件类型及机构证件类型、证件有效日期、投资人性别、投资人出生日期、投资者国家或地区、投资人职业代码、投资人手机号码或住址电话”字段（地址、电话号码中的分隔符‘|’用‘&amp;’代替）。</p></td><td><p>N</p></td></tr>
<tr><td><p>122</p></td><td><p>AccountAbbr</p></td><td><p>C</p></td><td><p>20</p></td><td><p>投资人户名简称</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>732</p></td><td><p>IPAddress</p></td><td><p>C</p></td><td><p>40</p></td><td><p>IP地址</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>735</p></td><td><p>MACAddress</p></td><td><p>C</p></td><td><p>20</p></td><td><p>MAC地址</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>739</p></td><td><p>IMEI</p></td><td><p>C</p></td><td><p>20</p></td><td><p>国际移动设备识别码</p></td><td><p>移动终端为Android操作系统版本时填写</p></td><td><p>N</p></td></tr>
<tr><td><p>740</p></td><td><p>UUID</p></td><td><p>C</p></td><td><p>32</p></td><td><p>通用唯一识别码</p></td><td><p>移动终端为iOS操作系统版本时填写</p></td><td><p>N</p></td></tr>
<tr><td><p>731</p></td><td><p>LaunMoneyRiskRate</p></td><td><p>C</p></td><td><p>3</p></td><td><p>洗钱风险等级</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>181</p></td><td><p>AcctNameOfInvestorInClearingAgency</p></td><td><p>C</p></td><td><p>200</p></td><td><p>投资人收款银行账户户名</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>182</p></td><td><p>AcctNoOfInvestorInClearingAgency</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人收款银行账户账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>183</p></td><td><p>ClearingAgency</p></td><td><p>C</p></td><td><p>20</p></td><td><p>投资人收款银行账户开户行</p></td><td><p>填写银行三位销售机构代码</p></td><td><p>N</p></td></tr>
<tr><td><p>254</p></td><td><p>Specification</p></td><td><p>C</p></td><td><p>60</p></td><td><p>摘要/说明</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>619</p></td><td><p>AddFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>增删标志</p></td><td><p>0- 作废，1-新增</p><p>全量对账时此字段赋值为‘1’</p></td><td><p>Y</p></td></tr>
<tr><td><p>635</p></td><td><p>ReservedField1</p></td><td><p>C</p></td><td><p>20</p></td><td><p>预留字段1</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>636</p></td><td><p>ReservedField2</p></td><td><p>C</p></td><td><p>20</p></td><td><p>预留字段2</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>637</p></td><td><p>ReservedField3</p></td><td><p>C</p></td><td><p>30</p></td><td><p>预留字段3</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>638</p></td><td><p>ReservedField4</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>预留字段4</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>639</p></td><td><p>ReservedField5</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>预留字段5</p></td><td></td><td><p>N</p></td></tr>
</table>

### 4.6.8. 机构反洗钱信息(X3/XC/X8/XD)

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否</p><p>必需</p></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>增量数据报送必填</p></td><td><p>N</p></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td><p>增量数据报送必填</p></td><td><p>N</p></td></tr>
<tr><td><p>93</p></td><td><p>TransactionTime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td><p>增量数据报送必填</p></td><td><p>N</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td><p>场内填写席位代码</p></td><td><p>Y</p></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金帐号</p></td><td><p>场内填写证券账号。</p></td><td><p>Y</p></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td><p>0-机构，1-个人，2-产品</p></td><td><p>Y</p></td></tr>
<tr><td><p>258</p></td><td><p>OriginalAppDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>原申请日期</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>90</p></td><td><p>OriginalAppSheetNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>原申请单编号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>85</p></td><td><p>InvestorName</p></td><td><p>C</p></td><td><p>200</p></td><td><p>投资人户名</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>27</p></td><td><p>CertificateType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>个人证件类型及机构证件类型</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>72</p></td><td><p>CertificateNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人证件号码</p></td><td></td><td><p>Y</p></td></tr>
<tr><td><p>286</p></td><td><p>CertValidDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>证件有效日期</p></td><td><p>证件到期日。长期有效填写99991231。</p></td><td><p>Y</p></td></tr>
<tr><td><p>23</p></td><td><p>InvestorsBirthday</p></td><td><p>A</p></td><td><p>8</p></td><td><p>投资人出生日期</p></td><td><p>填写机构、产品的成立日期。</p></td><td><p>Y</p></td></tr>
<tr><td><p>681</p></td><td><p>LivingCountry</p></td><td><p>C</p></td><td><p>3</p></td><td><p>现居国家或地区</p></td><td><p>对机构投资者，‘现居国家或地区和现居地址’和‘注册地国家或地区代码和现居地址2’至少必填其中一套。</p><p>采用ISO 3166两位字母。</p><p>对机构投资者，填写办公所在国家（或地区）。</p></td><td><p>N</p></td></tr>
<tr><td><p>682</p></td><td><p>LivingAddress</p></td><td><p>C</p></td><td><p>300</p></td><td><p>现居地址</p></td><td><p>对机构投资者，‘现居国家或地区和现居地址’和‘注册地国家或地区代码和现居地址2’至少必填其中一套。</p><p>对机构投资者，填写办公地址。</p><p>固定格式：省|市|县|街道及单元及门牌号。境内地址所有栏位均必填。</p><p>1）“省、市、县”填写每年12月民政部发布的最新“中华人民共和国县以上行政区划代码”(六位数字)的省级、地市级、县级行政区区划代码。</p><p>2）若为境外地址，“省、市、县”不填,‘街道及单元及门牌号’填写完整地址。</p></td><td><p>N</p></td></tr>
<tr><td><p>649</p></td><td><p>RegRegionCode</p></td><td><p>C</p></td><td><p>2</p></td><td><p>注册地国家或地区代码</p></td><td><p>产品投资者必填。</p><p>采用ISO 3166两位字母。</p><p>机构投资者填写注册所在国家或地区。产品投资者填写资产管理人注册所在国家或地区。</p></td><td><p>N</p></td></tr>
<tr><td><p>683</p></td><td><p>LivingAddress2</p></td><td><p>C</p></td><td><p>300</p></td><td><p>现居地址2</p></td><td><p>产品投资者必填。</p><p>对机构投资者，填写注册地址。</p><p>对产品投资者，填写资产管理人营业执照上注册地址。</p><p>格式同‘现居地址’。</p></td><td><p>N</p></td></tr>
<tr><td><p>721</p></td><td><p>ManageRange</p></td><td><p>C</p></td><td><p>2000</p></td><td><p>经营范围</p></td><td><p>对机构投资者，指营业执照载明的经营范围。对产品投资者，填写资产管理人经营范围。</p></td><td><p>Y</p></td></tr>
<tr><td><p>336</p></td><td><p>Vocation</p></td><td><p>C</p></td><td><p>4</p></td><td><p>行业</p></td><td><p>对产品投资者，指资产管理人所在行业</p></td><td><p>Y</p></td></tr>
<tr><td><p>722</p></td><td><p>RegCapital</p></td><td><p>N</p></td><td><p>20</p></td><td><p>注册资本</p></td><td><p>对产品投资者，指资产管理人注册资本。</p><p>单位：元。</p></td><td><p>Y</p></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td><p>对机构投资者，指注册资本币种；对产品投资者，指资产管理人注册资本币种。</p><p>具体编码采用GB/T 12406-2008中3位数字。</p></td><td><p>Y</p></td></tr>
<tr><td><p>723</p></td><td><p>OrgNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>组织机构代码</p></td><td><p>机构投资者必填</p></td><td><p>N</p></td></tr>
<tr><td><p>724</p></td><td><p>TaxNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>税务登记证号码</p></td><td><p>机构投资者必填</p></td><td><p>N</p></td></tr>
<tr><td><p>725</p></td><td><p>InstRepr</p></td><td><p>C</p></td><td><p>300</p></td><td><p>法定代表人</p></td><td><p>填写法定代表人或负责人信息。</p><p>产品投资者填写资产管理人的法定代表人。</p><p>格式：名称|个人/机构标志|证件类型|证件号码|证件有效期|电话号码|电子邮箱。</p><p>前5项不允许为空，其中电话号码中的的分隔符‘|’用‘&amp;’代替。</p></td><td><p>Y</p></td></tr>
<tr><td><p>291</p></td><td><p>ControlHolder</p></td><td><p>C</p></td><td><p>2000</p></td><td><p>控股股东</p></td><td><p>对机构投资者、产品投资者，‘控股股东’和‘实际控制人’至少必填其一。</p><p>对产品投资者，填写资产管理人的控股股东。</p><p>格式：名称|个人/机构标志|证件类型|证件号码|证件有效期|电话号码|电子邮箱|#END#|名称|个人/机构标志|证件类型|证件号码|证件有效期|电话号码|电子邮箱|#END#|……（最后以字符串|#END#|结尾）。</p><p>前5项不允许为空，其中电话号码中的的分隔符‘|’用‘&amp;’代替。</p></td><td><p>N</p></td></tr>
<tr><td><p>292</p></td><td><p>ActualController</p></td><td><p>C</p></td><td><p>2000</p></td><td><p>实际控制人</p></td><td><p>对产品投资者，填写资产管理人的实际控制人。</p><p>格式同‘控股股东’，前5项不允许为空。</p></td><td><p>N</p></td></tr>
<tr><td><p>726</p></td><td><p>Transactor</p></td><td><p>C</p></td><td><p>2000</p></td><td><p>经办人</p></td><td><p>产品投资者填写资产管理人的经办人。</p><p>格式同‘控股股东’，前5项不允许为空。</p></td><td><p>Y</p></td></tr>
<tr><td><p>727</p></td><td><p>BeneOwner</p></td><td><p>C</p></td><td><p>2000</p></td><td><p>受益所有人</p></td><td><p>除反洗钱规定中豁免的情况外，其余机构、产品投资者必填。填写穿透后的最终自然人。</p><p>格式：名称|个人/机构标志|证件类型|证件号码|证件有效期|国家或地区|地址|判定受益人方式|持股或表决权占比|特定自然人标识|#END#|名称|个人/机构标志|证件类型|证件号码|证件有效期|国家或地区|地址|判定受益人方式|持股或表决权占比|特定自然人标识|#END#|……（最后以字符串|#END#|结尾。）</p><p>除“持股或表决权占比”（仅在判定受益所有人方式基于股权或表决权时必填），其余栏位均必填。</p><p>其中：</p><p>1)地址：格式参照‘现居地址’，但将‘现居地址’中的分隔符‘|’用‘&amp;’代替，即‘省&amp;市&amp;县&amp;街道及单元及门牌号’。</p><p>2)判定受益人方式：</p><p>01：公司及其他机构、组织-直接或者间接拥有25%及以上公司股权或者表决权的自然人 02：公司及其他机构、组织-通过人事、财务等其他方式对公司进行控制的自然人 03：公司及其他机构、组织-高级管理人员04：公司及其他机构、组织-其他受益所有人05：合伙企业-拥有25%及以上合伙权益的自然人06：合伙企业-其他受益所有人</p><p>07：信托-委托人08：信托-受托人</p><p>09：信托-受益人10：信托-其他受益所有人11：基金及其他产品-份额权益占25%及以上的自然人12：基金及其他产品-其他受益所有人 99:其它。</p><p>3）持股或表决权占比: 填写小数，比如0.65。最多不超过8位小数。</p></td><td><p>N</p></td></tr>
<tr><td><p>367</p></td><td><p>FundNameAbbr</p></td><td><p>C</p></td><td><p>80</p></td><td><p>基金简称</p></td><td><p>产品投资者必填</p><p>指产品简称</p></td><td><p>N</p></td></tr>
<tr><td><p>665</p></td><td><p>InvestorProCode</p></td><td><p>C</p></td><td><p>30</p></td><td><p>投资者产品代码</p></td><td><p>投资者为公募基金产品或基金业协会备案产品时必填，填写行业编码中心分配的编码或协会备案产品编码。</p></td><td><p>N</p></td></tr>
<tr><td><p>654</p></td><td><p>FundEndDate</p></td><td><p>C</p></td><td><p>8</p></td><td><p>到期日</p></td><td><p>产品投资者必填</p><p>无到期日填写99991231。</p></td><td><p>N</p></td></tr>
<tr><td><p>728</p></td><td><p>AssetManager</p></td><td><p>C</p></td><td><p>300</p></td><td><p>资产管理人</p></td><td><p>产品投资者必填</p><p>格式：名称|个人/机构标志|证件类型|证件号码|证件有效期。</p></td><td><p>N</p></td></tr>
<tr><td><p>738</p></td><td><p>CustodianName</p></td><td><p>C</p></td><td><p>100</p></td><td><p>托管人名称</p></td><td><p>产品投资者若有托管人则必填</p></td><td><p>N</p></td></tr>
<tr><td><p>38</p></td><td><p>CustodianCode</p></td><td><p>C</p></td><td><p>18</p></td><td><p>托管人代码</p></td><td><p>产品投资者若有托管人则必填</p><p>填写托管人的三位销售代码。若无销售代码则填写组织机构代码或社会信用代码。</p></td><td><p>N</p></td></tr>
<tr><td><p>732</p></td><td><p>IPAddress</p></td><td><p>C</p></td><td><p>40</p></td><td><p>IP地址</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>735</p></td><td><p>MACAddress</p></td><td><p>C</p></td><td><p>20</p></td><td><p>MAC地址</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>739</p></td><td><p>IMEI</p></td><td><p>C</p></td><td><p>20</p></td><td><p>国际移动设备识别码</p></td><td><p>移动终端为Android操作系统版本时填写</p></td><td><p>N</p></td></tr>
<tr><td><p>740</p></td><td><p>UUID</p></td><td><p>C</p></td><td><p>32</p></td><td><p>通用唯一识别码</p></td><td><p>移动终端为iOS操作系统版本时填写</p></td><td><p>N</p></td></tr>
<tr><td><p>731</p></td><td><p>LaunMoneyRiskRate</p></td><td><p>C</p></td><td><p>3</p></td><td><p>洗钱风险等级</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>181</p></td><td><p>AcctNameOfInvestorInClearingAgency</p></td><td><p>C</p></td><td><p>200</p></td><td><p>投资人收款银行账户户名</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>182</p></td><td><p>AcctNoOfInvestorInClearingAgency</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人收款银行账户账号</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>183</p></td><td><p>ClearingAgency</p></td><td><p>C</p></td><td><p>20</p></td><td><p>投资人收款银行账户开户行</p></td><td><p>填写银行三位销售机构代码</p></td><td><p>N</p></td></tr>
<tr><td><p>254</p></td><td><p>Specification</p></td><td><p>C</p></td><td><p>60</p></td><td><p>摘要/说明</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>619</p></td><td><p>AddFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>增删标志</p></td><td><p>0-作废，1-新增</p><p>全量对账时此字段赋值为‘1’</p></td><td><p>Y</p></td></tr>
<tr><td><p>635</p></td><td><p>ReservedField1</p></td><td><p>C</p></td><td><p>20</p></td><td><p>预留字段1</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>636</p></td><td><p>ReservedField2</p></td><td><p>C</p></td><td><p>20</p></td><td><p>预留字段2</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>637</p></td><td><p>ReservedField3</p></td><td><p>C</p></td><td><p>30</p></td><td><p>预留字段3</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>638</p></td><td><p>ReservedField4</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>预留字段4</p></td><td></td><td><p>N</p></td></tr>
<tr><td><p>639</p></td><td><p>ReservedField5</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>预留字段5</p></td><td></td><td><p>N</p></td></tr>
</table>

### 4.6.9. 跨境基金计税参数(G1)

本表要求每日全量报送跨境销售的所有基金，每只产品只报送其主基金代码（无论是否中国结算TA登记，均需报送）,需包含基金的未销户的全部股票账户（份额占比为0也要报送）。

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>备注</p></td><td><p>是否</p><p>必需</p></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td><p>填写主基金代码</p></td><td><p>Y</p></td></tr>
<tr><td><p>754</p></td><td><p>MarketFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>市场标志</p></td><td><p>指股票账户所在市场。</p><p>0：深圳 1：上海 2：北京</p></td><td><p>Y</p></td></tr>
<tr><td><p>658</p></td><td><p>StockAccount</p></td><td><p>C</p></td><td><p>10</p></td><td><p>股票账户</p></td><td><p>基金产品的股票账户，此账户将根据境外投资者计税占比收取红利税。</p></td><td><p>Y</p></td></tr>
<tr><td><p>659</p></td><td><p>TaxRatio	</p></td><td><p>N</p></td><td><p>7(四位小数)</p></td><td><p>计税比例</p></td><td><p>表示境外市场投资者计税占比（比如所持份额或市值所占比例），用于计算产品持有股票应缴红利税。</p><p>同一产品的多个股票账户，其计税占比应相同。</p><p>举例：计税占比49.23%,即为0.4923。</p></td><td><p>Y</p></td></tr>
<tr><td><p>660</p></td><td><p>RatioDate</p></td><td><p>C</p></td><td><p>8</p></td><td><p>比例日期</p></td><td><p>以该日登记的份额为准(一般T日申请T+1日登记)，统计境外市场投资者计税占比。</p></td><td><p>Y</p></td></tr>
</table>

# 5.

# 6. 附录A接口文件规范数据类型定义

<table>
<tr><td></td><td colspan="4"></td></tr>
<tr><td></td><td colspan="4"></td></tr>
<tr><td><p>文件组织结构</p></td><td colspan="4"><p>数据集中备份系统与各TA以大文件形式交换数据，对于中国结算对应深市和沪市提供两个TA：98—表示深市TA和99—表示沪市TA。</p></td></tr>
<tr><td><p>数据索引文件名</p></td><td colspan="4"><p>数据索引文件名为：“OFI/OFB”+“_”+文件创建人代码＋“_”+文件接收人代码＋“_” ＋日期(YYYYMMDD)＋“.TXT”。</p></td></tr>
<tr><td rowspan="10"><p>数据索引文件格式</p></td><td><p>名称</p></td><td><p>长度</p></td><td><p>值</p></td><td><p>含义(作用)</p></td></tr>
<tr><td><p>文件标识</p></td><td><p>8</p></td><td><p>“OFDCFIDX”</p></td><td><p>用以标明该文件的格式类型</p></td></tr>
<tr><td><p>文件版本号</p></td><td><p>8</p></td><td><p>22</p></td><td><p>2．2版本</p></td></tr>
<tr><td><p>文件创建人</p></td><td><p>20</p></td><td><p>TA/基金管理人由证监会统一发放</p></td><td><p>用于标明该文件的提交人</p></td></tr>
<tr><td><p>文件接收人</p></td><td><p>20</p></td><td><p>00</p></td><td><p>表示基金集中备份系统</p></td></tr>
<tr><td><p>日期</p></td><td><p>8</p></td><td><p>日期</p></td><td><p>与文件名日期一致，不是机器时间</p></td></tr>
<tr><td><p>文件个数</p></td><td><p>8</p></td><td><p>要传送的数据文件的个数</p></td><td><p>用于标明接下来要传送的数据文件个数</p></td></tr>
<tr><td><p>文件名1</p></td><td></td><td></td><td><p>第一个文件名</p></td></tr>
<tr><td><p>…</p></td><td></td><td></td><td></td></tr>
<tr><td><p>文件结束标识</p></td><td><p>8</p></td><td><p>“OFDCFEND”</p></td><td><p>文件结束</p></td></tr>
<tr><td><p>数据文件名</p></td><td colspan="4"><p>数据文件名“OFD”+“_”+文件创建人代码＋“_”+文件接收人代码＋“_”+日期(YYYYMMDD)+“_”+两位文件类型编码+“.TXT”。如数据文件有拆分，在“.TXT”前增加“_顺序号”，顺序号为3位长度。</p></td></tr>
<tr><td rowspan="24"><p>数据文件格式</p></td><td><p>名称</p></td><td><p>长度</p></td><td><p>值</p></td><td><p>含义(作用)</p></td></tr>
<tr><td><p>文件标识</p></td><td><p>8</p></td><td><p>“OFDCFDAT”</p></td><td><p>用以标明该文件的格式类型</p></td></tr>
<tr><td><p>文件版本号</p></td><td><p>8</p></td><td><p>22</p></td><td><p>2．2版本</p></td></tr>
<tr><td><p>文件创建人</p></td><td><p>20</p></td><td><p>TA/基金管理人由证监会统一发放</p></td><td><p>用于标明该文件的提交人</p></td></tr>
<tr><td><p>文件接收人</p></td><td><p>20</p></td><td><p>00</p></td><td><p>表示基金集中备份系统</p></td></tr>
<tr><td><p>日期</p></td><td><p>8</p></td><td><p>日期</p></td><td><p>与文件名日期一致，不是机器时间</p></td></tr>
<tr><td><p>汇总表号</p></td><td><p>8</p></td><td></td><td><p>文件传输次序标志</p></td></tr>
<tr><td rowspan="2"><p>文件类型码</p></td><td rowspan="2"><p>8</p></td><td rowspan="2"><p>参照文件类型定义里面的文件类型编码</p></td><td rowspan="2"><p>用于标明文件的功能类型</p></td></tr>
<tr></tr>
<tr><td><p>发送人</p></td><td><p>8</p></td><td></td><td></td></tr>
<tr><td><p>接收人</p></td><td><p>8</p></td><td></td><td></td></tr>
<tr><td><p>字段数</p></td><td><p>8</p></td><td><p>N</p></td><td><p>标明该数据文件的构成字段数</p></td></tr>
<tr><td><p>字段名1</p></td><td></td><td></td><td><p>采用数据字典中的字段名</p></td></tr>
<tr><td><p>…</p></td><td></td><td></td><td></td></tr>
<tr><td><p>字段名N</p></td><td></td><td></td><td></td></tr>
<tr><td><p>记录数</p></td><td><p>16</p></td><td><p>M</p></td><td><p>该数据文件包含的数据记录数，最多9999999999999999条</p></td></tr>
<tr><td><p>记录1</p></td><td></td><td></td><td></td></tr>
<tr><td><p>记录２</p></td><td></td><td></td><td></td></tr>
<tr><td><p>记录３</p></td><td></td><td></td><td></td></tr>
<tr><td><p>…</p></td><td></td><td></td><td></td></tr>
<tr><td><p>记录M-2</p></td><td></td><td></td><td></td></tr>
<tr><td><p>记录M-1</p></td><td></td><td></td><td></td></tr>
<tr><td><p>记录M</p></td><td></td><td></td><td></td></tr>
<tr><td><p>文件结束标识</p></td><td><p>8</p></td><td><p>“OFDCFEND”</p></td><td><p>文件结束</p></td></tr>
</table>

# 7. 附录B数据字典

<table>
<tr><td><p>ID</p></td><td><p>字段名</p></td><td><p>类型</p></td><td><p>长度</p></td><td><p>描述</p></td><td><p>取值说明</p></td></tr>
<tr><td><p>1</p></td><td><p>AcctManFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金账户管理费</p></td><td></td></tr>
<tr><td><p>2</p></td><td><p>InstAppSubsAmnt</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>法人追加认购金额</p></td><td></td></tr>
<tr><td><p>3</p></td><td><p>InstAppSubsVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>法人追加认购份数</p></td><td></td></tr>
<tr><td><p>4</p></td><td><p>Address</p></td><td><p>C</p></td><td><p>300</p></td><td><p>通讯地址</p></td><td></td></tr>
<tr><td><p>5</p></td><td><p>InstReprIDCode</p></td><td><p>C</p></td><td><p>40</p></td><td><p>法人代表身份证件代码</p></td><td></td></tr>
<tr><td><p>6</p></td><td><p>InstReprIDType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>法人代表证件类型</p></td><td><p>参考数据字典“证件类型”中的个人部分</p></td></tr>
<tr><td><p>7</p></td><td><p>InstReprName</p></td><td><p>C</p></td><td><p>60</p></td><td><p>法人代表姓名</p></td><td></td></tr>
<tr><td><p>8</p></td><td><p>AppSheetSerialNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>申请单编号</p></td><td><p>同一销售商不能重复</p></td></tr>
<tr><td><p>9</p></td><td><p>TotalSubsAmnt</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申购总金额</p></td><td></td></tr>
<tr><td><p>10</p></td><td><p>TotalAccptdSubsVol</p></td><td><p>N</p></td><td><p>10</p></td><td><p>成功申购总笔数</p></td><td><p>申请总笔数</p></td></tr>
<tr><td><p>11</p></td><td><p>TotalSubsCharge</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申购手续费总金额</p></td><td></td></tr>
<tr><td><p>12</p></td><td><p>TotalSubsVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申购总份数</p></td><td></td></tr>
<tr><td><p>13</p></td><td><p>AvailableVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>持有人可用基金份数</p></td><td></td></tr>
<tr><td><p>14</p></td><td><p>IssueType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>基金发行方式</p></td><td><p>1-不限量发行，2-限额发行3-比例配售</p></td></tr>
<tr><td><p>15</p></td><td><p>AmntReinbursed</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>退回金额</p></td><td></td></tr>
<tr><td><p>16</p></td><td><p>BackendLoad</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>每笔交易后端收费</p></td><td></td></tr>
<tr><td><p>17</p></td><td><p>AcctBalanceInIndividualDistributor</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>持有人在单个销售机构的基金份数</p></td><td></td></tr>
<tr><td><p>18</p></td><td><p>TotalVolOfDistributorInTA</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金总份数(含冻结)</p></td><td></td></tr>
<tr><td><p>19</p></td><td><p>AcctNoOfFMInClearingAgency</p></td><td><p>C</p></td><td><p>28</p></td><td><p>基金管理人在资金清算机构的交收账号</p></td><td></td></tr>
<tr><td><p>20</p></td><td><p>AcctNameOfFMInClearingAgency</p></td><td><p>C</p></td><td><p>60</p></td><td><p>基金管理人在资金清算机构的交收账户名</p></td><td></td></tr>
<tr><td><p>21</p></td><td><p>ClearingAgencyCode</p></td><td><p>A</p></td><td><p>9</p></td><td><p>基金资金清算机构代码</p></td><td></td></tr>
<tr><td><p>22</p></td><td><p>BasisforCalculatingDividend</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>红利/红股再投资基数</p></td><td><p>登记日基金持有人的基金份数</p></td></tr>
<tr><td><p>23</p></td><td><p>InvestorsBirthday</p></td><td><p>A</p></td><td><p>8</p></td><td><p>投资人出生日期</p></td><td></td></tr>
<tr><td><p>24</p></td><td><p>DefDividendMethod</p></td><td><p>A</p></td><td><p>1</p></td><td><p>默认分红方式</p></td><td><p>0-红利转投，1-现金分红</p></td></tr>
<tr><td><p>25</p></td><td><p>DiscountRateOfCommission</p></td><td><p>N</p></td><td><p>5(四位小数)</p></td><td><p>销售佣金折扣率</p></td><td></td></tr>
<tr><td><p>26</p></td><td><p>PagerNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>投资人传呼机号码</p></td><td></td></tr>
<tr><td><p>27</p></td><td><p>CertificateType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>证件类型</p></td><td><p>个人证件类型</p><p>0-身份证，1-中国护照</p><p>2-军官证，3-士兵证</p><p>4-港澳居民来往内地通行证，5-户口本</p><p>6-外国护照，7-其它</p><p>8-文职证，9-警官证</p><p>A-台胞证,B-外国人永久居留身份证,C-港澳台居民居住证</p><p>机构证件类型</p><p>0-组织机构代码证</p><p>1-营业执照，2-行政机关</p><p>3-社会团体，4-军队</p><p>5-武警</p><p>6-下属机构（具有主管单位批文号）</p><p>7-基金会，8-其它，9-登记证书，A-批文</p><p>产品证件类型<br>1-营业执照，8-其它，9-登记证书，A-批文</p></td></tr>
<tr><td><p>28</p></td><td><p>DepositAcct</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人在销售人处开设用于交易的资金账号</p></td><td></td></tr>
<tr><td><p>29</p></td><td><p>RegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易所在地区编号</p></td><td></td></tr>
<tr><td><p>30</p></td><td><p>TransferDateFromCustodian</p></td><td><p>A</p></td><td><p>8</p></td><td><p>清算资金自托管人处划出日期</p></td><td></td></tr>
<tr><td><p>31</p></td><td><p>TransferDateThroughClearingAgency</p></td><td><p>A</p></td><td><p>8</p></td><td><p>清算资金经清算人划出日期</p></td><td></td></tr>
<tr><td><p>32</p></td><td><p>TransactionCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易确认日期</p></td><td></td></tr>
<tr><td><p>33</p></td><td><p>AnnContent</p></td><td><p>C</p></td><td><p>4000</p></td><td><p>公告内容</p></td><td></td></tr>
<tr><td><p>34</p></td><td><p>CodeOfTargetFund</p></td><td><p>C</p></td><td><p>6</p></td><td><p>转换时的目标基金代码</p></td><td></td></tr>
<tr><td><p>35</p></td><td><p>MinAmountByInst</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>法人首次认购最低金额</p></td><td></td></tr>
<tr><td><p>36</p></td><td><p>MinVolByInst</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>法人首次认购最低份数</p></td><td></td></tr>
<tr><td><p>37</p></td><td><p>CurrencyType</p></td><td><p>A</p></td><td><p>3</p></td><td><p>结算币种</p></td><td><p>具体编码依GB/T 12406-2008中3位数字。</p><p>例如：156-人民币</p></td></tr>
<tr><td><p>38</p></td><td><p>CustodianCode</p></td><td><p>C</p></td><td><p>18</p></td><td><p>托管人代码</p></td><td></td></tr>
<tr><td><p>39</p></td><td><p>AmountOfPeriodicSubs</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>定时定额申购的金额</p></td><td></td></tr>
<tr><td><p>40</p></td><td><p>DateOfPeriodicSubs</p></td><td><p>A</p></td><td><p>8</p></td><td><p>定时定额申购日期</p></td><td></td></tr>
<tr><td><p>41</p></td><td><p>VolOfDividendforReinvestment</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金账户红利再投资基金份数</p></td><td></td></tr>
<tr><td><p>42</p></td><td><p>DividentDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>分红日/发放日</p></td><td></td></tr>
<tr><td><p>43</p></td><td><p>DividendAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金账户红利资金</p></td><td></td></tr>
<tr><td><p>44</p></td><td><p>TotalDividendAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金红利总额</p></td><td></td></tr>
<tr><td><p>45</p></td><td><p>DividendOrShare</p></td><td><p>A</p></td><td><p>1</p></td><td><p>红利/红股再投资标志</p></td><td><p>0-红利再投资，1-红利</p></td></tr>
<tr><td><p>46</p></td><td><p>XRDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>除权日</p></td><td></td></tr>
<tr><td><p>47</p></td><td><p>DownLoaddate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易数据下传日期</p></td><td><p>发送日期</p></td></tr>
<tr><td><p>48</p></td><td><p>EducationLevel</p></td><td><p>C</p></td><td><p>3</p></td><td><p>投资人学历</p></td><td><p>01-研究生02-大学本科03- 大学专科04-中专或技校05-技工学校06-高中07-初中08-小学09-文盲或半文盲</p></td></tr>
<tr><td><p>49</p></td><td><p>EmailAddress</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人E-MAIL地址</p></td><td></td></tr>
<tr><td><p>50</p></td><td><p>TotalDividendIndeed</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金实发红利总金额</p></td><td></td></tr>
<tr><td><p>51</p></td><td><p>FaxNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人传真号码</p></td><td></td></tr>
<tr><td><p>52</p></td><td><p>Charge</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>手续费</p></td><td></td></tr>
<tr><td><p>53</p></td><td><p>AgencyFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>代理费</p></td><td></td></tr>
<tr><td><p>54</p></td><td><p>ChargeRate</p></td><td><p>N</p></td><td><p>6(4位小数)</p></td><td><p>手续费率</p></td><td></td></tr>
<tr><td><p>55</p></td><td><p>TotalTransFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>交易确认费用合计</p></td><td></td></tr>
<tr><td><p>56</p></td><td><p>TotalFeeForDividend</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>分红费用合计</p></td><td></td></tr>
<tr><td><p>57</p></td><td><p>AnnouncementNo</p></td><td><p>C</p></td><td><p>13</p></td><td><p>公告文件号</p></td><td><p>基金管理公司编码：(NNN) +YYYYMMDD+序号(NN)</p></td></tr>
<tr><td><p>58</p></td><td><p>FreezingDeadline</p></td><td><p>A</p></td><td><p>8</p></td><td><p>冻结截止日期</p></td><td></td></tr>
<tr><td><p>59</p></td><td><p>TotalFrozenVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金冻结总份数</p></td><td></td></tr>
<tr><td><p>60</p></td><td><p>FrozenCause</p></td><td><p>A</p></td><td><p>1</p></td><td><p>冻结原因</p></td><td><p>0-司法冻结，1-柜台冻结</p><p>2-质押冻结，3-质押、司法双重冻结 4-柜台、司法双重冻结</p></td></tr>
<tr><td><p>61</p></td><td><p>FrontendFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>每笔交易前端收费</p></td><td></td></tr>
<tr><td><p>62</p></td><td><p>ConfirmedVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金账户交易确认份数</p></td><td></td></tr>
<tr><td><p>63</p></td><td><p>FundName</p></td><td><p>C</p></td><td><p>200</p></td><td><p>基金名称</p></td><td></td></tr>
<tr><td><p>64</p></td><td><p>ConfirmedAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>每笔交易确认金额</p></td><td></td></tr>
<tr><td><p>65</p></td><td><p>VocationCode</p></td><td><p>C</p></td><td><p>5</p></td><td><p>投资人职业代码</p></td><td><p>1、党政机关负责人及管理人员</p><p>2、企事业单位负责人及管理人员</p><p>3、民主党派和工商联负责人及管理人员</p><p>4、人民团体或群众团体负责人及管理人员</p><p>5、社会组织（社会团体、基金会、社会服务机构、外国商会等）负责人及管理人员</p><p>6、科学研究及教学人员</p><p>7、文学艺术、体育专业人员</p><p>8、新闻出版、文化专业人员</p><p>9、卫生专业技术人员</p><p>10、工程、农业专业人员</p><p>11、法律、会计、审计、税务专业人员</p><p>12、经济和金融专业人员</p><p>13、宗教人士等特殊职业人员</p><p>14、其他专业技术人员</p><p>15、党政机关、企事业单位行政工作人员</p><p>16、民主党派、工商联、人民团体或社会组织等单位工作人员</p><p>17、人民警察、消防、应急救援人员</p><p>18、批发与零售服务人员</p><p>19、房地产服务人员</p><p>20、旅游、住宿和餐饮服务人员</p><p>21、珠宝、黄金等贵金属行业服务人员</p><p>22、文化、体育和娱乐服务人员</p><p>23、典当、拍卖行业服务人员</p><p>24、艺术品或文物收藏行业服务人员</p><p>25、废品、旧货回收服务人员</p><p>26、交通运输、仓储、邮政业服务人员</p><p>27、信息运输、软件和信息技术服务人员</p><p>28、居民、健康服务人员</p><p>29、其他社会生产和社会服务人员</p><p>30、农、林、牧、渔业生产及辅助人员</p><p>31、生产制造及有关人员</p><p>32、军人</p><p>33、国际组织工作人员</p><p>34、离退休人员</p><p>35、个体工商户（含淘宝店自营等）</p><p>36、无业</p><p>37、学生</p><p>注：若不在上述范围则按GB/T 6565-2015填写。</p></td></tr>
<tr><td><p>66</p></td><td><p>TotalFundVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金总份数</p></td><td></td></tr>
<tr><td><p>67</p></td><td><p>FundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金代码</p></td><td></td></tr>
<tr><td><p>68</p></td><td><p>FundStatus</p></td><td><p>C</p></td><td><p>1</p></td><td><p>基金状态</p></td><td><p>0-可申购赎回，1-发行</p><p>4-停止申购赎回</p><p>5-停止申购，6-停止赎回</p><p>8-基金终止，9-基金封闭</p></td></tr>
<tr><td><p>69</p></td><td><p>HomeTelNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人住址电话</p></td><td></td></tr>
<tr><td><p>70</p></td><td><p>MaxRedemptionVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金最高赎回份数</p></td><td></td></tr>
<tr><td><p>71</p></td><td><p>MinAccountBalance</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金最低持有份数</p></td><td></td></tr>
<tr><td><p>72</p></td><td><p>CertificateNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人证件号码</p></td><td></td></tr>
<tr><td><p>73</p></td><td><p>AnnualIncome</p></td><td><p>N</p></td><td><p>16</p></td><td><p>投资人年收入</p></td><td></td></tr>
<tr><td><p>74</p></td><td><p>AnnouncementDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>公告日期</p></td><td></td></tr>
<tr><td><p>75</p></td><td><p>AnnouncementType</p></td><td><p>A</p></td><td><p>1</p></td><td><p>公告类别</p></td><td><p>0-常规，1-异常</p></td></tr>
<tr><td><p>76</p></td><td><p>Interest</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>基金账户利息金额</p></td><td></td></tr>
<tr><td><p>77</p></td><td><p>BackAmountByInvalid</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>因为无效而划回投资人的资金</p></td><td></td></tr>
<tr><td><p>78</p></td><td><p>IPOStartDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>基金募集开始日期</p></td><td></td></tr>
<tr><td><p>79</p></td><td><p>IPOEndDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>基金募集结束日期</p></td><td></td></tr>
<tr><td><p>80</p></td><td><p>LargeRedemptionFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>巨额赎回处理标志</p></td><td><p>0-取消，1-顺延</p></td></tr>
<tr><td><p>81</p></td><td><p>LengthOfAnnouncement</p></td><td><p>N</p></td><td><p>10</p></td><td><p>公告内容长度</p></td><td></td></tr>
<tr><td><p>82</p></td><td><p>FundManagerCode</p></td><td><p>C</p></td><td><p>18</p></td><td><p>基金管理人</p></td><td></td></tr>
<tr><td><p>83</p></td><td><p>MobileTelNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人手机号码</p></td><td></td></tr>
<tr><td><p>84</p></td><td><p>MultiAcctFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>多渠道开户标志</p></td><td><p>0-首次开设基金账户</p><p>1-已经其它渠道开户</p></td></tr>
<tr><td><p>85</p></td><td><p>InvestorName</p></td><td><p>C</p></td><td><p>200</p></td><td><p>投资人户名</p></td><td></td></tr>
<tr><td><p>86</p></td><td><p>NAV</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>基金单位净值</p></td><td></td></tr>
<tr><td><p>87</p></td><td><p>BranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>网点号码</p></td><td></td></tr>
<tr><td><p>88</p></td><td><p>OfficeTelNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人单位电话号码</p></td><td></td></tr>
<tr><td><p>89</p></td><td><p>OriginalSerialNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA的原确认流水号</p></td><td></td></tr>
<tr><td><p>90</p></td><td><p>OriginalAppSheetNo</p></td><td><p>C</p></td><td><p>24</p></td><td><p>原申请单编号</p></td><td></td></tr>
<tr><td><p>91</p></td><td><p>OriginalSubsDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>原申购日期</p></td><td></td></tr>
<tr><td><p>92</p></td><td><p>TransactionDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交易发生日期</p></td><td></td></tr>
<tr><td><p>93</p></td><td><p>Transactiontime</p></td><td><p>A</p></td><td><p>6</p></td><td><p>交易发生时间</p></td><td></td></tr>
<tr><td><p>94</p></td><td><p>OtherFee1</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>其他费用1</p></td><td></td></tr>
<tr><td><p>95</p></td><td><p>OtherFee2</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其他费用2</p></td><td></td></tr>
<tr><td><p>96</p></td><td><p>OtherFee3</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>其他费用3</p></td><td></td></tr>
<tr><td><p>97</p></td><td><p>TargetDistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>对方销售人代码</p></td><td></td></tr>
<tr><td><p>98</p></td><td><p>IndividualOrInstitution</p></td><td><p>A</p></td><td><p>1</p></td><td><p>个人/机构标志</p></td><td><p>0-机构，1-个人，2-产品</p></td></tr>
<tr><td><p>99</p></td><td><p>IndiAppSubsVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>个人追加认购份数</p></td><td></td></tr>
<tr><td><p>100</p></td><td><p>IndiAppSubsAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>个人追加认购金额</p></td><td></td></tr>
<tr><td><p>101</p></td><td><p>PostCode</p></td><td><p>A</p></td><td><p>6</p></td><td><p>投资人邮政编码</p></td><td></td></tr>
<tr><td><p>102</p></td><td><p>RedemptionDateInAdvance</p></td><td><p>A</p></td><td><p>8</p></td><td><p>预约赎回日期</p></td><td></td></tr>
<tr><td><p>103</p></td><td><p>IPOPrice</p></td><td><p>N</p></td><td><p>7(四位小数)</p></td><td><p>发行价格</p></td><td></td></tr>
<tr><td><p>104</p></td><td><p>MinSubsVolByIndi</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>个人首次认购最低份数</p></td><td></td></tr>
<tr><td><p>105</p></td><td><p>MinSubsAmountByIndi</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>个人首次认购最低金额</p></td><td></td></tr>
<tr><td><p>106</p></td><td><p>TransactorCertNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>经办人证件号码</p></td><td></td></tr>
<tr><td><p>107</p></td><td><p>TransactorCertType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>经办人证件类型</p></td><td><p>参考数据字典“证件类型”中的个人部分</p></td></tr>
<tr><td><p>108</p></td><td><p>TransactorName</p></td><td><p>C</p></td><td><p>60</p></td><td><p>经办人姓名</p></td><td></td></tr>
<tr><td><p>109</p></td><td><p>TotalRedemptionAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金赎回总金额</p></td><td></td></tr>
<tr><td><p>110</p></td><td><p>TotalTransactionOfSuccessfulRedemption</p></td><td><p>N</p></td><td><p>10</p></td><td><p>成功赎回总笔数</p></td><td></td></tr>
<tr><td><p>111</p></td><td><p>TotalFeeOfRedemption</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>赎回手续费总金额</p></td><td></td></tr>
<tr><td><p>112</p></td><td><p>VolOnRegistraionDate</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>权益登记日基金账户份数</p></td><td></td></tr>
<tr><td><p>113</p></td><td><p>RegistrationDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>权益登记日期</p></td><td></td></tr>
<tr><td><p>114</p></td><td><p>RegistrarCode</p></td><td><p>C</p></td><td><p>18</p></td><td><p>注册登记人代码</p></td><td></td></tr>
<tr><td><p>115</p></td><td><p>RegistrationFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>注册登记费</p></td><td></td></tr>
<tr><td><p>116</p></td><td><p>TotalReinvestmentDividend</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>红利自动再投资总金额</p></td><td></td></tr>
<tr><td><p>117</p></td><td><p>BackAmountByExcess</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>因为剩余而划回投资人的资金</p></td><td></td></tr>
<tr><td><p>118</p></td><td><p>TotalRedemptionVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>赎回总份数</p></td><td></td></tr>
<tr><td><p>119</p></td><td><p>ReturnCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>交易处理返回代码</p></td><td></td></tr>
<tr><td><p>120</p></td><td><p>TransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>投资人基金交易账号</p></td><td><p>投资人在销售机构开设的用于交易的账号</p></td></tr>
<tr><td><p>121</p></td><td><p>DistributorCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>销售人代码</p></td><td></td></tr>
<tr><td><p>122</p></td><td><p>AccountAbbr</p></td><td><p>C</p></td><td><p>20</p></td><td><p>投资人户名简称</p></td><td></td></tr>
<tr><td><p>123</p></td><td><p>DividendRatio</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>红利比例</p></td><td></td></tr>
<tr><td><p>124</p></td><td><p>ConfidentialDocumentCode</p></td><td><p>C</p></td><td><p>8</p></td><td><p>密函编号</p></td><td></td></tr>
<tr><td><p>125</p></td><td><p>DocumentSendDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>文件发送日期</p></td><td></td></tr>
<tr><td><p>126</p></td><td><p>Sex</p></td><td><p>A</p></td><td><p>1</p></td><td><p>投资人性别</p></td><td><p>1-男，2-女</p></td></tr>
<tr><td><p>127</p></td><td><p>SHSecuritiesAccountID</p></td><td><p>C</p></td><td><p>10</p></td><td><p>上交所证券账号</p></td><td></td></tr>
<tr><td><p>128</p></td><td><p>SZSecuritiesAccountID</p></td><td><p>C</p></td><td><p>10</p></td><td><p>深交所证券账号</p></td><td></td></tr>
<tr><td><p>129</p></td><td><p>FundSize</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金规模</p></td><td></td></tr>
<tr><td><p>130</p></td><td><p>FundSponsor</p></td><td><p>C</p></td><td><p>18</p></td><td><p>基金发起人</p></td><td></td></tr>
<tr><td><p>131</p></td><td><p>AnnouncementTitle</p></td><td><p>C</p></td><td><p>100</p></td><td><p>公告标题</p></td><td></td></tr>
<tr><td><p>132</p></td><td><p>ApplicationVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请基金份数</p></td><td></td></tr>
<tr><td><p>133</p></td><td><p>TradingPrice</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>交易价格</p></td><td><p>投资者的单位交易成本</p></td></tr>
<tr><td><p>134</p></td><td><p>ApplicationAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请金额</p></td><td></td></tr>
<tr><td><p>135</p></td><td><p>BusinessCode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务代码</p></td><td></td></tr>
<tr><td><p>136</p></td><td><p>TAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>投资人基金账号</p></td><td></td></tr>
<tr><td><p>137</p></td><td><p>TASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>TA确认交易流水号</p></td><td></td></tr>
<tr><td><p>138</p></td><td><p>StampDuty</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>印花税</p></td><td></td></tr>
<tr><td><p>139</p></td><td><p>Tax</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>税金</p></td><td></td></tr>
<tr><td><p>140</p></td><td><p>TelNo</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人电话号码</p></td><td></td></tr>
<tr><td><p>141</p></td><td><p>TargetBranchCode</p></td><td><p>C</p></td><td><p>9</p></td><td><p>对方网点号</p></td><td></td></tr>
<tr><td><p>142</p></td><td><p>TargetTransactionAccountID</p></td><td><p>C</p></td><td><p>17</p></td><td><p>对方销售人处投资人交易账号</p></td><td></td></tr>
<tr><td><p>143</p></td><td><p>AggregationOfTransactionByBusinessType</p></td><td><p>N</p></td><td><p>16</p></td><td><p>每种业务笔数汇总</p></td><td></td></tr>
<tr><td><p>144</p></td><td><p>AggregationDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>汇总日期</p></td><td></td></tr>
<tr><td><p>145</p></td><td><p>TotalVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金份数汇总</p></td><td></td></tr>
<tr><td><p>146</p></td><td><p>TotalAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金金额汇总</p></td><td></td></tr>
<tr><td><p>147</p></td><td><p>TargetTAAccountID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>对方基金账号</p></td><td></td></tr>
<tr><td><p>148</p></td><td><p>TrailCommission</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>尾随佣金</p></td><td></td></tr>
<tr><td><p>149</p></td><td><p>UpdateDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>基金净值日期</p></td><td></td></tr>
<tr><td><p>150</p></td><td><p>ValidPeriod</p></td><td><p>N</p></td><td><p>2</p></td><td><p>交易申请有效天数</p></td><td></td></tr>
<tr><td><p>151</p></td><td><p>FaceValue</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>基金面值</p></td><td></td></tr>
<tr><td><p>152</p></td><td><p>TargetRegionCode</p></td><td><p>A</p></td><td><p>4</p></td><td><p>对方所在地区编号</p></td><td></td></tr>
<tr><td><p>153</p></td><td><p>TotalFailingVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>失败份数汇总</p></td><td></td></tr>
<tr><td><p>154</p></td><td><p>TotalSuccessfulVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>成功份数汇总</p></td><td></td></tr>
<tr><td><p>155</p></td><td><p>DividendPerUnit</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>单位基金分红金额(含税)</p></td><td></td></tr>
<tr><td><p>156</p></td><td><p>InterestTax</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>利息税</p></td><td></td></tr>
<tr><td><p>157</p></td><td><p>FundVolBalance</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金份数余额</p></td><td></td></tr>
<tr><td><p>158</p></td><td><p>BeginAllotNo</p></td><td><p>N</p></td><td><p>12</p></td><td><p>配号开始号</p></td><td></td></tr>
<tr><td><p>159</p></td><td><p>EndAllotNo</p></td><td><p>N</p></td><td><p>12</p></td><td><p>配号结束号</p></td><td></td></tr>
<tr><td><p>160</p></td><td><p>TotalAllotNo</p></td><td><p>N</p></td><td><p>12</p></td><td><p>配号总数</p></td><td></td></tr>
<tr><td><p>161</p></td><td><p>CfmVolOfTargetFund</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>目标基金的确认份数</p></td><td></td></tr>
<tr><td><p>162</p></td><td><p>TargetNAV</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>目标基金的单位净值</p></td><td></td></tr>
<tr><td><p>163</p></td><td><p>TargetFundPrice</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>目标基金的价格</p></td><td></td></tr>
<tr><td><p>164</p></td><td><p>TradingMethod</p></td><td><p>C</p></td><td><p>8</p></td><td><p>使用的交易手段</p></td><td><p>共8个字符，每个字符代表一种交易手段，其含义为：第1位：CALLCENTER<br>第2位：INTERNET<br>第3位：自助终端</p><p>第4位：柜台<br>第5~8位：保留<br>每个字符取1表示使用此种手段，取0表示不使用</p></td></tr>
<tr><td><p>165</p></td><td><p>ContractNo</p></td><td><p>A</p></td><td><p>20</p></td><td><p>合约编号</p></td><td></td></tr>
<tr><td><p>166</p></td><td><p>SelfHelp</p></td><td><p>C</p></td><td><p>1</p></td><td><p>自助终端</p></td><td><p>0-取消，1-开通</p></td></tr>
<tr><td><p>167</p></td><td><p>MinorFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>未成年人标志</p></td><td><p>0-否，1-是</p></td></tr>
<tr><td><p>168</p></td><td><p>MinorID</p></td><td><p>C</p></td><td><p>18</p></td><td><p>未成年人ID号</p></td><td><p>原身份证字段在儿童开户时代表监护人的身份证号</p></td></tr>
<tr><td><p>169</p></td><td><p>DeliverType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>对帐单寄送选择</p></td><td><p>1-不寄送，2-按季，3-半年，4-一年</p></td></tr>
<tr><td><p>170</p></td><td><p>TransactorIDType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>经办人识别方式</p></td><td><p>1-书面委托，2-印鉴，3-密码，4-证件</p></td></tr>
<tr><td><p>171</p></td><td><p>AccountCardID</p></td><td><p>C</p></td><td><p>8</p></td><td><p>基金账户卡的凭证号</p></td><td></td></tr>
<tr><td><p>172</p></td><td><p>TotalFrontendFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易前端收费总额</p></td><td></td></tr>
<tr><td><p>173</p></td><td><p>TotalBackendLoad</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易后端收费总额</p></td><td></td></tr>
<tr><td><p>174</p></td><td><p>TotalFailingAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>失败金额汇总</p></td><td></td></tr>
<tr><td><p>175</p></td><td><p>TotalSuccessfulAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>成功金额汇总</p></td><td></td></tr>
<tr><td><p>176</p></td><td><p>TransferDirection</p></td><td><p>A</p></td><td><p>1</p></td><td><p>转入/转出标识</p></td><td><p>0-转出，1-转入</p></td></tr>
<tr><td><p>177</p></td><td><p>BusinessFinishFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>业务过程完全结束标识</p></td><td><p>0-中间过程</p><p>1-业务过程结束</p></td></tr>
<tr><td><p>178</p></td><td><p>TotalFailingDealingNum</p></td><td><p>N</p></td><td><p>16</p></td><td><p>失败交易笔数</p></td><td></td></tr>
<tr><td><p>179</p></td><td><p>TotalSuccessfulDealingNum</p></td><td><p>N</p></td><td><p>16</p></td><td><p>成功交易笔数</p></td><td></td></tr>
<tr><td><p>180</p></td><td><p>ConvertStatus</p></td><td><p>C</p></td><td><p>1</p></td><td><p>基金转换状态</p></td><td><p>0-可转入，可转出</p><p>1-只可转入</p><p>2-只可转出</p><p>3-不可转换</p></td></tr>
<tr><td><p>181</p></td><td><p>AcctNameOfInvestorInClearingAgency</p></td><td><p>C</p></td><td><p>200</p></td><td><p>投资人收款银行账户户名</p></td><td></td></tr>
<tr><td><p>182</p></td><td><p>AcctNoOfInvestorInClearingAgency</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投资人收款银行账户账号</p></td><td></td></tr>
<tr><td><p>183</p></td><td><p>ClearingAgency</p></td><td><p>C</p></td><td><p>20</p></td><td><p>投资人收款银行账户开户行</p></td><td><p>填写银行三位销售机构代码</p></td></tr>
<tr><td><p>184</p></td><td><p>UnFrozenBalance</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>解冻红利金额</p></td><td></td></tr>
<tr><td><p>185</p></td><td><p>BusinessOrganiger</p></td><td><p>C</p></td><td><p>3</p></td><td><p>业务发起人代码</p></td><td><p>指是TA发起还是销售商发起。TA发起，填2位TA编号</p></td></tr>
<tr><td><p>186</p></td><td><p>AccountType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>账户类型</p></td><td><p>0-普通账户，1-机构散户</p></td></tr>
<tr><td><p>187</p></td><td><p>FrozenBalance</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>冻结金额</p></td><td></td></tr>
<tr><td><p>188</p></td><td><p>FrozenShares</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>冻结红利再投资份数</p></td><td></td></tr>
<tr><td><p>189</p></td><td><p>TotalFare</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>交易费用汇总</p></td><td></td></tr>
<tr><td><p>190</p></td><td><p>VastRedeemFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>巨额赎回标志</p></td><td><p>0：非巨额；1：巨额</p></td></tr>
<tr><td><p>191</p></td><td><p>TermOfPeriodicSubs</p></td><td><p>N</p></td><td><p>5</p></td><td><p>定时定额申购期限</p></td><td></td></tr>
<tr><td><p>192</p></td><td><p>FutureBuyDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>指定申购日期</p></td><td></td></tr>
<tr><td><p>193</p></td><td><p>RateFee</p></td><td><p>N</p></td><td><p>9(八位小数)</p></td><td><p>费率</p></td><td><p>分段收费考虑</p></td></tr>
<tr><td><p>194</p></td><td><p>MinFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>最少收费</p></td><td></td></tr>
<tr><td><p>195</p></td><td><p>DaysRedemptionInAdvance</p></td><td><p>N</p></td><td><p>5</p></td><td><p>预约赎回工作日天数</p></td><td></td></tr>
<tr><td><p>198</p></td><td><p>MaxSubsVolByIndi</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>个人最高认购份数</p></td><td></td></tr>
<tr><td><p>199</p></td><td><p>MaxSubsAmountByIndi</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>个人最高认购金额</p></td><td></td></tr>
<tr><td><p>200</p></td><td><p>MaxSubsVolByInst</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>法人最高认购份数</p></td><td></td></tr>
<tr><td><p>201</p></td><td><p>MaxSubsAmountByInst</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>法人最高认购金额</p></td><td></td></tr>
<tr><td><p>202</p></td><td><p>UnitSubsVolByIndi</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>个人认购份数单位</p></td><td></td></tr>
<tr><td><p>203</p></td><td><p>UnitSubsAmountByIndi</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>个人认购金额单位</p></td><td></td></tr>
<tr><td><p>204</p></td><td><p>UnitSubsVolByInst</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>法人认购份数单位</p></td><td></td></tr>
<tr><td><p>205</p></td><td><p>UnitSubsAmountByInst</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>法人认购金额单位</p></td><td></td></tr>
<tr><td><p>206</p></td><td><p>MinBidsAmountByIndi</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>个人首次申购最低金额</p></td><td></td></tr>
<tr><td><p>207</p></td><td><p>MinBidsAmountByInst</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>法人首次申购最低金额</p></td><td></td></tr>
<tr><td><p>208</p></td><td><p>MinAppBidsAmountByIndi</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>个人追加申购最低金额</p></td><td></td></tr>
<tr><td><p>209</p></td><td><p>MinAppBidsAmountByInst</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>法人追加申购最低金额</p></td><td></td></tr>
<tr><td><p>210</p></td><td><p>MinRedemptionVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金最少赎回份数</p></td><td></td></tr>
<tr><td><p>211</p></td><td><p>MinInterconvertVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>最低基金转换份数</p></td><td></td></tr>
<tr><td><p>212</p></td><td><p>IssueTypeByIndi</p></td><td><p>C</p></td><td><p>1</p></td><td><p>个人发行方式</p></td><td><p>1-比例发行，2-摇号</p><p>3-先来先买</p></td></tr>
<tr><td><p>213</p></td><td><p>IssueTypeByInst</p></td><td><p>C</p></td><td><p>1</p></td><td><p>机构发行方式</p></td><td><p>1-比例发行，2-摇号</p><p>3-先来先买</p></td></tr>
<tr><td><p>214</p></td><td><p>SubsType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>认购方式</p></td><td><p>0-金额认购，1-份数认购</p></td></tr>
<tr><td><p>215</p></td><td><p>CollectFeeType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>交易费收取方式</p></td><td><p>0-价内费，1-价外费</p></td></tr>
<tr><td><p>216</p></td><td><p>NextTradeDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>下一开放日</p></td><td></td></tr>
<tr><td><p>217</p></td><td><p>SalerNetReceivableAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>销售人净收结算金额</p></td><td></td></tr>
<tr><td><p>218</p></td><td><p>SalerNetPayableAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>销售人净付结算金额</p></td><td></td></tr>
<tr><td><p>219</p></td><td><p>SalerTotalFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>销售人收取费用总额</p></td><td></td></tr>
<tr><td><p>220</p></td><td><p>SalerBuyFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>销售人收取申购费用</p></td><td></td></tr>
<tr><td><p>221</p></td><td><p>SalerBidFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>销售人收取赎回费用</p></td><td></td></tr>
<tr><td><p>222</p></td><td><p>FundTotalFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>赎回费用总额(扣除保留在基金资产部分)</p></td><td></td></tr>
<tr><td><p>223</p></td><td><p>RaiseTotalAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>认购资金总额</p></td><td></td></tr>
<tr><td><p>224</p></td><td><p>AccumulativeTotalRaiseAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>累计认购资金总额</p></td><td></td></tr>
<tr><td><p>225</p></td><td><p>RaiseInterest</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>认购期间利息</p></td><td></td></tr>
<tr><td><p>226</p></td><td><p>SalerRaiseFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>销售人认购费</p></td><td></td></tr>
<tr><td><p>227</p></td><td><p>Conversion InAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>转入款</p></td><td></td></tr>
<tr><td><p>228</p></td><td><p>Converting To Amount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>转出款</p></td><td></td></tr>
<tr><td><p>229</p></td><td><p>Saler Exchange Fee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>销售人转换费</p></td><td></td></tr>
<tr><td><p>230</p></td><td><p>Bid Tax</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申购印花税</p></td><td></td></tr>
<tr><td><p>231</p></td><td><p>Redemption Tax</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>赎回印花税</p></td><td></td></tr>
<tr><td><p>232</p></td><td><p>IndividualCapitalGainTax</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>分红个人利得所得税</p></td><td></td></tr>
<tr><td><p>233</p></td><td><p>InstituteCapital GainTax</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>分红机构利得所得税</p></td><td></td></tr>
<tr><td><p>234</p></td><td><p>Individual Income Tax</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>分红个人增值所得税</p></td><td></td></tr>
<tr><td><p>235</p></td><td><p>Institute Income Tax</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>分红机构增值所得税</p></td><td></td></tr>
<tr><td><p>236</p></td><td><p>SalerReinvestmentFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>销售人再投资费</p></td><td></td></tr>
<tr><td><p>237</p></td><td><p>SubFeeRetTA</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申购归注册登记人所得费用</p></td><td><p>包括注册登记人的费用</p></td></tr>
<tr><td><p>238</p></td><td><p>RedemFeeRetTA</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>赎回归注册登记人所得费用</p></td><td><p>包括注册登记人的费用</p></td></tr>
<tr><td><p>239</p></td><td><p>TotalTransInAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金转换入总金额</p></td><td></td></tr>
<tr><td><p>240</p></td><td><p>TotalFeeOfTransInAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金转换入手续费总金额</p></td><td></td></tr>
<tr><td><p>241</p></td><td><p>TotalTransInVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金转换入总份数</p></td><td></td></tr>
<tr><td><p>242</p></td><td><p>TotalTransOutAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金转换出总金额</p></td><td></td></tr>
<tr><td><p>243</p></td><td><p>TotalFeeOfTransOutAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金转换出手续费总金额</p></td><td></td></tr>
<tr><td><p>244</p></td><td><p>TotalTransOutVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金转换出总份数</p></td><td></td></tr>
<tr><td><p>245</p></td><td><p>BidTrade</p></td><td><p>N</p></td><td><p>13</p></td><td><p>成功申购总户数</p></td><td></td></tr>
<tr><td><p>246</p></td><td><p>RedeemTrade</p></td><td><p>N</p></td><td><p>13</p></td><td><p>成功赎回总户数</p></td><td></td></tr>
<tr><td><p>247</p></td><td><p>FreezeTotal</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>冻结总份数</p></td><td></td></tr>
<tr><td><p>248</p></td><td><p>ManagerCode</p></td><td><p>C</p></td><td><p>18</p></td><td><p>管理人代码</p></td><td></td></tr>
<tr><td><p>249</p></td><td><p>NetBidTotalAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申购成功资金总额(不含费用，不含税)</p></td><td></td></tr>
<tr><td><p>250</p></td><td><p>NetRedeemTotalAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>赎回成功资金总额(不含费用，不含税)</p></td><td></td></tr>
<tr><td><p>251</p></td><td><p>CreditDebit</p></td><td><p>N</p></td><td><p>1</p></td><td><p>借贷方向</p></td><td><p>0-借方 1-贷方</p></td></tr>
<tr><td><p>252</p></td><td><p>RedemptionFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>赎回费</p></td><td></td></tr>
<tr><td><p>253</p></td><td><p>NetSettlement</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>资金清算净额</p></td><td><p>全额交收可以用作实际清算额</p></td></tr>
<tr><td><p>254</p></td><td><p>Specification</p></td><td><p>C</p></td><td><p>60</p></td><td><p>摘要/说明</p></td><td></td></tr>
<tr><td><p>255</p></td><td><p>TransferFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>过户费</p></td><td></td></tr>
<tr><td><p>256</p></td><td><p>FromTAFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>是否注册登记人发起业务标志</p></td><td><p>0-由销售人发起</p><p>1-由注册登记人发起</p><p>2-由管理人发起</p></td></tr>
<tr><td><p>257</p></td><td><p>FrozenMethod</p></td><td><p>A</p></td><td><p>1</p></td><td><p>冻结方式</p></td><td><p>0-原份数冻结，</p><p>1-原份数+滋息冻结</p></td></tr>
<tr><td><p>258</p></td><td><p>OriginalAppDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>原申请日期</p></td><td><p>格式为：YYYYMMDD</p></td></tr>
<tr><td><p>259</p></td><td><p>TotalBackendLoadVol</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>交易后端收费总份数</p></td><td></td></tr>
<tr><td><p>260</p></td><td><p>ShareClass</p></td><td><p>A</p></td><td><p>1</p></td><td><p>收费类别(份额类别)</p></td><td><p>0-前收费，1-后收费</p></td></tr>
<tr><td><p>261</p></td><td><p>OriginalCfmDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>TA的原确认日期</p></td><td></td></tr>
<tr><td><p>262</p></td><td><p>RedemptionInAdvanceFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>预约赎回标志</p></td><td><p>0-非预约赎回，1-预约赎回</p></td></tr>
<tr><td><p>263</p></td><td><p>RedemptionReason</p></td><td><p>A</p></td><td><p>1</p></td><td><p>强行赎回原因</p></td><td><p>0-小于最低持有数，</p><p>1-司法执行，2-政策原因</p><p>3-全份额快速过户后强制结转收益并强赎，4-到期清盘</p></td></tr>
<tr><td><p>264</p></td><td><p>DetailFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>明细标志</p></td><td><p>0-非明细，1-明细</p></td></tr>
<tr><td><p>265</p></td><td><p>DeliverWay</p></td><td><p>C</p></td><td><p>8</p></td><td><p>对帐单寄送方式</p></td><td><p>共8个字符，每个字符代表一种交易手段，其含义为：</p><p>第1位：邮寄，</p><p>第2位：传真，</p><p>第3位：E-mail，</p><p>第4位：短消息，</p><p>第5~8位：保留。</p><p>每位字符取1表示采用此种手段，取0表示不使用</p></td></tr>
<tr><td><p>266</p></td><td><p>VolumeByInterest</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>利息产生的基金份数</p></td><td></td></tr>
<tr><td><p>267</p></td><td><p>ValueLine</p></td><td><p>N</p></td><td><p>7(两位小数)</p></td><td><p>产品价值线数值</p></td><td></td></tr>
<tr><td><p>268</p></td><td><p>AccountStatus</p></td><td><p>A</p></td><td><p>1</p></td><td><p>账户状态</p></td><td><p>0-正常，1-冻结，2-挂失，3-注销</p></td></tr>
<tr><td><p>269</p></td><td><p>BeginDateOfPeriodicSubs</p></td><td><p>A</p></td><td><p>8</p></td><td><p>定时定额申购起始日期</p></td><td><p>格式为：YYYYMMDD</p></td></tr>
<tr><td><p>270</p></td><td><p>EndDateOfPeriodicSubs</p></td><td><p>A</p></td><td><p>8</p></td><td><p>定时定额申购终止日期</p></td><td><p>格式为：YYYYMMDD</p></td></tr>
<tr><td><p>271</p></td><td><p>SendDayOfPeriodicSubs</p></td><td><p>N</p></td><td><p>2</p></td><td><p>定时定额申购每周期发送日</p></td><td><p>指每周期的第几天。如果遇非交易日，则顺延到下一交易日。</p></td></tr>
<tr><td><p>272</p></td><td><p>TotalVolumeofReinvestmentDividend</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>红利再投资份额总额</p></td><td></td></tr>
<tr><td><p>273</p></td><td><p>AccumulativeNAV</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>累计基金单位净值</p></td><td></td></tr>
<tr><td><p>274</p></td><td><p>ShareRegisterDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>份额注册日期</p></td><td></td></tr>
<tr><td><p>275</p></td><td><p>LargeBuyFlag</p></td><td><p>A</p></td><td><p>1</p></td><td><p>巨额购买处理标志</p></td><td><p>0-取消，1-顺延</p></td></tr>
<tr><td><p>276</p></td><td><p>FeeCalculator</p></td><td><p>A</p></td><td><p>1</p></td><td><p>计费人</p></td><td><p>0-TA计费  1-基金计费</p></td></tr>
<tr><td><p>277</p></td><td><p>IndiAcctCfmRate</p></td><td><p>N</p></td><td><p>5(四位小数)</p></td><td><p>个人账户确认比例</p></td><td></td></tr>
<tr><td><p>278</p></td><td><p>InstAcctCfmRate</p></td><td><p>N</p></td><td><p>5(四位小数)</p></td><td><p>机构账户确认比例</p></td><td></td></tr>
<tr><td><p>279</p></td><td><p>GenAcctCfmRate</p></td><td><p>N</p></td><td><p>5(四位小数)</p></td><td><p>综合账户确认比例</p></td><td></td></tr>
<tr><td><p>280</p></td><td><p>VarietyCodeOfPeriodicSubs</p></td><td><p>C</p></td><td><p>5</p></td><td><p>定时定额品种代码</p></td><td></td></tr>
<tr><td><p>281</p></td><td><p>SerialNoOfPeriodicSubs</p></td><td><p>C</p></td><td><p>5</p></td><td><p>定时定额申购序号</p></td><td></td></tr>
<tr><td><p>282</p></td><td><p>CorpName</p></td><td><p>C</p></td><td><p>200</p></td><td><p>工作单位名称</p></td><td></td></tr>
<tr><td><p>283</p></td><td><p>RefundAmount</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>退款金额</p></td><td></td></tr>
<tr><td><p>284</p></td><td><p>SecuritiesAccountID</p></td><td><p>C</p></td><td><p>10</p></td><td><p>证券账号</p></td><td></td></tr>
<tr><td><p>285</p></td><td><p>SalePercent</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>配售比例</p></td><td></td></tr>
<tr><td><p>286</p></td><td><p>CertValidDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>证件有效日期</p></td><td></td></tr>
<tr><td><p>287</p></td><td><p>InstTranCertValidDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>机构经办人身份证件有效日期</p></td><td></td></tr>
<tr><td><p>288</p></td><td><p>InstReprCertValidDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>机构法人身份证件有效日期</p></td><td></td></tr>
<tr><td><p>289</p></td><td><p>ClientRiskRate</p></td><td><p>C</p></td><td><p>1</p></td><td><p>客户风险等级</p></td><td><p>1-低风险承受能力</p><p>2-较低风险承受能力</p><p>3-中等风险承受能力</p><p>4-较高风险承受能力</p><p>5-高风险承受能力</p></td></tr>
<tr><td><p>290</p></td><td><p>InstReprManageRange</p></td><td><p>C</p></td><td><p>2</p></td><td><p>机构法人经营范围</p></td><td><p>01-农、林、牧、渔业 02-采矿业03-制造业 04-电力、燃气及水的生产和供应业 05-建筑业 06-交通运输、仓储和邮政业  07-信息传输、计算机服务和软件业 08-批发和零售业 09-住宿和餐饮业 10-金融业 11-房地产业 12-租赁和商务服务业 13-科学研究、技术服务和地质勘查业 14-水利、环境和公共设施管理业 15-居民服务和其他服务业 16-教育 17-卫生、社会保障和社会福利业 18-文化、体育和娱乐业 19-公共管理与社会组织 20-国际组织</p></td></tr>
<tr><td><p>291</p></td><td><p>ControlHolder</p></td><td><p>C</p></td><td><p>2000</p></td><td><p>控股股东</p></td><td></td></tr>
<tr><td><p>292</p></td><td><p>ActualController</p></td><td><p>C</p></td><td><p>2000</p></td><td><p>实际控制人</p></td><td></td></tr>
<tr><td><p>293</p></td><td><p>MarriageStatus</p></td><td><p>C</p></td><td><p>1</p></td><td><p>婚姻状况</p></td><td><p>0-未婚  1-已婚</p></td></tr>
<tr><td><p>294</p></td><td><p>FamilyNum</p></td><td><p>N</p></td><td><p>2</p></td><td><p>家庭人口数</p></td><td></td></tr>
<tr><td><p>295</p></td><td><p>Penates</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>家庭资产</p></td><td></td></tr>
<tr><td><p>296</p></td><td><p>MediaHobby</p></td><td><p>C</p></td><td><p>1</p></td><td><p>媒体偏好</p></td><td><p>0-网络  1-广播 2-电视 3-报刊 4-其它</p></td></tr>
<tr><td><p>297</p></td><td><p>CustomerNo</p></td><td><p>C</p></td><td><p>12</p></td><td><p>TA客户编号</p></td><td></td></tr>
<tr><td><p>298</p></td><td><p>RationProtocolNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>定期定额协议号</p></td><td></td></tr>
<tr><td><p>299</p></td><td><p>RationType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>定期定额种类</p></td><td></td></tr>
<tr><td><p>300</p></td><td><p>BreachFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>违约金</p></td><td></td></tr>
<tr><td><p>301</p></td><td><p>SalesPromotion</p></td><td><p>C</p></td><td><p>3</p></td><td><p>促销活动代码</p></td><td></td></tr>
<tr><td><p>302</p></td><td><p>AcceptMethod</p></td><td><p>C</p></td><td><p>1</p></td><td><p>受理方式</p></td><td><p>0-柜台1-电话2-网上3-自助 4-传真 5-其他</p></td></tr>
<tr><td><p>303</p></td><td><p>ForceRedemptionType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>强制赎回类型</p></td><td><p>0-强制赎回，1-违约赎回，2-到期 3-个人养老金提前赎回</p></td></tr>
<tr><td><p>304</p></td><td><p>AllowBreachRedempt</p></td><td><p>C</p></td><td><p>1</p></td><td><p>允许违约赎回标志</p></td><td><p>0-允许，1-不允许</p></td></tr>
<tr><td><p>305</p></td><td><p>PunishFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>惩罚性费用</p></td><td></td></tr>
<tr><td><p>306</p></td><td><p>BreachFeeBackToFund</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>违约金归基金资产金额</p></td><td></td></tr>
<tr><td><p>307</p></td><td><p>FutureSubscribeDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>指定认购日期</p></td><td></td></tr>
<tr><td><p>308</p></td><td><p>TotalDivident</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>累计单位分红</p></td><td></td></tr>
<tr><td><p>309</p></td><td><p>ErrorDetail</p></td><td><p>C</p></td><td><p>60</p></td><td><p>出错详细信息</p></td><td></td></tr>
<tr><td><p>310</p></td><td><p>FundType</p></td><td><p>C</p></td><td><p>2</p></td><td><p>基金类型</p></td><td><p>公募产品(含证券公司参照公募基金管理的大集合)：</p><p>01-股票型02-债券型03-混合型04-货币型 05-其它  06-基金中基金</p><p>非公募产品：</p><p>11:银行理财产品；12:信托计划；13:基金公司单一资管计划;14基金公司集合资管计划；15:基金子公司单一资管计划;16基金子公司集合资管计划;17保险产品；18:保险公司及其子公司资产管理计划；19:证券公司及其子公司集合资管计划；20:证券公司及其子公司单一资管计划；21:期货公司及其子公司资产管理计划；22:私募投资基金；23:政府类引导基金；24:全国社保基金；25:地方社保基金；26:基本养老保险；27:养老金产品；28:企业年金及职业年金；29:境外资金（QFII）；30:境外资金（RQFII）；31:其它境外资金；32:社会公益基金（慈善基金、捐赠基金等）；99:其他产品</p></td></tr>
<tr><td><p>311</p></td><td><p>PointsType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>积分类型</p></td><td><p>0-基金公司一般积分 1-利添利联名卡积分</p></td></tr>
<tr><td><p>312</p></td><td><p>Points</p></td><td><p>N</p></td><td><p>15（两位小数）</p></td><td><p>积分值</p></td><td></td></tr>
<tr><td><p>313</p></td><td><p>FundCorpCode</p></td><td><p>C</p></td><td><p>8</p></td><td><p>基金公司代码</p></td><td></td></tr>
<tr><td><p>314</p></td><td><p>FundServerTel</p></td><td><p>C</p></td><td><p>40</p></td><td><p>基金公司客服电话</p></td><td></td></tr>
<tr><td><p>315</p></td><td><p>FundInternetAddress</p></td><td><p>C</p></td><td><p>200</p></td><td><p>基金公司网站网址</p></td><td></td></tr>
<tr><td><p>316</p></td><td><p>PointsStatus</p></td><td><p>C</p></td><td><p>1</p></td><td><p>积分状态</p></td><td><p>0-正常 1-作废</p></td></tr>
<tr><td><p>317</p></td><td><p>AnnouncFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>公告标志</p></td><td><p>0-公告  1-不公告</p></td></tr>
<tr><td><p>318</p></td><td><p>TransferPermitFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>跨市场转入允许标志</p></td><td><p>0-允许，1-不允许</p></td></tr>
<tr><td><p>319</p></td><td><p>InstAccount</p></td><td><p>C</p></td><td><p>30</p></td><td><p>销售人结算法人资金帐号</p></td><td></td></tr>
<tr><td><p>320</p></td><td><p>CapitalType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>资金类型</p></td><td></td></tr>
<tr><td><p>321</p></td><td><p>ReceOrPayFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>收付标志</p></td><td></td></tr>
<tr><td><p>322</p></td><td><p>CalculateDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>清算日期</p></td><td></td></tr>
<tr><td><p>323</p></td><td><p>PayDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>交收日期</p></td><td></td></tr>
<tr><td><p>324</p></td><td><p>SeatCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>席位代码</p></td><td></td></tr>
<tr><td><p>325</p></td><td><p>InstitutionType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>机构类型</p></td><td><p>若为机构分类如下：</p><p>101:证券公司；102:证券公司子公司；103:银行；104:信托公司；105:基金管理公司；106:基金管理公司子公司；107:保险公司；108:私募基金管理人；109:期货公司；110:期货公司子公司；111:财务公司；112:其他境内金融机构；113:机关法人；114:事业单位法人；115:社会团体法人；116:非金融机构企业法人；117:非金融类非法人机构；118:境外代理人；119:境外金融机构；120:外国战略投资者；121:境外非金融机构；122:其它；123:银行子公司；124:保险子公司</p><p>若为产品分类如下：</p><p>201:开放式公募基金产品；202:封闭式公募基金产品；203:银行理财产品；204:信托计划；205:基金公司专户；206:基金子公司产品；207:保险产品；208:保险公司及其子公司的资产管理计划；209:证券公司及其子公司集合理财产品（含证券公司大集合）；210:证券公司及其子公司专项资管计划；211:证券公司及其子公司单一资管计划；212:期货公司及其子公司的资产管理计划；213:私募投资基金；214:政府引导基金；215:全国社保基金；216:地方社保基金；217:基本养老保险；218:养老金产品；219:企业年金及职业年金；220:境外资金（QFII）；221:境外资金（RQFII）；222:其它境外资金；223:社会公益基金（慈善基金、捐赠基金等）； 224:其他产品</p></td></tr>
<tr><td><p>326</p></td><td><p>DistributorName</p></td><td><p>C</p></td><td><p>200</p></td><td><p>销售人名称</p></td><td></td></tr>
<tr><td><p>327</p></td><td><p>TakeIncomeFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>带走收益标志</p></td><td><p>0-不带走，1-带走</p></td></tr>
<tr><td><p>328</p></td><td><p>PurposeOfPeSubs</p></td><td><p>C</p></td><td><p>40</p></td><td><p>定投目的</p></td><td></td></tr>
<tr><td><p>329</p></td><td><p>FrequencyOfPeSubs</p></td><td><p>N</p></td><td><p>5</p></td><td><p>定投频率</p></td><td></td></tr>
<tr><td><p>330</p></td><td><p>BatchNumOfPeSubs</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>定投期数</p></td><td></td></tr>
<tr><td><p>331</p></td><td><p>FundTypeName</p></td><td><p>C</p></td><td><p>30</p></td><td><p>基金类型名称</p></td><td></td></tr>
<tr><td><p>332</p></td><td><p>RegistrarName</p></td><td><p>C</p></td><td><p>100</p></td><td><p>注册登记人名称</p></td><td></td></tr>
<tr><td><p>333</p></td><td><p>FundManagerName</p></td><td><p>C</p></td><td><p>100</p></td><td><p>基金管理人名称</p></td><td></td></tr>
<tr><td><p>334</p></td><td><p>EnglishFirstName</p></td><td><p>C</p></td><td><p>20</p></td><td><p>投资人英文名</p></td><td></td></tr>
<tr><td><p>335</p></td><td><p>EnglishFamliyName</p></td><td><p>C</p></td><td><p>20</p></td><td><p>投资人英文姓</p></td><td></td></tr>
<tr><td><p>336</p></td><td><p>Vocation</p></td><td><p>C</p></td><td><p>4</p></td><td><p>行业</p></td><td><p>采用国标GB/T4754-2017 </p></td></tr>
<tr><td><p>337</p></td><td><p>CorpoProperty</p></td><td><p>C</p></td><td><p>2</p></td><td><p>企业性质</p></td><td><p>0-国企 1-民营 2-合资</p><p>3-其它</p></td></tr>
<tr><td><p>338</p></td><td><p>StaffNum</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>员工人数</p></td><td></td></tr>
<tr><td><p>339</p></td><td><p>Hobbytype</p></td><td><p>C</p></td><td><p>2</p></td><td><p>兴趣爱好类型</p></td><td></td></tr>
<tr><td><p>340</p></td><td><p>Province</p></td><td><p>C</p></td><td><p>6</p></td><td><p>省/直辖市</p></td><td><p>采用国标GB/T 2260-2007中6位数字代码</p></td></tr>
<tr><td><p>341</p></td><td><p>City</p></td><td><p>C</p></td><td><p>6</p></td><td><p>市</p></td><td><p>采用国标GB/T 2260-2007中6位数字代码</p></td></tr>
<tr><td><p>342</p></td><td><p>County</p></td><td><p>C</p></td><td><p>6</p></td><td><p>县/区</p></td><td><p>采用国标GB/T 2260-2007中6位数字代码</p></td></tr>
<tr><td><p>343</p></td><td><p>CommendPerson</p></td><td><p>C</p></td><td><p>40</p></td><td><p>推荐人</p></td><td></td></tr>
<tr><td><p>344</p></td><td><p>CommendPersonType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>推荐人类型</p></td><td><p>1:内部员工2:注册用户</p><p>3:基金账户4:客户经理编号5:客户经理姓名0:其他</p></td></tr>
<tr><td><p>345</p></td><td><p>CapitalMode</p></td><td><p>C</p></td><td><p>2</p></td><td><p>资金方式</p></td><td><p>1：普通方式，2：兴业银基通，3：银联通，4：工行网银，5：好易联，6：汇付天下，7：工行银基通，8：好易联托收，9：银行代扣款，A：农行网银，B：建行网银，C：交行网银，D：北京银行，E：支付宝，F：浦发网银，G：招行网银，H：开联网银，I：富友，J：民生网银，K：网下转账，L：平安网银，M：通联，N：中行网银，P：易宝，Q：财富通</p></td></tr>
<tr><td><p>346</p></td><td><p>DetailCapticalMode</p></td><td><p>C</p></td><td><p>2</p></td><td><p>明细资金方式</p></td><td></td></tr>
<tr><td><p>347</p></td><td><p>BackenloadDiscount</p></td><td><p>N</p></td><td><p>5（4位小数）</p></td><td><p>补差费折扣率</p></td><td></td></tr>
<tr><td><p>348</p></td><td><p>CombineNum</p></td><td><p>C</p></td><td><p>6</p></td><td><p>组合编号</p></td><td></td></tr>
<tr><td><p>349</p></td><td><p>AlternationDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>最后更新日</p></td><td></td></tr>
<tr><td><p>350</p></td><td><p>TargetDistributorType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>对方销售人类型</p></td><td></td></tr>
<tr><td><p>351</p></td><td><p>XRValue</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>单位除权值</p></td><td></td></tr>
<tr><td><p>352</p></td><td><p>XRValueFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>单位除权值正负</p></td><td><p>0-正  1-负</p></td></tr>
<tr><td><p>353</p></td><td><p>XRType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>除权类型</p></td><td><p>0-分红   1-净值调整</p></td></tr>
<tr><td><p>354</p></td><td><p>DividendType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>分红类型</p></td><td><p>0-普通分红，1-质押基金分红，2-货币基金收益结转，3-保本基金赔付，4- </p><p>清盘资产分配</p></td></tr>
<tr><td><p>355</p></td><td><p>SequenceNO</p></td><td><p>A</p></td><td><p>20</p></td><td><p>序号</p></td><td></td></tr>
<tr><td><p>356</p></td><td><p>OperateDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>生效日期</p></td><td><p>YYYYMMDD</p></td></tr>
<tr><td><p>357</p></td><td><p>VolLowerLimit</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>份额下限</p></td><td></td></tr>
<tr><td><p>358</p></td><td><p>VolUpperLimit</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>份额上限</p></td><td></td></tr>
<tr><td><p>359</p></td><td><p>AmountLowerLimit</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>金额下限</p></td><td></td></tr>
<tr><td><p>360</p></td><td><p>AmountUpperLimit</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>金额上限</p></td><td></td></tr>
<tr><td><p>361</p></td><td><p>DaysLowerLimit</p></td><td><p>N</p></td><td><p>5</p></td><td><p>天数下限</p></td><td></td></tr>
<tr><td><p>362</p></td><td><p>DaysUpperLimit</p></td><td><p>N</p></td><td><p>5</p></td><td><p>天数上限</p></td><td></td></tr>
<tr><td><p>363</p></td><td><p>MaxFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>最高费用</p></td><td></td></tr>
<tr><td><p>365</p></td><td><p>GetFeeRateMethod</p></td><td><p>C</p></td><td><p>1</p></td><td><p>取费率方式</p></td><td><p>1-按金额 2-按天数 3-按份额 4-不分段</p></td></tr>
<tr><td><p>366</p></td><td><p>FeeRateFlag </p></td><td><p>C</p></td><td><p>1</p></td><td><p>费率标志</p></td><td><p>0-绝对费率 1-相对费率</p></td></tr>
<tr><td><p>367</p></td><td><p>FundNameAbbr</p></td><td><p>C</p></td><td><p>80</p></td><td><p>基金简称</p></td><td></td></tr>
<tr><td><p>368</p></td><td><p>IsGuaranteedFund</p></td><td><p>C</p></td><td><p>1</p></td><td><p>是否保本基金</p></td><td><p>0-非  1-是</p></td></tr>
<tr><td><p>369</p></td><td><p>IsLOFFund</p></td><td><p>C</p></td><td><p>1</p></td><td><p>是否LOF基金</p></td><td><p>0-非  1-是</p></td></tr>
<tr><td><p>370</p></td><td><p>IsQDIIFund</p></td><td><p>C</p></td><td><p>1</p></td><td><p>是否QDII基金</p></td><td><p>0-非  1-是</p></td></tr>
<tr><td><p>371</p></td><td><p>IsETFFund</p></td><td><p>C</p></td><td><p>1</p></td><td><p>是否ETF基金</p></td><td><p>0-非  1-是</p></td></tr>
<tr><td><p>372</p></td><td><p>RedeemFeeBackRatio</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>赎回费归基金资产比例</p></td><td></td></tr>
<tr><td><p>373</p></td><td><p>FundEstablishDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>基金成立日期</p></td><td><p>YYYYMMDD</p></td></tr>
<tr><td><p>374</p></td><td><p>ConstantFee</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>固定费用</p></td><td></td></tr>
<tr><td><p>375</p></td><td><p>IsDiscount</p></td><td><p>C</p></td><td><p>1</p></td><td><p>是否允许打折</p></td><td><p>0-非  1-是</p></td></tr>
<tr><td><p>376</p></td><td><p>BuyPayPeriod</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申购交收天数</p></td><td></td></tr>
<tr><td><p>377</p></td><td><p>RedemptionPayPeriod</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>赎回交收天数</p></td><td></td></tr>
<tr><td><p>378</p></td><td><p>ConversionPayPeriod</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金转换交收天数</p></td><td></td></tr>
<tr><td><p>379</p></td><td><p>ChargePayMethod</p></td><td><p>C</p></td><td><p>1</p></td><td><p>手续费结算方式</p></td><td><p>0-净额结算  1-全额结算</p></td></tr>
<tr><td><p>380</p></td><td><p>CompareProportion</p></td><td><p>N</p></td><td><p>16（八位小数）</p></td><td><p>相对比例</p></td><td><p>费率针对指定费率的比例，即费率/指定费率</p></td></tr>
<tr><td><p>381</p></td><td><p>CompareCapitalType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>相对资金类型</p></td><td></td></tr>
<tr><td><p>382</p></td><td><p>SubPayBackPeriod</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>认购退款交收天数</p></td><td></td></tr>
<tr><td><p>383</p></td><td><p>DividendPayPeriod</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>分红交收天数</p></td><td></td></tr>
<tr><td><p>384</p></td><td><p>WholeFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>全量标志</p></td><td><p>0-增量   1-全量</p></td></tr>
<tr><td><p>385</p></td><td><p>ModifyWay</p></td><td><p>C</p></td><td><p>1</p></td><td><p>修改方式</p></td><td><p>0-新增   1-修改  2-删除</p></td></tr>
<tr><td><p>386</p></td><td><p>ChangeAgencyFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>转换代理费</p></td><td></td></tr>
<tr><td><p>387</p></td><td><p>RecuperateAgencyFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>补差代理费</p></td><td></td></tr>
<tr><td><p>388</p></td><td><p>RedemptionSequence</p></td><td><p>C</p></td><td><p>1</p></td><td><p>指定赎回方式</p></td><td><p>0-先进先出 1-后进先出</p></td></tr>
<tr><td><p>389</p></td><td><p>BuyUpperAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申购金额上限</p></td><td></td></tr>
<tr><td><p>390</p></td><td><p>CovertInUpperAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金转换转入金额上限</p></td><td></td></tr>
<tr><td><p>391</p></td><td><p>PeriodSubUpperAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>定时定额申购金额上限</p></td><td></td></tr>
<tr><td><p>392</p></td><td><p>ChargeType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>收费类型</p></td><td></td></tr>
<tr><td><p>393</p></td><td><p>SpecifyRateFee</p></td><td><p>N</p></td><td><p>9（八位小数）</p></td><td><p>指定费率</p></td><td></td></tr>
<tr><td><p>394</p></td><td><p>SpecifyFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>指定费用</p></td><td></td></tr>
<tr><td><p>395</p></td><td><p>PeriodSubTimeUnit</p></td><td><p>C</p></td><td><p>1</p></td><td><p>定投周期单位</p></td><td></td></tr>
<tr><td><p>501</p></td><td><p>FundIncome</p></td><td><p>N</p></td><td><p>8(五位小数)</p></td><td><p>货币基金万份收益率</p></td><td></td></tr>
<tr><td><p>502</p></td><td><p>FundIncomeFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>货币基金万份收益正负</p></td><td><p>0-正  1-负</p></td></tr>
<tr><td><p>503</p></td><td><p>Yield</p></td><td><p>N</p></td><td><p>8(五位小数)</p></td><td><p>货币基金七日年收益</p></td><td></td></tr>
<tr><td><p>504</p></td><td><p>YieldFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>货币基金七日年收益正负</p></td><td><p>0-正  1-负</p></td></tr>
<tr><td><p>505</p></td><td><p>GuaranteedNAV</p></td><td><p>N</p></td><td><p>16(八位小数)</p></td><td><p>保本净值</p></td><td></td></tr>
<tr><td><p>506</p></td><td><p>HandleCharge</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>经手费</p></td><td></td></tr>
<tr><td><p>507</p></td><td><p>UndistributeMonetaryIncome</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>货币基金未付收益金额</p></td><td></td></tr>
<tr><td><p>508</p></td><td><p>GuaranteedAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>剩余保本金额</p></td><td></td></tr>
<tr><td><p>509</p></td><td><p>ExchangeFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>交易所标志</p></td><td><p>0-深圳场内  1-上海场内</p><p>2-场外 3-北京场内</p></td></tr>
<tr><td><p>510</p></td><td><p>UndistributeMonetaryIncomeFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>货币基金未付收益金额正负</p></td><td><p>0-正  1-负</p></td></tr>
<tr><td><p>511</p></td><td><p>Ref</p></td><td><p>C</p></td><td><p>10</p></td><td><p>券商用</p></td><td></td></tr>
<tr><td><p>512</p></td><td><p>Internet</p></td><td><p>C</p></td><td><p>1</p></td><td><p>INTERNET交易</p></td><td><p>0-取消，1-开通</p></td></tr>
<tr><td><p>521</p></td><td><p>ShareType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>份额类别</p></td><td><p>保留字段。0-前收费，1-后收费</p></td></tr>
<tr><td><p>522</p></td><td><p>Nationality</p></td><td><p>C</p></td><td><p>3</p></td><td><p>投资者国家或地区</p></td><td><p>采用ISO 3166两位字母</p></td></tr>
<tr><td><p>524</p></td><td><p>NetNo</p></td><td><p>C</p></td><td><p>9</p></td><td><p>操作（清算）网点编号</p></td><td></td></tr>
<tr><td><p>526</p></td><td><p>TargetShareType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>对方基金份额类别</p></td><td></td></tr>
<tr><td><p>527</p></td><td><p>SourceType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>份额原始来源</p></td><td><p>0-认购1-申购 2-定期定额申购3-分红</p></td></tr>
<tr><td><p>529</p></td><td><p>VastRedeemRatio</p></td><td><p>N</p></td><td><p>9(8位小数)</p></td><td><p>巨额赎回兑现比例</p></td><td></td></tr>
<tr><td><p>530</p></td><td><p>Broker</p></td><td><p>C</p></td><td><p>12</p></td><td><p>经纪人</p></td><td><p>客户所属的经纪人</p></td></tr>
<tr><td><p>532</p></td><td><p>ProtocalEndDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>协议截止日期</p></td><td></td></tr>
<tr><td><p>533</p></td><td><p>RationDate</p></td><td><p>N</p></td><td><p>5</p></td><td><p>定期定额的指定日期</p></td><td></td></tr>
<tr><td><p>535</p></td><td><p>FundDayIncomeFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>基金当日总收益正负</p></td><td></td></tr>
<tr><td><p>536</p></td><td><p>FundDayIncome</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>基金当日总收益</p></td><td></td></tr>
<tr><td><p>537</p></td><td><p>CustomerID</p></td><td><p>C</p></td><td><p>12</p></td><td><p>客户号</p></td><td></td></tr>
<tr><td><p>538</p></td><td><p>RationKind</p></td><td><p>C</p></td><td><p>3</p></td><td><p>定期定额品种代码</p></td><td></td></tr>
<tr><td><p>539</p></td><td><p>BelongFundAssetFare</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>归基金资产费</p></td><td></td></tr>
<tr><td><p>540</p></td><td><p>BackFare</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>后收手续费</p></td><td></td></tr>
<tr><td><p>541</p></td><td><p>RecuperateFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>补差费</p></td><td></td></tr>
<tr><td><p>542</p></td><td><p>ChangeFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>转换费</p></td><td></td></tr>
<tr><td><p>543</p></td><td><p>AchievementPay</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>业绩报酬</p></td><td></td></tr>
<tr><td><p>544</p></td><td><p>AchievementCompen</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>业绩补偿</p></td><td></td></tr>
<tr><td><p>549</p></td><td><p>OverAmount</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请超限金额</p></td><td></td></tr>
<tr><td><p>550</p></td><td><p>OverShares</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>申请超限份额</p></td><td></td></tr>
<tr><td><p>551</p></td><td><p>CapitalGainTax</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>红利所得税</p></td><td></td></tr>
<tr><td><p>552</p></td><td><p>CashDividendFee</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>现金分红手续费</p></td><td></td></tr>
<tr><td><p>553</p></td><td><p>ConfirmPayDate</p></td><td><p>C</p></td><td><p>8</p></td><td><p>确认支付日期</p></td><td></td></tr>
<tr><td><p>554</p></td><td><p>NetValueDate</p></td><td><p>C</p></td><td><p>8</p></td><td><p>净值日期</p></td><td></td></tr>
<tr><td><p>555</p></td><td><p>NetValueType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>净值类型</p></td><td><p>0-普通净值1-申购净值 2-赎回净值</p></td></tr>
<tr><td><p>556</p></td><td><p>FundYearIncomeRate</p></td><td><p>N</p></td><td><p>8(五位小数)</p></td><td><p>货币基金年收益率</p></td><td><p>最近一年来的收益率</p></td></tr>
<tr><td><p>557</p></td><td><p>FundYearIncomeRateFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>货币基金年收益率正负</p></td><td></td></tr>
<tr><td><p>558</p></td><td><p>BeginInterestDate</p></td><td><p>C</p></td><td><p>8</p></td><td><p>起息日期</p></td><td><p>转发LOF认购明细中起息日期</p></td></tr>
<tr><td><p>559</p></td><td><p>LofDataType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>LOF数据类别</p></td><td><p>转发LOF认购明细中数据类别</p></td></tr>
<tr><td><p>560</p></td><td><p>ManagerRealRatio</p></td><td><p>N</p></td><td><p>7(四位小数)</p></td><td><p>实际计算折扣</p></td><td></td></tr>
<tr><td><p>561</p></td><td><p>CostPrice</p></td><td><p>N</p></td><td><p>16(八位小数)</p></td><td><p>成本价</p></td><td><p>批量份额调整业务用</p></td></tr>
<tr><td><p>562</p></td><td><p>GeneralTASerialNO</p></td><td><p>C</p></td><td><p>20</p></td><td><p>总TA确认流水号</p></td><td></td></tr>
<tr><td><p>601</p></td><td><p>DrawBonusUnit</p></td><td><p>N</p></td><td><p>10</p></td><td><p>分红单位</p></td><td></td></tr>
<tr><td><p>602</p></td><td><p>FrozenSharesforReinvest</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>冻结再投资份额</p></td><td></td></tr>
<tr><td><p>603</p></td><td><p>SharesAdjustmentFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>份额强制调整标志</p></td><td><p>0-柜台业务1-管理人批量调整2-管理人普通调整3-ETF份额标准化4-货币基金收益结转5-基金分拆 6-确权 7-挂失换新号8-基金升降级9-净值调整 A-业绩报酬  B-业绩补偿 C-联名卡还款份额调整 D-基金展期份额调整  E-买卖  F-调账G-调整收益 H-跨市场转托管回冲 I-做市转入转出</p></td></tr>
<tr><td><p>604</p></td><td><p>PeriodicStatus</p></td><td><p>C</p></td><td><p>1</p></td><td><p>定期定额状态</p></td><td><p>0-允许定期定额业务</p><p>1-仅允许定投业务</p><p>2-仅允许定赎业务</p><p>3-禁止定期定额业务</p></td></tr>
<tr><td><p>605</p></td><td><p>TransferAgencyStatus</p></td><td><p>C</p></td><td><p>1</p></td><td><p>转托管状态</p></td><td><p>0-允许所有转托管</p><p>1-仅允许场外转托管</p><p>2-仅允许跨市场转托管</p><p>3-禁止所有转托管</p></td></tr>
<tr><td><p>606</p></td><td><p>TransactionAccountStatus</p></td><td><p>C</p></td><td><p>1</p></td><td><p>交易账户状态</p></td><td><p>0-正常，3-注销</p></td></tr>
<tr><td><p>607</p></td><td><p>RationNo</p></td><td><p>C</p></td><td><p>3</p></td><td><p>定期定额序号</p></td><td></td></tr>
<tr><td><p>608</p></td><td><p>AchievementPayFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>业绩报酬正负</p></td><td></td></tr>
<tr><td><p>609</p></td><td><p>IndiMaxPurchase</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>个人最大申购金额</p></td><td></td></tr>
<tr><td><p>610</p></td><td><p>InstMaxPurchase</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>法人最大申购金额</p></td><td></td></tr>
<tr><td><p>611</p></td><td><p>IndiDayMaxSumBuy</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>个人当日累计购买最大金额</p></td><td></td></tr>
<tr><td><p>612</p></td><td><p>InstDayMaxSumBuy</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>法人当日累计购买最大金额</p></td><td></td></tr>
<tr><td><p>613</p></td><td><p>IndiDayMaxSumRedeem</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>个人当日累计赎回最大份额</p></td><td></td></tr>
<tr><td><p>614</p></td><td><p>InstDayMaxSumRedeem</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>法人当日累计赎回最大份额</p></td><td></td></tr>
<tr><td><p>615</p></td><td><p>IndiMaxRedeem</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>个人最大赎回份额</p></td><td></td></tr>
<tr><td><p>616</p></td><td><p>InstMaxRedeem</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>法人最大赎回份额</p></td><td></td></tr>
<tr><td><p>617</p></td><td><p>TargetRegistrarCode</p></td><td><p>C</p></td><td><p>18</p></td><td><p>对方TA代码</p></td><td></td></tr>
<tr><td><p>618</p></td><td><p>AllowRedemptDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>可赎回日期</p></td><td></td></tr>
<tr><td><p>619</p></td><td><p>AddFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>增删标志</p></td><td></td></tr>
<tr><td><p>620</p></td><td><p>ContractType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>合同类型</p></td><td><p>1-电子签名合同 2-纸质合同</p></td></tr>
<tr><td><p>621</p></td><td><p>SerialNo</p></td><td><p>C</p></td><td><p>26</p></td><td><p>流水号</p></td><td></td></tr>
<tr><td><p>622</p></td><td><p>Version</p></td><td><p>C</p></td><td><p>8</p></td><td><p>版本号</p></td><td></td></tr>
<tr><td><p>623</p></td><td><p>SignType</p></td><td><p>C</p></td><td><p>1</p></td><td><p>签署类型</p></td><td></td></tr>
<tr><td><p>624</p></td><td><p>AcceptPlace</p></td><td><p>C</p></td><td><p>40</p></td><td><p>受理地点</p></td><td></td></tr>
<tr><td><p>625</p></td><td><p>Notes</p></td><td><p>C</p></td><td><p>64</p></td><td><p>附加信息</p></td><td></td></tr>
<tr><td><p>626</p></td><td><p>SignRiskNotice</p></td><td><p>C</p></td><td><p>1</p></td><td><p>已签署风险揭示书</p></td><td><p>0-未签署风险揭示书；</p><p>1-已签署电子风险揭示书；</p><p>2-已签署纸质风险揭示书。</p></td></tr>
<tr><td><p>627</p></td><td><p>RiskMatching</p></td><td><p>C</p></td><td><p>1</p></td><td><p>风险承受能力匹配情况</p></td><td><p>1-客户风险匹配；</p><p>2-客户风险不匹配且已签署风险责任承诺书。</p></td></tr>
<tr><td><p>628</p></td><td><p>CardNo</p></td><td><p>C</p></td><td><p>32</p></td><td><p>卡号</p></td><td></td></tr>
<tr><td><p>629</p></td><td><p>SecondStatus</p></td><td><p>C</p></td><td><p>1</p></td><td><p>第二用途状态</p></td><td></td></tr>
<tr><td><p>630</p></td><td><p>ThirdStatus</p></td><td><p>C</p></td><td><p>1</p></td><td><p>第三用途状态</p></td><td></td></tr>
<tr><td><p>631</p></td><td><p>SecondNotes</p></td><td><p>C</p></td><td><p>64</p></td><td><p>第二用途信息</p></td><td></td></tr>
<tr><td><p>632</p></td><td><p>ThirdNotes</p></td><td><p>C</p></td><td><p>64</p></td><td><p>第三用途信息</p></td><td></td></tr>
<tr><td><p>633</p></td><td><p>SecondDate</p></td><td><p>C</p></td><td><p>8</p></td><td><p>第二用途日期</p></td><td></td></tr>
<tr><td><p>634</p></td><td><p>ThirdDate</p></td><td><p>C</p></td><td><p>8</p></td><td><p>第三用途日期</p></td><td></td></tr>
<tr><td><p>635</p></td><td><p>ReservedField1</p></td><td><p>C</p></td><td><p>20</p></td><td><p>预留字段1</p></td><td></td></tr>
<tr><td><p>636</p></td><td><p>ReservedField2</p></td><td><p>C</p></td><td><p>20</p></td><td><p>预留字段2</p></td><td></td></tr>
<tr><td><p>637</p></td><td><p>ReservedField3</p></td><td><p>C</p></td><td><p>30</p></td><td><p>预留字段3</p></td><td></td></tr>
<tr><td><p>638</p></td><td><p>ReservedField4</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>预留字段4</p></td><td></td></tr>
<tr><td><p>639</p></td><td><p>ReservedField5</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>预留字段5</p></td><td></td></tr>
<tr><td><p>640</p></td><td><p>TAAccountID2</p></td><td><p>C</p></td><td><p>35</p></td><td><p>投资人基金帐号</p></td><td></td></tr>
<tr><td><p>641</p></td><td><p>FundCode2</p></td><td><p>C</p></td><td><p>12</p></td><td><p>基金代码</p></td><td></td></tr>
<tr><td><p>642</p></td><td><p>CodeOfTargetFund2</p></td><td><p>C</p></td><td><p>12</p></td><td><p>转换时的目标基金代码</p></td><td></td></tr>
<tr><td><p>643</p></td><td><p>Charge2</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>手续费</p></td><td></td></tr>
<tr><td><p>644</p></td><td><p>AgencyFee2</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>代理费</p></td><td></td></tr>
<tr><td><p>645</p></td><td><p>PayAmount</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>交收金额</p></td><td></td></tr>
<tr><td><p>646</p></td><td><p>FundManagerCode2</p></td><td><p>C</p></td><td><p>18</p></td><td><p>基金管理人</p></td><td></td></tr>
<tr><td><p>647</p></td><td><p>CustodianCode2</p></td><td><p>C</p></td><td><p>18</p></td><td><p>托管人代码</p></td><td></td></tr>
<tr><td><p>648</p></td><td><p>RegistrarCode2</p></td><td><p>C</p></td><td><p>18</p></td><td><p>注册登记人代码</p></td><td></td></tr>
<tr><td><p>649</p></td><td><p>RegRegionCode</p></td><td><p>C</p></td><td><p>2</p></td><td><p>注册地国家或地区代码</p></td><td><p>采用ISO 3166两位字母。</p><p>对个人表示身份证明文件的颁发国家或地区，对机构表示注册地国家或地区。</p></td></tr>
<tr><td><p>650</p></td><td><p>SaleRegionCode</p></td><td><p>C</p></td><td><p>2</p></td><td><p>销售地国家或地区代码</p></td><td><p>采用ISO 3166两位字母。</p></td></tr>
<tr><td><p>651</p></td><td><p>MainFundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>主基金代码</p></td><td></td></tr>
<tr><td><p>652</p></td><td><p>ClassFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>分级标识</p></td><td><p>0：非分级  1：优先劣后分级  2：优先顺序分级</p></td></tr>
<tr><td><p>653</p></td><td><p>PriorFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>优先劣后标识</p></td><td><p>0：劣后 1：优先 2:中间</p><p>优先劣后分级产品必填</p></td></tr>
<tr><td><p>654</p></td><td><p>FundEndDate</p></td><td><p>C</p></td><td><p>8</p></td><td><p>到期日</p></td><td></td></tr>
<tr><td><p>655</p></td><td><p>RelationUsage</p></td><td><p>C</p></td><td><p>2</p></td><td><p>关系用途</p></td><td></td></tr>
<tr><td><p>656</p></td><td><p>AccumulativePerDiv</p></td><td><p>N</p></td><td><p>16（两位小数）</p></td><td><p>累积单位分红</p></td><td></td></tr>
<tr><td><p>657</p></td><td><p>CapTermFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>资金交收终端标志</p></td><td></td></tr>
<tr><td><p>658</p></td><td><p>StockAccount</p></td><td><p>C</p></td><td><p>10</p></td><td><p>股票账户</p></td><td></td></tr>
<tr><td><p>659</p></td><td><p>TaxRatio</p></td><td><p>N</p></td><td><p>7四位小数)</p></td><td><p>计税比例</p></td><td></td></tr>
<tr><td><p>660</p></td><td><p>RatioDate</p></td><td><p>C</p></td><td><p>8</p></td><td><p>比例日期</p></td><td></td></tr>
<tr><td><p>661</p></td><td><p>DestinationCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>基金资金全部投向产品代码</p></td><td></td></tr>
<tr><td><p>662</p></td><td><p>PublicFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>公募标识</p></td><td><p>0:非公募1：公募</p></td></tr>
<tr><td><p>663</p></td><td><p>DistributorCode2</p></td><td><p>C</p></td><td><p>18</p></td><td><p>销售人代码2</p></td><td></td></tr>
<tr><td><p>664</p></td><td><p>InvestorType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>投资者类型</p></td><td><p>参照“325机构类型”字段</p></td></tr>
<tr><td><p>665</p></td><td><p>InvestorProCode</p></td><td><p>C</p></td><td><p>30</p></td><td><p>投资者产品代码</p></td><td><p>投资者为公募基金产品或基金业协会备案产品时必填，填写行业编码中心分配的编码或协会备案产品编码。</p></td></tr>
<tr><td><p>666</p></td><td><p>PriorSequence</p></td><td><p>A</p></td><td><p>2</p></td><td><p>分级优先顺序</p></td><td><p>填写两位数值用于区分不同的优先顺序，从01起开始分配，数字越小优先级越高。</p></td></tr>
<tr><td><p>667</p></td><td><p>TargetDistributorCode2</p></td><td><p>C</p></td><td><p>18</p></td><td><p>对方销售人代码2</p></td><td></td></tr>
<tr><td><p>668</p></td><td><p>LeverageMultiple</p></td><td><p>N</p></td><td><p>10(四位小数)</p></td><td><p>杠杆倍数</p></td><td></td></tr>
<tr><td><p>669</p></td><td><p>FormalFundCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>正式代码</p></td><td></td></tr>
<tr><td><p>670</p></td><td><p>InvestAdName</p></td><td><p>C</p></td><td><p>80</p></td><td><p>投资顾问名称</p></td><td></td></tr>
<tr><td><p>671</p></td><td><p>InvestAdBusCode</p></td><td><p>C</p></td><td><p>18</p></td><td><p>投资顾问社会信用代码</p></td><td></td></tr>
<tr><td><p>672</p></td><td><p>InvestAdManCode</p></td><td><p>C</p></td><td><p>18</p></td><td><p>投资顾问私募管理人编码</p></td><td></td></tr>
<tr><td><p>673</p></td><td><p>LeverageRate</p></td><td><p>N</p></td><td><p>16(四位小数)</p></td><td><p>杠杆率</p></td><td></td></tr>
<tr><td><p>674</p></td><td><p>SurveyMethod</p></td><td><p>C</p></td><td><p>1</p></td><td><p>调查规则</p></td><td></td></tr>
<tr><td><p>675</p></td><td><p>GetInvestCerFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>取得投资人声明标识</p></td><td></td></tr>
<tr><td><p>676</p></td><td><p>NonResiFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>非居民标识</p></td><td></td></tr>
<tr><td><p>677</p></td><td><p>ChineseName</p></td><td><p>C</p></td><td><p>100</p></td><td><p>中文姓名</p></td><td></td></tr>
<tr><td><p>678</p></td><td><p>EnglishFirstName2</p></td><td><p>C</p></td><td><p>100</p></td><td><p>英文名2</p></td><td></td></tr>
<tr><td><p>679</p></td><td><p>EnglishFamliyName2</p></td><td><p>C</p></td><td><p>100</p></td><td><p>英文姓2</p></td><td></td></tr>
<tr><td><p>680</p></td><td><p>EnglishName</p></td><td><p>C</p></td><td><p>200</p></td><td><p>英文全称</p></td><td></td></tr>
<tr><td><p>681</p></td><td><p>LivingCountry</p></td><td><p>C</p></td><td><p>3</p></td><td><p>现居国家或地区</p></td><td></td></tr>
<tr><td><p>682</p></td><td><p>LivingAddress</p></td><td><p>C</p></td><td><p>300</p></td><td><p>现居地址</p></td><td></td></tr>
<tr><td><p>683</p></td><td><p>LivingAddress2</p></td><td><p>C</p></td><td><p>300</p></td><td><p>现居地址2</p></td><td></td></tr>
<tr><td><p>684</p></td><td><p>LivingAddress3</p></td><td><p>C</p></td><td><p>300</p></td><td><p>现居地址3</p></td><td></td></tr>
<tr><td><p>685</p></td><td><p>LivingAddress4</p></td><td><p>C</p></td><td><p>300</p></td><td><p>现居地址4</p></td><td></td></tr>
<tr><td><p>686</p></td><td><p>BirthDate</p></td><td><p>C</p></td><td><p>8</p></td><td><p>出生日期</p></td><td></td></tr>
<tr><td><p>687</p></td><td><p>BirthCountry</p></td><td><p>C</p></td><td><p>3</p></td><td><p>出生国家或地区</p></td><td></td></tr>
<tr><td><p>688</p></td><td><p>BirthCountryEngName</p></td><td><p>C</p></td><td><p>200</p></td><td><p>出生国英文名称</p></td><td></td></tr>
<tr><td><p>689</p></td><td><p>BirthCity</p></td><td><p>C</p></td><td><p>200</p></td><td><p>出生城市</p></td><td></td></tr>
<tr><td><p>690</p></td><td><p>AddressType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>地址类型</p></td><td></td></tr>
<tr><td><p>691</p></td><td><p>TaxCountry</p></td><td><p>C</p></td><td><p>3</p></td><td><p>税收居民国</p></td><td></td></tr>
<tr><td><p>692</p></td><td><p>TaxID</p></td><td><p>C</p></td><td><p>200</p></td><td><p>纳税人识别号</p></td><td></td></tr>
<tr><td><p>693</p></td><td><p>PassiveNonFinFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>消极非金融机构标识</p></td><td></td></tr>
<tr><td><p>694</p></td><td><p>HaveNonResConFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>存在非居民控制人标识</p></td><td></td></tr>
<tr><td><p>695</p></td><td><p>ChineseName2</p></td><td><p>C</p></td><td><p>100</p></td><td><p>中文姓名2</p></td><td></td></tr>
<tr><td><p>696</p></td><td><p>EnglishFirstName3</p></td><td><p>C</p></td><td><p>100</p></td><td><p>英文名3</p></td><td></td></tr>
<tr><td><p>697</p></td><td><p>EnglishFamliyName3</p></td><td><p>C</p></td><td><p>100</p></td><td><p>英文姓3</p></td><td></td></tr>
<tr><td><p>698</p></td><td><p>ControllerType</p></td><td><p>C</p></td><td><p>6</p></td><td><p>控制人类型</p></td><td></td></tr>
<tr><td><p>699</p></td><td><p>ConNonResiFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>控制人非居民标识</p></td><td></td></tr>
<tr><td><p>700</p></td><td><p>ConShareRatio</p></td><td><p>N</p></td><td><p>7（四位小数）</p></td><td><p>控制人持股比例</p></td><td></td></tr>
<tr><td><p>701</p></td><td><p>LivingCountry2</p></td><td><p>C</p></td><td><p>3</p></td><td><p>现居国家或地区2</p></td><td></td></tr>
<tr><td><p>702</p></td><td><p>LivingAddress5</p></td><td><p>C</p></td><td><p>300</p></td><td><p>现居地址5</p></td><td></td></tr>
<tr><td><p>703</p></td><td><p>LivingAddress6</p></td><td><p>C</p></td><td><p>300</p></td><td><p>现居地址6</p></td><td></td></tr>
<tr><td><p>704</p></td><td><p>LivingAddress7</p></td><td><p>C</p></td><td><p>300</p></td><td><p>现居地址7</p></td><td></td></tr>
<tr><td><p>705</p></td><td><p>LivingAddress8</p></td><td><p>C</p></td><td><p>300</p></td><td><p>现居地址8</p></td><td></td></tr>
<tr><td><p>706</p></td><td><p>RegRegionCode2</p></td><td><p>C</p></td><td><p>2</p></td><td><p>国家或地区2</p></td><td></td></tr>
<tr><td><p>707</p></td><td><p>BirthDate2</p></td><td><p>C</p></td><td><p>8</p></td><td><p>出生日期2</p></td><td></td></tr>
<tr><td><p>708</p></td><td><p>BirthCountry2</p></td><td><p>C</p></td><td><p>3</p></td><td><p>出生国家或地区2</p></td><td></td></tr>
<tr><td><p>709</p></td><td><p>BirthCouEngName2</p></td><td><p>C</p></td><td><p>200</p></td><td><p>出生国英文名称2</p></td><td></td></tr>
<tr><td><p>710</p></td><td><p>BirthCity2</p></td><td><p>C</p></td><td><p>120</p></td><td><p>出生城市2</p></td><td></td></tr>
<tr><td><p>711</p></td><td><p>TaxCountry2</p></td><td><p>C</p></td><td><p>3</p></td><td><p>税收居民国2</p></td><td></td></tr>
<tr><td><p>712</p></td><td><p>TaxID2</p></td><td><p>C</p></td><td><p>200</p></td><td><p>纳税人识别号2</p></td><td></td></tr>
<tr><td><p>713</p></td><td><p>Specification2</p></td><td><p>C</p></td><td><p>60</p></td><td><p>摘要/说明2</p></td><td></td></tr>
<tr><td><p>714</p></td><td><p>ReservedField6</p></td><td><p>C</p></td><td><p>300</p></td><td><p>预留字段6</p></td><td></td></tr>
<tr><td><p>715</p></td><td><p>AuxCertType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>辅助身份证明文件类型</p></td><td><p>参考数据字典的“证件类型”字段</p></td></tr>
<tr><td><p>716</p></td><td><p>AuxCertCode</p></td><td><p>C</p></td><td><p>40</p></td><td><p>辅助身份证明文件号码</p></td><td></td></tr>
<tr><td><p>717</p></td><td><p>AuxCertValidDate</p></td><td><p>C</p></td><td><p>8</p></td><td><p>辅助身份证明文件有效日期</p></td><td></td></tr>
<tr><td><p>718</p></td><td><p>RecvAccountNum</p></td><td><p>C</p></td><td><p>40</p></td><td><p>收方账号</p></td><td></td></tr>
<tr><td><p>719</p></td><td><p>PayAccountNum</p></td><td><p>C</p></td><td><p>40</p></td><td><p>付方账号</p></td><td></td></tr>
<tr><td><p>720</p></td><td><p>SettleType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>交收类型</p></td><td><p>0：多边净额 1：双边净额</p><p>2：逐笔全额</p></td></tr>
<tr><td><p>721</p></td><td><p>ManageRange</p></td><td><p>C</p></td><td><p>2000</p></td><td><p>经营范围</p></td><td></td></tr>
<tr><td><p>722</p></td><td><p>RegCapital</p></td><td><p>N</p></td><td><p>20</p></td><td><p>注册资本</p></td><td></td></tr>
<tr><td><p>723</p></td><td><p>OrgNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>组织机构代码</p></td><td></td></tr>
<tr><td><p>724</p></td><td><p>TaxNo</p></td><td><p>C</p></td><td><p>20</p></td><td><p>税务登记证号码</p></td><td></td></tr>
<tr><td><p>725</p></td><td><p>InstRepr</p></td><td><p>C</p></td><td><p>300</p></td><td><p>法定代表人</p></td><td></td></tr>
<tr><td><p>726</p></td><td><p>Transactor</p></td><td><p>C</p></td><td><p>2000</p></td><td><p>经办人</p></td><td></td></tr>
<tr><td><p>727</p></td><td><p>BeneOwner</p></td><td><p>C</p></td><td><p>2000</p></td><td><p>受益所有人</p></td><td></td></tr>
<tr><td><p>728</p></td><td><p>AssetManager</p></td><td><p>C</p></td><td><p>300</p></td><td><p>资产管理人</p></td><td></td></tr>
<tr><td><p>729</p></td><td><p>OriPayDate</p></td><td><p>C</p></td><td><p>8</p></td><td><p>原交收日期</p></td><td></td></tr>
<tr><td><p>730</p></td><td><p>TransferReason</p></td><td><p>C</p></td><td><p>3</p></td><td><p>过户原因</p></td><td><p>0-继承，1-赠与，2-司法，3-其它，4-基金份额互换，5-份额转让，6-基金通撮合，A-做市转托管</p></td></tr>
<tr><td><p>731</p></td><td><p>LaunMoneyRiskRate</p></td><td><p>C</p></td><td><p>3</p></td><td><p>洗钱风险等级</p></td><td><p>1-低2-较低3-中等</p><p>4-较高5-高</p></td></tr>
<tr><td><p>732</p></td><td><p>IPAddress</p></td><td><p>C</p></td><td><p>40</p></td><td><p>IP地址</p></td><td><p>IPV4地址以“点分十进制”表示X:X:X:X的形式记录。</p><p>IPV6地址以“冒号分十六进制”表示n:n:n:n:n:n:n:n的形式记录，n表示四个十六位进制地址元素之一的十六进制值，可采用零压缩法来记录。</p></td></tr>
<tr><td><p>733</p></td><td><p>NewIncome</p></td><td><p>N</p></td><td><p>16(两位小数)</p></td><td><p>新增收益</p></td><td></td></tr>
<tr><td><p>734</p></td><td><p>NewIncomeFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>新增收益正负</p></td><td><p>0-正  1-负</p></td></tr>
<tr><td><p>735</p></td><td><p>MACAddress</p></td><td><p>C</p></td><td><p>20</p></td><td><p>MAC地址</p></td><td><p>MAC地址去掉地址中的“-”或“：”进行记录。</p></td></tr>
<tr><td><p>736</p></td><td><p>SpecialPersonFlag</p></td><td><p>C</p></td><td><p>3</p></td><td><p>特定自然人标识</p></td><td><p>0-否 1-外国政要2-外国政要的特定关系人  3-国际组织高管 4-国际组织高管的特定关系人  A-其他</p></td></tr>
<tr><td><p>737</p></td><td><p>RelatedPerson</p></td><td><p>C</p></td><td><p>500</p></td><td><p>关联人</p></td><td></td></tr>
<tr><td><p>738</p></td><td><p>CustodianName</p></td><td><p>C</p></td><td><p>100</p></td><td><p>托管人名称</p></td><td></td></tr>
<tr><td><p>739</p></td><td><p>IMEI</p></td><td><p>C</p></td><td><p>20</p></td><td><p>国际移动设备识别码</p></td><td></td></tr>
<tr><td><p>740</p></td><td><p>UUID</p></td><td><p>C</p></td><td><p>32</p></td><td><p>通用唯一识别码</p></td><td></td></tr>
<tr><td><p>741</p></td><td><p>RedeemCloseMode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>赎回封闭方式</p></td><td><p>0不封闭；1周期封闭；2封闭固定期限（买入后封闭）；3封闭固定期限（产品封闭）</p><p>周期封闭：比如短期理财产品。</p><p>买入后封闭：投资者某日买入的份额，经固定期限后方可赎回。</p><p>产品封闭：产品封闭一段时间后开放。</p></td></tr>
<tr><td><p>742</p></td><td><p>CloseLength</p></td><td><p>N</p></td><td><p>8</p></td><td><p>封闭期长度</p></td><td></td></tr>
<tr><td><p>743</p></td><td><p>CloseUnit</p></td><td><p>C</p></td><td><p>3</p></td><td><p>封闭期单位</p></td><td><p>0-日  1-周  2-月  3-季</p><p>4-半年 5-年</p></td></tr>
<tr><td><p>744</p></td><td><p>SideBagFlag</p></td><td><p>C</p></td><td><p>3</p></td><td><p>侧袋标志</p></td><td><p>0-否  1-是</p></td></tr>
<tr><td><p>745</p></td><td><p>NextTradeEndDate</p></td><td><p>A</p></td><td><p>8</p></td><td><p>下一开放期结束日</p></td><td></td></tr>
<tr><td><p>746</p></td><td><p>ReceCapAccType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>收方资金账户类型</p></td><td><p>1-投资者结算户 </p><p>2-做市商结算户</p></td></tr>
<tr><td><p>747</p></td><td><p>PayCapAccType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>付方资金账户类型</p></td><td><p>1-投资者结算户 </p><p>2-做市商结算户</p></td></tr>
<tr><td><p>748</p></td><td><p>NAVSendMode</p></td><td><p>C</p></td><td><p>3</p></td><td><p>净值发送模式</p></td><td><p>0- 普通</p><p>1-迟1个交易日</p><p>2-迟2个交易日</p><p>......</p><p>9-迟9个交易日</p><p>A-不固定</p><p>B-其它</p><p>注：普通基金T+1日发布T日净值。取值1-9分别表示推迟发布1-9个交易日。</p><p>比如QDII基金T日晚上无法估值，则属于迟发，若T+2日发布T日净值，比普通基金迟一天，则填写‘1’。 </p><p>注：定期开放的基金不属于迟发。</p></td></tr>
<tr><td><p>749</p></td><td><p>SideBagOriCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>侧袋原代码</p></td><td></td></tr>
<tr><td><p>750</p></td><td><p>InlandAgencyCode</p></td><td><p>C</p></td><td><p>18</p></td><td><p>内地代理人代码</p></td><td></td></tr>
<tr><td><p>751</p></td><td><p>FundStatus2</p></td><td><p>C</p></td><td><p>3</p></td><td><p>基金状态2</p></td><td><p>0-正常交易1-认购期 2-发行成功3-发行失败 8-基金终止</p></td></tr>
<tr><td><p>752</p></td><td><p>LastChangeDate</p></td><td><p>C</p></td><td><p>8</p></td><td><p>最后修改日期</p></td><td></td></tr>
<tr><td><p>753</p></td><td><p>OpenAccDate</p></td><td><p>C</p></td><td><p>8</p></td><td><p>开户日期</p></td><td></td></tr>
<tr><td><p>754</p></td><td><p>MarketFlag</p></td><td><p>C</p></td><td><p>1</p></td><td><p>市场标志</p></td><td></td></tr>
<tr><td><p>755</p></td><td><p>InvestAdviserCode</p></td><td><p>C</p></td><td><p>40</p></td><td><p>投顾机构代码</p></td><td></td></tr>
<tr><td><p>756</p></td><td><p>AccChar</p></td><td><p>C</p></td><td><p>30</p></td><td><p>账户特征值</p></td><td><p>从左往右，每个字符代表一种特征：</p><p>第1位：投顾账户</p><p>第2位：个人养老金基金专用交易账户</p><p>每位字符取1表示属于此分类，取0表示不属于。</p></td></tr>
<tr><td><p>757</p></td><td><p>ApprovalNum</p></td><td><p>C</p></td><td><p>100</p></td><td><p>批文号</p></td><td></td></tr>
<tr><td><p>758</p></td><td><p>BackFareCode</p></td><td><p>C</p></td><td><p>6</p></td><td><p>后收费代码</p></td><td></td></tr>
<tr><td><p>759</p></td><td><p>FundChar</p></td><td><p>C</p></td><td><p>80</p></td><td><p>基金特征值</p></td><td><p>从左往右，每个字符代表一种特征：</p><p>第1位：证券公司现金管理产品</p><p>第2位：QDII基金</p><p>第3位：证券公司大集合（参公集合资产管理计划）</p><p>第4位：个人养老金基金单设份额类别（指个人养老金可投资的基金代码）</p><p>第5位：内地互认基金用于向香港销售的代码</p><p>第6位：养老目标基金</p><p>第7位：REITs基金</p><p>第8位：MOM基金</p><p>第9位：香港互认基金用于向内地销售的代码</p><p>第10位：浮动净值货币基金</p><p>第11位-第80位：保留</p><p>每位字符取1表示该基金代码属于此分类，取0表示不属于。</p><p>举例：某养老目标基金有两个代码A和B，其中A用于个人养老金的投资，则A和B的第4位字符取值分别为1和0，第6位字符取值均为1；某内地互认基金有代码A和B，A用于向内地销售，B用于向香港销售，则A和B的第5位字符取值分别为0和1。</p></td></tr>
<tr><td><p>760</p></td><td><p>NonPubFundInvType</p></td><td><p>C</p></td><td><p>3</p></td><td><p>非公募产品投向分类</p></td><td><p>01-权益类 02-固收类 03-商品及金融衍生品类 04-混合类  99-其它</p></td></tr>
<tr><td><p>2418</p></td><td><p>Detail</p></td><td><p>C</p></td><td><p>200</p></td><td><p>详细信息</p></td><td></td></tr>
</table>

# 8.

# 9.

<table>
<tr><td></td><td></td><td></td></tr>
<tr><td></td><td></td><td></td></tr>
<tr><td></td><td></td><td></td></tr>
</table>
