import numpy as np
import pytesseract

from app.pipeline.ocr_engine import OCREngine


def _fake_tesseract_data():
    return {
        "text": ["HELLO", "WORLD"],
        "conf": ["85", "90"],
        "left": [10, 40],
        "top": [15, 20],
        "width": [20, 30],
        "height": [10, 10],
        "level": [5, 5],
        "block_num": [1, 1],
        "line_num": [1, 1],
        "word_num": [1, 2],
    }


def test_extract_handles_grayscale_and_color_arrays(monkeypatch):
    engine = OCREngine()

    def _fake_image_to_data(_img, config, output_type):
        assert output_type == pytesseract.Output.DICT
        return _fake_tesseract_data()

    monkeypatch.setattr(pytesseract, "image_to_data", _fake_image_to_data)

    gray = np.zeros((64, 64), dtype=np.uint8)
    color = np.zeros((64, 64, 3), dtype=np.uint8)

    gray_text, gray_blocks, gray_conf = engine.extract(gray)
    color_text, color_blocks, color_conf = engine.extract(color)

    assert gray_text == "HELLO WORLD"
    assert color_text == "HELLO WORLD"
    assert len(gray_blocks) == 2
    assert len(color_blocks) == 2
    assert gray_conf > 0
    assert color_conf > 0
