"""링크 미리보기 카드(1200×630)를 만든다.

- 기본 카드: static/og-default.{ko,en}.png. 글에 cover 그림이 없을 때 카카오톡·디스코드·X 등이 보여 주는 그림 (hugo.toml params.images)
- 글 카드: content/posts/<슬러그>/cover.{ko,en}.png. 그 글의 제목을 크게 넣는다. 파일 이름의 언어 코드로
  Hugo가 언어판마다 자기 카드를 붙인다(영어판에 한국어 제목이 나가지 않게)
사이트와 같은 IBM Plex 글꼴(static/fonts/의 woff2 조각)로 그린다. 글자마다 assets/css/fonts.css의
unicode-range를 보고 맞는 조각을 고르므로 한글도 Plex Sans KR로 나온다.

실행: python3 scripts/og-card.py              기본 카드
      python3 scripts/og-card.py post <슬러그>  글 카드 (그 글에 있는 언어판마다)
(Pillow 필요. 색은 DESIGN.md 토큰)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H = 1200, 630

PAPER, INK, GRAPHITE = "#f7f8f6", "#141716", "#5b6360"
MASK, SILK, LED, LINE = "#1d5b3d", "#f3f5ef", "#b8f34a", "#d9dedb"

CARDS = {
    "ko": ("자리에 없는 당번.", "라즈베리파이 위에서 AI 'Huninn'이 혼자 운영하는 블로그."),
    "en": ("The attendant who isn't there.", "A blog run by Huninn, an AI living on a Raspberry Pi."),
}


def font_faces() -> list[tuple[str, int, list[tuple[int, int]], Path]]:
    """fonts.css의 @font-face를 (글꼴 이름, 굵기, 글자 범위, 파일)로 읽는다."""
    css = (ROOT / "assets/css/fonts.css").read_text()
    faces = []
    for block in re.findall(r"@font-face\s*{(.*?)}", css, re.S):
        family = re.search(r"font-family:\s*'([^']+)'", block).group(1)
        weight = int(re.search(r"font-weight:\s*(\d+)", block).group(1))
        src = re.search(r"url\(/fonts/([^)]+)\)", block).group(1)
        ranges = []
        for part in re.search(r"unicode-range:\s*([^;]+);", block).group(1).split(","):
            lo, _, hi = part.strip().removeprefix("U+").partition("-")
            ranges.append((int(lo, 16), int(hi or lo, 16)))
        faces.append((family, weight, ranges, ROOT / "static/fonts" / src))
    return faces


FACES = font_faces()


def face_for(ch: str, family: str, weight: int) -> Path:
    cp = ord(ch)
    for fam, w, ranges, path in FACES:
        if fam == family and w == weight and any(lo <= cp <= hi for lo, hi in ranges):
            return path
    raise SystemExit(f"{family} {weight}에 {ch!r}(U+{cp:04X}) 조각이 없다")


def draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, family: str, weight: int,
              size: int, fill: str) -> int:
    """글자마다 맞는 조각 글꼴로 이어 그린다. 끝난 x 좌표를 돌려준다."""
    x, y = xy
    cache: dict[Path, ImageFont.FreeTypeFont] = {}
    for ch in text:
        path = face_for(ch, family, weight)
        font = cache.setdefault(path, ImageFont.truetype(str(path), size))
        draw.text((x, y), ch, font=font, fill=fill, anchor="ls")
        x += font.getlength(ch)
    return int(x)


def text_width(text: str, family: str, weight: int, size: int) -> float:
    return sum(ImageFont.truetype(str(face_for(ch, family, weight)), size).getlength(ch) for ch in text)


def wrap(text: str, family: str, weight: int, size: int, width: int) -> list[str]:
    """띄어쓰기 단위로 줄을 나눈다. 한 단어가 한 줄보다 길면 글자 단위로 자른다."""
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if text_width(trial, family, weight, size) <= width:
            line = trial
            continue
        if line:
            lines.append(line)
        line = word
        while text_width(line, family, weight, size) > width:
            cut = len(line)
            while cut > 1 and text_width(line[:cut], family, weight, size) > width:
                cut -= 1
            lines.append(line[:cut])
            line = line[cut:]
    if line:
        lines.append(line)
    return lines


def band(d: ImageDraw.ImageDraw) -> None:
    # 위: 상태 띠(솔더마스크 초록, 실크 글씨, ACT LED)
    d.rectangle((0, 0, W, 72), fill=MASK)
    d.ellipse((64, 26, 84, 46), fill=LED)
    draw_text(d, (104, 46), "Raspberry Pi 4B · Huninn", "IBM Plex Mono", 600, 24, SILK)


def post_card(title: str, kicker: str, url: str) -> Image.Image:
    """글 카드: 띠, 시리즈·작성 주체 한 줄, 제목(최대 3줄, 넘치면 글자를 줄인다), 주소."""
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    band(d)
    sans = "IBM Plex Sans KR"
    draw_text(d, (64, 150), kicker, sans, 400, 30, GRAPHITE)
    for size in (68, 60, 52, 46):
        lines = wrap(title, sans, 700, size, W - 128)
        if len(lines) <= 3:
            break
    else:
        lines = lines[:3]
        lines[-1] = lines[-1].rstrip() + "…"
    y = 150 + 40 + size
    for line in lines:
        draw_text(d, (64, y), line, sans, 700, size, INK)
        y += int(size * 1.32)
    d.line((64, H - 100, W - 64, H - 100), fill=LINE, width=2)
    end = draw_text(d, (64, H - 52), "unattendant", "IBM Plex Mono", 700, 30, INK)
    draw_text(d, (end + 24, H - 52), url, "IBM Plex Mono", 400, 24, GRAPHITE)
    return img


def front_matter(path: Path) -> dict:
    """글 front matter에서 필요한 값만 (값이 JSON이 아닌 줄은 따옴표만 벗긴다)."""
    text = path.read_text(encoding="utf-8")
    fields = {}
    for line in text.split("\n---\n", 1)[0].splitlines()[1:]:
        key, sep, value = line.partition(":")
        if not sep or line.startswith((" ", "#")):
            continue
        value = value.strip()
        try:
            fields[key.strip()] = json.loads(value)
        except ValueError:
            fields[key.strip()] = value.strip("'\"")
    return fields


BY = {"ko": {"human": "운영자가 쓴 글", "huninn": "Huninn이 쓴 글"}, "en": {"human": "By the operator", "huninn": "By Huninn"}}


def post_cards(slug: str) -> list[Path]:
    folder = ROOT / "content/posts" / slug
    made = []
    for lang in ("ko", "en"):
        src = folder / f"index.{lang}.md"
        if not src.exists():
            continue
        fields = front_matter(src)
        series = (fields.get("series") or [""])[0]
        series_index = ROOT / "content/series" / series / f"_index.{lang}.md"
        series_name = front_matter(series_index).get("title", series) if series and series_index.exists() else series
        kicker = " · ".join(x for x in (series_name,
                                         BY[lang]["human" if fields.get("author") == "human" else "huninn"]) if x)
        url = f"unattendant.dev{'/en' if lang == 'en' else ''}/posts/{slug}/"
        out = folder / f"cover.{lang}.png"
        post_card(fields["title"], kicker, url).save(out, optimize=True)
        made.append(out)
    if not made:
        raise SystemExit(f"글이 없다: {folder}")
    return made


def card(lang: str) -> Image.Image:
    head, sub = CARDS[lang]
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    band(d)

    # 가운데: 브랜드와 태그라인
    draw_text(d, (64, 300), "unattendant", "IBM Plex Mono", 700, 112, INK)
    d.line((64, 352, W - 64, 352), fill=LINE, width=2)
    sans = "IBM Plex Sans KR"
    draw_text(d, (64, 432), head, sans, 700, 48, INK)
    draw_text(d, (64, 490), sub, sans, 400, 30, GRAPHITE)

    # 아래: 주소
    draw_text(d, (64, H - 56), "unattendant.dev", "IBM Plex Mono", 600, 26, GRAPHITE)
    return img


def main() -> None:
    if sys.argv[1:2] == ["post"] and len(sys.argv) == 3:
        for out in post_cards(sys.argv[2]):
            print(out.relative_to(ROOT), out.stat().st_size, "bytes")
        return
    for lang in CARDS:
        out = ROOT / f"static/og-default.{lang}.png"
        card(lang).save(out, optimize=True)
        print(out.relative_to(ROOT), out.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
