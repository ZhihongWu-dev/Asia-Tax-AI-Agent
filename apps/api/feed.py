"""Read an agent's event stream into what the web page shows: its thinking, its visible text and its tool calls."""
import json
import re

KEYS = ("file_path", "path", "pattern", "query", "url", "command", "name", "target", "input", "run_id", "case_id")


def tool_label(name):
    if name.startswith("mcp__"):
        _, server, tool = name.split("__", 2)
        return "%s · %s" % (server, tool)
    return name


def tool_detail(data):
    """One short argument, enough to see what the call is about."""
    value = next((data[k] for k in KEYS if isinstance(data.get(k), str) and data[k]), "")
    value = " ".join(value.split())
    return value[:87] + "..." if len(value) > 90 else value


def items_of(event):
    kind = event.get("type")
    if kind == "stream_event":
        inner = event.get("event") or {}
        if inner.get("type") == "content_block_start":
            block = (inner.get("content_block") or {}).get("type")
            if block in ("thinking", "text"):
                return [{"kind": block, "text": "", "start": True}]
        if inner.get("type") == "content_block_delta":
            delta = inner.get("delta") or {}
            if delta.get("type") == "thinking_delta":
                return [{"kind": "thinking", "text": delta.get("thinking", "")}]
            if delta.get("type") == "text_delta":
                return [{"kind": "text", "text": delta.get("text", "")}]
    if kind == "assistant":
        blocks = (event.get("message") or {}).get("content") or []
        return [{"kind": "tool", "name": tool_label(b.get("name", "")), "detail": tool_detail(b.get("input") or {})}
                for b in blocks if isinstance(b, dict) and b.get("type") == "tool_use"]
    return []


class Tail:
    """One stream file, read as it grows. Only whole lines count; a line still being written waits for the next read."""

    def __init__(self, path, secret=""):
        self.path, self.secret, self.offset = path, secret.encode(), 0
        self.items, self.result, self.session_id = [], {}, ""

    def read(self):
        with open(self.path, "rb") as f:
            f.seek(self.offset)
            data = f.read()
        end = data.rfind(b"\n")
        if end < 0:
            return []
        self.offset += end + 1
        fresh = []
        for line in data[:end].split(b"\n"):
            if self.secret:
                line = line.replace(self.secret, b"<redacted>")
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("type") == "result":
                self.result = event
            self.session_id = event.get("session_id") or self.session_id
            fresh.extend(items_of(event))
        self.items.extend(fresh)
        return fresh


def merged(items):
    """Adjacent pieces of the same kind as one item. `start` marks a new paragraph, and survives on the first piece of a batch."""
    out = []
    for item in items:
        if item["kind"] in ("thinking", "text") and out and out[-1]["kind"] == item["kind"]:
            out[-1] = {**out[-1], "text": out[-1]["text"] + ("\n\n" if item.get("start") else "") + item["text"]}
        else:
            out.append(dict(item))
    return [i for i in out if i["kind"] == "tool" or i.get("start") or i["text"].strip()]


# ------------------------------------------------------------ what reaches the client
LEAK = re.compile(r"[A-Za-z]:[\\/]\S+|(?<![\w/])(?:cases|intake|report|log|notes|bugs)[\\/]\S*|\bCASE-[\w-]+|\b\d{8}-[0-9a-f]{8}\b|\b[\w-]+\.(?:jsonl?|py|md)\b")
LONG_LINE = 160
EMPTY_TAIL = re.compile(r"^(?:[-*_]{3,}|[#*\s]*sources?[:*\s]*)$", re.I)


def client_text(text):
    """A reply without file paths, case ids or run ids: a short line that carries one is dropped, a paragraph keeps its sentence."""
    kept = []
    for line in (text or "").splitlines():
        if not LEAK.search(line):
            kept.append(line)
        elif len(line) > LONG_LINE:
            kept.append(re.sub(r"\s{2,}", " ", LEAK.sub("", line)))
    while kept and (not kept[-1].strip() or EMPTY_TAIL.match(kept[-1].strip())):
        kept.pop()
    return "\n".join(kept).strip()
