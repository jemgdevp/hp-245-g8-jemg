# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este repo

Build de un **EFI de OpenCore (Hackintosh)** para un portátil concreto: **HP 245 G8** con **AMD Ryzen 3 5300U** (Lucienne/Renoir, Zen 2 APU, iGPU Vega 6 `1002:164c`). No es un proyecto de software: el "producto" es la carpeta `macos/EFI/` que se sincroniza a un USB instalador de macOS. El objetivo actual (ver `README.md`) es **pasar el instalador de macOS Ventura/Sonoma con aceleración gráfica vía NootedRed** en este hardware específico; aún no instalar.

Casi todo el trabajo vive en `macos/`. La raíz contiene solo scaffolding de Ruflo/Claude Code (`.claude/`, `node_modules/`, `*.db`) e imágenes de diagnóstico de pruebas de arranque (`Pasted image*.png`, `IMG_*`) — estas son artefactos de sesión, no fuente.

## Flujo de trabajo (editar → generar → validar → sincronizar)

Todo se ejecuta desde `macos/`. El ciclo de iteración (bisección rápida del bug de framebuffer) es:

```bash
cd macos
# 1. Editar los toggles de prueba en el generador (ver "Toggles" abajo)
#    Para cambios de fondo (kexts, quirks, boot-args) se edita el cuerpo del script.
python3 scripts/05_generate_config.py        # regenera EFI/OC/config.plist (+ backup automático)
./tools/ocvalidate ./EFI/OC/config.plist     # SIEMPRE validar antes de sincronizar
./scripts/06_sync_usb_efi.sh                  # sincroniza EFI/ al USB (label MACOS)
```

- `SYNC_FAST=1 ./scripts/06_sync_usb_efi.sh` — excluye `OC/Resources/Audio/` (~360 mp3) para iterar rápido. Por defecto el sync es **completo** (OpenCore puede quejarse de archivos faltantes aunque `AudioSupport=false`).
- `06_sync_usb_efi.sh` está diseñado para correr **sin sudo** (usa `udisksctl`); rechaza ejecutarse como root. Override: `FORCE_SUDO=1`. El USB debe tener label `MACOS` (override con `USB_LABEL=` / `MOUNT_POINT=`).
- Usar siempre un puerto **USB 2.0 (negro)** para el pendrive durante las pruebas.

Scripts de bootstrap (de un solo uso, normalmente ya ejecutados — generan `*.log` junto a ellos):
- `01_install_ocat.sh` — instala OCAT + dependencias (Arch Linux).
- `02_download_recovery.sh` — descarga el recovery de macOS (Ventura por defecto; ver nota de board-id dentro).
- `03_download_kexts.sh` — descarga los kexts a `macos/kexts/`.
- `04_generate_config.sh` — guía interactiva legacy para OCAT. **Obsoleto**: el generador real es `05_generate_config.py`. Ojo: los headers de los scripts `0X_*` mencionan `MacBookPro16,3`, pero el SMBIOS vigente es `iMac20,1` (lo define `05_generate_config.py`, que es la fuente de verdad).

## Arquitectura del generador (`scripts/05_generate_config.py`)

Es la **única fuente de verdad** del `config.plist`. Cómo funciona y por qué importa:

