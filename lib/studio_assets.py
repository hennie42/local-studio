#!/usr/bin/env python3
"""Asset library core (see docs/assets-design.md and docs/assets.md): the local index, the source adapters, and the
project side (proposals, approvals, fetch, manifest, credits). The CLI is bin/studio-assets.

Library layout under STUDIO_ASSET_HOME:
  index.db                 SQLite: one row per asset (and per pack, kind "pack"); FTS5 search over name/tags/pack
  mirror/<source>/<pack>/  Kenney and KayKit packs (no API: mirrored, indexed per file)
  cache/<source>/<id>/<res>/  API assets (Poly Haven, ambientCG), downloaded when first approved, then reused
  thumbs/<source>/...      rendered model thumbnails and cached remote previews
  taste.json               every yes/no from reviews, read before proposals
  sync.log, state.json     weekly sync log and per-source state

Project layout (Godot or Unreal project dir):
  assets/<source>/<pack>/...     fetched files (git LFS)
  assets/ASSETS.json             manifest: source, URL, licence as checked, date and sha256 per file
  assets/proposals/*.json        proposals and their decisions
  assets/style.json              style lock and default resolution
  CREDITS.md                     generated from the manifest

Licences: CC0 only. Each pack's/asset's licence is read from the source at sync time (Kenney/KayKit: the pack's
licence text or page; API sources: their CC0 terms) and recorded with the date; anything not CC0 is not indexed.
"""
import datetime
import hashlib
import json
import os
import pathlib
import re
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from studio_config import cfg  # noqa: E402

STUDIO = pathlib.Path(__file__).resolve().parents[1]
HOME = pathlib.Path(cfg.get("STUDIO_ASSET_HOME") or pathlib.Path.home() / "StudioProjects/assets").expanduser()
UA = "local-studio-assets/1.0 (personal CC0 asset index; https://github.com/hennie42/local-studio)"
KINDS = ("model", "texture", "material", "hdri", "sprite", "tileset", "ui", "sound", "pack")
RES = ("1k", "2k", "4k")
TODAY = lambda: datetime.date.today().isoformat()  # noqa: E731


def log(msg):
    HOME.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.datetime.now().isoformat(timespec='seconds')} {msg}"
    print(msg, flush=True)
    with open(HOME / "sync.log", "a") as f:
        f.write(line + "\n")


# ------------------------------------------------------------------------------------------------- http
_last = {}


def http(url, method="GET", data=None, headers=None, polite=1.0, tries=4, raw=False):
    """GET/POST with our User-Agent, a per-host delay (polite seconds) and retries on 5xx/timeouts."""
    host = urllib.parse.urlparse(url).netloc
    wait = polite - (time.time() - _last.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    h = {"User-Agent": UA, **(headers or {})}
    for i in range(tries):
        try:
            _last[host] = time.time()
            r = urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h, method=method), timeout=60)
            return r if raw else r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < tries - 1:
                time.sleep(int(e.headers.get("Retry-After") or 0) or 30 * (i + 1))
                continue
            if e.code < 500 or i == tries - 1:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if i == tries - 1:
                raise
        time.sleep(2 ** i * 2)


def http_json(url, **kw):
    return json.loads(http(url, **kw))


def download(url, dest, polite=0.5):
    dest = pathlib.Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with http(url, raw=True, polite=polite) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    tmp.replace(dest)
    return dest


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------- index
SCHEMA = """
create table if not exists assets (
  id text primary key, source text, pack text, name text, kind text, category text, tags text, style text,
  license text, license_note text, license_checked text, page_url text,
  path text,          -- mirrored file relative to HOME (Kenney/KayKit), null for API assets
  remote text,        -- json: what fetch needs for API assets
  thumb text,         -- relative path under HOME or an https URL
  dims_m text,        -- json [x, y, z] in metres (glTF axes: y up), if known
  tris integer, bytes integer, updated text);
create virtual table if not exists fts using fts5(id unindexed, name, tags, pack, kind, category, style);
create table if not exists meta (key text primary key, value text);
"""


def db():
    HOME.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(HOME / "index.db")
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c


COLS = ("id", "source", "pack", "name", "kind", "category", "tags", "style", "license", "license_note",
        "license_checked", "page_url", "path", "remote", "thumb", "dims_m", "tris", "bytes", "updated")


def upsert(c, rows):
    for r in rows:
        r = {k: r.get(k) for k in COLS}
        for k in ("remote", "dims_m"):
            if r[k] is not None and not isinstance(r[k], str):
                r[k] = json.dumps(r[k])
        if isinstance(r["tags"], (list, tuple)):
            r["tags"] = " ".join(sorted({t.lower() for t in r["tags"] if t}))
        r["updated"] = r["updated"] or TODAY()
        c.execute(f"insert or replace into assets ({','.join(COLS)}) values ({','.join('?' * len(COLS))})",
                  [r[k] for k in COLS])
        c.execute("delete from fts where id = ?", (r["id"],))
        c.execute("insert into fts (id, name, tags, pack, kind, category, style) values (?,?,?,?,?,?,?)",
                  (r["id"], r["name"], r["tags"] or "", r["pack"] or "", r["kind"], r["category"] or "", r["style"] or ""))


