#!/usr/bin/env python3
"""Apply CRYSTAL's first Generation 10-ready runtime patch to pinned pokeemerald-expansion.

This intentionally targets only:
- full 16-bit Species / Item / Move identities in BoxPokemon;
- checksum/encryption coverage for the extension word;
- a 10-sector PokemonStorage allocation;
- 15-sector duplicated save slots in 128 KiB flash.

Trainer Hill and Recorded Battle standalone sectors are disabled for the CRYSTAL
runtime profile so the two remaining sectors can retain Hall of Fame storage.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

PINNED = "75b806a3ab57a81ff1eb6179288981f0b3cc3050"

def fail(message: str) -> None:
    raise SystemExit(f"CRYSTAL Gen10 patch failed: {message}")

def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        fail(f"{path}: expected exactly one replacement target, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

def check_head(root: Path) -> None:
    try:
        head = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return
    if head != PINNED:
        fail(f"upstream HEAD {head} != pinned {PINNED}")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream", type=Path)
    args = parser.parse_args()
    root = args.upstream.resolve()
    check_head(root)

    pokemon_h = root / "include/pokemon.h"
    pokemon_c = root / "src/pokemon.c"
    save_h = root / "include/save.h"
    save_c = root / "src/save.c"

    replace_once(
        pokemon_h,
        """    u16 hpLost:14; // 16383 HP.
    u16 shinyModifier:1;
    u16 unused_1E:1;

    union
""",
        """    u16 hpLost:14; // 16383 HP.
    u16 shinyModifier:1;
    u16 unused_1E:1;

    // CRYSTAL: high bits for full 16-bit Species/Item/Move identities.
    // Layout: species[0:4], item[5:10], moves[11:30], bit31 reserved.
    u32 crystalExtendedIds;

    union
""",
    )

    helper_anchor = """struct SpeciesItem
{
    enum Species species;
    enum Item item;
};

"""
    helpers = helper_anchor + """// CRYSTAL Generation 10-ready BoxPokemon identity extension.
#define CRYSTAL_EXT_SPECIES_SHIFT 0
#define CRYSTAL_EXT_ITEM_SHIFT    5
#define CRYSTAL_EXT_MOVE1_SHIFT   11
#define CRYSTAL_EXT_MOVE2_SHIFT   16
#define CRYSTAL_EXT_MOVE3_SHIFT   21
#define CRYSTAL_EXT_MOVE4_SHIFT   26
#define CRYSTAL_EXT_SPECIES_HIGH_BITS 5
#define CRYSTAL_EXT_ITEM_HIGH_BITS    6
#define CRYSTAL_EXT_MOVE_HIGH_BITS    5

static ALWAYS_INLINE u32 CrystalIdMask(u32 bits)
{
    return (1u << bits) - 1u;
}

static ALWAYS_INLINE u16 CrystalJoinId(u16 low, u32 extension, u32 lowBits, u32 highBits, u32 shift)
{
    return (low & CrystalIdMask(lowBits))
         | (((extension >> shift) & CrystalIdMask(highBits)) << lowBits);
}

static ALWAYS_INLINE void CrystalSetIdHigh(u32 *extension, u16 value, u32 lowBits, u32 highBits, u32 shift)
{
    const u32 mask = CrystalIdMask(highBits) << shift;
    *extension = (*extension & ~mask)
               | ((((u32)value >> lowBits) & CrystalIdMask(highBits)) << shift);
}

static ALWAYS_INLINE u16 CrystalGetMoveId(struct BoxPokemon *boxMon, u16 low, u32 shift)
{
    return CrystalJoinId(low, boxMon->crystalExtendedIds, 11, CRYSTAL_EXT_MOVE_HIGH_BITS, shift);
}

static ALWAYS_INLINE void CrystalSetMoveId(struct BoxPokemon *boxMon, u16 *unused, u16 value, u32 shift)
{
    (void)unused;
    CrystalSetIdHigh(&boxMon->crystalExtendedIds, value, 11, CRYSTAL_EXT_MOVE_HIGH_BITS, shift);
}

