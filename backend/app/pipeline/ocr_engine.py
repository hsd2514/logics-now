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
    """Stage 2: OCR extraction with spatial coordinates for heatmap"""
    
    def __init__(self):
        self.config = '--oem 3 --psm 6'  # LSTM engine, assume uniform block
    
    def extract(self, image: np.ndarray) -> Tuple[str, List[TextBlock], float]:
        """
        Extract text with bounding boxes.
        Returns: (full_text, text_blocks, avg_confidence)
        """
        # Convert numpy array to PIL Image
        if len(image.shape) == 2:
            pil_image = Image.fromarray(image)
        else:
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        # Get detailed OCR data with bounding boxes
        data = pytesseract.image_to_data(pil_image, config=self.config, output_type=pytesseract.Output.DICT)
        
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
    
    def extract_from_path(self, image_path: str) -> Tuple[str, List[TextBlock], float]:
        """Extract text from image file path."""
        image = Image.open(image_path)
        data = pytesseract.image_to_data(image, config=self.config, output_type=pytesseract.Output.DICT)
        
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
