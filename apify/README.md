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