"""
    replace_once(pokemon_c, helper_anchor, helpers)

    replace_once(
        pokemon_c,
        """        case MON_DATA_SPECIES:
            retVal = IsBadEgg(boxMon) ? SPECIES_EGG : GetSubstruct0(boxMon)->species;
            break;
        case MON_DATA_HELD_ITEM:
            retVal = GetSubstruct0(boxMon)->heldItem;
            break;
""",
        """        case MON_DATA_SPECIES:
            retVal = IsBadEgg(boxMon)
                   ? SPECIES_EGG
                   : CrystalJoinId(GetSubstruct0(boxMon)->species, boxMon->crystalExtendedIds, 11, CRYSTAL_EXT_SPECIES_HIGH_BITS, CRYSTAL_EXT_SPECIES_SHIFT);
            break;
        case MON_DATA_HELD_ITEM:
            retVal = CrystalJoinId(GetSubstruct0(boxMon)->heldItem, boxMon->crystalExtendedIds, 10, CRYSTAL_EXT_ITEM_HIGH_BITS, CRYSTAL_EXT_ITEM_SHIFT);
            break;
""",
    )

    replace_once(
        pokemon_c,
        """        case MON_DATA_MOVE1:
            retVal = GetSubstruct1(boxMon)->move1;
            break;
        case MON_DATA_MOVE2:
            retVal = GetSubstruct1(boxMon)->move2;
            break;
        case MON_DATA_MOVE3:
            retVal = GetSubstruct1(boxMon)->move3;
            break;
        case MON_DATA_MOVE4:
            retVal = GetSubstruct1(boxMon)->move4;
            break;
""",
        """        case MON_DATA_MOVE1:
            retVal = CrystalGetMoveId(boxMon, GetSubstruct1(boxMon)->move1, CRYSTAL_EXT_MOVE1_SHIFT);
            break;
        case MON_DATA_MOVE2:
            retVal = CrystalGetMoveId(boxMon, GetSubstruct1(boxMon)->move2, CRYSTAL_EXT_MOVE2_SHIFT);
            break;
        case MON_DATA_MOVE3:
            retVal = CrystalGetMoveId(boxMon, GetSubstruct1(boxMon)->move3, CRYSTAL_EXT_MOVE3_SHIFT);
            break;
        case MON_DATA_MOVE4:
            retVal = CrystalGetMoveId(boxMon, GetSubstruct1(boxMon)->move4, CRYSTAL_EXT_MOVE4_SHIFT);
            break;
""",
    )

    replace_once(
        pokemon_c,
        """        case MON_DATA_SPECIES:
        {
            struct PokemonSubstruct0 *substruct0 = GetSubstruct0(boxMon);
            SET16(substruct0->species);
            if (substruct0->species)
                boxMon->hasSpecies = TRUE;
            else
                boxMon->hasSpecies = FALSE;
            break;
        }
        case MON_DATA_HELD_ITEM:
            SET16(GetSubstruct0(boxMon)->heldItem);
            break;
""",
        """        case MON_DATA_SPECIES:
        {
            struct PokemonSubstruct0 *substruct0 = GetSubstruct0(boxMon);
            u16 value;
            SET16(value);
            substruct0->species = value;
            CrystalSetIdHigh(&boxMon->crystalExtendedIds, value, 11, CRYSTAL_EXT_SPECIES_HIGH_BITS, CRYSTAL_EXT_SPECIES_SHIFT);
            boxMon->hasSpecies = value != SPECIES_NONE;
            break;
        }
        case MON_DATA_HELD_ITEM:
        {
            struct PokemonSubstruct0 *substruct0 = GetSubstruct0(boxMon);
            u16 value;
            SET16(value);
            substruct0->heldItem = value;
            CrystalSetIdHigh(&boxMon->crystalExtendedIds, value, 10, CRYSTAL_EXT_ITEM_HIGH_BITS, CRYSTAL_EXT_ITEM_SHIFT);
            break;
        }
""",
    )

    replace_once(
        pokemon_c,
        """        case MON_DATA_MOVE1:
            SET16(GetSubstruct1(boxMon)->move1);
            break;
        case MON_DATA_MOVE2:
            SET16(GetSubstruct1(boxMon)->move2);
            break;
        case MON_DATA_MOVE3:
            SET16(GetSubstruct1(boxMon)->move3);
            break;
        case MON_DATA_MOVE4:
            SET16(GetSubstruct1(boxMon)->move4);
            break;