def drop_source(c, source, keep_ids=None):
    """Remove a source's rows that the latest sync did not see (withdrawn assets, licence changes)."""
    ids = [r[0] for r in c.execute("select id from assets where source = ?", (source,))]
    gone = [i for i in ids if keep_ids is None or i not in keep_ids]
    for i in gone:
        c.execute("delete from assets where id = ?", (i,))
        c.execute("delete from fts where id = ?", (i,))
    return len(gone)


def get(c, asset_id):
    r = c.execute("select * from assets where id = ?", (asset_id,)).fetchone()
    return dict(r) if r else None


def search(c, query="", kind=None, source=None, style=None, pack=None, limit=40):
    where, args = [], []
    if query.strip():
        terms = [re.sub(r"[^\w-]", "", t) for t in query.split()]
        fts = " ".join(f'"{t}"*' for t in terms if t)
        where.append("a.id in (select id from fts where fts match ?)")
        args.append(fts)
    for col, val in (("kind", kind), ("source", source), ("pack", pack)):
        if val:
            where.append(f"a.{col} = ?"); args.append(val)
    if style:
        where.append("a.style like ?"); args.append(f"%{style}%")
    sql = "select a.* from assets a" + (" where " + " and ".join(where) if where else "")
    sql += " order by (a.kind = 'pack') desc, a.pack, a.name limit ?"
    return [dict(r) for r in c.execute(sql, args + [limit])]


def stats(c):
    return [dict(r) for r in c.execute(
        "select source, kind, count(*) n, sum(coalesce(bytes,0)) bytes from assets group by source, kind order by source, kind")]


# ------------------------------------------------------------------------------------------------- glTF helpers
def glb_json(p):
    b = pathlib.Path(p).read_bytes()
    if b[:4] == b"glTF":
        n = struct.unpack_from("<I", b, 12)[0]
        return json.loads(b[20:20 + n])
    return json.loads(b)  # .gltf


def gltf_deps(p):
    """External files a .glb/.gltf references (textures, .bin), relative to its folder."""
    j = glb_json(p)
    uris = [x.get("uri") for x in j.get("images", []) + j.get("buffers", [])]
    return [urllib.parse.unquote(u) for u in uris if u and not u.startswith("data:")]


# ------------------------------------------------------------------------------------------------- sources
ONLY = {x for x in os.environ.get("STUDIO_ASSETS_ONLY", "").split(",") if x}  # tests: limit mirrored packs


class Source:
    name = ""
    mirrored = False

    def sync(self, c):
        raise NotImplementedError

    def fetch(self, row, res):
        """Returns [(local file, path inside the project's assets/<source>/<pack>/ folder, url)]."""
        raise NotImplementedError


class PolyHaven(Source):
    """api.polyhaven.com (no key, unique User-Agent). Models (glTF), textures (PBR maps), HDRIs. CC0."""
    name = "polyhaven"
    API = "https://api.polyhaven.com"
    TYPES = {"models": "model", "textures": "texture", "hdris": "hdri"}

    def sync(self, c):
        seen = set()
        for t, kind in self.TYPES.items():
            data = http_json(f"{self.API}/assets?t={t}")
            rows = []
            for key, a in data.items():
                aid = f"polyhaven:{key}"
                seen.add(aid)
                dims = a.get("dimensions")
                rows.append({
                    "id": aid, "source": self.name, "pack": t, "name": a.get("name", key), "kind": kind,
                    "category": "/".join(a.get("categories", [])[:3]), "tags": a.get("tags", []) + a.get("categories", []),
                    "style": "photoreal", "license": "CC0", "license_note": "Poly Haven: all assets CC0; credit appreciated",
                    "license_checked": TODAY(), "page_url": f"https://polyhaven.com/a/{key}",
                    "remote": {"key": key, "type": t},
                    "thumb": f"https://cdn.polyhaven.com/asset_img/thumbs/{key}.png?width=256&height=256",
                    "dims_m": [round(d / 1000, 3) for d in dims] if dims and kind == "model" else None,
                    "tris": a.get("polycount")})
            upsert(c, rows)
            log(f"polyhaven: {len(rows)} {t}")
        c.execute("insert or replace into meta values ('polyhaven_terms', ?)", (TODAY(),))
        return seen

    def fetch(self, row, res):
        key, t = json.loads(row["remote"])["key"], json.loads(row["remote"])["type"]
        files = http_json(f"{self.API}/files/{key}")
        out = []
        dest = HOME / "cache/polyhaven" / key / res

        def get_file(f, rel):
            p = dest / rel
            if not p.exists() or (f.get("md5") and hashlib.md5(p.read_bytes()).hexdigest() != f["md5"]):
                download(f["url"], p)
            out.append((p, f"{key}/{rel}", f["url"]))

        if t == "models":
            g = files["gltf"].get(res) or files["gltf"][sorted(files["gltf"])[0]]
            get_file(g["gltf"], f"{key}.gltf")
            for rel, f in g["gltf"].get("include", {}).items():
                get_file(f, rel)
        elif t == "hdris":
            h = files["hdri"].get(res) or files["hdri"]["1k"]
            get_file(h["hdr"], f"{key}_{res}.hdr")
        else:
            for m in ("Diffuse", "nor_gl", "Rough", "arm", "AO", "Displacement"):
                if m in files and res in files[m]:
                    fmt = "png" if "png" in files[m][res] and m in ("nor_gl", "Displacement") else "jpg"
                    f = files[m][res][fmt]
                    get_file(f, f"{key}_{m.lower()}_{res}.{fmt}")
        return out


