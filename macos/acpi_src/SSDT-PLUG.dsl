// SSDT-PLUG para HP 245 G8 (Ryzen 3 5300U). Inyecta plugin-type=1 en el primer
// procesador. La DSDT real declara las CPU como Device(_HID "ACPI0007") con
// nombre \_SB.P000 (NO PR00 como el EFI de referencia del 5500U), por eso se
// usa DeviceObj y el path P000 verificado en la DSDT extraída.
DefinitionBlock ("", "SSDT", 2, "OCLT", "CpuPlug", 0x00003000)
{
    External (_SB_.P000, DeviceObj)

    Scope (\_SB.P000)
    {
        Method (_DSM, 4, NotSerialized)
        {
            If ((Arg2 == Zero))
            {
                Return (Buffer (One)
                {
                     0x03
                })
            }

            Return (Package (0x02)
            {
                "plugin-type",
                One
            })
        }
    }
}
