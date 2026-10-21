"""Local review page for asset proposals (studio-assets review <project>).

Serves 127.0.0.1 only. One card per need: the main set and the alternative side by side, thumbnails, measured
size of 3D models, play buttons for sounds, a veto per item, a yes per set (or none), an optional reason. Submit
saves the decisions into the proposal, taste.json and the project's style lock, then the server exits.
Files are served only from the asset library (thumbnails, mirrored sounds), never from elsewhere on disk.
"""
import html
import http.server
import json
import pathlib
import threading
import urllib.parse

import studio_assets as sa

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Asset review</title><style>
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1f22;--mute:#666b73;--line:#dedbd5;--acc:#2f6f4f;--no:#a33a2a;--chip:#eef0ec}
@media (prefers-color-scheme:dark){:root{--bg:#17181a;--card:#212326;--ink:#e8e6e1;--mute:#9a9fa6;--line:#34373b;--acc:#6fbf8f;--no:#e0806e;--chip:#2b2e31}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,sans-serif}
header{padding:20px 16px 8px;max-width:1200px;margin:auto}h1{font-size:22px;margin:0 0 4px}.mute{color:var(--mute)}
main{max-width:1200px;margin:auto;padding:0 16px 120px}.need{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:16px 0;padding:16px}
.need h2{font-size:18px;margin:0 0 2px}.sets{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px;margin-top:12px}
.set{border:2px solid var(--line);border-radius:8px;padding:12px}.set.chosen{border-color:var(--acc)}
.set h3{font-size:15px;margin:0 0 4px;display:flex;gap:8px;align-items:center}.chip{background:var(--chip);border-radius:20px;padding:1px 9px;font-size:12px}
.items{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:8px;margin-top:10px}
.item{border:1px solid var(--line);border-radius:6px;padding:6px;font-size:12px;position:relative}.item.vetoed{opacity:.35}
.item img{width:100%;aspect-ratio:1;object-fit:contain;background:var(--chip);border-radius:4px;display:block}
.item .nm{overflow-wrap:anywhere;margin-top:4px}.item label{display:block;color:var(--no);margin-top:2px;cursor:pointer}
.item audio{width:100%;height:28px;margin-top:4px}.ph{width:100%;aspect-ratio:1;display:grid;place-items:center;background:var(--chip);border-radius:4px;font-size:11px;color:var(--mute)}
.choice{display:flex;flex-wrap:wrap;gap:14px;margin-top:12px;align-items:center}.choice input[type=text]{flex:1;min-width:220px;padding:7px 9px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink)}
.lock{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin-top:8px}
footer{position:fixed;bottom:0;left:0;right:0;background:var(--card);border-top:1px solid var(--line);padding:12px 16px;display:flex;gap:12px;justify-content:center;align-items:center}
button{background:var(--acc);color:#fff;border:0;border-radius:7px;padding:10px 22px;font-size:15px;cursor:pointer}a{color:var(--acc)}
.gap{border-left:3px solid var(--no);padding:4px 10px;margin:8px 0}.gapnote{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:16px 0;padding:8px 16px}
</style></head><body><header><h1>Asset review: __PROJECT__</h1><div class="mute">__BRIEF__</div>
<div class="lock">__LOCK__</div></header><main>__NEEDS__</main>
<footer><span class="mute" id="status">Choose a set (or none) for each need, veto single items, then save.</span><button onclick="save()">Save decisions</button></footer>
<script>
function pick(need,set){document.querySelectorAll(`[data-need="${need}"] .set`).forEach(e=>e.classList.toggle('chosen',e.dataset.set===set))}
function veto(cb){cb.closest('.item').classList.toggle('vetoed',cb.checked)}
window.onerror=(m)=>{document.getElementById('status').textContent='Page error: '+m+' (tell the director)'};
async function save(){const out={decisions:{},lift_lock:false,lock:null};
 document.querySelectorAll('.need').forEach(n=>{const id=n.dataset.need;const r=n.querySelector('input[type=radio]:checked');
  const set=r?r.value:null;out.decisions[id]={set:set==='none'?null:set,reason:n.querySelector('input[type=text]').value,
  vetoed:[...n.querySelectorAll(`.set[data-set="${set}"] input[type=checkbox]:checked`)].map(c=>c.value)}});
 const lift=document.getElementById('lift');if(lift&&lift.checked){out.lift_lock=true;out.lock=document.getElementById('newlock').value||null}
 const missing=Object.entries(out.decisions).filter(([k,v])=>!document.querySelector(`[data-need="${k}"] input[type=radio]:checked`));
 if(missing.length){document.getElementById('status').textContent='Still undecided: '+missing.map(m=>m[0]).join(', ');return}
 const r=await fetch('/decide',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(out)});
 document.getElementById('status').textContent=r.ok?'Saved. You can close this tab.':'Saving failed: '+await r.text();
 if(r.ok)document.querySelector('footer button').disabled=true}
</script></body></html>"""


def media_url(ref):
    if not ref:
        return None
    if ref.startswith("http"):
        return ref
    return "/lib/" + urllib.parse.quote(ref)


def fmt_dims(d):
    return " x ".join(f"{v:.2f}" for v in d) + " m" if d else ""


def render(project, prop):
    style = sa.style_of(project)
    e = html.escape
    needs = []
    for need in prop["needs"]:
        sets = []
        for s in need["sets"]:
            items = []
            for it in s["items"]:
                media = ""
                if it["kind"] == "sound":
                    row_path = (sa.get(sa.db(), it["id"]) or {}).get("path")
                    media = f'<div class="ph">sound</div><audio controls preload="none" src="{media_url(row_path)}"></audio>' if row_path else '<div class="ph">sound</div>'
                elif it.get("thumb"):
                    media = f'<img src="{e(media_url(it["thumb"]))}" alt="">'
                else:
                    media = '<div class="ph">no preview</div>'
                extra = fmt_dims(it.get("dims_m"))
                if it.get("tris"):
                    extra += f", {it['tris']:,} tris"
                items.append(f'<div class="item">{media}<div class="nm" title="{e(it["id"])}">{e(it["name"])}</div>'
                             f'<div class="mute">{e(extra)}</div>'
                             f'<label><input type="checkbox" value="{e(it["id"])}" onchange="veto(this)"> veto</label></div>')
            src = ", ".join(sorted({i["source"] for i in s["items"]}))
            sets.append(f'<div class="set" data-set="{e(s["id"])}"><h3><input type="radio" name="{e(need["id"])}" value="{e(s["id"])}" '
                        f'onchange="pick(\'{e(need["id"])}\',\'{e(s["id"])}\')"> Set {e(s["id"])} <span class="chip">{e(s.get("style") or "")}</span>'
                        f'<span class="chip">{e(src)}</span></h3><div>{e(s.get("why", ""))}</div><div class="items">{"".join(items)}</div></div>')
        gaps = "".join(f'<div class="gap"><b>Gap:</b> {e(g)}</div>' for g in need.get("gaps", []))
        needs.append(f'<section class="need" data-need="{e(need["id"])}"><h2>{e(need["id"])}</h2><div class="mute">{e(need.get("why", ""))}</div>'
                     f'{gaps}<div class="sets">{"".join(sets)}</div><div class="choice"><label><input type="radio" name="{e(need["id"])}" value="none" '
                     f'onchange="pick(\'{e(need["id"])}\',\'none\')"> none of these</label><input type="text" placeholder="reason (optional, remembered for next time)"></div></section>')
    for g in prop.get("gaps", []):
        needs.append(f'<section class="gapnote"><div class="gap"><b>Gap:</b> {e(g)}</div></section>')
    lock = style.get("lock")
    lock_html = (f'Style lock: <b>{e(lock)}</b>. <label><input type="checkbox" id="lift"> lift it</label> '
                 f'<input type="text" id="newlock" placeholder="new lock (empty = none)">' if lock else
                 'No style lock yet: the first approved set sets it.')
    return (PAGE.replace("__PROJECT__", e(pathlib.Path(project).name)).replace("__BRIEF__", e(prop.get("brief", "")))
            .replace("__LOCK__", lock_html).replace("__NEEDS__", "".join(needs)))


def serve(project, prop_path, port=8765, open_browser=True):
    prop = sa.load_json(prop_path, {})
    done = threading.Event()
    result = {}

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, code, body, ctype="text/html; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            if u.path == "/":
                return self.send(200, render(project, prop).encode())
            if u.path.startswith("/lib/"):
                p = (sa.HOME / urllib.parse.unquote(u.path[5:])).resolve()
                if not p.is_relative_to(sa.HOME.resolve()) or not p.is_file():
                    return self.send(404, b"not found", "text/plain")
                ctype = {".png": "image/png", ".jpg": "image/jpeg", ".ogg": "audio/ogg", ".wav": "audio/wav",
                         ".mp3": "audio/mpeg"}.get(p.suffix.lower(), "application/octet-stream")
                return self.send(200, p.read_bytes(), ctype)
            self.send(404, b"not found", "text/plain")

        def do_POST(self):
            if self.path != "/decide" or self.headers.get("Origin", "http://127.0.0.1").split("//")[-1].split(":")[0] not in ("127.0.0.1", "localhost"):
                return self.send(403, b"forbidden", "text/plain")
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            try:
                result["prop"] = sa.record_decision(project, prop_path, body["decisions"], body.get("lock"),
                                                    body.get("lift_lock", False))
            except Exception as ex:  # noqa: BLE001
                return self.send(500, str(ex).encode(), "text/plain")
            self.send(200, b"ok", "text/plain")
            done.set()

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), H)
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    print(f"Review page: {url}  (waiting for the decisions; Ctrl+C to stop)", flush=True)
    if open_browser:
        import webbrowser
        webbrowser.open(url)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        done.wait()
    finally:
        srv.shutdown()
    return result.get("prop")