class AmbientCG(Source):
    """ambientcg.com/api/v2/full_json (no key). PBR materials and HDRIs. CC0."""
    name = "ambientcg"
    API = "https://ambientcg.com/api/v2/full_json"

    def sync(self, c):
        seen, rows, offset = set(), [], 0
        while True:
            q = urllib.parse.urlencode({"type": "Material,HDRI", "limit": 250, "offset": offset,
                                        "include": "tagData,previewData,dimensionsData,downloadData"})
            d = http_json(f"{self.API}?{q}")
            found = d.get("foundAssets", [])
            for a in found:
                if not isinstance(a, dict) or "assetId" not in a:
                    continue
                aid = f"ambientcg:{a['assetId']}"
                seen.add(aid)
                kind = "hdri" if a.get("dataType") == "HDRI" else "material"
                downloads = {}
                folders = a.get("downloadFolders") or {}
                for folder in (folders.values() if isinstance(folders, dict) else folders):
                    cats = folder.get("downloadFiletypeCategories") or {}
                    for cat in (cats.values() if isinstance(cats, dict) else cats):
                        for dl in cat.get("downloads", []):
                            downloads[dl.get("attribute")] = {"url": dl.get("downloadLink") or dl.get("fullDownloadPath"),
                                                              "size": dl.get("size")}
                prev = a.get("previewImage") or {}
                prev = prev if isinstance(prev, dict) else {}
                dims = [a.get("dimensionX"), a.get("dimensionY"), a.get("dimensionZ")]
                rows.append({
                    "id": aid, "source": self.name, "pack": a.get("displayCategory") or kind, "name": a.get("displayName"),
                    "kind": kind, "category": a.get("displayCategory"), "tags": a.get("tags", []), "style": "photoreal",
                    "license": "CC0", "license_note": "ambientCG: all assets CC0", "license_checked": TODAY(),
                    "page_url": a.get("shortLink") or f"https://ambientcg.com/view?id={a['assetId']}",
                    "remote": {"key": a["assetId"], "downloads": downloads},
                    "thumb": prev.get("256-PNG") or prev.get("128-PNG") or next(iter(prev.values()), None),
                    "dims_m": [round(x / 100, 2) if x else 0 for x in dims] if any(dims) else None})
            offset += len(found)
            if not found or offset >= d.get("numberOfResults", 0):
                break
        upsert(c, rows)
        log(f"ambientcg: {len(rows)} materials/HDRIs")
        return seen

    def fetch(self, row, res):
        r = json.loads(row["remote"])
        key, dls = r["key"], r["downloads"]
        want = {"1k": "1K", "2k": "2K", "4k": "4K"}[res]
        attr = next((a for a in (f"{want}-JPG", f"{want}-PNG", f"{want}", f"{want}-HDR") if a in dls), None) \
            or next((a for a in dls if a.startswith(want)), None) or sorted(dls)[0]
        dest = HOME / "cache/ambientcg" / key / res
        z = dest / f"{key}_{attr}.zip"
        if not z.exists():
            download(dls[attr]["url"], z)
        out = []
        with zipfile.ZipFile(z) as zf:
            for n in zf.namelist():
                if n.endswith("/") or n.lower().endswith((".usda", ".usdc", ".mtlx", ".blend")):
                    continue
                p = dest / "files" / n
                if not p.exists():
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(zf.read(n))
                out.append((p, f"{key}/{n}", dls[attr]["url"]))
        return out


