"""Prospecção B2B (parceiros, eventos e comunidades) para o Roga Wellness Day a partir de exports do Apify.

Segue o briefing em briefing_gpt.md: só usa páginas públicas de empresas, só guarda contato
comercial publicado no site oficial e NÃO coleta dados de hóspedes, seguidores ou participantes.

Uso:
  # 1) Depois de rodar apify/google-search-scraper com ../inputs/5_google_search.json:
  #    lista URLs de novos locais/eventos para rodar no website-content-crawler (2ª rodada)
  python prospect_partners.py urls google.json > novas_urls.txt

  # 2) Depois de rodar apify/website-content-crawler (sementes e, opcionalmente, novas URLs):
  python prospect_partners.py build crawl_sementes.json [crawl_novos.json ...] --out saida/
"""
import argparse
import csv
import json
import math
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

HERE = Path(__file__).parent
EVENT_DAY = date(2026, 11, 7)
WINDOW_START = date(2025, 1, 1)
ATIBAIA = (-23.117, -46.550)

# Coordenadas aproximadas do centro do município, usadas para distância em LINHA RETA até Atibaia
# (não é distância rodoviária; confira no mapa antes de usar em material comercial).
CITY_COORDS = {
    "atibaia": (-23.117, -46.550), "mairipora": (-23.318, -46.587), "joanopolis": (-22.930, -46.274),
    "braganca paulista": (-22.952, -46.542), "piracaia": (-23.054, -46.358), "nazare paulista": (-23.181, -46.395),
    "jundiai": (-23.186, -46.884), "campinas": (-22.906, -47.061), "valinhos": (-22.971, -46.996),
    "vinhedo": (-23.030, -46.975), "itatiba": (-23.006, -46.839), "extrema": (-22.855, -46.318),
    "campos do jordao": (-22.739, -45.591), "santo antonio do pinhal": (-22.827, -45.663),
    "sao bento do sapucai": (-22.689, -45.731), "sao jose dos campos": (-23.180, -45.886),
    "sao paulo": (-23.550, -46.633), "cotia": (-23.604, -46.919), "embu das artes": (-23.649, -46.852),
    "santana de parnaiba": (-23.444, -46.918), "porto feliz": (-23.215, -47.524), "itu": (-23.264, -47.299),
    "sorocaba": (-23.502, -47.458), "ubatuba": (-23.434, -45.071), "ilhabela": (-23.778, -45.358),
    "sao sebastiao": (-23.760, -45.410), "rio de janeiro": (-22.907, -43.173), "penedo": (-22.433, -44.530),
    "lapa": (-25.770, -49.716), "gramado": (-29.379, -50.874), "lima duarte": (-21.844, -43.793),
    "itacare": (-14.278, -38.996),
}

ACTIVITIES = {
    "yoga": r"\byoga\b",
    "pilates": r"\bpilates\b",
    "breathwork": r"breathwork|respira[cç][aã]o consciente|t[eé]cnicas? de respira",
    "sound healing": r"sound\s*healing|banho de som|sound bath|ta[cç]as tibetanas|sound therapy",
    "meditação": r"medita[cç][aã]o|mindfulness",
    "banho de gelo": r"banho de gelo|cold\s*plunge|imers[aã]o no gelo|crioterapia",
    "sauna": r"\bsauna",
    "spa": r"\bspa\b|massagem|massagens",
    "trilha/natureza": r"trilha|caminhada|natureza|floresta|banho de floresta",
    "longevidade": r"longevidade|longevity|biohack",
    "nutrição": r"nutri[cç][aã]o|alimenta[cç][aã]o (?:saud|consc)|detox",
    "recovery": r"recovery|recupera[cç][aã]o muscular|fisioterapia",
}
ACTIVITIES = {k: re.compile(v, re.I) for k, v in ACTIVITIES.items()}
AFFINITY = {"yoga", "breathwork", "sound healing", "banho de gelo", "trilha/natureza", "meditação", "recovery", "longevidade"}

