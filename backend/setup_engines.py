from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENGINES_DIR = BASE_DIR / "engines"
ENGINES_DIR.mkdir(parents=True, exist_ok=True)

# Put the original engine zips next to this file, then run:
#   python setup_engines.py
# It will unzip into stable folder names the backend expects.

ENGINE_ZIPS = {
    "gene_crossover_engine": ["potential gene crossover experiment - engine.zip"],
    "pubmed_scorer_engine": ["prev research pubmed 2 - scorer (for early kill confirm bias).zip"],
    "compound_subjective_engine": ["supplement_compound - subjective vs objective data.zip"],
    "disease_overlap_engine": ["disease overlap 1 - genes.zip"],
    "orthomolecular_pill_miner_engine": ["orthomolecular molecule pill miner.zip"],
}


def find_zip(name_variants: list[str]) -> Path | None:
    for v in name_variants:
        p = BASE_DIR / v
        if p.exists():
            return p
    # also allow exact with leading tilde
    for v in name_variants:
        p = BASE_DIR / ("~" + v)
        if p.exists():
            return p
    return None


def unzip_flat(zippath: Path, outdir: Path) -> None:
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zippath, "r") as z:
        z.extractall(outdir)

    # Many of your zips contain a single top-level folder. If so, lift it.
    children = [p for p in outdir.iterdir() if p.is_dir()]
    if len(children) == 1:
        inner = children[0]
        # move inner content up
        for item in inner.iterdir():
            shutil.move(str(item), str(outdir / item.name))
        shutil.rmtree(inner)


def main():
    print("[setup] engines dir:", ENGINES_DIR)

    ok = True
    for stable_name, variants in ENGINE_ZIPS.items():
        zp = find_zip(variants)
        if not zp:
            ok = False
            print(f"[missing] place one of these next to setup_engines.py: {variants}")
            continue

        out = ENGINES_DIR / stable_name
        print(f"[unzip] {zp.name} -> {out}")
        unzip_flat(zp, out)

    if not ok:
        print("\n[done] some zips were missing. copy them into backend/ and run again.")
    else:
        print("\n[done] all engines installed.")
        print("next: run backend with: uvicorn app:app --reload --port 8787")


if __name__ == "__main__":
    main()
