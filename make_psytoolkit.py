#!/usr/bin/env python3
"""
stimuli/ 폴더 결과를 PsyToolkit 업로드용으로 정리하는 스크립트.

  python3 make_psytoolkit.py stimuli psytoolkit_upload scenes.csv

결과
  psytoolkit_upload/cctv_g1/  : 장면 20장(jpg) + 버튼·안내 이미지 + cctv_g1.psy (실험 코드)
  psytoolkit_upload/cctv_g2/  : 〃
  psytoolkit_upload/cctv_g3/  : 장면 1단계/2단계 40장 + 버튼·안내 이미지 + cctv_g3.psy
각 폴더의 이미지를 PsyToolkit 실험에 업로드하고, .psy 내용을 코드 창에 붙여 넣으면 된다.
"""
import csv
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 720, 1280
BG = (18, 22, 30)
SCENES = [f"S{i:02d}" for i in range(1, 19)]   # 주의확인(ATTN) 장면은 쓰지 않음
ROWS = []

FONTS = [
    "/mnt/c/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgunbd.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
]
FONTS_R = [
    "/mnt/c/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/malgun.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
]


def font(size, bold=False):
    for p in (FONTS if bold else FONTS_R) + FONTS + FONTS_R:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    sys.exit("한글 폰트가 없어요: sudo apt install -y fonts-nanum")


def wrap(d, text, f, width):
    out = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            t = word if not cur else cur + " " + word
            if d.textlength(t, font=f) > width and cur:
                out.append(cur); cur = word
            else:
                cur = t
        out.append(cur)
    return out


def button(path, text, color):
    im = Image.new("RGB", (300, 130), BG)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 299, 129], radius=22, fill=color)
    f = font(44, bold=True)
    tw = d.textlength(text, font=f)
    d.text(((300 - tw) / 2, 34), text, font=f, fill="white")
    im.save(path)


def conf_button(path, n, word):
    im = Image.new("RGB", (124, 150), BG)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 123, 149], radius=16, fill=(52, 64, 86))
    f, fs = font(48, bold=True), font(18)
    d.text(((124 - d.textlength(str(n), font=f)) / 2, 22), str(n), font=f, fill="white")
    if word:
        d.text(((124 - d.textlength(word, font=fs)) / 2, 100), word, font=fs, fill=(190, 200, 215))
    im.save(path)


def text_screen(path, title, body, foot="화면을 눌러 계속하십시오"):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    y = 110
    if title:
        ft = font(40, bold=True)
        for line in wrap(d, title, ft, W - 100):
            d.text(((W - d.textlength(line, font=ft)) / 2, y), line, font=ft, fill="white"); y += 58
        y += 40
    fb = font(29)
    for line in wrap(d, body, fb, W - 110):
        d.text((55, y), line, font=fb, fill=(225, 230, 238)); y += 46
    if foot:
        ff = font(28, bold=True)
        d.text(((W - d.textlength(foot, font=ff)) / 2, H - 110), foot, font=ff, fill=(255, 210, 0))
    im.save(path)


COMMON = ("지능형 CCTV가 이상 상황을 감지했을 때 보내는 알림 화면을 보게 됩니다.\n\n"
          "각 화면을 보고, 싸움·쓰러짐·침입 중 하나가 실제로 일어나고 있다고 판단되면 [신고], 그렇지 않으면 [무시]를 눌러 주십시오. 사람의 나이나 상황의 심각성과 관계없이, 해당 상황이 일어나고 있는지만 판단해 주십시오.\n\n"
          "노란 점선은 출입이 제한된 감시구역입니다. 사람의 발이 구역 안에 있거나 경계를 넘어가는 중이면 침입으로 봅니다.\n\n"
          "시간 제한은 없습니다. 판단한 뒤에는 그 판단에 얼마나 확신하는지 1~5 중에서 선택합니다.")
GROUP_TEXT = {
    "cctv_g1": "화면 위쪽에는 AI가 감지한 이벤트가, 사진에는 감지된 사람이 빨간 상자로 표시됩니다.",
    "cctv_g2": "화면 위쪽에는 AI가 감지한 이벤트가, 사진에는 감지된 사람이 빨간 상자로, 아래쪽에는 생성형 AI의 분석 보고서가 표시됩니다.",
    "cctv_g3": "각 장면은 두 단계로 진행됩니다. 먼저 AI 표시 없이 사진만 보고 판단한 뒤, AI가 감지한 이벤트와 빨간 상자가 표시된 화면을 보고 최종 판단을 합니다.",
}


