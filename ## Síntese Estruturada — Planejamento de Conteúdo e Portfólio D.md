## Síntese Estruturada — Planejamento de Conteúdo e Portfólio Data Science
### Versão 2.0 — Atualizada

---

### 1. Contexto Geral

**Objetivo triplo:** construção de marca pessoal para vaga de estágio (Instituto Eldorado — Manaus), atração de clientes para consultoria, e crescimento de audiência com monetização futura.

**Perfil de produção:** iniciante em vídeo, celular + webcam mediana + software de edição instalado, até 3h/semana para produção, Canva disponível.

**Plataformas:** YouTube (vídeo principal), Instagram Reels (corte), LinkedIn (vídeo nativo).

**Nome do canal:** `adriano.dados`

---

### 2. Identidade Visual

| Elemento | Definição |
|---|---|
| Estética | Limpo e corporativo — referência Alex The Analyst |
| Base | Branco `#FFFFFF` / Cinza claro `#F4F6F8` |
| Texto | Cinza escuro `#1E2A3A` |
| Cor principal | Azul profundo `#1A56DB` |
| Acento | Ciano elétrico `#00C2FF` |
| Tipografia | Inter Bold (títulos) / Inter Regular (corpo) |
| Substituta | DM Sans (se Inter indisponível no Canva) |

**Marca textual:** `adriano` em `#1E2A3A` + `.dados` em `#1A56DB` — Inter Bold, mesmo tamanho.

**Thumbnail padrão:** fundo `#F4F6F8`, faixa inferior azul `#1A56DB` (25% da altura), título Inter Bold 72pt, palavra de destaque em `#00C2FF`, foto com glow ciano atrás (opacidade 30–40%), assinatura `adriano.dados` na faixa inferior.

**Especificações de tamanho:**

| Peça | Dimensão |
|---|---|
| Foto de perfil (todas as plataformas) | 800×800px |
| Banner YouTube | 2560×1440px (área segura: 1546×423px) |
| Banner LinkedIn | 1584×396px |
| Thumbnail | 1280×720px |
| Story Instagram | 1080×1920px |

**Bio padrão:** *"Data Science aplicada a problemas reais | Manaus, AM | Novos vídeos toda semana"*

---

### 3. Cronograma de Produção

**Fluxo semanal dentro das 3h:**

| Etapa | Tempo |
|---|---|
| Roteiro e planejamento | 40 min |
| Gravação | 30–40 min |
| Edição (CapCut ou DaVinci) | 50–60 min |
| Corte para Reels/LinkedIn | 20 min |
| Publicação + legendas | 20 min |

**Duração por plataforma:**

| Plataforma | Formato | Duração |
|---|---|---|
| YouTube | Vídeo principal | 8–12 min |
| Instagram | Reels (corte do melhor trecho) | 60–90 seg |
| LinkedIn | Vídeo nativo (mesmo corte) | 60–90 seg |

**Regra de distribuição:** grava uma vez, distribui três vezes. O corte para Reels e LinkedIn é sempre o momento de maior valor concentrado do vídeo principal.

---

### 4. Sequência de Vídeos e Projetos

| Semana | Vídeo / Tema | Projeto de Portfólio | Corte Reels |
|---|---|---|---|
| 1 | Fase 0 — identidade e setup | — | — |
| 2 | Estatística aplicada / métricas de ML | Risco de Crédito | Comparação acurácia vs. AUC |
| 3 | EDA com Python | Conversão de Pacientes | Reveal do funil |
| 4 | SQL ao vivo | Pipeline DataSUS | Window Function ao vivo |
| 5 | ETL na prática | Pipeline DataSUS (continuação) | Antes vs. depois do dado bruto |
| 6 | Visualização de dados | Segmentação — State of Data Brazil | Gráfico enganoso vs. correto |
| 7 | Dashboard interativo | Dashboard Educacional AM | Dashboard ao vivo com filtros |
| 8 | Storytelling com dados | Análise de Sentimentos NLP PT-BR | Apresentação ruim vs. reconstruída |

---

### 5. Estrutura de Roteiro Padrão (5 Blocos)

```
[GANCHO]          0:00–0:45   screencasting — mostra resultado final
[CONTEXTO]        0:45–2:00   câmera — por que isso importa para negócio
[DESENVOLVIMENTO] 2:00–9:00   screencasting — código, análise, decisões
[INSIGHT FINAL]   9:00–10:30  câmera — o que os dados revelaram
[CTA]             10:30–11:00 câmera — GitHub, próximo vídeo, inscrição
```

**Formato recomendado:** screencasting com voz + câmera nos blocos 2, 4 e 5 (referência Sigmoidal). Rosto obrigatório na thumbnail (mínimo 40% da área, lado direito).

---

### 6. Portfólio — 7 Projetos

