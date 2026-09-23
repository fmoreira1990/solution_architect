# Fitness functions

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** as verificações automatizadas que transformam regras de arquitetura em build vermelho. Não cobre os testes de comportamento da fatia — cobre os que protegem **decisões**.
**Requisitos cobertos:** `D-03`
**Fontes:** `docs/CONVENCOES.md`, `docs/governance/politica-contratos.md`, todas as ADRs
**Data:** 2026-09-23

---

## O critério

Uma fitness function só conta se **sabe falhar**. Verificação que passa em qualquer circunstância é decoração — e pior que ausência, porque o pipeline verde dá permissão para seguir.

Por isso, as três mais importantes deste repositório foram validadas por **teste de mutação**: quebra-se deliberadamente o que elas protegem e confirma-se que o build fica vermelho.

| Fitness function | Mutação aplicada | Resultado |
|---|---|---|
| Drift entre contrato e implementação | campo `campo_nao_documentado` adicionado à resposta | ✅ falhou com `só na API: {'campo_nao_documentado'}` |
| Isolamento entre clientes (F1.5) | camada de verificação de dono removida | ✅ falhou com `DID NOT RAISE ConflitoIdempotencia` |
| Cabeçalho canônico dos documentos | — | ✅ **encontrou 7 violações reais**: nenhuma ADR declarava `Escopo` nem `Data` |

A terceira não precisou de mutação: ela falhou de verdade, na primeira execução, e as ADRs foram corrigidas.

---

## 1. Contratos — protegem a `ADR-0004`

`slice/tests/test_contratos_versionados.py`

| # | Verifica | Regra protegida |
|---|---|---|
| 1 | Specs OpenAPI e AsyncAPI parseiam | — |
| 2 | Todas as respostas implementadas estão documentadas (`200/201/409/422`) | documentação completa |
| 3 | `Idempotency-Key` obrigatória em v2, **opcional em v1** | `E3` — tornar obrigatório é breaking |
| 4 | **`RECEBIDO` nunca aparece no enum de status da v1** | `S1` — semântica da fachada |
| 5 | v1 marcada como deprecada, com header `Sunset` | ciclo de vida |
| 6 | **Campos declarados == campos devolvidos pela API real** | spec drift |
| 7 | Status devolvido pertence ao enum declarado | drift de valores |
| 8 | Envelope de evento declarado == publicado pelo relay | drift de eventos |
| 9 | AsyncAPI declara `event_id` como chave de deduplicação | obrigação `C2` |
| 10 | Tipos de evento do contrato existem na implementação | integridade |

**A nº 6 é a mais valiosa.** Ela compara o contrato com a aplicação **rodando**, não com outro documento. É o que detecta o caso em que alguém adiciona um campo e esquece do spec — e foi a validada por mutação.

**A nº 4 merece destaque:** ela codifica uma regra semântica que nenhum diff de schema alcança. Se a fachada síncrona v1 cair, `RECEBIDO` aparece no enum e o build fica vermelho antes de qualquer consumidor quebrar.

---

## 2. Governança — protegem as convenções

`slice/tests/test_governanca.py`

| # | Verifica | Regra protegida |
|---|---|---|
| 1 | Todo documento declara `Escopo`, `Fontes` e `Data` | `Q8` — rastreabilidade |
| 2 | Existem ≥ 4 ADRs | `P1-17` |
| 3 | Toda ADR tem Contexto, Decisão, Alternativas, Trade-offs, Gatilho e Enforcement | `Q3`, `Q4`, `Q5` |
| 4 | Toda ADR rejeita ≥ 2 alternativas, com uma escolhida | **`Q2`** |
| 5 | Referências cruzadas entre ADRs apontam para ADRs existentes | integridade |
| 6 | **Nenhuma exceção técnica vencida** | `excecao-tecnica.md` §3 |
| 7 | Contratos citados na documentação existem | integridade |
| 8 | **Testes citados na documentação existem** | impede alegar cobertura inexistente |

**A nº 8 é a que mais protege a honestidade do entregável.** Toda a documentação cita testes como evidência — `test_queda_entre_publicar_e_marcar_nao_perde_evento`, `test_evento_nao_carrega_pii` e outros. Se um teste for renomeado ou removido, a documentação passaria a alegar uma cobertura que não existe. Agora o build quebra.

**A nº 6 é o que impede o processo de exceção de virar formulário morto**, que é como a maioria dos processos de waiver termina.

---

## 3. Diagramas — protegem `E-02`

`tools/validar-mermaid.mjs`

Valida os blocos Mermaid com o **parser oficial**, o mesmo que o GitHub usa.

Existe porque **Mermaid falha em silêncio**: um diagrama com erro de sintaxe não gera aviso, apenas não aparece. Sem esta verificação, o entregável poderia chegar ao avaliador com diagramas em branco — e `E-02` cairia por um detalhe.

A primeira versão desta verificação era um checador por expressão regular (balanceamento de `subgraph`, índices de `linkStyle`). Ela passava em diagramas que o Mermaid rejeitaria. Foi substituída pelo parser real assim que o Node ficou disponível.

---

## 4. Segurança — protegem o threat model

`slice/tests/test_seguranca.py`

| # | Verifica | Ameaça |
|---|---|---|
| 1 | Chave de outro cliente não devolve pedido alheio | **F1.5** |
| 2 | A defesa em profundidade funciona **mesmo com o hash neutralizado** | F1.5 |
| 3 | Namespaces de chamadores distintos não colidem | F1.5 |
| 4 | Preço adulterado após a assinatura é recusado | F1.2 |
| 5 | Item injetado na oferta é recusado | F1.2 |
| 6 | **Evento não carrega PII** | **F4.2** |

A nº 2 precisou de `monkeypatch` para ter valor: sem neutralizar o hash canônico, ela passaria pela primeira verificação e não exercitaria a camada que promete testar. Um teste que não isola o que promete é pior que nenhum.

---

## 5. O que **não** é automatizável

Registrado para não passar por cobertura que não existe.

| Regra | Por que não automatiza | Como é tratada |
|---|---|---|
| Quebras semânticas `S2`–`S6` | não há detector genérico para "o significado mudou" | checklist obrigatório em PR que toque `contracts/` |
| `Q1` — decisão ancorada em restrição real | exige julgamento | revisão de par |
| `Q7` — `???` em vez de invenção | distinguir lacuna declarada de número inventado exige contexto | revisão |
| `Q11` — não superdimensionar | exige julgamento sobre proporcionalidade | seção "O que **não** está nesta arquitetura" |
| Diff estrutural `E1`–`E6` | exige versão publicada como linha de base | entra quando houver |

**A limitação está declarada de propósito.** Governança leve é escolha; o custo dela é depender de disciplina em parte das regras. Quando um caso concreto de `S2`–`S6` aparecer, ele vira teste específico — foi exatamente assim que `S1` virou a verificação nº 4 da seção 1.

---

## Como rodar

```bash
# tudo, incluindo a prova executável
cd slice && python prova.py

# só as fitness functions
cd slice && python -m pytest tests/test_governanca.py tests/test_contratos_versionados.py tests/test_seguranca.py

# diagramas
cd tools && npm install && node validar-mermaid.mjs
```

No CI, as três rodam em `.github/workflows/ci.yml`.

---

## Pendências registradas

- O diff estrutural de OpenAPI precisa de versão publicada como linha de base.
- Não há SAST nem verificação de dependências vulneráveis — débito `D6` de `riscos-premissas.md`.
- A verificação de PII em schema (`ADR-0006`, enforcement 1) está especificada e não implementada: depende do schema multi-região da onda 90.
