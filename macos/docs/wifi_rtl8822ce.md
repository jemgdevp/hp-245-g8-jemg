# WiFi: RTL8822CE (10ec:c822) — Estado en macOS

## Diagnóstico

```
$ lspci -nnk | grep -i net
01:00.0 Network controller [0280]: Realtek Semiconductor Co., Ltd.
          RTL8822CE 802.11ac PCIe Wireless Network Adapter [10ec:c822]
```

## Verdicto

**El chip RTL8822CE NO tiene soporte nativo ni kext funcional para macOS.**

A diferencia de los chips Intel (que sí funcionan con `AirportItlwm.kext`), 
los chips Realtek PCIe modernos no tienen drivers comunitarios estables en 2025/2026.

## Opciones disponibles

### Opción 1: Dongle USB WiFi (recomendado)
- **TL-WN725N** (Realtek RTL8188EUS) — ~$10 USD, driver disponible
- **Archer T2U Nano** (Mediatek MT7610U) — ~$15 USD
- Instalar con `RTL8192CU` o `MT7610` kexts comunitarios

### Opción 2: Reemplazar tarjeta interna
Si tu laptop tiene slot M.2 (NGFF/CNVi):
- **BCM94360NG** — Broadcom nativo (AirDrop, Handoff funcionan)
- **Intel AX210** — Compatible con `AirportItlwm.kext`

### Opción 3: Tethering USB
- Conectar celular Android/iOS por USB y usar tethering
- macOS lo reconoce como interfaz de red automáticamente

## Acción requerida
Necesito saber qué opción prefieres para recomendarte el kext o dongle exacto.
Mientras tanto, la EFI se generará **sin kext de WiFi** — puedes agregarlo después.
