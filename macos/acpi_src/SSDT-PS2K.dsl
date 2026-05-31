/*
 * SSDT-PS2K: Fix _HID del teclado PS/2 para VoodooPS2Controller.
 *
 * El DSDT declara PS2K con _HID = HPQ8001 (propietario HP) y _CID = PNP0303.
 * VoodooPS2Keyboard enlaza por IONameMatch con PNP0303; macOS puede ignorar _CID
 * cuando _HID es propietario. Este SSDT añade un Method _HID que devuelve PNP0303
 * bajo Darwin, forzando el enlace correcto.
 *
 * Path validado contra docs/DSDT.dsl: \_SB.PCI0.SBRG.PS2K (línea 15217)
 * Recursos: IO 0x60/0x64, IRQ 1 — puerto i8042 físico real.
 */
DefinitionBlock ("", "SSDT", 2, "OCLT", "PS2KFix", 0x00003000)
{
    External (_SB_.PCI0.SBRG.PS2K, DeviceObj)

    Scope (\_SB.PCI0.SBRG.PS2K)
    {
        Method (_HID, 0, NotSerialized)
        {
            If (_OSI ("Darwin"))
            {
                Return ("PNP0303")
            }

            Return (EisaId ("HPQ8001"))
        }
    }
}
