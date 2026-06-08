# Features Plan

> Las features aquí están estructuradas con descripción, rationale, alcance y estado.
> Solo se promocionan a este archivo cuando están bien definidas.
> Ideas sueltas van a `IDEAS.md` primero.

## Template

```markdown
## [feature-name]
- **Descripción**: ...
- **Rationale**: ...
- **Alcance**: ...
- **Estado**: pending | in_progress | completed
```

---

## software-assistant
- **Descripción**: Buscador e instalador de software Linux por lenguaje natural. Traduce nombres de apps Windows/macOS a alternativas Linux, busca paquetes en repos oficiales y AUR, y guía al usuario en la instalación.
- **Rationale**: Eliminar la fricción de "¿cómo se llama este programa en Linux?" para usuarios nuevos.
- **Alcance**: Búsqueda dinámica vía web, alternativas multiplataforma, integración con PackageTools (pacman/yay/AUR audit).
- **Estado**: completed

## smart-sudo
- **Descripción**: Protocolo de seguridad para comandos sudo: detecta `sudo` en comandos, evalúa si el usuario confirmó explícitamente, y fuerza confirmación visual si no.
- **Rationale**: Prevenir ejecución accidental de comandos privilegiados sin ser molestos cuando el usuario ya pidió explícitamente.
- **Alcance**: Integración en `CommandTool.execute_command`, diálogo `_ConfirmDialog`, flag `user_confirmed`.
- **Estado**: completed

## global-hotkey-call
- **Descripción**: Activar el modo llamada (Voice Call Mode) mediante `Ctrl+Shift+Space` mientras la app tiene foco. Al presionarlo, crea una nueva conversación y dispara el modo llamada automáticamente.
- **Rationale**: Permitir iniciar una llamada por voz al instante sin tener que hacer clic en el botón manualmente.
- **Alcance**: `QShortcut("Ctrl+Shift+Space")` conectado a `_on_call_hotkey` en main_window, `_new_conversation()` + `QTimer.singleShot` para sincronizar inicialización.
- **Estado**: completed
