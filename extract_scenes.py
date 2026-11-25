#!/usr/bin/env python3
"""
scenes.csv 의 video / time_sec 열을 보고 원본 화질 사진을 뽑는 스크립트.
결과 파일 이름은 file 열(S01.jpg 등)을 따른다.

사용법:
  python3 extract_scenes.py scenes.csv <영상이 있는 폴더> [저장 폴더]
예:
  python3 extract_scenes.py scenes.csv "07.지능형_관제_서비스_CCTV_영상_데이터/3.개방데이터/1.데이터" originals
"""
import csv
import subprocess
import sys
from pathlib import Path

if len(sys.argv) < 3:
    print(__doc__)
    sys.exit(1)

csv_path, video_root = Path(sys.argv[1]), Path(sys.argv[2])
out = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("originals")
out.mkdir(parents=True, exist_ok=True)

videos = {p.stem: p for p in video_root.rglob("*.mp4")}
with open(csv_path, encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

for r in rows:
    sid, vid, t, name = r["scene_id"], r["video"].strip(), r["time_sec"].strip(), r["file"].strip()
    if not t:
        print(f"  [건너뜀] {sid}: time_sec 비어 있음")
        continue
    v = videos.get(vid.replace(".mp4", ""))
    if v is None:
        print(f"  [건너뜀] {sid}: 영상 {vid} 를 찾지 못함")
        continue
    dst = out / name
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", t, "-i", str(v),
                    "-frames:v", "1", "-q:v", "2", str(dst)], check=False)
    print(f"  {'완료' if dst.exists() else '실패'} {sid}: {vid} {t}초 -> {dst}")
print(f"\n끝! {out.resolve()} 폴더를 확인하세요.")
