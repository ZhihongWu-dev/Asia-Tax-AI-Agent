#!/usr/bin/env python
"""The web host (agent/orchestration_cli_spec.en.md section 8): the API behind apps/web, one local user, bound to this machine.

  python apps/api/server.py     then open http://127.0.0.1:8000

A client message is one headless turn of the front agent. When the front agent says the intake is ready, the host starts the
orchestrator as its own process; progress and thinking are read from the case files, so a page reload or a restart of this
server loses nothing and a run keeps going without it.
"""
import asyncio
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "agent" / "tools"), str(Path(__file__).resolve().parent)]
import orchestrate as orch  # noqa: E402
from feed import LEAK, Tail, client_text, merged  # noqa: E402

CASES = orch.CASES
UPLOADS = CASES / "_uploads"
DIST = ROOT / "apps" / "web" / "dist"
USER = {"id": "local", "email": "local@taxrora.dev"}
FRONT_TURNS = 120
AUTO_RESTARTS = 3
ATTACHMENT = "\n\n[Taxrora attachment]\n"
START = "[[START_RUN]]"
FRONT_JARGON = re.compile(r"(?i)\b(?:intake package|handoff(?: file)?|return list|preview run|open items?|changes_rank|ranked recommendation|ranking|orchestrator|judgment points?|run_id|intake_check|facts\.json|answers\.json|unknown_not_asked)\b")
REWRITE = """[Host] Your last reply to the client used names of system parts: %s. The client does not know them. Rewrite that same reply in plain words: the same content, questions and decisions, said as what the client can do and what happens next. Call no tools. Output only the rewritten reply%s."""
UPLOAD_TYPES = {".pdf": "pdf", ".doc": "word", ".docx": "word", ".xls": "excel", ".xlsx": "excel",
                ".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image"}
UPLOAD_LIMIT = 10 * 1024 * 1024
RESUMABLE = ("rate_limited", "agent_failed", "revision_limit", "stopped", "system_defect")
PIPELINE = (("intake", "front"), ("review_intake", "review"), ("run", "program"), ("analysis", "analysis"),
            ("review_draft", "review"), ("polish", "polish"), ("review_final", "review"))
WEB_NOTE = """You are running behind the web interface; these points replace the Bash step of your procedure.
The client reads your replies in a chat window. The case already exists and its id is in the first message, so do not call case_new. Uploaded documents are already in intake/documents/. The host has already written each client message to dialogue.md word for word: do not append client entries, and never write words for the client.
Starting the orchestrator is the host's job, so never run orchestrate.py yourself. When step 4 is ready (handoff.md written, intake_check clean), tell the client in one or two sentences that the analysis is starting, and end your reply with the line [[START_RUN]]. The host then runs it and shows the progress beside the chat.
When it ends, the host sends you a message beginning [Host] with the stop, the detail and the status. Act on it as steps 4 and 5 say. When the case must run again, end your reply with [[START_RUN]] again. On delivered the host adds the report download link to your reply, so your reply is a short cover note on Part 1 of the polished report, never a report of its own. The client never sees the file system: write no file paths, case ids or run ids, and no Sources section.
After a report has been delivered, a client message that brings back a point does not start a run: record it, say in one sentence that you have recorded it, and stop; the host then re-runs the computation and asks you to relay the preliminary result. End a reply with [[START_RUN]] after a delivered report only when the client asks for a revised report or says they need a formal document to act on."""
DELIVERED_NOTE = "The report is the deliverable. Its Part 1 (Strategy) follows between the <<< >>> lines; it is this run's report, and what you told the client about earlier runs no longer holds. Tell the client, in at most 120 words and without tables: the recommended plan, its expected tax and the range over all outcomes, any recovery or deadline Part 1 names, and the one or two points the client should confirm. Use only what Part 1 says, in its figures; add no analysis of your own and do not reproduce the report."
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?%?")
NUMBER_FIX = "These figures in your note are not in this run's report: %s; use the figures of the Part 1 text you were given only."
RELAY_FIX = "[Host] Rewrite your last note to the client. %s Call no tools. Output only the note%s."
RELAY_FALLBACK = {"delivered": "The analysis is complete and the report is ready.", "need_front": "The system needs another look at this case.",
                  "no_change": "We have recorded this. It does not change the conclusions of your report, which stands as delivered."}
