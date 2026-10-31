# Evidências verificadas — DebugMesh, Entrega 1

**Branch:** `release/primeira-entrega`  
**Validação completa:** 30/10/2026 (31/10/2026 em UTC), [GitHub Actions #41158522191](https://github.com/GhrCastro/TP01-Computacao-Distribuida/actions/runs/41158522191), commit `43bb1232d373707afe054097c63cbde909cb4758`, conclusão **success**.

## Escopo da verificação

A [proposta](proposta-debugmesh.md) define para a primeira entrega: pelo menos dois processos/nós; comunicação gRPC; relógios lógicos; eleição de líder; diagnóstico estruturado; relatório SBC de até quatro páginas. O teste usa **dois coordenadores e três workers em contêineres independentes**, conectados pela rede virtual do Docker Compose, e um cliente gRPC no runner do GitHub Actions. Esta topologia prova comunicação real entre processos via rede de contêineres; **não prova uso de computadores físicos diferentes**.

## Testes automatizados

- `python-tests (3.11)`: **13 testes**, aprovado.
- `python-tests (3.12)`: **13 testes**, aprovado.
- `compose-smoke`: aprovado. Script [`scripts/verify_compose_entrega1.py`](../scripts/verify_compose_entrega1.py), com asserções reais no cliente gRPC, verificação dos eventos e coleta de logs.
- `sbc-report`: aprovado. Documento compilado pelo `pdflatex` e inspecionado por `pdfinfo`: **3 páginas (máximo 4)**.

**Artefatos da execução:**
- [Resultados e logs do Docker Compose](https://github.com/GhrCastro/TP01-Computacao-Distribuida/actions/runs/41158522191/artifacts/13025727700) — `summary.json`, respostas gRPC, logs de todos os processos e `compose-ps.txt`.
- [Relatório SBC em PDF, metadados e log de compilação](https://github.com/GhrCastro/TP01-Computacao-Distribuida/actions/runs/41158522191/artifacts/13025609405).
- [Testes em Python 3.11](https://github.com/GhrCastro/TP01-Computacao-Distribuida/actions/runs/41158522191/artifacts/13025967334).
- [Testes em Python 3.12](https://github.com/GhrCastro/TP01-Computacao-Distribuida/actions/runs/41158522191/artifacts/13025334723).

## Asserções aprovadas no teste de ponta a ponta

| Verificação | Resultado |
|---|---|
| `initial_election_A_leader_B_follower` | Coordenador A (prioridade 20) aceita submissões; B (10) rejeita requisições como não líder |
| `three_workers_before_failover` | Amostra de 12 linhas gera 6 findings, provenientes de worker-a, worker-b e worker-c |
| `worker_offline_is_reported_as_failed` | Interrupção do worker-b leva ao estado `ANALYSIS_FAILED` com erro gRPC observável |
| `three_workers_after_failover` | Após a parada de A, B atende nova análise com os três workers |
| `leader_failover_to_B` | B assume a liderança |
| `higher_priority_A_reclaims_leadership` | A retorna e B deixa de atuar como líder |
| `event_logs_election_worker_activity_and_lamport` | Logs mostram eleição de A, detecção da falha e eleição de B, atividade dos três workers e recebimentos cujo timestamp é maior que o remoto |

O workflow agora **falha** caso essas propriedades não se verifiquem. As evidências são guardadas mesmo em caso de falha, por `actions/upload-artifact`, com retenção configurada para 30 dias.

Os 13 testes Python cobrem regras de Lamport e concorrência do relógio, mensagens Protobuf, classificação de logs, chamadas reais gRPC, erros de entrada, worker indisponível, muitas análises concorrentes, eleição, recuperação de liderança, ordenação causal e rejeição de candidatos inconsistentes.

## Pendências humanas / limites

1. **Contribuições individuais:** o relatório lista os cinco integrantes, mas a descrição das contribuições precisa ser confirmada pelo grupo antes de entrega final. Não atribuir trabalho fictício.
2. **Máquinas físicas:** não foi realizado teste entre dois computadores físicos; a proposta armazenada no repositório exige múltiplos processos/nós e não explicita essa obrigatoriedade. Caso o professor tenha imposto uma regra adicional fora desse documento, será necessário testar nessa topologia.
3. **Revisão acadêmica:** ler o PDF final e conferir dados de autoria e exigências adicionais da disciplina. Compilar e ter no máximo 4 páginas não substitui essa revisão.
4. **Escopo da Entrega 2:** não há consenso, replicação, reatribuição automática de tarefas, TLS, nem recuperação do estado de análises do coordenador interrompido.

## Reprodução

O workflow `.github/workflows/test-entrega1.yml` é acionado por push, pull request ou execução manual na branch `release/primeira-entrega`. Ele executa os testes, sobe o cluster Docker, verifica falhas e eleições, compila o relatório e publica artefatos. Para execução local:

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
docker compose up --build -d
python scripts/verify_compose_entrega1.py
docker compose down -v
```

O script deve ser executado a partir da raiz do repositório, com Docker Compose e portas 50051 e 50052 disponíveis. As evidências locais são geradas em `artifacts/entrega1-compose/`.