RELEVANT_PAGE = re.compile(
    r"agenda|evento|retiro|experi[eê]n|spa|wellness|bem-?estar|yoga|pacote|programa|imers|"
    r"parceir|facilitador|terapeut|sentir|healing|longev",
    re.I,
)
RETREAT = re.compile(r"retiro|imers[aã]o|vivência|jornada|semana tem[aá]tica|programa de \d+ dias", re.I)
PARTNERSHIP_PAGE = re.compile(r"parceir|patrocin|seja parceiro|eventos corporativos|corporativo|imprensa", re.I)
JUNK_LINE = re.compile(r"^(saiba mais|ver mais|leia mais|comprar|reservar?|inscreva-se|confira)\b|^[>\W]*$", re.I)
FACILITATOR = re.compile(r"facilitador|professor|terapeuta|instrutor|condu[zç]|com a? ?(?:prof|terapeuta)", re.I)

MONTHS = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6, "jul": 7, "ago": 8,
    "set": 9, "out": 10, "nov": 11, "dez": 12,
}
MONTH_ALT = "|".join(sorted(MONTHS, key=len, reverse=True))
# "25 a 31 de outubro de 2026", "25 de outubro", "25/10/2026", "25/10", "25 e 26/10"
DATE_RANGE_TXT = re.compile(rf"\b(\d{{1,2}})\s*(?:a|e|-|–|até)\s*(\d{{1,2}})\s+de\s+({MONTH_ALT})\.?(?:\s+(?:de\s+)?(\d{{4}}))?", re.I)
DATE_TXT = re.compile(rf"\b(\d{{1,2}})\s+(?:de\s+)?({MONTH_ALT})\.?(?:\s+(?:de\s+)?(\d{{4}}))?\b", re.I)
DATE_NUM = re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b")
PRICE = re.compile(r"R\$\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+(?:,\d{2})?)")
PRICE_CONTEXT = re.compile(
    r"por pessoa|p/ pessoa|por casal|casal|di[aá]ria|por noite|noite|pacote|quarto|apartamento|"
    r"day ?use|sess[aã]o|\d+ ?min|ingresso|parcel|por h[oó]spede",
    re.I,
)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?:\+?55\s?)?\(?\b[1-9]{2}\)?\s?\d{4,5}[-\s.]\d{4}\b")
BUSINESS_EMAIL_PREFIX = re.compile(
    r"^(contato|reservas?|eventos?|comercial|vendas|spa|marketing|parcerias?|atendimento|"
    r"recepcao|recep[cç][aã]o|hotel|info|sac|relacionamento|imprensa|grupos)", re.I,
)
INSTAGRAM = re.compile(r"https?://(?:www\.)?instagram\.com/([A-Za-z0-9_.]{2,30})/?", re.I)
INSTAGRAM_SKIP = {"p", "reel", "reels", "explore", "stories", "accounts", "tv", "about"}

# Domínios que não são o site oficial de um local (agregadores entram como fonte de evento)
SKIP_DOMAINS = re.compile(
    r"instagram\.com|facebook\.com|youtube\.com|tiktok\.com|linkedin\.com|twitter\.com|x\.com|"
    r"pinterest\.|google\.|wikipedia\.org|tripadvisor\.|booking\.com|decolar\.|hoteis\.com|"
    r"expedia\.|trivago\.|airbnb\.|reclameaqui\.|glassdoor\.|maps\.app",
    re.I,
)
EVENT_PLATFORMS = re.compile(r"sympla\.com\.br|eventbrite\.|even3\.com\.br|doity\.com\.br|ingresse\.com", re.I)