CARD_NOTE = """[Host] The client's message changed the case after the last report. The program re-ran the computation on what is recorded now; its preliminary result follows as JSON between <<< >>>. Tell the client in at most 120 words, without tables: whether the recommended structure of the last report still comes first (use the plan names of that report where the JSON gives them), its tax now, and which points are still open. Say that this is a preliminary result before our review and that the report is the formal conclusion. %s Use only the figures in the JSON. Call no tools.
<<<
%s
>>>"""
CARD_REPORT = "The JSON says a revised report is due (%s): say that we are now preparing it."
CARD_WAIT = "No revised report is due yet: say that we will prepare one when the open points are settled, or sooner if the client needs a formal document or asks for it; then they only need to say so."
SETTLED_MESSAGES = {
    "rate_limited": "The run paused because the model usage limit was reached. Nothing is lost: resume it from the progress panel once the limit resets.",
    "agent_failed": "The run stopped on a system error: %s. Nothing is lost: resume it from the progress panel.",
    "revision_limit": "The run stopped after too many revision rounds: %s. Resume it from the progress panel, or send more information.",
    "system_defect": "The run stopped before the report was reviewed: a system check found a defect that affects the figures. Nothing is lost: resume it from the progress panel once the defect is fixed.",
}

app = FastAPI(title="Taxrora planning host")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
guard = threading.RLock()
signed_in = True
starting, turning, tails = set(), {}, {}


@app.middleware("http")
async def own_page_only(request, call_next):
    """A browser cannot send this header from another site without a preflight this server never answers."""
    if request.method not in ("GET", "HEAD") and not request.headers.get("x-taxrora-request"):
        return JSONResponse({"detail": "forbidden"}, status_code=403)
    return await call_next(request)


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def failure(code, status=400):
    return HTTPException(status_code=status, detail=code)


def valid_case(case_id):
    if not re.fullmatch(r"CASE-\d{8}-[0-9a-f]{6}", case_id) or not (CASES / case_id / "chat.json").exists():
        raise failure("case_not_found", 404)
    return case_id


# ------------------------------------------------------------ the chat of a case
def load(case_id):
    return json.loads((CASES / case_id / "chat.json").read_text(encoding="utf-8"))


def save(doc, touch=True):
    if touch:
        doc["revision"] += 1
        doc["updated_at"] = now()
    path = CASES / doc["id"] / "chat.json"
    fresh = path.with_suffix(".tmp")
    fresh.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    os.replace(fresh, path)


def public(doc):
    return {k: v for k, v in doc.items() if k not in ("session_id", "settled", "restarts", "held")}


def message(role, text, **extra):
    return {"id": secrets.token_hex(8), "role": role, "text": text, "at": now(), **extra}


# ------------------------------------------------------------ one turn of the front agent
class Turn:
    """A headless front turn. The stream goes to a file like every other agent's, so all of them are read the same way."""

    def __init__(self, case_id, prompt, label):
        self.case_id, self.began = case_id, time.time()
        folder = CASES / case_id / "log" / "runs"
        folder.mkdir(parents=True, exist_ok=True)
        stem = folder / ("%03d-%s" % (orch.next_output_number(folder), label))
        self.out, self.err = stem.with_suffix(".jsonl"), stem.with_suffix(".err")
        session = load(case_id).get("session_id")
        cmd = [orch.claude_bin(), "-p"] + orch.agent_flags("front") + orch.STREAM_FLAGS + [
            "--max-turns", str(FRONT_TURNS), "--allowedTools", ",".join(orch.TOOLS["front"]), "--append-system-prompt", WEB_NOTE]
        if session:
            cmd += ["--resume", session]
        with open(self.out, "wb") as out, open(self.err, "wb") as err:
            self.proc = subprocess.Popen(cmd, cwd=str(ROOT), env=orch.claude_env("front"), stdin=subprocess.PIPE, stdout=out, stderr=err)
        try:
            self.proc.stdin.write(prompt.encode("utf-8"))
            self.proc.stdin.close()
        except OSError:
            pass                                                           # it exited early; outcome() reports why
        self.tail = Tail(self.out, orch.qwen_key())

    def poll(self):
        if time.time() - self.began > orch.NODE_TIMEOUT:
            self.stop()
        return self.tail.read()

    @property
    def done(self):
        return self.proc.poll() is not None

    def stop(self):
        if not self.done:
            orch.stop_tree(self.proc)

    def outcome(self):
        """(reply, failure code) after the process ended; the session stays with the case."""
        self.tail.read()
        orch.scrub(self.out)
        orch.scrub(self.err)
        result = self.tail.result
        stderr = self.err.read_text(encoding="utf-8", errors="replace")
        code = orch.classify(self.proc.returncode, False, result, stderr)
        reply = (result.get("result") or "").strip()
        if self.tail.session_id and code is None:
            with guard:
                doc = load(self.case_id)
                doc["session_id"] = self.tail.session_id
                save(doc, touch=False)
        return reply, code or (None if reply else "agent_failed")


