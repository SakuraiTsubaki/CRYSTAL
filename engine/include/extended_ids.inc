; CRYSTAL Generation 10-ready ID contract
; RGBDS-compatible constants/macros.
;
; All cross-subsystem identities are 16-bit master IDs.
; Compact ROM/save encodings must be decoded before gameplay logic.

DEF CRYSTAL_MASTER_ID_BITS EQU 16
DEF CRYSTAL_MASTER_ID_SIZE EQU 2
DEF CRYSTAL_ID_NONE        EQU 0
DEF CRYSTAL_ID_MIN         EQU 1
DEF CRYSTAL_ID_MAX         EQU $ffff

DEF CRYSTAL_SPECIES_ID_SIZE          EQU 2
DEF CRYSTAL_VARIETY_ID_SIZE          EQU 2
DEF CRYSTAL_FORM_ID_SIZE             EQU 2
DEF CRYSTAL_MOVE_ID_SIZE             EQU 2
DEF CRYSTAL_ITEM_ID_SIZE             EQU 2
DEF CRYSTAL_ABILITY_ID_SIZE          EQU 2
DEF CRYSTAL_TYPE_ID_SIZE             EQU 2
DEF CRYSTAL_EVOLUTION_METHOD_ID_SIZE EQU 2
DEF CRYSTAL_RESOURCE_ID_SIZE         EQU 2
DEF CRYSTAL_FEATURE_ID_SIZE          EQU 2

MACRO crystal_id
    dw \\1
ENDM

MACRO crystal_assert_id
    ASSERT (\\1) >= CRYSTAL_ID_NONE
    ASSERT (\\1) <= CRYSTAL_ID_MAX
ENDM
