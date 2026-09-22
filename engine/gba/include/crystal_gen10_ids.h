#ifndef GUARD_CRYSTAL_GEN10_IDS_H
#define GUARD_CRYSTAL_GEN10_IDS_H

#include <stdint.h>

/*
 * CRYSTAL GBA Generation 10-ready identity extension.
 *
 * The pinned pokeemerald-expansion BoxPokemon stores:
 *   Species: 11 low bits
 *   Item:    10 low bits
 *   Move:    11 low bits x4
 *
 * One 32-bit extension word supplies the missing high bits:
 *   Species +5, Item +6, Move +5 x4 = 31 bits.
 * Bit 31 stays reserved for a future schema flag.
 */
#define CRYSTAL_GEN10_ID_BITS 16u
#define CRYSTAL_GEN10_ID_MAX  0xFFFFu

#define CRYSTAL_GEN10_SPECIES_LOW_BITS 11u
#define CRYSTAL_GEN10_ITEM_LOW_BITS    10u
#define CRYSTAL_GEN10_MOVE_LOW_BITS    11u

#define CRYSTAL_GEN10_SPECIES_HIGH_BITS (CRYSTAL_GEN10_ID_BITS - CRYSTAL_GEN10_SPECIES_LOW_BITS)
#define CRYSTAL_GEN10_ITEM_HIGH_BITS    (CRYSTAL_GEN10_ID_BITS - CRYSTAL_GEN10_ITEM_LOW_BITS)
#define CRYSTAL_GEN10_MOVE_HIGH_BITS    (CRYSTAL_GEN10_ID_BITS - CRYSTAL_GEN10_MOVE_LOW_BITS)

#define CRYSTAL_GEN10_SPECIES_HIGH_SHIFT 0u
#define CRYSTAL_GEN10_ITEM_HIGH_SHIFT    5u
#define CRYSTAL_GEN10_MOVE1_HIGH_SHIFT   11u
#define CRYSTAL_GEN10_MOVE2_HIGH_SHIFT   16u
#define CRYSTAL_GEN10_MOVE3_HIGH_SHIFT   21u
#define CRYSTAL_GEN10_MOVE4_HIGH_SHIFT   26u
#define CRYSTAL_GEN10_RESERVED_SHIFT     31u

#define CRYSTAL_GEN10_MASK(width) ((uint32_t)((1u << (width)) - 1u))
#define CRYSTAL_GEN10_SPECIES_LOW_MASK ((uint16_t)CRYSTAL_GEN10_MASK(CRYSTAL_GEN10_SPECIES_LOW_BITS))
#define CRYSTAL_GEN10_ITEM_LOW_MASK    ((uint16_t)CRYSTAL_GEN10_MASK(CRYSTAL_GEN10_ITEM_LOW_BITS))
#define CRYSTAL_GEN10_MOVE_LOW_MASK    ((uint16_t)CRYSTAL_GEN10_MASK(CRYSTAL_GEN10_MOVE_LOW_BITS))
#define CRYSTAL_GEN10_HIGH_WORD_USED_MASK 0x7FFFFFFFu

struct CrystalGen10Ids
{
    uint16_t species;
    uint16_t heldItem;
    uint16_t moves[4];
};

static inline uint32_t CrystalGen10PackHighIds(const struct CrystalGen10Ids *ids)
{
    return (((uint32_t)ids->species >> CRYSTAL_GEN10_SPECIES_LOW_BITS) & CRYSTAL_GEN10_MASK(CRYSTAL_GEN10_SPECIES_HIGH_BITS)) << CRYSTAL_GEN10_SPECIES_HIGH_SHIFT
         | (((uint32_t)ids->heldItem >> CRYSTAL_GEN10_ITEM_LOW_BITS) & CRYSTAL_GEN10_MASK(CRYSTAL_GEN10_ITEM_HIGH_BITS)) << CRYSTAL_GEN10_ITEM_HIGH_SHIFT
         | (((uint32_t)ids->moves[0] >> CRYSTAL_GEN10_MOVE_LOW_BITS) & CRYSTAL_GEN10_MASK(CRYSTAL_GEN10_MOVE_HIGH_BITS)) << CRYSTAL_GEN10_MOVE1_HIGH_SHIFT
         | (((uint32_t)ids->moves[1] >> CRYSTAL_GEN10_MOVE_LOW_BITS) & CRYSTAL_GEN10_MASK(CRYSTAL_GEN10_MOVE_HIGH_BITS)) << CRYSTAL_GEN10_MOVE2_HIGH_SHIFT
         | (((uint32_t)ids->moves[2] >> CRYSTAL_GEN10_MOVE_LOW_BITS) & CRYSTAL_GEN10_MASK(CRYSTAL_GEN10_MOVE_HIGH_BITS)) << CRYSTAL_GEN10_MOVE3_HIGH_SHIFT
         | (((uint32_t)ids->moves[3] >> CRYSTAL_GEN10_MOVE_LOW_BITS) & CRYSTAL_GEN10_MASK(CRYSTAL_GEN10_MOVE_HIGH_BITS)) << CRYSTAL_GEN10_MOVE4_HIGH_SHIFT;
}

static inline uint16_t CrystalGen10SpeciesLow(uint16_t id)
{
    return (uint16_t)(id & CRYSTAL_GEN10_SPECIES_LOW_MASK);
}

static inline uint16_t CrystalGen10ItemLow(uint16_t id)
{
    return (uint16_t)(id & CRYSTAL_GEN10_ITEM_LOW_MASK);
}

static inline uint16_t CrystalGen10MoveLow(uint16_t id)
{
    return (uint16_t)(id & CRYSTAL_GEN10_MOVE_LOW_MASK);
}

static inline uint16_t CrystalGen10Join(uint16_t low, uint32_t highWord, uint32_t lowBits, uint32_t highBits, uint32_t shift)
{
    const uint32_t lowMask = CRYSTAL_GEN10_MASK(lowBits);
    const uint32_t highMask = CRYSTAL_GEN10_MASK(highBits);
    return (uint16_t)(((uint32_t)low & lowMask) | (((highWord >> shift) & highMask) << lowBits));
}

static inline uint16_t CrystalGen10JoinSpecies(uint16_t low, uint32_t highWord)
{
    return CrystalGen10Join(low, highWord, CRYSTAL_GEN10_SPECIES_LOW_BITS, CRYSTAL_GEN10_SPECIES_HIGH_BITS, CRYSTAL_GEN10_SPECIES_HIGH_SHIFT);
}

static inline uint16_t CrystalGen10JoinItem(uint16_t low, uint32_t highWord)
{
    return CrystalGen10Join(low, highWord, CRYSTAL_GEN10_ITEM_LOW_BITS, CRYSTAL_GEN10_ITEM_HIGH_BITS, CRYSTAL_GEN10_ITEM_HIGH_SHIFT);
}

static inline uint16_t CrystalGen10JoinMove(uint16_t low, uint32_t highWord, unsigned slot)
{
    static const uint8_t shifts[4] = {
        CRYSTAL_GEN10_MOVE1_HIGH_SHIFT,
        CRYSTAL_GEN10_MOVE2_HIGH_SHIFT,
        CRYSTAL_GEN10_MOVE3_HIGH_SHIFT,
        CRYSTAL_GEN10_MOVE4_HIGH_SHIFT,
    };
    return slot < 4
        ? CrystalGen10Join(low, highWord, CRYSTAL_GEN10_MOVE_LOW_BITS, CRYSTAL_GEN10_MOVE_HIGH_BITS, shifts[slot])
        : 0;
}

#endif
