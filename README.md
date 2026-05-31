# GRating Rebalancer

Calibre GUI plugin that reads Goodreads rating data through fixed Calibre
identifiers and writes library-relative percentile outputs to user-selected
custom columns.

The plugin never writes to `grrating` or `grvotes`.
It writes one raw `0.0-100.0` percentile Output column, with an optional
Rating column for distribution-shaped values such as percentile, decimal,
range, or star output.
Series-adjusted percentile calculations always run through a score-to-percentile
map, using a locked map when available and a freshly built map otherwise, and
distribution curves are applied only to the optional Rating field.

## Runtime Shape

- `__init__.py`: lightweight Calibre wrapper metadata.
- `ui.py`: toolbar/menu integration.
- `main.py`: workflow orchestration only.
- `config.py`: preferences and configuration widget.
- `metadata_io.py`: focused Calibre reads/writes.
- `scoring.py`: pure series adjustment logic.
- `percentiles.py`: pure percentile and output conversion logic.
- `locked_mapping.py`: locked mapping persistence helpers.
- `results.py`: small run/result models.

## Check

```powershell
py -3.12 _dev_tools\run_tests.py
py -3.12 -m py_compile __init__.py ui.py main.py config.py about.py common.py metadata_io.py scoring.py percentiles.py locked_mapping.py results.py
```

If `py -3.12` is unavailable, use the workspace virtual environment or another
Python 3 command.

## Package

Release zips should include runtime files only. Exclude `_dev_tools/`, `_docs/`,
caches, compiled Python files, and local planning material.
