#!/usr/bin/env python3
"""Check the dashboard page (lib/status_page.html) against tests/dashboard/fixture.json in headless Firefox.

  python3 tests/dashboard/check_page.py [--shots DIR]

Serves the page with the fixture at /api/status, injects a console hook and a probe that inspects the DOM after
rendering (phone width 390 px and desktop 1280 px): no JS errors, every panel present, donut slices sum to 100%
and follow the colour rules, range switching works, no horizontal scroll at phone width, the alert badge is in the
title. Prints CHECK OK or the failures. --shots also saves screenshots (phone + desktop) for review.
"""
import argparse
import http.server
import json
import pathlib
import subprocess
import sys
import tempfile
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAGE = ROOT / "lib/status_page.html"
FIXTURE = pathlib.Path(__file__).with_name("fixture.json")
PNG_1PX = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de0000000c4944415408d763f8"
                        "cfc0000003010100c9fe92ef0000000049454e44ae426082")

HOOK = """<script>(function(){for(const k of ['error','warn']){const o=console[k];console[k]=function(...a){
try{navigator.sendBeacon('/log',k+': '+a.join(' '))}catch(e){};o.apply(console,a)}}
window.addEventListener('error',e=>navigator.sendBeacon('/log','pageerror: '+e.message+' line '+e.lineno));
window.addEventListener('unhandledrejection',e=>navigator.sendBeacon('/log','pageerror: '+e.reason));})();</script>"""

