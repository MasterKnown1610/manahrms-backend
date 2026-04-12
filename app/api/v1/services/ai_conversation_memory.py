"""
In-process conversation memory for AI chat (per company + user + conversation_id).

Use this so follow-up messages ("last name is Reddy") keep context without the client
resending the full transcript. For multi-worker production, replace with Redis.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List, Optional

_lock = threading.Lock()
# key -> (messages, last_touch_epoch)
_store: Dict[str, tuple[List[Dict[str, str]], float]] = {}

MAX_MESSAGES_PER_CONV = 40
MAX_CONVERSATIONS = 2000
TTL_SECONDS = 48 * 3600


def _make_key(company_id: int, user_id: int, conversation_id: str) -> str:
    return f"{company_id}:{user_id}:{conversation_id}"


def _prune_unlocked() -> None:
    now = time.time()
    dead = [k for k, (_, ts) in _store.items() if now - ts > TTL_SECONDS]
    for k in dead:
        del _store[k]
    while len(_store) > MAX_CONVERSATIONS:
        _store.pop(next(iter(_store)))


def get_messages(company_id: int, user_id: int, conversation_id: str) -> List[Dict[str, str]]:
    with _lock:
        _prune_unlocked()
        entry = _store.get(_make_key(company_id, user_id, conversation_id))
        if not entry:
            return []
        msgs, ts = entry
        if time.time() - ts > TTL_SECONDS:
            del _store[_make_key(company_id, user_id, conversation_id)]
            return []
        return [dict(m) for m in msgs]


def append_turn(
    company_id: int,
    user_id: int,
    conversation_id: str,
    user_content: str,
    assistant_content: str,
) -> None:
    with _lock:
        _prune_unlocked()
        key = _make_key(company_id, user_id, conversation_id)
        msgs, _ = _store.get(key, ([], 0.0))
        msgs = list(msgs)
        msgs.append({"role": "user", "content": user_content})
        msgs.append({"role": "assistant", "content": assistant_content})
        if len(msgs) > MAX_MESSAGES_PER_CONV:
            msgs = msgs[-MAX_MESSAGES_PER_CONV:]
        _store[key] = (msgs, time.time())


def new_conversation_id() -> str:
    return str(uuid.uuid4())
