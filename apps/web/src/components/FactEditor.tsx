import { useState } from "react";
import { useLocale } from "../locale";
import {
  fieldLabel,
  type Case,
  type FieldSpec,
  type FactValue,
} from "../workspace";
import type { FactPatch } from "../api";

export default function FactEditor({
  current,
  fields,
  busy,
  onSave,
  onConfirm,
}: {
  current: Case;
  fields: FieldSpec[];
  busy: boolean;
  onSave: (patch: FactPatch) => void;
  onConfirm: () => void;
}) {
  const { t, locale } = useLocale();
  const initial = Object.fromEntries(
    Object.entries(current.facts).map(([k, record]) => [k, record.value]),
  );
  const [draft, setDraft] = useState<Record<string, FactValue>>(initial);
  const [extra, setExtra] = useState<string[]>([]);
  const patch: FactPatch = {};
  for (const [key, value] of Object.entries(draft)) {
    const type = fields.find((f) => f.field_name === key)?.data_type;
    let normalized: FactValue | null =
      typeof value === "string" ? value.trim() : value;
    if (normalized === "") normalized = null;
    else if (
      typeof normalized === "string" &&
      !["unknown", "conflict"].includes(normalized)
    ) {
      if (type === "list")
        normalized = normalized
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
      else if (
        ["integer", "decimal"].includes(type || "") &&
        Number.isFinite(Number(normalized))
      )
        normalized = Number(normalized);
    }
    if (JSON.stringify(normalized) !== JSON.stringify(initial[key] ?? null))
      patch[key] = normalized;
  }
  const dirty = Object.keys(patch).length > 0;
  const keys = new Set([...Object.keys(draft), ...current.questions, ...extra]);
  const visible = fields.filter((f) => keys.has(f.field_name));
  function change(key: string, value: FactValue) {
    setDraft((all) => ({ ...all, [key]: value }));
  }
  return (
    <>
      <p className="panel-description">
        {t("请核对候选事实。未知项可以保留，冲突项需先修订。")}
      </p>
      <form
        className="facts-form"
        onSubmit={(e) => {
          e.preventDefault();
          onSave(patch);
        }}
      >
        {visible.map((field) => {
          const key = field.field_name,
            value = draft[key] ?? "";
          const numeric = ["integer", "decimal"].includes(field.data_type);
          return (
            <div key={key} className="fact-field">
              <label htmlFor={`fact-${key}`}>{fieldLabel(field, locale)}</label>
              {field.data_type === "enum" ? (
                <select
                  id={`fact-${key}`}
                  value={String(value)}
                  disabled={busy}
                  onChange={(e) => change(key, e.target.value)}
                >
                  <option value="">{t("待补充")}</option>
                  {[
                    ...new Set([
                      ...(field.enum_values || []),
                      "unknown",
                      "conflict",
                    ]),
                  ].map((option) => (
                    <option value={option} key={option}>
                      {t(`value:${option}`)}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  id={`fact-${key}`}
                  disabled={busy}
                  aria-label={fieldLabel(field, locale)}
                  value={Array.isArray(value) ? value.join(", ") : value}
                  inputMode={numeric ? "decimal" : undefined}
                  maxLength={1000}
                  placeholder={
                    field.data_type === "date" ? "YYYY-MM-DD" : t("待补充")
                  }
                  onChange={(e) => change(key, e.target.value)}
                />
              )}
              <span className="fact-tools">
                <span>
                  {current.facts[key]?.origin === "model"
                    ? t("模型提取，待核对")
                    : t("手工记录")}
                </span>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => change(key, "unknown")}
                >
                  {t("暂不清楚")}
                </button>
              </span>
            </div>
          );
        })}
        <label>
          {t("补充事实")}
          <select
            value=""
            disabled={busy}
            onChange={(e) => setExtra([...extra, e.target.value])}
          >
            <option value="">{t("选择需要补充的事实")}</option>
            {fields
              .filter((f) => !keys.has(f.field_name))
              .map((f) => (
                <option key={f.field_name} value={f.field_name}>
                  {fieldLabel(f, locale)}
                </option>
              ))}
          </select>
        </label>
        <button
          className="primary-button"
          disabled={busy || !dirty}
          type="submit"
        >
          {t("保存事实")}
        </button>
        <p className="panel-note">
          {t("确认将锁定当前事实版本；后续修改会使旧分析过期。")}
        </p>
        <button
          className="primary-button"
          type="button"
          disabled={
            busy ||
            dirty ||
            !Object.keys(current.facts).length ||
            Object.values(current.facts).some((f) => f.value === "conflict")
          }
          onClick={onConfirm}
        >
          {t("确认事实并分析")}
        </button>
        {dirty && <small>{t("请先保存修改，再确认。")}</small>}
      </form>
    </>
  );
}
