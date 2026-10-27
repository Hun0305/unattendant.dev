"""파비콘을 만든다: static/favicon.svg, favicon.ico(16·32·48), apple-touch-icon.png(180).

상태 띠처럼 솔더마스크 초록 바탕에 실크색 u, 오른쪽 위에 ACT LED. 글꼴 없이 도형만 써서
SVG와 PNG가 같은 모양이 된다. 색은 assets/css/main.css의 --mask, --silk, --led와 같다.

실행: python3 scripts/favicon.py  (Pillow 필요. 사이트 레포 루트에서)
"""
from pathlib import Path

from PIL import Image, ImageDraw

MASK, SILK, LED = "#1d5b3d", "#f3f5ef", "#b8f34a"
# 32칸 격자 기준 도형
RADIUS = 6                  # 바탕 모서리
U_LEFT, U_RIGHT, U_TOP, U_BEND = 10, 22, 12, 19   # u의 두 기둥과 꺾이는 높이(반원 중심)
STROKE = 3.6
LED_C, LED_R = (25, 7), 2.6

STATIC = Path(__file__).resolve().parent.parent / "static"


def svg() -> str:
    r = (U_RIGHT - U_LEFT) / 2
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        f'<rect width="32" height="32" rx="{RADIUS}" fill="{MASK}"/>'
        f'<path d="M{U_LEFT} {U_TOP}V{U_BEND}a{r:g} {r:g} 0 0 0 {2 * r:g} 0V{U_TOP}" fill="none" '
        f'stroke="{SILK}" stroke-width="{STROKE}"/>'
        f'<circle cx="{LED_C[0]}" cy="{LED_C[1]}" r="{LED_R}" fill="{LED}"/>'
        "</svg>\n"
    )


def png(size: int) -> Image.Image:
    k = size * 8 / 32  # 8배로 그려 줄여서 가장자리를 부드럽게 한다
    big = Image.new("RGBA", (size * 8, size * 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.rounded_rectangle((0, 0, 32 * k - 1, 32 * k - 1), radius=RADIUS * k, fill=MASK)
    half, r = STROKE / 2, (U_RIGHT - U_LEFT) / 2
    cx = (U_LEFT + U_RIGHT) / 2
    for x in (U_LEFT, U_RIGHT):
        d.rectangle(((x - half) * k, U_TOP * k, (x + half) * k, U_BEND * k), fill=SILK)
    d.arc(((cx - r - half) * k, (U_BEND - r - half) * k, (cx + r + half) * k, (U_BEND + r + half) * k),
          0, 180, fill=SILK, width=round(STROKE * k))
    d.ellipse(((LED_C[0] - LED_R) * k, (LED_C[1] - LED_R) * k, (LED_C[0] + LED_R) * k, (LED_C[1] + LED_R) * k),
              fill=LED)
    return big.resize((size, size), Image.LANCZOS)


def main() -> None:
    (STATIC / "favicon.svg").write_text(svg(), encoding="utf-8")
    png(48).save(STATIC / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    # 홈 화면 아이콘은 iOS가 모서리를 깎으므로 바탕을 꽉 채운다
    touch = Image.new("RGB", (180, 180), MASK)
    touch.paste(png(180), (0, 0), png(180))
    touch.save(STATIC / "apple-touch-icon.png", optimize=True)
    for name in ("favicon.svg", "favicon.ico", "apple-touch-icon.png"):
        print(f"{name}: {(STATIC / name).stat().st_size} bytes")


if __name__ == "__main__":
    main()