""",
        """        case MON_DATA_MOVE1:
        case MON_DATA_MOVE2:
        case MON_DATA_MOVE3:
        case MON_DATA_MOVE4:
        {
            static const u8 shifts[] = {
                CRYSTAL_EXT_MOVE1_SHIFT,
                CRYSTAL_EXT_MOVE2_SHIFT,
                CRYSTAL_EXT_MOVE3_SHIFT,
                CRYSTAL_EXT_MOVE4_SHIFT,
            };
            struct PokemonSubstruct1 *substruct1 = GetSubstruct1(boxMon);
            u16 *moves[] = {
                (u16 *)&substruct1->move1,
                (u16 *)&substruct1->move2,
                (u16 *)&substruct1->move3,
                (u16 *)&substruct1->move4,
            };
            const u32 slot = field - MON_DATA_MOVE1;
            u16 value;
            SET16(value);
            *moves[slot] = value;
            CrystalSetMoveId(boxMon, moves[slot], value, shifts[slot]);
            break;
        }
""",
    )

    # Avoid taking addresses of C bitfields: replace the temporary array implementation
    # above with direct assignments after the structural replacement has created the block.
    replace_once(
        pokemon_c,
        """            struct PokemonSubstruct1 *substruct1 = GetSubstruct1(boxMon);
            u16 *moves[] = {
                (u16 *)&substruct1->move1,
                (u16 *)&substruct1->move2,
                (u16 *)&substruct1->move3,
                (u16 *)&substruct1->move4,
            };
            const u32 slot = field - MON_DATA_MOVE1;
            u16 value;
            SET16(value);
            *moves[slot] = value;
            CrystalSetMoveId(boxMon, moves[slot], value, shifts[slot]);
""",
        """            struct PokemonSubstruct1 *substruct1 = GetSubstruct1(boxMon);
            const u32 slot = field - MON_DATA_MOVE1;
            u16 value;
            SET16(value);
            switch (slot)
            {
            case 0: substruct1->move1 = value; break;
            case 1: substruct1->move2 = value; break;
            case 2: substruct1->move3 = value; break;
            default: substruct1->move4 = value; break;
            }
            CrystalSetIdHigh(&boxMon->crystalExtendedIds, value, 11, CRYSTAL_EXT_MOVE_HIGH_BITS, shifts[slot]);
""",
    )

    # Remove now-unused helper that existed only to make the first replacement readable.
    replace_once(
        pokemon_c,
        """static ALWAYS_INLINE void CrystalSetMoveId(struct BoxPokemon *boxMon, u16 *unused, u16 value, u32 shift)
{
    (void)unused;
    CrystalSetIdHigh(&boxMon->crystalExtendedIds, value, 11, CRYSTAL_EXT_MOVE_HIGH_BITS, shift);
}

