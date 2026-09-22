#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "crystal_gen10_ids.h"

static void RoundTrip(uint16_t species, uint16_t item,
                      uint16_t m1, uint16_t m2, uint16_t m3, uint16_t m4)
{
    struct CrystalGen10Ids ids = { species, item, { m1, m2, m3, m4 } };
    const uint32_t high = CrystalGen10PackHighIds(&ids);

    assert((high & ~CRYSTAL_GEN10_HIGH_WORD_USED_MASK) == 0);
    assert(CrystalGen10JoinSpecies(CrystalGen10SpeciesLow(species), high) == species);
    assert(CrystalGen10JoinItem(CrystalGen10ItemLow(item), high) == item);
    assert(CrystalGen10JoinMove(CrystalGen10MoveLow(m1), high, 0) == m1);
    assert(CrystalGen10JoinMove(CrystalGen10MoveLow(m2), high, 1) == m2);
    assert(CrystalGen10JoinMove(CrystalGen10MoveLow(m3), high, 2) == m3);
    assert(CrystalGen10JoinMove(CrystalGen10MoveLow(m4), high, 3) == m4);
}

int main(void)
{
    RoundTrip(0, 0, 0, 0, 0, 0);
    RoundTrip(1, 1, 1, 1, 1, 1);
    RoundTrip(1572, 873, 847, 934, 2047, 2048);
    RoundTrip(2047, 1023, 2047, 2047, 2047, 2047);
    RoundTrip(2048, 1024, 2048, 4095, 32768, 65535);
    RoundTrip(65535, 65535, 65535, 65535, 65535, 65535);

    struct CrystalGen10Ids max = {65535, 65535, {65535, 65535, 65535, 65535}};
    assert(CrystalGen10PackHighIds(&max) == 0x7FFFFFFFu);
    assert(CrystalGen10JoinMove(0, 0, 4) == 0);

    puts("CRYSTAL Gen10 16-bit ID packing: OK");
    return 0;
}
