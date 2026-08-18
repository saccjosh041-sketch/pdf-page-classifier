import json
import os
import sys

if not sys.flags.utf8_mode and os.environ.get("PYTHONUTF8") != "1":
    import subprocess

    raise SystemExit(
        subprocess.run([sys.executable, "-X", "utf8", sys.argv[0], *sys.argv[1:]]).returncode
    )

from paddleocr import PPStructureV3

IMAGE_LABELS = {"image", "chart", "seal"}  # PP-DocLayout_plus-L classes that are non-table visuals


def _build_pipeline() -> PPStructureV3:
    return PPStructureV3(
        device="cpu",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        use_formula_recognition=False,
        use_chart_recognition=False,
        use_table_recognition=True,
    )


def classify_pdf(pdf_path: str) -> list[dict]:
    pipeline = _build_pipeline()
    pages = []

    for page_number, res in enumerate(pipeline.predict(pdf_path), start=1):
        boxes = res["layout_det_res"]["boxes"]
        table_boxes = [b for b in boxes if b.get("label") == "table"]
        image_boxes = [b for b in boxes if b.get("label") in IMAGE_LABELS]
        text_boxes = [
            b for b in boxes if b.get("label") != "table" and b.get("label") not in IMAGE_LABELS
        ]

        elements = [
            name
            for name, present in (
                ("table", bool(table_boxes)),
                ("text", bool(text_boxes)),
                ("image", bool(image_boxes)),
            )
            if present
        ]

        scores = [b["score"] for b in table_boxes if b.get("score") is not None]
        pages.append(
            {
                "page_number": page_number,
                "type": "+".join(elements) if elements else "none",
                "table_confidence": sum(scores) / len(scores) if scores else None,
            }
        )

    return pages


if __name__ == "__main__":
    print(json.dumps(classify_pdf(sys.argv[1]), ensure_ascii=False, indent=2))
