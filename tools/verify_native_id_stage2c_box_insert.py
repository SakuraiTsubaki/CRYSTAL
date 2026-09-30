#!/usr/bin/env python3
"""Verify native Stage 2c legacy box insertion helpers."""

from __future__ import annotations
import argparse,re
from pathlib import Path

SYMBOL_RE=re.compile(r"^([0-9A-Fa-f]{2}):([0-9A-Fa-f]{4})\s+(\S+)$")
REQUIRED=(
 "CrystalClearTempSidecar",
 "CrystalInsertLegacyZeroSidecarIntoCurrentBox",
 "CrystalInsertLegacyZeroSidecarAtBoxFront",
)

def symbols(path:Path):
    out={}
    for line in path.read_text(encoding="utf-8").splitlines():
        m=SYMBOL_RE.match(line.strip())
        if m:
            b,a,n=m.groups();out[n]=(int(b,16),int(a,16))
    return out

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("rom",type=Path)
    ap.add_argument("sym",type=Path)
    args=ap.parse_args()
    sym=symbols(args.sym)
    for name in REQUIRED:
        bank,addr=sym.get(name,(-1,-1))
        if bank!=0x80 or not (0x4000<=addr<0x8000):
            raise SystemExit(f"{name}: expected bank 0x80, got {bank:#x}:{addr:#x}")
    if len(args.rom.read_bytes())!=0x400000:
        raise SystemExit("ROM size changed")
    print(f"{args.rom.name}: Stage 2c legacy box insertion bridge OK")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
