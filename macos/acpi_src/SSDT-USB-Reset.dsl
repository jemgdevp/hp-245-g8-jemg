// SSDT-USB-Reset para HP 245 G8 (Ryzen 3 5300U).
// Resource: https://github.com/dortania/OpenCore-Post-Install/blob/master/extra-files/SSDT-USB-Reset.dsl
//
// Desactiva SOLO los RHUB (root hub) de los XHCI bajo Darwin para que macOS
// reconstruya y re-enumere el árbol USB desde cero. NO desactiva el controlador
// (eso mataría el pendrive del instalador). Fix estándar para cuelgues durante
// la enumeración USB. Paths validados contra la DSDT real:
//   \_SB.PCI0.GP17.XHC0.RHUB  y  \_SB.PCI0.GP17.XHC1.RHUB
DefinitionBlock ("", "SSDT", 2, "OCLT", "UsbReset", 0x00001000)
{
    External (\_SB.PCI0.GP17.XHC0.RHUB, DeviceObj)
    Scope (\_SB.PCI0.GP17.XHC0.RHUB)
    {
        Method (_STA, 0, NotSerialized)  // _STA: Status
        {
            If (_OSI ("Darwin"))
            {
                Return (Zero)
            }
            Else
            {
                Return (0x0F)
            }
        }
    }

    External (\_SB.PCI0.GP17.XHC1.RHUB, DeviceObj)
    Scope (\_SB.PCI0.GP17.XHC1.RHUB)
    {
        Method (_STA, 0, NotSerialized)  // _STA: Status
        {
            If (_OSI ("Darwin"))
            {
                Return (Zero)
            }
            Else
            {
                Return (0x0F)
            }
        }
    }
}
