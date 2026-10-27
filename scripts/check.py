"""사이트를 임시 폴더에 빌드하고 배포 전에 볼 것을 검사한다. 표준 라이브러리만 쓴다.

1. 빌드: hugo 경고(WARN)·오류가 없다 (i18n 누락은 값이 빈 문자열인 bandDaysUnit만 허용)
2. 내부 링크: 페이지의 href·src가 빌드 결과 안의 파일과 #앵커를 가리킨다
3. CSP: 실행되는 인라인 <script>가 없다 (Caddy가 script-src 'self'를 건다. JSON-LD 같은 데이터 블록은 괜찮다)
4. 피드·사이트맵: XML로 읽히고, RSS 본문에 소제목 # 링크와 /로 시작하는 주소가 없다
5. i18n: 두 언어의 키가 같다 (영어판에서만 쓰는 koreanOriginal은 예외)

실행: python3 scripts/check.py   (사이트 레포 루트에서. 실패하면 종료 코드 1)
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://unattendant.dev"
ALLOWED_I18N_WARNINGS = {"en|bandDaysUnit"}  # 영어는 단위 없이 숫자만 쓴다
LANG_ONLY_KEYS = {"koreanOriginal"}  # 영어판 글에서 한국어 원문으로 가는 안내


def build(out: Path) -> list[str]:
    # 배포와 같은 --minify로 빌드한다 (속성 따옴표가 빠지므로 아래 정규식은 따옴표를 선택으로 본다)
    result = subprocess.run(["hugo", "--minify", "--source", str(ROOT), "--destination", str(out), "--printI18nWarnings"],
                            capture_output=True, text=True)
    problems = []
    if result.returncode != 0:
        problems.append("빌드 실패: " + (result.stderr or result.stdout).strip()[-800:])
    for line in (result.stdout + result.stderr).splitlines():
        if "WARN" in line or "ERROR" in line:
            m = re.search(r"MISSING_TRANSLATION\|(\w+)\|(\w+)", line)
            if m and f"{m.group(1)}|{m.group(2)}" in ALLOWED_I18N_WARNINGS:
                continue
            problems.append(f"빌드 경고: {line.strip()}")
    return problems


def links(public: Path) -> list[str]:
    problems = []
    ids_cache: dict[Path, set[str]] = {}

    def ids_of(page: Path) -> set[str]:
        if page not in ids_cache:
            ids_cache[page] = set(re.findall(r'\sid="?([^" >]+)', page.read_text(encoding="utf-8", errors="replace")))
        return ids_cache[page]

    for page in sorted(public.rglob("*.html")):
        html = page.read_text(encoding="utf-8", errors="replace")
        for url in re.findall(r'(?:href|src)="?([^" >]+)', html):
            url = url.replace(BASE, "")
            if url.startswith(("http:", "https:", "mailto:", "data:", "//")):
                continue
            path, _, frag = url.partition("#")
            target = page
            if path:  # Hugo는 같은 글의 #앵커도 /posts/<슬러그>/#앵커로 바꿔 쓴다
                target = public / urllib.parse.unquote(path).lstrip("/")
                if path.endswith("/"):
                    target /= "index.html"
                if not target.exists():
                    problems.append(f"없는 파일: {page.relative_to(public)} → {url}")
                    continue
            if frag and target.suffix == ".html" and not {frag, urllib.parse.unquote(frag)} & ids_of(target):
                problems.append(f"없는 앵커: {page.relative_to(public)} → {url}")
    return problems


def inline_scripts(public: Path) -> list[str]:
    problems = []
    for page in sorted(public.rglob("*.html")):
        for attrs in re.findall(r"<script([^>]*)>", page.read_text(encoding="utf-8", errors="replace")):
            if "src=" in attrs or "application/ld+json" in attrs or "application/json" in attrs:
                continue
            problems.append(f"인라인 스크립트(CSP에 막힌다): {page.relative_to(public)}")
    return problems


def feeds(public: Path) -> list[str]:
    problems = []
    content = "{http://purl.org/rss/1.0/modules/content/}encoded"
    for path in sorted(public.rglob("*.xml")):
        try:
            tree = ET.parse(path)
        except ET.ParseError as e:
            problems.append(f"XML로 읽히지 않는다: {path.relative_to(public)} ({e})")
            continue
        for item in tree.getroot().iter("item"):
            body = item.findtext(content) or ""
            if "h-anchor" in body:
                problems.append(f"RSS 본문에 소제목 # 링크: {path.relative_to(public)} {item.findtext('title')}")
            if re.search(r'(?:href|src)="/', body):
                problems.append(f"RSS 본문에 상대 주소: {path.relative_to(public)} {item.findtext('title')}")
    return problems


def i18n() -> list[str]:
    keys = {lang: set(re.findall(r"^(\w+)\s*=", (ROOT / f"i18n/{lang}.toml").read_text(encoding="utf-8"), re.M))
            for lang in ("ko", "en")}
    problems = []
    for a, b in (("ko", "en"), ("en", "ko")):
        for key in sorted(keys[a] - keys[b] - LANG_ONLY_KEYS):
            problems.append(f"i18n: {a}에만 있는 키 {key}")
    return problems


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="site-check-") as tmp:  # /tmp는 RAM이다
        public = Path(tmp) / "public"
        problems = build(public)
        if public.exists():
            problems += links(public) + inline_scripts(public) + feeds(public)
        problems += i18n()
        pages = len(list(public.rglob("*.html"))) if public.exists() else 0
    for p in problems:
        print(p)
    print(f"{'실패' if problems else '통과'}: 페이지 {pages}개, 문제 {len(problems)}개")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
