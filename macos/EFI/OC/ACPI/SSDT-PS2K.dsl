/*
 * Intel ACPI Component Architecture
 * AML/ASL+ Disassembler version 20251212 (64-bit version)
 * Copyright (c) 2000 - 2025 Intel Corporation
 * 
 * Disassembling to symbolic ASL+ operators
 *
 * Disassembly of /home/jemg/Dev/hp-245-g8-jemg/macos/EFI/OC/ACPI/SSDT-PS2K.aml
 *
 * Original Table Header:
 *     Signature        "SSDT"
 *     Length           0x00000077 (119)
 *     Revision         0x02
 *     Checksum         0xC4
 *     OEM ID           "OCLT"
 *     OEM Table ID     "PS2KFix"
 *     OEM Revision     0x00003000 (12288)
 *     Compiler ID      "INTL"
 *     Compiler Version 0x20251212 (539300370)
 */
DefinitionBlock ("", "SSDT", 2, "OCLT", "PS2KFix", 0x00003000)
{
    External (_SB_.PCI0.SBRG.PS2K, DeviceObj)

    Scope (\_SB.PCI0.SBRG.PS2K)
    {
        Method (_HID, 0, NotSerialized)  // _HID: Hardware ID
        {
            If (_OSI ("Darwin"))
            {
                Return ("PNP0303")
            }

            Return (0x01801122)
        }
    }
}

