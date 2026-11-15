"""A read-only file surface that applies the existing case-role access policy."""
import re
from pathlib import Path
import access

PROJECT = Path(__file__).resolve().parents[2]


class Files:
    def __init__(self, role, case_id, project=PROJECT):
        if role not in access.AGENTS or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", case_id):
            raise ValueError("invalid role or case id")
        self.role, self.case_id, self.project = role, case_id, Path(project).resolve()
        self.cases = self.project / "cases"

    def path(self, raw):
        raw = str(raw).strip().replace("\\", "/")
        if raw in ("", ".", "./"):
            raw = "cases/" + self.case_id                        # the session's own case
        elif raw.split("/", 1)[0] == self.case_id:
            raw = "cases/" + raw                                  # relative to the cases root, as the other tools take it
        p = (self.project / raw).resolve()
        rel = p.relative_to(self.project)
        parts = rel.parts
        if not parts or any(x.startswith(".") for x in parts):
            raise PermissionError("hidden files are not part of the case file surface")
        if parts[0] == "cases":
            if len(parts) < 2 or parts[1] != self.case_id:
                raise PermissionError("this CLI session is bound to one case")
            why = access.denied(self.role, Path(*parts[1:]).as_posix(), self.cases)
            if why:
                raise PermissionError(why)
            return p
        # 2026-11-12: nothing outside the case: the library and products come through retrieval, and the specifications,
        # code and configuration are not the agents' to read (their prompt carries what they need)
        raise PermissionError("read the case's files (cases/<case_id>/...); the library and the products are read through tax-read")

    # Typed parameters: without them the tool schema has no types, and a model sends the numbers as strings.
    def read_file(self, path: str, offset: int = 0, max_chars: int = 16000) -> dict:
        p = self.path(path)
        if p.suffix.lower() not in (".md", ".txt", ".json", ".jsonl", ".csv", ".mmd"):
            raise PermissionError("use parsed document pages or read_image for binary files")
        text = p.read_text(encoding="utf-8-sig")
        offset, size = max(0, int(offset or 0)), min(max(1, int(max_chars or 16000)), 32000)
        return {"text": text[offset:offset + size], "offset": offset, "next_offset": offset + size if len(text) > offset + size else None}

    def list_files(self, path: str, pattern: str = "*", limit: int = 100) -> dict:
        folder = self.path(path)
        if any(x in pattern for x in ("..", "/", "\\")):
            raise PermissionError("pattern must match file names, not paths")
        result = []
        for p in sorted(folder.rglob(pattern)):
            if len(result) >= min(max(int(limit or 100), 1), 300):
                break
            try:
                self.path(p)
            except (PermissionError, ValueError):
                continue
            if p.is_file():
                result.append(p.relative_to(self.project).as_posix())
        return {"files": result}

    def search(self, path: str, query: str, limit: int = 30) -> dict:
        """Lines containing query (case-insensitive) in one file or in the files under a folder."""
        target = self.path(path)
        names = [target.relative_to(self.project).as_posix()] if target.is_file() else self.list_files(path, limit=300)["files"]
        hits, cap = [], min(max(int(limit or 30), 1), 100)
        for name in names:
            p = self.path(name)
            if p.suffix.lower() not in (".md", ".txt", ".csv", ".json", ".jsonl", ".mmd"):
                continue
            for number, line in enumerate(p.read_text(encoding="utf-8-sig").splitlines(), 1):
                if query.casefold() in line.casefold():
                    hits.append({"path": name, "line": number, "text": line[:1000]})
                if len(hits) >= cap:
                    return {"hits": hits}
        return {"hits": hits}

    def read_image(self, path: str):
        if self.role == "polish":
            raise PermissionError("polish reads the render_pdf layout report")
        p = self.path(path)
        if p.suffix.lower() not in (".png", ".jpg", ".jpeg"):
            raise PermissionError("only case image pages may be read here")
        from mcp.server.mcpserver import Image
        return Image(path=p)


def build_server(role, case_id):
    from mcp.server.mcpserver import MCPServer
    files = Files(role, case_id)
    server = MCPServer("tax-files")
    for name in ("read_file", "list_files", "search", "read_image"):
        if name != "read_image" or role != "polish":
            server.add_tool(getattr(files, name), name=name)
    return server
