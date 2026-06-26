#!/usr/bin/env python3
"""
Ingest content from Kiwix ZIMs, Calibre library, and loose files into MeiliSearch.
Run this after adding new content, then delete any temp files.
"""

import os
import sqlite3
import subprocess
import shutil
import hashlib
from pathlib import Path
from bs4 import BeautifulSoup
import meilisearch
import glob


MEILI_URL = "http://localhost:7700"
PREP_DIR = Path("/mnt/vault")
TEMP_DIR = PREP_DIR / "tmp_extract"
ZIM_DIR = PREP_DIR / "zim"
CALIBRE_DB = PREP_DIR / "pdf" / "metadata.db"
CALIBRE_DIR = PREP_DIR / "pdf"

client = meilisearch.Client(MEILI_URL)

# Create the index if it doesn't exist
try:
    client.create_index("vault", {"primaryKey": "id"})
except:
    pass


def make_id(text):
    """Generate a stable ID from a string."""
    return hashlib.md5(text.encode()).hexdigest()


def ingest_zim(zim_path):
    zim_name = zim_path.stem
    print(f"Listing articles in {zim_path.name}...")
    skip_extensions = {'.png', '.jpg', '.svg', '.css', '.js', '.ico', '.gif', '.woff', '.woff2', '.ttf', '.eot'}

    # Fetch already-indexed IDs for this ZIM
    existing_ids = set()
    offset = 0
    while True:
        result = client.index("vault").get_documents(
            {"filter": f'source = "{zim_name}"', "fields": ["id"], "limit": 1000, "offset": offset}
        )
        if not result.results:
            break
        existing_ids.update(doc.id for doc in result.results)
        if (len(existing_ids) == 0):
            print(f"  {len(existing_ids)} articles already in index, will skip.")
        offset += len(result.results)

    documents = []
    current_path = None
    current_title = None
    current_mime = None
    total_indexed = 0
    skipped = 0
    proc = subprocess.Popen(
        ["zimdump", "list", "--details", str(zim_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1
    )
    for line in proc.stdout:
        line = line.strip()
        if line.startswith("path: "):
            current_path = line[6:]
            current_title = None
            current_mime = None
        elif line.startswith("* title:"):
            current_title = line.split(":", 1)[1].strip()
        elif line.startswith("* mime-type:"):
            current_mime = line.split(":", 1)[1].strip()
        elif line.startswith("* item size:"):
            if current_path and current_mime and current_mime.startswith("text/html"):
                if not any(current_path.endswith(ext) for ext in skip_extensions):
                    doc_id = make_id(f"zim-{zim_name}-{current_path}")
                    if doc_id in existing_ids:
                        skipped += 1
                        continue
                    title = current_title or current_path.replace('-', ' ').replace('_', ' ')
                    kiwix_url = f"http://localhost:8888/{zim_name}/{current_path}"
                    documents.append({
                        "id": doc_id,
                        "title": title,
                        "content": "",
                        "type": "wiki",
                        "source": zim_name,
                        "url": kiwix_url,
                    })
            if len(documents) >= 1000:
                client.index("vault").add_documents(documents)
                total_indexed += len(documents)
                print(f"  Indexed {total_indexed} articles...")
                documents = []
    proc.wait()
    if documents:
        client.index("vault").add_documents(documents)
        total_indexed += len(documents)
    print(f"  Done with {zim_path.name} — {total_indexed} new, {skipped} skipped (already indexed)")


def make_id(text):
    return hashlib.md5(text.encode()).hexdigest()

def is_indexed(doc_id):
    try:
        client.index("vault").get_document(doc_id)
        return True
    except:
        return False


def ingest_calibre():
    if not CALIBRE_DB.exists():
        print("Calibre database not found, skipping")
        return
    # Import any new PDFs sitting in the root of the library folder
    new_pdfs = glob.glob(os.path.join(CALIBRE_DIR, "*.pdf"))
    if new_pdfs:
        print(f"  Importing {len(new_pdfs)} new PDFs into Calibre...")
        subprocess.run(
            ["calibredb", "add"] + new_pdfs + ["--with-library=" + str(CALIBRE_DIR)],
        )
        # Delete the root PDFs (Calibre made copies in subfolders)
        for pdf in new_pdfs:
            os.remove(pdf)
            print(f"  Removed {os.path.basename(pdf)} (imported into Calibre)")
    print("Indexing Calibre library...")
    conn = sqlite3.connect(str(CALIBRE_DB))
    query = """
        SELECT b.id, b.title, b.author_sort, b.path,
               d.format, d.name,
               (SELECT GROUP_CONCAT(t.name, ', ')
                FROM books_tags_link btl
                JOIN tags t ON btl.tag = t.id
                WHERE btl.book = b.id) as tags
        FROM books b
        LEFT JOIN data d ON b.id = d.book
        ORDER BY b.id DESC
    """
    seen_titles = set()
    documents = []
    for row in conn.execute(query):
        book_id, title, author, path, fmt, name, tags = row
        if not fmt:
            continue
        title_key = title.lower().strip()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        fmt_lower = fmt.lower()
        calibre_url = f"http://localhost:8083/read/{book_id}/{fmt_lower}"
        file_path = os.path.join(CALIBRE_DIR, path, f"{name}.{fmt_lower}")
        first_page_id = make_id(f"calibre-{book_id}-{fmt}-p1")
        if is_indexed(first_page_id):
            print(f"  Skipping {title} (already indexed)")
            continue
        if os.path.exists(file_path) and fmt_lower == "pdf":
            try:
                result = subprocess.run(
                    ["pdftotext", file_path, "-", "-layout"],
                    capture_output=True, text=True, timeout=120
                )
                pages = result.stdout.split('\f')
                for page_num, page_text in enumerate(pages, 1):
                    page_text = page_text.strip()
                    if not page_text or len(page_text) < 20:
                        continue
                    documents.append({
                        "id": make_id(f"calibre-{book_id}-{fmt}-p{page_num}"),
                        "title": f"{title} — Page {page_num}",
                        "book_title": title,
                        "author": author or "Unknown",
                        "content": page_text[:3000],
                        "tags": tags or "",
                        "type": "book",
                        "source": "calibre",
                        "url": f"{calibre_url}#page={page_num}",
                        "page": page_num,
                    })
                    if len(documents) >= 1000:
                        client.index("vault").add_documents(documents)
                        documents = []
                print(f"  Processed {len(pages)} pages from {title}")
            except Exception as e:
                print(f"  Error processing {file_path}: {e}")
    if documents:
        client.index("vault").add_documents(documents)
    print("  Done indexing books")
    conn.close()


def ingest_loose_files():
    """Index PDFs and text files not managed by Calibre."""
    print("Indexing loose files...")

    documents = []
    extensions = {".pdf", ".txt", ".md", ".html", ".htm"}
    calibre_dir = str(PREP_DIR / "pdf")
    for root, dirs, files in os.walk(PREP_DIR):
        if "venv" in root or "tmp_extract" in root or root.startswith(calibre_dir):
            continue

        for filename in files:
            ext = Path(filename).suffix.lower()
            if ext not in extensions:
                continue

            filepath = Path(root) / filename

            content = ""
            if ext == ".pdf":
                try:
                    result = subprocess.run(
                        ["pdftotext", str(filepath), "-"],
                        capture_output=True, text=True, timeout=30
                    )
                    content = result.stdout[:2000]
                except:
                    content = ""
            elif ext in {".txt", ".md", ".html", ".htm"}:
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        raw = f.read()
                    if ext in {".html", ".htm"}:
                        soup = BeautifulSoup(raw, "html.parser")
                        content = soup.get_text(separator=" ", strip=True)[:2000]
                    else:
                        content = raw[:2000]
                except:
                    content = ""

            documents.append({
                "id": make_id(f"file-{filepath}"),
                "title": filename,
                "content": content,
                "type": "file",
                "source": "local",
                "url": f"file://{filepath}",
            })

    if documents:
        client.index("vault").add_documents(documents)
    print(f"  Indexed {len(documents)} files")


import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest content into the vault index.")
    parser.add_argument("--fresh", action="store_true", help="Clear index before ingesting")
    parser.add_argument("--path", type=Path, help="Path to the vault directory")
    args = parser.parse_args()
    PREP_DIR = args.path
    if not PREP_DIR:
        print("Error: --path is required")
        exit(1)
    if not PREP_DIR.exists():
        print(f"Error: {PREP_DIR} does not exist")
        exit(1)
    if not PREP_DIR.is_dir():
        print(f"Error: {PREP_DIR} is not a directory")
        exit(1)
    if args.fresh:
        print("Clearing index...")
        client.index("vault").delete_all_documents()
        client.index("vault").update_ranking_rules([
            "words",
            "typo",
            "proximity",
            "attribute",
            "sort",
            "exactness",
        ])

        client.index("vault").update_searchable_attributes([
            "title",
            "content",
            "author",
            "tags",
            "source",
        ])

        client.index("vault").update_stop_words([
            "the", "a", "an", "is", "are", "was", "were", "of", "in", "to", "for", "and", "or", "on"
        ])

        client.index("vault").update_distinct_attribute("book_title")

        client.index("vault").update_filterable_attributes([
            "type", "source"
        ])

    # If no specific ingest option is provided, default to all
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # Index each ZIM one at a time (extract, index, delete)
    for zim_file in sorted(ZIM_DIR.glob("*.zim")):
        ingest_zim(zim_file)

    # Index Calibre books
    ingest_calibre()

    # Index loose files
    ingest_loose_files()

    # Final cleanup
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)

    print("\nDone! Search at http://localhost:7700")