class MirroredSource(Source):
    """Pack sources without an API: each pack zip is mirrored (only the useful formats are kept) and every file is
    indexed. Licence text checked per pack; non-CC0 packs are skipped and logged."""
    mirrored = True
    KEEP = (".glb", ".gltf", ".bin", ".png", ".jpg", ".jpeg", ".ogg", ".wav", ".mp3", ".tsx", ".tmx", ".txt", ".xml", ".json")
    SKIP_DIRS = ("fbx", "obj format", "vector", "font", "construct", "__macosx", "source", "unity", "godot", "blend")

    def mirror_pack(self, slug, zip_url, version):
        dest = HOME / "mirror" / self.name / slug
        stamp = dest / ".version"
        if stamp.exists() and stamp.read_text() == version:
            return dest, False
        with tempfile.TemporaryDirectory() as td:
            z = pathlib.Path(urllib.parse.unquote(zip_url[7:])) if zip_url.startswith("file://") \
                else download(zip_url, pathlib.Path(td) / "pack.zip")
            tmp = dest.with_name(slug + ".new")
            shutil.rmtree(tmp, ignore_errors=True)
            with zipfile.ZipFile(z) as zf:
                for n in zf.namelist():
                    low = n.lower()
                    licence = low.endswith(("license.txt", "licence.txt"))
                    # prefix match on folder names ("fbx(unity)", "Source files"); a substring test would drop
                    # e.g. KayKit_ResourceBits ("source")
                    in_skipped_dir = any(part.startswith(d) for part in low.split("/")[:-1] for d in self.SKIP_DIRS)
                    if n.endswith("/") or not licence and (in_skipped_dir or not low.endswith(self.KEEP)):
                        continue
                    p = tmp / n
                    if not p.resolve().is_relative_to(tmp.resolve()):
                        continue  # zip-slip guard
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(zf.read(n))
            # flatten a single top-level folder
            kids = [k for k in tmp.iterdir()] if tmp.exists() else []
            if len(kids) == 1 and kids[0].is_dir():
                inner = kids[0]
                for k in list(inner.iterdir()):
                    k.rename(tmp / k.name)
                inner.rmdir()
            shutil.rmtree(dest, ignore_errors=True)
            if tmp.exists():
                tmp.rename(dest)
            else:
                dest.mkdir(parents=True)
        stamp.write_text(version)
        return dest, True

    @staticmethod
    def licence_of(pack_dir):
        txt = ""
        for p in list(pack_dir.glob("*icen*e*.txt")) + list(pack_dir.glob("*/*icen*e*.txt")):
            txt += p.read_text(errors="replace")
        ok = bool(re.search(r"CC0|Creative Commons Zero|publicdomain/zero", txt, re.I))
        return ok, " ".join(txt.split())[:300]

    def index_pack(self, c, slug, pack_dir, meta):
        """One row per useful file plus one pack row. meta: name, category, tags, style, page, license_note, preview."""
        rows, seen = [], set()
        files = sorted(p for p in pack_dir.rglob("*") if p.is_file())
        previews = {p.stem.lower(): p for p in files if "preview" in str(p.parent).lower() and p.suffix == ".png"}
        sheetish = re.compile(r"tilemap|tilesheet|spritesheet|sheet|atlas", re.I)
        for p in files:
            rel = p.relative_to(pack_dir)
            low, parts = str(rel).lower(), [x.lower() for x in rel.parts]
            ext = p.suffix.lower()
            if p.name.startswith(".") or "license" in low or "licence" in low:
                continue
            kind = None
            if ext in (".glb", ".gltf"):
                kind = "model"
            elif ext in (".ogg", ".wav", ".mp3"):
                kind = "sound"
            elif ext in (".png", ".jpg", ".jpeg"):
                if any("preview" in x for x in parts[:-1]) or p.parent == pack_dir or meta["category"] == "3D":
                    continue  # previews, samples, a 3D pack's model textures: not assets on their own
                if meta["category"] == "Textures":
                    kind = "texture"
                elif sheetish.search(low):
                    kind = "tileset"
                elif meta.get("ui") or "ui" in meta["tags"]:
                    kind = "ui"
                else:
                    kind = "sprite"
                # 2D packs ship each sprite several times (Default/Double, colour variants): keep the default size
                if any(x in ("double", "@2x", "retina") for x in parts[:-1]):
                    continue
            if not kind:
                continue
            aid = f"{self.name}:{slug}/{rel.as_posix()}"
            seen.add(aid)
            words = re.split(r"[\s_\-/().]+", rel.with_suffix("").as_posix())
            thumb = None
            if kind == "model":
                pv = previews.get(p.stem.lower())
                thumb = str(pv.relative_to(HOME)) if pv else None  # else rendered by `sync --thumbs`
            elif kind in ("sprite", "tileset", "ui", "texture"):
                thumb = str(p.relative_to(HOME))
            rows.append({
                "id": aid, "source": self.name, "pack": slug, "name": p.stem, "kind": kind, "category": meta["category"],
                "tags": [w for w in words if len(w) > 1 and not w.isdigit()] + meta["tags"], "style": meta["style"],
                "license": "CC0", "license_note": meta["license_note"], "license_checked": TODAY(),
                "page_url": meta["page"], "path": str(p.relative_to(HOME)), "thumb": thumb, "bytes": p.stat().st_size})
        pack_id = f"{self.name}:{slug}"
        seen.add(pack_id)
        prev = meta.get("preview")
        rows.append({
            "id": pack_id, "source": self.name, "pack": slug, "name": meta["name"], "kind": "pack",
            "category": meta["category"], "tags": meta["tags"] + [w for w in slug.split("-")], "style": meta["style"],
            "license": "CC0", "license_note": meta["license_note"], "license_checked": TODAY(), "page_url": meta["page"],
            "path": str(pack_dir.relative_to(HOME)), "thumb": prev,
            "bytes": sum(p.stat().st_size for p in files),
            "remote": {"files": len(rows), "kinds": sorted({r["kind"] for r in rows})}})
        upsert(c, rows)
        return seen

    def fetch(self, row, res):
        src = HOME / row["path"]
        pack_dir = HOME / "mirror" / self.name / row["pack"]
        out = [(src, src.relative_to(pack_dir).as_posix(), row["page_url"])]
        if src.suffix.lower() in (".glb", ".gltf"):
            for dep in gltf_deps(src):
                d = (src.parent / dep).resolve()
                if d.exists() and d.is_relative_to(pack_dir.resolve()):
                    out.append((d, d.relative_to(pack_dir.resolve()).as_posix(), row["page_url"]))
        return out


