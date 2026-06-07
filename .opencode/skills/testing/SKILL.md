---
name: testing
description: Comandos y workflow completo para verificar calidad de código en este proyecto. Usar siempre que haya que correr tests, ejecutar lint, verificar tipos con basedpyright, debuggear un test fallido, o preparar un commit. Aplicar cuando el usuario diga "corre los tests", "chequea el código", "pre-commit", "¿pasan los tests?", o antes de cada commit según el workflow del proyecto. También usar si hay errores de ruff, basedpyright, o pytest que haya que diagnosticar.
---

# Testing & Quality Skill

## Pipeline rápido (recomendado)

```bash
source venv/bin/activate && pre-commit run --all-files
```

Ejecuta ruff check, ruff format, basedpyright y pytest en un solo comando. Usar esto por defecto.

## Pipeline manual equivalente

Usar cuando pre-commit falle y haya que aislar qué parte falla:

```bash
# Paso 1: lint
source venv/bin/activate && ruff check .

# Paso 2: formato
source venv/bin/activate && ruff format . --check

# Paso 3: tipos
source venv/bin/activate && basedpyright .

# Paso 4: tests
source venv/bin/activate && python -m pytest tests/ -v
```

## Correr un test específico

```bash
source venv/bin/activate && python -m pytest tests/test_<módulo>.py -v -k "<nombre_del_test>"
```

Ejemplo: `python -m pytest tests/test_audio.py -v -k "test_silence_detection"`

## Criterio de éxito (automatizado)

El pipeline pasa cuando **todos** estos dan exit code 0:
- `ruff check .` — sin errores de lint
- `ruff format . --check` — sin diferencias de formato
- `basedpyright .` — sin errores de tipo (warnings OK según config de pyproject.toml)
- `pytest tests/ -v` — todos los tests en `tests/` pasan

## Smoke test manual (después del pipeline automatizado)

Ejecutar solo después de que el pipeline automatizado pase:

1. Lanzar la app: `source venv/bin/activate && python3 main.py`
2. Verificar que abre sin crash ni traceback en consola
3. Enviar un mensaje de texto en el chat
4. Confirmar que no hay errores en la salida de consola

## Política de commits

No hacer commit hasta que **tanto el pipeline automatizado como el smoke test manual pasen**. Un commit por fase del workflow, nunca a mitad de una fase.
