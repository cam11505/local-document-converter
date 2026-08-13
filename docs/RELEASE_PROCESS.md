# Release Process

The project uses two Windows Python 3.12 validation layers:

1. `CI` runs on every pull request and push to `main`. It covers Ruff, formatting, strict
   Mypy, unit/mocked tests, the core CLI, and wheel construction without optional heavy
   runtimes.
2. `Release candidate smoke` is triggered manually before a release. It installs the
   Docling profile, runs the real PDF integration and CLI conversion, builds the wheel,
   and uploads the wheel and generated Markdown as workflow artifacts.

## Release gate

Do not create a version tag or GitHub Release until all of the following are true:

- The project owner has selected a distribution license and the repository root contains
  the matching `LICENSE` file.
- `pyproject.toml` contains the SPDX license expression and `license-files` metadata.
- A human reviewer has accepted or resolved every dependency/model licensing item recorded
  in `DEPENDENCY_AUDIT.md` and `THIRD_PARTY_LICENSE_NOTES.md`.
- The latest `CI` and `Release candidate smoke` workflow runs are successful on the exact
  commit to be tagged.
- The working tree is clean, the local and remote commit SHAs match, and `CHANGELOG.md`
  contains the intended release notes.

After those gates pass, create the annotated `v0.1.0` tag from `main`, push it, and publish
the GitHub Release using the validated wheel artifact and changelog entry.