class Kenney(MirroredSource):
    """kenney.nl: ~220 packs, one zip each, no API. Pages are read politely (1 request/s)."""
    name = "kenney"
    SITE = "https://kenney.nl"

    def packs(self):
        slugs = []
        for page in range(1, 60):
            try:
                html = http(f"{self.SITE}/assets" + (f"/page:{page}" if page > 1 else "")).decode()
            except urllib.error.HTTPError:
                break  # past the last page the site answers 500
            found = [s for s in re.findall(r"href='https://kenney\.nl/assets/([a-z0-9-]+)'", html)
                     if s not in slugs and not s.startswith(("page", "category", "tag", "series"))]
            if not found:
                break
            slugs += list(dict.fromkeys(found))
        return [s for s in slugs if not ONLY or s in ONLY]

    def sync(self, c):
        seen, new = set(), 0
        for slug in self.packs():
            try:
                html = http(f"{self.SITE}/assets/{slug}").decode()
                z = re.search(r"href='(https://kenney\.nl/media/pages/assets/[^']+\.zip)'", html)
                if not z:
                    log(f"kenney: {slug}: no download link, skipped"); continue
                if not re.search(r"CC0", html):
                    log(f"kenney: {slug}: page does not say CC0, skipped"); continue
                cat = (re.search(r"/assets/category:(\w+)'", html) or [None, "Other"])[1]
                tags = sorted(set(re.findall(r"/assets/tag:([\w-]+)'", html)))
                title = (re.search(r"<h1[^>]*>([^<]+)</h1>", html) or [None, slug])[1].strip()
                version = z.group(1).split("/")[-2]  # the media hash changes with each pack update
                pack_dir, changed = self.mirror_pack(slug, z.group(1), version)
                ok, lic = self.licence_of(pack_dir)
                if not ok:
                    log(f"kenney: {slug}: licence file is not CC0, skipped: {lic[:120]}")
                    shutil.rmtree(pack_dir, ignore_errors=True); continue
                new += changed
                pv = next((p for p in (pack_dir / "Preview.png", pack_dir / "Sample.png") if p.exists()), None)
                style = "Kenney pixel" if "pixel" in tags else ("Kenney low-poly" if cat == "3D" else f"Kenney {cat.lower()}")
                seen |= self.index_pack(c, slug, pack_dir, {
                    "name": title, "category": cat, "tags": tags, "style": style, "page": f"{self.SITE}/assets/{slug}",
                    "license_note": lic[:200], "preview": str(pv.relative_to(HOME)) if pv else None,
                    "ui": "interface" in tags})
                c.commit()
            except Exception as e:  # one broken pack must not stop the sync
                log(f"kenney: {slug}: {type(e).__name__}: {e}")
        log(f"kenney: {len([s for s in seen if s.count('/') == 0])} packs, {new} new or updated")
        return seen


