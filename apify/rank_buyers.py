"""Lista de possíveis compradores do Roga Wellness Day para abordagem por DM MANUAL.

Fonte: pessoas que comentaram publicamente em posts de wellness/eventos (hashtags e influencers).
Guarda só o mínimo: @, primeiro nome, comentário e link do post — sem telefone/e-mail.

Uso:
  # 1) Posts com comentários que valem raspar (exports do instagram-hashtag-scraper e/ou instagram-scraper)
  python rank_buyers.py posts hashtags.json [influencer_posts.json ...] > post_urls.txt

  # (opcional) URLs dos perfis do top do ranking de influencers para o instagram-scraper
  python rank_buyers.py influencers ranking.csv --top 30 > influencer_urls.txt

  # 2) Usernames de quem comentou (export do instagram-comment-scraper), para o instagram-profile-scraper
  python rank_buyers.py commenters comments.json > commenters.txt

  # 3) Ranking final com DM sugerida
  python rank_buyers.py rank --comments comments.json --profiles commenter_profiles.json \
      [--posts hashtags.json influencer_posts.json] > leads.csv
"""
import argparse
import ast
import csv
import json
import re
import sys
from collections import defaultdict

from rank_influencers import MATURE_AUDIENCE, NICHE, PREMIUM_BRANDS, SP_REGION, load

MAX_FOLLOWERS = 30_000   # acima disso é criador/influencer, não comprador
MIN_POSTS = 3            # filtra perfis vazios/bots
MIN_COMMENTS_ON_POST = 5
PRICE_PER_RESULT = 2.60 / 1000  # Apify plano Free (comentários e perfis)

# Intenção forte: pergunta de compra / quer ir
INTENT_STRONG = re.compile(
    r"quero (?:ir|muito|participar|fazer)|j[aá] quero|me convid|quero conhecer|quero viver|onde (?:compr|vend|é|fica)|como (?:fa[cç]o|faz|participo|compro)|"
    r"quanto (?:custa|[eé]\b|fica|sai|t[aá]\b|ser[aá])|qual (?:o )?valor|valores|valor\?|pre[cç]o|ingresso|"
    r"(?:cad[eê]|qual|tem|manda|passa)\W+(?:o )?link|link (?:da|de|pra|para) (?:inscri|compra)|tem vaga|"
    r"pr[oó]xim[ao] (?:edi[cç][aã]o|data|turma|evento)|quando (?:vai|tem|ser[aá]|abre)|vai ter|"
    r"me (?:avisa|chama|manda)|(?:como|onde|quando)\b.{0,25}inscri|inscri[cç][oõ]es? (?:abert|abre)|"
    r"n[aã]o consegui\b.{0,30}inscri|vou (?:sim|estar|participar)",
    re.I,
)
# Profissionais e negócios do nicho: tendem a responder oferecendo serviço. Viram lista de parceiros/afiliados.
PROFESSIONAL = re.compile(
    r"terapeut|terapias|instrutor|professor|prof[ªa]\b|personal|massoterap|facilitador|yogini|coach|nutricionist|"
    r"psic[oó]log|fisioterap|esteticist|studio|est[uú]dio|espa[cç]o\b|cl[ií]nica|agend|atendimento|consult[oó]rio|"
    r"cursos?\b|aulas?\b|mentor|ayurv|reiki|sound ?heal|healer|\bcrp\b|\bcrn\b|crefito|rep\. comercial|"
    r"idealizador|fundador|unhas|sal[aã]o|doceria|papelaria|snacks|skin|nutrition|loja|@\w+(?:store|shop)",
    re.I,
)
# Quem está vendendo/repassando não é comprador
SELLER = re.compile(r"\bvendo\b|repasso|troco titularidade|transfiro", re.I)
# Sinais de que a pessoa mora longe de SP (bio ou local dos posts)
OTHER_REGION = re.compile(
    r"\b(?:rj|mg|ba|pr|sc|rs|df|go|pe|ce|es|am|pa|mt|ms|rn|pb|al|se|pi|ma|to|ro)\b|rio de janeiro|niter[oó]i|maric[aá]|"
    r"floripa|florian[oó]polis|bras[ií]lia|belo horizonte|\bbh\b|curitiba|salvador|recife|fortaleza|"
    r"porto alegre|goi[aâ]nia|vit[oó]ria|natal|manaus|bel[eé]m|bauru|ribeir[aã]o preto|portugal|lisboa|\bporto\b|rio tinto|braga\b|🇵🇹|"
    r"\busa\b|eua|miami|argentina|paraguai",
    re.I,
)

