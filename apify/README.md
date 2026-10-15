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

# Compradores para DM manual · `rank_buyers.py`

Objetivo: achar **pessoas** que já comentaram com interesse em posts de wellness ou de eventos parecidos e montar uma lista para a equipe mandar **DM manual** pela conta da Roga.

## Passo a passo no Apify
1. Rode as etapas 1–5 do ranking de influencers acima (`hashtags.json` e `ranking.csv`).
2. Gere os perfis para o **apify/instagram-scraper**: `python rank_buyers.py influencers ranking.csv --top 30`.
   Junte com perfis de eventos, estúdios e retiros parecidos em SP e cole em `directUrls` de `inputs/6_influencer_posts.json`. Exporte como `influencer_posts.json`.
3. Escolha os posts que valem raspar: `python rank_buyers.py posts hashtags.json influencer_posts.json > post_urls.txt`.
   Isso pega posts do nicho com 5 ou mais comentários, com SP e posts de evento primeiro.
4. Cole `post_urls.txt` em `inputs/7_comments.json` e rode **apify/instagram-comment-scraper**. Exporte como `comments.json`.
5. Liste quem tem intenção: `python rank_buyers.py commenters comments.json > commenters.txt`.
6. Rode **apify/instagram-profile-scraper** com `commenters.txt` e exporte como `commenter_profiles.json`.
7. Gere o ranking final:
   `python rank_buyers.py rank --comments comments.json --profiles commenter_profiles.json --posts hashtags.json influencer_posts.json > leads.csv`

## O que tem no `leads.csv`
@, link do perfil, primeiro nome, score, intenção (forte/média), motivos, o comentário e o post de origem, e uma **DM sugerida** já personalizada com nome, post e tema.
As colunas `status`, `enviado_em`, `respondeu` e `comprou` servem para a equipe marcar o andamento.

Pontuação: pergunta ou intenção de compra ("quero ir", "quanto?", "link?") vale +30; marcar amigo +15; comentar em vários posts do nicho +8 por post a mais; SP na bio +20; sinais de 30–55 anos ou profissionais +8 cada.
Ficam de fora: lojas, estúdios e clínicas, perfis com mais de 30 mil seguidores, perfis com menos de 3 posts, o dono do post e comentários de spam.

## Boas práticas para não bloquear a conta (e respeitar a LGPD)
- No máximo **20–30 DMs por dia**, enviadas à mão, com pausas entre elas. Nada de automação de envio.
- Comece pela intenção **forte**. Edite a DM sugerida para não mandar o texto idêntico para todo mundo.
- Primeira mensagem curta e pedindo permissão ("posso te mandar a programação?"). No máximo **1 follow-up**.
- Se a pessoa disser que não quer, marque `status = nao_contatar` e não insista.
- A lista não sai da equipe e é **apagada depois do evento** (07/11). Não guarde telefone nem e-mail.

---

# (Opcional) Prospecção B2B de parceiros e eventos · `prospeccao/`

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

## Painel de envio (`painel_dm.py`)
`python painel_dm.py leads.csv > painel_dm.html` gera uma página que abre no navegador. Cada pessoa vira um card com a DM editável e os botões **Copiar e abrir Direct** (abre a conversa pelo `ig.me`), **Perfil**, **Marcar enviada** e **Não contatar**.
O painel conta quantas DMs foram enviadas no dia e avisa ao passar de 30. O progresso fica salvo no navegador e pode ser exportado em CSV. O envio é sempre manual, para não arriscar a conta.
Os arquivos de `saida/` têm dados de pessoas e ficam fora do git.

## Rodada 2: perfis de wellness (`inputs/9_perfis_wellness.json`)
Ficou definida depois do teste: hashtags de corrida trouxeram o público errado. Esta rodada usa 15 perfis de yoga, sound healing, breathwork e recovery tirados dos dados do teste, e roda no **apify/instagram-scraper**.