class KayKit(MirroredSource):
    """KayKit (Kay Lousberg) on itch.io: the free tier of each pack, CC0. itch.io's robots.txt disallows automated
    downloads (/*/download/), so the zips are downloaded once by hand into STUDIO_ASSET_HOME/inbox/kaykit/; sync
    reads each pack page (allowed) for the licence and title, mirrors the matching zip and indexes it, and lists
    the packs not downloaded yet. A newer zip in the inbox replaces the mirrored one."""
    name = "kaykit"
    PROFILE = "https://kaylousberg.itch.io"
    POLITE = 6.0  # itch.io answers 429 to faster crawling (and 429 backs off, see http())

    def packs(self):
        html = http(self.PROFILE, polite=self.POLITE).decode()
        slugs = sorted(set(re.findall(r'href="https://kaylousberg\.itch\.io/([a-z0-9-]+)"', html)))
        return [s for s in slugs if not ONLY or s in ONLY]

    @staticmethod
    def compact(s):
        return re.sub(r"[^a-z]", "", s.lower().replace("kaykit", ""))

    def zip_for(self, slug, zips):
        """itch zips run words together (KayKit_BlockBits_1.0_FREE.zip): compare letters only."""
        want = self.compact(slug)
        best = [z for z in zips if want and want in self.compact(z.stem)]
        return max(best, key=lambda z: z.stat().st_mtime) if best else None

    def sync(self, c):
        inbox = HOME / "inbox/kaykit"
        inbox.mkdir(parents=True, exist_ok=True)
        zips = sorted(inbox.glob("*.zip"))
        seen, missing = set(), []
        slugs = self.packs()
        # each zip belongs to the one pack whose name it matches most specifically (kaykit-character-animations,
        # not kaykit-animations)
        owner = {}
        for slug in sorted(slugs, key=lambda x: -len(self.compact(x))):
            z = self.zip_for(slug, [z for z in zips if z not in owner.values()])
            if z:
                owner[slug] = z
        for slug in slugs:
            try:
                html = http(f"{self.PROFILE}/{slug}", polite=self.POLITE).decode()
                if not re.search(r"\.gl(b|tf)|glTF", html, re.I) or "bundle" in slug:
                    continue  # not a 3D asset pack (bundles, tools)
                if not re.search(r"CC0|Creative Commons Zero", html):
                    log(f"kaykit: {slug}: page does not say CC0, skipped"); continue
                if not (re.search(r'title="[^"]*free[^"]*" class="name"', html, re.I) or "Name your own price" in html):
                    continue  # paid-only pack: not part of the free library
                z = owner.get(slug)
                if not z:
                    missing.append(slug); continue
                version = f"{z.name}:{z.stat().st_size}:{int(z.stat().st_mtime)}"
                pack_dir, _ = self.mirror_pack(slug, z.as_uri(), version)
                ok, lic = self.licence_of(pack_dir)
                title = (re.search(r'<h1 class="game_title">([^<]+)</h1>', html) or [None, slug])[1]
                cover = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                seen |= self.index_pack(c, slug, pack_dir, {
                    "name": title.strip(), "category": "3D", "tags": ["kaykit", "low-poly"], "style": "KayKit low-poly",
                    "page": f"{self.PROFILE}/{slug}",
                    "license_note": lic[:200] if ok else "itch.io page: Creative Commons Zero v1.0 Universal (CC0)",
                    "preview": cover.group(1) if cover else None})
                c.commit()
            except Exception as e:
                log(f"kaykit: {slug}: {type(e).__name__}: {e}")
        log(f"kaykit: {len([s for s in seen if s.count('/') == 0])} packs indexed")
        if missing:
            log(f"kaykit: {len(missing)} packs not downloaded yet: put the free zip of each in {inbox}/ "
                f"(browser, 'Download Now' -> 'No thanks, just take me to the downloads'):")
            for m in missing:
                log(f"  {self.PROFILE}/{m}")
        # keep already-indexed packs whose zip is still mirrored
        return seen | {r[0] for r in c.execute("select id from assets where source = 'kaykit'")
                       if (HOME / "mirror/kaykit" / r[0].split(":", 1)[1].split("/")[0]).exists()}


SOURCES = {s.name: s for s in (Kenney(), KayKit(), PolyHaven(), AmbientCG())}


def sync(names=None):
    c = db()
    for n in names or SOURCES:
        t0 = time.time()
        try:
            seen = SOURCES[n].sync(c)
            if seen:
                gone = drop_source(c, n, seen)
                if gone:
                    log(f"{n}: removed {gone} assets no longer offered")
            c.execute("insert or replace into meta values (?, ?)", (f"synced_{n}", TODAY()))
            c.commit()
            log(f"{n}: sync done in {time.time() - t0:.0f} s")
        except Exception as e:
            log(f"{n}: sync FAILED: {type(e).__name__}: {e}")
    return c


