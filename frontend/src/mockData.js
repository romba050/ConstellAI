// frontend/src/mockData.js
// expanded seeded dataset for drug mimic engine.
// goal:
// - keep the institutional navigation shell
// - add more real starter drugs across more domains
// - allow physiology interventions to appear in the same mimic selection flow

export const DISEASE_UNIVERSE = buildDiseaseUniverse();

export function getCategoryById(categoryId) {
  return DISEASE_UNIVERSE.find((c) => c.id === categoryId) || null;
}

export function getSubcategoriesForCategory(categoryId) {
  return getCategoryById(categoryId)?.children || [];
}

export function getSubcategoryById(subcategoryId) {
  for (const cat of DISEASE_UNIVERSE) {
    for (const sub of cat.children || []) {
      if (sub.id === subcategoryId) return sub;
    }
  }
  return null;
}

export function getDrugsForSubcategory({ diseaseId, subcat }) {
  const existing = (subcat?.drugs || []).filter(Boolean);
  if (existing.length) return existing;

  return [];
}

export function getAllCategories() {
  return DISEASE_UNIVERSE.map(({ id, label }) => ({ id, label }));
}

export const COMPOUND_DB = [
  {
    id: 'resveratrol',
    name: 'resveratrol',
    kind: 'compound',
    targets: ['SIRT1↑', 'NFκB↓', 'mTOR↓ (INDIRECT)'],
    tags: ['sirtuin', 'polyphenol'],
    liverLoad: 1,
    nadBoost: 0,
    cypFlags: ['CYP3A4_INHIBIT_LIGHT', 'CYP2C9_INHIBIT_LIGHT'],
    notes: 'seed compound.',
  },
  {
    id: 'nmn',
    name: 'nmn',
    kind: 'compound',
    targets: ['NAD+↑', 'SIRT1↑ (INDIRECT)'],
    tags: ['nad_booster'],
    liverLoad: 1,
    nadBoost: 3,
    cypFlags: [],
    notes: 'seed nad stack risk model.',
  },
  {
    id: 'nr',
    name: 'nicotinamide riboside (nr)',
    kind: 'compound',
    targets: ['NAD+↑'],
    tags: ['nad_booster', 'b3_derivative'],
    liverLoad: 1,
    nadBoost: 3,
    cypFlags: [],
    notes: 'seed compound.',
  },
  {
    id: 'nicotinamide',
    name: 'nicotinamide',
    kind: 'compound',
    targets: ['NAD+↑ (INDIRECT)'],
    tags: ['nad_booster', 'b3_derivative'],
    liverLoad: 1,
    nadBoost: 2,
    cypFlags: [],
    notes: 'seed compound.',
  },
  {
    id: 'curcumin',
    name: 'curcumin',
    kind: 'compound',
    targets: ['NFκB↓', 'TNF↓', 'IL6↓', 'PI3K↓'],
    tags: ['anti_inflammatory'],
    liverLoad: 1,
    nadBoost: 0,
    cypFlags: ['CYP3A4_INHIBIT_LIGHT'],
    notes: 'seed compound.',
  },
  {
    id: 'quercetin',
    name: 'quercetin',
    kind: 'compound',
    targets: ['PI3K↓', 'AKT↓', 'NFκB↓'],
    tags: ['polyphenol'],
    liverLoad: 2,
    nadBoost: 0,
    cypFlags: ['CYP3A4_INHIBIT_LIGHT'],
    notes: 'seed compound.',
  },
  {
    id: 'egcg',
    name: 'egcg',
    kind: 'compound',
    targets: ['EGFR↓ (LIGHT SIGNAL)', 'NFκB↓', 'MAPK↓'],
    tags: ['polyphenol'],
    liverLoad: 3,
    nadBoost: 0,
    cypFlags: [],
    notes: 'seed compound.',
  },
  {
    id: 'berberine',
    name: 'berberine',
    kind: 'compound',
    targets: ['AMPK↑', 'mTOR↓', 'SREBF1↓'],
    tags: ['metabolic'],
    liverLoad: 2,
    nadBoost: 0,
    cypFlags: ['CYP3A4_INHIBIT_MED', 'CYP2D6_INHIBIT_LIGHT'],
    notes: 'seed compound.',
  },
  {
    id: 'luteolin',
    name: 'luteolin',
    kind: 'compound',
    targets: ['IL6↓', 'TNF↓', 'NFκB↓', 'MAPK↓'],
    tags: ['anti_inflammatory', 'polyphenol'],
    liverLoad: 1,
    nadBoost: 0,
    cypFlags: ['CYP3A4_INHIBIT_LIGHT'],
    notes: 'seed compound.',
  },
  {
    id: 'apigenin',
    name: 'apigenin',
    kind: 'compound',
    targets: ['CDK↓', 'NFκB↓', 'BDNF↑ (LIGHT SIGNAL)'],
    tags: ['polyphenol'],
    liverLoad: 1,
    nadBoost: 0,
    cypFlags: [],
    notes: 'seed compound.',
  },
  {
    id: 'sulforaphane',
    name: 'sulforaphane',
    kind: 'compound',
    targets: ['NRF2↑', 'NFκB↓', 'AKT↓ (LIGHT SIGNAL)'],
    tags: ['detox', 'anti_inflammatory'],
    liverLoad: 1,
    nadBoost: 0,
    cypFlags: [],
    notes: 'seed compound.',
  },
  {
    id: 'omega3',
    name: 'omega-3',
    kind: 'compound',
    targets: ['TNF↓', 'IL6↓', 'PPARα↑'],
    tags: ['lipid_support'],
    liverLoad: 0,
    nadBoost: 0,
    cypFlags: [],
    notes: 'seed compound.',
  },
  {
    id: 'creatine',
    name: 'creatine',
    kind: 'compound',
    targets: ['ATP BUFFER↑', 'BDNF↑ (LIGHT SIGNAL)'],
    tags: ['performance'],
    liverLoad: 0,
    nadBoost: 0,
    cypFlags: [],
    notes: 'seed compound.',
  },

  {
    id: 'phys_cold_exposure',
    name: 'cold exposure / cold plunge',
    kind: 'physiology',
    targets: ['AMPK↑', 'PGC1A↑', 'SIRT3↑', 'NOREPINEPHRINE↑'],
    tags: ['physiology', 'temperature'],
    liverLoad: 0,
    nadBoost: 0,
    cypFlags: [],
    notes: 'physiology mimic entry.',
  },
  {
    id: 'phys_sauna',
    name: 'heat exposure / sauna',
    kind: 'physiology',
    targets: ['HSP70↑', 'BDNF↑', 'NITRIC OXIDE↑'],
    tags: ['physiology', 'temperature'],
    liverLoad: 0,
    nadBoost: 0,
    cypFlags: [],
    notes: 'physiology mimic entry.',
  },
  {
    id: 'phys_zone2',
    name: 'zone 2 endurance',
    kind: 'physiology',
    targets: ['AMPK↑', 'PGC1A↑', 'BDNF↑', 'INSULIN SENSITIVITY↑'],
    tags: ['physiology', 'exercise'],
    liverLoad: 0,
    nadBoost: 0,
    cypFlags: [],
    notes: 'physiology mimic entry.',
  },
  {
    id: 'phys_resistance_training',
    name: 'resistance training',
    kind: 'physiology',
    targets: ['GLUT4↑', 'IGF1↑ (starter)', 'INSULIN SENSITIVITY↑'],
    tags: ['physiology', 'exercise'],
    liverLoad: 0,
    nadBoost: 0,
    cypFlags: [],
    notes: 'physiology mimic entry.',
  },
  {
    id: 'phys_sleep_optimization',
    name: 'sleep optimization',
    kind: 'physiology',
    targets: ['CORTISOL↓', 'BDNF↑', 'INFLAMMATION↓'],
    tags: ['physiology', 'recovery'],
    liverLoad: 0,
    nadBoost: 0,
    cypFlags: [],
    notes: 'physiology mimic entry.',
  },
  {
    id: 'phys_bright_light_am',
    name: 'bright light morning',
    kind: 'physiology',
    targets: ['CIRCADIAN ALIGNMENT↑', 'CORTISOL AWAKENING RESPONSE↑', 'SLEEP DRIVE↑ (NIGHT)'],
    tags: ['physiology', 'circadian'],
    liverLoad: 0,
    nadBoost: 0,
    cypFlags: [],
    notes: 'physiology mimic entry.',
  },
  {
    id: 'phys_time_restricted_feeding',
    name: 'time-restricted feeding',
    kind: 'physiology',
    targets: ['AMPK↑', 'mTOR↓', 'AUTOPHAGY↑'],
    tags: ['physiology', 'feeding'],
    liverLoad: 0,
    nadBoost: 0,
    cypFlags: [],
    notes: 'physiology mimic entry.',
  },
];

