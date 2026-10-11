# official 配套资料核对

由 `python official/tools/audit_handoff.py` 核对当前资料库和引擎。

- 对照此前上传版本：原先缺少的 74 个参数、8 个法条引用均已补齐。
- 数据库完整性：`ok`。
- 参数、条款、口径 CSV 与数据库内容一致。
- 184 条规则编译通过；缺少参数 0，缺少法条引用 0。
- D14–D31 均有记录，全部口径引语在所引条款中逐字找到（忽略空白）。

## D14–D31 的原文依据

完整陈述、原文引语及使用位置见 [decisions.csv](decisions.csv)。

| 口径 | 引文锚点数 | 依据原件 |
|---|---:|---|
| D14 | 6 | [hk.ord.2025-21.pdf](raw/hk/hk.ord.2025-21.pdf), [sg.memta2024.s16.html](raw/sg/sg.memta2024.s16.html), [sg.memta2024.s17.html](raw/sg/sg.memta2024.s17.html) |
| D15 | 7 | [hk.ord.2025-21.pdf](raw/hk/hk.ord.2025-21.pdf), [sg.memta2024.s16.html](raw/sg/sg.memta2024.s16.html), [sg.memta2024.s21.html](raw/sg/sg.memta2024.s21.html) |
| D16 | 7 | [hk.ord.2025-21.pdf](raw/hk/hk.ord.2025-21.pdf), [sg.memta2024.regs.pdf.pdf](raw/sg/sg.memta2024.regs.pdf.pdf), [sg.memta2024.s16.html](raw/sg/sg.memta2024.s16.html), [sg.memta2024.s2.html](raw/sg/sg.memta2024.s2.html) |
| D17 | 12 | [hk.ord.2025-21.pdf](raw/hk/hk.ord.2025-21.pdf), [intl.oecd.globe.commentary.2026.pdf](raw/intl/intl.oecd.globe.commentary.2026.pdf), [sg.memta2024.regs.s48.html](raw/sg/sg.memta2024.regs.s48.html), [sg.memta2024.regs.s70.html](raw/sg/sg.memta2024.regs.s70.html), [sg.memta2024.regs.s73.html](raw/sg/sg.memta2024.regs.s73.html), [sg.memta2024.regs.s9.html](raw/sg/sg.memta2024.regs.s9.html), [sg.memta2024.s19.html](raw/sg/sg.memta2024.s19.html), [sg.memta2024.s20.html](raw/sg/sg.memta2024.s20.html) |
| D18 | 10 | [cn.cs.2009-59.html](raw/cn/cn.cs.2009-59.html), [cn.cs.2014-109.html](raw/cn/cn.cs.2014-109.html), [cn.sta.2013-72.html](raw/cn/cn.sta.2013-72.html), [hk.cap117.en.rtf](raw/hk/hk.cap117.en.rtf), [sg.sda1929.relief2014.sch2.html](raw/sg/sg.sda1929.relief2014.sch2.html), [sg.sda1929.s15.html](raw/sg/sg.sda1929.s15.html) |
| D19 | 12 | [cn.cs.2009-59.html](raw/cn/cn.cs.2009-59.html), [cn.cs.2009-60.html](raw/cn/cn.cs.2009-60.html), [cn.law.stamp.flk.pdf](raw/cn/cn.law.stamp.flk.pdf), [cn.reg.eit.html](raw/cn/cn.reg.eit.html), [hk.cap117.en.rtf](raw/hk/hk.cap117.en.rtf), [hk.cr.redomiciliation.faq.html](raw/hk/hk.cr.redomiciliation.faq.html), [sg.ca1967.s355.html](raw/sg/sg.ca1967.s355.html), [sg.sda1929.relief2014.html](raw/sg/sg.sda1929.relief2014.html), [sg.sda1929.relief2014.sch4.html](raw/sg/sg.sda1929.relief2014.sch4.html), [sg.sda1929.sch1.html](raw/sg/sg.sda1929.sch1.html) |
| D20 | 12 | [hk.ord.2025-21.pdf](raw/hk/hk.ord.2025-21.pdf), [intl.oecd.globe.central-record.2025-12.pdf](raw/intl/intl.oecd.globe.central-record.2025-12.pdf), [sg.memta2024.s11.html](raw/sg/sg.memta2024.s11.html), [sg.memta2024.s13.html](raw/sg/sg.memta2024.s13.html), [sg.memta2024.s14.html](raw/sg/sg.memta2024.s14.html) |
| D21 | 5 | [cn.law.eit.html](raw/cn/cn.law.eit.html), [hk.cap112.en.rtf](raw/hk/hk.cap112.en.rtf), [sg.ita1947.full.html](raw/sg/sg.ita1947.full.html) |
| D22 | 16 | [cn.cs.2010-111.html](raw/cn/cn.cs.2010-111.html), [cn.law.stamp.flk.pdf](raw/cn/cn.law.stamp.flk.pdf), [cn.reg.eit.html](raw/cn/cn.reg.eit.html), [cn.reg.vat.html](raw/cn/cn.reg.vat.html), [treaty.cn-hk.2006.p4.zh.pdf](raw/cn/treaty.cn-hk.2006.p4.zh.pdf), [treaty.cn-sg.2007.zh.pdf](raw/cn/treaty.cn-sg.2007.zh.pdf), [hk.cap112.en.rtf](raw/hk/hk.cap112.en.rtf), [sg.ita1947.full.html](raw/sg/sg.ita1947.full.html) |
| D23 | 6 | [cn.cs.2026-input.html](raw/cn/cn.cs.2026-input.html), [cn.law.vat.html](raw/cn/cn.law.vat.html), [cn.reg.vat.html](raw/cn/cn.reg.vat.html) |
| D24 | 1 | [sg.ita1947.full.html](raw/sg/sg.ita1947.full.html) |
| D25 | 4 | [cn.cs.2026-10.html](raw/cn/cn.cs.2026-10.html), [cn.cs.2026-11.html](raw/cn/cn.cs.2026-11.html), [cn.reg.vat.html](raw/cn/cn.reg.vat.html) |
| D26 | 2 | [cn.law.vat.html](raw/cn/cn.law.vat.html), [cn.sta.2013-09.html](raw/cn/cn.sta.2013-09.html) |
| D27 | 2 | [hk.ord.2025-21.pdf](raw/hk/hk.ord.2025-21.pdf) |
| D28 | 5 | [cn.cs.2014-109.html](raw/cn/cn.cs.2014-109.html), [cn.cs.2024-14.html](raw/cn/cn.cs.2024-14.html), [cn.law.vat.html](raw/cn/cn.law.vat.html), [cn.sta.2015-40.html](raw/cn/cn.sta.2015-40.html) |
| D29 | 3 | [cn.form.a108000.a01.doc](raw/cn/cn.form.a108000.a01.doc), [cn.mof.2016-22.html](raw/cn/cn.mof.2016-22.html), [cn.mof.cas14.a01.pdf](raw/cn/cn.mof.cas14.a01.pdf) |
| D30 | 4 | [cn.cs.2026-10.html](raw/cn/cn.cs.2026-10.html), [cn.cs.2026-25.a01.pdf](raw/cn/cn.cs.2026-25.a01.pdf), [cn.law.stamp.flk.pdf](raw/cn/cn.law.stamp.flk.pdf), [cn.law.vat.html](raw/cn/cn.law.vat.html) |
| D31 | 4 | [cn.gsf.2009-82.html](raw/cn/cn.gsf.2009-82.html), [cn.law.stamp.flk.pdf](raw/cn/cn.law.stamp.flk.pdf), [cn.law.vat.html](raw/cn/cn.law.vat.html) |

废止或替代关系保留在 [removed.csv](removed.csv)、[superseded.csv](superseded.csv) 和 [repealed_stubs.csv](repealed_stubs.csv)，适用局限见 [currency.csv](currency.csv)。本次沿用来源记录，没有另行编写法律口径。

构建报告见 [STATUS.md](STATUS.md) 和 [INDEX.md](INDEX.md)，详细核对结果见 [handoff_audit.json](handoff_audit.json)。
口径属于项目登记的法律解释，本核对验证证据链和代码配套关系，不代表外部税务专家审核。
