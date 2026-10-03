# med-r5 frontend

## run

```bash
npm i
npm run dev
```

## notes

- tab 1: drug mimic workspace (graph, target click, compound selection, interaction review, optimization, hypothesis export).
- tab 2: safeguard rail for protocol review and preventable-failure analysis.
- lm studio: optional. openai-style endpoint `/v1/chat/completions` with `response_format: {type:"json_object"}`.
- exports are framed for research workflow handoff and human review.

## assets

- `public/assets/` includes your MED-R5 concept images.
