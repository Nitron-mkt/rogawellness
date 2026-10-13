# Raspagem de influencers · Roga Wellness Day (07/11/2026)

## Passo a passo no Apify
1. **apify/instagram-hashtag-scraper** com `inputs/1_hashtags_instagram.json` → exporte em JSON (`hashtags.json`).
2. **apify/instagram-search-scraper** com `inputs/2_search_instagram.json` → exporte (`search.json`).
3. Gere a lista de usernames:
   `python rank_influencers.py usernames hashtags.json search.json > usernames.txt`
4. **apify/instagram-profile-scraper** colando o `usernames.txt` em `usernames` → exporte (`profiles.json`).
5. Ranking:
   `python rank_influencers.py rank profiles.json > ranking.csv`
6. (Opcional) **clockworks/tiktok-scraper** com `inputs/3_tiktok.json` para achar criadores no TikTok e procurá-los no Instagram.

O ranking só considera perfis entre 50 mil e 2 milhões de seguidores (`MIN_FOLLOWERS`/`MAX_FOLLOWERS` no script)
e pontua: engajamento, link/cupom de afiliado na bio, posts com cupom, frequência de #publi, região SP,
aderência ao nicho, marcas premium citadas e sinais de público 30-55 (mãe, médica, executiva, longevidade, marca própria); contas >1M com engajamento <1% perdem pontos. Revise manualmente o top 30 antes de convidar.

---

# Prospecção B2B de parceiros e eventos · `prospeccao/`

Baseado no briefing `prospeccao/briefing_gpt.md`, que tem 18 locais-semente. O objetivo é achar **parceiros** (hotéis, spas, retiros, organizadores de eventos e facilitadores) para divulgar o Roga Day para as **próprias bases opt-in**, com cupom e UTM. Nada aqui coleta hóspedes, seguidores ou participantes.

## Passo a passo no Apify
1. **apify/website-content-crawler** com `inputs/4_crawl_locais.json` → exporte JSON (`crawl_sementes.json`).
   Se um site ficar em branco (bloqueio ou SPA), rode só ele de novo com `"crawlerType": "playwright:firefox"`.
2. **apify/google-search-scraper** com `inputs/5_google_search.json` → exporte (`google.json`).
3. Novas URLs (eventos na Sympla/Eventbrite e novos retiros/hotéis):
   `python prospeccao/prospect_partners.py urls google.json > novas_urls.txt`
4. Revise `novas_urls.txt` e rode o **website-content-crawler** de novo com essas URLs em `startUrls`, `maxCrawlDepth: 1` e sem `includeUrlGlobs` → `crawl_novos.json`.
5. Consolidação:
   `python prospeccao/prospect_partners.py build crawl_sementes.json crawl_novos.json --out prospeccao/saida`

## Saídas (`prospeccao/saida/`, fora do git)
- `roga_locais_enriquecidos.csv`: sementes e novos locais com pontuação 0–100 (proximidade 30, afinidade 25, premium 20, organizadores 15, mensuração 10), prioridade A/B/C e ângulo de parceria.
- `roga_eventos_wellness.csv`: um registro por evento datado, retiro ou programa contínuo, com `temporal_status` e `in_window_until_event` (acontece entre hoje e 07/11).
- `roga_parceiros_publicos.csv`: organizadores e facilitadores, só com contato comercial publicado no site oficial.
- `roga_prospeccao.json`, `roga_top20_oportunidades.md` e `roga_erros_de_coleta.md`.

Limitações: as datas sem ano são inferidas (confidence=low). A distância é em **linha reta** até Atibaia. A cidade de locais novos é inferida do texto. Todo evento sai como `needs_review`, então valide na página-fonte antes de usar em proposta.
