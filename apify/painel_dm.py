"""Gera o painel de envio de DMs (HTML único, abre no navegador, sem publicar nada).

Uso:
  python painel_dm.py leads.csv > painel_dm.html

Cada card tem: [Abrir Direct] (ig.me abre a conversa direto), [Copiar DM], [Perfil],
[Enviado] e [Não contatar]. O progresso fica salvo no navegador e pode ser exportado em CSV.
"""
import csv
import html
import json
import sys

DAILY_LIMIT = 30


def read_leads(path):
    with open(path, encoding="utf-8-sig") as f:
        sample = f.read(4096)
        f.seek(0)
        delim = ";" if sample.count(";") > sample.count(",") else ","
        return list(csv.DictReader(f, delimiter=delim))


def build(leads):
    data = [{
        "u": r["username"], "nome": r.get("nome") or "", "score": r.get("score") or "",
        "intencao": r.get("intencao") or "", "motivos": r.get("motivos") or "",
        "comentario": r.get("comentario") or "", "post": r.get("post") or "",
        "privado": str(r.get("privado")).lower() == "true", "bio": r.get("bio") or "",
        "dm": r.get("dm_sugerida") or "",
    } for r in leads if r.get("username")]
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.replace("__DATA__", payload).replace("__LIMIT__", str(DAILY_LIMIT))


