#!/usr/bin/env python3
"""
실험 자극 이미지를 그룹별로 만드는 스크립트 (세로 720x1280, 휴대폰 화면용).

화면 구성 (모든 그룹 공통 위치)
  0   ~ 120   상단 바   : "CCTV 화면" + AI 라벨 배지 (G3 1단계는 배지 없음)
  120 ~ 660   장면      : 원본 높이 전체를 4:3 으로 자른 사진 (720x540)
  660 ~ 1060  보고서 칸 : G2 만 생성형 AI 보고서, 나머지 그룹은 빈칸
  1060~ 1280  버튼 자리 : 비워 둠 (PsyToolkit 에서 [신고] [무시] 버튼을 올림)

입력
  scenes.csv : scene_id, file, label, boxes, roi, r_time, r_place, r_text 열 사용
    boxes : 사람마다 "x1 y1 x2 y2", 여러 명이면 | 로 구분 (원본 픽셀 좌표)
    roi   : 감시 구역 꼭짓점 "x y" 를 ; 로 구분 (침입 장면만)
    zoom  : (선택) 확대 배율. 비우면 1 (확대 없음). 예) 1.5 -> 1.5배 확대, 모든 그룹에 똑같이 적용
  originals/ : extract_scenes.py 로 뽑은 원본 사진

출력 (out 폴더)
  g1/        라벨 + 사람 박스 (+ 감시 구역)
  g2/        g1 + 생성형 AI 보고서
  g3_step1/  사람 박스·라벨 없음 (감시 구역만)
  g3_step2/  g1 과 동일 (G3 최종 판단 화면)

사용법
  python3 make_stimuli.py scenes.csv originals stimuli
"""
import csv
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---- 화면 크기와 영역 ----
W, H = 720, 1280
TOP_H = 120
SCENE_Y, SCENE_W, SCENE_H = TOP_H, 720, 540
REPORT_Y, REPORT_H = SCENE_Y + SCENE_H, 400
BUTTON_Y = REPORT_Y + REPORT_H          # 1060 ~ 1280 비움

# 원본 높이 전체를 쓰고 너비는 높이의 4/3 (1920x1080 -> 1440x1080, 1280x720 -> 960x720)
# 해상도가 달라도 화면에 보이는 범위(배율)는 모든 장면이 같다
GEO = {"cw": 1440, "ch": 1080, "scale": 0.5}

# ---- 스타일 (모든 장면 동일) ----
BG = (18, 22, 30)
TOP_BG = (28, 34, 46)
BOX_COLOR = (235, 40, 40)
BOX_WIDTH = 2
ROI_COLOR = (255, 210, 0)
ROI_WIDTH = 3
ROI_DASH = 12
LABEL_BG = (205, 25, 25)
REPORT_BG = (34, 44, 60)
REPORT_HEAD = (62, 100, 160)
MUTED = (160, 170, 185)

ATTN_TEXT = "판단과 관계없이 [무시]를 눌러 주십시오"

FONT_BOLD = [
    "/mnt/c/Windows/Fonts/malgunbd.ttf",
    "C:/Windows/Fonts/malgunbd.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
]
FONT_REG = [
    "/mnt/c/Windows/Fonts/malgun.ttf",
    "C:/Windows/Fonts/malgun.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
]


def font(size, bold=False):
    for p in (FONT_BOLD if bold else FONT_REG) + FONT_BOLD + FONT_REG:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    sys.exit("한글 폰트를 찾지 못했어요. 'sudo apt install -y fonts-nanum' 후 다시 실행하세요.")


def parse_boxes(s):
    out = []
    for part in (s or "").split("|"):
        nums = part.split()
        if len(nums) == 4:
            out.append(tuple(float(n) for n in nums))
    return out


def parse_roi(s):
    pts = []
    for part in (s or "").split(";"):
        nums = part.split()
        if len(nums) == 2:
            pts.append((float(nums[0]), float(nums[1])))
    return pts


