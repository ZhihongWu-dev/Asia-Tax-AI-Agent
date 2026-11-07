# STATUS

Written by `tools/build.py` at every build; do not edit. The acceptance of one jurisdiction is `python database/tools/build.py --jur <code>` (数据库规范.md §5).

| What | Count |
|---|---|
| Documents | 285 |
| Clauses | 36522 |
| Clauses left out (superseded.csv) | 217 |
| Repealed-provision stubs left out | 50 |
| Parameters | 572 |
| Treaty rows | 55 |
| Absence records | 45 |
| Errors / warnings | 20 / 117 |
| Gaps: (jurisdiction, category) / (jurisdiction, subject, slot) / pairs without a treaty row / unresolved downloads | 6 / 36 / 0 / 2 |

## Documents

| id | jur | type | category | format | text | slicing | clauses | title |
|---|---|---|---|---|---|---|---|---|
| ae.cabinet116.2022.taxable-threshold.en | ae | regulation | 1;2 | pdf | ok | ae_article | 8 | Cabinet Decision 116 of 2022 on the Taxable Income Threshold |
| ae.cabinet142.2024.dmtt.en | ae | regulation | 1;3 | pdf | ocr | page | 74 | Cabinet Decision 142 of 2024: Top-up Tax on Multinational En |
| ae.cabinet49.2023.natural-persons.en | ae | regulation | 2 | pdf | ok | ae_article | 9 | Cabinet Decision 49 of 2023 on Businesses or Business Activi |
| ae.fta.corporate-tax-faq | ae | guidance | 1;3;4;5;6;9 | html | ok | whole | 1 | Federal Tax Authority Corporate Tax FAQ |
| ae.fta.corporate-tax-registration | ae | page | page_deadlines | html | ok | whole | 1 | Corporate Tax Registration |
| ae.fta.foreign-source-income | ae | guidance | 4;5;6 | pdf | ok | numbered_para | 10 | Corporate Tax Guide: Taxation of Foreign Source Income |
| ae.fta.general-corporate-tax | ae | guidance | 1;2;3;4;5;6;7;9;page_rates | pdf | ok | numbered_para | 12 | Corporate Tax – General |
| ae.fta.natural-persons-2023 | ae | guidance | 2;page_rates | pdf | ok | page | 45 | Corporate Tax Guide: Taxation of Natural Persons |
| ae.fta.tax-resident-certificate-2024 | ae | guidance | 6;8 | pdf | ok | page | 67 | Tax Resident and Tax Residency Certificate |
| ae.fta.withholding-faq | ae | guidance | 7 | html | ok | whole | 1 | Federal Tax Authority FAQ: UAE Corporate Tax withholding tax |
| ae.law.corporate-tax.fta2022.en | ae | law | 1;4;9 | pdf | ok | ae_article | 330 | Taxation of Corporations and Businesses |
| ae.law.corporate-tax.legislation1582.en | ae | law | 1;4;9 | pdf | ok | ae_article | 323 | Federal Decree-Law No. (47) of 2022 On Corporate and Busines |
| ae.law.corporate-tax.mof2022.en | ae | law | 1;4;9 | pdf | ok | ae_article | 332 | Federal Decree-Law No. 47 of 2022 on the Taxation of Corpora |
| ae.mof.dta-index | ae | page | page_treaties | pdf | ok | page | 6 | Avoidance of Double Taxation Agreements |
| ae.mof.top-up-tax | ae | page | 3 | html | ok | whole | 1 | Top-up Tax |
| cn.cs.2009-125 | cn | guidance | 1 | html | ok | cn_item | 16 | 财政部 国家税务总局关于企业境外所得税收抵免有关问题的通知 |
| cn.cs.2009-59 | cn | guidance | 9 | html | ok | cn_item | 13 | 财政部 国家税务总局关于企业重组业务企业所得税处理若干问题的通知 |
| cn.cs.2009-60 | cn | guidance | 9 | html | ok | cn_item | 6 | 财政部 国家税务总局关于企业清算业务企业所得税处理若干问题的通知 |
| cn.cs.2017-84 | cn | guidance | 1 | html | ok | cn_item | 4 | 财政部 税务总局关于完善企业境外所得税收抵免政策问题的通知 |
| cn.cs.2019-34 | cn | guidance | 6 | html | ok | cn_item | 3 | 财政部 税务总局关于在中国境内无住所的个人居住时间判定标准的公告 |
| cn.cs.2020-03 | cn | guidance | 2 | html | ok | cn_item | 14 | 财政部 税务总局关于境外所得有关个人所得税政策的公告 |
| cn.cs.2026-27 | cn | guidance | 2 | html | ok | cn_item | 3 | 关于外籍个人股息红利个人所得税政策有关事项的公告（财政部 税务总局公告2026年第27号） |
| cn.gsf.2009-02 | cn | guidance | 3;4 | html | ok | cn_article | 118 | 国家税务总局关于印发《特别纳税调整实施办法（试行）》的通知 |
| cn.gsf.2009-82 | cn | guidance | 6 | html | ok | cn_item | 9 | 国家税务总局关于境外注册中资控股企业依据实际管理机构标准认定为居民企业有关问题的通知 |
| cn.gsh.2009-37 | cn | guidance | 3 | html | ok | whole | 1 | 国家税务总局关于简化判定中国居民股东控制外国企业所在国实际税负的通知 |
| cn.law.eit | cn | law | 1;3;4;9 | html | ok | cn_article | 60 | 中华人民共和国企业所得税法 |
| cn.law.iit | cn | law | 2;3;4 | html | ok | cn_article | 22 | 中华人民共和国个人所得税法 |
| cn.law.stamp | cn | law | 9 | html | ok | cn_article | 20 | 中华人民共和国印花税法 |
| cn.law.stamp.a01 | cn | attachment | 9 | pdf | ok | page | 7 | 中华人民共和国印花税法（含印花税税目税率表） |
| cn.law.tca | cn | law | 10 | html | ok | cn_article | 94 | 中华人民共和国税收征收管理法 |
| cn.order.32 | cn | regulation | 4 | html | ok | cn_article | 22 | 一般反避税管理办法（试行） |
| cn.reg.eit | cn | regulation | 1;3;4;9 | html | ok | cn_article | 132 | 中华人民共和国企业所得税法实施条例 |
| cn.reg.iit | cn | regulation | 2 | html | ok | cn_article | 36 | 中华人民共和国个人所得税法实施条例 |
| cn.sta.2008-112 | cn | guidance | page_rates | html | ok | cn_item | 3 | 国家税务总局关于下发协定股息税率情况一览表的通知 |
| cn.sta.2009-81 | cn | guidance | 1 | html | ok | cn_item | 6 | 国家税务总局关于执行税收协定股息条款有关问题的通知（国税函〔2009〕81号） |
| cn.sta.2014-09 | cn | guidance | 6 | html | ok | cn_item | 5 | 国家税务总局关于依据实际管理机构标准实施居民企业认定有关问题的公告 |
| cn.sta.2014-67 | cn | guidance | 9 | html | ok | cn_article | 31 | 股权转让所得个人所得税管理办法（试行）（国家税务总局公告2014年第67号） |
| cn.sta.2015-07 | cn | guidance | 9 | html | ok | cn_item | 19 | 国家税务总局关于非居民企业间接转让财产企业所得税若干问题的公告 |
| cn.sta.2017-37 | cn | guidance | 9 | html | ok | cn_item | 17 | 国家税务总局关于非居民企业所得税源泉扣缴有关问题的公告 |
| cn.sta.2018-09 | cn | guidance | 5 | html | ok | cn_item | 12 | 国家税务总局关于税收协定中“受益所有人”有关问题的公告 |
| cn.sta.2018-09.interp | cn | guidance | 11 | html | ok | cn_item | 3 | 关于《国家税务总局关于税收协定中“受益所有人”有关问题的公告》的解读 |
| cn.sta.2019-35 | cn | guidance | 7 | html | ok | cn_article | 25 | 国家税务总局关于发布《非居民纳税人享受协定待遇管理办法》的公告 |
| cn.sta.2019-35.a01 | cn | attachment | 7 | xls | ok | whole | 1 | 非居民纳税人享受协定待遇信息报告表.xls |
| cn.sta.2025-04 | cn | guidance | 8 | html | ok | cn_item | 8 | 国家税务总局关于《中国税收居民身份证明》有关事项的公告 |
| cn.sta.2025-04.a01 | cn | attachment | 8 | pdf | ok | page | 1 | 中国税收居民身份证明.pdf |
| cn.sta.2025-04.a02 | cn | attachment | 8 | pdf | ok | page | 6 | 《中国税收居民身份证明》申请表.pdf |
| cn.sta.ssty | cn | page | page_treaties | html | ok | html_section | 7 | 税收条约 |
| hk.cap112 | hk | law | 1;2;4;9;10 | rtf | ok | hk_section | 643 | Inland Revenue Ordinance (Cap. 112) |
| hk.cap117 | hk | law | 9 | rtf | ok | hk_section | 196 | Stamp Duty Ordinance (Cap. 117) |
| hk.dipn.44 | hk | guidance | 5 | pdf | ok | numbered_para | 161 | DIPN 44 (Revised): Arrangement between the Mainland of China |
| hk.form.ir1313a | hk | form | 8 | pdf | ok | page | 5 | IR1313A Application for Certificate of Resident Status (Comp |
| hk.form.ir1313b | hk | form | 8 | pdf | ok | page | 4 | IR1313B Application for Certificate of Resident Status (Comp |
| hk.form.ir1314a | hk | form | 8 | pdf | ok | page | 2 | IR1314A Application for Certificate of Resident Status (Indi |
| hk.form.ir1314b | hk | form | 8 | pdf | ok | page | 2 | IR1314B Application for Certificate of Resident Status (Indi |
| hk.ird.ar72 | hk | guidance | 11 | html | ok | whole | 1 | IRD Advance Ruling Case No. 72 (foreign-sourced dividends: r |
| hk.ird.cor | hk | guidance | 6;8 | html | ok | html_section | 7 | IRD: Certificate of Resident Status |
| hk.ird.cor.faq | hk | guidance | 6;8 | html | ok | html_faq | 26 | IRD FAQ: Certificate of Resident Status |
| hk.ird.dta-list | hk | page | page_treaties | html | ok | whole | 1 | IRD: Comprehensive Double Taxation Agreements concluded |
| hk.ird.dta-rates | hk | page | page_rates | html | ok | whole | 1 | IRD: Tax Rates for Dividends, Interest, Royalties and Techni |
| id.dgt.article23 | id | page | 1;page_deadlines | html | ok | whole | 1 | Article 23 Income Tax |
| id.dgt.article26 | id | page | 1;7;page_deadlines | html | ok | whole | 1 | Income Tax - Article 26 (Income Tax for Foreign Taxpayers) |
| id.dgt.ease-taxation | id | page | 1;4;page_rates | html | ok | html_section | 7 | Ease of Doing Business in Taxation Cluster |
| id.dgt.individual-calculation | id | page | 2 | html | ok | html_section | 7 | Income Tax Calculation Mechanism Individual |
| id.dgt.residence-registration | id | regulation | 6 | html | ok | id_pasal | 465 | Petunjuk Pelaksanaan Administrasi Nomor Pokok Wajib Pajak, P |
| id.dgt.skd-spdn | id | guidance | 8 | html | ok | html_section | 3 | Surat Keterangan Domisili Subjek Pajak Dalam Negeri |
| id.dgt.treaty-index | id | page | page_treaties | html | ok | whole | 1 | Tax Treaty |
| id.per25-2018.treaty-procedure | id | regulation | 5;7 | pdf | ok | page | 17 | Regulation of the Director General of Taxes Number PER-25/PJ |
| id.tax-law-compilation-2022 | id | law | 1;2;3;4;9 | pdf | ok | page | 352 | Compilation Into Single Document Of Taxation Laws |
| in.itd.act2025-scope | in | guidance | 1;2 | html | ok | html_section | 40 | Objective and scope of the New Act |
| in.itd.beneficial-owner-guide-2026 | in | guidance | 5 | pdf | ok | page | 4 | Step by Step Guide: Schedule FA and Schedule FSI |
| in.itd.domestic-company-2026 | in | guidance | 1 | html | ok | html_section | 4 | Domestic Company for AY 2026-27 |
| in.itd.dtaa-directory.20261031 | in | page | page_treaties | html | ok | whole | 1 | Treaties With Other Countries |
| in.itd.foreign-assets-2026 | in | guidance | 2;6 | pdf | ocr | page | 4 | Who should Disclose Foreign Asset/Income? |
| in.itd.foreign-income-guide.2018 | in | guidance | 1;2;6 | pdf | ok | numbered_para | 23 | Tax Treatment of Foreign Income of Persons Resident in India |
| in.itd.form15ca | in | form | 1 | html | ok | html_section | 7 | Form 15CA FAQs |
| in.itd.form41-dtaa | in | guidance | 7 | html | ok | html_section | 8 | Form 41 User Manual |
| in.itd.form42-trc | in | guidance | 8 | html | ok | html_section | 6 | Form 42 User Manual |
| in.itd.form67 | in | form | 1 | html | ok | html_section | 7 | Form 67 User Manual |
| in.itd.forms-transition2026 | in | guidance | 7 | html | ok | html_section | 39 | Income Tax Forms FAQs: transition to the Income-tax Act 2025 |
| in.itd.individual-rates-2026 | in | guidance | 2;page_rates | html | ok | html_section | 20 | Individual having Income from Business / Profession for AY 2 |
| in.itd.nonresident-faq | in | guidance | 6 | html | ok | html_section | 28 | Non Resident FAQs |
| in.itd.tax-calendar | in | page | page_deadlines | html | ok | html_section | 9 | Income Tax Department Tax Calendar |
| in.itd.tds-transition2026 | in | guidance | 1;7 | html | ok | html_section | 30 | Tax Payments FAQ: Income-tax Act 2025 transition |
| in.law.finance2026.gazette.en | in | law | 1;3 | pdf | ok | in_section | 213 | Finance Act 2026 (No. 4 of 2026): official Gazette |
| in.law.ita2025.fa2026.en | in | law | 1;2;3;4;9 | pdf | ok | in_section | 2807 | INCOME-TAX ACT, 2025 [AS AMENDED BY FINANCE ACT, 2026] |
| in.rules2026 | in | regulation | 4;7;9 | pdf | ok | in_section | 1574 | Income-tax Rules, 2026 |
| intl.mli.notification-35-7b.hk.en | intl | treaty |  | pdf | ok | page | 4 | Hong Kong SAR (submitted by China): notifications under MLI  |
| intl.mli.positions.cn.en | intl | treaty |  | pdf | ok | page | 37 | The Full List of the Final Reservations and Notifications of |
| intl.mli.positions.my.2022.en | intl | treaty |  | pdf | ok | page | 47 | Malaysia: Status of List of Reservations and Notifications |
| intl.mli.positions.th.en | intl | treaty |  | pdf | ok | page | 33 | Kingdom of Thailand: MLI reservations and notifications upon |
| intl.mli.positions.vn.en | intl | treaty |  | pdf | ok | page | 44 | Socialist Republic of Viet Nam: MLI reservations and notific |
| intl.oecd.mli.en | intl | treaty |  | pdf | ok | en_article | 214 | Multilateral Convention to Implement Tax Treaty Related Meas |
| intl.oecd.mli.parties.20260915.en | intl | treaty |  | pdf | ok | page | 6 | Signatories and Parties to the Multilateral Convention to Im |
| intl.oecd.mtc2017.full | intl | guidance | 11 | pdf | ok | numbered_para | 217 | OECD Model Tax Convention on Income and on Capital 2017 (Ful |
| jp.cta | jp | law | 1;4;9 | xml | ok | jp_article | 1128 | 法人税法（昭和40年法律第34号） |
| jp.cta.order | jp | law | 1;3 | xml | ok | jp_article | 1882 | 法人税法施行令（昭和40年政令第97号） |
| jp.gta | jp | law | 10 | xml | ok | jp_article | 719 | 国税通則法（昭和37年法律第66号） |
| jp.ita | jp | law | 1;2;9 | xml | ok | jp_article | 1007 | 所得税法（昭和40年法律第33号） |
| jp.ita.order | jp | law | 9 | xml | ok | jp_article | 1439 | 所得税法施行令（昭和40年政令第96号） |
| jp.mof.treaty-list | jp | page | page_treaties | html | ok | whole | 1 | 我が国の租税条約等の一覧 |
| jp.nta.2505 | jp | page | page_deadlines | html | ok | html_section | 10 | No.2505 源泉所得税及び復興特別所得税の納付期限と納期の特例 |
| jp.nta.2884 | jp | page | page_rates | html | ok | html_section | 11 | No.2884 非居住者等に対する源泉徴収・源泉徴収の税率 |
| jp.nta.2888 | jp | guidance | 7 | html | ok | html_section | 8 | No.2888 租税条約に関する届出書の提出（源泉徴収関係） |
| jp.nta.9205 | jp | guidance | 10 | html | ok | html_section | 10 | No.9205 延滞税について（国税庁タックスアンサー） |
| jp.nta.9210 | jp | guidance | 8 | html | ok | html_section | 8 | No.9210 居住者証明書の請求 |
| jp.nta.entai_wariai | jp | page | 10 | html | ok | whole | 1 | 延滞税の割合（国税庁） |
| jp.nta.joyaku.form1 | jp | guidance | 7 | html | ok | html_section | 10 | A3-1 租税条約に関する届出（配当に対する所得税及び復興特別所得税の軽減・免除）［様式1］ |
| jp.nta.tsutatsu.cta.13-2-1 | jp | guidance | 1 | html | ok | jp_tsutatsu | 11 | 法人税基本通達 第13章の2 第1節 外貨建取引に係る会計処理等（13の2－1－1〜） |
| jp.nta.tsutatsu.cta.9-1-3 | jp | guidance | 9 | html | ok | jp_tsutatsu | 11 | 法人税基本通達 第9章 第1節 第3款 有価証券の評価損（9－1－13、9－1－14 市場有価証券等以外の株式の価額） |
| jp.nta.tsutatsu.ita.02 | jp | guidance | 6 | html | ok | html_section | 6 | 所得税基本通達 法第2条《定義》関係（住所の意義ほか） |
| jp.recon | jp | law | 1;2 | xml | ok | jp_article | 303 | 東日本大震災からの復興のための施策を実施するために必要な財源の確保に関する特別措置法（平成23年法律第117号） |
| jp.sma | jp | law | 2;3;9 | xml | ok | jp_article | 3788 | 租税特別措置法（昭和32年法律第26号） |
| kr.corporate-tax-act.20260701.ko | kr | law | 1;3;4;6;9 | pdf | ok | kr_pdf_article | 823 | 법인세법 |
| kr.income-tax-act.20260701.ko | kr | law | 2;3;4;6;9 | pdf | ok | kr_pdf_article | 1148 | 소득세법 |
| kr.itca.enforcement-decree | kr | regulation | 3;4 | pdf | ok | page | 163 | ENFORCEMENT DECREE OF THE ADJUSTMENT OF INTERNATIONAL TAXES  |
| kr.nts.corporate-rate-2026 | kr | guidance | 1;page_rates | html | ok | html_section | 3 | 법인세 세율 (2026년 이후) |
| kr.nts.corporate-tax-overview | kr | guidance | 1 | html | ok | html_section | 7 | 법인세 개요 |
| kr.nts.filing-returns | kr | page | page_deadlines | html | ok | html_section | 3 | Filing returns |
| kr.nts.forms | kr | page | 8 | html | ok | html_section | 8 | Application Forms and English Certificates |
| kr.nts.global-income-faq | kr | guidance | 2 | html | ok | whole | 1 | Global income tax guidance |
| kr.nts.nonresident-wht | kr | guidance | 1 | html | ok | html_section | 3 | 비거주자 원천징수 |
| kr.nts.nonresident-wht-agent | kr | guidance | 1 | html | ok | html_section | 3 | 원천징수의무자 |
| kr.nts.nonresident-wht-rate | kr | guidance | 1 | html | ok | html_section | 3 | 원천징수세율 |
| kr.nts.tax-treaty-application | kr | form | 7 | pdf | ok | page | 13 | Application for Non-Taxation and Tax Exemption under the Tax |
| kr.nts.tax-treaty-index | kr | page | page_treaties | html | ok | whole | 1 | Tax Treaty |
| my.finance-act862.2024 | my | law | 1;2;8 | pdf | ok | my_section | 50 | Finance Act 2024 (Act 862) |
| my.hasil.be2025.explanatory | my | guidance | 1;2;8 | pdf | ok | page | 36 | HASiL Form BE explanatory notes for Year of Assessment 2025 |
| my.hasil.dta-index | my | page | page_treaties | html | ok | whole | 1 | PPPDK Menyeluruh |
| my.hasil.e-residence | my | guidance | 6;7;8 | html | ok | html_section | 8 | Sijil Taraf Mastautin / e-Residence |
| my.hasil.foreign-income-2024 | my | guidance | 1 | pdf | ok | numbered_para | 21 | Guidelines on Tax Treatment in Relation to Income Received f |
| my.hasil.wht | my | page | page_deadlines | html | ok | html_section | 3 | Cukai Pegangan |
| my.hasil.wht-rates | my | page | page_rates | html | ok | whole | 1 | Kadar Cukai Pegangan PPPDK |
| my.ita1967 | my | law | 1;2;4;9 | pdf | ok | my_section | 2355 | Income Tax Act 1967 (Act 53) |
| my.ita1967.updated2026.en | my | law | 1;2;4;8;9 | pdf | ok | my_section | 2387 | Income Tax Act 1967 (Act 53), online updated text as at 1 Ja |
| my.pua148.2025.dividend-income | my | regulation | 1;2 | pdf | ok | my_section | 18 | Income Tax (Determination of Chargeable Income of an Individ |
| my.pua157.2024.foreign-dividends-amendment | my | regulation | 1;2 | pdf | ok | my_section | 12 | Income Tax (Exemption) (No. 6) Order 2022 (Amendment) Order  |
| my.pua235.2022.foreign-dividends | my | regulation | 1;2 | pdf | ok | my_section | 24 | Income Tax (Exemption) (No. 6) Order 2022, P.U.(A)235/2022 |
| my.pua451.2024.individual-fsi-extension | my | regulation | 2 | pdf | ok | my_section | 8 | Income Tax (Exemption) (No. 5) Order 2022 (Amendment) Order  |
| sg.iras.cor | sg | guidance | 6;8 | html | ok | html_section | 6 | IRAS: Tax residency of a company / Certificate of Residence |
| sg.iras.cor.apply | sg | guidance | 8 | html | ok | html_section | 12 | IRAS: Applying for a Certificate of Residence / Tax Reclaim  |
| sg.iras.dta-list | sg | page | page_treaties | html | ok | whole | 1 | IRAS: List of DTAs, Limited DTAs and EOI Arrangements |
| sg.iras.etax.dta | sg | guidance | 11 | pdf | ok | numbered_para | 129 | IRAS e-Tax Guide: Avoidance of Double Taxation Agreements (D |
| sg.iras.etax.fsi | sg | guidance | 1 | pdf | ok | numbered_para | 30 | IRAS e-Tax Guide: Tax Exemption for Foreign-Sourced Income ( |
| sg.iras.stamp.shares | sg | guidance | 9 | html | ok | html_section | 8 | IRAS: Stamp Duty for Shares - Buying or Acquiring Shares |
| sg.iras.wht-rates | sg | page | page_rates | html | ok | whole | 1 | IRAS: Types of payment and withholding tax rates |
| sg.ita1947 | sg | law | 1;2;4;9;10 | html | ok | sso_section | 358 | Income Tax Act 1947 |
| th.mof.fx.2548 | th | guidance | 1 | html | ok | th_clause | 12 | ประกาศกระทรวงการคลัง เรื่อง อัตราแลกเปลี่ยนเงินตราต่างประเทศ |
| th.rc1.th | th | law | 1 | html | ok | th_section | 21 | ประมวลรัษฎากร ลักษณะ 1 ข้อความเบื้องต้น มาตรา 5-13 |
| th.rc2.th | th | law | 10 | html | ok | th_section | 23 | ประมวลรัษฎากร หมวด 2 วิธีการเกี่ยวแก่ภาษีอากรประเมิน มาตรา 1 |
| th.rc3.rates.th | th | law | 1 | html | ok | whole | 1 | ประมวลรัษฎากร บัญชีอัตราภาษีเงินได้ (ท้ายหมวด 3) |
| th.rc3a.en | th | law | 1;2;9 | html | ok | th_section | 120 | Revenue Code, Chapter 3 Income Tax, Sections 38-64 (English  |
| th.rc3a.th | th | law | 1;2;9 | html | ok | th_section | 128 | ประมวลรัษฎากร หมวด 3 ภาษีเงินได้ มาตรา 38-64 |
| th.rc3b.en | th | law | 1;9 | html | ok | th_section | 75 | Revenue Code, Chapter 3 Income Tax, Sections 65-76 (English  |
| th.rc3b.th | th | law | 1;9 | html | ok | th_section | 90 | ประมวลรัษฎากร หมวด 3 ภาษีเงินได้ มาตรา 65-76 |
| th.rc6.stamp.th | th | law | 9 | html | ok | whole | 1 | ประมวลรัษฎากร บัญชีอัตราอากรแสตมป์ (ท้ายหมวด 6) |
| th.rd.cor-company | th | guidance | 8 | html | ok | whole | 1 | Certificate of Residence (Company) |
| th.rd.cor-individual | th | guidance | 8 | html | ok | whole | 1 | Certificate of Residence (Individual Taxpayer) |
| th.rd.dta-list | th | page | page_treaties | html | ok | whole | 1 | Double Tax Agreement (DTA) |
| th.rd.foreign-company | th | page | page_rates;page_deadlines | html | ok | whole | 1 | Income Tax Guide for Foreign Company |
| th.rd.p132-2548 | th | guidance | 1 | html | ok | th_clause | 37 | คำสั่งกรมสรรพากร ที่ ป.132/2548 (การคำนวณเงินตราต่างประเทศเป |
| th.rd.ruling.0811-6620 | th | guidance | 11 | html | ok | whole | 1 | หนังสือตอบข้อหารือ กค 0811/6620 (เงินเพิ่มตามมาตรา 27) |
| th.rd10.en | th | regulation | 1 | pdf | ok | th_section | 61 | Royal Decree issued under the Revenue Code Governing Exempti |
| th.rd442.th | th | regulation | 1 | html | ok | th_section | 7 | พระราชกฤษฎีกาออกตามความในประมวลรัษฎากร ว่าด้วยการยกเว้นรัษฎา |
| treaty.ae-cn.1993.en | ae-cn | treaty |  | pdf | ok | en_article | 118 | Agreement between China and the United Arab Emirates for the |
| treaty.ae-cn.1993.mli.en | ae-cn | treaty |  | pdf | ok | en_article | 123 | Synthesised text of the MLI and the China–United Arab Emirat |
| treaty.ae-hk.2014.en | ae-hk | treaty |  | pdf | ok | page | 1 | Agreement between Hong Kong and the United Arab Emirates for |
| treaty.ae-hk.2014.mli.en | ae-hk | treaty |  | pdf | ok | en_article | 118 | Synthesised text of the MLI and the Hong Kong–United Arab Em |
| treaty.ae-id.2019.en | ae-id | treaty |  | pdf | ocr | en_article | 147 | Agreement between Indonesia and the United Arab Emirates for |
| treaty.ae-in.1992.mli.en | ae-in | treaty |  | pdf | scanned_or_empty | page | 0 | India–United Arab Emirates Double Taxation Agreement |
| treaty.ae-in.1992.p1.en | ae-in | treaty |  | pdf | ok | en_article | 6 | First Protocol to the India–United Arab Emirates Double Taxa |
| treaty.ae-in.1992.p2.en | ae-in | treaty |  | pdf | ocr | page | 4 | Second Protocol to the India–United Arab Emirates Double Tax |
| treaty.ae-jp.2013.convention.mof.en | ae-jp | treaty |  | pdf | ok | en_article | 126 | CONVENTION BETWEEN JAPAN AND THE UNITED ARAB EMIRATES FOR TH |
| treaty.ae-jp.2013.mli.en | ae-jp | treaty |  | htm | ok | whole | 1 | Application of the MLI to the Tax Treaty between Japan and t |
| treaty.ae-jp.2013.summary.en | ae-jp | treaty |  | htm | ok | whole | 1 | Key Points of the Tax Convention with the United Arab Emirat |
| treaty.ae-kr.2019.en | ae-kr | treaty |  | html | ok | en_article | 136 | Convention between the Republic of Korea and the United Arab |
| treaty.ae-my.1995.en | ae-my | treaty |  | pdf | ocr | en_article | 117 | United Arab Emirates–Malaysia Double Taxation Agreement |
| treaty.ae-sg.1995.mli.en | ae-sg | treaty |  | pdf | ok | en_article | 171 | Singapore–United Arab Emirates Double Taxation Agreement, as |
| treaty.ae-th.2000.en | ae-th | treaty |  | pdf | ocr | en_article | 119 | Agreement between the Kingdom of Thailand and the United Ara |
| treaty.ae-vn.2009.en | ae-vn | treaty |  | pdf | ok | en_article | 124 | Agreement between the United Arab Emirates and the Socialist |
| treaty.cn-hk.2006.p2.zh | cn-hk | treaty |  | pdf | ok | cn_article | 6 | 内地和香港特别行政区关于对所得避免双重征税和防止偷漏税的安排第二议定书 |
| treaty.cn-hk.2006.p3.zh | cn-hk | treaty |  | pdf | ok | page | 3 | 《内地和香港特别行政区关于对所得避免双重征税和防止偷漏税的安排》第三议定书 |
| treaty.cn-hk.2006.p4.zh | cn-hk | treaty |  | pdf | ok | cn_article | 6 | 《内地和香港特别行政区关于对所得避免双重征税和防止偷漏税的安排》第四议定书 |
| treaty.cn-hk.2006.p5.zh | cn-hk | treaty |  | pdf | ok | cn_article | 14 | 《内地和香港特别行政区关于对所得避免双重征税和防止偷漏税的安排》第五议定书 |
| treaty.cn-hk.2006.zh | cn-hk | treaty |  | pdf | ok | cn_article | 116 | 内地和香港特别行政区关于对所得避免双重征税和防止偷漏税的安排（含第一议定书） |
| treaty.cn-id.2001.en | cn-id | treaty |  | pdf | ok | en_article | 115 | Agreement between China and Indonesia for the Avoidance of D |
| treaty.cn-id.2001.mli.en | cn-id | treaty |  | pdf | ok | en_article | 120 | Synthesised text of the MLI and the China-Indonesia DTA |
| treaty.cn-id.2001.mou.en | cn-id | treaty |  | pdf | ok | page | 1 | Memorandum of Understanding on the Agreement between China a |
| treaty.cn-id.2001.p1.en | cn-id | treaty |  | pdf | ok | page | 1 | Protocol to the Agreement between China and Indonesia |
| treaty.cn-in.1994.en | cn-in | treaty |  | pdf | ok | en_article | 121 | Agreement between China and India for the Avoidance of Doubl |
| treaty.cn-in.1994.p1.en | cn-in | treaty |  | pdf | ok | page | 1 | Protocol to the Agreement between China and India |
| treaty.cn-in.1994.p2.en | cn-in | treaty |  | pdf | ok | en_article | 35 | Protocol amending the Agreement between China and India (201 |
| treaty.cn-jp.1983.en | cn-jp | treaty |  | pdf | ok | en_article | 114 | Agreement between China and Japan for the Avoidance of Doubl |
| treaty.cn-jp.1983.mli.en | cn-jp | treaty |  | pdf | ok | en_article | 117 | Synthesised text of the MLI and the China-Japan DTA |
| treaty.cn-jp.1983.notes.en | cn-jp | treaty |  | pdf | ok | page | 6 | Exchange of Notes (China-Japan) |
| treaty.cn-jp.1983.p1.en | cn-jp | treaty |  | pdf | ok | page | 1 | Protocol to the Agreement between China and Japan |
| treaty.cn-kr.1994.en | cn-kr | treaty |  | pdf | ok | en_article | 114 | Agreement between China and Korea for the Avoidance of Doubl |
| treaty.cn-kr.1994.mli.en | cn-kr | treaty |  | pdf | ok | en_article | 128 | Synthesised text of the MLI and the China-Korea DTA |
| treaty.cn-kr.1994.mou1.en | cn-kr | treaty |  | pdf | ok | page | 2 | Memorandum of Understanding on the Tax Agreement between Chi |
| treaty.cn-kr.1994.mou2.en | cn-kr | treaty |  | pdf | ok | page | 3 | Memorandum of Understanding on the Agreement between China a |
| treaty.cn-kr.1994.p1.en | cn-kr | treaty |  | pdf | ok | page | 1 | Protocol to the Agreement between China and Korea |
| treaty.cn-kr.1994.p2.en | cn-kr | treaty |  | pdf | ok | en_article | 9 | Second Protocol to the Agreement between China and Korea |
| treaty.cn-my.1985.en | cn-my | treaty |  | pdf | ok | en_article | 125 | Agreement between China and Malaysia for the Avoidance of Do |
| treaty.cn-my.1985.mli.en | cn-my | treaty |  | pdf | ok | en_article | 126 | Synthesised text of the MLI and the China-Malaysia DTA |
| treaty.cn-my.1985.notes.en | cn-my | treaty |  | pdf | ok | page | 4 | Exchange of Notes (China-Malaysia) |
| treaty.cn-my.1985.p1.en | cn-my | treaty |  | pdf | ok | page | 2 | Protocol (China-Malaysia) |
| treaty.cn-sg.2007.en | cn-sg | treaty |  | pdf | ok | en_article | 122 | Agreement between China and Singapore for the Avoidance of D |
| treaty.cn-sg.2007.mli.en | cn-sg | treaty |  | pdf | ok | en_article | 132 | Synthesised text of the MLI and the China-Singapore DTA |
| treaty.cn-sg.2007.p2.en | cn-sg | treaty |  | pdf | ok | en_article | 6 | Second Protocol to the Agreement between China and Singapore |
| treaty.cn-sg.2007.p3.en | cn-sg | treaty |  | pdf | ok | page | 2 | Third Protocol to the Agreement between China and Singapore |
| treaty.cn-th.1986.en | cn-th | treaty |  | pdf | ok | en_article | 116 | Agreement between China and Thailand for the Avoidance of Do |
| treaty.cn-th.1986.mli.en | cn-th | treaty |  | pdf | ok | en_article | 117 | Synthesised text of the MLI and the China-Thailand DTA |
| treaty.cn-vn.1995.en | cn-vn | treaty |  | pdf | ok | en_article | 116 | Agreement between China and Viet Nam for the Avoidance of Do |
| treaty.cn-vn.1995.mli.en | cn-vn | treaty |  | pdf | ok | en_article | 120 | Synthesised text of the MLI and the China-Vietnam DTA |
| treaty.cn-vn.1995.notes.en | cn-vn | treaty |  | pdf | ok | page | 2 | Exchange of Notes (China-Viet Nam) |
| treaty.cn-vn.1995.p1.en | cn-vn | treaty |  | pdf | ok | page | 1 | Protocol to the Agreement between China and Viet Nam |
| treaty.hk-id.2010.en | hk-id | treaty |  | rtf | ok | en_article | 133 | Hong Kong-Indonesia comprehensive DTA, s.49 Order (Cap. 112B |
| treaty.hk-id.2010.mli.en | hk-id | treaty |  | pdf | ok | en_article | 134 | Synthesised text of the MLI and the Hong Kong-Indonesia DTA  |
| treaty.hk-in.2018.en | hk-in | treaty |  | rtf | ok | en_article | 144 | Hong Kong-India comprehensive DTA, s.49 Order (Cap. 112DD) |
| treaty.hk-in.2018.mli.en | hk-in | treaty |  | pdf | ok | en_article | 144 | Synthesised text of the MLI and the Hong Kong-India DTA (IRD |
| treaty.hk-jp.2010.en | hk-jp | treaty |  | rtf | ok | en_article | 135 | Hong Kong-Japan comprehensive DTA, s.49 Order (Cap. 112BS) |
| treaty.hk-jp.2010.mli.en | hk-jp | treaty |  | pdf | ok | en_article | 132 | Synthesised text of the MLI and the Hong Kong-Japan DTA (IRD |
| treaty.hk-jp.2010.notes.en | hk-jp | treaty |  | pdf | ok | page | 3 | Exchange of Notes of 31 March 2012 regarding Article 11 of t |
| treaty.hk-kr.2014.en | hk-kr | treaty |  | rtf | ok | en_article | 123 | Hong Kong-Korea comprehensive DTA, s.49 Order (Cap. 112CL) |
| treaty.hk-kr.2014.mli.en | hk-kr | treaty |  | pdf | ok | en_article | 121 | Synthesised text of the MLI and the Hong Kong-Korea DTA (IRD |
| treaty.hk-my.2012.en | hk-my | treaty |  | rtf | ok | en_article | 133 | Hong Kong-Malaysia comprehensive DTA, s.49 Order (Cap. 112CC |
| treaty.hk-my.2012.mli.en | hk-my | treaty |  | pdf | ok | en_article | 132 | Synthesised text of the MLI and the Hong Kong-Malaysia DTA ( |
| treaty.hk-th.2005.en | hk-th | treaty |  | rtf | ok | en_article | 124 | Hong Kong-Thailand comprehensive DTA, s.49 Order (Cap. 112AX |
| treaty.hk-th.2005.mli.en | hk-th | treaty |  | pdf | ok | en_article | 124 | Synthesised text of the MLI and the Hong Kong-Thailand DTA ( |
| treaty.hk-th.2005.notes.en | hk-th | treaty |  | pdf | ok | page | 1 | Note from the Government of Hong Kong to the Government of T |
| treaty.hk-vn.2008.en | hk-vn | treaty |  | rtf | ok | en_article | 128 | Hong Kong-Viet Nam comprehensive DTA and its 2014 Protocol,  |
| treaty.id-in.2012.mli.en | id-in | treaty |  | pdf | ok | en_article | 156 | Synthesised text of the Indonesia–India Double Taxation Agre |
| treaty.id-jp.1982.mli.en | id-jp | treaty |  | pdf | ok | en_article | 126 | Synthesised text of the Indonesia–Japan Double Taxation Agre |
| treaty.id-kr.1988.mli.en | id-kr | treaty |  | pdf | ok | en_article | 35 | Synthesised text of the Indonesia–Republic of Korea Double T |
| treaty.id-my.1991.mli.en | id-my | treaty |  | pdf | ok | en_article | 140 | Synthesised text of the Indonesia–Malaysia Double Taxation A |
| treaty.id-sg.2020.en | id-sg | treaty |  | html | ok | en_article | 34 | Indonesia–Singapore Agreement for the Elimination of Double  |
| treaty.id-th.2012.mli.en | id-th | treaty |  | html | ok | en_article | 41 | Synthesised text of the Indonesia–Thailand Double Taxation A |
| treaty.id-vn.1997.mli.en | id-vn | treaty |  | pdf | ok | en_article | 128 | Synthesised text of the Indonesia–Vietnam Double Taxation Ag |
| treaty.in-jp.1989.en | in-jp | treaty |  | pdf | scanned_or_empty | page | 0 | Convention between the Government of Japan and the Governmen |
| treaty.in-jp.1989.mli.en | in-jp | treaty |  | pdf | ok | en_article | 134 | Synthesised Text of the MLI and the Convention between Japan |
| treaty.in-jp.2006.protocol.en | in-jp | treaty |  | pdf | ok | page | 3 | Protocol Amending the Convention between Japan and India for |
| treaty.in-jp.2015.protocol.en | in-jp | treaty |  | pdf | ok | en_article | 22 | Protocol Amending the Convention between Japan and India for |
| treaty.in-kr.2015.law | in-kr | treaty |  | html | ok | whole | 1 | Agreement between the Republic of Korea and the Republic of  |
| treaty.in-my.2012.hasil | in-my | treaty |  | pdf | ok | en_article | 147 | Double Taxation Avoidance Agreement between Malaysia and the |
| treaty.in-my.2012.mli.hasil | in-my | treaty |  | pdf | ok | en_article | 155 | Synthesised Text: Malaysia-India Double Taxation Avoidance A |
| treaty.in-sg.1994.en | in-sg | treaty |  | pdf | ok | en_article | 241 | Agreement between the Government of the Republic of Singapor |
| treaty.in-th.2015.en | in-th | treaty |  | pdf | ocr | en_article | 122 | Convention between the Kingdom of Thailand and the Republic  |
| treaty.in-th.2015.protocol.en | in-th | treaty |  | pdf | ocr | page | 1 | Protocol to the Convention between the Kingdom of Thailand a |
| treaty.in-vn.1994.mofa | in-vn | treaty |  | html | ok | whole | 1 | Agreement between Viet Nam and India for the Avoidance of Do |
| treaty.in-vn.1994.mofa.text | in-vn | treaty |  | pdf | scanned_or_empty | page | 0 | Agreement between Viet Nam and India for the Avoidance of Do |
| treaty.jp-kr.1998.mli.en | jp-kr | treaty |  | pdf | ok | en_article | 128 | Synthesised text of the MLI and the Japan-Korea convention |
| treaty.jp-my.1999.mli.en | jp-my | treaty |  | pdf | ok | en_article | 126 | Synthesised text of the MLI and the Japan-Malaysia agreement |
| treaty.jp-sg.1994.mli.en | jp-sg | treaty |  | pdf | ok | en_article | 134 | Synthesised text of the MLI and the Japan-Singapore agreemen |
| treaty.jp-sg.1994.p1.en | jp-sg | treaty |  | pdf | ok | page | 3 | Protocol amending the Japan-Singapore agreement (2010) |
| treaty.jp-th.1990.mli.en | jp-th | treaty |  | pdf | ok | en_article | 124 | Synthesised text of the MLI and the Japan-Thailand conventio |
| treaty.jp-vn.1995.mli.en | jp-vn | treaty |  | pdf | ok | en_article | 128 | Synthesised text of the MLI and the Japan-Viet Nam agreement |
| treaty.jp-vn.1995.notes.en | jp-vn | treaty |  | pdf | ok | page | 5 | Japan-Viet Nam exchange of notes (2014), Japanese and Englis |
| treaty.kr-my.1982.hasil | kr-my | treaty |  | pdf | ok | en_article | 126 | Double Taxation Avoidance Agreement between Malaysia and the |
| treaty.kr-my.1982.mli.hasil | kr-my | treaty |  | pdf | ok | en_article | 127 | Synthesised Text: Malaysia-Korea Double Taxation Avoidance A |
| treaty.kr-sg.2019.iras | kr-sg | treaty |  | pdf | ok | en_article | 248 | Agreement between Singapore and the Republic of Korea for th |
| treaty.kr-th.2006.rd | kr-th | treaty |  | pdf | scanned_or_empty | page | 0 | Convention between Thailand and the Republic of Korea for th |
| treaty.kr-vn.1994.mofa | kr-vn | treaty |  | html | ok | whole | 1 | Agreement between Viet Nam and the Republic of Korea for the |
| treaty.kr-vn.1994.mofa.text | kr-vn | treaty |  | pdf | scanned_or_empty | page | 0 | Agreement between Viet Nam and the Republic of Korea for the |
| treaty.kr-vn.2019.protocol.mofa | kr-vn | treaty |  | html | ok | whole | 1 | Second Protocol amending the Viet Nam-Korea Double Taxation  |
| treaty.kr-vn.2019.protocol.mofa.text | kr-vn | treaty |  | pdf | scanned_or_empty | page | 0 | Second Protocol amending the Viet Nam-Korea Double Taxation  |
| treaty.my-sg.2004.en | my-sg | treaty | 1;2;3;4 | pdf | ok | en_article | 130 | Agreement between the Government of Malaysia and the Governm |
| treaty.my-th.1982.en | my-th | treaty | 1;2;3;4 | pdf | ok | en_article | 136 | Agreement between the Government of Malaysia and the Governm |
| treaty.my-vn.1995.en | my-vn | treaty | 1;2;3;4 | pdf | ok | en_article | 123 | Agreement between the Government of Malaysia and the Governm |
| treaty.sg-th.2015.en | sg-th | treaty |  | pdf | ok | en_article | 235 | Agreement between Singapore and Thailand for the Avoidance o |
| treaty.sg-vn.1994.en | sg-vn | treaty |  | pdf | ok | en_article | 149 | Agreement between Singapore and Vietnam for the Avoidance of |
| treaty.th-vn.1992.art01-05.en | th-vn | treaty |  | html | ok | en_article | 20 | Agreement between Thailand and Viet Nam for the Avoidance of |
| treaty.th-vn.1992.art06-10.en | th-vn | treaty |  | html | ok | en_article | 24 | Agreement between Thailand and Viet Nam for the Avoidance of |
| treaty.th-vn.1992.art11-15.en | th-vn | treaty |  | html | ok | en_article | 27 | Agreement between Thailand and Viet Nam for the Avoidance of |
| treaty.th-vn.1992.art16-20.en | th-vn | treaty |  | html | ok | en_article | 11 | Agreement between Thailand and Viet Nam for the Avoidance of |
| treaty.th-vn.1992.art21-25.en | th-vn | treaty |  | html | ok | en_article | 16 | Agreement between Thailand and Viet Nam for the Avoidance of |
| treaty.th-vn.1992.art26-28.en | th-vn | treaty |  | html | ok | en_article | 5 | Agreement between Thailand and Viet Nam for the Avoidance of |
| vn.btc.tax-administration.14-vbhn-2026 | vn | regulation | 7 | pdf | scanned_or_empty | page | 1 | Consolidated Circular 80/2021/TT-BTC on Tax Administration ( |
| vn.btc.treaty-procedure | vn | regulation | 7;8 | pdf | ok | page | 94 | Văn bản hợp nhất Thông tư hướng dẫn thực hiện Hiệp định thuế |
| vn.gov.beneficial-owner-criteria | vn | guidance | 5 | htm | ok | html_section | 140 | Nghị định 168/2025/NĐ-CP về đăng ký doanh nghiệp |
| vn.gov.pit-withholding-rates | vn | page | 6;page_rates | htm | ok | html_section | 10 | Quy định mới về khấu trừ thuế thu nhập cá nhân |
| vn.gov.related-party-tax-avoidance | vn | guidance | 4 | htm | ok | html_section | 13 | Tăng cường công tác nghiệp vụ phát hiện, điều tra, xử lý ngh |
| vn.gov.tax-filing-deadlines | vn | page | page_deadlines | htm | ok | html_section | 10 | Quy định thời hạn nộp hồ sơ khai thuế |
| vn.law.cit2025.en | vn | law | 1;4;9 | htm | ok | whole | 1 | Law on Corporate Income Tax |
| vn.law.pit.consolidation112.2026.vi | vn | law | 2 | pdf | ocr | page | 15 | Luật Thuế thu nhập cá nhân — 112/VBHN-VPQH |
| vn.law.pit2026.vi | vn | law | 2 | pdf | ok | vn_article | 140 | Luật Thuế thu nhập cá nhân số 109/2025/QH15 |
| vn.mofa.treaty-index | vn | page | page_treaties | html | ok | whole | 1 | Cơ sở dữ liệu Điều ước quốc tế |

## Errors

- doc treaty.ae-in.1992.mli.en: no text (scanned_or_empty)
- doc treaty.in-jp.1989.en: no text (scanned_or_empty)
- doc treaty.in-vn.1994.mofa.text: no text (scanned_or_empty)
- doc treaty.kr-th.2006.rd: no text (scanned_or_empty)
- doc treaty.kr-vn.1994.mofa.text: no text (scanned_or_empty)
- doc treaty.kr-vn.2019.protocol.mofa.text: no text (scanned_or_empty)
- doc vn.btc.tax-administration.14-vbhn-2026: no text (scanned_or_empty)
- param kr.final.company_cit_marginal_rate_band1: cite_id not found: kr.corporate-tax-act.20260701.ko#a55.table1.row1
- param kr.final.company_cit_marginal_rate_band2: cite_id not found: kr.corporate-tax-act.20260701.ko#a55.table1.row2
- param kr.final.company_cit_marginal_rate_band3: cite_id not found: kr.corporate-tax-act.20260701.ko#a55.table1.row3
- param kr.final.company_cit_marginal_rate_band4: cite_id not found: kr.corporate-tax-act.20260701.ko#a55.table1.row4
- param kr.final.individual_global_income_marginal_rate_band1: cite_id not found: kr.income-tax-act.20260701.ko#a55.table1.row1
- param kr.final.individual_global_income_marginal_rate_band2: cite_id not found: kr.income-tax-act.20260701.ko#a55.table1.row2
- param kr.final.individual_global_income_marginal_rate_band3: cite_id not found: kr.income-tax-act.20260701.ko#a55.table1.row3
- param kr.final.individual_global_income_marginal_rate_band4: cite_id not found: kr.income-tax-act.20260701.ko#a55.table1.row4
- param kr.final.individual_global_income_marginal_rate_band5: cite_id not found: kr.income-tax-act.20260701.ko#a55.table1.row5
- param kr.final.individual_global_income_marginal_rate_band6: cite_id not found: kr.income-tax-act.20260701.ko#a55.table1.row6
- param kr.final.individual_global_income_marginal_rate_band7: cite_id not found: kr.income-tax-act.20260701.ko#a55.table1.row7
- param kr.final.individual_global_income_marginal_rate_band8: cite_id not found: kr.income-tax-act.20260701.ko#a55.table1.row8
- decision ae.absent.cfc: quote not found verbatim in ae.mof.top-up-tax#all (copy it from: python database/tools/find.py --cite ae.mof.top-up-tax#all)

## Warnings

- clause kr.income-tax-act.20260701.ko#17.2: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#17.3: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#17.4: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#17.5: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#17.6: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#21.2: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#21.3: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#21.4: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#21.5: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#37.2: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#37.3: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#37.4: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#70.2: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#70.3: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#70.4: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#70.5: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#70.6: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#89.2: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#89.3: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#95.2: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#95.3: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#95.4: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#95.5: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#95.6: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#95.7: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-9.2: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-10.2: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-10.3: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-10.4: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-10.5: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-10.6: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-12.2: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-13.2: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-13.3: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-14.2: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-14.3: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-15.2: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-15.3: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-15.4: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-15.5: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-15.6: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-16.2: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-16.3: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-16.4: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-16.5: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-17.2: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-17.3: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-17.4: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#118-18.2: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#126.2: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#126.3: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#126.4: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#126.5: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#126.6: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#127.2: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#127.3: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#127.4: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#127.5: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#127.6: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#127.7: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#127.8: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#156.2: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#156.3: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#156.4: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#156.5: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#156.6: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#156.7: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#156.8: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#156.9: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#156.10: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#156.11: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#156.12: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#156.13: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#156.14: duplicate cite_id, later one dropped
- clause kr.income-tax-act.20260701.ko#156.15: duplicate cite_id, later one dropped
- th.outbound_wht.dividend_wht_rate cites th.rc3.rates.th#all: a law is cited by provision; fix the slicer or record 'th.rc3.rates.th sliced as whole/page' in session_log.md (§4.3)
- th.final.cit_rate cites th.rc3.rates.th#all: a law is cited by provision; fix the slicer or record 'th.rc3.rates.th sliced as whole/page' in session_log.md (§4.3)
- th.final.progressive_bracket_1_rate cites th.rc3.rates.th#all: a law is cited by provision; fix the slicer or record 'th.rc3.rates.th sliced as whole/page' in session_log.md (§4.3)
- th.final.progressive_bracket_1_upper cites th.rc3.rates.th#all: a law is cited by provision; fix the slicer or record 'th.rc3.rates.th sliced as whole/page' in session_log.md (§4.3)
- th.final.progressive_bracket_2_rate cites th.rc3.rates.th#all: a law is cited by provision; fix the slicer or record 'th.rc3.rates.th sliced as whole/page' in session_log.md (§4.3)
- th.final.progressive_bracket_2_upper cites th.rc3.rates.th#all: a law is cited by provision; fix the slicer or record 'th.rc3.rates.th sliced as whole/page' in session_log.md (§4.3)
- th.final.progressive_bracket_3_rate cites th.rc3.rates.th#all: a law is cited by provision; fix the slicer or record 'th.rc3.rates.th sliced as whole/page' in session_log.md (§4.3)
- th.final.progressive_bracket_3_upper cites th.rc3.rates.th#all: a law is cited by provision; fix the slicer or record 'th.rc3.rates.th sliced as whole/page' in session_log.md (§4.3)
- th.final.progressive_bracket_4_rate cites th.rc3.rates.th#all: a law is cited by provision; fix the slicer or record 'th.rc3.rates.th sliced as whole/page' in session_log.md (§4.3)
- th.final.progressive_bracket_4_upper cites th.rc3.rates.th#all: a law is cited by provision; fix the slicer or record 'th.rc3.rates.th sliced as whole/page' in session_log.md (§4.3)
- th.final.progressive_bracket_5_rate cites th.rc3.rates.th#all: a law is cited by provision; fix the slicer or record 'th.rc3.rates.th sliced as whole/page' in session_log.md (§4.3)
- th.final.progressive_bracket_5_upper cites th.rc3.rates.th#all: a law is cited by provision; fix the slicer or record 'th.rc3.rates.th sliced as whole/page' in session_log.md (§4.3)
- th.final.progressive_bracket_6_rate cites th.rc3.rates.th#all: a law is cited by provision; fix the slicer or record 'th.rc3.rates.th sliced as whole/page' in session_log.md (§4.3)
- th.final.progressive_bracket_6_upper cites th.rc3.rates.th#all: a law is cited by provision; fix the slicer or record 'th.rc3.rates.th sliced as whole/page' in session_log.md (§4.3)
- th.final.progressive_bracket_7_rate cites th.rc3.rates.th#all: a law is cited by provision; fix the slicer or record 'th.rc3.rates.th sliced as whole/page' in session_log.md (§4.3)
- th.restructure.gain_tax_rate cites th.rc3.rates.th#all: a law is cited by provision; fix the slicer or record 'th.rc3.rates.th sliced as whole/page' in session_log.md (§4.3)
- th.restructure.resident_gain_tax_rate cites th.rc3.rates.th#all: a law is cited by provision; fix the slicer or record 'th.rc3.rates.th sliced as whole/page' in session_log.md (§4.3)
- th.restructure.stamp_rate cites th.rc6.stamp.th#all: a law is cited by provision; fix the slicer or record 'th.rc6.stamp.th sliced as whole/page' in session_log.md (§4.3)
- th.restructure.stamp_base cites th.rc6.stamp.th#all: a law is cited by provision; fix the slicer or record 'th.rc6.stamp.th sliced as whole/page' in session_log.md (§4.3)
- id.final.cit_rate cites id.tax-law-compilation-2022#p184: a law is cited by provision; fix the slicer or record 'id.tax-law-compilation-2022 sliced as whole/page' in session_log.md (§4.3)
- id.inbound.foreign_dividend_exempt_if_invested cites id.tax-law-compilation-2022#p133: a law is cited by provision; fix the slicer or record 'id.tax-law-compilation-2022 sliced as whole/page' in session_log.md (§4.3)
- vn.final.cit_rate cites vn.law.cit2025.en#all: a law is cited by provision; fix the slicer or record 'vn.law.cit2025.en sliced as whole/page' in session_log.md (§4.3)
- vn.inbound.foreign_income_taxable cites vn.law.cit2025.en#all: a law is cited by provision; fix the slicer or record 'vn.law.cit2025.en sliced as whole/page' in session_log.md (§4.3)
- vn.inbound.foreign_tax_credit_cap cites vn.law.cit2025.en#all: a law is cited by provision; fix the slicer or record 'vn.law.cit2025.en sliced as whole/page' in session_log.md (§4.3)
- vn.residence.worldwide_tax_scope cites vn.law.cit2025.en#all: a law is cited by provision; fix the slicer or record 'vn.law.cit2025.en sliced as whole/page' in session_log.md (§4.3)
- ae-jp.outbound_wht.dividend_rate_parent cites treaty.ae-jp.2013.summary.en#all: a treaty is cited by provision; fix the slicer or record 'treaty.ae-jp.2013.summary.en sliced as whole/page' in session_log.md (§4.3)
- ae-jp.outbound_wht.dividend_rate_other cites treaty.ae-jp.2013.summary.en#all: a treaty is cited by provision; fix the slicer or record 'treaty.ae-jp.2013.summary.en sliced as whole/page' in session_log.md (§4.3)
- ae-jp.outbound_wht.interest_rate_government cites treaty.ae-jp.2013.summary.en#all: a treaty is cited by provision; fix the slicer or record 'treaty.ae-jp.2013.summary.en sliced as whole/page' in session_log.md (§4.3)
- ae-jp.outbound_wht.interest_rate cites treaty.ae-jp.2013.summary.en#all: a treaty is cited by provision; fix the slicer or record 'treaty.ae-jp.2013.summary.en sliced as whole/page' in session_log.md (§4.3)
- ae-jp.outbound_wht.royalty_rate cites treaty.ae-jp.2013.summary.en#all: a treaty is cited by provision; fix the slicer or record 'treaty.ae-jp.2013.summary.en sliced as whole/page' in session_log.md (§4.3)
- ae-jp.anti_abuse.ppt_applies cites treaty.ae-jp.2013.mli.en#all: a treaty is cited by provision; fix the slicer or record 'treaty.ae-jp.2013.mli.en sliced as whole/page' in session_log.md (§4.3)
- id.residence.residence_days_threshold cites id.tax-law-compilation-2022#p121: a law is cited by provision; fix the slicer or record 'id.tax-law-compilation-2022 sliced as whole/page' in session_log.md (§4.3)
- id.residence.residence_test cites id.tax-law-compilation-2022#p121: a law is cited by provision; fix the slicer or record 'id.tax-law-compilation-2022 sliced as whole/page' in session_log.md (§4.3)
- id.final.individual_top_rate cites id.tax-law-compilation-2022#p184: a law is cited by provision; fix the slicer or record 'id.tax-law-compilation-2022 sliced as whole/page' in session_log.md (§4.3)
- id.cfc.overseas_dividend_receipt_time cites id.tax-law-compilation-2022#p187: a law is cited by provision; fix the slicer or record 'id.tax-law-compilation-2022 sliced as whole/page' in session_log.md (§4.3)
- id.anti_abuse.substance_over_form cites id.tax-law-compilation-2022#p189: a law is cited by provision; fix the slicer or record 'id.tax-law-compilation-2022 sliced as whole/page' in session_log.md (§4.3)
- kr.cfc.cfc_reporting_required cites kr.itca.enforcement-decree#p59: a regulation is cited by provision; fix the slicer or record 'kr.itca.enforcement-decree sliced as whole/page' in session_log.md (§4.3)
- kr.anti_abuse.substance_over_form_principle cites kr.itca.enforcement-decree#p4: a regulation is cited by provision; fix the slicer or record 'kr.itca.enforcement-decree sliced as whole/page' in session_log.md (§4.3)
- ae.final.in_scope_mne_dmtt_applies cites ae.cabinet142.2024.dmtt.en#p2: a regulation is cited by provision; fix the slicer or record 'ae.cabinet142.2024.dmtt.en sliced as whole/page' in session_log.md (§4.3)
- vn.absent.3 cites vn.law.cit2025.en#all: a law is cited by provision; fix the slicer or record 'vn.law.cit2025.en sliced as whole/page' in session_log.md (§4.3)
- vn.absent.cfc cites vn.law.cit2025.en#all: a law is cited by provision; fix the slicer or record 'vn.law.cit2025.en sliced as whole/page' in session_log.md (§4.3)
- vn.absent.company.outbound_wht cites vn.law.cit2025.en#all: a law is cited by provision; fix the slicer or record 'vn.law.cit2025.en sliced as whole/page' in session_log.md (§4.3)

## Gaps

Cells of jurisdiction | category with neither a document nor an absence record:

- id|10
- vn|10
- my|10
- ae|10
- kr|10
- in|10

Cells of jurisdiction | subject | slot with neither a parameter nor an absence record:

- id|company|penalty
- id|company|restructure
- id|company|exit
- id|individual|penalty
- id|individual|restructure
- id|individual|exit
- vn|company|penalty
- vn|company|restructure
- vn|company|exit
- vn|individual|penalty
- vn|individual|restructure
- vn|individual|exit
- my|company|penalty
- my|company|restructure
- my|company|exit
- my|individual|penalty
- my|individual|restructure
- my|individual|exit
- ae|company|penalty
- ae|company|restructure
- ae|company|exit
- ae|individual|penalty
- ae|individual|restructure
- ae|individual|exit
- kr|company|penalty
- kr|company|restructure
- kr|company|exit
- kr|individual|penalty
- kr|individual|restructure
- kr|individual|exit
- in|company|penalty
- in|company|restructure
- in|company|exit
- in|individual|penalty
- in|individual|restructure
- in|individual|exit

Pairs without a treaty row (a row with empty doc_id records "no treaty"):

None.

Downloads in blocked.csv not yet in doc.csv:

- sg.sda1929 (Singapore Statutes Online answered 403 to a plain request and hung on retries with the fetch tool; not retried with disguised requests. The IRAS page sg.iras.stamp.shares carries the 0.2% rate and the NAV valuation in the meantime.)
- sg.sda1929 (Second plain attempt 2026-10-31 (requests engine, no disguise): the request hung with no answer and was stopped after 120 s; the first attempt answered 403. Not retried with disguised requests. The IRAS page sg.iras.stamp.shares remains the source of the 0.2% rate and the NAV valuation.)

## Repealed-provision stubs left out

- `sg.ita1947#s18A`: 18A. [ Repealed by Act 21 of 2003 ]
- `sg.ita1947#s29`: 29. [ Repealed by Act 19 of 2013 ]
- `sg.ita1947#s30`: 30. [ Repealed by Act 19 of 2013 ]
- `sg.ita1947#s40`: 40. [ Repealed by Act 41 of 2020 ]
- `sg.ita1947#s44`: 44. [ Repealed by Act 19 of 2013 ]
- `sg.ita1947#s44A`: 44A. [ Repealed by Act 19 of 2013 ]
- `sg.ita1947#s48`: 48. [ Repealed by Act 27 of 2009 ]
- `sg.ita1947#s105C`: 105C. [ Repealed by Act 19 of 2013 ]
- `hk.cap112#s5A`: 5A. (Repealed 56 of 1993 s. 3)
- `hk.cap112#s6`: 6. (Repealed 8 of 1983 s. 7)
- `hk.cap112#s7`: 7. (Repealed 56 of 1993 s. 5)
- `hk.cap112#s7B`: 7B. (Repealed 56 of 1993 s. 7)
- `hk.cap112#s11A`: 11A. (Repealed 71 of 1983 s. 4)
- `hk.cap112#s12BA`: 12BA. (Repealed 31 of 1998 s. 6)
- `hk.cap112#s15B`: 15B. (Repealed 71 of 1983 s. 13)
- `hk.cap112#s19A`: 19A. (Repealed 56 of 1993 s. 14)
- `hk.cap112#s19B`: 19B. (Repealed 56 of 1993 s. 15)
- `hk.cap112#s20`: 20. (Repealed 27 of 2018 s. 15)
- `hk.cap112#s20AG`: 20AG. (Repealed 5 of 2019 s. 5)
- `hk.cap112#s20AH`: 20AH. (Repealed 5 of 2019 s. 5)
- `hk.cap112#s20AI`: 20AI. (Repealed 5 of 2019 s. 5)
- `hk.cap112#s20AJ`: 20AJ. (Repealed 5 of 2019 s. 5)
- `hk.cap112#s20AK`: 20AK. (Repealed 5 of 2019 s. 5)
- `hk.cap112#s20AL`: 20AL. (Repealed 5 of 2019 s. 5)
- `hk.cap112#s38C`: 38C. (Repealed 19 of 1996 s. 9)
- `hk.cap112#s40A`: 40A. (Repealed 56 of 1993 s. 19)
- `hk.cap112#s42B`: 42B. (Repealed 43 of 1989 s. 14)
- `hk.cap112#s43A`: 43A. (Repealed 19 of 1991 s. 4)
- `hk.cap112#s44`: 44. (Repealed 49 of 1956 s. 33)
- `hk.cap112#s45`: 45. (Repealed 32 of 1998 s. 28)
- `hk.cap112#s46`: 46. (Repealed 12 of 1999 s. 3)
- `hk.cap112#s47`: 47. (Repealed 49 of 1956 s. 35)
- `hk.cap112#s48`: 48. (Repealed 49 of 1956 s. 35)
- `hk.cap112#s55`: 55. (Repealed 49 of 1956 s. 39)
- `hk.cap112#s58A`: 58A. (Repealed 43 of 1989 s. 18)
- `hk.cap112#s59A`: 59A. (Repealed 52 of 1993 s. 6)
- `hk.cap112#s63A`: 63A. (Repealed 12 of 1999 s. 3)
- `hk.cap112#s73`: 73. (Repealed 49 of 1956 s. 54)
- `hk.cap112#s74`: 74. (Repealed 49 of 1956 s. 54)
- `hk.cap112#s75A`: 75A. (Repealed 43 of 1989 s. 26)
- `hk.cap112#s78`: 78. (Repealed 49 of 1956 s. 59)
- `hk.cap112#s80A`: 80A. (Repealed 17 of 1989 s. 19)
- `hk.cap112#s87A`: 87A. (Repealed 76 of 1993 s. 9)
- `hk.cap112#sch15B`: Schedule 15B (Repealed 5 of 2019 s. 7)
- `hk.cap112#sch16A`: Schedule 16A (Repealed 5 of 2019 s. 10)
- `hk.cap112#sch16B`: Schedule 16B (Repealed 5 of 2019 s. 10)
- `hk.cap117#s20`: 20. (Repealed 33 of 2024 s. 5)
- `hk.cap117#s26`: 26. (Repealed 14 of 2014 s. 6)
- `hk.cap117#s29E`: 29E. (Repealed 14 of 2014 s. 25)
- `hk.cap117#s29I`: 29I. (Repealed L.N. 90 of 1999 and 44 of 1999 s. 21)

## Formula images in the text

Singapore Statutes Online prints some formulas as images; the text shows a marker where each one stood.

- `sg.ita1947`: 018b5236-94ff-4954-8e8e-b4252920efb6
- `sg.ita1947`: 01cfe7e5-ff5b-488b-b8ca-29c4b7d9cf00
- `sg.ita1947`: 02ff1d7a-c72e-4d24-972f-e2edc0a81c11
- `sg.ita1947`: 08a18b72-9e66-457c-b38f-ffc43bd93e22
- `sg.ita1947`: 0aab77a9-a08b-4248-828a-6f09113f31e5
- `sg.ita1947`: 0b2461c0-ba28-4c45-9dbd-9fb8c033f4ea
- `sg.ita1947`: 0b5471ca-d5ec-42b0-afe9-3226a39cf222
- `sg.ita1947`: 0c2dcb94-73e0-4e2d-adfb-ccb1c8de79fa
- `sg.ita1947`: 0d180d28-c924-4d58-8dca-0b2a83b66cd1
- `sg.ita1947`: 0df4e0bc-dc34-4a58-81bf-64414ba4da91
- `sg.ita1947`: 13396767-9f3a-4b40-a452-3db2b2a0b957
- `sg.ita1947`: 14a24a10-0758-49f3-8484-715766a47237
- `sg.ita1947`: 1693b6b2-4104-4b50-acfc-f5cbe7e48566
- `sg.ita1947`: 1871157a-403e-4530-8f6c-b27c9fcfb669
- `sg.ita1947`: 193f0baf-c022-414d-9d3d-698ec5606540
- `sg.ita1947`: 19d61cf4-3faf-4374-994f-f407086988da
- `sg.ita1947`: 19d63ca1-5dff-4168-96a4-f441849b7d09
- `sg.ita1947`: 1aaf5290-bef3-4e6e-994d-7b6444170862
- `sg.ita1947`: 1c515532-63cc-4133-b02b-16622a137a3f
- `sg.ita1947`: 223ff022-5c10-4ebe-9bdb-49eae9129f13
- `sg.ita1947`: 2311ddd7-115c-43fb-9665-1de507cb6107
- `sg.ita1947`: 235f4315-58a2-47e8-8781-f67ade580ef1
- `sg.ita1947`: 25ed638d-7c7a-470d-bbbe-8ab58b327890
- `sg.ita1947`: 26902e6a-75a1-4d1a-bb00-bcbdab992f7a
- `sg.ita1947`: 291eb7a3-22bb-4272-9005-082f5692cbff
- `sg.ita1947`: 31221017-e9b5-4c71-8fe0-6363b0abf540
- `sg.ita1947`: 324f0b1e-cf7a-4bac-a8a4-8878b7a5fdd0
- `sg.ita1947`: 32dd4ad0-c32e-416d-97c6-e3d537b7c6a2
- `sg.ita1947`: 344f1d86-aea0-4ee3-9823-c9e3e4fe95a6
- `sg.ita1947`: 3521424b-e92e-45ae-a9b9-351a360bc198
- `sg.ita1947`: 38589b53-09f4-423d-8ec8-7dad6dfae141
- `sg.ita1947`: 39a8881b-ad62-4632-99e1-8626bc595f7b
- `sg.ita1947`: 39c38b19-b5ee-48e4-8679-184edd108bef
- `sg.ita1947`: 3a9ae984-4b25-4b8a-b119-d2b738175a44
- `sg.ita1947`: 3b3d9c1c-b575-4663-9d35-268c787c3fab
- `sg.ita1947`: 414b5dcf-28f7-43f9-bd07-5ec5df968126
- `sg.ita1947`: 42057b1e-17e9-4803-891d-8dfd9dc6f4e3
- `sg.ita1947`: 421a1e79-8d4d-459a-a147-0da6266258e4
- `sg.ita1947`: 44c1f0fb-d5dc-4e84-a7f9-fba96550e57c
- `sg.ita1947`: 44d0098a-61fa-4f96-8651-27495ae07244
- `sg.ita1947`: 46c3af9f-6a6d-4ac1-8c60-a8d4d1730b63
- `sg.ita1947`: 4ab1b8d1-8011-42d2-9513-3493ac879680
- `sg.ita1947`: 4b510414-0761-474c-a222-b5a6a27d5027
- `sg.ita1947`: 4b59451f-a953-49d4-afad-c0304c3e50c3
- `sg.ita1947`: 4df55635-af32-42f7-a357-e78ee585a2a0
- `sg.ita1947`: 4e339a06-6076-4ecc-b14a-5d0b32dea317
- `sg.ita1947`: 4e7d4db0-b30d-43d9-a208-f23f41a1c900
- `sg.ita1947`: 4fe0ebf6-6944-4de2-acb2-068134b904a2
- `sg.ita1947`: 4fe8d1a8-eceb-4482-9e4b-e539770411a8
- `sg.ita1947`: 50561084-3208-4e1c-beee-4fe813d6d3b6
- `sg.ita1947`: 56195678-8172-4f54-993c-75245295a9e8
- `sg.ita1947`: 5645756d-3eb1-486a-acfd-5bbc7d5b73de
- `sg.ita1947`: 5a5d14da-b523-4a4d-9e1d-79efe2e39c58
- `sg.ita1947`: 5c28db4c-adda-4947-ae1c-ebbb7d1146f6
- `sg.ita1947`: 5e5818d9-acfd-4323-87fc-e988fbcfbc24
- `sg.ita1947`: 5fb9a583-64fb-4f0f-933a-f76b0182cd39
- `sg.ita1947`: 604def22-b609-4866-a8cf-db05dd821b1e
- `sg.ita1947`: 60d8c0d6-25cd-4670-9168-2466f61ab878
- `sg.ita1947`: 62c4a5db-1d97-4f66-afe5-fcaef56e0335
- `sg.ita1947`: 667e6f37-1992-4aeb-a4a4-41a2d46d7bd0
- `sg.ita1947`: 6b78f022-7e1f-434a-b7ac-66489553866c
- `sg.ita1947`: 6dd4f620-c40d-42be-9ec9-e3db2277a6b3
- `sg.ita1947`: 6f9707bc-b9d5-4225-b679-553501f55fcf
- `sg.ita1947`: 7720a2f1-0d8c-4c58-8897-4246a579baea
- `sg.ita1947`: 7774ed88-cd76-410b-bed1-edbbeef8bd32
- `sg.ita1947`: 788065a1-671f-4763-ab68-d04166c869cd
- `sg.ita1947`: 7bc60fcb-7f7f-4e7c-af0f-bd5e0464656c
- `sg.ita1947`: 83998a69-a5ce-4833-8430-719eb5cf5d5e
- `sg.ita1947`: 8596a242-b8ba-4a9e-8ad9-effe35b70b3a
- `sg.ita1947`: 895add11-e271-4ac0-9e9f-7db41e8af6a0
- `sg.ita1947`: 8be73833-d2bf-47c2-a630-0e3ec500b5a6
- `sg.ita1947`: 8d3d50a4-7ed1-4c74-afbf-79cace5236e1
- `sg.ita1947`: 8e678ad7-2a3d-4c84-8619-93242da6d66e
- `sg.ita1947`: 91301bed-6dd3-4b63-87be-34d671a55860
- `sg.ita1947`: 915e74e9-92f1-4dff-90df-1fa403ffae0c
- `sg.ita1947`: 92d5ad10-f708-4ad5-9933-5a4eba14b52d
- `sg.ita1947`: 9806a5f5-a843-491c-a6bd-edc709b88846
- `sg.ita1947`: 99c51d9c-bec0-4a8b-9c66-72103bcbbc7c
- `sg.ita1947`: 9c7677e4-5224-458e-b9b2-c3582095df30
- `sg.ita1947`: a6650fae-3a8c-4fad-9a91-fb6a2e62dcea
- `sg.ita1947`: a84b0ef3-d547-40ec-a447-b722ae69b441
- `sg.ita1947`: a91e1888-2a76-4860-a1f2-2201a9d34158
- `sg.ita1947`: aa27779c-dfb4-4734-851f-be07ad880d3f
- `sg.ita1947`: b39c4f5c-b480-48bf-986a-e85be2c77f5c
- `sg.ita1947`: b53ee4ad-756c-45db-9649-402a9df51127
- `sg.ita1947`: b56a2a04-ff75-4a43-843c-e645ea0178d4
- `sg.ita1947`: b64ceb3c-f72c-4842-b6d4-36828c7c451f
- `sg.ita1947`: b65e1197-1bb2-45cd-8b12-344fadc6be21
- `sg.ita1947`: b8af0965-fd42-46c4-99c4-97a7819a4e7c
- `sg.ita1947`: b924da7c-7c5d-48a1-a190-f192a12b4e54
- `sg.ita1947`: ba780dea-0a57-422a-b3e4-eeaebf46457f
- `sg.ita1947`: bc2c59e9-ce4a-4594-818d-ebd6b90ba3ea
- `sg.ita1947`: be331ebe-99b1-40b6-b870-4b1fd3e8d661
- `sg.ita1947`: bf6f8030-cf0e-4a93-9a4b-fe1397208aa0
- `sg.ita1947`: c1229b43-ab77-4fea-aee1-7498f946c169
- `sg.ita1947`: c18ff2ba-98ff-43db-ab1d-edefc6056e8a
- `sg.ita1947`: c1b05ef8-7ffb-4288-a748-9bd5ea778cd5
- `sg.ita1947`: c3909402-a028-4be5-9898-757a15bacf31
- `sg.ita1947`: c3c70331-7636-47eb-b056-bc5ba8c2808f
- `sg.ita1947`: c3d405e4-3980-48bd-a799-1d98460d05c4
- `sg.ita1947`: c47bf3ef-5427-4583-a900-5fb5d970473b
- `sg.ita1947`: c5c611a6-57e5-494c-9f2d-3dedd8e4b3aa
- `sg.ita1947`: c6995bb2-97a6-462e-a831-3147388757db
- `sg.ita1947`: c77d252e-57e4-460e-a21f-4a369f297bd3
- `sg.ita1947`: c7b3db5b-90e3-454b-83ab-196f89655cef
- `sg.ita1947`: ca4124b4-fbc3-4c6b-90ff-3842d5988be3
- `sg.ita1947`: cc0d3387-9c7f-4e96-b8e0-1b4ff9f676c8
- `sg.ita1947`: cdf475ed-00c8-4e8f-a3b1-f1b7a6c49b07
- `sg.ita1947`: ce1c84e6-58c7-441f-a6e7-57dc98565689
- `sg.ita1947`: cf979839-8b75-4b04-b241-168bfcf5aa7b
- `sg.ita1947`: cfc104ac-c001-419d-add0-6d98a3f6c8b1
- `sg.ita1947`: d06afe62-a2d8-485a-b8e8-0b69429f0191
- `sg.ita1947`: d09e0e28-b7d4-40fb-b54f-9efee69ad3eb
- `sg.ita1947`: d2694bc7-ec9d-4000-b53c-d9f07d204230
- `sg.ita1947`: d26b0df4-3269-4cbd-b6b9-95ee92ed807f
- `sg.ita1947`: d3717d45-92c1-4ca0-a395-2ecf1314ecc1
- `sg.ita1947`: d52b53bc-4e46-4b1b-aaf0-497860c5bb23
- `sg.ita1947`: d548ae93-f55c-4581-8771-135555401632
- `sg.ita1947`: d571e48f-5ff4-4387-94e4-38bb6b749585
- `sg.ita1947`: db315425-793e-47ab-bf1c-0bb740c5e022
- `sg.ita1947`: dc1971f0-4bfb-43d9-bfff-8114323b9529
- `sg.ita1947`: dc8715d7-4b3b-4ec0-8c93-544d7c1e5517
- `sg.ita1947`: ddcc7e6b-ca59-449f-b1cd-3d163c985324
- `sg.ita1947`: e671bfb9-fe04-4fb2-b768-81c38952c6d7
- `sg.ita1947`: eb83ed22-7e57-4171-bb6f-c325b3936850
- `sg.ita1947`: ebc9359d-47f3-4890-b5fb-971c68ab43eb
- `sg.ita1947`: efede5b2-7e54-4838-8f4f-302810cae572
- `sg.ita1947`: f309b6ab-b722-4e58-b784-a526b4cf50b0
- `sg.ita1947`: f39c35a0-70a9-454b-9111-96c378d37e2e
- `sg.ita1947`: f51fa4c9-fa91-49c3-a2a2-902a841a14ad
- `sg.ita1947`: f6bbd9bf-1e9f-4731-b80a-6d2fc351fcee
- `sg.ita1947`: f72c0506-a2cb-4715-a00c-e7f2eb6215d1
- `sg.ita1947`: f823ae92-23a4-4666-b91c-b7d51bed979e
- `sg.ita1947`: f8bb06d9-8052-498b-85c5-82225048e46a
- `sg.ita1947`: fa41bd46-4944-4c64-add6-4592b8ac0def
- `sg.ita1947`: ff14433e-bd6d-41ad-ad12-e5d214f0f3cf
- `sg.ita1947`: ff51a1bf-69ab-4bdc-82e2-5aeefd526da0
