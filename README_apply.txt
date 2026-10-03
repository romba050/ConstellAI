MED-R5 update pack

Touched files
- backend/app.py
- frontend/src/App.jsx
- frontend/src/RareDiseaseTab.jsx
- frontend/src/apiClient.js

What was added
- rare disease predictor backend endpoints + frontend tab wiring
- rare disease safety-decision inputs for habits/diet + drugs-first deviation strategy
- safeguard tab now uses backend and can store free-text deviation outcomes to memory
- memory summary now exposes safeguard protocol/savings metrics and predictor engine summary
- subj_obj tab now supports medicine / compound / physiology / diet query mode selection

How to apply
1. Open your project root.
2. Copy the files from this pack into the matching folders.
3. Let the OS replace the existing files.
4. Run backend, then frontend UI.

Known note
- frontend build was not fully run inside this export because vite is not installed in the uploaded snapshot. backend python compile and direct endpoint smoke checks passed.
