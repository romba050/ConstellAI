# MED-R5 archived software snapshot

This branch contains the active MED-R5 software from the supplied `medr-done` folder, uploaded on 2026-10-03. Frontend, backend, engines, registries, research memory, reports, assets, launch scripts, and dependency manifests are preserved.

The branch name is `old-sw` because Git branch names cannot contain spaces. The commit is based on the repository's existing `main` history.

Installed Node/Python dependencies, Python bytecode, frontend build output, duplicate backup/export folders, the generated export manifest, evidence-cache database, PubMed cache JSON, and recent evidence query history are omitted. They remain in the original desktop folder. Local credential files and generated caches are ignored by `.gitignore`.

See `README.md` for setup instructions. The original desktop software folder was not modified.
