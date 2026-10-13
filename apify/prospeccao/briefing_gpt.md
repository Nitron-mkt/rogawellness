# ROGA WELLNESS — Base de locais e briefing de pesquisa para Claude + Apify

**Atualizado em:** 13/10/2026  
**Objetivo:** identificar parceiros e audiências com afinidade para vender ingressos do **Roga Wellness Day (07/11/2026, Atibaia/SP, lote divulgado R$ 1.390)**.  
**Natureza da base:** 18 **locais/empreendimentos** com oferta ou posicionamento de bem-estar; não significa que 18 eventos futuros tenham sido confirmados. Os links são pontos iniciais para inspeção.  
**Importante:** este arquivo **não é uma lista de clientes ou hóspedes**, não contém contatos privados nem autoriza coletá-los.

## 1. Locais-semente para enriquecimento

Prioridade A = melhor proximidade/afinidade inicial; B = bom benchmark e possível parceria; C = maior distância e menor viabilidade imediata de conversão presencial. A classificação é hipótese comercial, não comprovação de intenção de compra.

| ID | Local | Cidade/UF | Categoria | Sinal wellness verificado / ângulo de pesquisa | Prioridade | URL de entrada |
|---|---|---|---|---|---|---|
| 01 | Unique Garden | Mairiporã/SP | hotel boutique premium | Spa Pandora, terapias e experiências de desconexão; pesquisar facilitadores, retiros e parcerias | A | https://www.uniquegarden.com.br/pt-br/sentir |
| 02 | Botanique Hotel | Campos do Jordão/SP | hotel luxo/natureza | Spa, massagens, saunas, bem-estar na Mantiqueira | A | https://www.botanique.com.br/ |
| 03 | Hotel Ponto de Luz | Joanópolis/SP | hotel de retiros | Agenda pública de retiros, autoconhecimento e eventos com facilitadores | A | https://pontodeluz.com/agenda/lista/ |
| 04 | Fasano Boa Vista | Porto Feliz/SP | hotel de luxo | Programa Bem-Estar com hospedagem e massagens; Spa Fasano | A | https://fasano.com.br/hotel/fasano-boa-vista/ |
| 05 | Boa Vista Surf Lodge | Porto Feliz/SP | resort/experiências premium | Programa Ritual de Spa incluindo yoga, pedras quentes e tratamentos | A | https://fasano.com.br/programa/spa-ritual/ |
| 06 | Rosewood São Paulo — Asaya Spa | São Paulo/SP | hotel de luxo + wellness membership | Yoga, pilates, sound therapy, spa e comunidade de membros | A | https://www.rosewoodhotels.com/pt/sao-paulo/wellness |
| 07 | Palácio Tangará — Spa | São Paulo/SP | hotel de luxo | Day Spa, experiências de bem-estar, spa e vouchers | A | https://experienciaspalaciotangara.com.br/ |
| 08 | JW Marriott São Paulo — Spa by JW | São Paulo/SP | hotel 5 estrelas | Day use, tratamentos e jornada relax | A | https://www.jwmarriottsaopaulo.com/ |
| 09 | Hotel Emiliano São Paulo — Spa Santapele | São Paulo/SP | hotel de luxo | Day Spa de até cinco horas; experiências sensoriais | A | https://emiliano.com.br/experiencias/day-spa/ |
| 10 | Renaissance São Paulo — The Spa | São Paulo/SP | hotel premium | Spa, eventos e experiências bem-estar | B | https://www.marriott.com/pt-br/hotels/saobr-renaissance-sao-paulo-hotel/overview/ |
| 11 | Fasano Rio de Janeiro | Rio de Janeiro/RJ | hotel de luxo | Yoga ao amanhecer e experiências fitness | B | https://fasano.com.br/experiencias/?categoria=bem-estar |
| 12 | Hotel Emiliano Rio — Spa Santapele | Rio de Janeiro/RJ | hotel de luxo | Spa sensorial e tratamentos; explorar parceiros de wellness | B | https://emiliano.com.br/spa-rj/spa-santapele/ |
| 13 | Rituaali Clínica & Spa | Penedo/RJ | clínica/spa de destino | Programas multidiários de spa, respiração, caminhada, nutrição e movimento | B | https://rituaali.com.br/pre-reserva/ |
| 14 | Lapinha SPA | Lapa/PR | spa de destino | Programação temática com Sound Healing (25–31/10) e outras semanas | B | https://lapinha.com.br/ |
| 15 | Kurotel | Gramado/RS | spa médico de luxo | Programação anual e imersões temáticas, outubro e novembro | C | https://www.kurotel.com.br/programacao-anual |
| 16 | IBITI / Engenho Lodge — Raízes Spa | Lima Duarte/MG | hospedagem de natureza e wellness | Healing Day, yoga e sound healing | B | https://ibiti.com/pt-br/categorias-do-guia/wellness-engenho/ |
| 17 | IBITI / Village — Village Spa | Lima Duarte/MG | hospedagem de natureza e wellness | Terapias, spa e watsu; **mesma marca/empreendimento do ID 16, outro espaço**, não contar como novo operador | B | https://ibiti.com/pt-br/categorias-do-guia/wellness-village/ |
| 18 | Txai Resort & Spa — Spa Shamash | Itacaré/BA | resort de luxo | Yoga, meditação, spa e jornadas de reconexão | C | https://txairesorts.com/spa-shamash/ |