PROBE = r"""<script>
setTimeout(async function(){
 const R = {fails: [], info: {}};
 const fail = m => R.fails.push(m);
 const q = s => document.querySelectorAll(s);
 const fx = window.__FIXTURE__;
 function hsl(c){ const m = c.match(/[\d.]+/g); if(!m) return null;
   let [r,g,b] = m.slice(0,3).map(x => x/255); const mx = Math.max(r,g,b), mn = Math.min(r,g,b);
   let h = 0, l = (mx+mn)/2, d = mx-mn, s = d ? d/(1-Math.abs(2*l-1)) : 0;
   if(d){ h = mx===r ? ((g-b)/d)%6 : mx===g ? (b-r)/d+2 : (r-g)/d+4; h = (h*60+360)%360; }
   return {h, s: s*100, l: l*100}; }
 function checkDonut(range){
   const s = fx.share[range];
   const paths = [...q('#donut [data-model]')];
   if(paths.length !== s.slices.length) fail(`${range}: ${paths.length} donut slices, fixture has ${s.slices.length}`);
   const sum = paths.reduce((a,p) => a + parseFloat(p.getAttribute('data-pct')||'NaN'), 0);
   if(Math.abs(sum-100) > 0.5) fail(`${range}: slices sum to ${sum.toFixed(2)}%, not 100`);
   const loc = [], onl = [];
   for(const p of paths){
     const sl = s.slices.find(x => x.model === p.getAttribute('data-model'));
     if(!sl){ fail(`${range}: slice ${p.getAttribute('data-model')} not in the fixture`); continue; }
     const c = hsl(getComputedStyle(p).fill);
     if(!c){ fail(`${range}: slice ${sl.model} has no computed fill`); continue; }
     if(sl.group === 'local'){ loc.push(c.l); if(c.h < 140 || c.h > 215 || c.s < 20) fail(`${range}: local slice ${sl.model} not blue-green (h ${c.h|0} s ${c.s|0})`); }
     if(sl.group === 'online'){ onl.push(c.l); if(!(c.h <= 40 || c.h >= 345) || c.s < 25) fail(`${range}: online slice ${sl.model} not orange-red (h ${c.h|0} s ${c.s|0})`); }
     if(sl.group === 'unclassified' && c.s > 15) fail(`${range}: unclassified slice ${sl.model} not grey (s ${c.s|0})`);
     if(!document.body.textContent.includes(sl.model)) fail(`${range}: slice ${sl.model} has no label`);
   }
   if(loc.length && onl.length && Math.max(...onl) >= Math.min(...loc)) fail(`${range}: online shades not darker than local (online max L ${Math.max(...onl)|0}, local min L ${Math.min(...loc)|0})`);
   const centre = document.querySelector('#donut-center');
   if(!centre || !centre.textContent.includes(String(Math.round(s.local_pct)))) fail(`${range}: #donut-center does not show ${Math.round(s.local_pct)}% local`);
 }
 try {
  R.info.width = innerWidth;
  if(document.documentElement.scrollWidth > innerWidth + 1) fail(`horizontal scroll at ${innerWidth}px (scrollWidth ${document.documentElement.scrollWidth})`);
  if(!document.title.startsWith('⚠')) fail(`title "${document.title}" has no ⚠ badge (fixture has red alerts)`);
  const p = fx.projects.find(v => v.name === fx.active_project);
  if(q('[data-ticket]').length !== p.board.length) fail(`${q('[data-ticket]').length} [data-ticket] rows, active project has ${p.board.length} tickets`);
  if(q('[data-job]').length !== fx.jobs.length) fail(`${q('[data-job]').length} [data-job] rows, fixture has ${fx.jobs.length}`);
  const qopen = fx.queue.items.filter(i => !['done','dropped'].includes(i.status)).length;
  if(q('[data-queue]').length < qopen) fail(`${q('[data-queue]').length} [data-queue] rows, ${qopen} open items`);
  if(q('[data-feed]').length < Math.min(10, fx.feed.length)) fail(`only ${q('[data-feed]').length} [data-feed] rows`);
  if(!q('button[data-pause]').length) fail('no button[data-pause] (the active project can pause)');
  const txt = document.body.textContent;
  for(const want of [p.eta.done.slice(11,16), p.eta.worst.slice(11,16), 'stalled', p.steps_line.text, fx.queue.items[0].item.slice(0,30), fx.machine.gpus[0].name])
    if(!txt.includes(want)) fail(`page text lacks "${want}"`);
  // layout bugs a screenshot showed: the ring cropped to a quadrant, the centre label on the legend, legend columns
  // run together, ticket counts of 0, a stall listed twice (once as "None")
  const box = e => e.getBoundingClientRect();
  const inside = (a, b) => a.left >= b.left - 1 && a.right <= b.right + 1 && a.top >= b.top - 1 && a.bottom <= b.bottom + 1;
  const apart = (a, b) => a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top;
  const svg = box(document.querySelector('#donut'));
  for(const pth of q('#donut [data-model]')) if(!inside(box(pth), svg)) fail(`donut slice ${pth.getAttribute('data-model')} drawn outside the svg`);
  const ring = [...q('#donut [data-model]')].reduce((u, pth) => { const r = box(pth);
    return {l: Math.min(u.l, r.left), r: Math.max(u.r, r.right), t: Math.min(u.t, r.top), b: Math.max(u.b, r.bottom)}; },
    {l: 1e9, r: -1e9, t: 1e9, b: -1e9});
  if(ring.r - ring.l < svg.width * 0.85 || ring.b - ring.t < svg.height * 0.85) fail(`donut ring ${(ring.r - ring.l)|0}x${(ring.b - ring.t)|0} px in a ${svg.width|0}x${svg.height|0} svg (cropped?)`);
  const ctr = box(document.querySelector('#donut-center'));
  if(!inside(ctr, svg)) fail('the centre label is not on the donut');
  if(!apart(ctr, box(document.querySelector('#share-legend')))) fail('the centre label overlaps the legend');
  for(const row of q('.legend-item')){
    const cells = [...row.children].map(box);
    for(let i = 1; i < cells.length; i++) if(cells[i].left < cells[i-1].right + 4) fail(`legend row "${row.textContent}": columns touch`);
  }
  const cnt = p.counts || {};
  const want = `${cnt.pass || 0} pass`;
  if(!document.querySelector('#ticket-counts').textContent.includes(want)) fail(`ticket counts "${document.querySelector('#ticket-counts').textContent}" lack "${want}"`);
  if(q('.alert-row').length !== fx.alerts.length) fail(`${q('.alert-row').length} alert rows, fixture has ${fx.alerts.length} alerts`);
  if(/\bNone\b/.test(document.querySelector('#alerts-list').textContent)) fail('"None" in the alerts');
  checkDonut('project');
  for(const r of ['today','all']){
    const b = document.querySelector(`[data-range="${r}"]`);
    if(!b){ fail(`no [data-range="${r}"] button`); continue; }
    b.click(); await new Promise(res => setTimeout(res, 900)); checkDonut(r);
  }
  // the page keeps polling (it once rendered its first answer forever)
  const polls = () => performance.getEntriesByType('resource').filter(e => e.name.includes('/api/status')).length;
  const before = polls();
  await new Promise(res => setTimeout(res, 5600));
  if(polls() <= before) fail(`no /api/status poll in 5.6 s (${before} before, ${polls()} after)`);
 } catch(e){ fail('probe exception: ' + e.message); }
 navigator.sendBeacon('/result', JSON.stringify(R));
}, 2500);
</script>"""


