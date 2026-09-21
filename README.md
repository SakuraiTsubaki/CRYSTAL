# CRYSTAL

**ポケットモンスター クリスタル** (Generation II)를 **Game Boy Advance / Generation III 계열 기반의 현대화 리메이크**로 재구축하는 저장소입니다.

## 현재 정본 방향

- 일본판 원작과 모든 확인된 revision을 원전으로 전수조사합니다.
- 원작의 지역, 스토리, 이벤트, NPC, 버전 고유 요소는 보존합니다.
- 포켓몬/타입/특성/기술/진화/폼/아이템/전투·육성 규칙은 현재 검증 가능한 최신 공식 기준으로 현대화합니다.
- 최종 실행 대상은 **GBA**입니다.
- GB/GBC mapper, SRAM, 원본 주소 구조는 원본 분석 자료로 보존하지만 최종 런타임 엔진으로 사용하지 않습니다.
- 미출시·미검증 세대 콘텐츠는 추측하지 않습니다.

## 기반

- 원본 조사: `SakuraiTsubaki/PocketMonsters-Crystal-Disassembly`
- 공통 현대화 연구: `SakuraiTsubaki/EMERALD`
- 현대 코어 기준: `rh-hideout/pokeemerald-expansion@75b806a3ab57a81ff1eb6179288981f0b3cc3050`

## 문서

- `PROJECT.md` — 현재 프로젝트 방향의 정본
- `config/remake.json` — 기계 판독 가능한 작품/엔진/원본 기준
- `docs/REMAKE_POLICY.md` — 원작 보존과 최신화 정책

저장소에 남아 있는 이전 확장 설계 문서와 도구는 삭제하지 않습니다. 원본 구조·세이브·ID·용량 연구 자료로 보존하며, GBA 리메이크에 필요한 내용만 새 런타임 설계로 옮깁니다.

ROM 바이너리는 GitHub에 커밋하지 않습니다.
