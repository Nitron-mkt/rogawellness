"""Rankeia influencers para o Roga Wellness Day a partir dos exports JSON do Apify.

Uso:
  # 1) Extrai usernames dos posts de hashtag/busca (para rodar no instagram-profile-scraper)
  python rank_influencers.py usernames hashtag_posts.json [search.json ...] > usernames.txt

  # 2) Rankeia os perfis exportados pelo apify/instagram-profile-scraper
  python rank_influencers.py rank profiles.json > ranking.csv

  # 3) Criadores wellness com e-mail na bio (export do instagram-search-scraper, searchType user)
  python rank_influencers.py creators search_users.json > criadores_email.csv
"""
import csv
import json
import re
import sys
from collections import Counter

MIN_FOLLOWERS = 50_000
MAX_FOLLOWERS = 2_000_000

AFFILIATE_BIO = re.compile(
    r"cupom|c[oó]digo|use meu|link na bio|desconto|%\s*off|afiliad|"
    r"linktr\.ee|beacons|hotmart|kiwify|eduzz|monetizze|amzn|amazon|"
    r"lnk\.bio|bio\.site|taplink",
    re.I,
)
PUBLI = re.compile(r"#publi|#ad\b|#publicidade|parceria|publipost|cupom|c[oó]digo\s+\w+", re.I)
COUPON_CAPTION = re.compile(r"cupom|c[oó]digo|use o|link na bio|%\s*off|desconto", re.I)
SP_REGION = re.compile(
    r"\bsp\b|s[aã]o paulo|campinas|atibaia|jundia[ií]|alphaville|"
    r"granja viana|bragan[cç]a|s[aã]o jos[eé] dos campos|valinhos|vinhedo|"
    r"santana de parna[ií]ba|barueri|santos|sorocaba",
    re.I,
)
NICHE = re.compile(
    r"yoga|pilates|funcional|corrida|maratona|trail|banho de gelo|cold|"
    r"breath|respira|medita|biohack|longevidade|sauna|sound|bem[- ]estar|"
    r"wellness|nutri|sa[uú]de|skincare|fit|treino|personal|beach tennis",
    re.I,
)
# Sinais de público 30-55 anos com renda (mulher madura, profissional, mãe)
MATURE_AUDIENCE = re.compile(
    r"m[aã]e d[eao]|maternidade|filhos|executiva|empres[aá]ria|fundadora|ceo|"
    r"m[eé]dica|dermato|nutr[oó]loga|endocrino|fisioterapeuta|psic[oó]loga|"
    r"menopausa|climat[eé]rio|40\+|50\+|longevidade|reposi[cç][aã]o hormonal|"
    r"marca pr[oó]pria|@\w+(store|shop|oficial)",
    re.I,
)
PREMIUM_BRANDS = re.compile(
    r"alo\b|aloyoga|lululemon|track\s*&?\s*field|trackandfield|\blive!|"
    r"wellhub|gympass|garmin|whoop|oura|oakley|fasano|botanique|kurotel|"
    r"txai|club med|smartfit|bodytech|technogym|on running|hoka|asics",
    re.I,
)


