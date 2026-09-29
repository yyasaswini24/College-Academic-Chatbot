import json
import re
import uuid
from datetime import datetime
from pathlib import Path

CHATS_DIR = Path(__file__).resolve().parent.parent / "data" / "chats"
TITLE_LENGTH = 40


def _chat_path(chat_id):
    # Ids can come from the page URL, so only allow simple names (no "../" tricks)
    if not re.fullmatch(r"[\w-]+", chat_id or ""):
        raise ValueError(f"Invalid chat id: {chat_id!r}")
    return CHATS_DIR / f"{chat_id}.json"


def new_chat_id():
    return datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]


def make_title(messages):
    for message in messages:
        if message["role"] == "user":
            text = " ".join(message["content"].split())
            if len(text) > TITLE_LENGTH:
                text = text[:TITLE_LENGTH].rstrip() + "..."
            return text
    return "New chat"


def save_chat(chat_id, messages):
    CHATS_DIR.mkdir(exist_ok=True)
    chat = {
        "id": chat_id,
        "title": make_title(messages),
        "updated": datetime.now().isoformat(timespec="seconds"),
        "messages": messages,
    }
    _chat_path(chat_id).write_text(json.dumps(chat, indent=2, ensure_ascii=False), encoding="utf-8")


def load_chat(chat_id):
    try:
        path = _chat_path(chat_id)
    except ValueError:
        return []
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))["messages"]


def list_chats():
    # Newest first: [{"id", "title", "updated"}, ...]
    if not CHATS_DIR.exists():
        return []

    chats = []
    for path in CHATS_DIR.glob("*.json"):
        try:
            chat = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        chats.append({"id": chat["id"], "title": chat["title"], "updated": chat["updated"]})

    return sorted(chats, key=lambda chat: chat["updated"], reverse=True)


def delete_chat(chat_id):
    _chat_path(chat_id).unlink(missing_ok=True)