def report_url(case_id, run_id):
    if run_id and (CASES / case_id / "report" / run_id / "briefing.pdf").exists():
        return "/api/cases/%s/report/%s/briefing.pdf" % (case_id, run_id)
    return None


def polished(case_id, run_id):
    """This run's polished report and its Part 1 (Strategy), or empty strings."""
    p = CASES / case_id / "report" / str(run_id) / "briefing.polished.md"
    text = p.read_text(encoding="utf-8") if run_id and p.exists() else ""
    m = re.search(r"(?ms)^##\s*(?:Part\s*)?1\b.*?(?=^##\s)", text)
    return text, (m.group(0).strip() if m else "")


def numbers(text):
    """The figures a text states: amounts of three digits or more and percentages, normalised."""
    out = set()
    for n in NUMBER.findall(text):
        pct, v = n.endswith("%"), n.rstrip("%").replace(",", "").rstrip(".")
        if pct or len(v.split(".")[0]) >= 3:
            try:
                out.add(("%", float(v)) if pct else ("n", float(v)))
            except ValueError:
                pass
    return out


def unsupported(note, report):
    """The figures of a cover note the report does not state."""
    return sorted(("%g%%" % v if k == "%" else "{:,.0f}".format(v)) for k, v in numbers(note) - numbers(report))


def relay(case_id, stop):
    """A background front turn: the client hears the end of the run in the agent's own words."""
    detail = "the report is ready" if stop["stop"] == "delivered" else stop.get("detail", "")     # the model repeats whatever path it is given
    report, part1 = polished(case_id, orch.info(case_id).get("run_id")) if stop["stop"] == "delivered" else ("", "")
    prompt = ("[Host] The orchestrator ended.\nstop: %s\ndetail: %s\nstatus: %s\n" % (stop["stop"], detail, stop.get("status"))
              + (DELIVERED_NOTE + "\n<<<\n" + part1 + "\n>>>\n" if stop["stop"] == "delivered" else "")
              + "What you write next goes to the client: no file paths, case ids, run ids or system names.")
    turn = turning[case_id] = Turn(case_id, prompt, "front-relay")
    restart = False
    try:
        try:
            turn.proc.wait(timeout=orch.NODE_TIMEOUT)
        except subprocess.TimeoutExpired:
            turn.stop()
        reply, code = turn.outcome()
        restart = START in reply
        reply = client_text(reply.replace(START, ""))
        if code or not reply:
            reply = RELAY_FALLBACK[stop["stop"]]
        def faults(text):
            out = []
            wrong = unsupported(text, report) if stop["stop"] == "delivered" and report else []
            if wrong:
                out.append(NUMBER_FIX % ", ".join(wrong))
            hits = sorted({m.group(0).lower() for m in FRONT_JARGON.finditer(text)})
            if hits:
                out.append("It names system parts the client does not know (%s); say the same in plain words." % ", ".join(hits))
            return out
        found = faults(reply) if not code else []
        if found:                                                        # one rewrite; a note still at fault is replaced by the plain fallback
            fix = turning[case_id] = Turn(case_id, RELAY_FIX % (" ".join(found), ""), "front-relay-fix")
            try:
                fix.proc.wait(timeout=orch.NODE_TIMEOUT)
            except subprocess.TimeoutExpired:
                fix.stop()
            again, code2 = fix.outcome()
            again = client_text(again.replace(START, "")) if again and not code2 else ""
            reply = again if again and not faults(again) else RELAY_FALLBACK[stop["stop"]]
        if stop["stop"] == "delivered":
            url = report_url(case_id, orch.info(case_id).get("run_id"))
            reply += "\n\n[Download the report (PDF)](%s)" % url if url else ""
        with guard:
            doc = load(case_id)
            held = restart and doc.get("restarts", 0) >= AUTO_RESTARTS         # review and front must not loop unattended
            if held:
                restart = False
                reply += "\n\nThe system has sent this case back %d times without a client message, so it stopped here. Resume it from the progress panel, or send more information." % AUTO_RESTARTS
            doc["messages"].append(message("assistant", reply))
            doc["restarts"] = doc.get("restarts", 0) + 1 if restart else doc.get("restarts", 0)
            doc["held"] = held
            save(doc)
    finally:
        turning.pop(case_id, None)
    if restart:
        start_run(case_id)