export const TARGET_INDEX = {
  'SIRT1↑': ['resveratrol', 'nmn', 'phys_time_restricted_feeding'],
  'SIRT1↑ (starter)': ['resveratrol', 'nmn', 'phys_time_restricted_feeding'],
  'SIRT1↑ (SECONDARY starter)': ['resveratrol', 'nmn', 'phys_time_restricted_feeding'],
  'SIRT1↑ (INDIRECT)': ['nmn'],
  'SIRT3↑': ['phys_cold_exposure'],
  'SIRT3↑ (starter)': ['phys_cold_exposure'],

  'NAD+↑': ['nmn', 'nr', 'nicotinamide'],
  'NAD+↑ (INDIRECT)': ['nicotinamide'],

  'NFκB↓': ['curcumin', 'resveratrol', 'quercetin', 'egcg', 'luteolin', 'sulforaphane'],
  'TNF↓': ['curcumin', 'luteolin', 'omega3'],
  'IL6↓': ['curcumin', 'luteolin', 'omega3'],
  'INFLAMMATION↓': ['omega3', 'phys_sleep_optimization'],
  'PI3K↓': ['curcumin', 'quercetin'],
  'AKT↓': ['quercetin', 'sulforaphane'],
  'AKT↓ (LIGHT SIGNAL)': ['sulforaphane'],

  'AMPK↑': ['berberine', 'phys_cold_exposure', 'phys_zone2', 'phys_time_restricted_feeding'],
  'mTOR↓': ['berberine', 'resveratrol', 'phys_time_restricted_feeding'],
  'SREBF1↓': ['berberine'],
  'AUTOPHAGY↑': ['phys_time_restricted_feeding'],
  'PGC1A↑': ['phys_cold_exposure', 'phys_zone2'],
  'NOREPINEPHRINE↑': ['phys_cold_exposure'],

  'EGFR↓': ['egcg'],
  'EGFR (KINASE)↓': ['egcg'],
  'EGFR↓ (LIGHT SIGNAL)': ['egcg'],
  'ERK1/2↓': ['quercetin'],
  'MAPK↓': ['quercetin', 'egcg', 'luteolin'],

  'PDCD1↓': [],
  'PD-1↓': [],
  'IFNG↑': [],
  'GZMB↑': [],
  'PRF1↑': [],

  'BDNF↑': ['phys_sauna', 'phys_zone2', 'phys_sleep_optimization'],
  'BDNF↑ (LIGHT SIGNAL)': ['apigenin', 'creatine', 'phys_sauna', 'phys_zone2'],
  'HSP70↑': ['phys_sauna'],
  'NITRIC OXIDE↑': ['phys_sauna'],
  'GLUT4↑': ['phys_resistance_training'],
  'INSULIN SENSITIVITY↑': ['phys_zone2', 'phys_resistance_training'],
  'PPARα↑': ['omega3'],
  'NRF2↑': ['sulforaphane'],
  'ATP BUFFER↑': ['creatine'],
  'CORTISOL↓': ['phys_sleep_optimization'],
  'CIRCADIAN ALIGNMENT↑': ['phys_bright_light_am'],
  'CORTISOL AWAKENING RESPONSE↑': ['phys_bright_light_am'],
  'SLEEP DRIVE↑ (NIGHT)': ['phys_bright_light_am'],
};

function buildDiseaseUniverse() {
  const spec = [
    { id: 'oncology', label: 'oncology', colorHint: 'violet', subs: ['solid tumors', 'hematologic', 'lung', 'breast', 'gi', 'cns', 'skin', 'rare oncology'] },
    { id: 'immunology', label: 'immunology', colorHint: 'blue', subs: ['autoimmune', 'allergy', 'inflammation', 'transplant', 'immunodeficiency', 'rare immunologic'] },
    { id: 'endocrine', label: 'endocrine / metabolic', colorHint: 'green', subs: ['diabetes', 'obesity', 'thyroid', 'dyslipidemia', 'metabolic syndrome', 'rare metabolic', 'supportive'] },
    { id: 'cardiology', label: 'cardiology', colorHint: 'red', subs: ['heart failure', 'hypertension', 'arrhythmia', 'atherosclerosis', 'thrombosis', 'rare cardiac'] },
    { id: 'neurology', label: 'neurology', colorHint: 'indigo', subs: ['neurodegeneration', 'demyelination', 'epilepsy', 'migraine', 'stroke', 'rare neurogenetic', 'supportive'] },
    { id: 'psychiatry', label: 'psychiatry', colorHint: 'purple', subs: ['mood', 'anxiety', 'psychosis', 'adhd', 'sleep', 'substance-related'] },
    { id: 'infectious', label: 'infectious disease', colorHint: 'teal', subs: ['viral', 'bacterial', 'fungal', 'parasitic', 'sepsis', 'rare infectious'] },
    { id: 'respiratory', label: 'respiratory', colorHint: 'sky', subs: ['asthma', 'copd', 'fibrosis', 'sleep apnea', 'resp infections'] },
    { id: 'gastro', label: 'gastro / hepatology', colorHint: 'amber', subs: ['ibd', 'liver', 'pancreas', 'ulcer', 'motility', 'rare gi'] },
    { id: 'nephrology', label: 'nephrology', colorHint: 'cyan', subs: ['chronic kidney disease', 'acute kidney injury', 'glomerular', 'dialysis', 'rare renal'] },
    { id: 'hematology', label: 'hematology', colorHint: 'rose', subs: ['anemia', 'coagulation', 'malignancy', 'transfusion', 'rare heme'] },
    { id: 'rheumatology', label: 'rheumatology', colorHint: 'lime', subs: ['rheumatoid', 'lupus', 'gout', 'vasculitis', 'rare rheum'] },
    { id: 'dermatology', label: 'dermatology', colorHint: 'fuchsia', subs: ['psoriasis', 'atopic', 'derm infections', 'wound / scar', 'rare derm'] },
    { id: 'obgyn', label: 'ob-gyn', colorHint: 'pink', subs: ['fertility', 'pregnancy', 'endometriosis', 'pcos'] },
    { id: 'urology', label: 'urology', colorHint: 'blue', subs: ['bph', 'uti', 'stones', 'incontinence'] },
    { id: 'ophthalmology', label: 'ophthalmology', colorHint: 'sky', subs: ['glaucoma', 'retina', 'dry eye', 'infection'] },
    { id: 'ent', label: 'ent', colorHint: 'stone', subs: ['sinus', 'ear', 'throat', 'vertigo'] },
    { id: 'pediatrics', label: 'pediatrics', colorHint: 'emerald', subs: ['infections', 'rare pediatric', 'growth', 'developmental'] },
    { id: 'geriatrics', label: 'geriatrics', colorHint: 'stone', subs: ['frailty', 'polypharmacy', 'cognitive decline', 'fall risk', 'metabolic aging'] },
    { id: 'rare_disease', label: 'rare disease', colorHint: 'purple', subs: ['inborn errors of metabolism', 'rare neurogenetic', 'rare immunologic', 'multisystem rare', 'rare oncology'] },
  ];

  const universe = spec.map((cat) => ({
    id: cat.id,
    label: cat.label,
    colorHint: cat.colorHint,
    children: cat.subs.map((s, idx) => ({
      id: `${cat.id}_${slug(s)}_${idx + 1}`,
      label: s,
      drugs: [],
    })),
  }));

  attachSeedDrugs(universe);
  return universe;
}

