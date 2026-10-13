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
import re
import sys
from collections import defaultdict

from rank_influencers import MATURE_AUDIENCE, NICHE, PREMIUM_BRANDS, SP_REGION, load

MAX_FOLLOWERS = 30_000   # acima disso é criador/influencer, não comprador
MIN_POSTS = 3            # filtra perfis vazios/bots
MIN_COMMENTS_ON_POST = 5

# Intenção forte: pergunta de compra / quer ir
INTENT_STRONG = re.compile(
    r"quero (?:ir|muito|participar|fazer)|onde (?:compr|vend|é|fica)|como (?:fa[cç]o|faz|participo|compro)|"
    r"quanto|valor|pre[cç]o|ingresso|link|tem vaga|pr[oó]xim[ao] (?:edi[cç][aã]o|data|turma|evento)|"
    r"quando (?:vai|tem|ser[aá])|vai ter|me (?:avisa|chama|manda)|inscri|vou (?:sim|estar|participar)|"
    r"bora\b|partiu|vamos\??$",
    re.I,
)
# Interesse: desejo/afinidade
INTENT_SOFT = re.compile(
    r"quero|preciso|sonho|amo|amei|que demais|incr[ií]vel|maravilh|necessito|que vontade|apaixonad|"
    r"top demais|perfeito|lindo|experi[eê]ncia|fiz e amei|j[aá] fiz|melhor coisa",
    re.I,
)
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


def suggested_dm(lead):
    hi = f"Oi, {lead['nome']}!" if lead["nome"] else "Oi!"
    where = f"no post da @{lead['post_owner']}" if lead["post_owner"] else "num post"
    tema = lead["tema"]
    if lead["intencao"] == "forte":
        return (f"{hi} Vi seu comentário {where} sobre {tema} e lembrei de você 😊 "
                f"Dia 07/11 vai rolar o Roga Wellness Day em Atibaia: um dia inteiro de {tema}, natureza e bem-estar. "
                f"Quer que eu te mande a programação e o link do ingresso?")
    if lead["marcou_amigo"]:
        return (f"{hi} Vi que você marcou alguém {where} sobre {tema} 💛 "
                f"Dia 07/11 tem o Roga Wellness Day em Atibaia, um dia de {tema} e bem-estar — ótimo para ir junto. "
                f"Posso te mandar os detalhes?")
    return (f"{hi} Vi seu comentário {where} sobre {tema}. "
            f"Estamos organizando o Roga Wellness Day (07/11, Atibaia), um dia todo dedicado a isso. "
            f"Posso te mandar a programação?")


def cmd_posts(paths):
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
    for _, _, url in rows:
        print(url)
    total = sum(c for _, c, _ in rows)
    print(f"{len(rows)} posts, {total} comentários no total", file=sys.stderr)


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


def cmd_commenters(paths):
    by_user = collect_comments(paths, {})
    ranked = sorted(by_user.values(), key=lambda cs: -max(comment_score(c)[0] for c in cs) - 5 * len(cs))
    for cs in ranked:
        if max(comment_score(c)[0] for c in cs) > 0:
            print(cs[0]["username"])


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
        if SP_REGION.search(bio):
            score += 20
            reasons.append("SP na bio")
        elif SP_REGION.search(context):
            score += 8
            reasons.append("post/evento em SP")
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

        lead = {
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
        lead["dm_sugerida"] = suggested_dm(lead)
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
    sub.add_parser("posts").add_argument("json", nargs="+")
    inf = sub.add_parser("influencers")
    inf.add_argument("ranking_csv")
    inf.add_argument("--top", type=int, default=30)
    sub.add_parser("commenters").add_argument("json", nargs="+")
    r = sub.add_parser("rank")
    r.add_argument("--comments", nargs="+", required=True)
    r.add_argument("--profiles", nargs="+", required=True)
    r.add_argument("--posts", nargs="*", default=[])
    a = ap.parse_args()
    if a.cmd == "posts":
        cmd_posts(a.json)
    elif a.cmd == "influencers":
        cmd_influencers(a.ranking_csv, a.top)
    elif a.cmd == "commenters":
        cmd_commenters(a.json)
    else:
        cmd_rank(a.comments, a.profiles, a.posts)


if __name__ == "__main__":
    main()