def settle(case_id):
    """Say how a run ended, once for each stop."""
    stop = orch.last_stop(case_id)
    if not stop or run_active(case_id) or case_id in turning:
        return
    with guard:
        doc = load(case_id)
        if doc.get("settled") == stop["time"]:
            return
        doc["settled"] = stop["time"]
        save(doc, touch=False)
    if stop["stop"] in ("delivered", "need_front", "no_change"):
        threading.Thread(target=relay, args=(case_id, stop), daemon=True).start()
    elif stop["stop"] in SETTLED_MESSAGES:
        text = SETTLED_MESSAGES[stop["stop"]]
        with guard:
            doc = load(case_id)
            doc["messages"].append(message("assistant", text % (client_text(stop.get("detail", "")) or "see the progress panel") if "%s" in text else text))
            save(doc)


# ------------------------------------------------------------ the orchestrator
def lock_pid(case_id):
    path = CASES / case_id / "log" / "run.lock"
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return int(text) if text.isdigit() and orch.pid_alive(int(text)) else None


async def card_turn(case_id, card):
    """One more front turn that relays the preview card; its figures must be the card's. Returns (doc, start a run)."""
    due = [k for k, v in card["triggers"].items() if v["value"]]
    slim = {k: card[k] for k in ("first", "first_changed", "worst", "baseline_first_now", "pending", "triggers")}
    prompt = CARD_NOTE % (CARD_REPORT % ", ".join(card["triggers"][k]["reason"] for k in due) if due else CARD_WAIT, json.dumps(slim, ensure_ascii=False, indent=1))
    turn = turning[case_id] = Turn(case_id, prompt, "front-card")
    try:
        while not turn.done:
            turn.poll()
            await asyncio.sleep(0.3)
        reply, code = turn.outcome()
    finally:
        turning.pop(case_id, None)
    start = bool(due) or (START in (reply or ""))
    reply = client_text((reply or "").replace(START, "")) if not code else ""
    allowed = {round(v, 2) for v in orch.imp().card_figures(card)}
    wrong = sorted(n for k, n in numbers(reply) if k == "n" and round(n, 2) not in allowed and n >= 1000)
    if not reply or wrong or FRONT_JARGON.search(reply):
        reply = ("We have recorded this and re-ran the computation. The structure we recommended %s; we will confirm it in the report."
                 % ("still comes first" if not card["first_changed"] else "is no longer the first choice"))
    with guard:
        fresh = load(case_id)
        fresh["messages"].append(message("assistant", reply))
        save(fresh)
    return fresh, start


def run_active(case_id):
    return case_id in starting or lock_pid(case_id) is not None


