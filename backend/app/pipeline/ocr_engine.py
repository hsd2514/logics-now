import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from rapidocr_onnxruntime import RapidOCR
import pytesseract
from PIL import Image
import numpy as np
import cv2
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class TextBlock:
    text: str
    x: float
    y: float
    width: float
    height: float
    confidence: float
    level: int
    block_num: int
    line_num: int
    word_num: int

class OCREngine:
    """Stage 2: Fast OCR extraction with spatial coordinates using RapidOCR (ONNX) with Tesseract Fallback"""
    
    def __init__(self):
        # Initialize RapidOCR (downloads onnx models on first run if missing)
        self.reader = RapidOCR()
        self.tesseract_config = '--oem 3 --psm 6'  # LSTM engine, assume uniform block
    
    def _extract_tesseract(self, image: np.ndarray) -> Tuple[str, List[TextBlock], float]:
        """Fallback extraction using PyTesseract."""
        if len(image.shape) == 2:
            pil_image = Image.fromarray(image)
        else:
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        data = pytesseract.image_to_data(pil_image, config=self.tesseract_config, output_type=pytesseract.Output.DICT)
        
        text_blocks = []
        full_text_parts = []
        confidences = []
        
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            text = data['text'][i].strip()
            conf = float(data['conf'][i])
            
            if text and conf > 0:
                block = TextBlock(
                    text=text,
                    x=float(data['left'][i]),
                    y=float(data['top'][i]),
                    width=float(data['width'][i]),
                    height=float(data['height'][i]),
                    confidence=conf / 100.0,
                    level=data['level'][i],
                    block_num=data['block_num'][i],
                    line_num=data['line_num'][i],
                    word_num=data['word_num'][i]
                )
                text_blocks.append(block)
                full_text_parts.append(text)
                confidences.append(conf)
        
        full_text = ' '.join(full_text_parts)
        avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0
        
        return full_text, text_blocks, avg_confidence

    def extract(self, image: np.ndarray) -> Tuple[str, List[TextBlock], float]:
        """
        Extract text with bounding boxes.
        Returns: (full_text, text_blocks, avg_confidence)
        """
        try:
            # Read text from numpy array using RapidOCR first
            result, _ = self.reader(image)
            
            text_blocks = []
            full_text_parts = []
            confidences = []
            
            if result:
                for i, res in enumerate(result):
                    bbox, text, conf = res
                    text = text.strip()
                    if text and float(conf) > 0:
                        # bbox is a list of 4 points: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                        x_coords = [p[0] for p in bbox]
                        y_coords = [p[1] for p in bbox]
                        
                        x_min, x_max = min(x_coords), max(x_coords)
                        y_min, y_max = min(y_coords), max(y_coords)
                        
                        block = TextBlock(
                            text=text,
                            x=float(x_min),
                            y=float(y_min),
                            width=float(x_max - x_min),
                            height=float(y_max - y_min),
                            confidence=float(conf),
                            level=1,
                            block_num=1,
                            line_num=i,
                            word_num=1
                        )
                        text_blocks.append(block)
                        full_text_parts.append(text)
                        confidences.append(float(conf))
            
            full_text = ' '.join(full_text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # If nothing was extracted, throwing so fallback triggers
            if not full_text:
                raise ValueError("No text extracted by RapidOCR")
                
            return full_text, text_blocks, avg_confidence
            
        except Exception as e:
            print(f"RapidOCR Failed or returned empty: {e}. Falling back to PyTesseract.")
            return self._extract_tesseract(image)
    
    def extract_from_path(self, image_path: str) -> Tuple[str, List[TextBlock], float]:
        """Extract text from image file path."""
        # Read image using cv2
        image = cv2.imread(image_path)
        return self.extract(image)
    
    def blocks_to_dict(self, blocks: List[TextBlock]) -> List[Dict]:
        """Convert TextBlock objects to dictionaries for JSON storage."""
        return [
            {
                'text': b.text,
                'x': b.x,
                'y': b.y,
                'width': b.width,
                'height': b.height,
                'confidence': b.confidence
            }
            for b in blocks
        ]
