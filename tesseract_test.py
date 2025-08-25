import fitz
from pathlib import Path

p = Path("C:/Users/Tamas/Documents/Python/Freelance/Testing/nas_file_organizer/Inbox/Invoice 1 - Tamas Kiss.pdf")
doc = fitz.open(p)
print("Pages:", len(doc))
for i, page in enumerate(doc):
    print("Page", i+1, "text:")
    print(page.get_text("text")[:200])