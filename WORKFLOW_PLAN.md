# Workflow Improvements Plan

Branch: `improve-workflow`
Base: `main`

## Fase 1 — ruff + basedpyright (linting + type checking) ✅

**Objetivo**: Agregar linting y type checking automatizados.

Pasos:
1. ✅ Instalar `ruff` y `basedpyright` en el venv
2. ✅ Crear `pyproject.toml` con configuración de ambos
3. ✅ Ejecutar `ruff check . --fix` y `ruff format .`
4. ✅ Ejecutar `basedpyright .` y corregir type errors (0 errors)
5. ✅ Actualizar `AGENTS.md` con comandos de verificación

## Fase 2 — pytest (tests automatizados) ✅

**Objetivo**: Agregar tests unitarios para módulos clave.

Pasos:
1. ✅ Instalar `pytest` y `pytest-asyncio` en el venv
2. ✅ Crear `tests/` con `__init__.py`, `conftest.py` y test files
3. ✅ Tests para: config, conversation, storage, helpers, logger, providers/base, tools/base, markdown (83 tests)
4. ✅ Actualizar `AGENTS.md` con comandos de test

## Fase 3 — pre-commit hooks ✅

**Objetivo**: Agregar linting + type checking + tests automatizados antes de cada commit.

Pasos:
1. ✅ Instalar `pre-commit` en el venv
2. ✅ Crear `.pre-commit-config.yaml` con hooks (ruff lint, ruff format, basedpyright, pytest, trailing-whitespace, end-of-file-fixer, check-yaml, check-json, check-added-large-files, no-commit-to-branch)
3. ✅ Ejecutar `pre-commit install`
4. ✅ Verificar con `pre-commit run --all-files`
5. ✅ Actualizar `AGENTS.md`