def ui(folder, exp):
    button(folder / "btn_report.png", "신고", (205, 25, 25))
    button(folder / "btn_ignore.png", "무시", (70, 82, 104))
    for n, w in zip(range(1, 6), ["전혀 아님", "아님", "보통", "확신함", "매우 확신"]):
        conf_button(folder / f"conf{n}.png", n, w)
    im = Image.new("RGB", (W, 300), BG)
    d = ImageDraw.Draw(im)
    f = font(36, bold=True)
    for i, line in enumerate(["방금 판단에", "얼마나 확신하십니까?"]):
        d.text(((W - d.textlength(line, font=f)) / 2, 90 + i * 56), line, font=f, fill="white")
    im.save(folder / "conf_q.png")
    text_screen(folder / "ui_intro.png", "실험 안내", COMMON + "\n\n" + GROUP_TEXT[exp])
    text_screen(folder / "ui_practice.png", "연습", "먼저 연습 장면 1개로 화면 사용법을 익힙니다.\n\n연습 결과는 분석에 포함되지 않습니다.")
    text_screen(folder / "ui_main.png", "본 실험", "이제 본 실험을 시작합니다.\n\n총 18개 장면이 무작위 순서로 나옵니다. 각 장면을 충분히 살펴본 뒤 판단해 주십시오.")
    text_screen(folder / "ui_done.png", "", "실험이 끝났습니다.\n\n화면을 눌러 설문으로 돌아가십시오.", foot="")
    if exp == "cctv_g3":
        text_screen(folder / "ui_step2.png", "", "이제 AI 감지 결과가 표시된 화면을 보고 최종 판단을 해 주십시오.", foot="화면을 눌러 계속하십시오")


