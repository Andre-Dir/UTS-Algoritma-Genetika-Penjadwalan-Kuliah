"""Ekspor XLSX sederhana (OOXML) memakai modul bawaan Python.

Tidak membutuhkan openpyxl/xlsxwriter; dipakai untuk download hasil di UI.
"""
from __future__ import annotations

import io
import math
import re
import zipfile
from xml.sax.saxutils import escape

SHEET_HEADER_STYLE = 1


def _column(index: int) -> str:
    out = ''
    while index:
        index, remainder = divmod(index - 1, 26)
        out = chr(65 + remainder) + out
    return out


def _safe(value) -> str:
    result = str(value if value is not None else '')
    return ''.join(ch for ch in result if ch in '\t\n\r' or ord(ch) >= 32)


def _sheet_xml(rows: list[list]):
    body = []
    max_columns = max((len(row) for row in rows), default=1)
    for i, row in enumerate(rows, start=1):
        cell_xml = []
        for j, value in enumerate(row, start=1):
            if value is None:
                continue
            position = f'{_column(j)}{i}'
            style = ' s="1"' if i == 1 else (' s="2"' if i % 2 == 0 else '')
            if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
                cell_xml.append(f'<c r="{position}"{style}><v>{value}</v></c>')
            else:
                sanitized = escape(_safe(value), {'"':'&quot;'})
                cell_xml.append(f'<c r="{position}" t="inlineStr"{style}><is><t xml:space="preserve">{sanitized}</t></is></c>')
        body.append(f'<row r="{i}">{"".join(cell_xml)}</row>')
    cols = ''.join(f'<col min="{i}" max="{i}" width="{min(34,max(13,len(_safe(rows[0][i-1]))+4 if rows else 14))}" customWidth="1"/>' for i in range(1, max_columns + 1))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
            f'<cols>{cols}</cols><sheetData>{"".join(body)}</sheetData>'
            '</worksheet>')


def create_xlsx(sheets: dict[str, list[dict] | list[list]]) -> bytes:
    """Terima mapping nama sheet -> list[dict] atau list[list], kembalikan bytes XLSX."""
    normalized = []
    seen = set()
    for title, values in sheets.items():
        title = re.sub(r'[\\/*?:\[\]]', '_', str(title))[:31] or 'Sheet'
        if title in seen:
            raise ValueError(f'Nama sheet ganda: {title}')
        seen.add(title)
        if values and isinstance(values[0], dict):
            columns = list(values[0].keys())
            rows = [columns] + [[r.get(c, '') for c in columns] for r in values]
        else:
            rows = values or [['Keterangan'], ['Tidak ada data']]
        normalized.append((title, rows))
    if not normalized:
        normalized = [('Ringkasan', [['Keterangan'], ['Belum ada data']])]

    contents = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    contents += '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    contents += '<Default Extension="xml" ContentType="application/xml"/>'
    contents += '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    contents += '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
    for i in range(1,len(normalized)+1):
        contents += f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
    contents += '</Types>'
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>')
    workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>')
    for i,(title,_) in enumerate(normalized,1):
        workbook += f'<sheet name="{escape(title)}" sheetId="{i}" r:id="rId{i}"/>'
    workbook += '</sheets></workbook>'
    workbook_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">')
    for i in range(1,len(normalized)+1):
        workbook_rels += f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
    workbook_rels += f'<Relationship Id="rId{len(normalized)+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    workbook_rels += '</Relationships>'
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
              '<fonts count="2"><font><sz val="11"/><name val="Aptos"/><color rgb="FF233047"/></font>'
              '<font><b/><sz val="11"/><name val="Aptos"/><color rgb="FFFFFFFF"/></font></fonts>'
              '<fills count="4"><fill><patternFill patternType="none"/></fill>'
              '<fill><patternFill patternType="gray125"/></fill>'
              '<fill><patternFill patternType="solid"><fgColor rgb="FF192B4B"/><bgColor indexed="64"/></patternFill></fill>'
              '<fill><patternFill patternType="solid"><fgColor rgb="FFF0F5FC"/><bgColor indexed="64"/></patternFill></fill></fills>'
              '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
              '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
              '<cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
              '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>'
              '<xf numFmtId="0" fontId="0" fillId="3" borderId="0" xfId="0" applyFill="1"/></cellXfs>'
              '</styleSheet>')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', contents)
        z.writestr('_rels/.rels', rels)
        z.writestr('xl/workbook.xml', workbook)
        z.writestr('xl/_rels/workbook.xml.rels', workbook_rels)
        z.writestr('xl/styles.xml', styles)
        for i, (_, rows) in enumerate(normalized,1):
            z.writestr(f'xl/worksheets/sheet{i}.xml', _sheet_xml(rows))
    return buffer.getvalue()
