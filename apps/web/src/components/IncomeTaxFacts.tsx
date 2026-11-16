import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api";
import { useLocale } from "../locale";
import type { Case } from "../workspace";
import { blankIncome, blankIncomeTax, incomeCategories, taxJurisdictions,
  type IncomeTaxInput, type TaxJurisdiction } from "../income-tax";

export default function IncomeTaxFacts({ current, busy, onUpdate }: {
  current: Case; busy: boolean; onUpdate: (doc: Case) => void;
}) {
  const { locale } = useLocale();
  const say = (zh: string, en: string) => locale === "en" ? en : zh;
  const [form, setForm] = useState<IncomeTaxInput>(() => structuredClone(current.income_tax || blankIncomeTax()));
  const [revision, setRevision] = useState(current.revision);
  const [conflict, setConflict] = useState(false);
  const [saving, setSaving] = useState(false), [error, setError] = useState(""), [saved, setSaved] = useState(false);
  const mounted = useRef(true), retry = useRef({ payload: "", id: "" });
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  function edit(patch: Partial<IncomeTaxInput>) {
    setForm(previous => ({ ...previous, ...patch, facts_confirmed: false })); setSaved(false); setError("");
  }
  function changeJurisdiction(next: TaxJurisdiction) {
    if (next === form.jurisdiction) return;
    if (form.incomes.some(item => item.gross_amount !== "" || item.foreign_tax_paid !== null) ||
        form.claimed_deductions !== null || form.carried_losses !== null) {
      setError(say("请先清空金额或新建案例，再切换税区。已填金额不会自动换算。", "Clear monetary amounts or create another case before changing jurisdiction. Amounts are not automatically converted.")); return;
    }
    edit({ jurisdiction: next, currency: taxJurisdictions[next][2],
      incomes: form.incomes.map(item => !item.description && !item.gross_amount && item.foreign_tax_paid === null
        ? { ...item, source_jurisdiction: next } : item) });
  }
  async function save(event: React.FormEvent) {
    event.preventDefault(); setError(""); setSaved(false);
    if (form.period_end < form.period_start) { setError(say("结束日期不能早于开始日期。", "End date must not precede start date.")); return; }
    if (form.subject === "company" && form.incomes.some(item => item.category === "employment")) {
      setError(say("企业收入不能归类为工资薪金，请核对收入类别。", "A company's income cannot be classified as employment income.")); return;
    }
    const payload = JSON.stringify([revision, form]);
    if (retry.current.payload !== payload) retry.current = { payload, id: crypto.randomUUID() };
    setSaving(true);
    try {
      await api.saveIncomeTax(current.id, revision, form, retry.current.id);
      const next = await api.get(current.id);
      if (mounted.current) {
        onUpdate(next); setRevision(next.revision); setConflict(false);
        setForm(structuredClone(next.income_tax || form)); setSaved(true);
      }
    } catch (e) {
      if (mounted.current && e instanceof ApiError && e.code === "revision_conflict") setConflict(true);
      if (mounted.current) setError(e instanceof ApiError && e.code === "revision_conflict"
        ? say("案例已在别处更新。当前填写内容仍保留，请核对后重新载入已保存资料。", "The case changed elsewhere. Your entries are retained. Review them before reloading saved details.")
        : say("保存未完成，请检查填写内容后重试。当前内容仍保留。", "Save did not complete. Check the entries and retry; your entries are retained."));
    } finally { if (mounted.current) setSaving(false); }
  }
  async function reload() {
    setSaving(true); setError("");
    try {
      const next = await api.get(current.id);
      if (mounted.current) { onUpdate(next); setRevision(next.revision); setForm(structuredClone(next.income_tax || blankIncomeTax())); setSaved(false); }
    } catch { if (mounted.current) setError(say("无法载入，请重试。", "Could not load saved details. Retry.")); }
    finally { if (mounted.current) setSaving(false); }
  }
  const jurisdictionOptions = Object.entries(taxJurisdictions).map(([code, names]) =>
    <option key={code} value={code}>{names[locale === "en" ? 1 : 0]}</option>);
  return <details className="income-tax-facts" open={!!current.income_tax}>
    <summary>{say("企业与个人所得税", "Corporate and personal income tax")}</summary>
    <p>{say("按纳税主体和所属期间整理收入。保存后可恢复资料；完整计算仍待规则核实，当前保存不会生成应缴税额。", "Record income by taxpayer and period. Saved details can be restored. Complete calculations still require rule validation; saving does not produce a tax liability.")}</p>
    <form onSubmit={save}>
      <fieldset disabled={busy || saving}>
        <legend>{say("所得税资料", "Income-tax details")}</legend>
        <div className="facts-field-grid">
          <label>{say("纳税主体", "Taxpayer")}<select value={form.subject} onChange={e => edit({ subject: e.target.value as IncomeTaxInput["subject"] })}>
            <option value="company">{say("企业", "Company")}</option><option value="individual">{say("个人", "Individual")}</option></select></label>
          <label>{say("申报税区", "Filing jurisdiction")}<select value={form.jurisdiction} onChange={e => changeJurisdiction(e.target.value as TaxJurisdiction)}>{jurisdictionOptions}</select></label>
          <label>{say("期间开始", "Period start")}<input required type="date" value={form.period_start} onChange={e => edit({ period_start: e.target.value })} /></label>
          <label>{say("期间结束", "Period end")}<input required type="date" value={form.period_end} onChange={e => edit({ period_end: e.target.value })} /></label>
          <label>{say("税务居民身份", "Tax residency")}<select value={form.residency} onChange={e => edit({ residency: e.target.value as IncomeTaxInput["residency"] })}>
            <option value="undetermined">{say("待确认", "Not established")}</option><option value="resident">{say("居民", "Resident")}</option><option value="nonresident">{say("非居民", "Non-resident")}</option></select></label>
        </div>
        <p>{say("以下所有金额均使用", "All amounts below use")} <strong>{form.currency}</strong>{say("。", ". ")}{say("如涉及换汇，请在说明中记录汇率、日期和依据。", "For converted amounts, record the rate, date and basis in the description.")}</p>
        {form.incomes.map((item, index) => <fieldset key={index} className="income-tax-item">
          <legend>{say("收入", "Income")} {index + 1}</legend>
          <div className="facts-field-grid">
            <label>{say("收入类别", "Income category")}<select value={item.category} onChange={e => edit({ incomes: form.incomes.map((row, i) => i === index ? { ...row, category: e.target.value as typeof item.category } : row) })}>
              {Object.entries(incomeCategories).map(([key, names]) => <option key={key} value={key}>{names[locale === "en" ? 1 : 0]}</option>)}</select></label>
            <label>{say("收入来源税区", "Income source jurisdiction")}<select value={item.source_jurisdiction} onChange={e => edit({ incomes: form.incomes.map((row, i) => i === index ? { ...row, source_jurisdiction: e.target.value as TaxJurisdiction } : row) })}>{jurisdictionOptions}</select></label>
            <label>{say("收入总额", "Gross income")}<input required type="number" min="0" step="any" value={item.gross_amount} onChange={e => edit({ incomes: form.incomes.map((row, i) => i === index ? { ...row, gross_amount: e.target.value } : row) })} /></label>
            <label>{say("已缴境外税额（未知留空）", "Foreign tax paid (blank if unknown)")}<input type="number" min="0" step="any" value={item.foreign_tax_paid ?? ""} onChange={e => edit({ incomes: form.incomes.map((row, i) => i === index ? { ...row, foreign_tax_paid: e.target.value || null } : row) })} /></label>
          </div>
          <label>{say("收入说明", "Income description")}<textarea required maxLength={1000} value={item.description} onChange={e => edit({ incomes: form.incomes.map((row, i) => i === index ? { ...row, description: e.target.value } : row) })} /></label>
          <button type="button" disabled={form.incomes.length === 1} onClick={() => edit({ incomes: form.incomes.filter((_, i) => i !== index) })}>{say("移除此项收入", "Remove this income")}</button>
        </fieldset>)}
        <button type="button" disabled={form.incomes.length >= 200} onClick={() => edit({ incomes: [...form.incomes, blankIncome(form.jurisdiction)] })}>{say("添加收入", "Add income")}</button>
        <div className="facts-field-grid">
          <label>{say("拟申报扣除额（未知留空）", "Claimed deductions (blank if unknown)")}<input type="number" min="0" step="any" value={form.claimed_deductions ?? ""} onChange={e => edit({ claimed_deductions: e.target.value || null })} /></label>
          <label>{say("结转亏损（未知留空）", "Carried losses (blank if unknown)")}<input type="number" min="0" step="any" value={form.carried_losses ?? ""} onChange={e => edit({ carried_losses: e.target.value || null })} /></label>
        </div>
        <label className="income-tax-confirm"><input type="checkbox" checked={form.facts_confirmed} onChange={e => { setForm(previous => ({ ...previous, facts_confirmed: e.target.checked })); setSaved(false); }} />{say("我已核对以上已填写事实；扣除与抵免资格仍需按规则核实。", "I have checked the entered facts. Deduction and credit eligibility still require rule validation.")}</label>
        <button type="submit" className="primary-button">{saving ? say("保存中…", "Saving…") : say("保存所得税资料", "Save income-tax details")}</button>
        {(conflict || current.revision !== revision) && <button type="button" onClick={reload}>{say("放弃当前填写，载入最新已保存资料", "Discard current entries and reload saved details")}</button>}
      </fieldset>
      {error && <p role="alert">{error}</p>}
      {saved && <p role="status">{say("所得税资料已保存。", "Income-tax details saved.")}</p>}
      {current.income_tax_status === "needs_information" && <div>
        <p>{say("上次保存时尚待确认：", "Still missing at the last save:")}</p>
        <ul>{(current.income_tax_missing || []).map(field => {
          const labels: Record<string, string> = {
            facts_confirmed: say("核对并确认已填写事实", "Review and confirm the entered facts"),
            residency: say("税务居民身份", "Tax residency"),
            claimed_deductions: say("拟申报扣除额", "Claimed deductions"),
            carried_losses: say("结转亏损", "Carried losses"),
          };
          const match = /^incomes\.(\d+)\.foreign_tax_paid$/.exec(field);
          return <li key={field}>{labels[field] || (match
            ? say("收入 " + (Number(match[1]) + 1) + " 的已缴境外税额", "Foreign tax paid for income " + (Number(match[1]) + 1))
            : say("其他待核实资料", "Other details requiring verification"))}</li>;
        })}</ul>
      </div>}
      {current.income_tax_status === "awaiting_rule_validation" && <p>{say("基础资料已齐，税务处理和计算规则仍待核实。", "Basic details are complete. Tax treatment and calculation rules still require validation.")}</p>}
    </form>
  </details>;
}
