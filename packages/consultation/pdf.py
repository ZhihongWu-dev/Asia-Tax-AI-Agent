"""Five-page consulting brief; all comparison numbers are derived from tool outputs."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from html import escape
import json
import os
from math import isfinite
from pathlib import Path

from packages.consultation.workflow import CORE, fingerprint, values


def comparison(brief):
    calculation = next((t for t in reversed(brief.get('tools', [])) if t['tool'] == 'calculate_tax'
                        and t.get('input_hash') == fingerprint(brief)), {})
    current, plan = (calculation.get(k, {}) for k in ('assess_current', 'plan_structure'))
    def number(out, side):
        bound = out.get(side) or {}
        value = bound.get('value')
        return value if bound.get('status') == 'finite' and isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) else None
    baseline, optimal = number(current, 'upper'), number(plan, 'upper')
    comparable = (calculation.get('status') == 'completed' and baseline is not None and optimal is not None
                  and current.get('currency') == plan.get('currency') == values(brief).get('currency')
                  and current.get('today') == plan.get('today') and current.get('status') == plan.get('status') == 'ready'
                  and not current.get('unmodelled') and not plan.get('unmodelled'))
    saving = float(Decimal(str(baseline)) - Decimal(str(optimal))) if comparable else None
    return {'currency': calculation.get('currency') or values(brief).get('currency') or '未知',
            'current': current, 'plan': plan, 'current_upper': baseline, 'plan_upper': optimal,
            'current_lower': number(current, 'lower'), 'plan_lower': number(plan, 'lower'),
            'saving': saving, 'saving_pct': round(saving / baseline * 100, 2) if comparable and baseline else None,
            'comparable': comparable, 'scope': '同一公司股息、同一币种、同一日期的模型范围；未包含最终个人收款税款及重组成本',
            'gaps': calculation.get('gaps', [])}


def render_pdf(brief, target: Path, progress=lambda *_: None):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepInFrame, Flowable

    if 'BriefCJK' not in pdfmetrics.getRegisteredFontNames():
        candidates = [os.environ.get('FSIE_BRIEF_FONT_PATH', ''),
            str(Path(__file__).resolve().parents[2] / 'assets/fonts/NotoSansSC-Regular.ttf'),
            '/System/Library/Fonts/Supplemental/Songti.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc']
        font = next((Path(f) for f in candidates if f and Path(f).is_file()), None)
        if font is None:
            raise RuntimeError('brief_font_missing: configure FSIE_BRIEF_FONT_PATH with an embeddable Chinese TrueType font')
        pdfmetrics.registerFont(TTFont('BriefCJK', str(font), subfontIndex=4 if font.name == 'Songti.ttc' else 0))
    ink, muted, green, pale = (colors.HexColor(x) for x in ('#17382F', '#53685F', '#377D66', '#EFF5F0'))
    body = ParagraphStyle('BriefBody', fontName='BriefCJK', fontSize=10.3, leading=16, textColor=ink, wordWrap='CJK', spaceAfter=8)
    small = ParagraphStyle('BriefSmall', parent=body, fontSize=8, leading=12)
    heading = ParagraphStyle('BriefHeading', parent=body, fontSize=21, leading=28, spaceAfter=18)
    sub = ParagraphStyle('BriefSub', parent=body, fontSize=12.5, leading=19, spaceBefore=12, spaceAfter=8)
    def p(text, style=body):
        return Paragraph(escape(str(text)).replace('\n', '<br/>'), style)
    def section(title, lines):
        return [p(title, sub), *[p('• ' + str(s)) for s in lines if s]]
    facts, analysis, c = values(brief), brief.get('analysis', {}), comparison(brief)
    tools = [t for t in brief.get('tools', []) if t.get('input_hash') == fingerprint(brief)]
    sources = {p['unit_id']: p for t in tools for p in t.get('passages', [])}
    money = lambda v: f"{v:,.2f} {c['currency']}" if v is not None else '尚无法量化 / Not established'
    usable = c['comparable'] and facts.get('goal') == 'reinvest_company' and any(t.get('passages') for t in tools)
    status = '模型候选中的有条件方案 / Conditional option' if usable else '待验证的条件性咨询简报 / Conditional research brief'
    generated = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    class Structure(Flowable):
        def __init__(self):
            Flowable.__init__(self); self.width = 490; self.height = 108
        def draw(self):
            cv = self.canv
            labels = [facts.get('payer_jurisdiction', '未知'), facts.get('direct_holder', '未知'), facts.get('beneficiary', '未知')]
            titles = ['分红公司 / Payer', '直接股东 / Holder', '最终收款人 / Beneficiary']
            for i, (label, title) in enumerate(zip(labels, titles)):
                x = i * 170
                cv.setFillColor(pale); cv.roundRect(x, 25, 148, 68, 9, stroke=0, fill=1)
                cv.setFillColor(ink); cv.setFont('BriefCJK', 9)
                cv.drawString(x + 10, 73, title)
                cv.drawString(x + 10, 48, str(label)[:20])
                if i < 2:
                    cv.setStrokeColor(green); cv.line(x + 150, 57, x + 167, 57)
                    cv.line(x + 162, 60, x + 167, 57); cv.line(x + 162, 54, x + 167, 57)
            cv.setFont('BriefCJK', 8); cv.setFillColor(muted)
            cv.drawString(0, 7, '既有中间公司：' + str(facts.get('intermediates') or '未知')[:75])

    class TaxBars(Flowable):
        def __init__(self):
            Flowable.__init__(self); self.width = 490; self.height = 128
        def draw(self):
            cv = self.canv
            if not c['comparable']:
                cv.setFillColor(pale); cv.roundRect(0, 15, 490, 100, 8, stroke=0, fill=1)
                cv.setFont('BriefCJK', 11); cv.setFillColor(ink)
                cv.drawString(15, 78, '暂无可比较的完整税负数据')
                cv.setFont('BriefCJK', 9); cv.drawString(15, 52, '区间、未决条件和个人税款缺口见下表；不以零替代未知税款。')
                return
            maximum = max(c['current_upper'], c['plan_upper'], 1)
            for i, (label, value) in enumerate([('现状模型上界', c['current_upper']), ('候选模型上界', c['plan_upper'])]):
                y = 88 - i * 48
                cv.setFillColor(ink); cv.setFont('BriefCJK', 9); cv.drawString(0, y + 12, label)
                cv.setFillColor(green if i else muted); cv.roundRect(0, y - 8, max(1, value / maximum * 320), 12, 3, stroke=0, fill=1)
                cv.setFillColor(ink); cv.drawString(330, y - 5, money(value))

    def table(rows, widths=None):
        t = Table([[p(cell, small) for cell in row] for row in rows], colWidths=widths or [180, 310], hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), pale), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                              ('BOTTOMPADDING', (0, 0), (-1, -1), 7), ('TOPPADDING', (0, 0), (-1, -1), 7),
                              ('LINEBELOW', (0, 0), (-1, -1), .4, colors.HexColor('#DDE6DF'))]))
        return t

    labels = dict(payer_jurisdiction='分红公司所在地', amount='分红金额', currency='币种', payment_date='计划分红日期',
                  direct_holder='直接股东', holding_pct='直接持股比例', beneficiary='最终收款人',
                  beneficiary_residence='最终收款人的税务居民地', intermediates='既有中间控股公司', goal='用户资金目标')
    translations = {'CN': '中国内地', 'HK': '香港', 'SG': '新加坡', 'none': '无',
                    'personal_now': '尽快取得个人现金', 'reinvest_company': '留在公司长期投资', 'mixed': '个人收款与公司投资兼顾'}
    def fact_text(key):
        v = facts.get(key)
        if v is None: return '未知 / Unknown'
        if key == 'amount' and isinstance(v, (int, float)): return f'{v:,.2f}'
        if key == 'holding_pct': return str(v) + '%'
        return translations.get(str(v), str(v))
    facts_rows = [['信息 / Fact', '本次陈述 / User statement']]
    facts_rows += [[labels[key], fact_text(key)] for key in CORE]
    page1 = [p('01  CURRENT STATE', small), p('股息路径与当前税务状况', heading), p(status), Structure(),
             table(facts_rows), *section('现状哪里需要改善', [analysis.get('diagnosis') or '现有资料不足以认定当前结构存在税务问题；先核对各层收款人与法律条件。']),
             p('依据用户陈述整理；金额、居民地和持股情况应与原始凭证核对。', small)]
    alternatives = analysis.get('alternatives') or ['保持现有分红路径，并核对可适用待遇。', '研究香港或新加坡持股与留存投资路径，先核对商业目的、持股期限和实质。', '个人即时收款路径，需补充最终居民地个人层税额。']
    page2 = [p('02  ALTERNATIVE OPTIONS', small), p('可改变什么，哪些路径值得比较', heading),
             *section('候选路径（研究假设，非已获批安排）', alternatives),
             table([['路径', '可行性与取舍'], ['现有结构', '保持用户明确的现状；不得凭空增加公司或更改历史持股。'],
                    ['香港 / 新加坡控股', '候选适用性受受益所有人、商业实质、反滥用、居民身份、持股与重组成本影响。'],
                    ['公司留存 / 个人分配', '终点不同，不可仅以公司层税额断言个人现金路径更优。']]),
             *section('工具实际覆盖', ['引擎当前映射中港新直接公司股息及 CNY；其他地区、复杂持股或个人层税额保留缺口。',
                                        '现状工具状态：' + str(c['current'].get('status', '未完成或未覆盖')),
                                        '规划工具状态：' + str(c['plan'].get('status', '未完成或未覆盖')),
                                        '已评估候选数：' + str(c['plan'].get('candidate_count', 0)),
                                        '引擎选定安排（仅条件满足后适用）：' + json.dumps(c['plan'].get('candidate') or '尚未选定', ensure_ascii=False)])]
    page3 = [p('03  OPTIMAL STRATEGY + TAX COMPARISON', small), p('有条件建议与量化比较', heading),
             p(analysis.get('recommendation') or '先保留现有结构；仅在列明条件和完整税负核实后选择可执行路径。'),
             p('推荐状态：' + ('仅可视为模型候选中的有条件最优，仍待法律核验。' if usable else '暂不能认定最终最优方案；以下保留可核对的工具结果。')),
             TaxBars(), table([['量化项目', '工具计算值'],
               ['现状税额区间', money(c['current_lower']) + ' 至 ' + money(c['current_upper'])],
               ['规划税额区间', money(c['plan_lower']) + ' 至 ' + money(c['plan_upper'])],
               ['模型上界差额（现状 - 候选）', money(c['saving'])],
               ['模型上界差额比例', str(c['saving_pct']) + '%' if c['saving_pct'] is not None else '不可量化'],
               ['计算口径', c['scope']]]),
             p('差额 = 现状模型上界 - 候选模型上界。差额为负表示候选更贵。未知不等于零；缺少相同口径或条件未满足时不展示节税结论。'),
             p('个人所得税、后续再分配税负及实施成本均未计入；以上数字不代表用户最终净到手金额。', small)]
    unknown = [key for key, record in brief.get('facts', {}).items() if record['value'] is None]
    questions = {q['key']: q for out in (c['current'], c['plan']) for q in out.get('questions', [])}
    requirements = analysis.get('requirements') or ['核对分红日适用的法规、协定及受益所有人条件。', '核对税务居民身份证明、商业目的、经济实质、持股比例和持股期限。']
    page4 = [p('04  REQUIREMENTS', small), p('落地条件与影响结论的变量', heading),
             *section('必要核验', requirements),
             *section('用户尚未确认的信息', unknown or ['本次基础字段均已有陈述；不代表法律条件均已满足。']),
             *section('引擎待补条件', [q.get('prompt') or q['key'] for q in list(questions.values())[:12]] or ['无可自动识别的问题；仍需核对实际法域覆盖。']),
             *section('计算与法域缺口', [*c['gaps'], *[str(x) for o in (c['current'], c['plan']) for x in o.get('unmodelled', [])]][:12]
                      or ['最终个人收款税款与实施费用尚未纳入计算。'])]
    actions = analysis.get('implementation') or ['整理股权架构、居民身份证明、分红决议及预计付款日。',
        '由当地税务顾问核验每一层实体的法律待遇、反滥用要求和实施成本。', '比较同一资金终点的净到手金额，确认条件后安排决议、申报与支付。',
        '保留证明材料、税单及计算版本，事实变更后重新评估。']
    bibliography = []
    for i, source in enumerate(list(sources.values())[:10], 1):
        bibliography.append(f"[{i}] {source.get('title') or source.get('source_id')} | {source.get('locator') or source['unit_id']}\n{source.get('url') or '锁定资料库；原文位置见标识'}\nSHA-256: {source.get('text_sha256', '未提供')}")
    page5 = [p('05  IMPLEMENTATION + SOURCES', small), p('执行路线与证据记录', heading),
             *section('建议实施顺序', [f'{i + 1}. {step}' for i, step in enumerate(actions)]),
             *section('法规及工具来源', bibliography or ['本轮未取得可展示的法源；所有法条适用结论仍待取得官方资料核验。']),
             p('规则引擎版本：' + str(c['current'].get('release') or c['plan'].get('release') or '未调用 / 未覆盖'), small),
             p('咨询技能版本：' + str(brief.get('skill', {}).get('version', 1)) + ' / ' + str(brief.get('skill', {}).get('sha256', '测试快照')), small),
             p('资料快照 SHA-256：' + fingerprint(brief), small),
             p('生成时间：' + generated, small),
             p('本简报列明用户输入、候选路径、工具结果与缺口。法律适用与实施需专业复核；不保证全球最低税负。', small)]

    def footer(cv, doc):
        cv.setFillColor(ink); cv.setFont('Helvetica', 10); cv.drawString(44, 810, 'TAXRORA / DIVIDEND ADVISORY')
        cv.setStrokeColor(green); cv.line(44, 797, 551, 797)
        cv.setFillColor(muted); cv.setFont('BriefCJK', 8)
        cv.drawString(44, 27, '咨询研究稿 - 条件与来源随报告保留')
        cv.drawRightString(551, 27, f'{doc.page} / 5')
    story = []
    for i, page in enumerate([page1, page2, page3, page4, page5]):
        progress(35 + i * 11, ['编排现状与结构图', '整理候选路径', '绘制税负比较', '整理实施条件', '整理行动步骤和来源'][i])
        story.append(KeepInFrame(490, 738, page, mode='shrink', hAlign='LEFT', vAlign='TOP'))
        if i < 4: story.append(PageBreak())
    target.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(target), pagesize=A4, topMargin=57, bottomMargin=40, leftMargin=44, rightMargin=44,
                      title='Taxrora Dividend Consultation Brief', author='Taxrora').build(story, onFirstPage=footer, onLaterPages=footer)
