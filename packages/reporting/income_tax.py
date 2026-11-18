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
