# Local Agent Notes

This file is local-only guidance for agents working from this Calibre GUI plugin template.

## Local Docs Reference

Check the local `_docs/` files before making broad changes or continuing an older thread:

- `_docs/PROJECT_CONTEXT.md`: template purpose, current project shape, editing habits, and command reminders.
- `_docs/ARCHITECTURE.md`: module responsibilities and packaging notes.
- `_docs/DECISIONS.md`: durable choices about template identity, Calibre boundaries, testing, and documentation style.
- `_docs/TASKS.md`: current todo list and watch points.
- `_docs/CODEX_HANDOFF.md`: preferred commands, test shape, and handoff notes.

When implementing an accepted plan, update the relevant local docs before finishing if the work changes template structure, durable decisions, task status, command expectations, or handoff notes. Keep updates concise and grounded in files that actually changed.

## Calibre Plugin Conventions

Prefer Calibre's plugin APIs, bundled third-party libraries, and conventions over generic Python or Qt patterns when Calibre provides an appropriate tool.

Use Calibre-facing APIs at plugin boundaries, including:

- `InterfaceActionBase` in `__init__.py` for wrapper metadata.
- `InterfaceAction` in `ui.py` for GUI lifecycle and toolbar/menu integration.
- `qt.core` imports instead of direct PyQt or PySide imports.
- `calibre.utils.config.JSONConfig` for plugin preferences.
- Calibre database APIs for reading or writing library metadata.
- Calibre job manager APIs for long-running work.
- `calibre.gui2` dialogs such as `error_dialog` and `question_dialog` for user-facing messages when they fit the workflow.

Plain Python remains appropriate for focused domain code, parser helpers, normalization logic, and other modules that do not need direct Calibre UI integration.

## Template Boundaries

- Keep `__init__.py` import-light so Calibre command-line utilities can inspect plugin metadata without loading Qt.
- Keep GUI action setup and menu wiring in `ui.py`.
- Keep selected-book workflow and future job orchestration in `main.py`.
- Keep preferences and the configuration widget in `config.py`.
- Keep about text in `about.py`, deriving version and author from wrapper metadata.
- Keep `common.py` small until repeated project behavior justifies shared helpers.
- Rename all template identity values together when starting a real plugin: display name, wrapper class, import package, preferences namespace, package marker, icon, author, version, and docs.

## Comment And Documentation Style

Use comments to document constraints that are easy to break during refactors, not to narrate obvious code.

Prefer these headings in module or class docstrings when they genuinely help:

- `Maintenance notes`
- `Type constraints`
- `Invariants`
- `Refactor warning`

Avoid labels such as `AGENT_HINT` or `AGENT_TELEMETRY`. They are noisy in normal source files and do not describe runtime behavior.

## When To Add Documentation

Add module or class documentation when code depends on:

- Calibre API behavior that is not obvious from the call site.
- Plugin import boundaries or deferred imports.
- Cross-module contracts between GUI action, runner, config, and helpers.
- Progress counters where the denominator must match real work.
- Calibre field write behavior or compatibility fallbacks.
- Parser or normalization rules where a simpler-looking change would broaden or narrow matches.
- User data storage, migrations, or cache layout.

Use inline comments for load-bearing details only:

- A line looks inefficient but protects a known edge case.
- A parser workaround handles a specific source shape.
- A fallback order is intentional because earlier options preserve more information or compatibility.
- A Calibre API call requires a less obvious argument or refresh step.

## When Not To Add Documentation

Do not add comments that merely restate the code.

Avoid broad claims like:

- "This simply handles..."
- "This easily manages..."
- "Optimize this later..."

Do not add complexity notes unless the logic is dense, performance-sensitive, or likely to be mistaken during refactoring.

## Packaging Notes

Release zips should contain runtime plugin files only. Exclude:

- `_docs/`
- `_dev_tools/`
- `__pycache__/`
- compiled Python files
- temporary sample files
- old project artifacts

Before packaging a real plugin, replace `images/plugin_icon.png` and remove any sample-only docs or fixtures that are not meant for users.
