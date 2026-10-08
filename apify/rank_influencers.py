"""Rankeia influencers para o Roga Wellness Day a partir dos exports JSON do Apify.

Uso:
  # 1) Extrai usernames dos posts de hashtag/busca (para rodar no instagram-profile-scraper)
  python rank_influencers.py usernames hashtag_posts.json [search.json ...] > usernames.txt

  # 2) Rankeia os perfis exportados pelo apify/instagram-profile-scraper
  python rank_influencers.py rank profiles.json > ranking.csv
"""
import csv
import json
import re
import sys
from collections import Counter

MIN_FOLLOWERS = 100_000
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


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("usernames", "rank"):
        sys.exit(__doc__)
    {"usernames": cmd_usernames, "rank": cmd_rank}[sys.argv[1]](sys.argv[2:])
