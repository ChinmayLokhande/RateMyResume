import sys

import pymupdf

source, output = pymupdf.open(sys.argv[1]), pymupdf.open()
for page in source:
    scan = output.new_page(width=page.rect.width, height=page.rect.height)
    scan.insert_image(scan.rect, pixmap=page.get_pixmap(dpi=150))
output.save(sys.argv[2])
print("wrote", sys.argv[2])