# Interesse: desejo/afinidade
INTENT_SOFT = re.compile(
    r"quero|preciso|sonho|amo|amei|que demais|incr[ií]vel|maravilh|necessito|que vontade|apaixonad|"
    r"top demais|perfeito|lindo|experi[eê]ncia|fiz e amei|j[aá] fiz|melhor coisa|bora\b|partiu|vamos",
    re.I,
)
GIVEAWAY = re.compile(r"sorteio|sortear|giveaway|concorrer|marque \d|marque (?:um|uma|dois|duas|seus|suas|amig)|ganhador|regras?:", re.I)
MENTION = re.compile(r"@([A-Za-z0-9_.]{2,30})")
SPAM = re.compile(r"promo|divulga|parceria\?|collab|seguidores|sigam|follow|dm (?:pra|para)|chama no direct|"
                  r"ganhe|renda extra|https?://", re.I)

THEMES = [
    ("banho de gelo", re.compile(r"banho de gelo|cold ?plunge|gelo|crio", re.I)),
    ("breathwork", re.compile(r"breath|respira", re.I)),
    ("sound healing", re.compile(r"sound|banho de som|ta[cç]as", re.I)),
    ("yoga", re.compile(r"yoga|ioga", re.I)),
    ("corrida", re.compile(r"corrida|maratona|running|trail", re.I)),
    ("longevidade", re.compile(r"longevidade|biohack", re.I)),
    ("retiro", re.compile(r"retiro|imers", re.I)),
]


