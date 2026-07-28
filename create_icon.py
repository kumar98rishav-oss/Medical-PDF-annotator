"""
Generate a simple app icon.
Run once: python create_icon.py
Produces: icon.ico
"""

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("pip install Pillow")
    print("Then run again: python create_icon.py")
    exit(1)

sizes = [16, 32, 48, 64, 128, 256]
images = []

for size in sizes:
    img = Image.new('RGBA', (size, size), (37, 99, 235, 255))  # Blue
    draw = ImageDraw.Draw(img)

    # Draw a simple document icon
    margin = size // 8
    doc_w = size - 2 * margin
    doc_h = size - 2 * margin

    # Document body (white rectangle)
    draw.rectangle(
        [margin, margin, margin + doc_w, margin + doc_h],
        fill=(255, 255, 255, 240),
        outline=(30, 64, 175, 255),
        width=max(1, size // 32)
    )

    # Lines on document
    line_margin = size // 5
    line_y_start = margin + size // 4
    line_spacing = size // 8

    for i in range(3):
        y = line_y_start + i * line_spacing
        if y + line_spacing < margin + doc_h:
            draw.rectangle(
                [line_margin, y, size - line_margin - size // 6, y + max(1, size // 20)],
                fill=(37, 99, 235, 180)
            )

    # Corner fold
    fold_size = size // 5
    fold_x = margin + doc_w - fold_size
    fold_y = margin
    draw.polygon(
        [(fold_x, fold_y), (margin + doc_w, fold_y + fold_size), (fold_x, fold_y + fold_size)],
        fill=(219, 234, 254, 255),
        outline=(30, 64, 175, 255),
    )

    images.append(img)

images[0].save(
    'icon.ico',
    format='ICO',
    sizes=[(s, s) for s in sizes],
    append_images=images[1:]
)
print("✓ icon.ico created")