def start_run(case_id):
    if run_active(case_id):
        return
    with guard:
        doc = load(case_id)
        doc["held"] = False
        save(doc, touch=False)
    starting.add(case_id)
    log = CASES / case_id / "log"
    log.mkdir(parents=True, exist_ok=True)
    # its own hidden console: neither Ctrl+C nor closing this server's window reaches the run
    flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with open(log / "orchestrate.out", "ab") as out, open(log / "orchestrate.err", "ab") as err:
        proc = subprocess.Popen([sys.executable, str(ROOT / "agent" / "tools" / "orchestrate.py"), "run", case_id], cwd=str(ROOT),
                                stdin=subprocess.DEVNULL, stdout=out, stderr=err, creationflags=flags)

    def watch():
        proc.wait()
        starting.discard(case_id)
        settle(case_id)

    threading.Thread(target=watch, daemon=True).start()


def log_rows(case_id):
    path = CASES / case_id / "log" / "runs.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def steps_of(cur, rows, active):
    """Every graph node with its state. A revision moves the stage back, so a later node returns to pending and keeps its history."""
    steps = [{"id": node, "agent": agent, "state": "pending", "runs": 0, "seconds": 0, "model": None, "started": None,
              "reason": "", "open": False, "failed": False} for node, agent in PIPELINE]
    index = {s["id"]: i for i, s in enumerate(steps)}
    position = 0
    for row in rows:
        if row.get("round") != cur.get("round") or row.get("node") not in index:
            continue
        step = steps[index[row["node"]]]
        if row["event"] == "start":
            position = index[row["node"]]
            step.update(runs=step["runs"] + 1, started=row["time"], open=True, failed=False, model=row.get("model"), reason=row.get("reason", ""))
        elif row["event"] == "end":
            step.update(open=False, seconds=step["seconds"] + (row.get("seconds") or 0), failed=row.get("stop") in ("rate_limited", "agent_failed"))
    delivered = cur.get("status") == "delivered"
    for i, step in enumerate(steps):
        if delivered or i < position:
            step["state"] = "done"
        elif i == position:
            if step["open"]:
                step["state"] = "running" if active else "stopped"
            elif step["failed"]:
                step["state"] = "failed"
            elif step["runs"]:
                step["state"] = "done"
        del step["open"], step["failed"]
    return steps


def blocks_of(case_id, after):
    """The agents' streams, oldest first, as one list that only grows: a cursor into it stays valid across polls and restarts."""
    folder = CASES / case_id / "log" / "runs"
    with guard:
        cache = tails.setdefault(case_id, {})
        if folder.exists():
            for path in sorted(folder.glob("*.jsonl")):
                if path.stem.split("-", 1)[1] != "front" and path not in cache:
                    cache[path] = Tail(path, orch.qwen_key())
        blocks, fresh, total = [], [], 0
        for path, tail in cache.items():
            if not path.exists():                       # archived after it was read: its items keep their place, the block goes
                total += len(tail.items)
                continue
            tail.read()
            label = path.stem.split("-", 1)[1]
            info = path.stat()
            blocks.append({"id": path.stem, "node": label, "agent": "front" if label == "front-relay" else orch.NODE_AGENT.get(label) or orch.LANE_AGENT.get(label, "program"),
                           "started": stamp(info.st_ctime), "ended": stamp(info.st_mtime) if tail.result else None})
            fresh.extend({**item, "block": path.stem} for item in merged(tail.items[max(0, after - total):]))
            total += len(tail.items)
        return blocks, fresh, total


def snapshot(case_id, after):
    settle(case_id)
    cur = orch.info(case_id)
    rows = log_rows(case_id)
    active = run_active(case_id)
    blocks, items, cursor = blocks_of(case_id, after)
    last = rows[-1] if rows else {}
    stop = {k: last.get(k) for k in ("stop", "detail", "time")} if last.get("event") == "stop" else None
    if stop:
        stop["detail"] = client_text(stop.get("detail") or "")
    steps = steps_of(cur, rows, active)
    doc = load(case_id)
    interrupted = not active and (doc.get("held") or any(s["state"] == "stopped" for s in steps))
    return {"active": active, "turning": case_id in turning, "status": cur.get("status"), "round": cur.get("round"), "revision": cur.get("revision", 0),
            "steps": steps, "stop": stop, "can_resume": interrupted or bool(not active and stop and stop["stop"] in RESUMABLE),
            "report": report_url(case_id, cur.get("run_id")) if cur.get("status") == "delivered" else None,
            "chat_revision": doc["revision"], "blocks": blocks, "items": items, "cursor": cursor}