function attachSeedDrugs(universe) {
  const onco = universe.find((x) => x.id === 'oncology');
  if (onco) {
    findSub(onco, 'solid tumors').drugs = [
      mkDrug('pembrolizumab', 'pembrolizumab', 'pd-1 blockade with immune-activation readouts.', ['PDCD1↓', 'IFNG↑', 'GZMB↑', 'PRF1↑'], ['PD-1↓'], ['SIRT3↑ (starter)'], ['T CELL CYTOTOXICITY↑', 'IFN GAMMA SIGNALING↑']),
      mkDrug('rapamycin', 'rapamycin', 'mtor-axis control for growth-dependent states.', ['mTOR↓', 'SREBF1↓', 'AKT↓'], ['MTOR COMPLEX↓'], ['SIRT1↑ (starter)'], ['AUTOPHAGY↑', 'CELL GROWTH↓']),
    ];
    findSub(onco, 'hematologic').drugs = [
      mkDrug('imatinib', 'imatinib', 'bcr-abl / kit / pdgfra anchor drug for overlap testing.', ['BCR-ABL↓', 'KIT↓', 'PDGFRA↓'], ['KIT↓', 'PDGFRA↓'], ['SIRT1↑ (starter)'], ['MAPK↓', 'CELL PROLIFERATION↓']),
    ];
    findSub(onco, 'lung').drugs = [
      mkDrug('osimertinib', 'osimertinib', 'egfr inhibitor with mapk / pi3k-akt coverage.', ['EGFR↓', 'ERK1/2↓', 'PI3K↓', 'AKT↓'], ['EGFR (KINASE)↓'], ['SIRT1↑ (SECONDARY starter)'], ['MAPK↓', 'PI3K-AKT↓']),
    ];
    findSub(onco, 'breast').drugs = [
      mkDrug('tamoxifen', 'tamoxifen', 'er-axis control for hormone-driven breast states.', ['ESR1↓', 'BCL2↓', 'CCND1↓'], ['ERα↓'], ['SIRT1↑ (starter)'], ['ESTROGEN RESPONSE↓']),
    ];
    findSub(onco, 'gi').drugs = [
      mkDrug('bevacizumab', 'bevacizumab', 'vegf-axis angiogenesis blocker.', ['VEGFA↓'], ['VEGFR SIGNALING↓'], [], ['ANGIOGENESIS↓']),
      mkDrug('metformin', 'metformin', 'ampk-leaning metabolic control with mtor downward pressure.', ['AMPK↑', 'mTOR↓', 'SREBF1↓'], ['METABOLIC STRESS SENSOR↑'], ['SIRT1↑ (SECONDARY starter)'], ['AMPK↑', 'METABOLIC CONTROL↑']),
    ];
    findSub(onco, 'rare oncology').drugs = [
      mkDrug('sirolimus', 'sirolimus', 'mTOR inhibitor often relevant to pathway-driven rare-oncology logic.', ['mTOR↓'], ['MTOR COMPLEX↓'], [], ['AUTOPHAGY↑', 'CELL GROWTH↓']),
      mkDrug('imatinib', 'imatinib', 'targeted kinase anchor used as a fast rare-oncology starter match.', ['KIT↓', 'PDGFRA↓', 'MAPK↓'], ['KIT↓'], ['SIRT1↑ (starter)'], ['CELL PROLIFERATION↓', 'MAPK↓']),
    ];
  }

  const endocrine = universe.find((x) => x.id === 'endocrine');
  if (endocrine) {
    findSub(endocrine, 'diabetes').drugs = [
      mkDrug('metformin', 'metformin', 'ampk activator starter.', ['AMPK↑', 'mTOR↓', 'SREBF1↓'], ['METABOLIC STRESS SENSOR↑'], [], ['AMPK↑', 'GLUCOSE CONTROL↑']),
      mkDrug('semaglutide', 'semaglutide', 'glp-1 receptor agonist.', ['APPETITE↓ (starter)', 'INSULIN SECRETION↑ (starter)'], ['GLP1R↑'], [], ['WEIGHT↓', 'GLUCOSE CONTROL↑']),
    ];
    findSub(endocrine, 'dyslipidemia').drugs = [
      mkDrug('atorvastatin', 'atorvastatin', 'hmgcr inhibitor.', ['HMGCR↓'], ['LDL RECEPTOR CLEARANCE↑ (starter)'], [], ['CHOLESTEROL SYNTHESIS↓']),
      mkDrug('evolocumab', 'evolocumab', 'pcsk9 inhibitor.', ['PCSK9↓'], ['LDL RECEPTOR RECYCLING↑'], [], ['LDL-C↓']),
    ];
    findSub(endocrine, 'metabolic syndrome').drugs = [
      mkDrug('metformin', 'metformin', 'metabolic anchor.', ['AMPK↑', 'mTOR↓'], [], [], ['AMPK↑']),
      mkDrug('pioglitazone', 'pioglitazone', 'ppar-gamma agonist.', ['PPARγ↑'], [], [], ['INSULIN SENSITIVITY↑']),
    ];
  }

  const neuro = universe.find((x) => x.id === 'neurology');
  if (neuro) {
    findSub(neuro, 'epilepsy').drugs = [
      mkDrug('valproate', 'valproate', 'hdac / gsk3b / creb leaning neuro seed.', ['HDAC2↓', 'GSK3B↓', 'CREB1↑'], [], [], ['NEURONAL EXCITABILITY↓']),
    ];
    findSub(neuro, 'neurodegeneration').drugs = [
      mkDrug('riluzole', 'riluzole', 'glutamate-handling neuroprotective seed.', ['SLC1A2↑'], [], [], ['EXCITOTOXICITY↓']),
      mkDrug('lithium', 'lithium', 'gsk3b / creb anchor for neuro-support reasoning.', ['GSK3B↓', 'CREB1↑'], [], [], ['NEUROPLASTICITY↑']),
    ];
    findSub(neuro, 'rare neurogenetic').drugs = [
      mkDrug('nusinersen', 'nusinersen', 'splice-modifying sma anchor.', ['SMN↑ (starter)'], [], [], ['MOTOR NEURON SUPPORT↑']),
      mkDrug('riluzole', 'riluzole', 'glutamate-handling neuro seed.', ['SLC1A2↑'], [], [], ['EXCITOTOXICITY↓']),
    ];
    findSub(neuro, 'migraine').drugs = [
      mkDrug('erenumab', 'erenumab', 'cgrp-axis blocker.', ['CGRP SIGNALING↓'], ['CGRP RECEPTOR↓'], [], ['MIGRAINE DRIVE↓']),
    ];
  }

  const psych = universe.find((x) => x.id === 'psychiatry');
  if (psych) {
    findSub(psych, 'mood').drugs = [
      mkDrug('lithium', 'lithium', 'mood-stabilizing gsk3b / creb seed.', ['GSK3B↓', 'CREB1↑'], [], [], ['NEUROPLASTICITY↑']),
    ];
    findSub(psych, 'sleep').drugs = [
      mkDrug('melatonin', 'melatonin', 'circadian-alignment starter.', ['CIRCADIAN ALIGNMENT↑'], ['MT1/MT2↑'], [], ['SLEEP ONSET↑']),
    ];
  }

  const immunology = universe.find((x) => x.id === 'immunology');
  if (immunology) {
    findSub(immunology, 'autoimmune').drugs = [
      mkDrug('adalimumab', 'adalimumab', 'tnf blockade seed.', ['TNF↓'], ['TNF RECEPTOR SIGNALING↓'], [], ['INFLAMMATION↓']),
      mkDrug('tofacitinib', 'tofacitinib', 'jak inhibitor seed.', ['JAK-STAT↓ (starter)'], [], [], ['CYTOKINE SIGNALING↓']),
    ];
    findSub(immunology, 'transplant').drugs = [
      mkDrug('sirolimus', 'sirolimus', 'mtor suppression seed.', ['mTOR↓'], [], [], ['T CELL PROLIFERATION↓']),
    ];
    findSub(immunology, 'rare immunologic').drugs = [
      mkDrug('sirolimus', 'sirolimus', 'pathway-first rare immunologic starter.', ['mTOR↓'], [], [], ['AUTOPHAGY↑', 'IMMUNE MODULATION']),
      mkDrug('anakinra', 'anakinra', 'il-1 blockade seed.', ['IL1 SIGNALING↓'], ['IL1R↓'], [], ['INFLAMMATION↓']),
    ];
  }

  const cardio = universe.find((x) => x.id === 'cardiology');
  if (cardio) {
    findSub(cardio, 'atherosclerosis').drugs = [
      mkDrug('atorvastatin', 'atorvastatin', 'lipid-lowering statin seed.', ['HMGCR↓'], [], [], ['CHOLESTEROL SYNTHESIS↓']),
      mkDrug('evolocumab', 'evolocumab', 'pcsk9 seed.', ['PCSK9↓'], [], [], ['LDL-C↓']),
    ];
    findSub(cardio, 'heart failure').drugs = [
      mkDrug('dapagliflozin', 'dapagliflozin', 'sglt2 seed with cardio-metabolic interest.', ['SGLT2↓ (starter)'], [], [], ['CARDIORENAL STRESS↓']),
    ];
  }

  const rare = universe.find((x) => x.id === 'rare_disease');
  if (rare) {
    findSub(rare, 'inborn errors of metabolism').drugs = [
      mkDrug('miglustat', 'miglustat', 'glycosphingolipid synthesis seed.', ['GLYCOSPHINGOLIPID SYNTHESIS↓ (starter)'], [], [], ['SUBSTRATE REDUCTION']),
      mkDrug('nitisinone', 'nitisinone', 'metabolic block seed.', ['TYROSINE PATHWAY BLOCK↓ (starter)'], [], [], ['TOXIC METABOLITE↓']),
    ];
    findSub(rare, 'rare neurogenetic').drugs = [
      mkDrug('nusinersen', 'nusinersen', 'sma seed.', ['SMN↑ (starter)'], [], [], ['MOTOR NEURON SUPPORT↑']),
      mkDrug('riluzole', 'riluzole', 'glutamate-handling seed.', ['SLC1A2↑'], [], [], ['EXCITOTOXICITY↓']),
    ];
    findSub(rare, 'rare immunologic').drugs = [
      mkDrug('sirolimus', 'sirolimus', 'mTOR seed for pathway-driven rare immunologic states.', ['mTOR↓'], [], [], ['AUTOPHAGY↑']),
      mkDrug('anakinra', 'anakinra', 'il-1 blockade seed.', ['IL1 SIGNALING↓'], [], [], ['INFLAMMATION↓']),
    ];
    findSub(rare, 'multisystem rare').drugs = [
      mkDrug('sirolimus', 'sirolimus', 'multisystem rare starter where mtor logic is present.', ['mTOR↓'], [], [], ['CELL GROWTH↓']),
      mkDrug('lithium', 'lithium', 'neuro-support starter for mixed central biology.', ['GSK3B↓', 'CREB1↑'], [], [], ['NEUROPLASTICITY↑']),
    ];
    findSub(rare, 'rare oncology').drugs = [
      mkDrug('sirolimus', 'sirolimus', 'rare-oncology seed.', ['mTOR↓'], [], [], ['AUTOPHAGY↑']),
      mkDrug('imatinib', 'imatinib', 'rare-oncology kinase seed.', ['KIT↓', 'PDGFRA↓'], [], [], ['MAPK↓']),
    ];
  }
}

