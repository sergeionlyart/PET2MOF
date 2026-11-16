"""Conservative, process-locked accounting: ambiguous failures are charged."""

import fcntl
import json
import os
import tempfile
import uuid
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path


class BudgetStop(RuntimeError):
    pass


def positive_decimal(value):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result <= 0:
            raise ValueError
        return result
    except Exception:
        raise BudgetStop("unknown or invalid price/budget") from None


class Ledger:
    def __init__(self, root, *, budget, page_limit, price, provider):
        self.path = Path(root) / "private" / "ocr_cache" / "ledger.json"
        self.budget = positive_decimal(budget)
        self.price = positive_decimal(price)
        if isinstance(page_limit, bool) or not isinstance(page_limit, int) or page_limit <= 0:
            raise BudgetStop("page limit required")
        if provider not in {"mistral", "google_docai"}:
            raise BudgetStop("unsupported provider")
        self.page_limit = page_limit
        self.provider = provider

    @contextmanager
    def _locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(self.path.with_suffix(".lock"), os.O_RDWR | os.O_CREAT, 0o600)
        with os.fdopen(descriptor, "a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                if self.path.exists():
                    try:
                        state = json.loads(self.path.read_text(encoding="utf-8"))
                        self._validate(state)
                    except Exception:
                        raise BudgetStop("invalid ledger; manual review required") from None
                else:
                    state = {"version": 1, "provider": self.provider, "blocked": None, "attempts": {}}
                if state["provider"] != self.provider:
                    raise BudgetStop("ledger belongs to another provider")
                yield state
                descriptor, temporary = tempfile.mkstemp(dir=self.path.parent, prefix=".ledger-")
                try:
                    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                        json.dump(state, stream, allow_nan=False)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(temporary, self.path)
                finally:
                    Path(temporary).unlink(missing_ok=True)
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    @staticmethod
    def _validate(state):
        if state["version"] != 1 or not isinstance(state["attempts"], dict):
            raise ValueError
        if state["blocked"] not in {None, "authorization", "limit", "price"}:
            raise ValueError
        for attempt in state["attempts"].values():
            if attempt["status"] not in {"reserved", "charged", "released"}:
                raise ValueError
            if type(attempt["pages"]) is not int or attempt["pages"] <= 0:
                raise ValueError
            positive_decimal(attempt["cost"])

    def reserve(self, pages):
        if type(pages) is not int or pages <= 0:
            raise BudgetStop("positive integer pages required")
        cost = self.price * pages
        denied = False
        with self._locked() as state:
            if state["blocked"]:
                raise BudgetStop("paid path stopped; review ledger")
            active = [a for a in state["attempts"].values() if a["status"] != "released"]
            total = sum((Decimal(a["cost"]) for a in active), Decimal(0))
            page_total = sum(a["pages"] for a in active)
            if total + cost > self.budget or page_total + pages > self.page_limit:
                state["blocked"] = "limit"
                denied = True
            else:
                reservation = uuid.uuid4().hex
                state["attempts"][reservation] = {"pages": pages, "cost": str(cost), "status": "reserved"}
        if denied:
            raise BudgetStop("budget or page limit reached")
        return reservation

    def confirm(self, reservation):
        self._finish(reservation, "charged")

    def release(self, reservation):
        """Only for a definite cancellation BEFORE transmission; never for a timeout."""
        self._finish(reservation, "released")

    def _finish(self, reservation, status):
        with self._locked() as state:
            attempt = state["attempts"][reservation]
            if attempt["status"] != "reserved":
                raise BudgetStop("reservation already settled")
            attempt["status"] = status

    def stop(self, reason="authorization"):
        if reason not in {"authorization", "limit", "price"}:
            raise ValueError("unknown stop reason")
        with self._locked() as state:
            state["blocked"] = reason

    def snapshot(self):
        with self._locked() as state:
            return json.loads(json.dumps(state))
