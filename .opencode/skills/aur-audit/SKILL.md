---
name: aur-audit
description: Auditoría de seguridad obligatoria antes de sugerir instalar cualquier paquete AUR. Usar siempre que el agente esté a punto de sugerir, recomendar o instalar un paquete AUR — incluso si el usuario lo pidió explícitamente por nombre. También aplicar cuando el usuario pregunte "¿cómo instalo X en Arch?", "¿es seguro X de AUR?", o cualquier pregunta sobre paquetes que no estén en los repos oficiales. No omitir nunca este paso, sin importar el contexto.
---

# AUR Package Audit Skill

## Paso obligatorio antes de cualquier sugerencia AUR

**SIEMPRE** ejecutar `show_pkgbuild <nombre-paquete>` antes de sugerir instalar desde AUR. Sin excepción.

La herramienta `show_pkgbuild` está registrada en `core/tools/` — usarla directamente.

## Qué revisar en el PKGBUILD

### Maintainer y actividad
- ¿Tiene maintainer activo? ¿Fecha de última actualización reciente?
- Orphaned packages (sin maintainer) = riesgo alto

### Votos de la comunidad
- Pocos votos = baja confianza de la comunidad
- No hay un número mínimo fijo, pero menos de ~20 votos en un paquete no-nicho es señal de alerta

### URLs de source
- ¿Apuntan a repos oficiales (GitHub, GitLab, sitio oficial del proyecto)?
- ¿Dominios desconocidos o acortadores de URL? → rechazar
- ¿Descarga binarios precompilados en lugar de compilar desde fuente? → revisar con cuidado extra

### Patrones sospechosos en el PKGBUILD
```
# Señales de alerta:
curl <url> | bash         # ejecución remota directa
eval $(...)               # evaluación de código remoto
wget <url> -O - | sh      # mismo patrón que curl | bash
install -m 4755           # setuid bit — casi nunca legítimo
```

## Regla de decisión

| Situación | Acción |
|-----------|--------|
| Paquete disponible en repos oficiales (`pacman -Ss`) | Usar el oficial, no AUR |
| PKGBUILD limpio, maintainer activo, buena reputación | Sugerir con nota de que el usuario debe revisar |
| Cualquier señal de alerta | No sugerir — explicar el problema al usuario |
| Orphaned o sin votos | Advertir explícitamente antes de sugerir |

## Output esperado

Antes de sugerir la instalación, informar al usuario:
- Resultado de la revisión del PKGBUILD
- Si hay alguna señal de alerta, explicarla
- Si hay alternativa en repos oficiales, mencionarla primero