- **Parte de `EFI/OC/config.plist` como plantilla** (lo lee, lo muta sección por sección con `plistlib`, y lo reescribe). No genera desde cero: respeta lo que ya hay y solo sobreescribe las claves que controla. Hace un backup `config_backup_<hash>.plist` en cada ejecución (de ahí los muchos backups en `EFI/OC/`).
- **Clona/actualiza `AMD_Vanilla`** en `tools/AMD_Vanilla` y carga sus kernel patches. **Inyecta `PHYSICAL_CORES = 4`** en los patches `cpuid_cores_per_package to constant` (el placeholder `0x00` de AMD_Vanilla cuelga el arranque SMP/PCI — este es un fix crítico, no cosmético).
- **`KEXTS`** es una lista de tuplas `(nombre, arch, minkernel, maxkernel, noexec)`. El 5º campo `noexec=True` marca kexts *codeless* (sin binario, p.ej. `AppleMCEReporterDisabler`, `UTBDefault`). Power management AMD real (`SMCAMDProcessor` + `AMDRyzenCPUPowerManagement`) en vez de `DummyPowerManagement`. TSC sync vía `ForgedInvariant` (no `AmdTscSync`).
- Cada constante y bloque lleva **comentarios densos que justifican la decisión** contra el hardware/log de arranque. No cambies valores sin leer el comentario adyacente — codifican fallos reales ya diagnosticados. Lista de gotchas confirmados:
  - `Cpuid1Data`/`Cpuid1Mask` **vacíos** — spoofear CPUID de Intel sobre los patches AMD causa panic tempranísimo (negro sin verbose).
  - Booter Quirks en esquema **moderno** (`RebuildAppleMemoryMap=True`, `SetupVirtualMap=True`, `SyncRuntimePermissions=True`, `EnableWriteUnprotector=False`, `DevirtualiseMmio=False`, `ProtectUefiServices=False`) — alineado con Otus9051 (mismo CPU). Es el que ARRANCA Ventura. El cuelgue tras ExitBootServices con el moderno fue un problema de sesiones tempranas, ANTES de alinear SMBIOS/power-kexts/ACPI; ya resuelto. NO revertir a legacy.
  - `npci=0x3000` en boot-args — el BIOS HP no expone Above 4G Decoding.
  - SMBIOS `iMac20,1` (board-id `Mac-CFF7D910A743CAAF`) — recomendado por ChefKiss para NootedRed en Renoir/Lucienne.

### Toggles de prueba (para bisección)

Variables booleanas pensadas para activar/desactivar pruebas sin reescribir el script:
- `USE_NRED_DP_DELAY` (módulo, ~línea 90) → añade `-NRedDPDelay` a boot-args (retrasa link-training del panel eDP interno).
- `USE_MINIMAL_ACPI_FOR_FB_TEST` (dentro de `build_config`, ~línea 221) → conmuta entre el set ACPI completo (10 SSDTs) y un set mínimo estilo Otus9051.

## ACPI / SSDTs

- Los `.aml` que carga el config viven en `EFI/OC/ACPI/`. Las fuentes editables (`.dsl`) están en `macos/acpi_src/` (p.ej. `SSDT-PLUG.dsl`, `SSDT-USB-Reset.dsl`) — si editas un `.dsl` hay que recompilarlo a `.aml` (con `iasl`) antes de regenerar.
- La DSDT real del equipo está volcada en `macos/docs/DSDT.dsl` / `.aml`; los paths de los SSDTs se validan contra ella (CPUs declaradas como `\_SB.P000`, no `PR00`).
- Hay un parche ACPI `GPRW → XPRW` (Find/Replace de 5 bytes) que neutraliza el instant-wake que cuelga el bus PCI en este chasis.

## Material de referencia (`macos/docs/`)

Carpetas clave para entender decisiones y diagnosticar:
- **`docs/DIAGNOSTICO.md`** — bitácora completa de bisección (qué se probó, qué colgó y por qué). Léela antes de tocar quirks/boot-args.
- `docs/hp-245-g8-efi-base/` — EFI de referencia del **mismo modelo** que arranca; fuente de los SSDTs reales.
- `docs/otus9051-hp15s/` — EFI de referencia del **mismo CPU exacto** (5300U) que arranca con HDMI externo.
- `docs/Hardware-Sniffer/`, `docs/OpCore-Simplify/` — repos vendados (con su propio `.git`); herramientas, no fuente de este proyecto. `docs/Report.json` es el dump de Hardware-Sniffer.

## Convenciones del repo

