#!/usr/bin/env python3
"""
05_export_excel.py
==================
Zero-Dependency OpenXML (.xlsx) Exporter (Guideline Section 10)
MT2013 Course Project - Class CC09 (2-Factor Experimental Design)

Generates `data/MT2013_CC09_Data.xlsx` with raw and processed observations,
group summaries, ANOVA, pairwise comparisons, and the sensitivity analysis.
"""

import csv
import os
import zipfile
from xml.sax.saxutils import escape


def col_letter(idx: int) -> str:
    result = ""
    idx += 1
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        result = chr(65 + rem) + result
    return result


def is_number(val: str) -> bool:
    if val.startswith("'"):
        return False
    try:
        float(val)
        return True
    except ValueError:
        return False


def build_sheet_xml(rows: list[list[str]]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        "  <sheetData>",
    ]
    for r_idx, row in enumerate(rows, start=1):
        lines.append(f'    <row r="{r_idx}">')
        for c_idx, val in enumerate(row):
            cell_ref = f"{col_letter(c_idx)}{r_idx}"
            val_str = str(val)
            if r_idx > 1 and is_number(val_str):
                lines.append(f'      <c r="{cell_ref}"><v>{val_str}</v></c>')
            else:
                clean_str = escape(val_str.lstrip("'"))
                lines.append(
                    f'      <c r="{cell_ref}" t="inlineStr"><is><t>{clean_str}</t></is></c>'
                )
        lines.append("    </row>")
    lines.append("  </sheetData>")
    lines.append("</worksheet>")
    return "\n".join(lines)


def read_csv_rows(filepath: str) -> list[list[str]]:
    with open(filepath, mode="r", encoding="utf-8") as f:
        return list(csv.reader(f))


def create_xlsx(output_path: str, sheets: list[tuple[str, list[list[str]]]]) -> None:
    content_types = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '  <Default Extension="xml" ContentType="application/xml"/>',
        '  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
    ]
    for i in range(1, len(sheets) + 1):
        content_types.append(
            f'  <Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    content_types.append("</Types>")

    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

    wb_lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
        "  <sheets>",
    ]
    wb_rels = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
    ]
    for i, (name, _) in enumerate(sheets, start=1):
        wb_lines.append(f'    <sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>')
        wb_rels.append(
            f'  <Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
        )
    wb_lines.append("  </sheets>")
    wb_lines.append("</workbook>")
    wb_rels.append("</Relationships>")

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", "\n".join(content_types))
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", "\n".join(wb_lines))
        zf.writestr("xl/_rels/workbook.xml.rels", "\n".join(wb_rels))
        for i, (_, rows) in enumerate(sheets, start=1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", build_sheet_xml(rows))


def main() -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    res_dir = os.path.join(base_dir, "results")

    sheets = [
        ("Summary_All_Groups", read_csv_rows(os.path.join(res_dir, "summary_all_groups.csv"))),
        ("Axis1_Length_Analysis", read_csv_rows(os.path.join(res_dir, "table_axis1_length_stats.csv"))),
        ("Axis2_Charset_Stats", read_csv_rows(os.path.join(res_dir, "table_axis2_charset_stats.csv"))),
        ("Axis2_Charset_ANOVA", read_csv_rows(os.path.join(res_dir, "table_axis2_anova.csv"))),
        ("Axis2_Pairwise", read_csv_rows(os.path.join(res_dir, "table_axis2_pairwise.csv"))),
        ("Sensitivity", read_csv_rows(os.path.join(res_dir, "table_sensitivity.csv"))),
        ("Security_TradeOff", read_csv_rows(os.path.join(res_dir, "table_tradeoff_length_vs_complexity.csv"))),
        ("Processed_Data", read_csv_rows(os.path.join(data_dir, "processed_experiment_data.csv"))),
        ("Raw_Data", read_csv_rows(os.path.join(data_dir, "raw_experiment_data.csv"))),
    ]

    out_xlsx = os.path.join(data_dir, "MT2013_CC09_Data.xlsx")
    create_xlsx(out_xlsx, sheets)
    print(f"Exported {len(sheets)}-sheet workbook -> {out_xlsx}")


if __name__ == "__main__":
    main()
