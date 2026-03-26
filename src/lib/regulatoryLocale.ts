const JA_COUNTRY_LABELS: Record<string, string> = {
  APAC: "APAC",
  Australia: "オーストラリア",
  Canada: "カナダ",
  China: "中国",
  Denmark: "デンマーク",
  European Union: "欧州連合",
  Germany: "ドイツ",
  India: "インド",
  International: "国際",
  Japan: "日本",
  Norway: "ノルウェー",
  Singapore: "シンガポール",
  South Korea: "韓国",
  Sweden: "スウェーデン",
  Taiwan: "台湾",
  United Kingdom: "英国",
  United States: "米国",
};

const JA_COMPOUND_CLASS_LABELS: Record<string, string> = {
  fluoropolymer: "フルオロポリマー",
  PFAS_and_fluoropolymer: "PFASおよびフルオロポリマー",
  pfas_and_fluoropolymer: "PFASおよびフルオロポリマー",
  PFAS_class: "PFASクラス",
  pfas_class: "PFASクラス",
};

const JA_LITIGATION_RELEVANCE_LABELS: Record<string, string> = {
  high: "高",
  medium: "中",
  low: "低",
};

const JA_STATUS_VALUE_LABELS: Record<string, string> = {
  advisory: "勧告",
  banned: "禁止",
  binding: "拘束力あり",
  compliant: "準拠",
  consultation: "意見募集",
  enforceable: "施行可能",
  enforced: "施行済み",
  final: "最終",
  finalized: "最終化済み",
  listed: "掲載済み",
  monitored: "監視中",
  monitoring: "監視中",
  proposed: "提案中",
  regulated: "規制対象",
  restricted: "制限",
  under_review: "審査中",
  unverified: "未検証",
};

