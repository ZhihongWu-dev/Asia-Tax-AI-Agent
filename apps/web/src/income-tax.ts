export const taxJurisdictions = {
  cn: ["中国内地", "Mainland China", "CNY"], hk: ["中国香港", "Hong Kong", "HKD"],
  sg: ["新加坡", "Singapore", "SGD"], id: ["印度尼西亚", "Indonesia", "IDR"],
  vn: ["越南", "Vietnam", "VND"], my: ["马来西亚", "Malaysia", "MYR"],
  th: ["泰国", "Thailand", "THB"], ae: ["阿联酋", "United Arab Emirates", "AED"],
  jp: ["日本", "Japan", "JPY"], kr: ["韩国", "South Korea", "KRW"], in: ["印度", "India", "INR"],
} as const;
export type TaxJurisdiction = keyof typeof taxJurisdictions;
export const incomeCategories = {
  business: ["经营收入", "Business"], employment: ["工资薪金", "Employment"], dividend: ["股息", "Dividends"],
  service_remuneration: ["个人劳务报酬", "Personal service remuneration"], author_remuneration: ["个人稿酬", "Author remuneration"],
  interest: ["利息", "Interest"], rental: ["租金", "Rent"], royalty: ["特许权使用费", "Royalties"],
  capital_gain: ["资本利得", "Capital gains"], other: ["其他", "Other"],
} as const;
export type IncomeItem = { category: keyof typeof incomeCategories; source_jurisdiction: TaxJurisdiction;
  gross_amount: string; foreign_tax_paid: string | null; description: string };
export type IncomeTaxInput = { scenario: "income_tax"; subject: "company" | "individual";
  jurisdiction: TaxJurisdiction; currency: string; period_start: string; period_end: string;
  residency: "resident" | "nonresident" | "undetermined"; incomes: IncomeItem[];
  claimed_deductions: string | null; carried_losses: string | null; facts_confirmed: boolean };
export type IncomeTaxView = { id: string; revision: number; income_tax: IncomeTaxInput | null;
  income_tax_status: string; missing_fields: string[] };
export function blankIncome(jurisdiction: TaxJurisdiction): IncomeItem {
  return { category: "business", source_jurisdiction: jurisdiction, gross_amount: "", foreign_tax_paid: null, description: "" };
}
export function blankIncomeTax(): IncomeTaxInput {
  return { scenario: "income_tax", subject: "company", jurisdiction: "cn", currency: "CNY", period_start: "", period_end: "",
    residency: "undetermined", incomes: [blankIncome("cn")], claimed_deductions: null, carried_losses: null, facts_confirmed: false };
}
