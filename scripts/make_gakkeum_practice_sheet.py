from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "output" / "pdf"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PNG_PATH = OUT_DIR / "crush_gakkeum_easy_practice.png"
PDF_PATH = OUT_DIR / "crush_gakkeum_easy_practice.pdf"

W, H = 2480, 3508  # A4 at 300 dpi
M = 150


def font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\malgunbd.ttf" if bold else r"C:\Windows\Fonts\malgun.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


F_TITLE = font(76, True)
F_SUB = font(34)
F_HEAD = font(42, True)
F_TEXT = font(31)
F_SMALL = font(25)
F_CHORD = font(44, True)
F_NOTE = font(28)


def text(draw, xy, value, fill="#111111", fnt=F_TEXT, anchor=None):
    draw.text(xy, value, font=fnt, fill=fill, anchor=anchor)


def rounded(draw, box, radius=18, fill="#ffffff", outline="#222222", width=3):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def staff(draw, x, y, width, measures):
    gap = 22
    for line in range(5):
        yy = y + line * gap
        draw.line((x, yy, x + width, yy), fill="#222222", width=3)

    bar_w = width / measures
    for i in range(measures + 1):
        bx = int(x + i * bar_w)
        draw.line((bx, y, bx, y + gap * 4), fill="#222222", width=4 if i in (0, measures) else 2)
    return bar_w, gap


def draw_note(draw, cx, cy, stem_up=True, fill="#111111"):
    draw.ellipse((cx - 14, cy - 10, cx + 14, cy + 10), fill=fill)
    if stem_up:
        draw.line((cx + 12, cy, cx + 12, cy - 88), fill=fill, width=5)
    else:
        draw.line((cx - 12, cy, cx - 12, cy + 88), fill=fill, width=5)


def draw_chord_grid(draw, x, y, chords, title):
    text(draw, (x, y), title, fnt=F_HEAD)
    y += 70
    box_w, box_h = 260, 130
    for i, chord in enumerate(chords):
        col = i % 4
        row = i // 4
        bx = x + col * (box_w + 24)
        by = y + row * (box_h + 24)
        rounded(draw, (bx, by, bx + box_w, by + box_h), fill="#fbfbf8", outline="#333333")
        text(draw, (bx + box_w / 2, by + 48), chord, fnt=F_CHORD, anchor="mm")
        text(draw, (bx + box_w / 2, by + 93), f"{i + 1}마디", fnt=F_SMALL, fill="#555555", anchor="mm")
    return y + 2 * (box_h + 24) + 20


def draw_pattern(draw, x, y):
    text(draw, (x, y), "반주 패턴", fnt=F_HEAD)
    y += 74
    text(draw, (x, y), "왼손: 1도 - 5도 - 8도 / 오른손: 코드톤을 부드럽게 펼치기", fnt=F_TEXT)
    y += 70
    staff_w = W - 2 * M
    bar_w, gap = staff(draw, x, y + 40, staff_w, 4)
    chords = ["Cmaj7", "Am7", "Fmaj7", "G7"]
    for i, chord in enumerate(chords):
        cx = x + i * bar_w + 25
        text(draw, (cx + 28, y), chord, fnt=F_NOTE, fill="#333333")
        base_y = y + 40 + gap * 4
        for j, offset in enumerate([0.18, 0.38, 0.58, 0.78]):
            nx = int(x + i * bar_w + bar_w * offset)
            draw_note(draw, nx, int(base_y - (j % 3) * 22), stem_up=True)
    y += 200
    text(draw, (x, y), "카운트: 1 & 2 & 3 & 4 &    느낌: 너무 세게 누르지 말고, 뒤 박자를 살짝 늦게", fnt=F_SMALL, fill="#333333")
    return y + 70


def draw_practice_steps(draw, x, y):
    text(draw, (x, y), "연습 순서", fnt=F_HEAD)
    y += 72
    steps = [
        "1. 메트로놈 68 bpm에서 왼손 루트음만 8마디 반복",
        "2. 왼손 1-5-8 패턴을 넣고 페달은 마디마다 갈기",
        "3. 오른손은 코드 전체를 누르지 말고 위 두 음만 가볍게",
        "4. 익숙해지면 76-82 bpm까지 올리기",
    ]
    for step in steps:
        text(draw, (x, y), step, fnt=F_TEXT)
        y += 50
    return y


def main():
    img = Image.new("RGB", (W, H), "#fffdf7")
    draw = ImageDraw.Draw(img)

    text(draw, (M, 130), "크러쉬 - 가끔", fnt=F_TITLE)
    text(draw, (M, 215), "개인 연습용 쉬운 피아노 코드 반주 악보 - C key", fnt=F_SUB, fill="#333333")
    text(draw, (W - M, 130), "4/4", fnt=F_HEAD, anchor="ra")
    text(draw, (W - M, 190), "Slow R&B Ballad", fnt=F_SMALL, fill="#555555", anchor="ra")
    draw.line((M, 285, W - M, 285), fill="#222222", width=4)

    y = 345
    text(draw, (M, y), "이 악보는 원곡 전체 멜로디 채보가 아니라, 치기 쉽게 만든 코드 중심 연습 버전입니다.", fnt=F_SMALL, fill="#555555")
    y += 70

    verse = ["Cmaj7", "Bm7b5  E7", "Am7", "Gm7  C7", "Fmaj7", "Em7  A7", "Dm7", "G7"]
    chorus = ["Cmaj7", "E7", "Am7", "Gm7  C7", "Fmaj7", "Em7  A7", "Dm7  G7", "Cmaj7"]
    y = draw_chord_grid(draw, M, y, verse, "Verse 루프")
    y += 45
    y = draw_chord_grid(draw, M, y, chorus, "Chorus 루프")
    y += 65
    y = draw_pattern(draw, M, y)
    y += 60
    y = draw_practice_steps(draw, M, y)

    rounded(draw, (M, H - 430, W - M, H - 170), radius=22, fill="#f5f1e8", outline="#d2c7b5", width=3)
    text(draw, (M + 45, H - 385), "건반 보이싱 예시", fnt=F_HEAD)
    examples = [
        "Cmaj7: 왼손 C-G-C / 오른손 E-G-B",
        "Am7: 왼손 A-E-A / 오른손 C-E-G",
        "Fmaj7: 왼손 F-C-F / 오른손 A-C-E",
        "G7: 왼손 G-D-G / 오른손 B-D-F",
    ]
    yy = H - 320
    for ex in examples:
        text(draw, (M + 45, yy), ex, fnt=F_TEXT)
        yy += 48

    img.save(PNG_PATH)
    img.save(PDF_PATH, "PDF", resolution=300.0)
    print(PDF_PATH)
    print(PNG_PATH)


if __name__ == "__main__":
    main()
