"""Cobrand sync (agent-browser)

Runs a Cobrand → CSV sync using the agent-browser daemon.

Outputs tracker-format campaign CSVs to: output/campaigns/

Assumptions / heuristics (tuned for Jake's Cobrand):
- Promotions list is paginated; we scan up to MAX_PROMO_PAGES.
- If multiple promos exist for the same campaign (e.g., Round 1 + Round 2), we prefer promos whose name contains RD2 / ROUND 2.
- TikTok sound IDs come from Notion CRM export mapping (config/campaign_sounds.json created from CRM export).

This is intentionally defensive: if we can't identify a campaign's sound ID(s), we skip writing a CSV and report it.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(r"C:\Users\jakeb\OneDrive\Desktop\Tracker-Warner-jake-onboarding")
AGENT_BROWSER_PROFILE = r"C:\Users\jakeb\.openclaw\browser\openclaw\user-data"

ORG_ID = "652c1528-f525-4c80-be5d-fda2aa6005fd"
PROMOTIONS_URL = f"https://music.cobrand.com/promote/?oid={ORG_ID}"

MAX_PROMO_PAGES = 5

OUTPUT_DIR = PROJECT_ROOT / "output" / "campaigns"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CAMPAIGN_SOUNDS_JSON = PROJECT_ROOT / "config" / "campaign_sounds.json"

PROMO_NAME_RE = re.compile(r"^\s*(?:[☑✅]+\s*)?(?P<artist>.+?)\s+\"(?P<song>.+?)\"\s+Promo\s*$", re.IGNORECASE)


@dataclass
class Promo:
    name: str
    href: str
    status: str
    created: str

    @property
    def url(self) -> str:
        if self.href.startswith("http"):
            return self.href
        return f"https://music.cobrand.com{self.href}"


def _run_agent_browser(args: list[str], *, timeout: int = 180) -> subprocess.CompletedProcess:
    # Call the PowerShell shim directly to avoid cmd.exe quoting issues (esp. for multi-line JS).
    ab_ps1 = r"C:\Users\jakeb\AppData\Roaming\npm\agent-browser.ps1"
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        ab_ps1,
        "--profile",
        AGENT_BROWSER_PROFILE,
    ] + args
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)


def ab_open(url: str) -> None:
    p = _run_agent_browser(["open", url], timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f"agent-browser open failed: {p.stderr or p.stdout}")


def ab_eval(js: str) -> str:
    p = _run_agent_browser(["eval", js], timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f"agent-browser eval failed: {p.stderr or p.stdout}")
    return (p.stdout or "").strip()


def _json(s: str):
    """agent-browser eval sometimes returns JSON as a JSON-encoded string; normalize."""
    obj = json.loads(s)
    if isinstance(obj, str):
        obj = json.loads(obj)
    return obj


def _safe_filename(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9 _\-]", "", s)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s[:120] or "campaign"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def _norm_loose(s: str) -> str:
    # Looser normalization for fuzzy matching across systems.
    # Key detail: remove apostrophes so "it's" matches "its".
    s = _norm(s)
    s = s.replace("’", "'").replace("“", '"').replace("”", '"')
    s = s.replace("'", "")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_campaign_sound_map() -> dict[tuple[str, str], list[str]]:
    """Return mapping: (artist_norm, song_norm) -> [sound_id, ...]

    Note: we keep this strict; fuzzy matching is handled separately.
    """
    if not CAMPAIGN_SOUNDS_JSON.exists():
        raise FileNotFoundError(f"Missing {CAMPAIGN_SOUNDS_JSON}. Generate it from Notion export first.")

    raw = json.loads(CAMPAIGN_SOUNDS_JSON.read_text(encoding="utf-8"))

    # campaign_sounds.json is sound_id -> [campaign dicts]
    out: dict[tuple[str, str], list[str]] = {}
    for sound_id, campaigns in raw.items():
        for c in campaigns:
            artist = _norm(c.get("artist", ""))
            song = _norm(c.get("song", ""))
            if not artist or not song:
                continue
            out.setdefault((artist, song), [])
            if sound_id not in out[(artist, song)]:
                out[(artist, song)].append(sound_id)
    return out


def parse_promo_artist_song(promo_name: str) -> tuple[str, str] | None:
    m = PROMO_NAME_RE.match(promo_name)
    if not m:
        return None
    return m.group("artist").strip(), m.group("song").strip()


def scan_promotions_pages(max_pages: int = MAX_PROMO_PAGES) -> list[Promo]:
    """Open promotions list and scan up to max_pages using the next-page arrow."""
    ab_open(PROMOTIONS_URL)

    promos: list[Promo] = []

    extract_js = r"""(() => {
      const rows = Array.from(document.querySelectorAll('[role=row]'));
      const out = [];
      for (const r of rows) {
        const a = Array.from(r.querySelectorAll('a')).find(x => (x.getAttribute('href')||'').includes('/promote/'));
        if (!a) continue;
        const name = (a.innerText||'').trim().split('\n')[0];
        const href = a.getAttribute('href');
        const txt = (r.innerText||'').trim();
        // Heuristic: status appears as a single word line (Active/Archived/etc)
        const lines = txt.split('\n').map(x=>x.trim()).filter(Boolean);
        const status = lines.find(x => ['Active','Archived','Paused','Complete','Completed'].includes(x)) || '';
        const created = lines.find(x => /^\w{3} \d{1,2}, \d{4}$/.test(x)) || '';
        out.push({name, href, status, created});
      }
      return JSON.stringify(out);
    })()"""

    next_btn_js = r"""(() => {
      const b = Array.from(document.querySelectorAll('button')).find(x => (x.className||'').toString().includes('cursor-pointer') && (x.className||'').toString().includes('fill-slate-500'));
      if (!b || b.disabled) return JSON.stringify({clicked:false});
      b.click();
      return JSON.stringify({clicked:true});
    })()"""

    wait_rows_js = r"""(async () => {
      const sleep = (ms) => new Promise(r => setTimeout(r, ms));
      for (let i=0;i<30;i++) {
        const n = document.querySelectorAll('[role=row]').length;
        if (n > 0) return JSON.stringify({ok:true,n});
        await sleep(400);
      }
      return JSON.stringify({ok:false, n: document.querySelectorAll('[role=row]').length});
    })()"""

    for page in range(1, max_pages + 1):
        wait = _json(ab_eval(wait_rows_js))
        if not wait.get("ok"):
            break

        page_promos = _json(ab_eval(extract_js))
        for p in page_promos:
            promos.append(Promo(
                name=p.get("name", ""),
                href=p.get("href", ""),
                status=p.get("status", ""),
                created=p.get("created", ""),
            ))

        if page == max_pages:
            break

        click_res = _json(ab_eval(next_btn_js))
        if not click_res.get("clicked"):
            break

        # small settle time
        ab_eval("(async()=>{await new Promise(r=>setTimeout(r,800)); return 'ok';})()")

    # De-dupe by href
    uniq: dict[str, Promo] = {}
    for p in promos:
        if p.href:
            uniq[p.href] = p
    return list(uniq.values())


def choose_promos(promos: list[Promo]) -> list[Promo]:
    """De-dupe promos by (artist,song) and prefer RD2/Round 2."""
    grouped: dict[tuple[str, str], list[Promo]] = {}

    for p in promos:
        parsed = parse_promo_artist_song(p.name)
        if not parsed:
            continue
        artist, song = parsed
        grouped.setdefault((_norm(artist), _norm(song)), []).append(p)

    chosen: list[Promo] = []
    for _, plist in grouped.items():
        # prefer RD2
        rd2 = [p for p in plist if re.search(r"\b(RD\s*2|ROUND\s*2)\b", p.name, re.IGNORECASE)]
        if rd2:
            chosen.append(sorted(rd2, key=lambda x: x.created)[-1])
            continue
        # otherwise prefer Active over Archived
        active = [p for p in plist if _norm(p.status) == "active"]
        if active:
            chosen.append(sorted(active, key=lambda x: x.created)[-1])
            continue
        chosen.append(sorted(plist, key=lambda x: x.created)[-1])

    # Also keep promos that don't match naming convention but might matter later
    return chosen


def scrape_creators_from_promo(promo_url: str) -> list[dict[str, Any]]:
    """Return list of {username, done, owed}. Uses scrolling until stable."""
    ab_open(promo_url)

    scrape_js = r"""(async () => {
      const sleep=(ms)=>new Promise(r=>setTimeout(r,ms));
      const getBtnRows = () => {
        const rows = Array.from(document.querySelectorAll('[role=row]'));
        const texts = [];
        for (const row of rows) {
          const t = (row.innerText||'').trim();
          if (!t) continue;
          // Paid/booked creators have a dollar amount on the row.
          if (!t.includes('$')) continue;
          // Include both booked (Hired) and in-flight (Live Post) rows.
          if (!(t.includes('Hired') || t.includes('Live Post'))) continue;
          texts.push(t);
        }
        return [...new Set(texts)];
      };

      const findScrollParent = (el) => {
        let cur = el;
        for (let i=0;i<12 && cur;i++) {
          const st = window.getComputedStyle(cur);
          const oy = st.overflowY;
          if ((oy==='auto' || oy==='scroll') && cur.scrollHeight > cur.clientHeight + 10) return cur;
          cur = cur.parentElement;
        }
        return null;
      };

      // wait for rows to render (don't require Pay Creator, Hired rows may not have that button)
      for (let i=0;i<60;i++) {
        if (getBtnRows().length) break;
        await sleep(250);
      }

      // Prefer the biggest scrollable container (virtualized lists), fallback to page scroller.
      const scrollers = Array.from(document.querySelectorAll('*')).filter(el => {
        const st = window.getComputedStyle(el);
        const oy = st.overflowY;
        return (oy==='auto' || oy==='scroll') && el.scrollHeight > el.clientHeight + 50 && el.clientHeight > 200;
      });
      const scrollEl = scrollers.sort((a,b)=>((b.scrollHeight-b.clientHeight)-(a.scrollHeight-a.clientHeight)))[0] || document.scrollingElement;

      const seen = new Set();
      let stable=0;
      for (let step=0; step<80; step++) {
        const texts = getBtnRows();
        let added=0;
        for (const t of texts) { if (!seen.has(t)) { seen.add(t); added++; } }
        if (added===0) stable++;
        else stable=0;

        if (stable>=6) break;

        // scroll down
        if (scrollEl) {
          const before = scrollEl.scrollTop;
          scrollEl.scrollTop = before + Math.max(300, Math.floor(scrollEl.clientHeight*0.8));
          await sleep(400);
          if (scrollEl.scrollTop === before) {
            // can't scroll further
            stable++;
          }
        } else {
          window.scrollBy(0, 800);
          await sleep(400);
        }
      }

      return JSON.stringify(Array.from(seen));
    })()"""

    texts = _json(ab_eval(scrape_js))

    creators: list[dict[str, Any]] = []
    for t in texts:
        lines = [ln.strip() for ln in t.split("\n") if ln.strip()]
        handle_candidates = [ln for ln in lines if re.fullmatch(r"[A-Za-z0-9_.]{2,}", ln) and ln.lower() not in {"note", "add tags", "pay creator"}]
        username = None
        if handle_candidates:
            def score(h: str) -> tuple[int, int]:
                return (
                    1 if re.search(r"[0-9_.]", h) else 0,
                    1 if h.lower() == h else 0,
                )
            username = sorted(handle_candidates, key=score, reverse=True)[0]

        m = re.search(r"Live Post\s*\((\d+)\/(\d+)\)", t)
        if m:
            done = int(m.group(1))
            owed = int(m.group(2))
        else:
            # Hired rows typically show owed as "N Live Posts".
            m2 = re.search(r"\b(\d+)\s+Live Posts\b", t)
            owed = int(m2.group(1)) if m2 else None
            done = 0 if owed is not None else None

        if username:
            creators.append({"username": username, "posts_done": done, "posts_owed": owed})

    # De-dupe by username
    uniq: dict[str, dict[str, Any]] = {}
    for c in creators:
        uniq[c["username"]] = c
    return list(uniq.values())


def write_campaign_csv(artist: str, song: str, sound_ids: list[str], creators: list[dict[str, Any]], *, needs_sound: bool = False) -> Path:
    suffix = "_NEEDS_SOUND" if needs_sound else ""
    out_path = OUTPUT_DIR / f"{_safe_filename(artist)}_{_safe_filename(song)}{suffix}.csv"
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["Account", "Song", "Artist", "Tiktok Sound ID", "Posts_Done", "Posts_Owed", "Needs_Scraping"],
        )
        w.writeheader()
        # If we don't have sound IDs yet, still write the creator roster with blank sound id.
        if not sound_ids:
            sound_ids = [""]
        for c in creators:
            for sid in sound_ids:
                w.writerow(
                    {
                        "Account": c["username"],
                        "Song": song,
                        "Artist": artist,
                        "Tiktok Sound ID": sid,
                        "Posts_Done": "" if c.get("posts_done") is None else c.get("posts_done"),
                        "Posts_Owed": "" if c.get("posts_owed") is None else c.get("posts_owed"),
                        "Needs_Scraping": ("Yes" if (c.get("posts_done") is None or c.get("posts_owed") is None or c.get("posts_done") < c.get("posts_owed")) else "No"),
                    }
                )
    return out_path


def _build_song_index(sound_map: dict[tuple[str, str], list[str]]) -> dict[str, list[str]]:
    song_index: dict[str, list[str]] = {}
    for (artist, song), ids in sound_map.items():
        song_index.setdefault(song, [])
        for sid in ids:
            if sid not in song_index[song]:
                song_index[song].append(sid)
    return song_index


def find_sound_ids(artist: str, song: str, sound_map: dict[tuple[str, str], list[str]], song_index: dict[str, list[str]]) -> list[str]:
    # 1) strict match
    ids = sound_map.get((_norm(artist), _norm(song)), [])
    if ids:
        return ids

    # 2) loose match on (artist,song)
    a2 = _norm_loose(artist)
    s2 = _norm_loose(song)
    for (a, s), cand in sound_map.items():
        if _norm_loose(a) == a2 and _norm_loose(s) == s2:
            return cand

    # 3) song-only match (only if unique)
    song_ids = song_index.get(_norm(song), [])
    if len(song_ids) == 1:
        return song_ids

    # 4) loose song-only match (unique)
    loose_matches: set[str] = set()
    for (a, s), cand in sound_map.items():
        if _norm_loose(s) == s2:
            for sid in cand:
                loose_matches.add(sid)
    if len(loose_matches) == 1:
        return list(loose_matches)

    return []


def main() -> int:
    started = datetime.now()
    print(f"[cobrand-sync] start {started.strftime('%Y-%m-%d %H:%M:%S')}")

    sound_map = load_campaign_sound_map()
    song_index = _build_song_index(sound_map)

    promos = scan_promotions_pages(MAX_PROMO_PAGES)
    chosen = choose_promos(promos)

    updated = []
    skipped = []

    for p in chosen:
        parsed = parse_promo_artist_song(p.name)
        if not parsed:
            skipped.append((p.name, "unparseable promo name"))
            continue

        artist, song = parsed
        sound_ids = find_sound_ids(artist, song, sound_map, song_index)

        try:
            creators = scrape_creators_from_promo(p.url)

            if not sound_ids:
                # Still write a creators roster so we can fill the sound later.
                out_csv = write_campaign_csv(artist, song, [], creators, needs_sound=True)
                skipped.append((p.name, "missing sound_id (wrote *_NEEDS_SOUND.csv)") )
                print(f"[needs_sound] {p.name}: {len(creators)} creators -> {out_csv.name}")
                continue

            out_csv = write_campaign_csv(artist, song, sound_ids, creators)
            updated.append((p.name, out_csv, len(creators), len(sound_ids)))
            print(f"[ok] {p.name}: {len(creators)} creators, {len(sound_ids)} sounds -> {out_csv.name}")
        except Exception as e:
            skipped.append((p.name, f"error: {e}"))

    print("\n[cobrand-sync] SUMMARY")
    print(f"Updated: {len(updated)} | Skipped: {len(skipped)}")
    for name, path, ncre, ns in updated[:10]:
        print(f"  + {name} -> {path.name} ({ncre} creators x {ns} sounds)")
    if len(updated) > 10:
        print(f"  ... {len(updated)-10} more")
    for name, why in skipped[:10]:
        print(f"  - {name}: {why}")
    if len(skipped) > 10:
        print(f"  ... {len(skipped)-10} more")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
