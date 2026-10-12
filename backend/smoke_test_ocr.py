from PIL import Image, ImageDraw, ImageFont
from paddleocr import PaddleOCR

# 1. Make a simple image containing known text
image = Image.new("RGB", (1000, 200), "white")
draw = ImageDraw.Draw(image)
draw.text(
    (30, 70),
    "Test Person  test@example.com  +91 90000 00000",
    fill="black",
    font=ImageFont.load_default(size=36),
)
image.save("/tmp/ocr_test.png")

# 2. Ask PaddleOCR to read it back
ocr = PaddleOCR(
    lang="en",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
)
results = ocr.predict("/tmp/ocr_test.png")

for page in results:
    print(page["rec_texts"])