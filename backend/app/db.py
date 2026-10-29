"""SQLite persistence layer for the SAMRUDHI Agentic OS.

Deliberately dependency-light (sqlite3 + JSON columns) so the whole system
runs in a single Docker volume with zero external services.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    specialty TEXT,
    geography TEXT,
    tone TEXT,
    audience TEXT,
    channels TEXT,
    brand_do TEXT,
    brand_dont TEXT,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS deliverables (
    id TEXT PRIMARY KEY,
    client_id TEXT,
    title TEXT,
    content_type TEXT,
    topic TEXT,
    status TEXT NOT NULL,
    current_stage TEXT,
    brief TEXT,
    plan TEXT,
    research TEXT,
    strategy TEXT,
    calendar TEXT,
    copy TEXT,
    creative TEXT,
    qa_report TEXT,
    screening TEXT,
    assurance TEXT,
    published TEXT,
    report TEXT,
    improvement TEXT,
    error TEXT,
    created_at REAL,
    updated_at REAL
);

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    deliverable_id TEXT,
    stage TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    status TEXT NOT NULL,
    input_summary TEXT,
    output_summary TEXT,
    provider TEXT,
    model TEXT,
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0,
    started_at REAL,
    finished_at REAL,
    duration_ms INTEGER DEFAULT 0,
    error TEXT
);

CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    deliverable_id TEXT,
    stage TEXT,
    kind TEXT,
    status TEXT NOT NULL,
    reviewer TEXT,
    decision TEXT,
    notes TEXT,
    created_at REAL,
    decided_at REAL
);

CREATE TABLE IF NOT EXISTS evaluations (
    id TEXT PRIMARY KEY,
    deliverable_id TEXT,
    run_id TEXT,
    agent_id TEXT,
    dimension TEXT,
    score REAL,
    evidence TEXT,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS feedback (
    id TEXT PRIMARY KEY,
    deliverable_id TEXT,
    agent_id TEXT,
    run_id TEXT,
    evaluator TEXT,
    dimension TEXT,
    score REAL,
    finding TEXT,
    severity TEXT,
    evidence TEXT,
    root_cause TEXT,
    corrective_action TEXT,
    status TEXT,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS ledger (
    id TEXT PRIMARY KEY,
    deliverable_id TEXT,
    run_id TEXT,
    agent_id TEXT,
    event TEXT,
    detail TEXT,
    ts REAL
);

CREATE TABLE IF NOT EXISTS chat (
    id TEXT PRIMARY KEY,
    role TEXT,
    agent_id TEXT,
    content TEXT,
    ts REAL
);

CREATE TABLE IF NOT EXISTS workforce_cycles (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    total_agents INTEGER DEFAULT 0,
    completed_agents INTEGER DEFAULT 0,
    failed_agents INTEGER DEFAULT 0,
    started_at REAL,
    finished_at REAL,
    summary TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_deliverable ON runs(deliverable_id);
CREATE INDEX IF NOT EXISTS idx_ledger_deliverable ON ledger(deliverable_id);
CREATE INDEX IF NOT EXISTS idx_cycles_started ON workforce_cycles(started_at);
"""