def load(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


def norm(text):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return text.lower().strip()


def canonical(url):
    parts = urlsplit(url.strip())
    host = parts.netloc.lower().removeprefix("www.")
    path = re.sub(r"/+$", "", parts.path) or "/"
    return urlunsplit(("https", host, path, "", ""))


def domain(url):
    return urlsplit(url).netloc.lower().removeprefix("www.")


def haversine(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return round(6371 * 2 * math.asin(math.sqrt(h)))


def distance_km(city):
    coords = CITY_COORDS.get(norm(city))
    return haversine(ATIBAIA, coords) if coords else None


def safe_date(y, m, d):
    try:
        return date(y, m, d)
    except ValueError:
        return None


def parse_dates(text, today):
    """Retorna lista de (data, ano_explicito). Sem ano no texto, assume a próxima ocorrência a partir de
    ~2 meses antes de `today` (confiança baixa)."""
    found = []

    def infer(month, day):
        for year in (today.year, today.year + 1):
            dt = safe_date(year, month, day)
            if dt and (today - dt).days <= 60:
                return dt
        return None

    def add(year, month, day):
        dt = safe_date(int(year), month, day) if year else infer(month, day)
        if dt:
            found.append((dt, bool(year)))

    for m in DATE_RANGE_TXT.finditer(text):
        month = MONTHS[norm(m.group(3))]
        d1, d2, year = int(m.group(1)), int(m.group(2)), m.group(4)
        add(year, month, d2)
        if d1 > d2:  # "29 a 05 de dezembro" -> começa no mês anterior
            pm = 12 if month == 1 else month - 1
            py = (int(year) - (1 if month == 1 else 0)) if year else None
            if py is None and found:
                end = found[-1][0]
                py = end.year - (1 if month == 1 else 0)
                dt = safe_date(py, pm, d1)
                if dt:
                    found.append((dt, False))
            else:
                add(py, pm, d1)
        else:
            add(year, month, d1)
    rest = DATE_RANGE_TXT.sub(" ", text)
    for m in DATE_TXT.finditer(rest):
        add(m.group(3), MONTHS[norm(m.group(2))], int(m.group(1)))
    for m in DATE_NUM.finditer(rest):
        day, month, year = int(m.group(1)), int(m.group(2)), m.group(3)
        if year and len(year) == 2:
            year = "20" + year
        add(year, month, day)
    return [(d, explicit) for d, explicit in found if WINDOW_START <= d <= date(2027, 12, 31)]


def parse_prices(text):
    prices = []
    for m in PRICE.finditer(text):
        value = float(m.group(1).replace(".", "").replace(",", "."))
        if value < 30:  # taxas, frete, valores de exemplo
            continue
        ctx = PRICE_CONTEXT.search(text[max(0, m.start() - 60): m.end() + 60])
        prices.append((value, ctx.group(0).lower() if ctx else None))
    return prices


def activities_in(text):
    return sorted(k for k, rx in ACTIVITIES.items() if rx.search(text))


def page_text(item):
    return item.get("markdown") or item.get("text") or ""


def page_url(item):
    crawl = item.get("crawl") or {}
    return item.get("url") or crawl.get("loadedUrl") or ""


def page_title(item):
    meta = item.get("metadata") or {}
    return (meta.get("title") or "").strip()


def load_seeds():
    with open(HERE / "seeds_locais.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def match_seed(url, seeds):
    best = None
    cu = canonical(url)
    for s in seeds:
        prefix = canonical(s["scope_prefix"])
        if cu == prefix or cu.startswith(prefix.rstrip("/") + "/") or (prefix.endswith("/") and cu.startswith(prefix)):
            if not best or len(prefix) > len(canonical(best["scope_prefix"])):
                best = s
    if best:
        return best
    for s in seeds:  # cai para o domínio
        if domain(s["url"]) == domain(url) and not s["group"]:
            return s
    return None


def guess_city(text):
    counts = Counter()
    t = norm(text)
    for city in CITY_COORDS:
        n = len(re.findall(rf"\b{re.escape(city)}\b", t))
        if n:
            counts[city] += n
    if not counts:
        return None
    city = counts.most_common(1)[0][0]
    return city.title()


def extract_events(item, place_id, today):
    """Um registro por linha datada (páginas de agenda) ou um programa contínuo por página relevante."""
    url, title, text = page_url(item), page_title(item), page_text(item)
    raw = [ln.strip() for ln in text.splitlines() if ln.strip(" #*|-\t")]
    lines = [ln.strip(" #*|-\t") for ln in raw]
    heading = [ln.startswith("#") for ln in raw]
    events = []
    seen = set()
    dated = [parse_dates(ln, today) for ln in lines]
    for i, line in enumerate(lines):
        dates = dated[i]
        if not dates:
            continue
        name = re.sub(DATE_RANGE_TXT, "", line)
        name = re.sub(DATE_TXT, "", name)
        name = re.sub(DATE_NUM, "", name).strip(" -–|,:•")
        # bloco do evento: da linha datada até a próxima linha datada (máx. 6 linhas)
        j = i + 1
        while j < len(lines) and j < i + 6 and not dated[j]:
            j += 1
        block_lines = lines[i:j]
        if len(name) < 8:
            # prioridade: cabeçalho logo acima > próxima linha "de título" > linha anterior > título da página
            def titleish(ln):
                return len(ln) >= 8 and not JUNK_LINE.search(ln) and not re.search(r"R\$|https?://|@", ln) and len(ln) <= 120
            prev_ok = i > 0 and not dated[i - 1] and titleish(lines[i - 1])
            near = [ln for ln in block_lines[1:] if titleish(ln)]
            if prev_ok and heading[i - 1]:
                name = lines[i - 1]
            elif near:
                name = near[0]
            elif prev_ok:
                name = lines[i - 1]
            else:
                name = title
        name = name[:140]
        block = " ".join(block_lines)
        ctx_text = f"{title} {name} {block}"
        acts = activities_in(ctx_text)
        if not acts and not RELEVANT_PAGE.search(ctx_text):
            continue
        ds = sorted(d for d, _ in dates)
        start, end = ds[0], ds[-1]
        key = (norm(name), start)
        if key in seen:
            continue
        seen.add(key)
        prices = parse_prices(block)
        events.append(make_event(
            place_id, url, title, name, start, end,
            "retreat" if RETREAT.search(ctx_text) else "dated_event",
            acts, prices, all(explicit for _, explicit in dates), today, block,
        ))
        if len(events) >= 40:
            break
    if not events and RELEVANT_PAGE.search(f"{url} {title}"):
        acts = activities_in(f"{title} {text}")
        if acts:
            events.append(make_event(
                place_id, url, title, title or url, None, None, "continuous_program",
                acts, parse_prices(text), False, today, text[:400],
            ))
    return events


def make_event(place_id, url, title, name, start, end, record_type, acts, prices, explicit_year, today, excerpt):
    if start is None:
        status = "unconfirmed"
    elif end < today:
        status = "past"
    elif start > today:
        status = "future"
    else:
        status = "ongoing"
    values = [p for p, _ in prices]
    contexts = sorted({c for _, c in prices if c})
    confidence = "medium" if (start and explicit_year) else "low"
    return {
        "place_id": place_id,
        "source_url": url,
        "record_type": record_type,
        "event_name": name or None,
        "start_date": start.isoformat() if start else None,
        "end_date": end.isoformat() if end else None,
        "temporal_status": status,
        "in_window_until_event": bool(start and today <= start <= EVENT_DAY) or bool(end and today <= end <= EVENT_DAY),
        "price_brl_min": min(values) if values else None,
        "price_brl_max": max(values) if values else None,
        "price_context": "; ".join(contexts) or None,
        "activities": acts,
        "evidence_excerpt": re.sub(r"\s+", " ", excerpt)[:240],
        "confidence": confidence,
        "scrape_status": "needs_review",
    }


def business_contacts(text, site_domain):
    emails = set()
    for e in EMAIL.findall(text):
        e = e.lower().rstrip(".")
        if re.search(r"\.(png|jpe?g|webp|gif|svg)$", e) or "sentry" in e or "example" in e:
            continue
        local, _, dom = e.partition("@")
        if dom.removeprefix("www.") == site_domain or BUSINESS_EMAIL_PREFIX.match(local):
            emails.add(e)
    phones = {re.sub(r"\s+", " ", p.strip()) for p in PHONE.findall(text)}
    return sorted(emails), sorted(phones)[:3]


def instagram_handles(text):
    return [h for h in INSTAGRAM.findall(text) if h.lower() not in INSTAGRAM_SKIP]


def score_place(p):
    dist = p["distance_km_linha_reta"]
    if dist is None:
        prox = 5
    elif dist <= 60:
        prox = 30
    elif dist <= 120:
        prox = 22
    elif dist <= 200:
        prox = 15
    elif dist <= 400:
        prox = 7
    else:
        prox = 0
    aff = min(25, 5 * len(AFFINITY & set(p["activities"])))
    if p["price_brl_min"] is not None and p["price_context"]:
        premium = 20
    elif p["price_brl_min"] is not None:
        premium = 10
    else:
        premium = 0
    org = min(15, (8 if p["n_future_events"] else 0) + (4 if p["facilitator_professional_urls"] else 0)
              + (3 if p["business_contact"] else 0))
    track = (5 if p["business_contact"] else 0) + (5 if p["has_partnership_page"] else 0)
    total = prox + aff + premium + org + track
    p["score"] = total
    p["score_breakdown"] = f"proximidade {prox}/30; afinidade {aff}/25; premium {premium}/20; organizadores {org}/15; mensuração {track}/10"
    p["priority"] = "A" if total >= 60 else "B" if total >= 40 else "C"


def partnership_angle(p):
    slug = re.sub(r"[^A-Z0-9]", "", norm(p["place_name"]).upper())[:10]
    acts = [a for a in p["activities"] if a in AFFINITY][:3]
    hook = ", ".join(acts) if acts else "bem-estar"
    if p["place_type"] in ("hotel", "resort"):
        base = "pacote hospedagem + ingresso para hóspedes/membros"
    elif p["place_type"] in ("festival", "comunidade", "studio"):
        base = "divulgação oficial para a comunidade com cupom exclusivo"
    else:
        base = "convite co-branded para a base opt-in do local"
    return f"{base}; ângulo {hook}; cupom ROGA{slug} + UTM utm_source={slug.lower()}"


def cmd_urls(paths):
    seeds = load_seeds()
    seed_domains = {domain(s["url"]) for s in seeds}
    seen = set()
    for path in paths:
        for page in load(path):
            for r in page.get("organicResults") or []:
                url = r.get("url") or ""
                d = domain(url)
                if not url or SKIP_DOMAINS.search(d):
                    continue
                if d in seed_domains and not RELEVANT_PAGE.search(url):
                    continue
                key = canonical(url) if EVENT_PLATFORMS.search(d) or d in seed_domains else d
                if key in seen:
                    continue
                seen.add(key)
                print(url)


def cmd_build(paths, out, today):
    seeds = load_seeds()
    out.mkdir(parents=True, exist_ok=True)
    accessed_default = datetime.now(timezone.utc).isoformat(timespec="seconds")

    pages_by_place = defaultdict(list)
    errors = []
    new_places = {}
    seen_urls = set()
    for path in paths:
        for item in load(path):
            url = page_url(item)
            if not url:
                continue
            cu = canonical(url)
            if cu in seen_urls:
                continue
            seen_urls.add(cu)
            crawl = item.get("crawl") or {}
            status = crawl.get("httpStatusCode")
            if (status and status >= 400) or len(page_text(item)) < 80:
                errors.append({"url": url, "problema": f"HTTP {status}" if status and status >= 400 else "página vazia/bloqueada"})
                continue
            seed = match_seed(url, seeds)
            if seed:
                pid = seed["place_id"]
            else:
                d = domain(url)
                key = cu if EVENT_PLATFORMS.search(d) else d
                if key not in new_places:
                    new_places[key] = f"N{len(new_places) + 1:03d}"
                pid = new_places[key]
            pages_by_place[pid].append(item)

    places, events, partners = [], [], []
    seed_by_id = {s["place_id"]: s for s in seeds}
    all_ids = [s["place_id"] for s in seeds] + sorted(set(new_places.values()))
    for pid in all_ids:
        items = pages_by_place.get(pid, [])
        seed = seed_by_id.get(pid)
        if not items:
            if seed:
                errors.append({"url": seed["url"], "problema": f"semente {pid} sem páginas coletadas (bloqueio, robots.txt ou fora do escopo do crawl)"})
            continue
        items.sort(key=lambda it: len(canonical(page_url(it))))
        full_text = "\n".join(page_text(it) for it in items)
        site = domain(page_url(items[0]))
        if seed:
            name, city, state, ptype = seed["place_name"], seed["city"], seed["state"], seed["place_type"]
            official = seed["url"]
            city_conf = "high"
        else:
            name = page_title(items[0]).split("|")[0].split(" - ")[0].strip() or site
            city = guess_city(full_text)
            state = None
            ptype = "festival" if EVENT_PLATFORMS.search(site) else "retiro" if RETREAT.search(full_text[:3000]) else "venue"
            official = page_url(items[0])
            city_conf = "low"

        place_events = []
        for it in items:
            place_events.extend(extract_events(it, pid, today))
        for ev in place_events:
            ev["accessed_at"] = next(((it.get("crawl") or {}).get("loadedTime") for it in items if page_url(it) == ev["source_url"]), None) or accessed_default
            ev["place_name"] = name

        emails, phones = business_contacts(full_text, site)
        handles = Counter(h.lower() for h in instagram_handles(full_text))
        site_key = norm(site.split(".")[0])
        org_handle = next((h for h, _ in handles.most_common() if site_key[:5] in h or h in norm(name).replace(" ", "")), None)
        if not org_handle and handles:
            org_handle = handles.most_common(1)[0][0]
        facilitators = set()
        for it in items:
            t = page_text(it)
            if FACILITATOR.search(t):
                facilitators.update(h.lower() for h in instagram_handles(t))
        facilitators.discard(org_handle)

        relevant_prices = [(e["price_brl_min"], e["price_brl_max"], e["price_context"]) for e in place_events if e["price_brl_min"]]
        acts = sorted({a for e in place_events for a in e["activities"]} or set(activities_in(full_text)))
        place = {
            "place_id": pid,
            "place_name": name,
            "city": city,
            "state": state,
            "city_confidence": city_conf,
            "place_type": ptype,
            "official_url": official,
            "source_url": page_url(items[0]),
            "accessed_at": (items[0].get("crawl") or {}).get("loadedTime") or accessed_default,
            "distance_km_linha_reta": distance_km(city) if city else None,
            "pages_collected": len(items),
            "activities": acts,
            "n_future_events": sum(1 for e in place_events if e["temporal_status"] in ("future", "ongoing")),
            "n_events_until_roga_day": sum(1 for e in place_events if e["in_window_until_event"]),
            "price_brl_min": min((p[0] for p in relevant_prices), default=None),
            "price_brl_max": max((p[1] for p in relevant_prices), default=None),
            "price_context": "; ".join(sorted({p[2] for p in relevant_prices if p[2]})) or None,
            "organization_social_url": f"https://instagram.com/{org_handle}" if org_handle else None,
            "facilitator_professional_urls": sorted(f"https://instagram.com/{h}" for h in facilitators)[:10],
            "business_contact": "; ".join(emails + phones) or None,
            "has_partnership_page": any(PARTNERSHIP_PAGE.search(f"{page_url(it)} {page_title(it)}") for it in items),
            "scrape_status": "success" if seed else "needs_review",
            "confidence": "medium" if seed else "low",
        }
        score_place(place)
        if seed and seed["priority_hint"] and seed["priority_hint"] != place["priority"]:
            place["priority_note"] = f"briefing sugeria {seed['priority_hint']}"
        place["partnership_angle"] = partnership_angle(place)
        places.append(place)
        events.extend(place_events)

        partners.append({
            "place_id": pid, "organizer_name": name, "role": "organizador/local",
            "organization_social_url": place["organization_social_url"], "facilitator_professional_url": None,
            "business_contact": place["business_contact"], "source_url": place["source_url"], "accessed_at": place["accessed_at"],
        })
        for url in place["facilitator_professional_urls"]:
            partners.append({
                "place_id": pid, "organizer_name": name, "role": "facilitador (perfil profissional citado no site do local)",
                "organization_social_url": None, "facilitator_professional_url": url,
                "business_contact": None, "source_url": place["source_url"], "accessed_at": place["accessed_at"],
            })

    places.sort(key=lambda p: -p["score"])
    events.sort(key=lambda e: (e["start_date"] or "9999", e["place_id"]))
    write_outputs(out, places, events, partners, errors, today)


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: "|".join(v) if isinstance(v, list) else v for k, v in r.items()})


def write_outputs(out, places, events, partners, errors, today):
    place_fields = [
        "place_id", "place_name", "city", "state", "city_confidence", "place_type", "official_url", "source_url",
        "accessed_at", "distance_km_linha_reta", "pages_collected", "activities", "n_future_events",
        "n_events_until_roga_day", "price_brl_min", "price_brl_max", "price_context", "organization_social_url",
        "facilitator_professional_urls", "business_contact", "has_partnership_page", "partnership_angle", "score",
        "score_breakdown", "priority", "priority_note", "confidence", "scrape_status",
    ]
    event_fields = [
        "place_id", "place_name", "source_url", "accessed_at", "record_type", "event_name", "start_date", "end_date",
        "temporal_status", "in_window_until_event", "price_brl_min", "price_brl_max", "price_context", "activities",
        "evidence_excerpt", "confidence", "scrape_status",
    ]
    partner_fields = [
        "place_id", "organizer_name", "role", "organization_social_url", "facilitator_professional_url",
        "business_contact", "source_url", "accessed_at",
    ]
    write_csv(out / "roga_locais_enriquecidos.csv", places, place_fields)
    write_csv(out / "roga_eventos_wellness.csv", events, event_fields)
    write_csv(out / "roga_parceiros_publicos.csv", partners, partner_fields)
    with open(out / "roga_prospeccao.json", "w", encoding="utf-8") as f:
        json.dump({"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "reference_date": today.isoformat(),
                   "places": places, "events": events, "partners": partners, "errors": errors}, f, ensure_ascii=False, indent=2)

    lines = ["# Top 20 oportunidades B2B · Roga Wellness Day (07/11/2026)", "",
             "Pontuação heurística 0–100 do briefing (não é dado observado). Distância em linha reta até Atibaia. "
             "Valide datas e preços na página-fonte antes de citar.", ""]
    for i, p in enumerate(places[:20], 1):
        upcoming = [e for e in events if e["place_id"] == p["place_id"] and e["in_window_until_event"]]
        lines += [
            f"## {i}. {p['place_name']} — {p['score']} pts (prioridade {p['priority']})",
            f"- **Local:** {p['city'] or '?'}/{p['state'] or '?'} · {p['distance_km_linha_reta'] or '?'} km de Atibaia · {p['place_type']}",
            f"- **Por quê:** {p['score_breakdown']}",
            f"- **Atividades:** {', '.join(p['activities']) or '—'}",
            f"- **Preço público:** {fmt_price(p)}",
            f"- **Eventos até 07/11:** {len(upcoming)}" + (f" (ex.: {upcoming[0]['event_name']} em {upcoming[0]['start_date']})" if upcoming else ""),
            f"- **Ação sugerida:** {p['partnership_angle']}",
            f"- **Argumento:** público premium de {', '.join(p['activities'][:3]) or 'bem-estar'} com perfil do Roga Day; ativação mensurável por cupom/UTM, sem compartilhar dados de clientes.",
            f"- **Contato comercial público:** {p['business_contact'] or 'não encontrado'} · {p['organization_social_url'] or ''} · {p['official_url']}",
            f"- **Evidência:** {p['confidence']} · fonte {p['source_url']}", "",
        ]
    (out / "roga_top20_oportunidades.md").write_text("\n".join(lines), encoding="utf-8")

    err = ["# Erros e limitações da coleta", "",
           "- Datas sem ano no texto foram assumidas como 2026 (confidence=low); todos os eventos estão como `needs_review`.",
           "- Distâncias são em linha reta a partir do centro do município; cidade de locais novos é inferida do texto (city_confidence=low).",
           "- Preços extraídos por padrão `R$`; o contexto (pessoa, casal, diária) só aparece quando escrito perto do valor.", "",
           "| URL | Problema |", "|---|---|"]
    err += [f"| {e['url']} | {e['problema']} |" for e in errors] or ["| — | nenhum erro registrado |"]
    missing = [p for p in places if not p["city"] or not p["business_contact"]]
    if missing:
        err += ["", "## Campos faltantes", ""]
        err += [f"- {p['place_id']} {p['place_name']}: " + ", ".join(
            x for x, ok in (("cidade", p["city"]), ("contato comercial", p["business_contact"])) if not ok) for p in missing]
    (out / "roga_erros_de_coleta.md").write_text("\n".join(err) + "\n", encoding="utf-8")
    print(f"{len(places)} locais, {len(events)} eventos/programas, {len(partners)} parceiros, {len(errors)} erros -> {out}", file=sys.stderr)


def fmt_price(p):
    if p["price_brl_min"] is None:
        return "não publicado"
    rng = f"R$ {p['price_brl_min']:,.0f}" if p["price_brl_min"] == p["price_brl_max"] else f"R$ {p['price_brl_min']:,.0f}–{p['price_brl_max']:,.0f}"
    return f"{rng.replace(',', '.')} ({p['price_context'] or 'unidade não informada'})"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("urls")
    u.add_argument("google_json", nargs="+")
    b = sub.add_parser("build")
    b.add_argument("crawl_json", nargs="+")
    b.add_argument("--out", default="saida")
    b.add_argument("--today", default=date.today().isoformat(), help="data de referência para futuro/passado (YYYY-MM-DD)")
    args = ap.parse_args()
    if args.cmd == "urls":
        cmd_urls(args.google_json)
    else:
        cmd_build(args.crawl_json, Path(args.out), date.fromisoformat(args.today))


if __name__ == "__main__":
    main()
