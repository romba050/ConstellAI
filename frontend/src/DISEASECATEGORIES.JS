// src/diseaseCategories.js
// generated/maintained list of disease categories (MeSH Diseases tree [C]).
// keep ids lowercase (for your DRUGS.category matching).
// source concept: MeSH "Diseases [C]" tree. update yearly if desired.

export const DISEASE_CATEGORIES = [
  { id: "infections", label: "Infections", mesh: "C01" },
  { id: "virus_diseases", label: "Virus diseases", mesh: "C02" },
  { id: "parasitic_diseases", label: "Parasitic diseases", mesh: "C03" },
  { id: "neoplasms", label: "Neoplasms", mesh: "C04" },

  { id: "musculoskeletal", label: "Musculoskeletal diseases", mesh: "C05" },
  { id: "digestive", label: "Digestive system diseases", mesh: "C06" },
  { id: "stomatognathic", label: "Stomatognathic diseases", mesh: "C07" },
  { id: "respiratory", label: "Respiratory tract diseases", mesh: "C08" },
  { id: "otorhinolaryngologic", label: "Otorhinolaryngologic diseases", mesh: "C09" },
  { id: "nervous_system", label: "Nervous system diseases", mesh: "C10" },
  { id: "eye", label: "Eye diseases", mesh: "C11" },
  { id: "urogenital", label: "Urogenital diseases", mesh: "C12" },
  { id: "male_genital", label: "Male urogenital diseases", mesh: "C13" },
  { id: "female_genital", label: "Female urogenital diseases and pregnancy complications", mesh: "C13" },

  { id: "cardiovascular", label: "Cardiovascular diseases", mesh: "C14" },
  { id: "hematologic", label: "Hemic and lymphatic diseases", mesh: "C15" },
  { id: "congenital", label: "Congenital, hereditary, and neonatal diseases and abnormalities", mesh: "C16" },
  { id: "skin_connective", label: "Skin and connective tissue diseases", mesh: "C17" },
  { id: "nutritional_metabolic", label: "Nutritional and metabolic diseases", mesh: "C18" },
  { id: "endocrine", label: "Endocrine system diseases", mesh: "C19" },
  { id: "immune", label: "Immune system diseases", mesh: "C20" },
  { id: "environmental", label: "Environmentally induced diseases", mesh: "C21" },
  { id: "animal", label: "Animal diseases", mesh: "C22" },
  { id: "pathological_conditions", label: "Pathological conditions, signs and symptoms", mesh: "C23" },
  { id: "occupational", label: "Occupational diseases", mesh: "C24" },
  { id: "chemically_induced", label: "Chemically induced disorders", mesh: "C25" }
];