function findSub(cat, label) {
  const hit = (cat.children || []).find((x) => x.label === label);
  if (!hit) throw new Error(`missing subcategory: ${cat.id} -> ${label}`);
  return hit;
}

function mkDrug(id, name, summary, genes = [], receptors = [], sirtuins = [], pathways = []) {
  return {
    id,
    name,
    summary,
    activates: { genes, receptors, sirtuins, pathways },
  };
}

function demoTargetsFor(diseaseId) {
  if (diseaseId === 'oncology') {
    return {
      genes: ['EGFR↓', 'PI3K↓', 'AKT↓', 'P53↑ (starter)'],
      receptors: ['EGFR (KINASE)↓', 'VEGFR↓ (starter)'],
      sirtuins: ['SIRT1↑ (starter)'],
      pathways: ['MAPK↓', 'PI3K-AKT↓'],
    };
  }
  if (diseaseId === 'immunology') {
    return {
      genes: ['TNF↓', 'IL6↓', 'NFκB↓', 'IFNG↑ (starter)'],
      receptors: ['PD-1↓ (starter)', 'TNFR↓ (starter)'],
      sirtuins: ['SIRT3↑ (starter)'],
      pathways: ['NFκB↓', 'JAK-STAT↓ (starter)'],
    };
  }
  if (diseaseId === 'endocrine') {
    return {
      genes: ['AMPK↑', 'mTOR↓', 'SREBF1↓'],
      receptors: ['INSR SIGNALING↑ (starter)'],
      sirtuins: ['SIRT1↑ (SECONDARY starter)'],
      pathways: ['AMPK↑', 'mTOR↓'],
    };
  }
  if (diseaseId === 'rare_disease') {
    return {
      genes: ['mTOR↓', 'GSK3B↓', 'CREB1↑', 'BDNF↑ (LIGHT SIGNAL)'],
      receptors: ['MTOR COMPLEX↓'],
      sirtuins: ['SIRT3↑ (starter)'],
      pathways: ['AUTOPHAGY↑', 'NEUROPLASTICITY↑'],
    };
  }
  return {
    genes: ['NFκB↓', 'IL6↓ (starter)', 'OX STRESS↓ (starter)'],
    receptors: ['RECEPTOR X↓ (starter)'],
    sirtuins: ['SIRT1↑ (starter)'],
    pathways: ['SYSTEMIC FX↑ (starter)'],
  };
}