def load(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


def cmd_usernames(paths):
    counts = Counter()
    for path in paths:
        for item in load(path):
            name = item.get("ownerUsername") or item.get("username")
            if name:
                counts[name] += 1
    for name, _ in counts.most_common():
        print(name)


def score_profile(p):
    followers = p.get("followersCount") or 0
    bio = " ".join(filter(None, [p.get("biography"), p.get("fullName"),
                                 p.get("externalUrl"), p.get("businessCategoryName")]))
    posts = p.get("latestPosts") or []
    captions = [(x.get("caption") or "") for x in posts]
    all_text = bio + " " + " ".join(captions)

    interactions = [(x.get("likesCount") or 0) + (x.get("commentsCount") or 0) for x in posts]
    interactions = [i for i in interactions if i >= 0]
    engagement = (sum(interactions) / len(interactions) / followers * 100) if followers and interactions else 0

    publis = sum(1 for c in captions if PUBLI.search(c))
    coupon_posts = sum(1 for c in captions if COUPON_CAPTION.search(c))
    affiliate_bio = bool(AFFILIATE_BIO.search(bio))
    sp = bool(SP_REGION.search(all_text))
    niche_hits = len(set(m.lower() for m in NICHE.findall(all_text)))
    mature = len(set(m.lower() for m in MATURE_AUDIENCE.findall(all_text)))
    brands = sorted(set(m.lower() for m in PREMIUM_BRANDS.findall(all_text)))

    score = 0.0
    # Engajamento: alvo >= 1,5% (macro) / >= 2,5% (mid)
    target = 1.5 if followers >= 500_000 else 2.5
    score += min(engagement / target, 2) * 25
    # Hábito de afiliado / venda
    score += 20 if affiliate_bio else 0
    score += min(coupon_posts, 4) * 5
    # Publis: 1-6 em ~12 posts é saudável; acima disso, saturado
    score += 10 if 1 <= publis <= 6 else (3 if publis > 6 else 0)
    # Região e nicho
    score += 15 if sp else 0
    score += min(niche_hits, 5) * 3
    score += min(len(brands), 3) * 5
    score += min(mature, 3) * 6
    # Contas gigantes tendem a público jovem/massa: penaliza engajamento baixo
    if followers > 1_000_000 and engagement < 1:
        score -= 15

    return {
        "username": p.get("username"),
        "url": f"https://instagram.com/{p.get('username')}",
        "nome": p.get("fullName"),
        "seguidores": followers,
        "engajamento_%": round(engagement, 2),
        "afiliado_bio": affiliate_bio,
        "posts_com_cupom": coupon_posts,
        "publis_ultimos_posts": publis,
        "regiao_sp": sp,
        "nichos": niche_hits,
        "sinais_publico_30_55": mature,
        "marcas_premium": ", ".join(brands),
        "verificado": p.get("verified"),
        "categoria": p.get("businessCategoryName"),
        "link_bio": p.get("externalUrl"),
        "bio": (p.get("biography") or "").replace("\n", " "),
        "score": round(score, 1),
    }


def cmd_rank(paths):
    rows = []
    for path in paths:
        for p in load(path):
            followers = p.get("followersCount") or 0
            if MIN_FOLLOWERS <= followers <= MAX_FOLLOWERS and not p.get("private"):
                rows.append(score_profile(p))
    rows.sort(key=lambda r: r["score"], reverse=True)
    if not rows:
        sys.exit("Nenhum perfil dentro da faixa de seguidores.")
    w = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)


EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
STORE = re.compile(r"loja|store|shop|compre|frete|pedidos|whats.*encomend|cl[ií]nica|consult[oó]rio|agende|agendamento", re.I)
CREATOR_MIN, CREATOR_MAX = 10_000, 500_000


def _num(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def cmd_creators(paths):
    """Criadores wellness com e-mail na bio (export do instagram-search-scraper ou do profile-scraper)."""
    seen, rows = set(), []
    for path in paths:
        for p in load(path):
            u = p.get("username")
            if not u or u in seen:
                continue
            seen.add(u)
            bio = p.get("biography") or ""
            emails = EMAIL.findall(bio)
            followers = _num(p.get("followersCount"))
            text = " ".join(filter(None, [bio, p.get("fullName"), p.get("businessCategoryName")]))
            if not emails or not (CREATOR_MIN <= followers <= CREATOR_MAX) or not NICHE.search(text) or STORE.search(text):
                continue
            if str(p.get("private")).lower() == "true":
                continue
            score = (15 if SP_REGION.search(text) else 0) + min(len(set(m.lower() for m in NICHE.findall(text))), 5) * 3 \
                + min(len(set(m.lower() for m in MATURE_AUDIENCE.findall(text))), 3) * 6 \
                + (10 if 30_000 <= followers <= 200_000 else 0)
            rows.append({
                "score": score, "username": u, "perfil": f"https://instagram.com/{u}", "nome": p.get("fullName"),
                "seguidores": followers, "email": emails[0].rstrip("."), "regiao_sp": bool(SP_REGION.search(text)),
                "categoria": p.get("businessCategoryName"), "link_bio": p.get("externalUrl"),
                "bio": bio.replace("\n", " "),
            })
    rows.sort(key=lambda r: -r["score"])
    if not rows:
        sys.exit("Nenhum criador com e-mail na bio dentro dos filtros.")
    w = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()), delimiter=";")
    w.writeheader()
    w.writerows(rows)
    print(f"{len(rows)} criadores com e-mail", file=sys.stderr)


if __name__ == "__main__":
    cmds = {"usernames": cmd_usernames, "rank": cmd_rank, "creators": cmd_creators}
    if len(sys.argv) < 3 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    cmds[sys.argv[1]](sys.argv[2:])