**Deduplicação:** são 18 locais/entradas, mas **17 operações/marcas-local distintas** se os dois espaços IBITI forem consolidados. Há também marcas com unidades diferentes (Fasano e Emiliano): mantê-las separadas por cidade e unidade, mas associar à matriz quando fizer sentido.

## 2. Tarefa exata para Claude com Apify

> Atue como pesquisador de inteligência comercial para o Roga Wellness Day. Use minha conexão Apify para enriquecer os 18 locais do quadro acima e descobrir **no mínimo 30 eventos/experiências ou comunidades adicionais** associados a turismo de bem-estar, hotelaria de luxo, day spa, yoga, pilates, recuperação, mindfulness, sound healing, retiros e longevidade no Brasil. Priorize São Paulo e locais a até aproximadamente 200 km de Atibaia (verifique distâncias; não invente). Janela de pesquisa: eventos de 01/01/2025 a 07/11/2026, destacando os que ainda ocorrerão entre 13/10 e 07/11/2026. NÃO confunda um serviço permanente de spa com evento datado. Registre fonte e data de acesso de cada fato. Gere CSV e JSON estruturados, mais resumo das 20 oportunidades comerciais de maior prioridade.

### Sequência operacional recomendada

1. **Descobrir as ferramentas/Actors disponíveis no Apify**, os inputs exigidos e as políticas de cada site. Não inventar nomes de actors ou campos de API. Preferir busca pública e extração de sites oficiais; para resultados de buscadores usar apenas ferramenta/actor apropriado e disponível.
2. Percorrer inicialmente cada `URL de entrada`, extrair links internos de `/agenda`, `/eventos`, `/experiencias`, `/spa`, `/wellness`, `/retiros`, pacotes, professores e parceiros públicos. Limitar domínio, número de páginas, profundidade e volume; evitar páginas repetidas.
3. Expandir por buscas públicas combinando nome do local + `retiro`, `evento wellness`, `yoga`, `sound healing`, `pilates`, `spa day`, `imersão`, `longevity`, `2026`, `2025`, `parceiros`, `facilitadores`. Para novos locais, exigir evidência de existência e fonte.
4. Identificar **organizador, canal comercial oficial, facilitadores profissionais públicos, marcas patrocinadoras e perfis institucionais**. Somente extrair dados de contato **publicados para contato comercial/profissional**. Não coletar, inferir ou contornar acesso a listas de hóspedes, inscritos, seguidores individuais ou participantes de eventos.
5. Eventos com datas, preços e links: validar na **página primária do evento**. Preço não encontrado = `null`. Datas antigas = `historico`, não `futuro`. Páginas sem data = `programa_continuo` ou `nao_confirmado`.
6. Priorizar canais de **parceria opt-in**: convite para organizador fazer divulgação oficial; links UTM/cupom por parceiro; públicos que se cadastram voluntariamente. Não orientar disparos a pessoas obtidas sem consentimento nem contornar login, captcha, robots.txt ou rate limits.
7. Exportar resultados com deduplicação por URL canônica, nome + local + data. Se Apify não puder abrir fonte, registrar erro e não inventar.

### Sugestões de consultas

```text
"wellness retreat" "São Paulo" hotel 2026
"retiro yoga" "Atibaia" OR "Joanópolis" OR "Mairiporã" 2026
"day spa" "evento" "São Paulo" 2026
"sound healing" hotel São Paulo 2026
"wellness weekend" hotel Brasil 2026
"yoga" "Fasano Boa Vista" evento
"retiro" "Ponto de Luz" facilitador 2026
"wellness" "Rosewood São Paulo" parceiros
"spa" "Botanique" yoga
"wellness" patrocinadores festival São Paulo 2026
```

## 3. Esquema obrigatório para CSV/JSON

