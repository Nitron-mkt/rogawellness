"""Rankeia influencers para o Roga Wellness Day a partir dos exports JSON do Apify.

Uso:
  # 1) Extrai usernames dos posts de hashtag/busca (para rodar no instagram-profile-scraper)
  python rank_influencers.py usernames hashtag_posts.json [search.json ...] > usernames.txt

  # 2) Rankeia os perfis exportados pelo apify/instagram-profile-scraper
  python rank_influencers.py rank profiles.json > ranking.csv

  # Score v4: educador de bem-estar com comunidade que compra (curso, formação, alunos, retiro)
  python rank_influencers.py rank --min 15000 --max 0 profiles.json > ranking_educadores.csv

  # Parceria (permuta, evento em conjunto, co-venda): só 500 mil+, sem teto
  python rank_influencers.py rank --min 500000 --max 0 profiles.json > ranking_parceria.csv

  # 3) Expande a base pelos "perfis relacionados" do profile-scraper (rodar de novo)
  python rank_influencers.py related profiles.json > usernames_relacionados.txt
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
    r"santana de parna[ií]ba|barueri|santos ?[-/,] ?sp|baixada santista|sorocaba|ribeir[aã]o preto|piracicaba|"
    r"guarulhos|osasco|s[aã]o bernardo|santo andr[eé]|mogi|indaiatuba|itu\b|"
    r"crm[- /]?sp|cref[^\n]{0,15}sp|crn[- ]?3\b",
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
    r"marca pr[oó]pria|@\w+(?:store|shop|oficial)",
    re.I,
)
PREMIUM_BRANDS = re.compile(
    r"alo\b|aloyoga|lululemon|track\s*&?\s*field|trackandfield|\blive!|"
    r"wellhub|gympass|garmin|whoop|oura|oakley|fasano|botanique|kurotel|"
    r"txai|club med|smartfit|bodytech|technogym|on running|hoka|asics",
    re.I,
)
# Lugares e viagens de alto padrão nos posts: público que paga ticket alto
HIGH_INCOME = re.compile(
    r"fasano|hotel unique|rosewood|cidade jardim|jk iguatemi|iguatemi|jardins|itaim|"
    r"vila nova concei|faria lima|trancoso|noronha|uxua|botanique|kurotel|txai|"
    r"club med|mykonos|amalfi|paris|london|londres|nova york|new york|dubai|tulum|"
    r"maldiv|aspen|lululemon|aloyoga|alo\b|on running|whoop|oura|garmin",
    re.I,
)
# Já produz evento próprio: candidato a co-criar um evento no Roga
EVENTS = re.compile(
    r"retiro|imers[aã]o|workshop|evento|encontro|ingresso|sympla|eventbrite|"
    r"vagas|turn[eê]|aul[aã]o|vivência|festival|summit|experi[eê]ncia",
    re.I,
)
# Vende produto próprio para a audiência: aceita permuta e co-venda em vez de cachê
OWN_PRODUCT = re.compile(
    r"curso|mentoria|m[eé]todo|programa|comunidade|assinatura|clube|app\b|"
    r"e-?book|desafio|marca pr[oó]pria|hotmart|kiwify|eduzz|@\w+(?:store|shop|oficial|brand)",
    re.I,
)

# Educador com comunidade: vende curso/formação/mentoria e tem alunos (o perfil ideal do Roga)
EDUCATOR = re.compile(
    r"alun[oa]s|turma|forma[cç][aã]o|mentoria|mentorad|curso|m[eé]todo|escola|instituto|"
    r"inscri[cç][oõ]es|lista de espera|vagas (?:abertas|limitadas)|matr[ií]cula|certifica|"
    r"programa de \w+|comunidade|membros|assinatura|plataforma|aulas? ao vivo|"
    r"hotmart|kiwify|eduzz|memberkit|greenn|ticto|monetizze|cademi|herospark|sympla",
    re.I,
)
# "+20 mil alunas", "4.000 alunos": comunidade já comprou dele
STUDENTS = re.compile(r"\+?\s?(\d+[.,]?\d*)\s?(mil|k)?\s+(alun[oa]s|mentorad[oa]s|membros|pacientes atendid|mulheres transformad|pessoas transformad|vidas transformad|praticantes)", re.I)
# Produto de ticket alto em bem-estar: experiência presencial e transformação longa
HIGH_TICKET = re.compile(
    r"retiro|imers[aã]o|presencial|forma[cç][aã]o|mentoria|vivência|jornada|"
    r"r\$\s?\d\.?\d{3}|\b(?:1|2|3|4|5)\.?\d{3},?\d{0,2} reais|12x|parcel",
    re.I,
)
WELLNESS_CORE = re.compile(
    r"yoga|medita|mindful|respira|breath|pranayama|sound|ta[cç]a tibetana|ayurveda|"
    r"longevidade|integrativ|funcional|anti-?inflama|desinflama|jejum|horm[oô]ni|menopausa|"
    r"sono|estresse|ansiedade|autoconhecimento|banho de gelo|crioterapia|trilha|montanha|"
    r"trail|ultra|natureza|pilates|mobilidade|corrida|nutri",
    re.I,
)
# Celebridade/entretenimento: audiência grande mas não compra transformação de bem-estar
CELEB = re.compile(r"\batriz\b|\bator\b|apresentador|tv host|cantor|modelo\b|\bmodel\b|reality|bbb|"
                   r"actress|actor|jornalista|influenciadora de moda|fashion|deputad|vereador|senador|#22\b", re.I)
CELEB_CATEGORY = re.compile(r"actor|artist|musician|\\btv\\b|politic|fashion|model", re.I)

# Texto em português: separa criador brasileiro de estrangeiro (espanhol divide "para", "con")
PT_BR = re.compile(r"ç[aã]o|ções|\bvoc[eê]\b|\bn[aã]o\b|\bbrasil|🇧🇷|\bsa[uú]de\b|\bpra\b", re.I)
# Conta de marca, app ou veículo: não é influencer para permuta
BRAND_CATEGORY = re.compile(r"brand|marca|product|produto|app page|company|empresa|media|news|shopping|retail", re.I)

# Já aceitou experiência em troca de conteúdo: o melhor indício de que topa permuta
INVITE = re.compile(r"a convite|#convite|convidad[ao] (d[aeo]|pel[ao])|#recebido|recebidos|"
                    r"hospedad[ao]|#hospedagem|cortesia|#press|presskit|experi[eê]ncia (incr|[uú]nica)", re.I)
# Página, corte ou canal temático: não é uma pessoa que pode viver o Roga
PAGE = re.compile(r"trechos|cortes|clips|\bdicas|receitas|frases|memes|curiosidades|pensament|"
                  r"fatos|not[ií]cias|humor \w+ e|entre no grupo|promo[cç][oõ]es|p[aá]gina|"
                  r"filmes|s[eé]ries|cl[aá]ssicos|achados|ofertas|perfil oficial d[aeo] (programa|marca)", re.I)
# Fala na primeira pessoa, profissão ou vida pessoal: indício de pessoa (confirmar olhando o perfil)
PERSON = re.compile(r"\b(eu|minha|meu|sou|m[aã]e d|pai d|esposa|marido)\b|cref|crn|crm|"
                    r"professor|treinador|nutricionista|m[eé]dic[oa]|atleta|personal", re.I)


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


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return 0 if not n else (xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2)


def score_profile(p):
    """Score 0-100 (v4): educador de bem-estar com comunidade que compra.

    Comunidade/infoproduto 40 · ticket alto 20 · engajamento 15 · SP 10 · nicho wellness 15.
    Celebridade sem produto de educação perde metade; sem nenhum sinal de educador, fica com 40%.

    "pessoa_real" e "brasil" não entram no score: são filtro. Conta que não é pessoa não deve
    ser rankeada, deve sair da lista.
    """
    followers = p.get("followersCount") or 0
    bio = " ".join(filter(None, [p.get("biography"), p.get("fullName"),
                                 p.get("externalUrl"), p.get("businessCategoryName")]))
    posts = p.get("latestPosts") or []
    captions = [(x.get("caption") or "") for x in posts]
    all_text = bio + " " + " ".join(captions)

    # Mediana, não média: um viral não pode carregar o perfil
    valid = [x for x in posts if (x.get("likesCount") or 0) >= 0]
    eng = median([((x.get("likesCount") or 0) + (x.get("commentsCount") or 0)) / followers * 100
                  for x in valid]) if followers else 0
    com = median([(x.get("commentsCount") or 0) / followers * 100 for x in valid]) if followers else 0

    publis = sum(1 for c in captions if PUBLI.search(c))
    coupon_posts = sum(1 for c in captions if COUPON_CAPTION.search(c))
    affiliate_bio = bool(AFFILIATE_BIO.search(bio))
    invites = sum(1 for c in captions if INVITE.search(c))
    # Localização marcada nos posts é o sinal mais forte de onde a pessoa vive
    locations = [x.get("locationName") or "" for x in posts]
    sp_posts = sum(1 for loc in locations if loc and SP_REGION.search(loc))
    sp = bool(SP_REGION.search(all_text)) or sp_posts > 0
    niche_hits = len(set(m.lower() for m in NICHE.findall(all_text)))
    mature = len(set(m.lower() for m in MATURE_AUDIENCE.findall(all_text)))
    brands = sorted(set(m.lower() for m in PREMIUM_BRANDS.findall(all_text)))
    events = len(set(m.lower() for m in EVENTS.findall(all_text)))
    own_product = len(set(m.lower() for m in OWN_PRODUCT.findall(all_text)))
    brasil = len(PT_BR.findall(all_text)) >= 3
    marca = bool(BRAND_CATEGORY.search(p.get("businessCategoryName") or ""))
    pagina = bool(PAGE.search(" ".join(filter(None, [p.get("username"), p.get("fullName"), p.get("biography")]))))
    pessoa = not (marca or pagina) and bool(PERSON.search(all_text))

    # v4 · "educador de bem-estar com comunidade que já compra": comunidade 40 · ticket 20 · engajamento 15 · SP 10 · nicho 15
    edu = len(set(m.lower() for m in EDUCATOR.findall(all_text)))
    students = 0
    for n, mil, _ in STUDENTS.findall(all_text):
        try:
            v = float(n.replace(".", "").replace(",", "."))
        except ValueError:
            continue
        students = max(students, int(v * 1000 if mil else v))
    ticket = len(set(m.lower() for m in HIGH_TICKET.findall(all_text)))
    core = len(set(m.lower() for m in WELLNESS_CORE.findall(all_text)))
    celeb = bool(CELEB.search(bio)) or bool(CELEB_CATEGORY.search(p.get("businessCategoryName") or ""))

    # 1. Comunidade que compra (40): sinais de curso/formação + alunos declarados + já faz evento
    s_comm = min(edu, 6) * 4 + (10 if students >= 1000 else 5 if students > 0 else 0) + min(events, 2) * 3
    s_comm = min(s_comm, 40)
    # 2. Ticket alto (20): retiro, imersão, formação, mentoria, preço de 4 dígitos, alta renda nos posts
    locs_text = " ".join(locations)
    high_income = len(set(m.lower() for m in HIGH_INCOME.findall(all_text + " " + locs_text)))
    s_ticket = min(min(ticket, 4) * 4 + min(high_income, 2) * 2 + min(len(brands), 1) * 2, 20)
    # 3. Engajamento real (15): mediana contra o porte, comentário pesa (comunidade conversa)
    bench = 1.5 if followers < 1_000_000 else (1.0 if followers < 3_000_000 else 0.7)
    s_eng = min(eng / bench, 1.0) * 9 + min(com / 0.03, 1.0) * 6
    # 4. SP (10) e 5. nicho wellness (15)
    s_sp = 10 if sp_posts > 0 else (6 if sp else 0)
    s_fit = min(core, 5) * 3
    score = s_comm + s_ticket + s_eng + s_sp + s_fit
    # Celebridade sem produto de educação não é o perfil: corta pela metade
    if celeb and edu < 3:
        score *= 0.5
    # Sem nenhum sinal de curso/aluno/comunidade: não é educador, vai para o fim
    if edu == 0:
        score *= 0.4
    # Mantidos para referência (modelo v3 de permuta)
    s_perm = min(min(invites, 2) * 6 + min(events, 2) * 4 + min(own_product, 2) * 2
                 + (3 if affiliate_bio or coupon_posts else 0) + (1 if 1 <= publis <= 6 else 0), 30)

    return {
        "username": p.get("username"),
        "url": f"https://instagram.com/{p.get('username')}",
        "nome": p.get("fullName"),
        "seguidores": followers,
        "pessoa_real": pessoa,
        "brasil": brasil,
        "engajamento_mediano_%": round(eng, 2),
        "comentarios_mediano_%": round(com, 3),
        "posts_a_convite": invites,
        "sinais_evento": events,
        "sinais_produto_proprio": own_product,
        "afiliado_bio": affiliate_bio,
        "posts_com_cupom": coupon_posts,
        "publis_ultimos_posts": publis,
        "regiao_sp": sp,
        "posts_em_sp": sp_posts,
        "nichos": niche_hits,
        "sinais_publico_30_55": mature,
        "marcas_premium": ", ".join(brands),
        "sinais_alta_renda": high_income,
        "verificado": p.get("verified"),
        "categoria": p.get("businessCategoryName"),
        "link_bio": p.get("externalUrl"),
        "bio": (p.get("biography") or "").replace("\n", " "),
        "sinais_educador": edu,
        "alunos_declarados": students,
        "sinais_ticket_alto": ticket,
        "nicho_wellness": core,
        "celebridade": celeb,
        "score_comunidade": round(s_comm, 1),
        "score_ticket": round(s_ticket, 1),
        "score_engajamento": round(s_eng, 1),
        "score_sp": s_sp,
        "score_fit": round(s_fit, 1),
        "score_permuta_v3": round(s_perm, 1),
        "score": round(score, 1),
    }


def cmd_rank(args):
    lo, hi, paths = MIN_FOLLOWERS, MAX_FOLLOWERS, []
    it = iter(args)
    for a in it:
        if a == "--min":
            lo = int(next(it))
        elif a == "--max":
            hi = int(next(it)) or float("inf")
        else:
            paths.append(a)
    rows, seen = [], set()
    for path in paths:
        for p in load(path):
            followers = p.get("followersCount") or 0
            if p.get("username") in seen:
                continue
            seen.add(p.get("username"))
            if lo <= followers <= hi and not p.get("private"):
                rows.append(score_profile(p))
    # Pessoa real e brasileira primeiro: o resto fica no fim só para conferência
    rows.sort(key=lambda r: (r["pessoa_real"] and r["brasil"], r["score"]), reverse=True)
    if not rows:
        sys.exit("Nenhum perfil dentro da faixa de seguidores.")
    w = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)


def cmd_related(paths):
    known, counts = set(), Counter()
    for path in paths:
        for p in load(path):
            known.add(p.get("username"))
            for r in p.get("relatedProfiles") or []:
                if r.get("username"):
                    counts[r["username"]] += 1
    for name, _ in counts.most_common():
        if name not in known:
            print(name)


if __name__ == "__main__":
    cmds = {"usernames": cmd_usernames, "rank": cmd_rank, "related": cmd_related}
    if len(sys.argv) < 3 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    cmds[sys.argv[1]](sys.argv[2:])
