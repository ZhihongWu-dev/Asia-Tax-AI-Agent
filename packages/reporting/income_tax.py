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
    if result.get('policy_version') in ('kr-company-direct-foreign-2026-20261122', 'kr-company-direct-foreign-history-2026-20261122', 'kr-company-direct-foreign-balances-2026-20261122'):
        lines += ['', '## ' + say('韩国分国抵免与地方税', 'Korean country credits and local tax'), '',
            say('国税、地方税分别结算。费用对应超限额与普通抵免结转分开列示。历史国税抵免与历史地方税扣除仅按下表各自核实的余额处理，不能互相复制；不含到期国税抵免扣除、其他国税减免、间接抵免或特殊税负。',
                'National and local authorities settle separately. Expense-related excess is separate from ordinary credit carryforward. Historical national credits and local deductions use their separately verified balances below and cannot be copied between ledgers. Excludes expired national-credit deductions, competing national reliefs, underlying credits and special taxes.'), '',
            '| ' + say('国家 | 限额所得 | 抵免限额 | 本期抵免 | 费用对应超限额（不作普通结转） | 普通抵免结转',
                'Country | Limit income | Credit limit | Current credit | Expense-related excess (not ordinary carry) | Ordinary credit carryforward') + ' |',
            '| --- | --- | --- | --- | --- | --- |']
        for row in result['foreign_credit']['country_credits']:
            values = [row['country'].upper()] + [row[k] for k in ('income_for_credit_limit', 'credit_limit',
                'current_foreign_tax_credit', 'expense_related_excess_not_carried', 'eligible_current_year_carryforward')]
            lines.append('| ' + ' | '.join(_text(v) for v in values) + ' |')
        lines += ['', '| ' + say('项目 | 金额', 'Item | Amount') + ' |', '| --- | --- |']
        for key, zh, en in [('current_local_foreign_tax_deduction', '地方税税基境外税扣除', 'Foreign-tax deduction from local base'),
                ('local_taxable_base', '地方税税基（取整前）', 'Local taxable base before rounding'),
                ('excess_current_local_deduction', '地方税扣除结转余额', 'Local deduction carryforward')]:
            lines.append(f'| {_text(say(zh,en))} | {_text(result["local_basis"][key])} |')
        lines += ['', '| ' + say('机关 | 应缴 | 应退', 'Authority | Payable | Refundable') + ' |', '| --- | --- | --- |']
        settlements = [(say('国税', 'National'), result['national']['settlement'])]
        settlements += [(name, row['settlement']) for name, row in result['local']['filings'].items()]
        for name, cash in settlements:
            lines.append('| ' + ' | '.join(_text(v) for v in (name, cash['payable'], cash['refundable'])) + ' |')
        if result.get('historical_foreign_credit'):
            lines += ['', '### ' + say('历史国税抵免余额', 'Historical national credit balances'), '',
                '| ' + say('编号 | 国家 | 核实到期日 | 本期使用 | 本期使用后未用余额',
                    'Reference | Country | Verified expiry | Used this period | Unused after current allocation') + ' |',
                '| --- | --- | --- | --- | --- |']
            for row in result['historical_foreign_credit']['historical_lots']:
                lines.append('| ' + ' | '.join(_text(row[k]) for k in ('identifier','country','expiry_date','used','remaining')) + ' |')
        if result['local_basis'].get('historical_local_deductions'):
            lines += ['', '### ' + say('历史地方税扣除余额', 'Historical local deduction balances'), '',
                '| ' + say('编号 | 类别 | 原发生额 | 以前已扣 | 本期扣除 | 结转排除 | 下期结转',
                    'Reference | Kind | Original amount | Previously deducted | Current deduction | Excluded carry | Next carryforward') + ' |',
                '| --- | --- | --- | --- | --- | --- | --- |']
            for row in result['local_basis']['historical_local_deductions']:
                lines.append('| ' + ' | '.join(_text(row[k]) for k in ('identifier','kind','original_amount','previously_deducted','current_deduction','excluded_from_next_carry','next_carryforward')) + ' |')
    if result.get('policy_version') == 'vn-company-foreign-ordinary20-2026-20261122':
        lines += ['', '## ' + say('越南境外抵免明细', 'Vietnam foreign credit details'), '',
            say('普通20%税率且不适用低营业额年度减税。视同税与实缴税分开，按同项越南税额限额；超限额不自动批准结转。金额为申报取整前值。',
                'Ordinary 20% rate outside low-revenue annual relief. Deemed and paid tax are separate, capped at Vietnamese tax on the same income. Excess does not automatically establish a carryforward. Before filing rounding.'), '',
            '| ' + say('来源 | 国家 | 方法 | 净所得 | 实缴税 | 抵免依据 | 限额 | 已用抵免',
                'Source | Country | Method | Net income | Paid tax | Credit basis | Limit | Credit used') + ' |',
            '| --- | --- | --- | --- | --- | --- | --- | --- |']
        for row in result['source_credits']:
            lines.append('| ' + ' | '.join(_text(row[k]) for k in ('source_id','country','method',
                'net_taxable_income','foreign_tax_paid','credit_basis','vietnam_same_income_limit','allowed_credit')) + ' |')
        lines += ['', '| ' + say('项目 | 金额', 'Item | Amount') + ' |', '| --- | --- |']
        for key,zh,en in [('allowed_foreign_tax_credit','境外抵免合计','Total foreign credit'),('prepaid_tax','境内预缴税款','Domestic prepaid tax')]:
            lines.append(f'| {_text(say(zh,en))} | {_text(result[key])} |')
    if result.get('policy_version') == 'sg-company-foreign-direct-ya2026-20261122':
        credit = result['foreign_credit']
        lines += ['', '## ' + say('新加坡境外直接抵免明细', 'Singapore direct foreign credit details'), '',
            say('逐来源与国家核算限额；合资格收入可选择汇总。先抵免再计算回扣，现金补助不重复冲减余额。金额尚未申报取整。',
                'Caps apply by source and country; elected qualifying income is pooled separately. Credit precedes the CIT rebate. The separate cash grant is not deducted again from the balance. Amounts precede filing rounding.'), '',
            '| ' + say('来源 | 国家 | 新加坡税额上限 | 合资格境外税 | 汇总 | 单项抵免',
                'Source | Country | Singapore tax limit | Eligible foreign tax | Pooled | Individual credit') + ' |',
            '| --- | --- | --- | --- | --- | --- |']
        for row in credit['sources']:
            values = [row['source_id'], row['country'].upper(), row['singapore_tax_limit'],
                row['eligible_foreign_tax'], say('是','Yes') if row['pool_elected'] else say('否','No'),
                say('计入汇总','Included in pool') if row['individual_credit'] is None else row['individual_credit']]
            lines.append('| ' + ' | '.join(_text(v) for v in values) + ' |')
        lines += ['', '| ' + say('项目 | 金额', 'Item | Amount') + ' |', '| --- | --- |']
        for data,key,zh,en in [(credit,'pooled_singapore_tax_limit','汇总抵免上限','Pooled credit limit'),
                (credit,'pooled_foreign_tax','汇总境外税款','Pooled foreign tax'),
                (credit,'pooled_credit','汇总抵免额','Pooled credit'),
                (result,'allowed_tax_setoff','境外抵免合计','Total foreign credit'),
                (result,'tax_before_rebate','抵免后回扣前税额','Tax after credit before rebate'),
                (result,'cit_rebate','企业税回扣','CIT rebate'),
                (result,'cash_grant_separate','单列现金补助','Separate cash grant'),
                (result,'prepaid_tax','预缴税款','Prepaid tax')]:
            lines.append(f'| {_text(say(zh,en))} | {_text(data[key])} |')
    if result.get('policy_version') == 'ae-ordinary-foreign-credit-20261122':
        lines += ['', '## ' + say('阿联酋逐项境外抵免', 'UAE income-by-income foreign credit'), '',
            say('按每项境外净所得分摊本国税额限额。未用境外税款不得跨来源抵扣、结转或作为费用扣除。以下金额为申报取整前值。',
                'Each net foreign source has its own allocated UAE tax limit. Unused foreign tax cannot offset another source, carry forward or back, or be deducted as an expense. Values precede filing rounding.'), '',
            '| ' + say('来源 | 国家 | 净所得 | 合资格境外税 | 抵免限额 | 已用抵免 | 不可结转余额',
                'Source | Country | Net income | Eligible foreign tax | Credit limit | Credit used | Forfeited excess') + ' |',
            '| --- | --- | --- | --- | --- | --- | --- |']
        for row in result['source_credits']:
            values = [row['source_id'], row['country'].upper(), row['net_taxable_income'],
                row['eligible_foreign_tax'], row['credit_limit'], row['credit_used'], row['forfeited_excess']]
            lines.append('| ' + ' | '.join(_text(v) for v in values) + ' |')
        lines += ['', '| ' + say('项目 | 金额', 'Item | Amount') + ' |', '| --- | --- |']
        for key,zh,en in [('allowed_foreign_tax_credit','境外抵免合计','Total foreign credit'),
                ('forfeited_excess','不可结转余额合计','Total forfeited excess'),
                ('prepaid_tax','预缴税款','Prepaid tax')]:
            lines.append(f'| {_text(say(zh,en))} | {_text(result[key])} |')
    if result.get('policy_version') == 'my-schedule7-direct-credit-20261122':
        lines += ['', '## ' + say('马来西亚双边及单边抵免', 'Malaysia bilateral and unilateral credits'), '',
            say('按来源分摊法定所得；单边抵免另受合资格境外税额一半的限制。逐项金额尚未应用总税额上限，总额调整另列；未抵免税额不结转。金额为申报取整前值。',
                'Statutory income is allocated by source. Unilateral credit is also limited to half the eligible foreign tax. Source amounts precede the overall tax cap, whose adjustment is shown separately. Unrelieved tax is not carried forward. Values precede filing rounding.'), '',
            '| ' + say('来源 | 征税国家 | 方法 | 分摊法定所得 | 合资格境外税 | 境外税上限 | 本国税上限 | 总额限制前抵免',
                'Source | Taxing country | Method | Allocated statutory income | Eligible foreign tax | Foreign-tax limit | Malaysian-tax limit | Credit before overall cap') + ' |',
            '| --- | --- | --- | --- | --- | --- | --- | --- |']
        for row in result['source_credits']:
            method = say('双边', 'Bilateral') if row['method'] == 'bilateral' else say('单边', 'Unilateral')
            values = [row['source_id'], row['taxing_country'].upper(), method,
                row['allocated_statutory_income'], row['eligible_foreign_tax'], row['foreign_tax_limit'],
                row['malaysian_tax_limit'], row['credit_before_overall_cap']]
            lines.append('| ' + ' | '.join(_text(v) for v in values) + ' |')
        lines += ['', '| ' + say('项目 | 金额', 'Item | Amount') + ' |', '| --- | --- |']
        for key,zh,en in [('allowed_foreign_tax_credit','境外抵免合计','Total foreign credit'),
                ('overall_cap_reduction','总税额上限调减','Overall cap reduction'),
                ('unrelieved_foreign_tax','未获抵免境外税额','Unrelieved foreign tax'),
                ('prepaid_tax','预缴税款','Prepaid tax')]:
            lines.append(f'| {_text(say(zh,en))} | {_text(result[key])} |')
    if result.get('policy_version') == 'id-article24-credit-20261122':
        lines += ['', '## ' + say('印尼分国分类境外抵免', 'Indonesia foreign credits by country and income type'), '',
            say('逐项抵免尚未应用总税额上限；总额调减及以前已抵免税款补回另列。未抵免税款不得作为费用或申请退税。金额为申报取整前值。',
                'Source credits precede the overall tax cap. Its reduction and recapture of previously credited tax are separate. Unrelieved foreign tax cannot become an expense deduction or refund. Values precede return rounding.'), '',
            '| ' + say('国家 | 所得类别 | 净所得 | 境外税额 | 条约上限 | 本国税上限 | 总额限制前抵免',
                'Country | Income type | Net income | Foreign tax | Treaty ceiling | Indonesian-tax limit | Credit before overall cap') + ' |',
            '| --- | --- | --- | --- | --- | --- | --- |']
        for row in result['source_credits']:
            values = [row['country'].upper(), row['category'], row['net_taxable_income'], row['foreign_tax'],
                row['treaty_permitted_tax'] if row['treaty_permitted_tax'] is not None else say('不适用','Not applicable'),
                row['indonesian_tax_limit'], row['credit_before_overall_cap']]
            lines.append('| ' + ' | '.join(_text(v) for v in values) + ' |')
        lines += ['', '| ' + say('项目 | 金额', 'Item | Amount') + ' |', '| --- | --- |']
        for key,zh,en in [('allowed_foreign_tax_credit','境外抵免合计','Total foreign credit'),
                ('overall_cap_reduction','总额限制调减','Overall cap reduction'),
                ('prior_credit_recapture','以前抵免补回','Prior-credit recapture'),
                ('prepaid_tax','境内预缴税款','Domestic prepaid tax')]:
            lines.append(f'| {_text(say(zh,en))} | {_text(result[key])} |')
    if result.get('foreign_credit_reconciliation') and 'rd300' in result.get('policy_version', ''):
        lines += ['', '## ' + say('泰国企业境外税款与费用核对', 'Thai company foreign tax and expense reconciliation'), '',
            say('按第300号法令及已确认的最终费用口径核对；已抵免税款不得重复扣除。费用资格由使用者确认，未自动推定。协定路径及中小企业规则需另行计算。',
                'RD300 reconciliation uses confirmed final expense bases. Credited tax cannot also be deducted. Expense eligibility is user verified, not inferred. Treaty elections and SME rules require separate calculations.'), '',
            '| ' + say('国家 | 收入总额 | 境外已缴税 | 年度费用 | 费用中的境外税 | 抵免额 | 未抵免未扣除税额',
                'Country | Gross income | Foreign tax paid | Annual expenses | Foreign tax in expenses | Exemption | Uncredited and undeducted tax') + ' |',
            '| --- | --- | --- | --- | --- | --- | --- |']
        for row in result['foreign_credit_reconciliation']['country_reconciliation']:
            values = [row['country'].upper(), row['gross_income'], row['foreign_tax_paid'],
                row['annual_allowable_expenses'], row['foreign_tax_in_annual_expenses'],
                row['rd300_exemption'], row['uncredited_and_undeducted_foreign_tax']]
            lines.append('| ' + ' | '.join(_text(v) for v in values) + ' |')
        allocations = [(row['country'], entry) for row in result['foreign_credit_reconciliation']['country_reconciliation']
            for entry in row.get('business_tax_period_allocations', [])]
        if allocations:
            lines += ['', '### ' + say('境外经营税款期间分摊', 'Foreign business tax period allocation'), '',
                '| ' + say('国家 | 凭证 | 所得年度结束日 | 税款支付日 | 归属本期税款 | 需更正原申报',
                    'Country | Evidence | Income period end | Tax payment date | Tax allocated to this period | Original return amendment required') + ' |',
                '| --- | --- | --- | --- | --- | --- |']
            for country, entry in allocations:
                amendment = entry['amendment_required']
                status = say('待确认原申报日期', 'Original filing date unknown') if amendment is None else (say('是', 'Yes') if amendment else say('否', 'No'))
                values = [country.upper(), entry['evidence_reference'], entry['thai_period_end'], entry['payment_date'],
                    entry['allocated_tax_before_credit_limits'], status]
                lines.append('| ' + ' | '.join(_text(v) for v in values) + ' |')
    if result.get('policy_version') in ('in-company-foreign-ty2026-27-20261122', 'in-company-foreign-ty2026-27-20261122-treaty-scope'):
        lines += ['', '## ' + say('印度企业境外抵免', 'Indian company foreign tax credits'), '',
            say('来源税额和资格依据已保存的核定工作表；普通税额与最低税额的抵免分别计算。本表不自动认定费用、协定或申报资格，余额尚未加入利息及费用。',
                'Source tax and eligibility follow the saved verified workpaper. Normal and minimum-tax credits are calculated separately. Expense, treaty and filing eligibility are not inferred; the balance excludes interest and fees.'), '',
            '| ' + say('来源 | 国家 | 境外已缴税 | 排除的争议税 | 普通税制抵免 | 最低税额抵免',
                'Source | Country | Foreign tax paid | Disputed tax excluded | Normal credit | Section206 credit') + ' |',
            '| --- | --- | --- | --- | --- | --- |']
        for row in result['foreign_credit']['source_credits']:
            values = [row['source_id'], row['country'].upper(), row['foreign_tax_paid_inr'],
                row['disputed_tax_excluded_inr'], row['normal_credit'],
                row['section206_credit'] if row['section206_credit'] is not None else say('不适用', 'Not applicable')]
            lines.append('| ' + ' | '.join(_text(v) for v in values) + ' |')
        lines += ['', '| ' + say('项目 | 金额', 'Item | Amount') + ' |', '| --- | --- |']
        for key,zh,en in [('annual_tax_before_foreign_credit','抵免前年度税额','Annual tax before foreign credit'),
                         ('allowed_foreign_tax_credit','本次适用境外抵免','Foreign credit applied'),
                         ('prepaid_tax','本期已核实预缴','Verified period prepayments')]:
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
    if result.get('osaka_local'):
        local = result['osaka_local']
        lines += ['', '## ' + say('大阪市地方税明细', 'Osaka city local tax details'), '',
            say('仅限全年全部办公地点位于大阪市的普通内国法人。上表应缴及应退合计为国家税；地方税另列如下，各税种不自动互抵。',
                'Ordinary domestic companies with all offices in Osaka city throughout the full year only. Payable and refundable totals above are national taxes; local amounts are listed separately below, without automatic cross-tax offsets.'), '',
            '| ' + say('税种 | 年度税额 | 中间申告义务 | 补退余额', 'Tax | Annual tax | Interim liability | Payment or refund balance') + ' |',
            '| --- | --- | --- | --- |']
        for key, zh, en in [('enterprise','事业税','Enterprise tax'),
                ('special_enterprise','特别法人事业税','Special enterprise tax'),
                ('prefectural_inhabitant','大阪府法人税割','Prefectural inhabitant levy'),
                ('city_inhabitant','大阪市法人税割','City inhabitant levy'),
                ('prefectural_capitation','大阪府均等割','Prefectural per-capita levy'),
                ('city_capitation','大阪市均等割','City per-capita levy')]:
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
    if result.get('property_transfers'):
        lines += ['', '## ' + say('逐笔财产转让明细', 'Property transfer transaction details'), '',
            say('每笔收入为转让总收入，不是净收益；单笔未抵扣亏损不自动抵减其他交易。来源地、普通税率、原值和优惠资格以已确认工作表为准。',
                'Each income is gross transfer proceeds, not net gain. Unoffset losses do not automatically reduce other transactions. Source classification, ordinary rate, cost and relief eligibility follow the confirmed workpaper.')]
        for row in result['property_transfers']['transactions']:
            lines += ['', '### ' + say('收入 ', 'Income ') + str(row['income_index']+1) + ' / ' + _text(row['country'].upper()), '',
                '| ' + say('项目 | 金额', 'Item | Amount') + ' |', '| --- | --- |']
            for key, zh, en in [('gross_proceeds','转让收入','Gross proceeds'),('original_cost','财产原值','Original cost'),
                    ('reasonable_transfer_expenses','合理费用','Reasonable expenses'),('gain_before_donation','捐赠前损益','Gain before donation'),
                    ('unoffset_loss','未抵扣亏损','Unoffset loss'),('allowed_donation','核定捐赠扣除','Allowed donation'),
                    ('taxable_income','应税所得','Taxable income'),('gross_tax','减免前税额','Tax before reduction'),
                    ('allowed_tax_reduction','核定减免税额','Allowed tax reduction'),('tax_after_reduction','减免后税额','Tax after reduction')]:
                lines.append(f'| {_text(say(zh,en))} | {_text(row[key])} |')
    if result.get('property_rentals'):
        # Earlier personal summaries predate rental support; preserve them for
        # historical snapshots while correcting the scope for rental results.
        lines = [line.replace('不含租赁、特殊奖金股权', '另含已核定普通租赁；不含特殊奖金股权')
                 .replace('Excludes rental, special bonuses/equity', 'Includes established ordinary rental. Excludes special bonuses/equity') for line in lines]
        lines += ['', '## ' + say('逐月财产租赁明细', 'Monthly property rental details'), '',
            say('按已确认的月份、来源地和普通20%税率计算。修缮费发生额与当期扣除额分别列示；未用余额不自动作为本期扣除。住房优惠、预收租金分摊和费用资格不自动推定。',
                'Uses established monthly allocation, source and ordinary20% rate. Repairs incurred and deductions used are distinct; unused balances are not current deductions. Housing relief, advance-rent allocation and expense eligibility are not inferred.')]
        for prop in result['property_rentals']['properties']:
            lines += ['', '### ' + _text(prop['property_id']) + ' / ' + _text(prop['country'].upper()), '']
            ledger = {r['month']: r for r in prop['repair_ledger']['months']}
            for row in prop['months']:
                lines += ['', '#### ' + say('月份 ', 'Month ') + str(row['month']), '',
                    '| ' + say('项目 | 金额', 'Item | Amount') + ' |', '| --- | --- |']
                for key, zh, en in [('gross_income','租赁收入','Rental income'),
                        ('eligible_taxes_and_fees','核定税费扣除','Established taxes and fees'),
                        ('eligible_sublease_rent','核定转租租金','Established sublease rent'),
                        ('eligible_new_repairs','新增合格修缮费','New eligible repairs'),
                        ('established_repair_deduction','本月修缮费扣除','Repair deduction used'),
                        ('balance_before_statutory_expense','法定费用扣除前余额','Balance before statutory expense'),
                        ('statutory_expense','法定费用扣除','Statutory expense'),
                        ('allowed_donation','核定捐赠扣除','Allowed donation'),
                        ('taxable_income','应税所得','Taxable income'),
                        ('gross_tax','减免前税额','Tax before reduction'),
                        ('allowed_tax_reduction','核定减免税额','Allowed tax reduction'),
                        ('tax_after_reduction','减免后税额','Tax after reduction')]:
                    lines.append(f'| {_text(say(zh,en))} | {_text(row[key])} |')
                repair = ledger[row['month']]
                for key, zh, en in [('opening_eligible_repairs','期初修缮费余额','Opening repair balance'),
                        ('closing_eligible_repairs','期末修缮费余额','Closing repair balance')]:
                    lines.append(f'| {_text(say(zh,en))} | {_text(repair[key])} |')
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