""",
        "",
    )

    replace_once(
        pokemon_c,
        """static u16 CalculateBoxMonChecksum(struct BoxPokemon *boxMon)
{
    u32 checksum = 0;

    for (u32 i = 0; i < ARRAY_COUNT(boxMon->secure.raw); i++)
        checksum += boxMon->secure.raw[i] + (boxMon->secure.raw[i] >> 16);

    return checksum;
}
""",
        """static u16 CalculateBoxMonChecksum(struct BoxPokemon *boxMon)
{
    u32 checksum = boxMon->crystalExtendedIds + (boxMon->crystalExtendedIds >> 16);

    for (u32 i = 0; i < ARRAY_COUNT(boxMon->secure.raw); i++)
        checksum += boxMon->secure.raw[i] + (boxMon->secure.raw[i] >> 16);

    return checksum;
}
""",
    )

    replace_once(
        pokemon_c,
        """static u16 CalculateBoxMonChecksumDecrypt(struct BoxPokemon *boxMon)
{
    u32 checksum = 0;

    for (u32 i = 0; i < ARRAY_COUNT(boxMon->secure.raw); i++)
    {
        boxMon->secure.raw[i] ^= (boxMon->otId ^ boxMon->personality);
        checksum += boxMon->secure.raw[i] + (boxMon->secure.raw[i] >> 16);
    }

    return checksum;
}
""",
        """static u16 CalculateBoxMonChecksumDecrypt(struct BoxPokemon *boxMon)
{
    const u32 key = boxMon->otId ^ boxMon->personality;
    u32 checksum;

    boxMon->crystalExtendedIds ^= key;
    checksum = boxMon->crystalExtendedIds + (boxMon->crystalExtendedIds >> 16);

    for (u32 i = 0; i < ARRAY_COUNT(boxMon->secure.raw); i++)
    {
        boxMon->secure.raw[i] ^= key;
        checksum += boxMon->secure.raw[i] + (boxMon->secure.raw[i] >> 16);
    }

    return checksum;
}
""",
    )

    replace_once(
        pokemon_c,
        """static u16 CalculateBoxMonChecksumReencrypt(struct BoxPokemon *boxMon)
{
    u32 checksum = 0;

    for (u32 i = 0; i < ARRAY_COUNT(boxMon->secure.raw); i++)
    {
        checksum += boxMon->secure.raw[i] + (boxMon->secure.raw[i] >> 16);
        boxMon->secure.raw[i] ^= (boxMon->otId ^ boxMon->personality);
    }

    return checksum;
}
""",
        """static u16 CalculateBoxMonChecksumReencrypt(struct BoxPokemon *boxMon)
{
    const u32 key = boxMon->otId ^ boxMon->personality;
    u32 checksum = boxMon->crystalExtendedIds + (boxMon->crystalExtendedIds >> 16);

    boxMon->crystalExtendedIds ^= key;
    for (u32 i = 0; i < ARRAY_COUNT(boxMon->secure.raw); i++)
    {
        checksum += boxMon->secure.raw[i] + (boxMon->secure.raw[i] >> 16);
        boxMon->secure.raw[i] ^= key;
    }

    return checksum;
}
""",
    )

    replace_once(
        pokemon_c,
        """static void EncryptBoxMon(struct BoxPokemon *boxMon)
{
    for (u32 i = 0; i < ARRAY_COUNT(boxMon->secure.raw); i++)
    {
        boxMon->secure.raw[i] ^= boxMon->personality;
        boxMon->secure.raw[i] ^= boxMon->otId;
    }
}
""",
        """static void EncryptBoxMon(struct BoxPokemon *boxMon)
{
    const u32 key = boxMon->personality ^ boxMon->otId;
    boxMon->crystalExtendedIds ^= key;
    for (u32 i = 0; i < ARRAY_COUNT(boxMon->secure.raw); i++)
        boxMon->secure.raw[i] ^= key;
}
""",
    )

    replace_once(
        pokemon_c,
        """static void DecryptBoxMon(struct BoxPokemon *boxMon)
{
    for (u32 i = 0; i < ARRAY_COUNT(boxMon->secure.raw); i++)
    {
        boxMon->secure.raw[i] ^= boxMon->otId;
        boxMon->secure.raw[i] ^= boxMon->personality;
    }
}
""",
        """static void DecryptBoxMon(struct BoxPokemon *boxMon)
{
    const u32 key = boxMon->personality ^ boxMon->otId;
    boxMon->crystalExtendedIds ^= key;
    for (u32 i = 0; i < ARRAY_COUNT(boxMon->secure.raw); i++)
        boxMon->secure.raw[i] ^= key;
}
""",
    )

    replace_once(
        pokemon_c,
        """    DecryptBoxMon(&old);
    boxMon->personality = personality;
    *new0 = *old0;
""",
        """    DecryptBoxMon(&old);
    boxMon->personality = personality;
    boxMon->crystalExtendedIds = old.crystalExtendedIds;
    *new0 = *old0;
""",
    )

    replace_once(
        save_h,
        """#define SECTOR_ID_PKMN_STORAGE_END   13
#define NUM_SECTORS_PER_SLOT         14
// Save Slot 1: 0-13;  Save Slot 2: 14-27
#define SECTOR_ID_HOF_1              28
#define SECTOR_ID_HOF_2              29
#define SECTOR_ID_TRAINER_HILL       30
#define SECTOR_ID_RECORDED_BATTLE    31
#define SECTORS_COUNT                32
""",
        """#define SECTOR_ID_PKMN_STORAGE_END   14