const JA_ASSERTION_TEXT_BY_ID: Record<string, string> = {
  APAC_FLUOROPOLYMER_GAP_001:
    "現在、APACでフルオロポリマー（PTFE、PVDF、FEP、PFA、ETFE）を加工助剤とは切り離した完成品として直接規制している国はありませんが、係争中の広義PFAS定義により将来的に捕捉される可能性があります。",
  APAC_FLUOROPOLYMER_MARKET_001:
    "アジア太平洋地域は2024年の世界フルオロポリマー市場の42.93%を占めており、PTFE、PVDF、フルオロエラストマーメーカーにとって地域規制は商業上きわめて重要です。",
  AUS_NEMP_001:
    "オーストラリアのPFAS国家環境管理計画（PFAS NEMP）は、全州・準州におけるPFAS汚染サイト調査と修復の拘束的枠組みを提供しています。",
  AUS_NHMRC_WATER_001:
    "NHMRC は豪州飲料水ガイドライン v4.0 を公表し、PFAS 指針値として PFOS 8 ng/L、PFOA 200 ng/L、PFHxS 30 ng/L、PFBS 1000 ng/L を設定しました。",
  CAN_PFOS_PROHIBITION_001:
    "カナダでは PFOS が引き続き有害物質禁止規制の対象であり、2026年6月30日に発効する PCTSR 2025 が PCTSR 2012 を置き換える予定です。",
  CHN_MEE_PFOA_CONSULT_001:
    "中国 MEE-FECO は、ストックホルム条約の国内実施に向けた PFOA、PFHxS、長鎖 PFCA の指示的リストについて、2025年5月19日を期限とするパブリックコメントを開始しました。",
  CHN_MEE_POLLUTANTS_001:
    "中国生態環境部（MEE）は、PFOS と PFOA を含む PFAS を「重点管理新汚染物質リスト」の優先汚染物質に指定しました。",
  CHN_MEE_THIRD_BATCH_001:
    "中国 MEE は、長鎖 PFCA、ペルフルオロアルキルスルホン酸塩、およびその誘導体を含む 29 種の特定 PFAS を盛り込んだ第3次重点管理化学物質案を公表しました。",
  CHN_PATENT_SIGNAL_001:
    "中国は、PFAS 商業特許出願件数が依然として増加している唯一の主要経済圏であり、他の主要経済圏ではいずれも減少しています。",
  CHN_SICHUAN_LOCAL_001:
    "四川省は、化学工業団地向けに PFOA と PFOS の排出基準（DB51/3202-2024）を定める中国初の地方規制を公布しました。",
  DEU_UBA_PFAS_001:
    "ドイツの改正飲料水令は、PFAS-20 に対して 2026年1月12日から 0.10 ug/L、PFAS-4 に対して 2028年1月12日から 0.020 ug/L という段階的な PFAS 上限値を設定しています。",
  DNK_FCM_PFAS_001:
    "デンマークは 2020 年以降、添加 PFAS を含む紙・板紙製食品接触材料の販売を禁止しています。",
  EU_DWD_COMPLIANCE_001:
    "欧州連合では、加盟国が 2026年1月12日までに飲料水指令の PFAS パラメータへ適合することが求められています。",
  EU_DWD_PFAS_PARAM_001:
    "EU 飲料水指令は、PFAS Total に 0.50 ug/L、Sum of PFAS に 0.10 ug/L のパラメータ値を設定しています。",
  EU_POPS_PFOA_001:
    "PFOA、その塩、および関連化合物は、ストックホルム条約の実施に整合した EU POPs 規則の枠組みで掲載されています。",
  IND_CPCB_MONITORING_001:
    "インド中央公害管理委員会（CPCB）には正式な PFAS 規制がありません。工業地帯周辺で PFAS 汚染は記録されていますが、規制整備はまだ初期段階です。",
  IND_FSSAI_FOOD_001:
    "インド FSSAI は、2025年10月6日に公表した食品安全・基準（包装）規則 2018 年改正案により、食品接触材料中の PFAS と BPA の全面禁止を提案しました。",
  JPN_AFFF_INVENTORY_001:
    "日本はストックホルム条約国内実施計画の下で 4 年間の AFFF 備蓄インベントリを進めており、2024 年調査では AFFF 量が 45%、PFOS 含有量が 36% 減少したことが示されています。",
  JPN_CSCL_PFOA_001:
    "日本は共同省令により、138 種の PFOA 関連化合物を化審法の第一種特定化学物質として禁止し、違反には刑事罰が適用されます。",
  JPN_CSCL_PFOS_001:
    "PFOS は、ストックホルム条約を実施する日本の化審法の下で第一種特定化学物質に指定されています。",
  JPN_MOE_FOOD_001:
    "日本は 2025 年内閣府告示第 105 号により、PFAS に関する食品接触材料基準を改正した可能性があります。",
  JPN_MOE_WATER_001:
    "日本環境省は、PFOS/PFOA の暫定水質目標を、2026 年 4 月発効予定の合算 50 ng/L の法的拘束力ある水質基準へ引き上げています。",
  KOR_MFDS_COSMETICS_001:
    "韓国 MFDS は、化粧品安全基準規則の改正により、2022年4月1日発効で化粧品中のペルフルオロ化合物を禁止しました。",
  KOR_MOE_WATER_001:
    "韓国環境部は、水環境保全法および下水道法の PFAS 改正案を提案し、PFAS 排出基準の設定を進めています。",
  KOR_REACH_PFAS_001:
    "韓国の K-REACH は、ストックホルム条約上の義務に従い、PFOA、PFOS、PFHxS を含む PFAS 化合物の登録と評価を求めています。",
  NOR_PFAS_RESTRICTION_001:
    "ノルウェーは 2026年1月1日から、4 種 PFAS 合計 4 ng/L の新しい飲料水基準を施行し、20 種 PFAS 合計 100 ng/L の値は EEA 編入待ちです。",
  SGP_NEA_AFFF_001:
    "シンガポール NEA は、環境保護管理法の下で、2026年1月1日から PFAS 含有消火泡を特定濃度閾値付きで禁止しました。",
  SWE_KEMI_PFAS_001:
    "スウェーデンの飲料水枠組みは、2026年1月1日から PFAS-4 に 4 ng/L、PFAS-21 に 100 ng/L の PFAS 基準を適用しています。",
  TWN_MOENV_269_001:
    "台湾 MOENV は、269 種の PFAS を「懸念化学物質」に指定する案を公表しました。",
  TWN_MOENV_357_001:
    "台湾 MOENV は、PFOA および PFOS 系 357 物質を 0% 管理濃度で毒性化学物質リストに追加する規制案を公表しました。",
  TWN_MOENV_DRINKING_001:
    "台湾は 2024 年 11 月に飲料水水質基準を改正して PFAS 基準値を追加し、アジアで初めて PFAS 飲料水基準を法制化した国となりました。",
  TWN_MOENV_PFHXS_001:
    "台湾は 2024年4月24日発効で、147 種の PFHxS 関連化合物を 0% 管理濃度の第一類毒性化学物質として禁止しました。",
  UK_HSE_REACH_001:
    "英国は、EU 離脱後も HSE が運営する独立した UK REACH 制度を維持しています。",
  UK_PFOS_PFOA_CARRYOVER_001:
    "英国では、EU 離脱後も保持法と英国独自の化学物質ガバナンス経路を通じて PFOS/PFOA 管理が継続しています。",
  US_EPA_CERCLA_001:
    "米国では、PFOA と PFOS が CERCLA 上の有害物質に指定されており、この規則は 2024年7月8日に発効しました。",
  US_EPA_NPDWR_2024_001:
    "米国 EPA は 2024 年 4 月に PFAS の NPDWR を最終化し、6 種 PFAS 指標に対する拘束力ある基準と 2024年6月25日の発効日を設定しました。",
  US_EPA_PFOA_MCL_001:
    "米国 EPA の現行 NPDWR 体制では、PFOA の最大汚染物質基準値（MCL）は 4 ppt、目標値（MCLG）は 0 のままです。",
  US_EPA_PFOS_MCL_001:
    "米国 EPA の現行 NPDWR 体制では、PFOS の最大汚染物質基準値（MCL）は 4 ppt、目標値（MCLG）は 0 のままです。",
  US_EPA_TSCA_REPORTING_001:
    "TSCA 第 8(a)(7) 条は、PFAS 含有成形品を含め、2011 年以降に製造または輸入された PFAS について報告を求めています。",
  US_NC_GENX_CONSENT_001:
    "ノースカロライナ州で裁判所命令として成立した Chemours 同意命令（2019 年 2 月）は、Fayetteville Works における GenX/PFAS 管理の中核的な州執行枠組みとして継続しています。",
};

