import json
import os
import sys

if not sys.flags.utf8_mode and os.environ.get("PYTHONUTF8") != "1":
    import subprocess

    raise SystemExit(
        subprocess.run([sys.executable, "-X", "utf8", sys.argv[0], *sys.argv[1:]]).returncode
    )

os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")  # avoid torch.compile retry loop without a C++ compiler

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableStructureOptions
from docling.document_converter import DocumentConverter, PdfFormatOption


def _build_converter() -> DocumentConverter:
    options = PdfPipelineOptions()
    options.do_ocr = False  #不做OCR
    options.do_table_structure = True   #偵測表格結構
    options.table_structure_options = TableStructureOptions(do_cell_matching=True)
    return DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})


def classify_pdf(pdf_path: str) -> list[dict]:
    doc = _build_converter().convert(pdf_path).document
    total_pages = len(doc.pages)

    has_table = {p: False for p in range(1, total_pages + 1)}
    has_text = {p: False for p in range(1, total_pages + 1)}
    has_image = {p: False for p in range(1, total_pages + 1)}
    table_confidences = {p: [] for p in range(1, total_pages + 1)}

    for table in doc.tables:
        if not table.prov:
            continue
        page_no = table.prov[0].page_no
        has_table[page_no] = True
        confidence = getattr(table, "confidence", None)
        if confidence is not None:
            table_confidences[page_no].append(confidence)

    for text_item in doc.texts:
        if text_item.prov:
            has_text[text_item.prov[0].page_no] = True

    for picture in doc.pictures:
        if picture.prov:
            has_image[picture.prov[0].page_no] = True

    pages = []
    for page_no in range(1, total_pages + 1):
        elements = [
            name
            for name, present in (
                ("table", has_table[page_no]),
                ("text", has_text[page_no]),
                ("image", has_image[page_no]),
            )
            if present
        ]
        confs = table_confidences[page_no]
        pages.append(
            {
                "page_number": page_no,
                "type": "+".join(elements) if elements else "none",
                "table_confidence": sum(confs) / len(confs) if confs else None,
            }
        )

    return pages


if __name__ == "__main__":
    print(json.dumps(classify_pdf(sys.argv[1]), ensure_ascii=False, indent=2))
