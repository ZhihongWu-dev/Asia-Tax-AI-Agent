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
        # The library is available through retrieval tools. Only business specs are
        # needed outside the case; credentials and implementation code never are.
        if len(parts) == 2 and parts[0] == "agent" and p.name.endswith(".en.md"):
            return p
        raise PermissionError("read case files or an English business specification; use retrieval for the library")

    def read_file(self, path, offset=0, max_chars=16000):
        p = self.path(path)
        if p.suffix.lower() not in (".md", ".txt", ".json", ".jsonl", ".csv", ".mmd"):
            raise PermissionError("use parsed document pages or read_image for binary files")
        text = p.read_text(encoding="utf-8-sig")
        offset, size = max(0, offset), min(max(1, max_chars), 32000)
        return {"text": text[offset:offset + size], "offset": offset, "next_offset": offset + size if len(text) > offset + size else None}

    def list_files(self, path, pattern="*", limit=100):
        folder = self.path(path)
        if any(x in pattern for x in ("..", "/", "\\")):
            raise PermissionError("pattern must match file names, not paths")
        result = []
        for p in sorted(folder.rglob(pattern)):
            if len(result) >= min(max(limit, 1), 300):
                break
            try:
                self.path(p)
            except (PermissionError, ValueError):
                continue
            if p.is_file():
                result.append(p.relative_to(self.project).as_posix())
        return {"files": result}

    def search(self, path, query, limit=30):
        hits = []
        for name in self.list_files(path, limit=300)["files"]:
            p = self.path(name)
            if p.suffix.lower() not in (".md", ".txt", ".csv", ".json"):
                continue
            for number, line in enumerate(p.read_text(encoding="utf-8-sig").splitlines(), 1):
                if query.casefold() in line.casefold():
                    hits.append({"path": name, "line": number, "text": line[:1000]})
                if len(hits) >= min(max(limit, 1), 100):
                    return {"hits": hits}
        return {"hits": hits}

    def read_image(self, path):
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
