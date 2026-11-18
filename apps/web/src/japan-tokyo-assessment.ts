import type { BasisField } from './income-assessment';
export const tokyoAmounts = [
 ['registered_capital','期末注册资本','Year-end registered capital'],['capital_reserve','期末资本准备金','Year-end capital reserve'],
 ['adjusted_statutory_capital','调整后法定资本额','Adjusted statutory capital'],['enterprise_income_additions','事业税所得调增','Enterprise income additions'],
 ['enterprise_income_deductions','事业税所得调减','Enterprise income deductions'],['eligible_enterprise_prior_losses','事业税可用旧亏损','Eligible enterprise prior losses'],
 ['enterprise_interim_liability','事业税中间申告义务','Enterprise interim liability'],['special_enterprise_interim_liability','特别法人事业税中间申告义务','Special enterprise interim liability'],
 ['inhabitant_interim_liability','住民税法人税割中间申告义务','Inhabitant levy interim liability'],['per_capita_interim_liability','均等割中间申告义务','Per-capita interim liability'],
] as const;
export const tokyoChecks = [
 ['all_offices_in_wards_for_full_year_verified','已核实全部办公地点全年仅在东京23区','All offices remained in Tokyo 23 wards for the entire year'],
 ['ordinary_domestic_entity_verified','已核实普通内国法人及行业范围','Ordinary domestic entity and industry verified'],
 ['size_based_exclusion_including_2025_2026_verified','已核实资本历史及控制关系，不适用2025至2026扩围后的外形标准课税','Capital history and control checked: expanded size-based taxation does not apply'],
 ['capital_employees_and_local_base_verified','已核实资本、逐区员工及地方税调整和亏损','Statutory capital, ward employees, local adjustments and losses verified'],
 ['no_local_tax_credits_or_treaty_amendments_verified','无地方税抵免或协定更正减免','No local tax credits or treaty-amendment relief verified'],
] as const;
export const tokyoWards=['千代田区','中央区','港区','新宿区','文京区','台東区','墨田区','江東区','品川区','目黒区','大田区','世田谷区','渋谷区','中野区','杉並区','豊島区','北区','荒川区','板橋区','練馬区','足立区','葛飾区','江戸川区'];
export function tokyoFields(values:Record<string,string>):BasisField[] {
 if(values.jpt_enabled!=='true')return [];
 const count=/^\d+$/.test(values.jpt_ward_count||'')?Math.max(1,Math.min(23,Number(values.jpt_ward_count))):1;
 const fields:BasisField[]=[...tokyoAmounts.map(([key,zh,en])=>({key:'jpt_'+key,label:[zh,en] as [string,string]})),
 {key:'jpt_ward_count',label:['设点特别区数量（同区合并）','Number of wards with offices (aggregate within each ward)'],integer:true,min:1,max:23},
 {key:'jpt_principal',label:['主办公地点所在行','Principal office row'],options:Array.from({length:count},(_,n)=>[String(n+1),[String(n+1),String(n+1)]] as [string,[string,string]])}];
 for(let n=0;n<count;n++)fields.push({key:`jpt_ward_${n}`,label:[`特别区 ${n+1}`,`Ward ${n+1}`],options:tokyoWards.map((name,i)=>[String(13101+i),[name,name]])},
 {key:`jpt_employees_${n}`,label:[`区内员工数 ${n+1}`,`Ward employee count ${n+1}`],integer:true,min:0});
 return [...fields,...tokyoChecks.map(([key,zh,en])=>({key:'jpt_'+key,label:[zh,en] as [string,string],boolean:true}))];
}
export function tokyoBasis(basis:Record<string,unknown>,values:Record<string,string>,explanation:string):Record<string,unknown> {
 if(values.jpt_enabled!=='true')return basis;
 const count=Number(values.jpt_ward_count),principal=Number(values.jpt_principal);
 if(!Number.isInteger(count)||count<1||count>23||!Number.isInteger(principal)||principal<1||principal>count)throw new Error('Invalid ward count');
 const paper:Record<string,unknown>={local_adjustments_explanation:explanation};
 for(const [key] of [...tokyoAmounts,...tokyoChecks])paper[key]=basis['jpt_'+key];
 const rows=Array.from({length:count},(_,n)=>({ward_code:basis[`jpt_ward_${n}`],employees:basis[`jpt_employees_${n}`],principal:n+1===principal}));
 if(new Set(rows.map(row=>row.ward_code)).size!==count)throw new Error('Duplicate ward');
 paper.wards=rows;
 const result:Record<string,unknown>={...basis,tokyo_local:paper};
 for(const key of Object.keys(result))if(key.startsWith('jpt_'))delete result[key];
 return result;
}