class Database:
    """Thread-safe SQLite wrapper using ONE persistent connection.

    Re-opening a connection per operation is catastrophically slow on NFS
    (each open/close + WAL checkpoint round-trips the network), so we keep a
    single connection alive and serialise access with a lock.
    """

    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            try:
                yield self._conn
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    # ---------- helpers ----------
    @staticmethod
    def now() -> float:
        return time.time()

    @staticmethod
    def new_id(prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4().hex[:10]}"

    @staticmethod
    def _rows(rows: list[sqlite3.Row]) -> list[dict]:
        json_fields = {"brief"}
        out = []
        for r in rows:
            d = dict(r)
            for k in json_fields & set(d):
                v = d[k]
                if isinstance(v, str) and v[:1] in ("{", "["):
                    try:
                        d[k] = json.loads(v)
                    except (ValueError, TypeError):
                        pass
            out.append(d)
        return out

    def _json(self, v: Any) -> str | None:
        if v is None:
            return None
        return json.dumps(v, ensure_ascii=False)

    # ---------- clients ----------
    def create_client(self, **kw: Any) -> dict:
        cid = kw.pop("id", None) or self.new_id("CLT")
        kw.setdefault("created_at", self.now())
        cols = ("name", "specialty", "geography", "tone", "audience",
                "channels", "brand_do", "brand_dont")
        vals = {c: kw.get(c) for c in cols}
        vals["created_at"] = kw["created_at"]
        with self._connect() as conn:
            conn.execute(
                f"INSERT INTO clients (id, {', '.join(cols)}, created_at) "
                f"VALUES (:id, {', '.join(':' + c for c in cols)}, :created_at)",
                {"id": cid, **vals},
            )
        return self.get_client(cid)  # type: ignore[return-value]

    def get_client(self, cid: str) -> dict | None:
        with self._connect() as conn:
            r = conn.execute("SELECT * FROM clients WHERE id=?", (cid,)).fetchone()
        return dict(r) if r else None

    def list_clients(self) -> list[dict]:
        with self._connect() as conn:
            return self._rows(conn.execute(
                "SELECT * FROM clients ORDER BY created_at").fetchall())

    # ---------- deliverables ----------
    def create_deliverable(self, client_id: str, title: str,
                           content_type: str, topic: str, brief: dict) -> dict:
        did = self.new_id("DLV")
        now = self.now()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO deliverables (id, client_id, title, content_type, "
                "topic, status, current_stage, brief, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?, ?,?,?)",
                (did, client_id, title, content_type, topic, "created",
                 None, self._json(brief), now, now),
            )
        return self.get_deliverable(did)  # type: ignore[return-value]

    def get_deliverable(self, did: str) -> dict | None:
        with self._connect() as conn:
            r = conn.execute("SELECT * FROM deliverables WHERE id=?", (did,)).fetchone()
        return dict(r) if r else None

    def list_deliverables(self, client_id: str | None = None) -> list[dict]:
        q = "SELECT * FROM deliverables"
        args: tuple = ()
        if client_id:
            q += " WHERE client_id=?"
            args = (client_id,)
        q += " ORDER BY updated_at DESC"
        with self._connect() as conn:
            return self._rows(conn.execute(q, args).fetchall())

    def update_deliverable(self, did: str, **fields: Any) -> dict | None:
        if not fields:
            return self.get_deliverable(did)
        # Only these fields are stored as JSON objects; all stage outputs are
        # plain Markdown text and must be stored verbatim.
        json_cols = {"brief"}
        sets, args = [], []
        for k, v in fields.items():
            if k in json_cols:
                sets.append(f"{k}=?")
                args.append(self._json(v))
            elif k in ("status", "current_stage", "error", "title", "topic",
                       "plan", "research", "strategy", "calendar", "copy",
                       "creative", "qa_report", "screening", "assurance",
                       "published", "report", "improvement"):
                sets.append(f"{k}=?")
                args.append(v)
        if not sets:
            return self.get_deliverable(did)
        sets.append("updated_at=?")
        args.append(self.now())
        args.append(did)
        with self._connect() as conn:
            conn.execute(f"UPDATE deliverables SET {', '.join(sets)} WHERE id=?", args)
        return self.get_deliverable(did)

    # ---------- runs ----------
    def create_run(self, deliverable_id: str, stage: str, agent_id: str,
                   status: str = "running", **kw: Any) -> dict:
        rid = self.new_id("RUN")
        kw.setdefault("started_at", self.now())
        cols = ("stage", "agent_id", "status", "input_summary", "output_summary",
                "provider", "model", "tokens_in", "tokens_out", "cost_usd",
                "started_at", "finished_at", "duration_ms", "error")
        vals = {c: kw.get(c) for c in cols}
        vals["stage"] = stage
        vals["agent_id"] = agent_id
        vals["status"] = status
        with self._connect() as conn:
            conn.execute(
                f"INSERT INTO runs (id, deliverable_id, {', '.join(cols)}) "
                f"VALUES (?, ?, {', '.join(':' + c for c in cols)})",
                [rid, deliverable_id] + [vals[c] for c in cols],
            )
        return self.get_run(rid)  # type: ignore[return-value]

    def get_run(self, rid: str) -> dict | None:
        with self._connect() as conn:
            r = conn.execute("SELECT * FROM runs WHERE id=?", (rid,)).fetchone()
        return dict(r) if r else None

    def finish_run(self, rid: str, status: str, **kw: Any) -> dict | None:
        kw["status"] = status
        kw.setdefault("finished_at", self.now())
        run = self.get_run(rid)
        if run and run.get("started_at") and "finished_at" in kw:
            kw["duration_ms"] = int((kw["finished_at"] - run["started_at"]) * 1000)
        sets = ", ".join(f"{k}=?" for k in kw)
        args = list(kw.values()) + [rid]
        with self._connect() as conn:
            conn.execute(f"UPDATE runs SET {sets} WHERE id=?", args)
        return self.get_run(rid)

    def list_runs(self, deliverable_id: str | None = None,
                  agent_id: str | None = None) -> list[dict]:
        q, args = "SELECT * FROM runs", []
        conds = []
        if deliverable_id:
            conds.append("deliverable_id=?")
            args.append(deliverable_id)
        if agent_id:
            conds.append("agent_id=?")
            args.append(agent_id)
        if conds:
            q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY started_at DESC LIMIT 500"
        with self._connect() as conn:
            return self._rows(conn.execute(q, args).fetchall())

    # ---------- approvals ----------
    def create_approval(self, deliverable_id: str, stage: str, kind: str,
                        status: str = "pending", **kw: Any) -> dict:
        aid = self.new_id("APR")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO approvals (id, deliverable_id, stage, kind, status,"
                " reviewer, decision, notes, created_at, decided_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (aid, deliverable_id, stage, kind, status, kw.get("reviewer"),
                 kw.get("decision"), kw.get("notes"), self.now(), kw.get("decided_at")),
            )
        return self.get_approval(aid)  # type: ignore[return-value]

    def get_approval(self, aid: str) -> dict | None:
        with self._connect() as conn:
            r = conn.execute("SELECT * FROM approvals WHERE id=?", (aid,)).fetchone()
        return dict(r) if r else None

    def decide_approval(self, aid: str, status: str, reviewer: str,
                        notes: str = "") -> dict | None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE approvals SET status=?, reviewer=?, notes=?, decided_at=? "
                "WHERE id=?",
                (status, reviewer, notes, self.now(), aid),
            )
        return self.get_approval(aid)

    def list_approvals(self, status: str | None = None,
                       deliverable_id: str | None = None) -> list[dict]:
        q, args = "SELECT * FROM approvals", []
        conds = []
        if status:
            conds.append("status=?")
            args.append(status)
        if deliverable_id:
            conds.append("deliverable_id=?")
            args.append(deliverable_id)
        if conds:
            q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY created_at DESC LIMIT 500"
        with self._connect() as conn:
            return self._rows(conn.execute(q, args).fetchall())

    # ---------- evaluations & feedback ----------
    def add_evaluation(self, deliverable_id: str, run_id: str, agent_id: str,
                       dimension: str, score: float, evidence: str) -> dict:
        eid = self.new_id("EVAL")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO evaluations (id, deliverable_id, run_id, agent_id,"
                " dimension, score, evidence, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (eid, deliverable_id, run_id, agent_id, dimension, score,
                 evidence, self.now()),
            )
        return {"id": eid, "deliverable_id": deliverable_id, "run_id": run_id,
                "agent_id": agent_id, "dimension": dimension, "score": score,
                "evidence": evidence}

    def list_evaluations(self, deliverable_id: str | None = None,
                         agent_id: str | None = None) -> list[dict]:
        q, args = "SELECT * FROM evaluations", []
        conds = []
        if deliverable_id:
            conds.append("deliverable_id=?")
            args.append(deliverable_id)
        if agent_id:
            conds.append("agent_id=?")
            args.append(agent_id)
        if conds:
            q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY created_at DESC LIMIT 500"
        with self._connect() as conn:
            return self._rows(conn.execute(q, args).fetchall())

    def add_feedback(self, deliverable_id: str, agent_id: str, run_id: str,
                     evaluator: str, dimension: str, score: float, finding: str,
                     severity: str, evidence: str, root_cause: str,
                     corrective_action: str, status: str = "open") -> dict:
        fid = self.new_id("FB")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO feedback (id, deliverable_id, agent_id, run_id,"
                " evaluator, dimension, score, finding, severity, evidence,"
                " root_cause, corrective_action, status, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (fid, deliverable_id, agent_id, run_id, evaluator, dimension,
                 score, finding, severity, evidence, root_cause,
                 corrective_action, status, self.now()),
            )
        return {"id": fid, "deliverable_id": deliverable_id, "agent_id": agent_id,
                "run_id": run_id, "evaluator": evaluator, "dimension": dimension,
                "score": score, "finding": finding, "severity": severity,
                "evidence": evidence, "root_cause": root_cause,
                "corrective_action": corrective_action, "status": status}

    def list_feedback(self, deliverable_id: str | None = None,
                      agent_id: str | None = None) -> list[dict]:
        q, args = "SELECT * FROM feedback", []
        conds = []
        if deliverable_id:
            conds.append("deliverable_id=?")
            args.append(deliverable_id)
        if agent_id:
            conds.append("agent_id=?")
            args.append(agent_id)
        if conds:
            q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY created_at DESC LIMIT 500"
        with self._connect() as conn:
            return self._rows(conn.execute(q, args).fetchall())

    # ---------- ledger (append-only) ----------
    def log(self, deliverable_id: str, agent_id: str, event: str,
            detail: str = "", run_id: str = "") -> None:
        lid = self.new_id("LED")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO ledger (id, deliverable_id, run_id, agent_id, event,"
                " detail, ts) VALUES (?,?,?,?,?,?,?)",
                (lid, deliverable_id, run_id, agent_id, event, detail, self.now()),
            )

    def list_ledger(self, deliverable_id: str | None = None,
                    limit: int = 500) -> list[dict]:
        q, args = "SELECT * FROM ledger", []
        if deliverable_id:
            q += " WHERE deliverable_id=?"
            args.append(deliverable_id)
        q += " ORDER BY ts DESC LIMIT ?"
        args.append(limit)
        with self._connect() as conn:
            return self._rows(conn.execute(q, args).fetchall())

    # ---------- chat ----------
    def add_chat(self, role: str, content: str, agent_id: str = "") -> dict:
        cid = self.new_id("MSG")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO chat (id, role, agent_id, content, ts) VALUES (?,?,?,?,?)",
                (cid, role, agent_id, content, self.now()),
            )
        return {"id": cid, "role": role, "agent_id": agent_id,
                "content": content, "ts": self.now()}

    def list_chat(self, limit: int = 200) -> list[dict]:
        with self._connect() as conn:
            return self._rows(conn.execute(
                "SELECT * FROM chat ORDER BY ts DESC LIMIT ?", (limit,)).fetchall())[::-1]

    # ---------- workforce cycles ----------
    def create_cycle(self, total_agents: int) -> dict:
        cid = self.new_id("CYC")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO workforce_cycles (id, status, total_agents, started_at)"
                " VALUES (?,?,?,?)",
                (cid, "running", total_agents, self.now()),
            )
        return self.get_cycle(cid)  # type: ignore[return-value]

    def get_cycle(self, cid: str) -> dict | None:
        with self._connect() as conn:
            r = conn.execute("SELECT * FROM workforce_cycles WHERE id=?", (cid,)).fetchone()
        return dict(r) if r else None

    def list_cycles(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            return self._rows(conn.execute(
                "SELECT * FROM workforce_cycles ORDER BY started_at DESC LIMIT ?",
                (limit,)).fetchall())

    def bump_cycle(self, cid: str, completed: int = 0, failed: int = 0) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE workforce_cycles SET completed_agents=completed_agents+?,"
                " failed_agents=failed_agents+? WHERE id=?",
                (completed, failed, cid),
            )

    def finish_cycle(self, cid: str, status: str, summary: str = "") -> dict | None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE workforce_cycles SET status=?, finished_at=?, summary=? WHERE id=?",
                (status, self.now(), summary, cid),
            )
        return self.get_cycle(cid)

    # ---------- stats ----------
    def stats(self) -> dict:
        with self._connect() as conn:
            def one(q: str) -> int:
                return conn.execute(q).fetchone()[0]
            runs = conn.execute(
                "SELECT status, COUNT(*), COALESCE(SUM(tokens_in),0),"
                " COALESCE(SUM(tokens_out),0), COALESCE(SUM(cost_usd),0),"
                " COALESCE(SUM(duration_ms),0) FROM runs GROUP BY status").fetchall()
            by_status = {r[0]: r[1] for r in runs}
            total_runs = sum(by_status.values())
            tokens_in = sum(r[2] for r in runs)
            tokens_out = sum(r[3] for r in runs)
            cost = sum(r[4] for r in runs)
            dur = sum(r[5] for r in runs)
            dl = conn.execute(
                "SELECT status, COUNT(*) FROM deliverables GROUP BY status").fetchall()
            dl_status = {r[0]: r[1] for r in dl}
            return {
                "clients": one("SELECT COUNT(*) FROM clients"),
                "deliverables": one("SELECT COUNT(*) FROM deliverables"),
                "deliverables_by_status": dl_status,
                "runs": total_runs,
                "runs_by_status": by_status,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": round(cost, 4),
                "avg_run_ms": int(dur / total_runs) if total_runs else 0,
                "pending_approvals": one("SELECT COUNT(*) FROM approvals WHERE status='pending'"),
                "feedback_open": one("SELECT COUNT(*) FROM feedback WHERE status='open'"),
            }


_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        from .config import get_settings
        _db = Database(get_settings().db_path)
    return _db