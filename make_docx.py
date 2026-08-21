"""
PROJECT_PLAN.md, DESIGN_LOG.md 의 내용을 그대로 옮겨 PROJECT_DESIGN.docx 를 만든다.
새 내용을 작성하지 않고, 두 파일의 절과 표를 찾아 그대로 옮기기만 한다.
"""
import re
import sys
from pathlib import Path

from docx import Document

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

PROJECT_TITLE = "여기에 제목을 적으세요"

PLAN_PATH = Path("PROJECT_PLAN.md")
LOG_PATH = Path("DESIGN_LOG.md")
OUT_PATH = Path("PROJECT_DESIGN.docx")


def read_text(path):
    return path.read_text(encoding="utf-8")


def split_h2_sections(text):
    """'## ' 로 시작하는 절 단위로 (제목, 본문줄들) 리스트를 반환한다."""
    sections = []
    heading = None
    body = []
    for line in text.splitlines():
        if line.startswith("## "):
            if heading is not None:
                sections.append((heading, body))
            heading = line[3:].strip()
            body = []
        elif heading is not None:
            body.append(line)
    if heading is not None:
        sections.append((heading, body))
    return sections


def find_section(sections, heading_prefix):
    for heading, body in sections:
        if heading.startswith(heading_prefix):
            return heading, body
    raise ValueError(f"'{heading_prefix}' 로 시작하는 절을 찾지 못했습니다.")


def parse_md_table(body_lines):
    """마크다운 표 줄들을 2차원 리스트(행 x 셀)로 바꾼다. 구분선(---)은 제외한다."""
    rows = []
    for line in body_lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", c) for c in cells):
            continue
        rows.append(cells)
    return rows


def join_prose(body_lines):
    """표가 아닌 본문 줄들을 한 문단으로 이어붙인다 (마크다운 줄바꿈 제거)."""
    parts = [line.strip() for line in body_lines if line.strip()]
    return " ".join(parts)


def add_table(doc, rows, style="Light Grid Accent 1"):
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = style
    for r, row in enumerate(rows):
        for c, cell_text in enumerate(row):
            table.cell(r, c).text = cell_text
    return table


def add_list_from_table(doc, rows):
    """표의 헤더 행을 제외한 나머지 행을 '항목 — 이유' 글머리 기호 목록으로 추가한다."""
    for row in rows[1:]:
        doc.add_paragraph(" — ".join(row), style="List Bullet")


def build():
    plan_sections = split_h2_sections(read_text(PLAN_PATH))
    log_sections = split_h2_sections(read_text(LOG_PATH))

    doc = Document()

    # 1. 제목
    doc.add_heading(PROJECT_TITLE, level=0)

    # 2. 프로젝트 주제 (한 줄 소개 — 누가 어떤 상황에서 쓰는지 포함)
    doc.add_heading("프로젝트 주제", level=1)
    _, intro_body = find_section(plan_sections, "1.")
    doc.add_paragraph(join_prose(intro_body))

    # 3. 설계 과정 — DESIGN_LOG.md 의 네 절을 그대로 옮긴다
    doc.add_heading("설계 과정", level=1)
    for heading, body in log_sections:
        doc.add_heading(heading, level=2)
        for line in body:
            text = line.strip()
            if not text:
                continue
            if text.startswith("- "):
                doc.add_paragraph(text[2:], style="List Bullet")
            else:
                doc.add_paragraph(text)

    # 4. 아키텍처 — 여섯 줄을 표로
    doc.add_heading("아키텍처", level=1)
    _, arch_body = find_section(plan_sections, "7.")
    add_table(doc, parse_md_table(arch_body))

    # 5. 완료 조건 — 조건과 판정 방법을 표로
    doc.add_heading("완료 조건", level=1)
    _, done_body = find_section(plan_sections, "3.")
    add_table(doc, parse_md_table(done_body))

    # 6. 범위 밖 — 뺀 것과 이유를 목록으로
    doc.add_heading("범위 밖", level=1)
    _, scope_body = find_section(plan_sections, "4.")
    add_list_from_table(doc, parse_md_table(scope_body))

    # 7. 위험과 대안 — 두 항목을 목록으로
    doc.add_heading("위험과 대안", level=1)
    _, risk_body = find_section(plan_sections, "8.")
    add_list_from_table(doc, parse_md_table(risk_body))

    doc.save(OUT_PATH)
    print(f"저장 완료: {OUT_PATH}")


if __name__ == "__main__":
    build()
