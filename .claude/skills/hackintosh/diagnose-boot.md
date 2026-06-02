---
name: diagnose-boot
description: Checklist de diagnóstico para problemas de arranque Hackintosh HP 245 G8
---
Checklist de diagnóstico para el HP 245 G8 con AMD Ryzen 3 5300U.

## Síntomas y causas conocidas
| Síntoma | Causa probable | Fix |
|---------|---------------|-----|
| Pantalla negra sin verbose | Cpuid1Data/Mask no vacíos | Vaciar Cpuid1Data en el generador |
| Cuelgue tras ExitBootServices | Booter Quirks en esquema moderno | Usar esquema legacy (RebuildAppleMemoryMap=False) |
| "OC: failed to load configuration" | BOOTx64.efi es OpenCore.efi en vez de Bootstrap | Copiar Bootstrap.efi a EFI/BOOT/BOOTx64.efi |
| Bucle arrancando OpenCore | Entrada NVRAM autorreferencial | LauncherOption=Disabled + limpiar NVRAM |
| Cuelgue en AppleKeyStore | TSC desincronizado | Usar ForgedInvariant (no AmdTscSync) |
| pci flags 0xc000 (no es cuelgue) | Banner informativo del framebuffer iGPU | El muro real es el framebuffer VRAM < 1GB |
| Muro en framebuffer / HDMI sin señal | iGPU Vega 6 necesita NootedRed (o NootedRed crashea todo) | Probar -radvesa sin NootedRed; si HDMI da señal → solo NootedRed |
| **LED Caps Lock encendido** | **Kernel panic** (el kernel macOS prende Caps Lock al morir) | Leer panic log; sospechoso #1: AMDRyzenCPUPowerManagement |
| Caps Lock on + AMDRyzenCPU instalado | AMDRyzenCPUPowerManagement v0.7.2 + DummyPM=False → panic | DummyPM=True + Enabled=False en AMDRyzenCPU y SMCAMDProcessor |

## Secuencia de diagnóstico
1. Leer log de OpenCore (ver skill read-oc-log)
2. Identificar último prefijo antes del cuelgue
3. Buscar en docs/DIAGNOSTICO.md el síntoma
4. Editar toggles en 05_generate_config.py
5. Ciclo: regen -> validate -> sync -> boot -> log

## Boot args de depuración
- -v: verbose mode (SIEMPRE activado en depuración)
- -NRedDPDelay: retrasa link-training eDP interno (NootedRed)
- npci=0x3000: bypass check PCI (HP BIOS sin Above 4G Decoding)
- debug=0x100: panic log en lugar de reinicio automático
- keepsyms=1: símbolos en kernel panic
