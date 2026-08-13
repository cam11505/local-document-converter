"""Regenerate the small Stage 9 OCR image fixture."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main() -> None:
    destination = Path(__file__).with_name("sample.png")
    image = Image.new("RGB", (720, 220), "white")
    draw = ImageDraw.Draw(image)
    regular = Path("C:/Windows/Fonts/arial.ttf")
    bold = Path("C:/Windows/Fonts/arialbd.ttf")
    title_font = ImageFont.truetype(str(bold), 36)
    body_font = ImageFont.truetype(str(regular), 28)
    draw.rectangle((18, 18, 702, 202), outline="black", width=3)
    draw.text((48, 52), "Stage 9 OCR Sample", fill="black", font=title_font)
    draw.text((48, 120), "Fallback text recovered.", fill="black", font=body_font)
    image.save(destination, format="PNG", optimize=False)


if __name__ == "__main__":
    main()
