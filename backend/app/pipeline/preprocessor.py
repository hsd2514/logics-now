import cv2
import numpy as np
from PIL import Image
from typing import Tuple
import io

class Preprocessor:
    """Stage 1: Image preprocessing - deskew, denoise, enhance"""
    
    def __init__(self):
        self.target_dpi = 300
    
    def process(self, image_path: str) -> Tuple[np.ndarray, float]:
        """
        Process image and return enhanced version with quality score.
        """
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Calculate initial quality score
        quality_score = self._calculate_quality(gray)
        
        # Deskew
        deskewed = self._deskew(gray)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(deskewed, None, 10, 7, 21)
        
        # Adaptive thresholding with CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # Binarization for OCR
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Recalculate quality after processing
        final_quality = self._calculate_quality(binary)
        
        return binary, max(quality_score, final_quality)
    
    def process_bytes(self, image_bytes: bytes) -> Tuple[np.ndarray, float]:
        """Process image from bytes."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise ValueError("Could not decode image bytes")
        
        # Save temporarily and process
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        quality_score = self._calculate_quality(gray)
        deskewed = self._deskew(gray)
        denoised = cv2.fastNlMeansDenoising(deskewed, None, 10, 7, 21)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        final_quality = self._calculate_quality(binary)
        
        return binary, max(quality_score, final_quality)
    
    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """Deskew image using Hough transform."""
        # Edge detection
        edges = cv2.Canny(image, 50, 150, apertureSize=3)
        
        # Detect lines
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
        
        if lines is None:
            return image
        
        # Calculate dominant angle
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            if abs(angle) < 45:  # Only consider near-horizontal lines
                angles.append(angle)
        
        if not angles:
            return image
        
        median_angle = np.median(angles)
        
        # Rotate image
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        return rotated
    
    def _calculate_quality(self, image: np.ndarray) -> float:
        """Calculate image quality score (0-1)."""
        # Laplacian variance for blur detection
        laplacian_var = cv2.Laplacian(image, cv2.CV_64F).var()
        blur_score = min(laplacian_var / 500, 1.0)
        
        # Contrast score
        contrast = image.std() / 128
        contrast_score = min(contrast, 1.0)
        
        # Noise estimation
        noise = self._estimate_noise(image)
        noise_score = max(0, 1 - noise / 50)
        
        # Combined score
        quality = 0.4 * blur_score + 0.3 * contrast_score + 0.3 * noise_score
        return round(quality, 3)
    
    def _estimate_noise(self, image: np.ndarray) -> float:
        """Estimate noise level in image."""
        H, W = image.shape
        M = [[1, -2, 1],
             [-2, 4, -2],
             [1, -2, 1]]
        sigma = np.sum(np.sum(np.abs(cv2.filter2D(image, -1, np.array(M)))))
        sigma = sigma * np.sqrt(0.5 * np.pi) / (6 * (W-2) * (H-2))
        return sigma