const JA_THRESHOLD_BY_ID: Record<string, string> = {
  AUS_NHMRC_WATER_001: "PFOS 8 ng/L、PFOA 200 ng/L、PFHxS 30 ng/L、PFBS 1000 ng/L",
  CHN_SICHUAN_LOCAL_001: "PFOA/PFOS 排出基準（具体値は DB51/3202-2024 を参照）",
  IND_FSSAI_FOOD_001: "全面禁止 — PFAS は食品接触材料の製造に使用してはなりません",
  JPN_MOE_WATER_001: "PFOS + PFOA 合算 50 ng/L",
  SGP_NEA_AFFF_001: "PFOA: 25 ppb、PFOS: 10000 ppb、PFHxS: 100 ppb — これらを超える泡消火剤は禁止",
  TWN_MOENV_357_001: "混合物中の管理濃度 0%（案）",
  TWN_MOENV_DRINKING_001: "PFOA+PFOS: 50 ng/L、PFOS+PFHxS: 70 ng/L、総 PFAS（20 化合物）: 100 ng/L",
  TWN_MOENV_PFHXS_001: "混合物中の管理濃度 0% — 完全禁止",
};

const JA_CASCADE_SOURCE_BY_ID: Record<string, string> = {
  AUS_NEMP_001:
    "豪州気候変動・エネルギー・環境・水省 PFAS 国家環境管理計画ページ (https://www.dcceew.gov.au/environment/protection/chemicals-management/pfas)",
  CAN_PFOS_PROHIBITION_001:
    "カナダ PFOS 禁止規制ページ",
  CHN_MEE_POLLUTANTS_001:
    "中国生態環境部「重点管理新汚染物質リスト（2023年版）」 (https://www.mee.gov.cn/)",
  CHN_SICHUAN_LOCAL_001:
    "CIRS Group による中国初の化学工業団地向け PFOA/PFOS 管理基準解説 (https://www.cirs-group.com/en/chemicals/china-implements-first-chemical-park-pfoa-and-pfos-control-standards)",
  DEU_UBA_PFAS_001:
    "UBA 新飲料水令の PFAS 基準値更新ページ (https://www.umweltbundesamt.de/en/topics/water/drinking-water/new-drinking-water-ordinance-ensures-high-quality)",
  DNK_FCM_PFAS_001:
    "デンマーク食品当局 PFAS ページ（英語） (https://en.foedevarestyrelsen.dk/food/food-safety-and-hygiene/chemical-food-safety/pfas)",
  EU_DWD_COMPLIANCE_001:
    "指令 2020/2184 第13条7項に基づく EU 技術ガイドライン (https://eur-lex.europa.eu/eli/C/2024/4910)",
  EU_DWD_PFAS_PARAM_001:
    "EU 指令 2020/2184 (https://eur-lex.europa.eu/eli/dir/2020/2184/oj)",
  JPN_MOE_FOOD_001:
    "2025 年内閣府告示第 105 号（未確認） (https://www.caa.go.jp/)",
  JPN_MOE_WATER_001:
    "日本環境省 水質基準改正プレスリリース (https://www.env.go.jp/water/)",
  KOR_MFDS_COSMETICS_001:
    "韓国 MFDS 化粧品安全基準規則ページ (https://www.mfds.go.kr/eng/wpge/m_24/de011014l001.do)",
  KOR_REACH_PFAS_001:
    "K-REACH ポータル 化学物質登録評価法 (https://www.me.go.kr/eng/web/main.do)",
  NOR_PFAS_RESTRICTION_001:
    "ノルウェー食品安全庁の新 PFAS 飲料水基準通知 (https://www.mattilsynet.no/mat-og-drikke/drikkevann/ny-grenseverdi-for-pfas-i-drikkevann)",
  SGP_NEA_AFFF_001:
    "NEA Circular NEA/HS/6.6 PFAS 含有消火泡の段階的廃止通知 (https://www.nea.gov.sg/docs/default-source/default-document-library/phase-out-of-fire-fighting-foams-containing-pfas-chemicals-listed-under-the-stockholm-convention_15mar24.pdf)",
  SWE_KEMI_PFAS_001:
    "スウェーデン国立食品庁 PFAS 飲料水規制 FAQ (https://www.livsmedelsverket.se/foretagande-regler-kontroll/dricksvattenproduktion/regler-om-dricksvatten/fragor-och-svar-om-dricksvattenforeskrifterna)",
  TWN_MOENV_DRINKING_001:
    "ChemLinked 台湾の PFAS 飲料水基準案記事 (https://sustainability.chemlinked.com/news/taiwan-drafts-standards-for-pfas-in-drinking-water)",
  UK_HSE_REACH_001:
    "HSE UK REACH 制度ページ (https://www.hse.gov.uk/reach/)",
  UK_PFOS_PFOA_CARRYOVER_001:
    "HSE UK REACH 制度ページ (https://www.hse.gov.uk/reach/)",
  US_EPA_CERCLA_001:
    "EPA CERCLA 指定 Q&A ページ (https://www.epa.gov/superfund/questions-and-answers-about-designation-pfoa-and-pfos-hazardous-substances-under-cercla)",
  US_EPA_NPDWR_2024_001:
    "EPA SDWA PFAS NPDWR ページ (https://www.epa.gov/sdwa/and-polyfluoroalkyl-substances-pfas)",
  US_EPA_TSCA_REPORTING_001:
    "EPA TSCA 第 8(a)(7) PFAS 報告ページ (https://www.epa.gov/assessing-and-managing-chemicals-under-tsca/tsca-section-8a7-reporting-and-recordkeeping)",
};

