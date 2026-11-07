from anvil import *

from ._anvil_designer import QuotaTemplate
from ... import pc


class Quota(QuotaTemplate):
    """"12 of 60 photos · 1.4 MB" with a meter (admins have no limit: no meter)."""

    def __init__(self, **properties):
        self._q, self._ready = None, False
        super().__init__(**properties)
        self._ready = True
        self._draw()

    def _draw(self):
        q = self._q
        if not self._ready or not q:
            return
        n = self.dom_nodes
        n["used"].textContent = str(q.get("used") or 0)
        n["size"].textContent = pc.kb(q.get("bytes") or 0)
        limit = q.get("max")
        n["of"].textContent = (" of %d photos" % limit) if limit else " photos"
        pc.show(n["meter"], bool(limit))
        if limit:
            pct = min(100, int(round(100.0 * (q.get("used") or 0) / limit)))
            n["bar"].style.width = "%d%%" % pct
            n["meter"].setAttribute("role", "img")
            n["meter"].setAttribute("aria-label", "%d%% of your photo drawer used" % pct)

    @property
    def quota(self):
        return self._q

    @quota.setter
    def quota(self, value):
        self._q = value
        self._draw()