- Commits: rama `main`, en español, sin trailer `Co-Authored-By` (ver regla en la sección Ruflo). No hacer `push` salvo que se pida.
- No commitear secretos. Los seriales/MLB del SMBIOS en `05_generate_config.py` son para este equipo personal (no son secretos de terceros), pero el `SystemUUID` y `ROM` se regeneran aleatoriamente en cada ejecución.
- `docs/Hardware-Sniffer` y `docs/OpCore-Simplify` tienen su propio `.git` — no los modifiques como si fueran parte de este repo.

---

# Ruflo — Claude Code Configuration

> Lo siguiente es configuración de Ruflo/Claude Code versionada a propósito (agentes y helpers custom). El uso de swarm/MCP es **opcional**: este proyecto es de iteración manual sobre scripts, no de desarrollo multi-archivo de software.

## Rules

- Do what has been asked; nothing more, nothing less
- NEVER create files unless absolutely necessary — prefer editing existing files
- NEVER create documentation files unless explicitly requested
- NEVER save working files or tests to root — use `/src`, `/tests`, `/docs`, `/config`, `/scripts`
- ALWAYS read a file before editing it
- NEVER commit secrets, credentials, or .env files
- NEVER add a `Co-Authored-By` trailer to user commits unless this project's `.claude/settings.json` has `attribution.commit` set (#2078). The Claude Code Bash tool may suggest one in its default commit-message template — ignore it. `Co-Authored-By` is semantic authorship attribution under git/GitHub convention; the tool is the facilitator, not a co-author.
- Keep files under 500 lines
- Validate input at system boundaries

## Agent Comms (SendMessage-First Coordination)

Named agents coordinate via `SendMessage`, not polling or shared state.

```
Lead (you) ←→ architect ←→ developer ←→ tester ←→ reviewer
              (named agents message each other directly)
```

### Spawning a Coordinated Team

```javascript
// ALL agents in ONE message, each knows WHO to message next
Agent({ prompt: "Research the codebase. SendMessage findings to 'architect'.",
  subagent_type: "researcher", name: "researcher", run_in_background: true })
Agent({ prompt: "Wait for 'researcher'. Design solution. SendMessage to 'coder'.",
  subagent_type: "system-architect", name: "architect", run_in_background: true })
Agent({ prompt: "Wait for 'architect'. Implement it. SendMessage to 'tester'.",
  subagent_type: "coder", name: "coder", run_in_background: true })
Agent({ prompt: "Wait for 'coder'. Write tests. SendMessage results to 'reviewer'.",
  subagent_type: "tester", name: "tester", run_in_background: true })
Agent({ prompt: "Wait for 'tester'. Review code quality and security.",
  subagent_type: "reviewer", name: "reviewer", run_in_background: true })

// Kick off the pipeline
SendMessage({ to: "researcher", summary: "Start", message: "[task context]" })
```

### Patterns

| Pattern | Flow | Use When |
|---------|------|----------|
| **Pipeline** | A → B → C → D | Sequential dependencies (feature dev) |
| **Fan-out** | Lead → A, B, C → Lead | Independent parallel work (research) |
| **Supervisor** | Lead ↔ workers | Ongoing coordination (complex refactor) |

### Rules

- ALWAYS name agents — `name: "role"` makes them addressable
- ALWAYS include comms instructions in prompts — who to message, what to send
- Spawn ALL agents in ONE message with `run_in_background: true`
- After spawning: STOP, tell user what's running, wait for results
- NEVER poll status — agents message back or complete automatically

## Swarm & Routing

### Config
- **Topology**: hierarchical-mesh (anti-drift)
- **Max Agents**: 15
- **Memory**: hybrid
- **HNSW**: Enabled
- **Neural**: Enabled

```bash
npx @claude-flow/cli@latest swarm init --topology hierarchical --max-agents 8 --strategy specialized
```

### Agent Routing

