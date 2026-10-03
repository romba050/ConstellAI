# MEDR5 Atlas hackathon edition

Upload destination: [romba050/ConstellAI — hacknation-buffalo-atlas](https://github.com/romba050/ConstellAI/tree/hacknation-buffalo-atlas). The original MEDR5 baseline is kept on `old-sw`; ConstellAI's existing `main` app is preserved. This branch runs the isolated MEDR5 edition described below.

The original MEDR5 application is preserved. Start the isolated Buffalo edition:

```sh
python hackathon/buffalo_atlas/run.py
```

Open http://127.0.0.1:8795/demo and use **Angelman / UBE3A**. Windows: double-click `START_BUFFALO_ATLAS.cmd`.

Read [the edition README](hackathon/buffalo_atlas/README.md) for setup, preserved/new technology, evidence, tests and limitations.

The default UI is dark. Source inspection includes real PubMed / PMC bibliography, study design, sample context and uncertainty; clinical safety stays separate from mechanistic priority. The official PDF review, 1-minute recording script and dataset reproduction command are in the edition README.

Research decision support — not medical advice.
