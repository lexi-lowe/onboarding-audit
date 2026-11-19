"""Render an audit as one self-contained HTML report.

Two ways to get ticket buttons:
  - owner's tracker in config: every finding gets a "File in <tracker>" button, or an
    "Already filed" link when the duplicate check found one.
  - report.tracker_notice: true (for a report shared with another company): a dismissible
    notice lets each reader connect their own Jira, Linear or GitHub in the browser.

The theme takes colours and a font from config["theme"], ideally read from the audited
product's own pages. The audited company's logo is never used, and a footer says who ran it.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

from .findings import Audit, Persona
from .rubric import OBSERVED
from .timing import fmt_duration
from .trackers import button_label, file_url

ASSETS = Path(__file__).resolve().parent.parent.parent / "assets"

DEFAULT_THEME = {
    "font": "Inter", "ink": "#222222", "muted": "#5f6368", "bg": "#f7f8fa", "card": "#ffffff",
    "line": "#dfe1e5", "accent": "#2f6f62", "accent_dark": "#245448", "tint": "#e7f2ef",
    "header": "#1d2b28", "header_ink": "#ffffff", "radius": "4px",
}
SEV_CLASS = {"High": "high", "Medium": "med", "Low": "low"}
e = lambda s: html.escape(str(s or ""), quote=True)


def _css(t: dict) -> str:
    return f""":root {{ --ink:{t['ink']}; --muted:{t['muted']}; --bg:{t['bg']}; --card:{t['card']}; --line:{t['line']}; --accent:{t['accent']}; --accent-dark:{t['accent_dark']}; --tint:{t['tint']}; --radius:{t['radius']}; --high:#d93025; --med:#c26401; --low:#8a8c8f; }}
* {{ box-sizing:border-box; }} [hidden] {{ display:none !important; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.6 "{e(t['font'])}", system-ui, sans-serif; }}
header.band {{ background:{t['header']}; color:{t['header_ink']}; }}
header.band .wrap {{ max-width:880px; margin:0 auto; padding:36px 24px 30px; }}
header.band h1 {{ font-size:30px; font-weight:600; margin:0 0 6px; }}
header.band .meta {{ opacity:.75; font-size:13px; }}
main {{ max-width:880px; margin:0 auto; padding:28px 24px 60px; }}
h2 {{ font-size:20px; font-weight:600; margin:40px 0 12px; }} h3 {{ font-weight:600; }} a {{ color:var(--accent-dark); }}
.lead {{ font-size:16px; margin:24px 0 0; }}
.finding {{ background:var(--card); border:1px solid var(--line); border-radius:var(--radius); padding:18px 20px; margin:12px 0; }}
.finding h3 {{ margin:0 0 6px; font-size:16px; }}
.sev {{ display:inline-block; font-size:11px; font-weight:600; letter-spacing:.04em; text-transform:uppercase; color:#fff; border-radius:2px; padding:2px 8px; margin-right:8px; vertical-align:2px; }}
.high {{ background:var(--high); }} .med {{ background:var(--med); }} .low {{ background:var(--low); }}
.finding p {{ margin:6px 0; }} .fix, .what {{ color:var(--muted); }} .what {{ font-size:13px; margin:0 0 6px; }}
.data {{ font-size:13px; background:var(--tint); padding:6px 10px; border-radius:2px; }}
figure {{ margin:12px 0 0; }} figure img {{ width:100%; border:1px solid var(--line); border-radius:var(--radius); display:block; }}
figcaption {{ font-size:13px; color:var(--muted); margin-top:6px; }}
table {{ width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--line); font-size:14px; }}
th, td {{ text-align:left; padding:10px 12px; border-bottom:1px solid var(--line); vertical-align:top; }} th {{ background:#f1f3f6; font-weight:600; }}
.file, .filed {{ display:inline-block; font-weight:600; font-size:13px; padding:6px 12px; border-radius:2px; margin:2px 0 8px; text-decoration:none; }}
.file {{ background:var(--accent); color:#fff; }} .filed {{ border:1.5px solid var(--accent); color:var(--accent-dark); }}
.hint {{ font-size:12px; color:var(--muted); margin-left:8px; }}
.notice {{ background:var(--tint); border:1px solid var(--accent); border-radius:2px; padding:12px 14px; }}
.notice-head {{ display:flex; gap:10px; align-items:flex-start; }} .notice-icon {{ flex:0 0 18px; margin-top:2px; color:var(--accent); }}
.notice-text {{ flex:1; font-size:14px; }} .notice-text strong {{ color:var(--accent-dark); }}
.notice-actions {{ display:flex; gap:12px; white-space:nowrap; }}
.notice-close {{ background:none; border:0; cursor:pointer; color:var(--accent-dark); font-size:18px; line-height:1; }}
.notice-body {{ margin:12px 0 0 28px; padding-top:12px; border-top:1px solid var(--line); }}
.seg {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:14px; }}
.seg button {{ font:inherit; font-size:14px; padding:6px 14px; border:1px solid var(--line); background:#fff; border-radius:2px; cursor:pointer; color:var(--ink); }}
.seg button[aria-pressed="true"] {{ border-color:var(--accent); color:var(--accent); font-weight:600; }}
.fields {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:10px; }}
.fields label {{ font-size:13px; color:var(--muted); display:block; }}
.fields input {{ display:block; width:100%; margin-top:4px; font:inherit; font-size:14px; padding:7px 9px; border:1px solid var(--line); border-radius:2px; }}
.help {{ grid-column:1/-1; font-size:12px; color:var(--muted); margin:0; }}
.row {{ display:flex; justify-content:space-between; align-items:center; gap:12px; margin-top:14px; }}
.link-btn {{ font:inherit; font-size:13px; background:none; border:0; color:var(--accent-dark); cursor:pointer; text-decoration:underline; padding:0; }}
.err {{ color:var(--high); font-size:13px; margin:8px 0 0; min-height:1em; }} .status {{ font-size:13px; color:var(--muted); }}
footer {{ max-width:880px; margin:0 auto; padding:0 24px 40px; color:var(--muted); font-size:12px; }}"""


def _persona_label(audit: Audit, pid: str) -> str:
    for r in audit.runs:
        if r.persona and r.persona.id == pid:
            return r.persona.label
    return pid


def _count(n: int, word: str) -> str:
    return "" if not n else f"{n} {word}{'' if n == 1 else 's'}"


def _funnel_table(audit: Audit) -> str:
    rows = audit.funnels()
    if not rows:
        return ""
    out = ['<h2>How far each signup got</h2>', '<table><tr><th>Signup path</th><th>Got to</th><th>Hands-on (estimated)</th><th>Waiting (measured)</th><th>Asked of the user</th></tr>']
    for persona, s in rows:
        label = persona.label if persona else "New user (no personas set)"
        got = "Reached activation" if s["reached_activation"] else (f"Stuck at {s['stopped_at']}" if s["stopped_at"] else "Run ended early")
        parts = [_count(s[k], word) for k, word in (("screens", "screen"), ("clicks", "click"), ("fields", "field"), ("choices", "choice"))]
        if s["handoffs"]:
            parts.append(_count(s["handoffs"], "handoff") + " to the account owner")
        asked = ", ".join(p for p in parts if p) or "nothing"
        out.append(f"<tr><td>{e(label)}</td><td>{e(got)}</td><td>{fmt_duration(s['effort_s'])}</td><td>{fmt_duration(s['system_wait_s'])}</td><td>{e(asked)}</td></tr>")
    out.append("</table>")
    out.append('<p class="what">Hands-on time is estimated from the actions each step asked for, using keystroke-level model averages for a practiced user; first-time users will be slower. Waiting is measured.</p>')
    return "\n".join(out)


def _card(audit: Audit, f, n: int, tracker: dict | None) -> str:
    sev = SEV_CLASS[f.severity]
    what = OBSERVED[f.observed][1] if f.observed else ""
    seen = ", ".join(_persona_label(audit, p) for p in f.personas) or "the audit run"
    act = ""
    if tracker:
        if f.filed and not f.filed.get("returned"):
            act = f'<div class="actions"><a class="filed" href="{e(f.filed["url"])}" target="_blank" rel="noopener">Filed as {e(f.filed["id"])}</a></div>'
        else:
            url = file_url(f, audit.month, audit.report_url, tracker)
            back = f'<span class="hint">Came back after {e(f.filed["id"])} was closed</span>' if f.filed else '<span class="hint">Opens a prefilled ticket to review and submit</span>'
            act = f'<div class="actions"><a class="file" href="{e(url)}" target="_blank" rel="noopener">{e(button_label(tracker))}</a>{back}</div>'
    parts = [f'<div class="finding" id="finding-{n}">',
             f'<h3><span class="sev {sev}">{f.severity}</span>{e(f.title)}</h3>', act,
             f'<p class="what">{"What happened: " + e(what) + " · " if what else ""}Seen on: {e(seen)} · Confidence: {e(f.confidence)}</p>',
             f"<p>{e(f.actual)}</p>"]
    if f.category == "taste":
        parts.append(f'<p class="what">Your preference: “{e(f.preference)}”</p>')
    if f.affected:
        parts.append(f'<p class="data">Your data: {e(f.affected["share"])} (source: {e(f.affected["source"])})</p>')
    if f.fix:
        parts.append(f'<p class="fix">Fix: {e(f.fix)}</p>')
    if f.screenshot:
        cap = f"<figcaption>{e(f.caption)}</figcaption>" if f.caption else ""
        parts.append(f'<figure><img src="{e(f.screenshot)}" alt="{e(f.title)}">{cap}</figure>')
    parts.append("</div>")
    return "\n".join(p for p in parts if p)


NOTICE = """<div class="notice" id="connect" role="region" aria-label="Send findings to your tracker">
<div class="notice-head"><svg class="notice-icon" viewBox="0 0 16 16" width="18" height="18" aria-hidden="true"><circle cx="8" cy="8" r="7.25" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="7.25" y="7" width="1.5" height="4.5" fill="currentColor"/><rect x="7.25" y="4.2" width="1.5" height="1.6" fill="currentColor"/></svg>
<div class="notice-text"><strong>Send these findings to your tracker.</strong> Connect Jira, Linear or GitHub and each finding gets a button that opens a prefilled ticket to review and submit. Nothing is filed automatically, and settings stay in this browser.</div>
<div class="notice-actions"><button type="button" class="link-btn" id="connect-open" aria-expanded="false" aria-controls="connect-body">Connect tracker</button><button type="button" class="notice-close" id="connect-dismiss" aria-label="Dismiss">&times;</button></div></div>
<div class="notice-body" id="connect-body" hidden>
<div class="seg" role="group" aria-label="Tracker"><button type="button" data-t="jira" aria-pressed="false">Jira</button><button type="button" data-t="linear" aria-pressed="false">Linear</button><button type="button" data-t="github" aria-pressed="false">GitHub</button></div>
<div class="fields" id="fields-jira" hidden><label>Jira site<input id="j-site" placeholder="yourteam.atlassian.net" autocomplete="off"></label><label>Project ID (number)<input id="j-pid" inputmode="numeric" placeholder="10000" autocomplete="off"></label><label>Issue type ID (number)<input id="j-type" inputmode="numeric" placeholder="10004" autocomplete="off"></label><p class="help"><span id="j-find">Enter your site to get links that list your project IDs and issue type IDs.</span> Jira Cloud is retiring the old create page these links use, so try one link first.</p></div>
<div class="fields" id="fields-linear" hidden><p class="help">No setup needed. Tickets open in your default team; severity sets the priority and the report is attached.</p></div>
<div class="fields" id="fields-github" hidden><label>Repository<input id="g-repo" placeholder="owner/name or the repo URL" autocomplete="off"></label></div>
<p class="err" id="connect-err" role="alert"></p>
<div class="row" id="connect-row" hidden><span class="status" id="connect-status"></span><button type="button" class="link-btn" id="connect-clear" hidden>Remove buttons</button></div>
</div></div>"""

NOTICE_JS = r"""(function(){
var $=function(i){return document.getElementById(i)}, KEY="onboarding-audit-tracker-v1", DKEY="onboarding-audit-notice-dismissed", current=null, timer;
function load(){try{return JSON.parse(localStorage.getItem(KEY)||"null")}catch(e){return null}}
function save(v){try{v?localStorage.setItem(KEY,JSON.stringify(v)):localStorage.removeItem(KEY)}catch(e){}}
function cfgFrom(t){if(t==="jira")return{site:$("j-site").value,projectId:$("j-pid").value,issueTypeId:$("j-type").value};if(t==="linear")return{};return{repo:$("g-repo").value}}
function fill(t,c){if(!c)return;if(t==="jira"){$("j-site").value=c.site||"";$("j-pid").value=c.projectId||"";$("j-type").value=c.issueTypeId||""}if(t==="github")$("g-repo").value=c.repo||""}
function jiraFind(){var s=$("j-site").value.trim().replace(/\/$/,"");if(s&&!/^https?:\/\//.test(s))s="https://"+s;var ok=/^https:\/\/[\w.-]+\.[a-z]{2,}(:\d+)?$/i.test(s);
$("j-find").innerHTML=ok?'Find your <a href="'+s+'/rest/api/3/project" target="_blank" rel="noopener">project IDs</a> and <a href="'+s+'/rest/api/3/issuetype" target="_blank" rel="noopener">issue type IDs</a>: copy the <code>id</code> next to the name.':"Enter your site to get links that list your project IDs and issue type IDs."}
function clearButtons(){document.querySelectorAll(".finding .tracker-act").forEach(function(n){n.remove()})}
function render(t,cfg){var urls=FINDINGS.map(function(f){return AuditTracker.url(t,f,CTX,cfg)});clearButtons();
FINDINGS.forEach(function(f,i){var card=$("finding-"+f.n);if(!card)return;var d=document.createElement("div");d.className="tracker-act";var a=document.createElement("a");a.className="file";a.href=urls[i];a.target="_blank";a.rel="noopener";a.textContent="File in "+AuditTracker.NAMES[t];var h=document.createElement("span");h.className="hint";h.textContent="Opens a prefilled ticket to review and submit";d.appendChild(a);d.appendChild(h);card.querySelector("h3").insertAdjacentElement("afterend",d)});
$("connect-status").textContent=FINDINGS.length+" findings now have a File in "+AuditTracker.NAMES[t]+" button.";$("connect-clear").hidden=false}
function apply(showErr){if(!current)return;var cfg=cfgFrom(current);try{render(current,cfg);save({type:current,cfg:cfg});$("connect-err").textContent=""}catch(e){clearButtons();$("connect-status").textContent="";$("connect-clear").hidden=true;$("connect-err").textContent=showErr?e.message+".":""}}
function pick(t){current=t;document.querySelectorAll(".seg button").forEach(function(b){b.setAttribute("aria-pressed",String(b.dataset.t===t))});["jira","linear","github"].forEach(function(x){$("fields-"+x).hidden=x!==t});$("connect-row").hidden=false;$("connect-err").textContent="";apply(false)}
function setOpen(o){$("connect-body").hidden=!o;$("connect-open").setAttribute("aria-expanded",String(o));$("connect-open").textContent=o?"Hide setup":"Connect tracker"}
function setDismissed(d){$("connect").hidden=d;$("connect-reopen").hidden=!d;try{d?localStorage.setItem(DKEY,"1"):localStorage.removeItem(DKEY)}catch(e){}}
document.querySelectorAll(".seg button").forEach(function(b){b.addEventListener("click",function(){pick(b.dataset.t)})});
document.querySelectorAll(".fields input").forEach(function(i){i.addEventListener("input",function(){if(i.id==="j-site")jiraFind();clearTimeout(timer);timer=setTimeout(function(){apply(false)},300)});i.addEventListener("blur",function(){if(i.value.trim())apply(true)})});
$("connect-clear").addEventListener("click",function(){clearButtons();save(null);current=null;document.querySelectorAll(".seg button").forEach(function(b){b.setAttribute("aria-pressed","false")});["jira","linear","github"].forEach(function(x){$("fields-"+x).hidden=true});$("connect-status").textContent="";$("connect-clear").hidden=true});
$("connect-open").addEventListener("click",function(){setOpen($("connect-body").hidden)});
$("connect-dismiss").addEventListener("click",function(){setDismissed(true)});
$("connect-reopen").addEventListener("click",function(ev){ev.preventDefault();setDismissed(false);setOpen(true)});
var dis=false;try{dis=localStorage.getItem(DKEY)==="1"}catch(e){}if(dis)setDismissed(true);
var saved=load();if(saved&&saved.type){setOpen(true);fill(saved.type,saved.cfg);jiraFind();pick(saved.type)}
})();"""


def render_html(audit: Audit, config: dict, note: str = "") -> str:
    theme = {**DEFAULT_THEME, **config.get("theme", {})}
    rcfg = config.get("report", {})
    owner_tracker = config.get("tracker") if not rcfg.get("tracker_notice") else None
    merged = audit.merged()
    friction = [f for f in merged if f.category != "taste"]
    taste = [f for f in merged if f.category == "taste"]
    ordered = friction + taste
    for i, f in enumerate(ordered, 1):
        f.report_anchor = f"finding-{i}"
    c = audit.counts()
    personas = [r.persona for r in audit.runs if r.persona]
    meta = [audit.month, f"{len(audit.runs)} run{'s' if len(audit.runs) > 1 else ''}",
            f"personas: {', '.join(p.label for p in personas)}" if personas else "no personas set, one generic new-user run"]
    if rcfg.get("permission_note"):
        meta.append(rcfg["permission_note"])
    font = theme["font"].replace(" ", "+")
    body = [f'<header class="band"><div class="wrap"><h1>{e(audit.product)} signup audit</h1><div class="meta">{" · ".join(e(m) for m in meta)}</div></div></header>', "<main>"]
    if rcfg.get("tracker_notice"):
        body.append(NOTICE)
    if audit.summary:
        body.append(f'<p class="lead">{e(audit.summary)}</p>')
    body.append(f'<p class="what">{c["High"]} high, {c["Medium"]} medium, {c["Low"]} low{f", plus {len(taste)} against your taste preferences" if taste else ""}.</p>')
    body.append(_funnel_table(audit))
    body.append("<h2>Friction, ranked</h2>")
    body += [_card(audit, f, i, owner_tracker) for i, f in enumerate(friction, 1)]
    if taste:
        body.append("<h2>Against your taste preferences</h2>")
        body += [_card(audit, f, i, owner_tracker) for i, f in enumerate(taste, len(friction) + 1)]
    if audit.worked:
        body.append("<h2>What worked</h2><ul>" + "".join(f"<li>{e(w)}</li>" for w in audit.worked) + "</ul>")
    notes = [["Severity", "Set by what happened in the run: High means blocked or sent to the wrong person, Medium means a workaround or an error, Low means extra effort or polish. How many users are affected is shown only when the owner supplied data."]]
    if note:
        notes.append(["Ticket status", note])
    notes += audit.notes
    body.append("<h2>Run notes</h2><table><tr><th>Item</th><th>Note</th></tr>" + "".join(f"<tr><td>{e(a)}</td><td>{e(b)}</td></tr>" for a, b in notes) + "</table>")
    body.append("</main>")
    auditor = rcfg.get("auditor", "")
    foot = f"Independent audit{' by ' + e(auditor) if auditor else ''}. Not a publication of {e(audit.product)}."
    if rcfg.get("tracker_notice"):
        foot += ' <a href="#" id="connect-reopen" hidden>Show tracker setup</a>'
    body.append(f"<footer>{foot}</footer>")
    script = ""
    if rcfg.get("tracker_notice"):
        data = [{"n": i, "key": f.key, "severity": f.severity, "confidence": f.confidence, "title": f.title,
                 "steps": f.steps, "expected": f.expected, "actual": f.actual, "fix": f.fix} for i, f in enumerate(ordered, 1)]
        script = ("<script>" + (ASSETS / "tracker.js").read_text() + "\nvar FINDINGS=" + json.dumps(data).replace("</", "<\\/")
                  + ";\nvar CTX=" + json.dumps({"reportUrl": audit.report_url, "month": audit.month}) + ";\n" + NOTICE_JS + "</script>")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(audit.product)} signup audit, {e(audit.month)}</title>
<link href="https://fonts.googleapis.com/css2?family={e(font)}:wght@400;600&display=swap" rel="stylesheet">
<style>{_css(theme)}</style></head><body>
{chr(10).join(b for b in body if b)}
{script}</body></html>"""
