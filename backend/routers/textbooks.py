from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.schemas import Textbook, TextbookStatus
import uuid
import os
import json
from backend import config

router = APIRouter()

_textbooks: dict[str, Textbook] = {}


def _load_existing_textbooks():
    """Load previously parsed textbooks from storage on startup."""
    parsed_dir = config.PARSED_DIR
    if not os.path.exists(parsed_dir):
        return
    for f in os.listdir(parsed_dir):
        if not f.endswith(".json"):
            continue
        path = os.path.join(parsed_dir, f)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            tb = Textbook(**data)
            _textbooks[tb.textbook_id] = tb
        except Exception:
            continue


_load_existing_textbooks()


@router.post("/upload", response_model=Textbook)
async def upload_textbook(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No file provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".md", ".markdown", ".txt", ".docx"]:
        raise HTTPException(400, f"Unsupported format: {ext}")

    book_id = f"book_{uuid.uuid4().hex[:8]}"
    save_path = os.path.join(config.UPLOAD_DIR, f"{book_id}{ext}")
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    title = os.path.splitext(file.filename)[0]
    textbook = Textbook(
        textbook_id=book_id,
        filename=file.filename,
        title=title,
        file_type=ext.lstrip("."),
        total_pages=0,
        total_chars=0,
        status=TextbookStatus.UPLOADED,
        chapters=[],
    )
    _textbooks[book_id] = textbook
    return textbook


@router.get("", response_model=list[Textbook])
async def list_textbooks():
    return list(_textbooks.values())


@router.get("/{textbook_id}", response_model=Textbook)
async def get_textbook(textbook_id: str):
    if textbook_id not in _textbooks:
        raise HTTPException(404, "Textbook not found")
    return _textbooks[textbook_id]


@router.post("/{textbook_id}/parse", response_model=Textbook)
async def parse_textbook(textbook_id: str):
    if textbook_id not in _textbooks:
        raise HTTPException(404, "Textbook not found")

    textbook = _textbooks[textbook_id]
    textbook.status = TextbookStatus.PARSING

    try:
        from backend.services.parser_service import parse_file
        result = parse_file(textbook)
        textbook.chapters = result.chapters
        textbook.total_pages = result.total_pages
        textbook.total_chars = result.total_chars
        textbook.status = TextbookStatus.PARSED

        parsed_path = os.path.join(config.PARSED_DIR, f"{textbook_id}.json")
        with open(parsed_path, "w", encoding="utf-8") as f:
            f.write(textbook.model_dump_json(indent=2))

    except Exception as e:
        textbook.status = TextbookStatus.FAILED
        raise HTTPException(500, f"Parse failed: {str(e)}")

    return textbook