# Alguns exports do Apify vêm com números e listas como texto ("12", "['a', 'b']")
def num(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def as_list(value):
    if isinstance(value, str):
        try:
            value = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return []
    return value if isinstance(value, list) else []


def as_bool(value):
    return value is True or str(value).lower() == "true"


PORTUGUESE = re.compile(r"\b(voc[eê]|n[aã]o|para|muito|com|mais|dia|corpo|sa[uú]de|treino|tamb[eé]m|hoje|aqui)\b", re.I)


def first_name(full_name):
    name = re.sub(r"[^\wÀ-ÿ\s'-]", " ", full_name or "").strip()
    first = name.split()[0] if name.split() else ""
    return first.capitalize() if 2 <= len(first) <= 15 and not any(ch.isdigit() for ch in first) else ""


def theme_of(text):
    for theme, rx in THEMES:
        if rx.search(text or ""):
            return theme
    return "bem-estar"


# Proposta do evento. "Emoções" no lugar de "espírito" para não gerar objeção religiosa.
PITCH = [
    "o Roga Wellness Day: 12 horas de experiências para cuidar do corpo, da mente e das emoções, no meio da natureza em Atibaia",
    "o Roga Wellness Day, em Atibaia: são 12 horas de experiências pensadas para cuidar do corpo, acalmar a mente e equilibrar as emoções",
    "o Roga Wellness Day: um dia inteiro (12 horas!) de experiências para desacelerar e cuidar de corpo, mente e emoções, em meio à natureza de Atibaia",
]
CLOSE_STRONG = [
    "Quer que eu te mande a programação completa e o link do ingresso?",
    "Posso te mandar a programação e os valores?",
    "Te mando a programação completa?",
]
CLOSE_SOFT = [
    "Posso te mandar a programação?",
    "Quer conhecer a programação?",
    "Se fizer sentido pra você, te mando os detalhes 😊",
]


def suggested_dm(lead):
    """DM personalizada; o texto varia por pessoa (hash do @) para não sair idêntico em todas."""
    k = sum(map(ord, lead["username"]))
    hi = f"Oi, {lead['nome']}, tudo bem?" if lead["nome"] else "Oi, tudo bem?"
    where = f"no post da @{lead['post_owner']}" if lead["post_owner"] else "num post"
    pitch = PITCH[k % len(PITCH)]
    date = "Dia 07/11 acontece"
    if lead["intencao"] == "forte":
        return (f"{hi} Vi seu comentário {where} e achei que você ia curtir saber disso 😊 "
                f"{date} {pitch}. {CLOSE_STRONG[k % len(CLOSE_STRONG)]}")
    if lead["marcou_amigo"]:
        return (f"{hi} Vi que você marcou alguém {where} 💛 "
                f"{date} {pitch}. É o tipo de dia perfeito pra viver junto com quem a gente gosta. "
                f"{CLOSE_SOFT[k % len(CLOSE_SOFT)]}")
    return (f"{hi} Vi seu comentário {where} e pelo seu perfil acho que você vai se identificar 🌿 "
            f"{date} {pitch}. {CLOSE_SOFT[k % len(CLOSE_SOFT)]}")


def partner_dm(lead):
    """Profissionais do nicho: convite para indicar o evento à própria comunidade, com comissão/cupom."""
    hi = f"Oi, {lead['nome']}, tudo bem?" if lead["nome"] else "Oi, tudo bem?"
    return (f"{hi} Vi seu trabalho por aqui e achei muito alinhado com o que estamos criando 🌿 "
            f"Dia 07/11 acontece o Roga Wellness Day, em Atibaia: 12 horas de experiências para cuidar do corpo, "
            f"da mente e das emoções. Estamos buscando profissionais parceiros para indicar o evento aos seus "
            f"alunos e clientes, com cupom exclusivo e comissão por ingresso vendido. Posso te explicar como funciona?")


def cmd_posts(paths, max_posts=0, per_post=0):
    seen = set()
    rows = []
    for path in paths:
        for p in load(path):
            url = p.get("url")
            comments = num(p.get("commentsCount"))
            text = " ".join(filter(None, [p.get("caption"), p.get("locationName"), " ".join(map(str, as_list(p.get("hashtags"))))]))
            if (not url or url in seen or comments < MIN_COMMENTS_ON_POST or not NICHE.search(text)
                    or not PORTUGUESE.search(p.get("caption") or "")):
                continue
            seen.add(url)
            # SP e posts de evento primeiro
            prio = (2 if SP_REGION.search(text) else 0) + (1 if re.search(r"evento|retiro|imers|ingresso|vagas", text, re.I) else 0)
            rows.append((prio, comments, url))
    rows.sort(reverse=True)
    rows = rows[:max_posts] if max_posts else rows
    for _, _, url in rows:
        print(url)
    total = sum(min(c, per_post) if per_post else c for _, c, _ in rows)
    print(f"{len(rows)} posts, até {total} comentários "
          f"(~US$ {total * PRICE_PER_RESULT:.2f})", file=sys.stderr)


def cmd_extract_comments(paths):
    """Converte os latestComments que o instagram-scraper já traz junto dos posts para o formato do
    instagram-comment-scraper (economiza rodar o raspador de comentários). Ignora posts de sorteio."""
    out, skipped = [], 0
    for path in paths:
        for p in load(path):
            if p.get("error") or not p.get("url"):
                continue
            if GIVEAWAY.search(p.get("caption") or ""):
                skipped += 1
                continue
            for c in as_list(p.get("latestComments")):
                if (isinstance(c, dict) and c.get("ownerUsername")
                        and c["ownerUsername"].lower() != (p.get("ownerUsername") or "").lower()):
                    out.append({"postUrl": p["url"], "ownerUsername": c["ownerUsername"], "text": c.get("text") or "",
                                "timestamp": c.get("timestamp") or ""})
    json.dump(out, sys.stdout, ensure_ascii=False)
    print(f"{len(out)} comentários extraídos ({skipped} posts de sorteio ignorados)", file=sys.stderr)


def cmd_influencers(path, top):
    with open(path, encoding="utf-8-sig") as f:
        for i, row in enumerate(csv.DictReader(f)):
            if i >= top:
                break
            print(f"https://www.instagram.com/{row['username']}/")


def collect_comments(paths, post_owner):
    by_user = defaultdict(list)
    for path in paths:
        for c in load(path):
            user = c.get("ownerUsername") or (c.get("owner") or {}).get("username")
            text = (c.get("text") or "").strip()
            post_url = c.get("postUrl") or c.get("inputUrl") or ""
            if not user or not text or SPAM.search(text):
                continue
            owner = post_owner.get(post_url.rstrip("/"))
            if owner and owner.lower() == user.lower():
                continue  # dono do post respondendo
            by_user[user.lower()].append({"username": user, "text": text, "post_url": post_url,
                                          "owner": owner, "timestamp": c.get("timestamp") or ""})
    return by_user


def comment_score(c):
    text = c["text"]
    strong = bool(INTENT_STRONG.search(text))
    soft = bool(INTENT_SOFT.search(text))
    tagged = bool(MENTION.search(text))
    return (30 if strong else 0) + (12 if soft else 0) + (15 if tagged else 0), strong, tagged


def cmd_commenters(paths, limit=0):
    by_user = collect_comments(paths, {})
    ranked = sorted(by_user.values(), key=lambda cs: -max(comment_score(c)[0] for c in cs) - 5 * len(cs))
    names = [cs[0]["username"] for cs in ranked if max(comment_score(c)[0] for c in cs) > 0]
    names = names[:limit] if limit else names
    print("\n".join(names))
    print(f"{len(names)} perfis (~US$ {len(names) * PRICE_PER_RESULT:.2f})", file=sys.stderr)


def cmd_rank(comment_paths, profile_paths, post_paths):
    post_owner, post_text = {}, {}
    for path in post_paths:
        for p in load(path):
            if p.get("url"):
                key = p["url"].rstrip("/")
                post_owner[key] = p.get("ownerUsername")
                post_text[key] = " ".join(filter(None, [p.get("caption"), p.get("locationName")]))
    by_user = collect_comments(comment_paths, post_owner)
    profiles = {}
    for path in profile_paths:
        for p in load(path):
            if p.get("username"):
                profiles[p["username"].lower()] = p
    influencers = {o.lower() for o in post_owner.values() if o}

    rows = []
    for key, comments in by_user.items():
        prof = profiles.get(key)
        if not prof or key in influencers:
            continue
        followers = num(prof.get("followersCount"))
        if followers > MAX_FOLLOWERS or num(prof.get("postsCount")) < MIN_POSTS:
            continue
        if as_bool(prof.get("isBusinessAccount")) and not re.search(r"pessoal|criador|blogueir|atleta|personal", prof.get("businessCategoryName") or "", re.I):
            continue  # loja/clínica/estúdio: não é comprador final

        comments = [c for c in comments if not SELLER.search(c["text"])]
        if not comments:
            continue
        scored = sorted(((comment_score(c), c) for c in comments), key=lambda x: -x[0][0])
        (best_pts, strong, tagged), best = scored[0]
        posts = {c["post_url"] for c in comments}
        bio = " ".join(filter(None, [prof.get("biography"), prof.get("fullName"), prof.get("businessCategoryName")]))
        context = bio + " " + " ".join(post_text.get(c["post_url"].rstrip("/"), "") for c in comments)

        score = best_pts
        reasons = []
        if strong:
            reasons.append("pergunta/intenção de compra")
        if tagged:
            reasons.append("marcou amigo")
        if len(posts) > 1:
            score += min(len(posts) - 1, 4) * 8
            reasons.append(f"comentou em {len(posts)} posts do nicho")
        post_places = " ".join(str(x.get("locationName") or "") for x in as_list(prof.get("latestPosts")) if isinstance(x, dict))
        if SP_REGION.search(bio):
            score += 20
            reasons.append("SP na bio")
        elif SP_REGION.search(post_places):
            score += 12
            reasons.append("posta de SP")
        elif OTHER_REGION.search(bio) or OTHER_REGION.search(post_places):
            score -= 25
            reasons.append("parece ser de fora de SP")
        elif SP_REGION.search(context):
            score += 4
            reasons.append("comentou em post de SP")
        mature = len(set(m.lower() for m in MATURE_AUDIENCE.findall(bio)))
        if mature:
            score += min(mature, 2) * 8
            reasons.append("sinais 30-55/profissional")
        if PREMIUM_BRANDS.search(context):
            score += 5
            reasons.append("marcas premium")
        if NICHE.search(bio):
            score += 5
            reasons.append("nicho na bio")
        if not prof.get("profilePicUrl") and not prof.get("profilePicUrlHD"):
            score -= 10

        tipo = "profissional" if PROFESSIONAL.search(f"{bio} {prof['username']}") else "consumidor"
        lead = {
            "tipo": tipo,
            "username": prof["username"],
            "perfil": f"https://instagram.com/{prof['username']}",
            "nome": first_name(prof.get("fullName")),
            "score": score,
            "intencao": "forte" if strong else "media" if best_pts else "fraca",
            "marcou_amigo": tagged,
            "motivos": "; ".join(reasons),
            "comentario": best["text"].replace("\n", " ")[:200],
            "post": best["post_url"],
            "post_owner": best["owner"] or "",
            "data_comentario": best["timestamp"][:10],
            "tema": theme_of(post_text.get(best["post_url"].rstrip("/"), "") + " " + best["text"]),
            "seguidores": followers,
            "privado": as_bool(prof.get("private")),
            "bio": (prof.get("biography") or "").replace("\n", " ")[:160],
        }
        lead["dm_sugerida"] = partner_dm(lead) if tipo == "profissional" else suggested_dm(lead)
        lead.update({"status": "", "enviado_em": "", "respondeu": "", "comprou": ""})
        rows.append(lead)

    rows.sort(key=lambda r: -r["score"])
    if not rows:
        sys.exit("Nenhum lead: confira se os JSON de comentários e perfis batem.")
    w = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    po = sub.add_parser("posts")
    po.add_argument("json", nargs="+")
    po.add_argument("--max-posts", type=int, default=0, help="só os N melhores posts")
    po.add_argument("--per-post", type=int, default=0, help="resultsLimit que será usado no comment scraper (para estimar custo)")
    inf = sub.add_parser("influencers")
    inf.add_argument("ranking_csv")
    inf.add_argument("--top", type=int, default=30)
    sub.add_parser("extract-comments").add_argument("json", nargs="+")
    co = sub.add_parser("commenters")
    co.add_argument("json", nargs="+")
    co.add_argument("--max", type=int, default=0, help="só os N perfis com mais intenção")
    r = sub.add_parser("rank")
    r.add_argument("--comments", nargs="+", required=True)
    r.add_argument("--profiles", nargs="+", required=True)
    r.add_argument("--posts", nargs="*", default=[])
    a = ap.parse_args()
    if a.cmd == "posts":
        cmd_posts(a.json, a.max_posts, a.per_post)
    elif a.cmd == "extract-comments":
        cmd_extract_comments(a.json)
    elif a.cmd == "influencers":
        cmd_influencers(a.ranking_csv, a.top)
    elif a.cmd == "commenters":
        cmd_commenters(a.json, a.max)
    else:
        cmd_rank(a.comments, a.profiles, a.posts)


if __name__ == "__main__":
    main()
