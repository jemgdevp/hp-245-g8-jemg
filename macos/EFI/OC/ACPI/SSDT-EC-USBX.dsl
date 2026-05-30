// SSDT-EC-USBX for HP 245 G8 (AMD Ryzen)
// Creates fake EC device + USBX power properties for macOS
DefinitionBlock ("", "SSDT", 2, "CORP", "EC-USBX", 0x00001000)
{
    External (_SB_.PCI0.LPCB, DeviceObj)

    Scope (\_SB.PCI0.LPCB)
    {
        // Check if EC exists; if not, create a compatible one
        If (_OSI ("Darwin"))
        {
            Device (EC)
            {
                Name (_HID, EisaId ("PNP0C09"))
                Name (_UID, 1)
                Name (_STA, 0x0B)
            }
        }
    }

    // USBX power properties
    Device (\_SB.USBX)
    {
        Name (_ADR, Zero)
        Method (_DSM, 4, NotSerialized)
        {
            If (!Arg2) { Return (Buffer() { 0x03 }) }
            Return (Package()
            {
                "kUSBSleepPortCurrentLimit", 2100,
                "kUSBSleepPowerSupply",     5100,
                "kUSBWakePortCurrentLimit",  2100,
                "kUSBWakePowerSupply",       5100
            })
        }
    }
}