#define NUM_SECTORS_PER_SLOT         15
// CRYSTAL: Save Slot 1: 0-14; Save Slot 2: 15-29.
// The final two physical sectors retain Hall of Fame storage.
// Hoenn Trainer Hill / Recorded Battle standalone sectors are not part of
// the CRYSTAL native save profile.
#define SECTOR_ID_HOF_1              30
#define SECTOR_ID_HOF_2              31
#define SECTOR_ID_TRAINER_HILL       0xFE
#define SECTOR_ID_RECORDED_BATTLE    0xFF
#define SECTORS_COUNT                32
""",
    )

    replace_once(
        save_c,
        """    SAVEBLOCK_CHUNK(struct PokemonStorage, 7),
    SAVEBLOCK_CHUNK(struct PokemonStorage, 8), // SECTOR_ID_PKMN_STORAGE_END
};
""",
        """    SAVEBLOCK_CHUNK(struct PokemonStorage, 7),
    SAVEBLOCK_CHUNK(struct PokemonStorage, 8),
    SAVEBLOCK_CHUNK(struct PokemonStorage, 9), // SECTOR_ID_PKMN_STORAGE_END
};
""",
    )

    replace_once(
        save_c,
        """    if (sector != SECTOR_ID_TRAINER_HILL && sector != SECTOR_ID_RECORDED_BATTLE)
        return SAVE_STATUS_ERROR;

    ReadFlash(sector, 0, (u8 *)&gSaveDataBuffer, SECTOR_SIZE);
""",
        """    if (sector >= SECTORS_COUNT)
        return SAVE_STATUS_ERROR;
    if (sector != SECTOR_ID_TRAINER_HILL && sector != SECTOR_ID_RECORDED_BATTLE)
        return SAVE_STATUS_ERROR;

    ReadFlash(sector, 0, (u8 *)&gSaveDataBuffer, SECTOR_SIZE);
""",
    )

    replace_once(
        save_c,
        """    if (sector != SECTOR_ID_TRAINER_HILL && sector != SECTOR_ID_RECORDED_BATTLE)
        return SAVE_STATUS_ERROR;

    savDataBuffer = &gSaveDataBuffer;
""",
        """    if (sector >= SECTORS_COUNT)
        return SAVE_STATUS_ERROR;
    if (sector != SECTOR_ID_TRAINER_HILL && sector != SECTOR_ID_RECORDED_BATTLE)
        return SAVE_STATUS_ERROR;

    savDataBuffer = &gSaveDataBuffer;
""",
    )

    recorded_c = root / "src/recorded_battle.c"

    replace_once(
        recorded_c,
        """// Save data using TryWriteSpecialSaveSector is allowed to exceed SECTOR_DATA_SIZE (up to the counter field)
STATIC_ASSERT(sizeof(struct RecordedBattleSave) <= SECTOR_COUNTER_OFFSET, RecordedBattleSaveFreeSpace);
""",
        """// CRYSTAL native saves use sectors 30-31 for Hall of Fame after the
// 15-sector dual-save expansion. Standalone Recorded Battle persistence is
// intentionally disabled instead of allowing an oversized write.
""",
    )

    replace_once(
        recorded_c,
        """static bool32 RecordedBattleToSave(struct RecordedBattleSave *battleSave, struct RecordedBattleSave *saveSector)
{
    memset(saveSector, 0, SECTOR_SIZE);
    memcpy(saveSector, battleSave, sizeof(*battleSave));

    saveSector->checksum = CalcByteArraySum((void *)(saveSector), sizeof(*saveSector) - 4);

    if (TryWriteSpecialSaveSector(SECTOR_ID_RECORDED_BATTLE, (void *)(saveSector)) != SAVE_STATUS_OK)
        return FALSE;
    else
        return TRUE;
}
""",
        """static bool32 RecordedBattleToSave(struct RecordedBattleSave *battleSave, struct RecordedBattleSave *saveSector)
{
    (void)battleSave;
    (void)saveSector;
    return FALSE;
}
""",
    )

    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("CRYSTAL Gen10 engine patch: applied cleanly")
    return 0

if __name__ == "__main__":
    sys.exit(main())
