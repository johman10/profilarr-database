# Unofficial TRaSH-Guides Database for Profilarr

This repository hosts [TRaSH-Guides's](https://trash-guides.info/) unofficial database for Profilarr in **PCD (Profilarr Config Database) 2.x format** containing:

- Quality Profiles
- Custom Formats
- Regex Patterns
- Media Management

The goal of this repository is to generate a Profilarr 2.x compatible database based on TRaSH-Guides configuration without any changes. If you want anything custom you can commit it yourself within the Profilarr UI.

The repo will be automatically kept in sync with the TRaSH-Guides repository. A GitHub Action will run every day pulling the latest version of TRaSH-Guides and running the scripts to generate and push any changes.

## Output Format

This repository generates Profilarr 2.x format output:
- **pcd.json** - Database metadata with version and dependencies
- **ops/1.initial.sql** - Complete SQL schema initialization with all data
- **media_management/** - YAML files for naming formats and quality definitions
- **deps/** - Dependencies directory (for future use)
- **tweaks/** - Tweaks directory (for future use)

## Scripts

The repository contains a script to generate the Profilarr database in PCD format based on TRaSH-Guides data.

### Requirements

- **Python 3.13+**
- **UV** for package management - install via [official instructions](https://github.com/astral-sh/uv?tab=readme-ov-file#installation)
- **TRaSH-Guides data** - a local clone with JSON data in `docs/json/` (not automatically cloned)

Dependencies are defined in `pyproject.toml` and managed by UV.

### Running the script

Assuming you're in the root directory of the repository you can now run:

```bash
uv run scripts/generate.py /path/to/trash-guides/docs/json .
```

This will generate:
- `pcd.json` with version metadata
- `ops/1.initial.sql` containing all database initialization SQL
- `media_management/` directory with YAML configuration files

## Testing

This project includes automated tests to validate the integrity of generated output files.

### Running Tests

The test suite validates:
- PCD format compliance (`pcd.json` structure and version management)
- SQL syntax validity in generated `ops/1.initial.sql`
- Presence of all required SQL sections (tags, regex patterns, custom formats, profiles)
- Completeness of INSERT statements and proper data structure

```bash
# Install dev dependencies
uv sync --extra dev

# Run all tests
uv run pytest tests/ -v

# Run specific test files
uv run pytest tests/test_pcd_format.py -v
uv run pytest tests/test_custom_formats.py -v
uv run pytest tests/test_profiles.py -v

# Run with coverage report
uv run pytest tests/ --cov=scripts --cov-report=term
```

### Test Suites

- **test_pcd_format.py** - Validates PCD structure, pcd.json integrity, and SQL format
- **test_custom_formats.py** - Validates custom format and regex pattern SQL generation
- **test_profiles.py** - Validates quality profile and profile-to-format mapping SQL generation

If a test fails, it will clearly indicate what validation failed, making it easy to identify and fix issues.

## Code Quality

This project uses **pylint** for static code analysis and quality checks.

```bash
# Install dev tools
uv sync --extra dev

# Run linting
uv run pylint scripts tests
```
