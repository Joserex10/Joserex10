"""Render first-party editorial product maps used by the profile README.

These are intentionally diagrams, not fabricated application screenshots.
The generated PNGs contain no EXIF metadata.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SIZE = (1200, 640)

BG = "#F7F7F4"
PAPER = "#FFFFFF"
INK = "#161B22"
MUTED = "#57606A"
HAIRLINE = "#D0D7DE"
BLUE = "#0969DA"
SOFT_BLUE = "#DDF4FF"
SOFT_GRAY = "#EAEEF2"


def font(size: int, *, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    if mono:
        candidates.extend(
            [
                Path("C:/Windows/Fonts/consola.ttf"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
            ]
        )
    elif bold:
        candidates.extend(
            [
                Path("C:/Windows/Fonts/segoeuib.ttf"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            ]
        )
    else:
        candidates.extend(
            [
                Path("C:/Windows/Fonts/segoeui.ttf"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            ]
        )

    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default(size=size)


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], *, fill: str, outline: str = HAIRLINE, radius: int = 16, width: int = 2) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def header(draw: ImageDraw.ImageDraw, number: str, title: str, subtitle: str) -> None:
    draw.text((68, 52), f"PRODUCT SYSTEM / {number}", font=font(18, mono=True), fill=BLUE)
    draw.text((68, 94), title, font=font(54, bold=True), fill=INK)
    draw.text((68, 162), subtitle, font=font(24), fill=MUTED)
    draw.line((68, 214, 1132, 214), fill=BLUE, width=3)
    draw.text((1132, 64), "CONCEPTUAL PRODUCT MAP · NOT A SCREENSHOT", font=font(14, mono=True), fill=MUTED, anchor="ra")


def save(image: Image.Image, filename: str) -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    image.save(ASSETS / filename, format="PNG", optimize=True)


def render_arca() -> None:
    image = Image.new("RGB", SIZE, BG)
    draw = ImageDraw.Draw(image)
    header(draw, "01", "Arca", "Your ideas, locally owned.")

    rounded(draw, (68, 250, 300, 570), fill=PAPER)
    draw.text((92, 278), "LOCAL VAULT", font=font(15, mono=True), fill=BLUE)
    for y, label in [(326, "notes/"), (372, "canvas/"), (418, "images/"), (464, "archive/")]:
        draw.ellipse((92, y + 5, 102, y + 15), fill=BLUE if y == 326 else HAIRLINE)
        draw.text((118, y), label, font=font(20, mono=True), fill=INK if y == 326 else MUTED)
    draw.text((92, 530), "Markdown on device", font=font(14), fill=MUTED)

    rounded(draw, (330, 250, 790, 570), fill=PAPER)
    draw.text((358, 278), "WRITING SURFACE", font=font(15, mono=True), fill=BLUE)
    draw.text((358, 328), "Thinking in systems", font=font(30, bold=True), fill=INK)
    draw.rounded_rectangle((358, 382, 716, 396), radius=7, fill=SOFT_GRAY)
    draw.rounded_rectangle((358, 420, 668, 434), radius=7, fill=SOFT_GRAY)
    draw.rounded_rectangle((358, 458, 734, 472), radius=7, fill=SOFT_GRAY)
    draw.rounded_rectangle((358, 496, 588, 510), radius=7, fill=SOFT_BLUE)

    rounded(draw, (820, 250, 1132, 570), fill=INK, outline=INK)
    draw.text((848, 278), "VISUAL CANVAS", font=font(15, mono=True), fill="#79C0FF")
    nodes = [(870, 360), (1026, 330), (996, 468), (890, 492)]
    for start, end in [(nodes[0], nodes[1]), (nodes[1], nodes[2]), (nodes[0], nodes[3]), (nodes[3], nodes[2])]:
        draw.line((*start, *end), fill="#484F58", width=3)
    for index, (x, y) in enumerate(nodes):
        fill = BLUE if index == 0 else "#30363D"
        outline = "#79C0FF" if index in (0, 2) else "#484F58"
        draw.rounded_rectangle((x - 28, y - 20, x + 28, y + 20), radius=9, fill=fill, outline=outline, width=2)
    save(image, "arca-preview.png")


def render_docuflow() -> None:
    image = Image.new("RGB", SIZE, BG)
    draw = ImageDraw.Draw(image)
    header(draw, "02", "DocuFlow", "Documentation without friction.")

    rounded(draw, (68, 250, 1132, 570), fill=PAPER)
    stages = [
        (92, "01", "CAPTURE", "Observe a workflow"),
        (344, "02", "REVIEW", "Edit every step"),
        (596, "03", "PROTECT", "Redact private data"),
        (848, "04", "EXPORT", "Ship a clear PDF"),
    ]
    for x, number, title, detail in stages:
        draw.text((x, 278), number, font=font(15, mono=True), fill=BLUE)
        draw.text((x, 314), title, font=font(22, bold=True), fill=INK)
        draw.text((x, 350), detail, font=font(16), fill=MUTED)

        if number == "01":
            draw.rounded_rectangle((x, 402, x + 196, 514), radius=12, fill=SOFT_GRAY)
            draw.ellipse((x + 80, 438, x + 116, 474), outline=BLUE, width=5)
            draw.ellipse((x + 93, 451, x + 103, 461), fill=BLUE)
        elif number == "02":
            for offset, width in [(0, 180), (34, 146), (68, 168)]:
                draw.rounded_rectangle((x, 408 + offset, x + width, 422 + offset), radius=7, fill=SOFT_GRAY)
            draw.rounded_rectangle((x, 500, x + 96, 520), radius=8, fill=SOFT_BLUE)
        elif number == "03":
            draw.rounded_rectangle((x, 402, x + 196, 514), radius=12, fill=SOFT_BLUE)
            draw.rounded_rectangle((x + 24, 430, x + 172, 458), radius=4, fill=INK)
            draw.rounded_rectangle((x + 42, 474, x + 154, 490), radius=4, fill=INK)
        else:
            draw.rounded_rectangle((x, 402, x + 196, 514), radius=12, fill=INK)
            draw.text((x + 98, 438), "PDF", font=font(31, bold=True), fill=PAPER, anchor="ma")
            draw.text((x + 98, 486), "LOCAL OUTPUT", font=font(13, mono=True), fill="#79C0FF", anchor="ma")

    for x in (318, 570, 822):
        draw.line((x, 432, x + 20, 432), fill=BLUE, width=3)
        draw.polygon([(x + 20, 426), (x + 32, 432), (x + 20, 438)], fill=BLUE)
    save(image, "docuflow-preview.png")


if __name__ == "__main__":
    render_arca()
    render_docuflow()