# ---------------- PsyToolkit 코드 ----------------
def psy_code(exp):
    g3 = exp == "cctv_g3"
    lines = ["options", "  resolution 720 1280", "  mouse on", "  background color 18 22 30", "", "bitmaps"]
    ui_names = ["btn_report", "btn_ignore", "conf_q", "conf1", "conf2", "conf3", "conf4", "conf5",
                "ui_intro", "ui_practice", "ui_main", "ui_done"] + (["ui_step2"] if g3 else [])
    lines += [f"  {n}" for n in ui_names]
    if g3:
        for s in SCENES + ["PRACTICE"]:
            lines += [f"  {s.lower()}_1 {s}_1.jpg", f"  {s.lower()}_2 {s}_2.jpg"]
    else:
        lines += [f"  {s.lower()} {s}.jpg" for s in SCENES + ["PRACTICE"]]
    lines.append("")

    # table: 장면이름, 정답(1=신고 필요, 0=신고 불필요), 라벨, 주의확인 여부
    # 정답과 라벨은 scenes.csv 에서 읽는다 (truth 가 '정탐' 이면 1, '오탐' 이면 0)
    truth = {r["scene_id"].strip(): (1 if r["truth"].strip().startswith("정탐") else 0) for r in ROWS}
    labels = {r["scene_id"].strip(): r["label"].strip() for r in ROWS}
    lines.append("table scenes")
    for s in SCENES:
        if s == "ATTN":
            lines.append(f'  "ATTN" attn_1 attn_2 9 "{labels["ATTN"]}" 1' if g3 else f'  "ATTN" attn 9 "{labels["ATTN"]}" 1')
        else:
            n = s.lower()
            lines.append(f'  "{s}" {n}_1 {n}_2 {truth[s]} "{labels[s]}" 0' if g3 else
                         f'  "{s}" {n} {truth[s]} "{labels[s]}" 0')
    lines.append("")

    def judge(prefix, img):
        # 장면 + 버튼 2개, 버튼만 누를 수 있음. 왼쪽=신고(1), 오른쪽=무시(2)
        return [
            "  draw off",
            f"    show bitmap {img} 0 0",
            "    show bitmap btn_report -175 530",
            "    show bitmap btn_ignore 175 530",
            "  draw on",
            "  readmouse l 2 3600000 range 2 3",
            f"  set ${prefix}rt RT",
            "  set $mx MOUSE_X",
            f"  set ${prefix}choice 2",
            "  if $mx < 0",
            f"    set ${prefix}choice 1",
            "  fi",
            "  clear screen",
            "  delay 300",
        ]

    conf = [
        "  draw off",
        "    show bitmap conf_q 0 -300",
        "    show bitmap conf1 -276 0",
        "    show bitmap conf2 -138 0",
        "    show bitmap conf3 0 0",
        "    show bitmap conf4 138 0",
        "    show bitmap conf5 276 0",
        "  draw on",
        "  readmouse l 2 3600000 range 2 6",
        "  set $confrt RT",
        "  set $mx MOUSE_X",
        "  set $conf 3",
        "  if $mx < -207",
        "    set $conf 1",
        "  fi",
        "  if $mx >= -207 && $mx < -69",
        "    set $conf 2",
        "  fi",
        "  if $mx > 69 && $mx <= 207",
        "    set $conf 4",
        "  fi",
        "  if $mx > 207",
        "    set $conf 5",
        "  fi",
        "  clear screen",
        "  delay 500",
    ]

    def tap(name):
        return [f"  show bitmap {name} 0 0", "  readmouse l 1 3600000", "  clear screen", "  delay 300"]

    # 연습 과제
    lines.append("task practice_task")
    if g3:
        lines += judge("first", "practice_1") + tap("ui_step2") + judge("", "practice_2")
    else:
        lines += judge("", "practice")
    lines += conf
    lines += ['  save BLOCKNUMBER TRIALCOUNT 0 -1 0 0 ' +
              ("$firstchoice $firstrt " if g3 else "") + "$choice $rt $conf $confrt", ""]

    # 본 과제
    lines += ["task scene", "  table scenes"]
    if g3:
        lines += judge("first", "@2") + tap("ui_step2") + judge("", "@3")
        lines += conf
        lines += ["  save BLOCKNUMBER TRIALCOUNT @1 @4 @5 @6 $firstchoice $firstrt $choice $rt $conf $confrt", ""]
    else:
        lines += judge("", "@2") + conf
        lines += ["  save BLOCKNUMBER TRIALCOUNT @1 @3 @4 @5 $choice $rt $conf $confrt", ""]

    # 안내 화면용 과제
    for n in ["intro", "practice", "main", "done"]:
        lines += [f"task show_{n}"] + tap("ui_" + n) + [""]

    # 블록마다 과제를 하나씩만 넣어 순서를 고정한다 (한 블록에 여러 과제를 넣으면 순서가 무작위로 섞임)
    lines += ["block b1_intro", "  tasklist", "    show_intro 1", "  end", "",
              "block b2_practice_info", "  tasklist", "    show_practice 1", "  end", "",
              "block b3_practice", "  tasklist", "    practice_task 1", "  end", "",
              "block b4_main_info", "  tasklist", "    show_main 1", "  end", "",
              "block b5_trials", "  tasklist", "    scene 18 all_before_repeat", "  end", "",
              "block b6_finish", "  tasklist", "    show_done 1", "  end", "",
              "blockorder", "  b1_intro", "  b2_practice_info", "  b3_practice", "  b4_main_info",
              "  b5_trials", "  b6_finish", ""]
    return "\n".join(lines)


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("stimuli")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("psytoolkit_upload")
    csv_path = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("scenes.csv")
    ROWS.extend(csv.DictReader(open(csv_path, encoding="utf-8-sig")))
    for exp, sub in (("cctv_g1", "g1"), ("cctv_g2", "g2"), ("cctv_g3", None)):
        folder = out / exp
        folder.mkdir(parents=True, exist_ok=True)
        for s in SCENES + ["PRACTICE"]:
            if sub:
                Image.open(src / sub / f"{s}.png").convert("RGB").save(folder / f"{s}.jpg", quality=85)
            else:
                Image.open(src / "g3_step1" / f"{s}.png").convert("RGB").save(folder / f"{s}_1.jpg", quality=85)
                Image.open(src / "g3_step2" / f"{s}.png").convert("RGB").save(folder / f"{s}_2.jpg", quality=85)
        ui(folder, exp)
        (folder / f"{exp}.psy").write_text(psy_code(exp), encoding="utf-8")
        n = len([p for p in folder.iterdir() if p.suffix in (".jpg", ".png")])
        print(f"  {exp}: 이미지 {n}개 + {exp}.psy")
    print(f"\n끝! {out.resolve()} 확인")


if __name__ == "__main__":
    main()
