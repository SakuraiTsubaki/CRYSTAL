#!/usr/bin/env python3
"""Patch pinned pret/pokecrystal into CRYSTAL's native GBC Stage 0 source build."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

PINNED = "e058e4f50b3bbf7377e036b81c25a72c54656c5c"


def fail(message: str) -> None:
    raise SystemExit(f"native source Stage 0 patch failed: {message}")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        fail(f"{path}: expected exactly one target, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def check_head(root: Path) -> None:
    head = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    if head != PINNED:
        fail(f"source HEAD {head} != pinned {PINNED}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    root = args.source.resolve()
    check_head(root)

    replace_once(
        root / "constants/ram_constants.asm",
        "DEF NUM_SRAM_BANKS EQU 4",
        "DEF NUM_SRAM_BANKS EQU 8",
    )

    replace_once(
        root / "engine/menus/empty_sram.asm",
        """EmptyAllSRAMBanks:
for x, NUM_SRAM_BANKS
	ld a, x
	call .EmptyBank
endr
	ret
""",
        """EmptyAllSRAMBanks:
; CRYSTAL: keep this routine exactly 21 bytes like retail international
; while expanding the bank range from 0..3 to 0..7.
	xor a
.loop
	push af
	call .EmptyBank
	pop af
	inc a
	cp NUM_SRAM_BANKS
	jr c, .loop
	xor a
	ret
	ds 8, 0
""",
    )

    replace_once(
        root / "Makefile",
        "RGBFIXFLAGS += -Cjv -t PM_CRYSTAL -k 01 -l 0x33 -m MBC3+TIMER+RAM+BATTERY -r 3 -p 0",
        "RGBFIXFLAGS += -Cjv -t PM_CRYSTAL -k 01 -l 0x33 -m MBC3+TIMER+RAM+BATTERY -r 5 -p 0",
    )

    replace_once(
        root / "Makefile",
        """\t$(RGBLINK) $(RGBLINKFLAGS) -l layout.link -n $*.sym -m $*.map -o $@ $(filter %.o,$^)
\t$(RGBFIX) $(RGBFIXFLAGS) $@
\ttools/stadium $@
""",
        """\t$(RGBLINK) $(RGBLINKFLAGS) -l layout.link -n $*.sym -m $*.map -o $@ $(filter %.o,$^)
\tpython3 tools/crystal_expand_padding.py $@
\t$(RGBFIX) $(RGBFIXFLAGS) $@
\ttools/stadium $@
""",
    )

    replace_once(
        root / "main.asm",
        """\tds $220
""",
        """\tds $220


SECTION "CRYSTAL Expansion End", ROMX[$7fff], BANK[$ff]
\tdb $ff
""",
    )

    replace_once(
        root / "layout.link",
        """ROMX $7f
\torg $7de0
\t"Stadium 2 Checksums"
WRAM0
""",
        """ROMX $7f
\torg $7de0
\t"Stadium 2 Checksums"
ROMX $ff
\torg $7fff
\t"CRYSTAL Expansion End"
WRAM0
""",
    )

    stadium = root / "tools/stadium.c"
    replace_once(
        stadium,
        """// A matching ROM is 2 MB
#define ROM_SIZE (NUM_BANKS * BANK_SIZE)
""",
        """// Stadium compatibility metadata still describes the original 128-bank domain.
#define ROM_SIZE (NUM_BANKS * BANK_SIZE)
// CRYSTAL native Stage 0 physically expands the cartridge image to 256 banks / 4 MiB.
#define EXPANDED_ROM_SIZE (256 * BANK_SIZE)
""",
    )
    replace_once(
        stadium,
        "void calculate_checksums(uint8_t *file, bool european) {",
        "void calculate_checksums(uint8_t *file, bool european, size_t filesize) {",
    )
    replace_once(
        stadium,
        """\tuint16_t globalsum = calculate_checksum(0, file, ROM_SIZE);
\tSET_U16BE(file + GLOBAL_OFF, globalsum);
""",
        """\tuint16_t globalsum = calculate_checksum(0, file, filesize);
\tSET_U16BE(file + GLOBAL_OFF, globalsum);
""",
    )
    replace_once(
        stadium,
        """\tif (filesize == ROM_SIZE) {
\t\tcalculate_checksums(file, european);
\t}
""",
        """\tif (filesize == ROM_SIZE || filesize == EXPANDED_ROM_SIZE) {
\t\tcalculate_checksums(file, european, (size_t)filesize);
\t}
""",
    )

    padding = root / "tools/crystal_expand_padding.py"
    padding.write_text(
        """#!/usr/bin/env python3
from pathlib import Path
import sys

ORIGINAL = 0x200000
EXPANDED = 0x400000

if len(sys.argv) != 2:
    raise SystemExit("usage: crystal_expand_padding.py ROM")

path = Path(sys.argv[1])
data = bytearray(path.read_bytes())
if len(data) != EXPANDED:
    raise SystemExit(f"expected 4 MiB linked image, got {len(data):#x}")
data[ORIGINAL:] = b"\\xff" * (EXPANDED - ORIGINAL)
path.write_bytes(data)
""",
        encoding="utf-8",
    )

    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("CRYSTAL native source Stage 0 patch: applied cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