function slug(s) {
  return String(s || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}

export const DRUG_LIBRARY = [
  { id: 'imatinib', name: 'imatinib', class: 'tyrosine kinase inhibitor', targets: ['BCR-ABL', 'KIT', 'PDGFRA'], pathways: ['MAPK', 'cell proliferation'], commonEffects: ['edema', 'fatigue'], candidateMimics: ['quercetin', 'resveratrol'] },
  { id: 'rapamycin', name: 'rapamycin', class: 'mTOR inhibitor', targets: ['mTOR'], pathways: ['autophagy', 'cell growth'], commonEffects: ['immunosuppression'], candidateMimics: ['berberine', 'resveratrol', 'time-restricted feeding'] },
  { id: 'sirolimus', name: 'sirolimus', class: 'mTOR inhibitor', targets: ['mTOR'], pathways: ['autophagy', 'cell growth'], commonEffects: ['mouth ulcers', 'immunosuppression'], candidateMimics: ['berberine', 'resveratrol', 'time-restricted feeding'] },
  { id: 'metformin', name: 'metformin', class: 'ampk activator', targets: ['AMPK'], pathways: ['metabolism', 'longevity'], commonEffects: ['gi upset'], candidateMimics: ['berberine', 'zone 2 endurance'] },
  { id: 'osimertinib', name: 'osimertinib', class: 'egfr inhibitor', targets: ['EGFR'], pathways: ['MAPK', 'PI3K-AKT'], commonEffects: ['rash', 'diarrhea'], candidateMimics: ['egcg', 'quercetin'] },
  { id: 'pembrolizumab', name: 'pembrolizumab', class: 'pd-1 inhibitor', targets: ['PDCD1'], pathways: ['t-cell activation'], commonEffects: ['immune toxicity'], candidateMimics: ['none'] },
  { id: 'tamoxifen', name: 'tamoxifen', class: 'serm', targets: ['ESR1'], pathways: ['estrogen response'], commonEffects: ['hot flashes', 'thrombosis'], candidateMimics: ['lignans'] },
  { id: 'lithium', name: 'lithium', class: 'mood stabilizer', targets: ['GSK3B'], pathways: ['neuroplasticity'], commonEffects: ['tremor', 'thyroid effects'], candidateMimics: ['creatine', 'sauna (supportive)'] },
  { id: 'valproate', name: 'valproate', class: 'broad antiseizure', targets: ['HDAC2', 'GSK3B'], pathways: ['neuronal excitability'], commonEffects: ['weight gain', 'hepatotoxicity'], candidateMimics: ['curcumin', 'luteolin'] },
  { id: 'riluzole', name: 'riluzole', class: 'glutamate modulator', targets: ['SLC1A2'], pathways: ['excitotoxicity'], commonEffects: ['fatigue', 'liver enzyme rise'], candidateMimics: ['creatine', 'sleep optimization'] },
  { id: 'atorvastatin', name: 'atorvastatin', class: 'statin', targets: ['HMGCR'], pathways: ['cholesterol synthesis'], commonEffects: ['myalgia'], candidateMimics: ['omega-3'] },
  { id: 'evolocumab', name: 'evolocumab', class: 'pcsk9 inhibitor', targets: ['PCSK9'], pathways: ['ldl receptor recycling'], commonEffects: ['injection site reaction'], candidateMimics: ['none'] },
  { id: 'semaglutide', name: 'semaglutide', class: 'glp-1 receptor agonist', targets: ['GLP1R'], pathways: ['appetite regulation'], commonEffects: ['nausea'], candidateMimics: ['time-restricted feeding (partial)', 'sleep optimization (supportive)'] },
  { id: 'nusinersen', name: 'nusinersen', class: 'antisense oligonucleotide', targets: ['SMN'], pathways: ['motor neuron support'], commonEffects: ['headache', 'procedural burden'], candidateMimics: ['none'] },
  { id: 'miglustat', name: 'miglustat', class: 'substrate reduction therapy', targets: ['glycosphingolipid synthesis'], pathways: ['lysosomal burden'], commonEffects: ['diarrhea'], candidateMimics: ['none'] },
];

export const TRAINING_OVERVIEW = [
  { id: 'rare', name: 'Rare disease engine', runs: 79, storedCases: 79, lastUpdate: '1970-2005 window', confidence: 'high', topPattern: 'Primary-first coverage then deviation fill.', improved: 'Historical replay logic is now stored as reusable hit logic.', summary: 'Primary candidate, deviation map, add-on path, simulation memory.' },
  { id: 'drug', name: 'Drug mimic engine', runs: 31, storedCases: 22, lastUpdate: 'expanded seeded drug + physiology library', confidence: 'medium', topPattern: 'Target overlap plus stack risk filtering, now with physiology mimics.', improved: 'Real starter drugs now seed more domains and physiology can be selected in the same stack.', summary: 'Drug targets, physiology / compound overlap, stack control, early-kill ideas.' },
  { id: 'evidence', name: 'Evidence engine', runs: 11, storedCases: 9, lastUpdate: 'compound compare seed', confidence: 'medium', topPattern: 'Objective literature vs subjective user signal.', improved: 'Layout ready for the existing subjective vs objective engine.', summary: 'Compare literature signal and real-world sentiment side by side.' },
  { id: 'safeguard', name: 'Safeguard engine', runs: 18, storedCases: 12, lastUpdate: 'protocol patterns', confidence: 'medium', topPattern: 'Frequent human-error paths become prevention checklists.', improved: 'Failure causes and savings estimates are visible in one pass.', summary: 'Translate protocol risk into short, usable deviation checklists.' },
];

export const EVIDENCE_STARTERS = [
  { compound: 'berberine', context: 'metabolic syndrome', targets: ['AMPK', 'mTOR'] },
  { compound: 'curcumin', context: 'systemic inflammation', targets: ['NFkB', 'TNF', 'IL6'] },
  { compound: 'resveratrol', context: 'longevity / neuroprotection', targets: ['SIRT1', 'NFkB'] },
  { compound: 'egcg', context: 'egfr-driven oncology', targets: ['EGFR', 'MAPK'] },
];


// launch-ready expansion: diet + physiology objective evidence anchors.
COMPOUND_DB.push(
  {
    id: 'diet_ketogenic',
    name: 'ketogenic diet',
    kind: 'diet',
    targets: ['mTOR↓ (CONTEXT)', 'AMPK↑ (CONTEXT)', 'KETONES↑', 'NEURONAL EXCITABILITY↓'],
    tags: ['diet', 'ketogenic'],
    liverLoad: 0,
    nadBoost: 0,
    cypFlags: [],
    notes: 'diet mimic entry.',
  },
  {
    id: 'diet_time_restricted',
    name: 'time-restricted feeding',
    kind: 'diet',
    targets: ['AMPK↑', 'mTOR↓', 'AUTOPHAGY↑', 'BDNF↑ (LIGHT SIGNAL)'],
    tags: ['diet', 'fasting'],
    liverLoad: 0,
    nadBoost: 0,
    cypFlags: [],
    notes: 'diet mimic entry.',
  },
  {
    id: 'diet_low_glycemic',
    name: 'low-glycemic diet',
    kind: 'diet',
    targets: ['INSULIN SENSITIVITY↑', 'GLUCOSE VARIABILITY↓', 'AMPK↑ (LIGHT SIGNAL)'],
    tags: ['diet', 'metabolic'],
    liverLoad: 0,
    nadBoost: 0,
    cypFlags: [],
    notes: 'diet mimic entry.',
  },
  {
    id: 'diet_mediterranean',
    name: 'mediterranean-style diet',
    kind: 'diet',
    targets: ['INFLAMMATION↓', 'PPARα↑', 'TNF↓', 'IL6↓'],
    tags: ['diet', 'anti_inflammatory'],
    liverLoad: 0,
    nadBoost: 0,
    cypFlags: [],
    notes: 'diet mimic entry.',
  },
  {
    id: 'phys_hiit',
    name: 'hiit / vigorous intervals',
    kind: 'physiology',
    targets: ['AMPK↑', 'PGC1A↑', 'INSULIN SENSITIVITY↑', 'BDNF↑ (LIGHT SIGNAL)'],
    tags: ['physiology', 'exercise'],
    liverLoad: 0,
    nadBoost: 0,
    cypFlags: [],
    notes: 'physiology mimic entry.',
  },
  {
    id: 'phys_daylight_walk',
    name: 'morning daylight walk',
    kind: 'physiology',
    targets: ['CIRCADIAN ALIGNMENT↑', 'BDNF↑ (LIGHT SIGNAL)', 'INSULIN SENSITIVITY↑'],
    tags: ['physiology', 'circadian', 'exercise'],
    liverLoad: 0,
    nadBoost: 0,
    cypFlags: [],
    notes: 'physiology mimic entry.',
  }
);

Object.assign(TARGET_INDEX, {
  'KETONES↑': ['diet_ketogenic'],
  'NEURONAL EXCITABILITY↓': ['diet_ketogenic'],
  'mTOR↓ (CONTEXT)': ['diet_ketogenic'],
  'AMPK↑ (CONTEXT)': ['diet_ketogenic'],
  'GLUCOSE VARIABILITY↓': ['diet_low_glycemic'],
  'AMPK↑ (LIGHT SIGNAL)': ['diet_low_glycemic'],
  'INSULIN SENSITIVITY↑': ['phys_zone2', 'phys_resistance_training', 'diet_low_glycemic', 'phys_hiit', 'phys_daylight_walk'],
  'AUTOPHAGY↑': ['phys_time_restricted_feeding', 'diet_time_restricted'],
  'AMPK↑': ['berberine', 'phys_cold_exposure', 'phys_zone2', 'phys_time_restricted_feeding', 'diet_time_restricted', 'phys_hiit'],
  'mTOR↓': ['berberine', 'resveratrol', 'phys_time_restricted_feeding', 'diet_time_restricted', 'diet_ketogenic'],
  'BDNF↑': ['phys_sauna', 'phys_zone2', 'phys_sleep_optimization', 'diet_time_restricted'],
  'BDNF↑ (LIGHT SIGNAL)': ['apigenin', 'creatine', 'phys_sauna', 'phys_zone2', 'diet_time_restricted', 'phys_hiit', 'phys_daylight_walk'],
  'PPARα↑': ['omega3', 'diet_mediterranean'],
  'INFLAMMATION↓': ['omega3', 'phys_sleep_optimization', 'diet_mediterranean'],
  'TNF↓': ['curcumin', 'luteolin', 'omega3', 'diet_mediterranean'],
  'IL6↓': ['curcumin', 'luteolin', 'omega3', 'diet_mediterranean'],
  'CIRCADIAN ALIGNMENT↑': ['phys_bright_light_am', 'phys_daylight_walk'],
});

DRUG_LIBRARY.push(
  { id: 'canagliflozin', name: 'canagliflozin', class: 'sglt2 inhibitor', targets: ['SGLT2'], pathways: ['glycosuria', 'metabolic stress'], commonEffects: ['genital infection risk'], candidateMimics: ['ketogenic diet', 'time-restricted feeding', 'zone 2 endurance'] },
  { id: 'empagliflozin', name: 'empagliflozin', class: 'sglt2 inhibitor', targets: ['SGLT2'], pathways: ['glycosuria', 'metabolic stress'], commonEffects: ['genital infection risk'], candidateMimics: ['ketogenic diet', 'time-restricted feeding', 'zone 2 endurance'] },
  { id: 'everolimus', name: 'everolimus', class: 'mTOR inhibitor', targets: ['mTOR'], pathways: ['autophagy', 'cell growth'], commonEffects: ['stomatitis', 'immunosuppression'], candidateMimics: ['berberine', 'resveratrol', 'time-restricted feeding', 'ketogenic diet'] },
  { id: 'acarbose', name: 'acarbose', class: 'alpha-glucosidase inhibitor', targets: ['post-prandial glucose handling'], pathways: ['glycemic variability'], commonEffects: ['gi upset'], candidateMimics: ['low-glycemic diet', 'time-restricted feeding'] },
  { id: 'fluoxetine', name: 'fluoxetine', class: 'ssri', targets: ['SERT'], pathways: ['monoamine signaling', 'neuroplasticity'], commonEffects: ['nausea', 'insomnia'], candidateMimics: ['sleep optimization', 'zone 2 endurance', 'bright light morning'] },
  { id: 'bupropion', name: 'bupropion', class: 'ndri', targets: ['DAT', 'NET'], pathways: ['catecholamine signaling'], commonEffects: ['insomnia', 'anxiety'], candidateMimics: ['bright light morning', 'zone 2 endurance', 'cold exposure / cold plunge'] },
  { id: 'levetiracetam', name: 'levetiracetam', class: 'antiseizure', targets: ['SV2A'], pathways: ['neuronal excitability'], commonEffects: ['somnolence', 'irritability'], candidateMimics: ['ketogenic diet'] },
  { id: 'donepezil', name: 'donepezil', class: 'acetylcholinesterase inhibitor', targets: ['AChE'], pathways: ['cholinergic tone'], commonEffects: ['nausea', 'bradycardia'], candidateMimics: ['morning daylight walk', 'zone 2 endurance'] }
);

export const OBJECTIVE_EVIDENCE_INDEX = {
  berberine: {
    title: 'berberine',
    mechanism: 'AMPK-leaning metabolic support with literature around mTOR-axis modulation.',
    refs: [
      { label: 'Frontiers 2023 · lysosomal AMPK mechanism', url: 'https://www.frontiersin.org/journals/pharmacology/articles/10.3389/fphar.2023.1148611/full' },
      { label: 'Springer 2025 · PI3K/AKT/mTOR chapter', url: 'https://link.springer.com/chapter/10.1007/978-981-95-4751-7_8' },
    ],
  },
  curcumin: {
    title: 'curcumin',
    mechanism: 'NF-kB / inflammatory-pathway anchor with broad mechanistic literature.',
    refs: [
      { label: 'Springer 2024 · NF-kB review', url: 'https://link.springer.com/article/10.1007/s10787-024-01492-1' },
      { label: 'Acta Biochim Biophys Sin 2012 · NF-kB tumor model', url: 'https://academic.oup.com/abbs/article/44/10/847/1049' },
    ],
  },
  resveratrol: {
    title: 'resveratrol',
    mechanism: 'SIRT1-centered polyphenol anchor with indirect PI3K-AKT-mTOR pathway adjacency in the current starter library.',
    refs: [
      { label: 'JBC · human SIRT1 activation mechanism', url: 'https://www.jbc.org/article/S0021-9258%2820%2965895-1/fulltext' },
      { label: 'Springer 2024 · resveratrol–SIRT1 review', url: 'https://link.springer.com/article/10.1007/s00210-024-03319-w' },
    ],
  },
  egcg: {
    title: 'EGCG',
    mechanism: 'EGFR / MAPK / PI3K-AKT-mTOR-interacting green tea catechin literature anchor.',
    refs: [
      { label: 'Molecules 2023 · EGCG therapeutic potential in cancer', url: 'https://www.mdpi.com/1420-3049/28/13/5246' },
      { label: 'Exploration 2024 · EGCG in human diseases', url: 'https://link.springer.com/article/10.1186/s43556-024-00240-9' },
    ],
  },
  sulforaphane: {
    title: 'sulforaphane',
    mechanism: 'Nrf2-centered cruciferous-derived signal.',
    refs: [
      { label: 'Inflammopharmacology 2024 · sulforaphane / Nrf2 review', url: 'https://link.springer.com/article/10.1007/s10787-024-01506-y' },
      { label: 'Antioxidants 2024 · Nrf2 pathway activation study', url: 'https://www.mdpi.com/2076-3921/14/3/308' },
    ],
  },
  omega3: {
    title: 'omega-3',
    mechanism: 'PPAR / inflammatory-lipid support anchor.',
    refs: [
      { label: 'Frontiers 2023 · PPAR-a / PPAR-g meta-analysis', url: 'https://www.frontiersin.org/journals/nutrition/articles/10.3389/fnut.2023.1202688/full' },
      { label: 'NFS Journal 2021 · gene expression meta-analysis', url: 'https://www.sciencedirect.com/science/article/pii/S1756464621002681' },
    ],
  },
  creatine: {
    title: 'creatine',
    mechanism: 'bioenergetic buffer with emerging brain / BDNF-support literature.',
    refs: [
      { label: 'Frontiers 2025 · creatine and muscle-brain axis', url: 'https://www.frontiersin.org/journals/nutrition/articles/10.3389/fnut.2025.1579204/full' },
      { label: 'Nutrition Reviews 2023 · memory meta-analysis', url: 'https://academic.oup.com/nutritionreviews/article/81/4/416/6671817' },
    ],
  },
  diet_ketogenic: {
    title: 'ketogenic diet',
    mechanism: 'ketosis-driven dietary therapy with strong epilepsy literature and mechanistic signaling interest.',
    refs: [
      { label: 'Nutrients 2025 · ketogenic diet in genetically confirmed DRE', url: 'https://www.mdpi.com/2072-6643/17/6/979' },
      { label: 'Frontiers 2025 · seizure-frequency meta-analysis', url: 'https://www.frontiersin.org/journals/nutrition/articles/10.3389/fnut.2025.1634041/full' },
    ],
  },
  diet_time_restricted: {
    title: 'time-restricted feeding',
    mechanism: 'feeding-window intervention linked to autophagy / AMPK-mTOR style literature.',
    refs: [
      { label: 'Mech Ageing Dev 2024 · neuroprotection review', url: 'https://www.sciencedirect.com/science/article/pii/S0014488624003716' },
      { label: 'Current Nutrition Reports 2025 · fasting-autophagy review', url: 'https://link.springer.com/article/10.1007/s13668-025-00666-9' },
    ],
  },
  diet_low_glycemic: {
    title: 'low-glycemic diet',
    mechanism: 'glycemic-variability and insulin-sensitivity support.',
    refs: [
      { label: 'Nutrients 2024 · TRF metabolic review', url: 'https://www.mdpi.com/2072-6643/16/11/1721' },
      { label: 'Nutrients 2025 · LGIT discussed inside KD review', url: 'https://www.mdpi.com/2072-6643/17/6/979' },
    ],
  },
  diet_mediterranean: {
    title: 'mediterranean-style diet',
    mechanism: 'anti-inflammatory / cardiometabolic dietary pattern.',
    refs: [
      { label: 'Frontiers 2023 · omega-3 / PPAR signaling meta-analysis', url: 'https://www.frontiersin.org/journals/nutrition/articles/10.3389/fnut.2023.1202688/full' },
      { label: 'Journal of Hepatology review · PPARa action', url: 'https://www.journal-of-hepatology.eu/article/S0168-8278%2814%2900806-X/fulltext' },
    ],
  },
  phys_sauna: {
    title: 'heat exposure / sauna',
    mechanism: 'heat-shock / BDNF-style supportive physiology.',
    refs: [
      { label: 'Exp Gerontol 2021 · sauna and healthspan review', url: 'https://www.sciencedirect.com/science/article/pii/S0531556521002916' },
      { label: 'J Neurophysiol 2025 · heat therapy increases HSP70 and BDNF', url: 'https://journals.physiology.org/doi/full/10.1152/jn.00301.2025' },
    ],
  },
  phys_cold_exposure: {
    title: 'cold exposure / cold plunge',
    mechanism: 'cold-response physiology linked to PGC-1a and adaptive thermogenesis literature.',
    refs: [
      { label: 'Adv Physiol Educ · PGC-1a induced by cold exposure', url: 'https://journals.physiology.org/doi/full/10.1152/advan.00052.2006' },
      { label: 'Am J Clin Nutr · PGC-1a regulation review', url: 'https://www.sciencedirect.com/science/article/pii/S0002916523021688' },
    ],
  },
  phys_zone2: {
    title: 'zone 2 endurance',
    mechanism: 'exercise anchor with BDNF and metabolic signaling literature.',
    refs: [
      { label: '2023 review · physical exercise on BDNF', url: 'https://www.sciencedirect.com/science/article/pii/S2949834123000168' },
      { label: 'Frontiers 2024 · exercise and BDNF review', url: 'https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2024.1505879/full' },
    ],
  },
  phys_hiit: {
    title: 'hiit / vigorous intervals',
    mechanism: 'exercise-driven AMPK / PGC-1a / BDNF supportive physiology.',
    refs: [
      { label: '2023 review · physical exercise on BDNF', url: 'https://www.sciencedirect.com/science/article/pii/S2949834123000168' },
      { label: 'Frontiers 2024 · exercise and BDNF review', url: 'https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2024.1505879/full' },
    ],
  },
  phys_bright_light_am: {
    title: 'bright light morning',
    mechanism: 'circadian-alignment supportive intervention.',
    refs: [
      { label: 'Sleep Med Rev · light therapies improve sleep timing', url: 'https://www.sciencedirect.com/science/article/pii/S1087079218301886' },
      { label: 'Sleep 2022 · natural light exposure and circadian rhythm review', url: 'https://academic.oup.com/sleep/article/45/7/zsac094/6571981' },
    ],
  },
  phys_daylight_walk: {
    title: 'morning daylight walk',
    mechanism: 'combined circadian + mild exercise support.',
    refs: [
      { label: 'Sleep 2022 · natural light exposure and circadian rhythm review', url: 'https://academic.oup.com/sleep/article/45/7/zsac094/6571981' },
      { label: 'Frontiers 2024 · exercise and BDNF review', url: 'https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2024.1505879/full' },
    ],
  },
  phys_sleep_optimization: {
    title: 'sleep optimization',
    mechanism: 'sleep-quality support with BDNF-linked literature context.',
    refs: [
      { label: 'Neurochem Res 2020 · BDNF between sleep and stress', url: 'https://link.springer.com/article/10.1007/s11064-019-02914-1' },
      { label: 'Sleep Med Rev 2023 · peripheral BDNF in insomnia meta-analysis', url: 'https://www.sciencedirect.com/science/article/pii/S1087079222001514' },
    ],
  },
};

export function getObjectiveEvidenceForId(id) {
  return OBJECTIVE_EVIDENCE_INDEX[String(id || '').trim()] || null;
}

export function getAllSeedDrugEntries() {
  const rows = [];
  for (const disease of DISEASE_UNIVERSE) {
    for (const sub of disease.children || []) {
      for (const drug of sub.drugs || []) {
        rows.push({
          diseaseId: disease.id,
          diseaseLabel: disease.label,
          subcatId: sub.id,
          subcatLabel: sub.label,
          drugId: drug.id,
          drugName: drug.name,
          summary: drug.summary || '',
        });
      }
    }
  }
  const seen = new Set();
  return rows.filter((row) => {
    const key = `${row.diseaseId}::${row.subcatId}::${row.drugId}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}


export const SIDE_EFFECT_SUPPORT_INDEX = {
  sirolimus: {
    drug: 'sirolimus',
    className: 'mTOR inhibitor',
    commonEffects: ['mouth ulcers', 'immunosuppression'],
    confidence: 0.74,
    confidenceLabel: 'moderate-high',
    effects: [
      {
        label: 'mouth ulcers / stomatitis',
        mechanism: 'mTOR-pathway suppression can impair mucosal turnover and recovery.',
        physiology: 'oral care protocol, friction reduction, hydration',
        diet: 'soft texture meals during flare, avoid high-irritant acidic intake',
        compound: 'glutamine-supportive logic, oral barrier support',
        medication: 'dexamethasone-style mouthwash protocol review',
        interactionRisk: 'low to moderate',
        evidenceTier: 'human review',
        confidence: 0.78,
        refs: [
          { label: 'Supportive Care in Cancer · mTOR-inhibitor stomatitis review', url: 'https://link.springer.com/article/10.1007/s00520-022-06821-5' },
          { label: 'Annals of Oncology · stomatitis management consensus', url: 'https://www.annalsofoncology.org/article/S0923-7534(19)31640-8/fulltext' },
        ],
      },
      {
        label: 'immune suppression drift',
        mechanism: 'strong mTOR inhibition can narrow immune reserve and wound-response tone.',
        physiology: 'infection surveillance, wound-healing awareness, sleep protection',
        diet: 'protein sufficiency and micronutrient coverage',
        compound: 'none seeded as direct support',
        medication: 'dose review / infection management pathway',
        interactionRisk: 'moderate',
        evidenceTier: 'mechanistic + human review',
        confidence: 0.66,
        refs: [
          { label: 'Drugs · sirolimus safety review', url: 'https://link.springer.com/article/10.2165/00003495-200565030-00004' },
        ],
      },
    ],
  },
  olanzapine: {
    drug: 'olanzapine',
    className: 'second-generation antipsychotic',
    commonEffects: ['weight gain', 'sedation', 'metabolic drift'],
    confidence: 0.72,
    confidenceLabel: 'moderate',
    effects: [
      {
        label: 'weight gain / metabolic drift',
        mechanism: 'histamine and appetite-axis effects can push weight and glucose burden upward.',
        physiology: 'zone 2 endurance + weight monitoring',
        diet: 'mediterranean-style diet, bright light morning',
        compound: 'none seeded as direct support',
        medication: 'metformin adjunctive review anchor',
        interactionRisk: 'moderate',
        evidenceTier: 'human review',
        confidence: 0.7,
        refs: [
          { label: 'Frontiers 2024 · exercise and BDNF review', url: 'https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2024.1404100/full' },
          { label: 'Metformin review and adverse-effect overview', url: 'https://pubmed.ncbi.nlm.nih.gov/27987248/' },
        ],
      },
    ],
  },
  risperidone: {
    drug: 'risperidone',
    className: 'second-generation antipsychotic',
    commonEffects: ['akathisia', 'prolactin drift'],
    confidence: 0.69,
    confidenceLabel: 'moderate',
    effects: [
      {
        label: 'akathisia / motor restlessness',
        mechanism: 'dopamine blockade can create motor inner-restlessness in susceptible patients.',
        physiology: 'sleep stabilization and stimulation-load review',
        diet: 'caffeine moderation if symptomatic',
        compound: 'none seeded as direct support',
        medication: 'beta-blocker / dose review pathway',
        interactionRisk: 'moderate',
        evidenceTier: 'human guideline',
        confidence: 0.67,
        refs: [
          { label: 'BJPsych Advances · akathisia management review', url: 'https://www.cambridge.org/core/journals/bjpsych-advances/article/recognising-and-managing-akathisia-a-clinical-review/5E0A7A4A0E8D5E8E1F5DBA0A5A0E4E6E' },
        ],
      },
    ],
  },
  metformin: {
    drug: 'metformin',
    className: 'AMPK activator',
    commonEffects: ['gi upset'],
    confidence: 0.76,
    confidenceLabel: 'moderate-high',
    effects: [
      {
        label: 'gi intolerance',
        mechanism: 'dose and intestinal glucose-handling shift can create nausea / diarrhea early.',
        physiology: 'slow titration logic, dosing with meals',
        diet: 'low-irritant meals during initiation',
        compound: 'none seeded as direct support',
        medication: 'extended-release formulation review',
        interactionRisk: 'low',
        evidenceTier: 'human review',
        confidence: 0.75,
        refs: [
          { label: 'Metformin review and adverse-effect overview', url: 'https://pubmed.ncbi.nlm.nih.gov/27987248/' },
        ],
      },
    ],
  },
};

export const NEGATIVE_HABIT_LIBRARY = [
  {
    id: 'smoking',
    name: 'nicotine / smoking',
    summary: 'oxidative stress · vascular injury',
    confidence: 0.72,
    signals: ['oxidative stress', 'vascular injury', 'inflammation'],
    impact: 'habit tilts the system toward inflammatory and vascular damage patterns that complicate drug-response logic.',
    offsets: {
      physiology: 'zone 2 endurance, morning daylight walk',
      diet: 'mediterranean-style diet',
      compound: 'omega-3, sulforaphane',
      medication: 'cessation support pathway',
    },
    refs: [
      { title: 'omega-3 evidence anchor', note: 'anti-inflammatory / lipid-support literature starter.', evidenceTier: 'human review', confidence: 0.67, label: 'NFS Journal 2021 · gene expression meta-analysis', url: 'https://www.sciencedirect.com/science/article/pii/S1756464621002681' },
      { title: 'sulforaphane evidence anchor', note: 'nrf2-centered signal support.', evidenceTier: 'mechanistic + human review', confidence: 0.63, label: 'Inflammopharmacology 2024 · sulforaphane / Nrf2 review', url: 'https://link.springer.com/article/10.1007/s10787-024-01506-y' },
    ],
  },
  {
    id: 'sleep',
    name: 'chronic sleep restriction',
    summary: 'cortisol drift · bdnf reduction',
    confidence: 0.71,
    signals: ['circadian drift', 'cortisol load', 'reduced bdnf tone'],
    impact: 'sleep restriction degrades recovery, neuroplasticity, and metabolic reserve.',
    offsets: { physiology: 'fixed wake time, morning daylight, zone 2 exercise', diet: 'late-meal reduction', compound: 'magnesium / glycine review', medication: 'sleep medicine review when indicated' },
    refs: [
      { title: 'exercise and sleep anchor', note: 'exercise supports sleep architecture and next-day function.', evidenceTier: 'human review', confidence: 0.66, label: 'Frontiers 2024 · exercise and BDNF review', url: 'https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2024.1404100/full' },
    ],
  },
  {
    id: 'sedentary',
    name: 'sedentary drift',
    summary: 'insulin resistance · low bdnf',
    confidence: 0.74,
    signals: ['insulin resistance', 'low aerobic reserve', 'bdnf drift'],
    impact: 'low movement compresses metabolic flexibility and neuroplastic support.',
    offsets: { physiology: 'zone 2 endurance, resistance training', diet: 'low-glycemic pattern', compound: 'creatine / omega-3 review', medication: 'none as default' },
    refs: [
      { title: 'creatine evidence anchor', note: 'bioenergetic support literature starter.', evidenceTier: 'human meta-analysis', confidence: 0.62, label: 'Nutrition Reviews 2023 · memory meta-analysis', url: 'https://academic.oup.com/nutritionreviews/article/81/4/416/6671817' },
    ],
  },
  {
    id: 'alcohol',
    name: 'daily alcohol load',
    summary: 'liver load · sleep fragmentation',
    confidence: 0.68,
    signals: ['liver stress', 'sleep fragmentation', 'inflammatory drift'],
    impact: 'daily alcohol adds hepatic burden and blunts recovery quality.',
    offsets: { physiology: 'sleep protection, hydration, training consistency', diet: 'protein sufficiency / liver-friendly pattern', compound: 'none seeded as direct support', medication: 'cessation / reduction pathway when needed' },
    refs: [
      { title: 'liver and sleep anchor', note: 'reduce alcohol burden before stacking hepatically active compounds.', evidenceTier: 'clinical principle', confidence: 0.58, label: 'NIAAA · alcohol and sleep overview', url: 'https://www.niaaa.nih.gov/publications/alcohol-and-sleep' },
    ],
  },
];
