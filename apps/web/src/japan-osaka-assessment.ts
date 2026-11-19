import type { BasisField } from './income-assessment';
export const osakaAmounts = [
 ['registered_capital','期末注册资本','Year-end registered capital'],['capital_reserve','期末资本准备金','Year-end capital reserve'],
 ['adjusted_statutory_capital','调整后法定资本额','Adjusted statutory capital'],['enterprise_income_additions','事业税所得调增','Enterprise income additions'],
 ['enterprise_income_deductions','事业税所得调减','Enterprise income deductions'],['eligible_enterprise_prior_losses','事业税可用旧亏损','Eligible enterprise prior losses'],
 ['enterprise_interim_liability','事业税中间申告义务','Enterprise interim liability'],['special_enterprise_interim_liability','特别法人事业税中间申告义务','Special enterprise interim liability'],
 ['prefectural_inhabitant_interim_liability','府法人税割中间申告义务','Prefectural inhabitant interim liability'],['city_inhabitant_interim_liability','市法人税割中间申告义务','City inhabitant interim liability'],
 ['prefectural_capitation_interim_liability','府均等割中间申告义务','Prefectural capitation interim liability'],['city_capitation_interim_liability','市均等割中间申告义务','City capitation interim liability'],
] as const;
export const osakaChecks = [
 ['all_offices_in_wards_for_full_year_verified','已核实全部办公地点全年仅在大阪市','All offices remained in Osaka city for the entire year'],
 ['ordinary_domestic_entity_verified','已核实普通内国法人及行业范围','Ordinary domestic entity and industry verified'],
 ['size_based_exclusion_including_2025_2026_verified','已核实资本历史及控制关系，不适用2025至2026扩围后的外形标准课税','Capital history and control checked: expanded size-based taxation does not apply'],
 ['capital_employees_and_local_base_verified','已核实资本、逐区员工及地方税调整和亏损','Statutory capital, ward employees, local adjustments and losses verified'],
 ['no_local_tax_credits_or_treaty_amendments_verified','无地方税抵免或协定更正减免','No local tax credits or treaty-amendment relief verified'],
] as const;
export function osakaFields(values:Record<string,string>):BasisField[] {
 if(values.jpo_enabled!=='true')return [];
 const count=/^\d+$/.test(values.jpo_ward_count||'')?Math.max(1,Math.min(24,Number(values.jpo_ward_count))):1;
 const fields:BasisField[]=[...osakaAmounts.map(([key,zh,en])=>({key:'jpo_'+key,label:[zh,en] as [string,string]})),
 {key:'jpo_ward_count',label:['设点大阪行政区数量（同区合并）','Number of wards with offices (aggregate within each ward)'],integer:true,min:1,max:24}];
 for(let n=0;n<count;n++)fields.push({key:`jpo_ward_${n}`,label:[`大阪行政区 ${n+1}`,`Ward ${n+1}`],text:true},
 {key:`jpo_employees_${n}`,label:[`区内员工数 ${n+1}`,`Ward employee count ${n+1}`],integer:true,min:0});
 return [...fields,...osakaChecks.map(([key,zh,en])=>({key:'jpo_'+key,label:[zh,en] as [string,string],boolean:true}))];
}
export function osakaBasis(basis:Record<string,unknown>,values:Record<string,string>,explanation:string):Record<string,unknown> {
 if(values.jpo_enabled!=='true')return basis;
 const count=Number(values.jpo_ward_count);
 if(!Number.isInteger(count)||count<1||count>24)throw new Error('Invalid ward count');
 const paper:Record<string,unknown>={local_adjustments_explanation:explanation};
 for(const [key] of [...osakaAmounts,...osakaChecks])paper[key]=basis['jpo_'+key];
 const rows=Array.from({length:count},(_,n)=>({ward_name:basis[`jpo_ward_${n}`],employees:basis[`jpo_employees_${n}`]}));
 if(new Set(rows.map(row=>row.ward_name)).size!==count)throw new Error('Duplicate ward');
 paper.wards=rows;
 const result:Record<string,unknown>={...basis,osaka_local:paper};
 for(const key of Object.keys(result))if(key.startsWith('jpo_'))delete result[key];
 return result;
}