# ------------------------------------------------------------ routes
@app.get("/api/auth/session")
def session():
    return {"configured": True, "user": USER if signed_in else None}


@app.post("/api/auth/login")
def login():
    global signed_in
    signed_in = True
    return {"user": USER}


@app.post("/api/auth/logout")
def logout():
    global signed_in
    signed_in = False
    return {}


@app.get("/api/cases")
def list_cases():
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in CASES.glob("CASE-*/chat.json")]
    return [public(d) for d in sorted(docs, key=lambda d: d["updated_at"], reverse=True)]


@app.post("/api/cases", status_code=201)
def create_case():
    case_id = "CASE-%s-%s" % (datetime.now().strftime("%Y%m%d"), secrets.token_hex(3))
    if orch.case().case_new(case_id).get("error"):
        raise failure("storage_unavailable", 503)
    at = now()
    doc = {"id": case_id, "title": "", "revision": 0, "messages": [], "created_at": at, "updated_at": at}
    save(doc, touch=False)
    return public(doc)


@app.get("/api/cases/{case_id}")
def get_case(case_id):
    return public(load(valid_case(case_id)))


@app.patch("/api/cases/{case_id}/organization")
async def organize(case_id, request: Request):
    body = await request.json()
    with guard:
        doc = load(valid_case(case_id))
        if body.get("revision") != doc["revision"]:
            raise failure("revision_conflict", 409)
        if isinstance(body.get("title"), str):
            doc["title"] = body["title"].strip()[:120]
        if isinstance(body.get("archived"), bool):
            doc["archived"] = body["archived"]
        save(doc)
    return public(doc)


def client_prompt(case_id, doc, text):
    """The words for the agent; an attachment goes into the case first."""
    words, _, raw = text.partition(ATTACHMENT)
    note = ""
    if raw:
        try:
            files = json.loads(raw)
            files = files if isinstance(files, list) else [files]
            sources = [UPLOADS / re.fullmatch(r"[0-9a-f]{32}", f["id"]).group() / Path(f["name"]).name for f in files]
        except (ValueError, KeyError, TypeError, AttributeError):
            raise failure("attachment_invalid")
        for source in sources:
            if orch.case().put_document(case_id, source.name, src_path=str(source)).get("error"):
                raise failure("attachment_invalid")
        note = "\n\n[The client attached %s; they are in cases/%s/intake/documents/.]" % (", ".join(s.name for s in sources), case_id)
    head = "" if doc.get("session_id") else "Case id: %s.\n" % case_id
    return "%sThe client says:\n%s%s" % (head, words, note), words


def sse(**event):
    return "data: %s\n\n" % json.dumps(event, ensure_ascii=False)