TEMPLATE = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Painel de DMs · Roga</title>
<style>
:root{--bg:#f6f4ef;--card:#fff;--ink:#1f2a24;--mute:#6b746e;--line:#e3dfd6;--accent:#2f6b4f;--accent-ink:#fff;--warn:#b5651d;--done:#e8f1ec;--no:#f3e9e6}
@media (prefers-color-scheme:dark){:root{--bg:#121513;--card:#1b201d;--ink:#e8ece9;--mute:#9aa49e;--line:#2c332f;--accent:#5fae86;--accent-ink:#0d130f;--warn:#e0a060;--done:#1d2b23;--no:#2d2220}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
header{position:sticky;top:0;z-index:2;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 16px}
.wrap{max-width:760px;margin:0 auto}h1{font-size:18px;margin:0 0 6px}
.stats{display:flex;gap:14px;flex-wrap:wrap;color:var(--mute);font-size:13px}.stats b{color:var(--ink)}
.bar{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap}
.bar button,.actions a,.actions button{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:7px 11px;font:inherit;font-size:14px;cursor:pointer;text-decoration:none}
.bar button.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
main{padding:12px 16px 60px}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;margin:0 0 12px}
.card.sent{background:var(--done)}.card.skip{background:var(--no);opacity:.7}
.top{display:flex;justify-content:space-between;gap:8px;align-items:baseline;flex-wrap:wrap}
.who{font-weight:600}.who small{color:var(--mute);font-weight:400}
.tag{font-size:12px;padding:2px 8px;border-radius:99px;border:1px solid var(--line);color:var(--mute);margin-left:4px}
.tag.forte{color:var(--accent);border-color:var(--accent)}.tag.priv{color:var(--warn);border-color:var(--warn)}
.meta{color:var(--mute);font-size:13px;margin:6px 0}.meta q{color:var(--ink)}
textarea{width:100%;min-height:110px;border:1px solid var(--line);border-radius:8px;padding:10px;font:inherit;background:var(--bg);color:var(--ink);resize:vertical}
.actions{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
.actions .primary{background:var(--accent);color:var(--accent-ink);border-color:var(--accent);font-weight:600}
.warn{color:var(--warn);font-size:13px;margin-top:6px}
.toast{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);background:var(--ink);color:var(--bg);padding:8px 14px;border-radius:8px;opacity:0;transition:.2s;pointer-events:none}.toast.show{opacity:1}
</style></head><body>
<header><div class="wrap">
<h1>Painel de DMs · Roga Wellness Day</h1>
<div class="stats"><span>Enviadas hoje: <b id="today">0</b>/__LIMIT__</span><span>Total enviadas: <b id="sent">0</b></span><span>Pendentes: <b id="pend">0</b></span></div>
<div class="bar"><button data-f="pend" class="on">Pendentes</button><button data-f="sent">Enviadas</button><button data-f="skip">Não contatar</button><button data-f="all">Todas</button><button id="export">Exportar CSV</button></div>
</div></header>
<main class="wrap" id="list"></main>
<div class="toast" id="toast"></div>
<script>
const LEADS = __DATA__, LIMIT = __LIMIT__, KEY = "roga_dm_status_v1";
let state = {}; try { state = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} };
const today = () => new Date().toISOString().slice(0, 10);
let filter = "pend";
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function toast(t){const el=document.getElementById("toast");el.textContent=t;el.classList.add("show");setTimeout(()=>el.classList.remove("show"),1600)}
async function copy(text){try{await navigator.clipboard.writeText(text)}catch(e){const t=document.createElement("textarea");t.value=text;document.body.appendChild(t);t.select();document.execCommand("copy");t.remove()}}
function stats(){const v=Object.values(state);document.getElementById("today").textContent=v.filter(s=>s.st==="sent"&&s.at===today()).length;document.getElementById("sent").textContent=v.filter(s=>s.st==="sent").length;document.getElementById("pend").textContent=LEADS.filter(l=>!(state[l.u]||{}).st).length}
function render(){
  const list=document.getElementById("list");list.innerHTML="";
  LEADS.forEach(l=>{
    const s=state[l.u]||{};const st=s.st||"pend";
    if(filter!=="all"&&filter!==st)return;
    const c=document.createElement("div");c.className="card "+(st==="sent"?"sent":st==="skip"?"skip":"");
    c.innerHTML=`<div class="top"><div class="who">${l.nome?esc(l.nome)+" <small>@"+esc(l.u)+"</small>":"@"+esc(l.u)}</div>
      <div>${l.intencao==="forte"?'<span class="tag forte">intenção forte</span>':""}${l.privado?'<span class="tag priv">privado</span>':""}<span class="tag">score ${esc(l.score)}</span></div></div>
      <div class="meta">Comentou: <q>${esc(l.comentario)}</q>${l.post?` · <a href="${esc(l.post)}" target="_blank" rel="noopener">ver post</a>`:""}</div>
      <div class="meta">${esc(l.motivos)}${l.bio?" · "+esc(l.bio):""}</div>
      <textarea>${esc(s.dm||l.dm)}</textarea>
      ${l.privado?'<div class="warn">Perfil privado: a DM vai para "Solicitações de mensagem". Não precisa seguir.</div>':""}
      <div class="actions">
        <button class="primary" data-a="go">1 · Copiar e abrir Direct</button>
        <a href="https://www.instagram.com/${encodeURIComponent(l.u)}/" target="_blank" rel="noopener">Perfil</a>
        <button data-a="sent">${st==="sent"?"✓ Enviada":"2 · Marcar enviada"}</button>
        <button data-a="skip">${st==="skip"?"Desfazer":"Não contatar"}</button>
      </div>`;
    const ta=c.querySelector("textarea");
    ta.addEventListener("input",()=>{state[l.u]=Object.assign({},state[l.u],{dm:ta.value});save()});
    c.querySelector('[data-a="go"]').onclick=async()=>{await copy(ta.value);toast("DM copiada — cole no Direct");window.open("https://ig.me/m/"+encodeURIComponent(l.u),"_blank")};
    c.querySelector('[data-a="sent"]').onclick=()=>{
      const sentToday=Object.values(state).filter(x=>x.st==="sent"&&x.at===today()).length;
      if(st!=="sent"&&sentToday>=LIMIT&&!confirm(`Já foram ${sentToday} hoje. Passar do limite aumenta o risco de bloqueio. Marcar mesmo assim?`))return;
      state[l.u]=Object.assign({},state[l.u],st==="sent"?{st:undefined,at:undefined}:{st:"sent",at:today()});save();stats();render()};
    c.querySelector('[data-a="skip"]').onclick=()=>{state[l.u]=Object.assign({},state[l.u],{st:st==="skip"?undefined:"skip"});save();stats();render()};
    list.appendChild(c);
  });
  if(!list.children.length)list.innerHTML='<p style="color:var(--mute)">Nada aqui.</p>';
}
document.querySelectorAll("[data-f]").forEach(b=>b.onclick=()=>{filter=b.dataset.f;document.querySelectorAll("[data-f]").forEach(x=>x.classList.toggle("on",x===b));render()});
document.getElementById("export").onclick=()=>{
  const rows=[["username","status","enviado_em","dm"]].concat(LEADS.map(l=>{const s=state[l.u]||{};return[l.u,s.st||"pendente",s.at||"",s.dm||l.dm]}));
  const csv=rows.map(r=>r.map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(";")).join("\n");
  const a=document.createElement("a");a.href=URL.createObjectURL(new Blob(["﻿"+csv],{type:"text/csv"}));a.download="dm_status_"+today()+".csv";a.click()};
stats();render();
</script></body></html>
"""


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.stdout.write(build(read_leads(sys.argv[1])))