| Campo | Tipo / instrução |
|---|---|
| `place_id` | ID da entrada-semente ou gerado para novo local |
| `place_name` | nome público |
| `city`, `state` | município/UF; não presumir cidade só pelo nome |
| `place_type` | hotel, spa, resort, retiro, comunidade, studio, festival |
| `official_url` | URL canônica |
| `source_url` | link preciso que sustenta o registro |
| `accessed_at` | timestamp ISO 8601 |
| `record_type` | `dated_event`, `continuous_program`, `retreat`, `venue_only` |
| `event_name` | nome ou `null` |
| `start_date`, `end_date` | YYYY-MM-DD ou `null` |
| `temporal_status` | `future`, `past`, `ongoing`, `unconfirmed` |
| `price_brl_min`, `price_brl_max` | valores numéricos BRL ou `null`; não extrapolar |
| `price_context` | por pessoa, casal, quarto, pacote, diária etc. |
| `activities` | array (yoga, breathwork, sound healing, spa, trilha etc.) |
| `organizer_name` | nome público ou `null` |
| `organization_social_url` | perfil institucional público |
| `facilitator_professional_url` | perfil profissional publicamente publicado, se houver |
| `business_contact` | somente e-mail/telefone comercial explicitamente publicado para negócios, ou `null` |
| `partnership_angle` | proposta de ativação orgânica/opt-in |
| `priority` | A, B ou C + justificativa |
| `evidence_excerpt` | paráfrase curta sustentada pela fonte |
| `confidence` | high/medium/low; separar fato de hipótese |
| `scrape_status` | success, blocked, unavailable, needs_review |

## 4. Critério de prioridade comercial

Pontuação interna de 0 a 100 (heurística, não dado observado):
- Até 30 pontos: proximidade a Atibaia / facilidade de deslocamento.
- Até 25 pontos: afinidade de programação (yoga, recovery, natureza, conexão e sound healing).
- Até 20 pontos: evidência verificável de oferta premium **com preço e unidade claros**.
- Até 15 pontos: existência de facilitadores, programação datada e organizadores acessíveis para parcerias.
- Até 10 pontos: possibilidade de divulgar e mensurar aquisição com URL própria/cupom.

**Não atribuir automaticamente poder aquisitivo ou intenção de compra a um indivíduo por ele seguir uma marca, aparecer em foto ou participar de comunidade.**

## 5. Saídas finais exigidas

- `roga_locais_enriquecidos.csv` — 18 sementes + novos locais validados.
- `roga_eventos_wellness.csv` — um registro por evento/programa, com tipo e status temporal.
- `roga_parceiros_publicos.csv` — organizações e facilitadores com contatos profissionais **públicos**, origem citada.
- `roga_prospeccao.json` — equivalente estruturado com fontes, datas e deduplicação.
- `roga_top20_oportunidades.md` — ranking das 20 oportunidades B2B de parceria, ação sugerida, argumento comercial, link de contato e grau de evidência.
- `roga_erros_de_coleta.md` — URLs inacessíveis, limitações, dúvidas e campos faltantes.

## 6. Referências primárias consultadas na montagem das sementes

- Unique Garden: https://www.uniquegarden.com.br/pt-br/sentir
- Botanique: https://www.botanique.com.br/
- Ponto de Luz: https://pontodeluz.com/agenda/lista/
- Fasano Boa Vista: https://fasano.com.br/hotel/fasano-boa-vista/
- Fasano / Boa Vista Surf Lodge: https://fasano.com.br/programa/spa-ritual/
- Rosewood: https://www.rosewoodhotels.com/pt/sao-paulo/wellness
- Palácio Tangará: https://experienciaspalaciotangara.com.br/
- JW Marriott: https://www.jwmarriottsaopaulo.com/
- Emiliano: https://emiliano.com.br/experiencias/day-spa/
- Renaissance: https://www.marriott.com/pt-br/hotels/saobr-renaissance-sao-paulo-hotel/overview/
- Fasano experiências: https://fasano.com.br/experiencias/?categoria=bem-estar
- Emiliano Rio: https://emiliano.com.br/spa-rj/spa-santapele/
- Rituaali: https://rituaali.com.br/pre-reserva/
- Lapinha: https://lapinha.com.br/
- Kurotel: https://www.kurotel.com.br/programacao-anual
- Ibiti: https://ibiti.com/pt-br/categorias-do-guia/wellness-engenho/ e https://ibiti.com/pt-br/categorias-do-guia/wellness-village/
- Txai: https://txairesorts.com/spa-shamash/

**Estado da coleta:** reconhecimento e verificação inicial de locais e programas por páginas públicas em 13/10/2026. **Apify não foi executado nesta etapa**; enriquecimento, contatos, eventos confirmados e exports são tarefas para a execução posterior no Claude.
