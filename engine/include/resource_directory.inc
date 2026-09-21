; CRYSTAL mapper-independent resource directory contract
; Resource IDs are canonical u16 identities. Physical placement is backend data.
;
; ResourceId -> directory entry -> mapper-specific bank/address.

DEF CRYSTAL_RESOURCE_ENTRY_BANK_OFFSET    EQU 0
DEF CRYSTAL_RESOURCE_ENTRY_ADDRESS_OFFSET EQU 2
DEF CRYSTAL_RESOURCE_ENTRY_LENGTH_OFFSET  EQU 4
DEF CRYSTAL_RESOURCE_ENTRY_FLAGS_OFFSET   EQU 6
DEF CRYSTAL_RESOURCE_ENTRY_SIZE           EQU 8

DEF CRYSTAL_RESOURCE_FLAG_NONE            EQU 0

; Emit one mapper-independent directory entry.
; bank/address are intentionally 16-bit even when the first MBC3 backend
; uses a smaller physical namespace.
MACRO crystal_resource_entry
    dw \\1 ; mapper/backend bank selector
    dw \\2 ; CPU/backend address
    dw \\3 ; byte length
    dw \\4 ; flags
ENDM