const JA_FLUOROPOLYMER_EXPOSURE_SEGMENTS: Record<string, string> = {
  "Fluoropolymer coatings flagged in CSCL ban context; processing aids restricted":
    "フルオロポリマーコーティングは化審法の禁止文脈で注視されており、加工助剤には制限があります",
  "No direct fluoropolymer product regulation; processing aids under K-REACH":
    "フルオロポリマー製品そのものへの直接規制はありませんが、加工助剤は K-REACH の対象です",
  "Major PTFE/PVDF manufacturing base; patent filings increasing; processing aid restrictions tightening":
    "主要な PTFE/PVDF 製造拠点であり、特許出願は増加中、加工助剤規制は強化方向です",
  "No direct fluoropolymer regulation; PFAS NEMP covers contaminated sites":
    "フルオロポリマーへの直接規制はありませんが、PFAS NEMP が汚染サイトを対象にしています",
  "Limited — AFFF focus only; no product-level fluoropolymer restrictions":
    "限定的で、AFFF 対応が中心です。製品レベルのフルオロポリマー規制はありません",
  "269 concerned substances designation may capture fluoropolymer processing aids; broadest APAC PFAS net":
    "269 種の懸念化学物質指定により、フルオロポリマー加工助剤が捕捉される可能性があります。APAC で最も広い PFAS 網です",
  "FSSAI ban scope includes PTFE-coated food contact materials — commercially significant for non-stick coatings":
    "FSSAI の禁止案は PTFE コーティング食品接触材料を含み、ノンスティック用途に商業上大きな影響があります",
};

