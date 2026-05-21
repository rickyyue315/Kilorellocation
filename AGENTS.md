# Project Instructions

## GitHub Push Convention
When the user says "upload to github", "push to github", or any equivalent phrase, always push to the remote `origin` pointing at:
- **URL**: `https://github.com/rickyyue315/Kilorellocation.git`

If the `origin` remote does not exist or points elsewhere, set it with:
```
git remote add origin https://github.com/rickyyue315/Kilorellocation.git
```
or update it with:
```
git remote set-url origin https://github.com/rickyyue315/Kilorellocation.git
```

## Documentation Sync on Mode Changes
Whenever a transfer mode is added, removed, or its logic is modified (in `business_logic.py`, `strategies/`, `models/mode.py`, or `ui/sidebar.py`), you MUST synchronise ALL of the following files before committing:

1. **`README.md`** — Update the mode list, mode comparison table, feature highlights, and interface flow if affected.
2. **`VERSION.md`** — Add a new version entry describing the change.
3. **`config.py`** — Bump `VERSION` to the new version number.
4. **`app.py`** — Update the module docstring version if `config.VERSION` changed.
5. **`ui/tutorial.py`** — Add/update the tutorial content for the affected mode(s). Each mode entry must include: scenario description, risk badge, source flow chart, destination flow chart, match order, scenario table, diff table, and extra notes. If a new mode group is needed, add a `_render_*_group()` function and register it in `render_tutorial_page()`.
6. **`調貨模式詳解.txt`** — Update the detailed mode description.
7. **`transfer_logic_ai_brief.md`** — Update the AI brief if matching priority or constraints changed.

Do NOT skip any of these files. If unsure which files are affected, check the full list above.