| Task | Agents | Topology |
|------|--------|----------|
| Bug Fix | researcher, coder, tester | hierarchical |
| Feature | architect, coder, tester, reviewer | hierarchical |
| Refactor | architect, coder, reviewer | hierarchical |
| Performance | perf-engineer, coder | hierarchical |
| Security | security-architect, auditor | hierarchical |

### When to Swarm
- **YES**: 3+ files, new features, cross-module refactoring, API changes, security, performance
- **NO**: single file edits, 1-2 line fixes, docs updates, config changes, questions

### 3-Tier Model Routing

| Tier | Handler | Use Cases |
|------|---------|-----------|
| 1 | Agent Booster (WASM) | Simple transforms — skip LLM, use Edit directly |
| 2 | Haiku | Simple tasks, low complexity |
| 3 | Sonnet/Opus | Architecture, security, complex reasoning |

## Memory & Learning

### Before Any Task
```bash
npx @claude-flow/cli@latest memory search --query "[task keywords]" --namespace patterns
npx @claude-flow/cli@latest hooks route --task "[task description]"
```

### After Success
```bash
npx @claude-flow/cli@latest memory store --namespace patterns --key "[name]" --value "[what worked]"
npx @claude-flow/cli@latest hooks post-task --task-id "[id]" --success true --store-results true
```

### MCP Tools (use `ToolSearch("keyword")` to discover)

| Category | Key Tools |
|----------|-----------|
| **Memory** | `memory_store`, `memory_search`, `memory_search_unified` |
| **Bridge** | `memory_import_claude`, `memory_bridge_status` |
| **Swarm** | `swarm_init`, `swarm_status`, `swarm_health` |
| **Agents** | `agent_spawn`, `agent_list`, `agent_status` |
| **Hooks** | `hooks_route`, `hooks_post-task`, `hooks_worker-dispatch` |
| **Security** | `aidefence_scan`, `aidefence_is_safe`, `aidefence_has_pii` |
| **Hive-Mind** | `hive-mind_init`, `hive-mind_consensus`, `hive-mind_spawn` |

### Background Workers

| Worker | When |
|--------|------|
| `audit` | After security changes |
| `optimize` | After performance work |
| `testgaps` | After adding features |
| `map` | Every 5+ file changes |
| `document` | After API changes |

```bash
npx @claude-flow/cli@latest hooks worker dispatch --trigger audit
```

## Agents

**Core**: `coder`, `reviewer`, `tester`, `planner`, `researcher`
**Architecture**: `system-architect`, `backend-dev`, `mobile-dev`
**Security**: `security-architect`, `security-auditor`
**Performance**: `performance-engineer`, `perf-analyzer`
**Coordination**: `hierarchical-coordinator`, `mesh-coordinator`, `adaptive-coordinator`
**GitHub**: `pr-manager`, `code-review-swarm`, `issue-tracker`, `release-manager`

Any string works as a custom agent type.

## Build & Test

- ALWAYS run tests after code changes
- ALWAYS verify build succeeds before committing

```bash
npm run build && npm test
```

## CLI Quick Reference

```bash
npx @claude-flow/cli@latest init --wizard           # Setup
npx @claude-flow/cli@latest swarm init --v3-mode     # Start swarm
npx @claude-flow/cli@latest memory search --query "" # Vector search
npx @claude-flow/cli@latest hooks route --task ""    # Route to agent
npx @claude-flow/cli@latest doctor --fix             # Diagnostics
npx @claude-flow/cli@latest security scan            # Security scan
npx @claude-flow/cli@latest performance benchmark    # Benchmarks
```

26 commands, 140+ subcommands. Use `--help` on any command for details.

## Setup

```bash
claude mcp add claude-flow -- npx -y @claude-flow/cli@latest
npx @claude-flow/cli@latest daemon start
npx @claude-flow/cli@latest doctor --fix
```

**Agent tool** handles execution (agents, files, code, git). **MCP tools** handle coordination (swarm, memory, hooks). **CLI** is the same via Bash.