# ------------------------------------------------------------------------------------------------- Blender
def blender_batch(mode, files, out_json, thumbs_dir=None):
    """Run lib/asset_blender.py over many files in one Blender process (measure, thumbs)."""
    lst = pathlib.Path(out_json).with_suffix(".in.json")
    lst.write_text(json.dumps({"mode": mode, "files": [str(f) for f in files],
                               "thumbs": str(thumbs_dir) if thumbs_dir else None}))
    subprocess.run(["blender", "-b", "--factory-startup", "-P", str(STUDIO / "lib/asset_blender.py"), "--",
                    str(lst), str(out_json)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return json.loads(pathlib.Path(out_json).read_text()) if pathlib.Path(out_json).exists() else {}


def blender_batch_fix(fixes, out_json):
    """fixes: {file: {"scale": s, "origin": "bottom-centre"}}; re-exports each file in place."""
    lst = pathlib.Path(out_json).with_suffix(".in.json")
    lst.write_text(json.dumps({"mode": "fix", "files": list(fixes), "fixes": fixes}))
    subprocess.run(["blender", "-b", "--factory-startup", "-P", str(STUDIO / "lib/asset_blender.py"), "--",
                    str(lst), str(out_json)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return json.loads(pathlib.Path(out_json).read_text()) if pathlib.Path(out_json).exists() else {}


def render_thumbs(c, limit=None, batch=200):
    """Render a thumbnail (and measure size/tris) for mirrored models that have none."""
    rows = [dict(r) for r in c.execute(
        "select id, path, thumb from assets where kind = 'model' and path is not null and (thumb is null or tris is null)"
        " order by (thumb is null)")]
    rows = rows[:limit] if limit else rows
    done = 0
    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        res = {}
        with tempfile.TemporaryDirectory() as td:
            for mode in ("measure", "thumbs"):  # models with a shipped preview are only measured
                part = [HOME / r["path"] for r in chunk if (r["thumb"] is None) == (mode == "thumbs")]
                if part:
                    res.update(blender_batch(mode, part, pathlib.Path(td) / f"{mode}.json", HOME / "thumbs"))
        for r in chunk:
            m = res.get(str(HOME / r["path"]))
            if not m or "error" in m:
                continue
            cur = get(c, r["id"])
            c.execute("update assets set dims_m = ?, tris = ?, thumb = coalesce(thumb, ?) where id = ?",
                      (json.dumps(m["dims_m"]), m["tris"],
                       str(pathlib.Path(m["thumb"]).relative_to(HOME)) if m.get("thumb") else cur["thumb"], r["id"]))
            done += 1
        c.commit()
        log(f"thumbs: {min(i + batch, len(rows))}/{len(rows)}")
    return done


# ------------------------------------------------------------------------------------------------- project side
def project_paths(project):
    p = pathlib.Path(project).resolve()
    a = p / "assets"
    return p, a, a / "ASSETS.json", a / "proposals", a / "style.json"


def load_json(p, default):
    p = pathlib.Path(p)
    return json.loads(p.read_text()) if p.exists() else default


def save_json(p, data):
    p = pathlib.Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def taste():
    return load_json(HOME / "taste.json", [])


def add_taste(entries):
    t = taste()
    t.extend(entries)
    save_json(HOME / "taste.json", t)


VISUAL = ("model", "texture", "material", "hdri", "sprite", "tileset", "ui", "pack")


def is_visual(s, c=None):
    """A set counts for the style lock if any item is visual (sounds have no visual style)."""
    kinds = {i.get("kind") or (get(c, i["id"]) or {}).get("kind") if isinstance(i, dict) else (get(c, i) or {}).get("kind")
             for i in s.get("items", [])}
    return bool(kinds & set(VISUAL))


def style_of(project):
    _, _, _, _, style = project_paths(project)
    return load_json(style, {"lock": None, "allow": [], "resolution": "2k"})


def validate_proposal(c, project, prop):
    """Checks a director's proposal; returns (errors, warnings). Format: docs/assets.md."""
    errors, warnings = [], []
    lock = style_of(project).get("lock")
    for need in prop.get("needs", []):
        sets = need.get("sets", [])
        if not need.get("id") or not sets:
            errors.append(f"need {need.get('id')!r}: needs an id and at least one set")
        if len(sets) > 2:
            errors.append(f"need {need['id']}: at most a main set and one alternative")
        styles = []
        for s in sets:
            items = s.get("items", [])
            if not items:
                errors.append(f"{need['id']}/{s.get('id')}: empty set")
            st = set()
            for it in items:
                aid = it["id"] if isinstance(it, dict) else it
                row = get(c, aid)
                if not row:
                    errors.append(f"{need['id']}/{s.get('id')}: unknown asset {aid}")
                    continue
                if row["license"] != "CC0":
                    errors.append(f"{aid}: licence {row['license']} is not CC0")
                st.add(row["style"])
            if len(st) > 1:
                warnings.append(f"{need['id']}/{s.get('id')}: mixes styles {sorted(st)}")
            styles.append(s.get("style") or (st.pop() if len(st) == 1 else None))
            allowed = {lock, *style_of(project).get("allow", [])}
            if lock and is_visual(s, c) and not ({s.get("style", styles[-1])} | st) <= allowed and not prop.get("lift_lock"):
                errors.append(f"{need['id']}/{s.get('id')}: style {styles[-1]!r} breaks the project's style lock "
                              f"{lock!r} (set \"lift_lock\": true only if the user asked)")
        if len(styles) == 2 and styles[0] == styles[1]:
            warnings.append(f"need {need['id']}: the alternative should be a different style")
    return errors, warnings


def add_proposal(c, project, prop):
    errors, warnings = validate_proposal(c, project, prop)
    if errors:
        return None, errors, warnings
    _, _, _, props, _ = project_paths(project)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    prop = dict(prop, status="open", created=stamp)
    for need in prop["needs"]:
        for s in need["sets"]:
            items = []
            for it in s["items"]:
                it = it if isinstance(it, dict) else {"id": it}
                row = get(c, it["id"])
                it.update({k: row[k] for k in ("name", "kind", "source", "pack", "style", "page_url")})
                it["thumb"] = row["thumb"]
                it["dims_m"] = json.loads(row["dims_m"]) if row["dims_m"] else None
                it["tris"] = row["tris"]
                items.append(it)
            s["items"] = items
            s.setdefault("style", items[0]["style"] if items else None)
    p = props / f"{stamp}.json"
    save_json(p, prop)
    return p, [], warnings


def open_proposals(project):
    _, _, _, props, _ = project_paths(project)
    return [(p, load_json(p, {})) for p in sorted(props.glob("*.json")) if load_json(p, {}).get("status") == "open"]


def record_decision(project, prop_path, decisions, lock=None, lift_lock=False):
    """decisions: {need_id: {"set": set_id or None, "vetoed": [ids], "reason": str}} from the review page."""
    prop = load_json(prop_path, {})
    style = style_of(project)
    entries = []
    for need in prop["needs"]:
        d = decisions.get(need["id"], {"set": None})
        need["decision"] = d
        for s in need["sets"]:
            yes = d.get("set") == s["id"]
            entries.append({"date": TODAY(), "project": pathlib.Path(project).name, "brief": prop.get("brief", "")[:200],
                            "need": need["id"], "set": s["id"], "style": s.get("style"),
                            "sources": sorted({i["source"] for i in s["items"]}), "decision": "yes" if yes else "no",
                            "vetoed": d.get("vetoed", []) if yes else [], "reason": d.get("reason", "")})
            if yes and not style.get("lock") and not lift_lock and is_visual(s):
                style["lock"] = lock or s.get("style")
    if lift_lock:
        style["lock"] = lock
    prop["status"] = "decided"
    prop["decided"] = datetime.datetime.now().isoformat(timespec="seconds")
    save_json(prop_path, prop)
    save_json(project_paths(project)[4], style)
    add_taste(entries)
    return prop


def approved_items(project):
    """(proposal path, need, item) for every approved, non-vetoed item of decided proposals."""
    _, _, _, props, _ = project_paths(project)
    for p in sorted(props.glob("*.json")):
        prop = load_json(p, {})
        if prop.get("status") != "decided":
            continue
        for need in prop["needs"]:
            d = need.get("decision") or {}
            for s in need["sets"]:
                if s["id"] != d.get("set"):
                    continue
                for it in s["items"]:
                    if it["id"] not in d.get("vetoed", []):
                        yield p, need, it


GITATTR = "assets/** filter=lfs diff=lfs merge=lfs -text\nassets/**/*.json !filter !diff !merge text\nassets/**/*.import !filter !diff !merge text\nassets/**/*.tres !filter !diff !merge text\nassets/**/*.md !filter !diff !merge text\n"


def ensure_lfs(project):
    p = pathlib.Path(project)
    if not (p / ".git").exists():
        return False
    ga = p / ".gitattributes"
    cur = ga.read_text() if ga.exists() else ""
    if "assets/** filter=lfs" not in cur:
        ga.write_text(cur + ("" if cur.endswith("\n") or not cur else "\n") + GITATTR)
    subprocess.run(["git", "-C", str(p), "lfs", "install", "--local"], capture_output=True)
    return True


def fetch(c, project, res=None, only=None):
    """Copy approved assets into the project, record them in ASSETS.json, regenerate CREDITS.md."""
    proj, assets, manifest_p, _, _ = project_paths(project)
    res = res or style_of(project).get("resolution", "2k")
    manifest = load_json(manifest_p, {"version": 1, "assets": {}})
    ensure_lfs(proj)
    fetched, failed = [], []
    for _, need, it in approved_items(project):
        aid = it["id"]
        if (only and aid not in only) or (aid in manifest["assets"] and manifest["assets"][aid].get("res") in (None, res)):
            continue
        row = get(c, aid)
        if not row:
            failed.append((aid, "no longer in the index")); continue
        try:
            files = SOURCES[row["source"]].fetch(row, res)
        except Exception as e:
            failed.append((aid, f"{type(e).__name__}: {e}")); continue
        rec = {"source": row["source"], "pack": row["pack"], "name": row["name"], "kind": row["kind"],
               "license": row["license"], "license_note": row["license_note"], "license_checked": row["license_checked"],
               "url": row["page_url"], "need": need["id"], "decorative": bool(it.get("decorative")),
               "fetched": TODAY(), "res": res if not SOURCES[row["source"]].mirrored else None, "files": []}
        for src, rel, url in files:
            dst = assets / row["source"] / safe(row["pack"]) / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists() or sha256(dst) != sha256(src):
                shutil.copy2(src, dst)
            rec["files"].append({"path": dst.relative_to(proj).as_posix(), "sha256": sha256(dst), "url": url})
        manifest["assets"][aid] = rec
        fetched.append(aid)
    save_json(manifest_p, manifest)
    write_credits(proj, manifest)
    return fetched, failed


def safe(s):
    return re.sub(r"[^\w.-]+", "_", s or "misc")


def write_credits(proj, manifest):
    by = {}
    for aid, a in sorted(manifest["assets"].items()):
        by.setdefault(a["source"], []).append((aid, a))
    names = {"kenney": "Kenney (www.kenney.nl)", "kaykit": "KayKit by Kay Lousberg (kaylousberg.itch.io)",
             "polyhaven": "Poly Haven (polyhaven.com)", "ambientcg": "ambientCG (ambientcg.com)"}
    out = ["# Credits", "", "All third-party assets in this project are CC0 (public domain). Credit is not required;",
           "it is given here as a courtesy. Generated by `studio-assets fetch` from assets/ASSETS.json.", ""]
    for src, items in by.items():
        out.append(f"## {names.get(src, src)}")
        out.append("")
        packs = {}
        for aid, a in items:
            packs.setdefault(a["pack"], []).append(a)
        for pack, lst in packs.items():
            out.append(f"- **{pack}**: {', '.join(sorted({x['name'] for x in lst}))} ({lst[0]['url']}), CC0, "
                       f"licence checked {lst[0]['license_checked']}")
        out.append("")
    (proj / "CREDITS.md").write_text("\n".join(out))