def serve(fixture_inline):
    got = {"log": [], "result": None}
    fixture = FIXTURE.read_text()

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(s, *x):
            pass

        def reply(s, code, body, ctype):
            b = body if isinstance(body, bytes) else body.encode()
            s.send_response(code)
            s.send_header("content-type", ctype)
            s.send_header("content-length", str(len(b)))
            s.end_headers()
            s.wfile.write(b)

        def do_GET(s):
            if s.path.split("?")[0] == "/":
                html = PAGE.read_text()
                pre = f"<script>window.__FIXTURE__ = {fixture};</script>"
                if fixture_inline:   # screenshot mode: render at load, without waiting for a fetch
                    pre += "<script>window.STATUS_FIXTURE = window.__FIXTURE__;</script>"
                html = html.replace("<head>", "<head>" + HOOK + pre, 1)
                if not fixture_inline:
                    html = html.replace("</body>", PROBE + "</body>", 1)
                s.reply(200, html, "text/html; charset=utf-8")
            elif s.path.startswith("/api/status"):
                s.reply(200, fixture, "application/json")
            elif s.path.startswith("/api/image"):
                s.reply(200, PNG_1PX, "image/png")
            else:
                s.reply(404, "not found", "text/plain")

        def do_POST(s):
            n = int(s.headers.get("content-length", 0))
            body = s.rfile.read(n).decode(errors="replace")
            if s.path == "/result":
                got["result"] = json.loads(body)
            elif s.path == "/log":
                got["log"].append(body)
            else:   # pause/resume: accept, the fixture doesn't change
                s.reply(200, '{"ok": true}', "application/json")
                return
            s.send_response(204)
            s.end_headers()

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, got, f"http://127.0.0.1:{srv.server_address[1]}/"


def run_probe(width, height):
    srv, got, url = serve(False)
    with tempfile.TemporaryDirectory(prefix="dash-check-") as prof:
        ff = subprocess.Popen(["firefox", "--headless", "--no-remote", "--profile", prof, "--window-size",
                               f"{width},{height}", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t0 = time.time()
        while time.time() - t0 < 50 and got["result"] is None:
            time.sleep(0.3)
        ff.terminate()
        try:
            ff.wait(10)
        except subprocess.TimeoutExpired:
            ff.kill()
    srv.shutdown()
    fails = []
    if got["result"] is None:
        fails.append(f"{width}px: the probe never reported (page crashed or hung?)")
    else:
        fails += [f"{width}px: {f}" for f in got["result"]["fails"]]
    fails += [f"{width}px: {l}" for l in got["log"] if l.startswith(("pageerror", "error"))]
    return fails


def screenshot(width, height, out):
    srv, _, url = serve(True)
    with tempfile.TemporaryDirectory(prefix="dash-shot-") as prof:
        subprocess.run(["firefox", "--headless", "--no-remote", "--profile", prof, "--window-size",
                        f"{width},{height}", "--screenshot", str(out), url], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=60)
    srv.shutdown()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots")
    a = ap.parse_args()
    if not PAGE.exists():
        sys.exit(f"CHECK FAILED: {PAGE} missing")
    fails = run_probe(390, 844) + run_probe(1280, 900)
    if a.shots:
        d = pathlib.Path(a.shots)
        d.mkdir(parents=True, exist_ok=True)
        screenshot(390, 2400, d / "phone.png")
        screenshot(1400, 1200, d / "desktop.png")
        print(f"screenshots in {d}")
    for f in fails:
        print("CHECK FAILED:", f)
    print("CHECK OK" if not fails else f"{len(fails)} failures")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