| # | Projeto | Setor | Stack Principal | Dataset | Fonte |
|---|---|---|---|---|---|
| 1 | Risco de Crédito | Financeiro | Python, scikit-learn, pandas | BCB SCR.data + sintético calibrado | dadosabertos.bcb.gov.br |
| 2 | Conversão de Pacientes | Saúde | Python, pandas, plotly, faker | Sintético com benchmark FVS-RCP | fvs.am.gov.br/dadossaude |
| 3 | SQL / Pipeline DataSUS | Saúde | Python, SQL, SQLite, sqlalchemy | DATASUS SIH-AM (internações AM) | tabnet.datasus.gov.br |
| 4 | Pipeline ETL completo | Saúde | Python, pandas, sqlalchemy, PostgreSQL | DATASUS FTP microdados AM | ftp.datasus.gov.br |
| 5 | Segmentação de Profissionais de Dados | Marketing | Python, scikit-learn, plotly, seaborn | State of Data Brazil 2023–2024 | kaggle.com/datasets/datahackers/state-of-data-brazil-2023 |
| 6 | Dashboard Educacional AM | Educação | Python, Streamlit, plotly, SQL | INEP Censo Escolar AM | inep.gov.br/microdados |
| 7 | Forecasting de Matrículas | Educação | Python, Prophet, statsmodels | INEP série histórica AM | inep.gov.br/microdados |

**Projeto 8 — Análise de Sentimentos (NLP):** dataset de avaliações em português brasileiro, fonte `github.com/lucasvbalves/nlp-pt-br-datasets`, stack Python + TextBlob/VADER + wordcloud + plotly. Vinculado ao Vídeo 8.

---

### 7. Estrutura GitHub — Padrão por Repositório

```
nome-do-projeto/
├── README.md
├── requirements.txt
├── .gitignore
├── data/
│   ├── raw/
│   ├── processed/
│   └── README.md
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_preprocessing.ipynb
│   ├── 03_modeling.ipynb
│   └── 04_insights.ipynb
├── src/
│   ├── data_loader.py
│   ├── preprocessing.py
│   └── visualization.py
├── reports/
│   └── figures/
└── docs/
    └── apresentacao.pdf
```

**Variações por projeto:**

| Projeto | Adição específica |
|---|---|
| Risco de Crédito | `notebooks/05_model_comparison.ipynb` |
| Conversão de Pacientes | `src/data_generator.py` com premissas documentadas |
| SQL / DataSUS | `sql/` com scripts organizados por complexidade |
| Pipeline ETL | `docs/pipeline_diagram.png` (draw.io ou Excalidraw) |
| Segmentação State of Data | `reports/executive_summary.md` em linguagem de negócio |
| Dashboard Educacional | Link ativo do deploy no Streamlit Cloud no README |
| Forecasting Matrículas | `notebooks/05_forecast_interpretation.ipynb` em markdown narrativo |

**README de cada projeto inclui obrigatoriamente:** problema de negócio, dataset com fonte e volume, metodologia em 4 etapas, principais resultados em 3 bullets, instruções de execução, e link do vídeo no YouTube.

**Perfil do GitHub:** repositório especial `username/username` com README de apresentação contendo stack, projetos em destaque e links de contato.

**Regra de commits:** mínimo um commit por dia durante a semana de desenvolvimento — mantém o gráfico de contribuições ativo.

---

### 8. Fontes de Dados Abertas

| Fonte | URL | Setor | Granularidade AM |
|---|---|---|---|
| BCB Dados Abertos | dadosabertos.bcb.gov.br | Financeiro | Por UF |
| DATASUS TabNet | tabnet.datasus.gov.br | Saúde | Município |
| DATASUS FTP | ftp.datasus.gov.br/dissemin/publicos/ | Saúde | Município |
| FVS-RCP Amazonas | fvs.am.gov.br/dadossaude | Saúde | Município AM |
| INEP Microdados | inep.gov.br/microdados | Educação | Escola/Município |
| Portal Transparência AM | transparencia.am.gov.br | Geral | Município AM |
| State of Data Brazil 2023–2024 | kaggle.com/datasets/datahackers/state-of-data-brazil-2023 | Marketing | Nacional + filtro regional |
| NLP PT-BR Datasets | github.com/lucasvbalves/nlp-pt-br-datasets | NLP/Sentimentos | Nacional |

---

### 9. Próximos Passos Pendentes

| Item | Prioridade |
|---|---|
| Guia de edição no CapCut para o Vídeo 1 | Alta |
| Scripts completos dos Vídeos 2 ao 7 | Alta |
| Instrução de acesso e extração do DATASUS para o Projeto 3 | Alta |
| Setup do OBS Studio para screencasting | Média |
| Deploy do Streamlit Cloud para o Projeto 6 | Média |

---

### 10. Pesquisas Pendentes Recomendadas

| Query | Objetivo |
|---|---|
| `LinkedIn video nativo alcance orgânico 2025` | Define fluxo de publicação |
| `melhor horário postar Instagram Reels Brasil 2025` | Otimiza alcance |
| `melhor horário postar LinkedIn Brasil 2025` | Otimiza alcance |
| `OBS Studio tutorial screencasting iniciante português` | Setup técnico |
| `Instituto Eldorado projetos Manaus dados LinkedIn` | Calibra portfólio para a vaga |