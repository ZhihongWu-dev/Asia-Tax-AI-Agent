"""Deterministic review record from a verified, saved assessment snapshot."""
from hashlib import sha256
from html import escape
import json
import re
from urllib.parse import quote, urlsplit


def _text(value):
    return re.sub(r'([\\`*{}\[\]()#+.!_|>\-])', r'\\\1', escape(str(value)).replace('\n', ' ').replace('\r', ' '))


def _json(value):
    content = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
    fence = '`' * max(3, 1 + max((len(s) for s in re.findall(r'`+', content)), default=0))
    return f'{fence}json\n{content}\n{fence}'


def render(run, locale='zh'):
    if locale not in ('zh', 'en'):
        raise ValueError('unsupported_report_locale')
    snapshot = {key: run[key] for key in ('inputs', 'basis', 'result')}
    digest = sha256(json.dumps(snapshot, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if digest != run['snapshot_hash']:
        raise ValueError('assessment_snapshot_mismatch')
    say = lambda zh, en: en if locale == 'en' else zh
    inputs, result = snapshot['inputs'], snapshot['result']
    lines = ['# ' + say('所得税计算记录', 'Income-tax calculation record'), '',
        say('此记录重现已保存的计算，不代表完成申报或专业审核。适用范围、资格和取整方式以所保存的计税依据及结果为准；不包含其后修改的资料。',
            'This record reproduces a saved calculation, not a completed return or professional approval. Scope, eligibility and rounding follow the saved basis and result. Later edits are not included.'), '',
        '## ' + say('案例与期间', 'Case and period'), '',
        '| ' + say('项目 | 内容', 'Item | Value') + ' |', '| --- | --- |']
    for label, value in [(say('税区', 'Jurisdiction'), inputs['jurisdiction'].upper()),
            (say('主体', 'Taxpayer'), say('企业', 'Company') if inputs['subject']=='company' else say('个人', 'Individual')),
            (say('期间', 'Period'), inputs['period_start'] + ' / ' + inputs['period_end']),
            (say('币种', 'Currency'), inputs['currency'])]:
        lines.append(f'| {_text(label)} | {_text(value)} |')
    if result.get('tax_scope') == 'japan_three_national_company_taxes_only':
        lines += ['', say('范围：仅日本企业三项国税，不含地方住民税、事业税或最低补足税。',
            'Scope: three Japanese national company taxes only; excludes local inhabitant, enterprise and minimum top-up taxes.')]
    if result.get('tax_scope') == 'national_income_and_reconstruction_tax_only':
        lines += ['', say('范围：仅日本国家所得税及复兴特别所得税，不含地方住民税及事业税。',
            'Scope: Japanese national income and reconstruction taxes only; excludes local inhabitant and enterprise taxes.')]
    lines += ['', '## ' + say('计算摘要', 'Calculation summary'), '',
        '| ' + say('项目 | 金额', 'Item | Amount') + ' |', '| --- | --- |']
    for key, zh, en in [('taxable_income','应纳税所得额','Taxable income'),
            ('chargeable_income','应课税收入','Chargeable income'),
            ('gross_tax','减免及抵免前税额','Tax before relief'),
            ('annual_liability','本期税额','Annual liability'),
            ('final_tax','本期最终税额','Final tax'), ('net_tax','减免后税额','Tax after relief'),
            ('total_payable','分别应缴合计（不与应退互抵）','Total payable (not netted against refunds)'),
            ('total_refundable','分别应退合计（不与应缴互抵）','Total refundable (not netted against payments)'),
            ('balance_due','补退余额（负数表示多缴）','Balance (negative means overpaid)'),
            ('corporation_balance_due','法人税补退余额','Corporation-tax balance'),
            ('local_corporation_balance_due','地方法人税补退余额','Local corporation-tax balance')]:
        if key in result:
            lines.append(f'| {_text(say(zh,en))} | {_text(result[key])} |')
    if result.get('tokyo_local'):
        local = result['tokyo_local']
        lines += ['', '## ' + say('东京23区地方税明细', 'Tokyo 23-ward local tax details'), '',
            say('仅限全年全部办公地点位于东京23区的普通内国法人。上表应缴及应退合计为国家税；地方税另列如下，各税种不自动互抵。',
                'Ordinary domestic companies with all offices in Tokyo 23 wards throughout the full year only. Payable and refundable totals above are national taxes; local amounts are listed separately below, without automatic cross-tax offsets.'), '',
            '| ' + say('税种 | 年度税额 | 中间申告义务 | 补退余额', 'Tax | Annual tax | Interim liability | Payment or refund balance') + ' |',
            '| --- | --- | --- | --- |']
        for key, zh, en in [('enterprise','事业税','Enterprise tax'),
                ('special_enterprise','特别法人事业税','Special enterprise tax'),
                ('inhabitant','住民税法人税割','Inhabitant levy'),
                ('per_capita','住民税均等割','Per-capita levy')]:
            values = [say(zh,en), local['local_tax_components'][key],
                local['local_interim_liabilities'][key], local['local_balances'][key]]
            lines.append('| ' + ' | '.join(_text(v) for v in values) + ' |')
        lines += ['', '| ' + say('项目 | 金额', 'Item | Amount') + ' |', '| --- | --- |']
        for key, zh, en in [('local_final_tax','地方税年度合计','Local annual tax total'),
                ('local_amounts_payable','地方税应补合计','Local amounts payable'),
                ('local_refunds','地方税应退合计','Local refund amounts')]:
            lines.append(f'| {_text(say(zh,en))} | {_text(local[key])} |')
    if result.get('tax_scope') == 'china_resident_ordinary_direct_foreign_credit_positive_bases':
        lines += ['', '## ' + say('境外直接抵免明细', 'Direct foreign credit details'), '',
            say('仅普通25%税率居民企业直接抵免及非负逐国税基；不含间接、饶让抵免或其他优惠。历史余额保留原始年度；本期到期未用金额不可结转。',
                'Ordinary 25% resident company direct credits and nonnegative country bases only; excludes indirect/deemed credits and other reliefs. Original excess years are preserved; unused amounts expiring this year cannot carry forward.'), '',
            say('抵免方式：', 'Credit method: ') + (say('不分国不分项', 'Pooled foreign income') if result['method']=='pooled' else say('分国不分项', 'Per country'))]
        for pool in result['pools']:
            label = say('综合抵免池', 'Pooled credit') if pool['pool']=='all_foreign' else pool['pool'].upper()
            lines += ['', '### ' + _text(label), '', '| ' + say('项目 | 金额', 'Item | Amount') + ' |', '| --- | --- |']
            for key, zh, en in [('taxable_income','应税所得','Taxable income'),('credit_limit','抵免限额','Credit limit'),
                    ('current_credit_used','当年税额抵免','Current credit used'),('prior_credit_used','历史余额抵免','Prior credit used'),
                    ('allowed_credit','抵免合计','Total credit allowed'),('current_excess','当年新增超限额','New current-year excess'),
                    ('current_excess_last_usable_year','新增余额最后可用年度','New excess last usable year')]:
                lines.append(f'| {_text(say(zh,en))} | {_text(pool[key])} |')
            if pool['carryforward_history']:
                lines += ['', '| ' + say('国家 | 原始年度 | 最后可用年度 | 期初余额 | 本期使用 | 本期前已失效 | 本期结束失效 | 下一年结转',
                    'Country | Origin year | Last usable year | Opening excess | Used this year | Previously expired | Expires after current year | Next-year carryforward') + ' |',
                    '| --- | --- | --- | --- | --- | --- | --- | --- |']
                for row in pool['carryforward_history']:
                    values = [row['country'].upper()] + [row[k] for k in ('origin_year','last_usable_year','opening_excess','credit_used','expired_amount','expires_after_current_year','next_year_carryforward')]
                    lines.append('| ' + ' | '.join(_text(v) for v in values) + ' |')
    if result.get('tax_scope') == 'china_resident_ordinary_comprehensive_business_investment_foreign_credit':
        lines += ['', '## ' + say('个人境外抵免明细', 'Personal foreign credit details'), '',
            say('普通综合所得、非负经营税基及普通20%利息股息；限额先扣除各类核定减免税额。全年合计包括境内普通利息股息税额，不等同于B表申报金额。已核定普通财产转让按逐笔工作表另计；不含租赁、特殊奖金股权或饶让抵免。历史余额仅在同国剩余限额内使用，本期到期未用金额不可结转。',
                'Ordinary comprehensive income, nonnegative business bases and ordinary20% interest/dividends; limits reflect verified category reductions. The full-year total includes domestic ordinary investment tax and is not a B-form filing amount. Established ordinary property transfers use separate transaction workpapers. Excludes rental, special bonuses/equity and deemed credits. Prior credits use remaining capacity in the same country; unused amounts expiring this year cannot carry forward.')]
        for pool in result['country_limits']:
            label = pool['country'].upper()
            lines += ['', '### ' + _text(label), '', '| ' + say('项目 | 金额', 'Item | Amount') + ' |', '| --- | --- |']
            for key, zh, en in [('comprehensive_credit_limit','综合所得限额','Comprehensive credit limit'),
                    ('business_credit_limit','经营所得限额','Business credit limit'),
                    ('other_category_credit_limit','其他分类所得限额','Other category credit limit'),('credit_limit','国别限额合计','Country credit limit'),
                    ('current_credit_used','当年税额抵免','Current credit used'),('prior_credit_used','历史余额抵免','Prior credit used'),
                    ('allowed_credit','抵免合计','Total credit allowed'),('current_excess','当年新增超限额','New current-year excess'),
                    ('current_excess_last_usable_year','新增余额最后可用年度','New excess last usable year')]:
                lines.append(f'| {_text(say(zh,en))} | {_text(pool[key])} |')
            if pool['carryforward_history']:
                lines += ['', '| ' + say('国家 | 原始年度 | 最后可用年度 | 期初余额 | 本期使用 | 本期前已失效 | 本期结束失效 | 下一年结转',
                    'Country | Origin year | Last usable year | Opening excess | Used this year | Previously expired | Expires after current year | Next-year carryforward') + ' |',
                    '| --- | --- | --- | --- | --- | --- | --- | --- |']
                for row in pool['carryforward_history']:
                    values = [pool['country'].upper()] + [row[k] for k in ('origin_year','last_usable_year','opening_excess','credit_used','expired_amount','expires_after_current_year','next_year_carryforward')]
                    lines.append('| ' + ' | '.join(_text(v) for v in values) + ' |')
    lines += ['', '## ' + say('保存的官方来源', 'Saved official sources'), '']
    sources = result.get('sources') or ([result['source']] if result.get('source') else [])
    for source in sources:
        title = _text(source.get('title') or source.get('doc_id') or say('来源', 'Source'))
        url = source.get('url', '')
        parsed = urlsplit(url)
        if parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username:
            target = quote(url, safe=':/?&=%#@+;,$!~.-_')
            lines.append(f'- [{title}]({target})')
        else:
            lines.append('- ' + title)
        if source.get('sha256'):
            lines.append('  SHA-256: ' + _text(source['sha256']))
    if not sources:
        lines.append(say('此快照未保存来源链接；请复核下方完整结果。', 'No source links were saved in this snapshot; review the complete result below.'))
    lines += ['', '## ' + say('完整资料、计税依据与结果', 'Complete inputs, basis and result'), '',
        _json(snapshot), '', '## ' + say('记录标识', 'Record references'), '',
        _json({key: run[key] for key in ('id', 'case_id', 'input_revision', 'created_at', 'status', 'snapshot_hash')}), '']
    return '\n'.join(lines)
