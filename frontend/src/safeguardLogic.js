// frontend/src/safeguardLogic.js

const FAILURE_LIBRARY = [
  {
    id: "freeze_cells_core",
    title: "CELL FREEZING / CRYOPRESERVATION",
    keywords: ["freeze", "freezing", "cryopreserve", "cryopreservation", "dms0", "dmso", "fbs", "mr frosty", "liquid nitrogen", "ln2", "cryovial"],
    commonFailures: [
      { cause: "WRONG FREEZING RATE (TOO FAST / TOO SLOW).", deviation: "USE CONTROLLED RATE (~1°C/MIN) OR VALIDATED DEVICE.", severity: "HIGH" },
      { cause: "WRONG STORAGE TEMPERATURE / LOCATION.", deviation: "VERIFY LN2 VAPOR VS LIQUID PHASE, LOG LOCATION + TEMP.", severity: "HIGH" },
      { cause: "DMSO % MIS-MEASURED OR OLD STOCK.", deviation: "DOUBLE-CHECK FINAL DMSO %, LABEL LOT, LIMIT ROOM-TEMP TIME.", severity: "MED" },
      { cause: "CELLS LEFT TOO LONG IN DMSO BEFORE FREEZE.", deviation: "SET TIMER. MAX ROOM-TEMP EXPOSURE WINDOW.", severity: "MED" },
      { cause: "MISLABELING VIALS / SWAPPED CELL LINES.", deviation: "2-PERSON LABEL CHECK + BARCODE, PHOTO CAPTURE OPTIONAL.", severity: "HIGH" },
    ],
    defaultFailuresPerYear: 5,
    defaultCostPerFailureEUR: 20000,
  },
  {
    id: "cell_culture_core",
    title: "CELL CULTURE / PASSAGING",
    keywords: ["culture", "passage", "passaging", "confluency", "media", "medium", "serum", "incubator", "co2", "contamination", "mycoplasma"],
    commonFailures: [
      { cause: "INCUBATOR SETPOINT DRIFT (CO2 / TEMP / HUMIDITY).", deviation: "DAILY CHECK. WEEKLY CALIBRATION LOG.", severity: "HIGH" },
      { cause: "MYCOPLASMA NOT SCREENED.", deviation: "SCHEDULE ROUTINE TESTING + QUARANTINE NEW LINES.", severity: "HIGH" },
      { cause: "WRONG MEDIA / SUPPLEMENT CONCENTRATION.", deviation: "STANDARDIZED MASTER MIX + SECOND PERSON CHECK.", severity: "MED" },
      { cause: "OVER-TRYPSINIZATION / OVER-STRESS DURING PASSAGE.", deviation: "TIMED PROTOCOL + NEUTRALIZATION CHECKPOINT.", severity: "MED" },
      { cause: "CROSS-CONTAMINATION BETWEEN LINES.", deviation: "ONE LINE AT A TIME + CLEAN ZONE + LABEL RULES.", severity: "HIGH" },
    ],
    defaultFailuresPerYear: 6,
    defaultCostPerFailureEUR: 15000,
  },
  {
    id: "pcr_qpcr",
    title: "PCR / qPCR",
    keywords: ["pcr", "qpcr", "primer", "primers", "ct", "cycling", "taq", "polymerase", "annealing"],
    commonFailures: [
      { cause: "PRIMER DESIGN / SPECIFICITY ISSUE.", deviation: "IN-SILICO CHECK + MELT CURVE + NEGATIVE CONTROL.", severity: "MED" },
      { cause: "CONTAMINATION (AEROSOL / CARRYOVER).", deviation: "SEPARATE PRE/POST AREAS + FILTER TIPS + UV CLEAN.", severity: "HIGH" },
      { cause: "WRONG THERMOCYCLER PROGRAM.", deviation: "LOCK TEMPLATE + VERSION CONTROL PROGRAM SETTINGS.", severity: "MED" },
      { cause: "REAGENT DEGRADATION (FREEZE/THAW).", deviation: "ALIQUOT ENZYMES, TRACK FREEZE/THAW COUNT.", severity: "MED" },
    ],
    defaultFailuresPerYear: 4,
    defaultCostPerFailureEUR: 8000,
  },
  {
    id: "rna_extraction",
    title: "RNA EXTRACTION / RNA-SEQ PREP",
    keywords: ["rna", "rnaseq", "trizol", "lysis", "column", "bioanalyzer", "rin", "degradation"],
    commonFailures: [
      { cause: "RNASE CONTAMINATION.", deviation: "RNASE-FREE ZONE + DEDICATED PIPETTES + GLOVES RULE.", severity: "HIGH" },
      { cause: "LOW RIN / DEGRADATION NOT CAUGHT EARLY.", deviation: "QC CHECKPOINT BEFORE DOWNSTREAM STEPS.", severity: "HIGH" },
      { cause: "WRONG INPUT MASS / NORMALIZATION ERROR.", deviation: "CALC SHEET + DOUBLE CHECK + RECORD RAW VALUES.", severity: "MED" },
    ],
    defaultFailuresPerYear: 3,
    defaultCostPerFailureEUR: 25000,
  },
];

function normalizeText(s) {
  return String(s || "").toLowerCase();
}

function matchLibrary(text) {
  const t = normalizeText(text);
  const scored = FAILURE_LIBRARY.map((x) => {
    const hits = x.keywords.reduce((acc, k) => (t.includes(k) ? acc + 1 : acc), 0);
    return { item: x, hits };
  }).sort((a, b) => b.hits - a.hits);

  const best = scored[0];
  if (!best || best.hits === 0) {
    // DEFAULT TO GENERAL CELL CULTURE WHEN THE TEXT IS TOO SPARSE TO CLASSIFY
    return { item: FAILURE_LIBRARY[1], hits: 0, fallback: true };
  }
  return { item: best.item, hits: best.hits, fallback: false };
}

export function safeguardAnalyze({ experimentText, failuresPerYear, costPerFailureEUR }) {
  const { item, fallback } = matchLibrary(experimentText);

  const fpy = Number.isFinite(+failuresPerYear) && +failuresPerYear > 0 ? +failuresPerYear : item.defaultFailuresPerYear;
  const cpf = Number.isFinite(+costPerFailureEUR) && +costPerFailureEUR > 0 ? +costPerFailureEUR : item.defaultCostPerFailureEUR;

  // USE A CONSERVATIVE AVOIDABLE FRACTION FOR THE HUMAN-ERROR LAYER.
  const avoidableFraction = 0.6;
  const yearlyWaste = Math.round(fpy * cpf);
  const yearlySavingsIfUsed = Math.round(yearlyWaste * avoidableFraction);

  const topFailures = item.commonFailures.slice(0, 5);

  const checklist = topFailures.map((x, idx) => ({
    step: idx + 1,
    text: x.deviation,
    severity: x.severity,
  }));

  return {
    matchedTitle: item.title,
    fallbackUsed: fallback,
    failuresPerYear: fpy,
    costPerFailureEUR: cpf,
    yearlyWasteEUR: yearlyWaste,
    yearlySavingsEUR: yearlySavingsIfUsed,
    topFailures,
    checklist,
  };
}