@app.post("/api/cases/{case_id}/messages")
async def send_message(case_id, request: Request):
    body = await request.json()
    text = str(body.get("text") or "")
    doc = load(valid_case(case_id))
    if body.get("revision") != doc["revision"]:
        raise failure("revision_conflict", 409)
    if case_id in turning or run_active(case_id):
        raise failure("run_active", 409)
    prompt, words = client_prompt(case_id, doc, text)
    orch.case().client_said(case_id, words)
    turn = turning[case_id] = Turn(case_id, prompt, "front")

    async def events():
        said, sent, process, closed = "", 0, [], False
        try:
            while True:
                finished = turn.done
                for item in turn.poll():
                    if item["kind"] != "text":
                        process.append(item)
                        yield sse(type="activity", item=item)
                        continue
                    if item.get("start") and said.strip():               # what it said before a tool call belongs to the process
                        process.append({"kind": "text", "text": said, "start": True})
                        yield sse(type="activity", item=process[-1])
                        yield sse(type="reset")
                        said, sent = "", 0
                    said += item["text"]
                safe = max(0, len(said) - len(START))                     # the end of the text may be the start mark
                leak = LEAK.search(said)
                safe = min(safe, leak.start()) if leak else safe          # the stored reply replaces the stream, without it
                if safe > sent:
                    yield sse(type="delta", text=said[sent:safe])
                    sent = safe
                if finished:
                    break
                await asyncio.sleep(0.15)
            reply, code = turn.outcome()
            if code:
                turning.pop(case_id, None)
                closed = True
                yield sse(type="error", code=code)
                return
            start = START in reply
            reply = client_text(reply.replace(START, "")) or "Noted."
            hits = sorted({m.group(0).lower() for m in FRONT_JARGON.finditer(reply)})
            if hits:                                                      # one rewrite in the same session; the client keeps the plain one
                fix = turning[case_id] = Turn(case_id, REWRITE % (", ".join(hits), ", ending with the line %s as before" % START if start else ""), "front-wording")
                while not fix.done:
                    fix.poll()
                    await asyncio.sleep(0.3)
                again, code2 = fix.outcome()
                plain = client_text(again.replace(START, "")) if again and not code2 else ""
                if plain and not FRONT_JARGON.search(plain):
                    reply = plain
                    yield sse(type="reset")
                    yield sse(type="delta", text=reply)
            with guard:
                fresh = load(case_id)
                fresh["title"] = fresh["title"] or " ".join(re.sub(r"[*_#`>]", "", words).split())[:40]
                fresh["restarts"], fresh["held"] = 0, False
                fresh["messages"].append(message("user", text))
                fresh["messages"].append(message("assistant", reply, activity=merged(process), seconds=round(time.time() - turn.began)))
                save(fresh)
            turning.pop(case_id, None)
            closed = True
            if not start and not run_active(case_id):
                card, why = await asyncio.to_thread(orch.preview, case_id)
                if card:
                    fresh, start = await card_turn(case_id, card)
            if start:
                start_run(case_id)
            yield sse(type="done", case=public(fresh))
        finally:
            if not closed:                                                # the client pressed stop or left
                turn.stop()
                turning.pop(case_id, None)

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.post("/api/attachments")
async def attachment(request: Request, filename: str = ""):
    name = Path(filename.replace("\\", "/")).name
    suffix = Path(name).suffix.lower()
    if suffix not in UPLOAD_TYPES:
        raise failure("attachment_type")
    data = await request.body()
    if len(data) > UPLOAD_LIMIT:
        raise failure("pdf_too_large", 413)
    token = secrets.token_hex(16)
    (UPLOADS / token).mkdir(parents=True)
    (UPLOADS / token / name).write_bytes(data)
    return {"id": token, "name": name, "kind": UPLOAD_TYPES[suffix], "page_count": 1, "pages": [{"page": 1, "text": ""}], "empty_pages": []}


@app.get("/api/cases/{case_id}/run")
def run_state(case_id, after: int = 0):
    return snapshot(valid_case(case_id), max(0, after))


@app.post("/api/cases/{case_id}/run")
def resume_run(case_id):
    valid_case(case_id)
    if case_id in turning:
        raise failure("run_active", 409)
    start_run(case_id)
    return {"started": True}


@app.post("/api/cases/{case_id}/run/stop")
def stop_run(case_id):
    valid_case(case_id)
    pid = lock_pid(case_id)
    if pid:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        else:
            os.kill(pid, 15)
        (CASES / case_id / "log" / "run.lock").unlink(missing_ok=True)
        orch.log_row(case_id, event="stop", stop="stopped", detail="stopped from the web page", status=orch.info(case_id).get("status"), nodes=[])
    return {"stopped": bool(pid)}


@app.get("/api/cases/{case_id}/report/{run_id}/briefing.pdf")
def report(case_id, run_id):
    valid_case(case_id)
    path = CASES / case_id / "report" / run_id / "briefing.pdf"
    if not re.fullmatch(r"[\w-]+", run_id) or not path.exists():
        raise failure("case_not_found", 404)
    return FileResponse(path, media_type="application/pdf", filename="briefing.pdf")


if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("TAXRORA_PORT", 8000)))