const JA_DEGRADATION_SOURCE: Record<string, string> = {
  "BoundState Literature Corpus (peer-reviewed)": "BoundState 文献コーパス（査読済み）",
  "Fallback data (limited literature coverage)": "フォールバックデータ（文献カバレッジ限定）",
  "No literature data available for this material": "この材料に関する文献データはありません",
};

const JA_AFFECTED_PRODUCT_LABELS: Record<string, string> = {
  "All PFAS-containing products": "すべての PFAS 含有製品",
  "PFAS food-contact materials": "PFAS 食品接触材料",
};

export function isJapaneseLocale(locale?: string): boolean {
  return (locale ?? "").toLowerCase().startsWith("ja");
}

export function localizeRegulatoryCountry(country: string, locale?: string): string {
  if (!isJapaneseLocale(locale)) return country;
  return JA_COUNTRY_LABELS[country] ?? country;
}

export function localizeCompoundClass(compoundClass: string, locale?: string): string {
  if (!isJapaneseLocale(locale)) return compoundClass;
  return JA_COMPOUND_CLASS_LABELS[compoundClass] ?? compoundClass;
}

export function localizeLitigationRelevance(value: string, locale?: string): string {
  if (!isJapaneseLocale(locale)) return value;
  return JA_LITIGATION_RELEVANCE_LABELS[value.toLowerCase()] ?? value;
}

export function localizeApacAssertionText(assertionId: string, text: string, locale?: string): string {
  if (!isJapaneseLocale(locale)) return text;
  return JA_ASSERTION_TEXT_BY_ID[assertionId] ?? text;
}

export function localizeApacThreshold(assertionId: string, value: string | null | undefined, locale?: string): string | null | undefined {
  if (!value || !isJapaneseLocale(locale)) return value;
  return JA_THRESHOLD_BY_ID[assertionId] ?? value;
}

