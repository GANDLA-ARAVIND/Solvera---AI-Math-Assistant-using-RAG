import os
import uuid
import io
import platform
import google.generativeai as genai

# Add Tesseract to PATH before importing pytesseract (Windows only)
if platform.system() == "Windows":
    tesseract_path = r"C:\Program Files\Tesseract-OCR"
    if os.path.exists(tesseract_path):
        os.environ["PATH"] = tesseract_path + ";" + os.environ.get("PATH", "")

try:
    import pytesseract
    if platform.system() == "Windows":
        # Also explicitly set the path after import
        pytesseract.pytesseract.pytesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
except Exception:
    pytesseract = None

from PIL import Image
from app.config import GOOGLE_API_KEY, OCR_MODEL
from app.utils.prompts import OCR_EXTRACTION_PROMPT

genai.configure(api_key=GOOGLE_API_KEY)

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class OCRService:
    def __init__(self):
        self.model = genai.GenerativeModel(OCR_MODEL)

    def _extract_with_tesseract(self, image: Image.Image) -> dict:
        if pytesseract is None:
            return {
                "success": False,
                "error": "tesseract_missing",
                "message": "Local OCR is not installed. Install Tesseract and pytesseract to use offline OCR.",
            }

        try:
            extracted_text = pytesseract.image_to_string(image)
            extracted_text = extracted_text.strip()
            if not extracted_text:
                return {
                    "success": False,
                    "error": "tesseract_no_text",
                    "message": "Local OCR did not detect any text. Try a clearer image.",
                }

            return {
                "success": True,
                "extracted_text": extracted_text,
                "confidence_note": "Extracted using local OCR (Tesseract). Please verify the extraction is correct.",
            }
        except Exception as e:
            return {
                "success": False,
                "error": "tesseract_failed",
                "error_detail": str(e),
                "message": "Local OCR failed to process the image.",
            }

    async def extract_math_from_image(self, image_bytes: bytes, filename: str) -> dict:
        """Process an uploaded image through Gemini Vision to extract math content."""
        try:
            if not GOOGLE_API_KEY:
                image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                local_result = self._extract_with_tesseract(image)
                if local_result.get("success"):
                    local_result["image_path"] = None
                return local_result
            # Save the image
            file_ext = os.path.splitext(filename)[1] or ".png"
            saved_filename = f"{uuid.uuid4().hex}{file_ext}"
            saved_path = os.path.join(UPLOAD_DIR, saved_filename)

            with open(saved_path, "wb") as f:
                f.write(image_bytes)

            # Prepare image for OCR
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

            # Call Gemini Vision
            response = self.model.generate_content([OCR_EXTRACTION_PROMPT, image])
            extracted_text = response.text.strip()

            return {
                "success": True,
                "extracted_text": extracted_text,
                "image_path": f"/static/uploads/{saved_filename}",
                "confidence_note": "Extracted using Gemini Vision. Please verify the extraction is correct.",
            }
        except Exception as e:
            error_text = str(e)
            if "Quota exceeded" in error_text or "429" in error_text:
                local_result = self._extract_with_tesseract(image)
                if local_result.get("success"):
                    local_result["image_path"] = f"/static/uploads/{saved_filename}"
                return local_result
            return {
                "success": False,
                "error": "ocr_failed",
                "error_detail": error_text,
                "message": "Failed to extract math from image. Please try a clearer image.",
            }


ocr_service = OCRService()