def crop_origin(img_w, img_h, boxes, sid, zoom=1.0):
    """박스들이 가운데 오도록 4:3 영역의 왼쪽 위 좌표를 정한다. zoom>1 이면 그만큼 확대."""
    GEO["ch"] = round(img_h / zoom)
    GEO["cw"] = min(round(GEO["ch"] * 4 / 3), img_w)
    GEO["scale"] = SCENE_W / GEO["cw"]
    CROP_W, CROP_H = GEO["cw"], GEO["ch"]
    if boxes:
        x1 = min(b[0] for b in boxes); x2 = max(b[2] for b in boxes)
        y1 = min(b[1] for b in boxes); y2 = max(b[3] for b in boxes)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        if x2 - x1 > CROP_W or y2 - y1 > CROP_H:
            print(f"  [주의] {sid}: 박스가 잘라낼 영역보다 넓어서 일부가 잘릴 수 있어요")
    else:
        cx, cy = img_w / 2, img_h / 2
    ox = min(max(cx - CROP_W / 2, 0), max(img_w - CROP_W, 0))
    oy = min(max(cy - CROP_H / 2, 0), max(img_h - CROP_H, 0))
    return ox, oy


def to_scene(pt, ox, oy):
    return ((pt[0] - ox) * GEO["scale"], (pt[1] - oy) * GEO["scale"] + SCENE_Y)


def dashed_polygon(d, pts):
    if len(pts) < 2:
        return
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        n = max(int(length // ROI_DASH), 1)
        for i in range(0, n, 2):
            a, b = i / n, min((i + 1) / n, 1)
            d.line([(x1 + (x2 - x1) * a, y1 + (y2 - y1) * a),
                    (x1 + (x2 - x1) * b, y1 + (y2 - y1) * b)], fill=ROI_COLOR, width=ROI_WIDTH)


def wrap(d, text, f, width):
    """띄어쓰기 단위로 줄바꿈 (단어 중간에서 끊지 않음)."""
    lines, cur = [], ""
    for word in text.split():
        trial = word if not cur else cur + " " + word
        if d.textlength(trial, font=f) > width and cur:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def canvas(photo, ox, oy, roi):
    """상단 바 + 장면(+감시 구역)까지 그린 기본 화면."""
    img = Image.new("RGB", (W, H), BG)
    cw, ch = GEO["cw"], GEO["ch"]
    scene = photo.crop((int(ox), int(oy), int(ox) + cw, int(oy) + ch))
    img.paste(scene.resize((SCENE_W, SCENE_H), Image.LANCZOS), (0, SCENE_Y))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, TOP_H], fill=TOP_BG)
    d.text((28, 22), "CCTV 화면", font=font(22), fill=MUTED)
    if roi:
        d2 = ImageDraw.Draw(img)
        dashed_polygon(d2, [to_scene(p, ox, oy) for p in roi])
        # 감시 구역 선이 상단 바·보고서 칸으로 넘어가지 않게 다시 덮기
        d2.rectangle([0, 0, W, TOP_H - 1], fill=TOP_BG)
        d2.text((28, 22), "CCTV 화면", font=font(22), fill=MUTED)
        d2.rectangle([0, REPORT_Y, W, H], fill=BG)
    return img


def warning_badge(d, label):
    f = font(30, bold=True)
    text = f"{label} 감지"
    tw = d.textlength(text, font=f)
    x, y, h = 28, 56, 50
    d.rounded_rectangle([x, y, x + 60 + tw + 20, y + h], radius=8, fill=LABEL_BG)
    tx, ty = x + 16, y + 9                                  # 경고 삼각형
    d.polygon([(tx + 16, ty), (tx + 32, ty + 30), (tx, ty + 30)], fill="white")
    d.text((tx + 13, ty + 5), "!", font=font(22, bold=True), fill=LABEL_BG)
    d.text((x + 60, y + 6), text, font=f, fill="white")


def add_boxes(d, boxes, ox, oy):
    for b in boxes:
        x1, y1 = to_scene((b[0], b[1]), ox, oy)
        x2, y2 = to_scene((b[2], b[3]), ox, oy)
        x1, x2 = max(x1, 0), min(x2, W - 1)
        y1, y2 = max(y1, SCENE_Y), min(y2, SCENE_Y + SCENE_H - 1)
        d.rectangle([x1, y1, x2, y2], outline=BOX_COLOR, width=BOX_WIDTH)