export function localizeFluoropolymerExposure(value: string | null | undefined, locale?: string): string | null | undefined {
  if (!value || !isJapaneseLocale(locale)) return value;
  return value
    .split(" | ")
    .map((segment) => {
      const [country, detail] = segment.split(": ", 2);
      if (!detail) return segment;
      const localizedCountry = localizeRegulatoryCountry(country, locale);
      const localizedDetail = JA_FLUOROPOLYMER_EXPOSURE_SEGMENTS[detail] ?? detail;
      return `${localizedCountry}: ${localizedDetail}`;
    })
    .join(" | ");
}

export function localizeDegradationSource(value: string, locale?: string): string {
  if (!value || !isJapaneseLocale(locale)) return value;
  return JA_DEGRADATION_SOURCE[value] ?? value;
}

export function localizeRegulatoryNote(note: string, locale?: string): string {
  if (!isJapaneseLocale(locale)) return note;
  if (note.startsWith("Limit: ")) {
    return `制限値：${note.slice("Limit: ".length)}`;
  }
  if (note.startsWith("Status: ")) {
    const raw = note.slice("Status: ".length);
    const localized = JA_STATUS_VALUE_LABELS[raw.toLowerCase().replace(/\s+/g, "_")] ?? raw;
    return `ステータス：${localized}`;
  }
  if (note.startsWith("No restrictions under ")) {
    const scope = note.slice("No restrictions under ".length);
    return `${scope} に基づく制限はありません`;
  }
  return note;
}

export function localizeCascadeStatus(assertionId: string, status: string, locale?: string): string {
  if (!isJapaneseLocale(locale)) return status;
  return JA_ASSERTION_TEXT_BY_ID[assertionId] ?? status;
}

export function localizeCascadeSource(assertionId: string, source: string | undefined, locale?: string): string | undefined {
  if (!source || !isJapaneseLocale(locale)) return source;
  return JA_CASCADE_SOURCE_BY_ID[assertionId] ?? source;
}

export function localizeAffectedProducts(products: string[], locale?: string): string[] {
  if (!isJapaneseLocale(locale)) return products;
  return products.map((product) => JA_AFFECTED_PRODUCT_LABELS[product] ?? product);
}

export function localizeCascadeRecommendation(recommendation: string, locale?: string): string {
  if (!isJapaneseLocale(locale)) return recommendation;
  const monitorMatch = recommendation.match(/^MONITOR: (.+) may face restrictions by (\d{4})\. Track EU REACH proposal and prepare for potential use restrictions\.$/);
  if (monitorMatch) {
    return `監視：${monitorMatch[1]} は ${monitorMatch[2]} 年までに制限を受ける可能性があります。EU REACH 提案を追跡し、潜在的な用途制限に備えてください。`;
  }
  const urgentMatch = recommendation.match(/^URGENT: (.+) is subject to existing bans\. Immediate phase-out required\. Consult legal counsel for compliance strategy\.$/);
  if (urgentMatch) {
    return `緊急：${urgentMatch[1]} は既存の禁止措置の対象です。直ちに段階的廃止が必要です。コンプライアンス戦略について法務に相談してください。`;
  }
  const highMatch = recommendation.match(/^HIGH PRIORITY: (.+) faces significant regulatory pressure\. Begin evaluating alternatives and supply chain impacts\.$/);
  if (highMatch) {
    return `高優先：${highMatch[1]} は大きな規制圧力に直面しています。代替材とサプライチェーン影響の評価を開始してください。`;
  }
  const lowMatch = recommendation.match(/^LOW RISK: (.+) not currently targeted but monitor regulatory developments as PFAS definition expands\.$/);
  if (lowMatch) {
    return `低リスク：${lowMatch[1]} は現時点で主対象ではありませんが、PFAS 定義の拡大に伴う規制動向を監視してください。`;
  }
  return recommendation;
}