def add_attn(d):
    f = font(26, bold=True)
    y = SCENE_Y + SCENE_H - 64
    d.rectangle([0, y, W, SCENE_Y + SCENE_H], fill=(0, 0, 0))
    tw = d.textlength(ATTN_TEXT, font=f)
    d.text(((W - tw) / 2, y + 16), ATTN_TEXT, font=f, fill=(255, 220, 0))


def add_report(d, row, sid):
    x0, x1 = 24, W - 24
    y = REPORT_Y + 20
    d.rounded_rectangle([x0, y, x1, REPORT_Y + REPORT_H - 10], radius=10, fill=REPORT_BG)
    d.rounded_rectangle([x0, y, x1, y + 48], radius=10, fill=REPORT_HEAD)
    d.rectangle([x0, y + 30, x1, y + 48], fill=REPORT_HEAD)
    d.text((x0 + 18, y + 9), "생성형 AI 분석 보고서", font=font(24, bold=True), fill="white")
    y += 62
    fk, fv = font(21, bold=True), font(21)
    for k, v in (("일시", row["r_time"]), ("장소", row["r_place"]), ("이벤트", row["label"])):
        d.text((x0 + 18, y), k, font=fk, fill=MUTED)
        d.text((x0 + 100, y), v.strip(), font=fv, fill="white")
        y += 32
    y += 6
    d.line([(x0 + 18, y), (x1 - 18, y)], fill=(90, 102, 124), width=1)
    y += 12
    d.text((x0 + 18, y), "분석", font=fk, fill=MUTED)
    y += 32
    fb = font(21)
    lines = wrap(d, row["r_text"].strip(), fb, x1 - x0 - 36)
    for line in lines:
        d.text((x0 + 18, y), line, font=fb, fill="white")
        y += 31
    if y > REPORT_Y + REPORT_H - 14:
        print(f"  [주의] {sid}: 보고서 문장이 길어서 칸을 넘어요 ({len(lines)}줄). r_text 를 줄여 주세요")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    csv_path, src = Path(sys.argv[1]), Path(sys.argv[2])
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("stimuli")
    for sub in ("g1", "g2", "g3_step1", "g3_step2"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    with open(csv_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        sid = row["scene_id"].strip()
        path = src / row["file"].strip()
        if not path.exists():
            print(f"  [건너뜀] {sid}: 사진 없음 {path}")
            continue
        boxes, roi = parse_boxes(row.get("boxes")), parse_roi(row.get("roi"))
        if not boxes:
            print(f"  [주의] {sid}: boxes 가 비어 있어요 (박스 없이 가운데로 자름)")
        photo = Image.open(path).convert("RGB")
        try:
            zoom = max(float(row.get("zoom") or 1), 1.0)
        except ValueError:
            zoom = 1.0
        ox, oy = crop_origin(photo.width, photo.height, boxes, sid, zoom)
        attn = sid.upper() == "ATTN"

        step1 = canvas(photo, ox, oy, roi)
        if attn:
            add_attn(ImageDraw.Draw(step1))
        step1.save(out / "g3_step1" / f"{sid}.png")

        g1 = canvas(photo, ox, oy, roi)
        d = ImageDraw.Draw(g1)
        add_boxes(d, boxes, ox, oy)
        warning_badge(d, row["label"].strip())
        if attn:
            add_attn(d)
        g1.save(out / "g1" / f"{sid}.png")
        g1.save(out / "g3_step2" / f"{sid}.png")

        g2 = g1.copy()
        add_report(ImageDraw.Draw(g2), row, sid)
        g2.save(out / "g2" / f"{sid}.png")
        print(f"  완료 {sid}: 박스 {len(boxes)}개{', 감시구역' if roi else ''}{f', 확대 {zoom}배' if zoom > 1 else ''}")

    print(f"\n끝! {out.resolve()} 의 g1 / g2 / g3_step1 / g3_step2 폴더를 확인하세요.")


if __name__ == "__main__":
    main()
