# Evidências de testes — DebugMesh, Entrega 1

Validações executadas em **25/10/2026** e **26/10/2026** na branch `release/primeira-entrega`. O registro abaixo distingue a evidência histórica da verificação mais recente.

## Testes automatizados
- **Execução mais recente confirmada:** [GitHub Actions 40321544511](https://github.com/GhrCastro/TP01-Computacao-Distribuida/actions/runs/40321544511), em 26/10/2026, commit `a2a7d8cf28423595a8f005bd1a0e597cc420d1b6`, conclusão `success`.
- `python-tests (3.11)`: **13 testes** (6 unitários + 7 de integração), job aprovado.
- `python-tests (3.12)`: **13 testes** (6 unitários + 7 de integração), job aprovado.
- `compose-smoke`: aprovado com build, inicialização de coordenadores/workers, submissão ao líder, parada de `coordinator-a` e submissão ao `coordinator-b`.
- Execução histórica: [GitHub Actions 40225688989](https://github.com/GhrCastro/TP01-Computacao-Distribuida/actions/runs/40225688989), commit `5ee014d3`, 6 testes por versão do Python e `compose-smoke` aprovado. Não usar essa contagem antiga como resultado final.

## Cobertura da suíte atual (13 testes)
- **Unidade (6):** regra Lamport, análise determinística, round-trip Protobuf, causalidade no ciclo de mensagens, timestamps atrasados e segurança com 1.200 incrementos concorrentes.
- **Integração (7):** três workers via gRPC/erros de entrada, worker indisponível, eleição/failover, muitas análises concorrentes sem starvation, rejeição de anúncio de líder de menor prioridade, causalidade entre findings e resposta final, rejeição de prioridade de candidato inconsistente.

## Cenário Docker Compose
1. Dois coordenadores (prioridades 20 e 10) e três workers receberam logs sintéticos via gRPC.
2. Primeira análise: 12 linhas e 6 `Finding` sem erros; os resultados incluem `worker-a`, `worker-b` e `worker-c`.
3. O coordenador `coordinator-a` registrou eleição como líder.
4. Após `docker compose stop coordinator-a`, `coordinator-b` registrou `leader_unreachable` e depois `elected`.
5. A nova análise no `coordinator-b` terminou em `ANALYSIS_COMPLETED`, com 6 resultados sem erros.

## Mecanismos verificados
| Mecanismo | Evidência |
|---|---|
| gRPC | Chamadas cliente-coordenador e coordenador-workers, serialização Protobuf |
| Paralelismo | Tarefas particionadas e processadas pelos três workers |
| Lamport | Timestamps transportados em mensagens e testes de relações causais |
| Eleição Bully simplificada | Coordenador de maior prioridade, seguido de sucessão após falha |
| Tratamento de erros | Análise inexistente, entrada inválida, worker offline e estado `ANALYSIS_FAILED` |

## Pendências de validação externa
- Reproduzir em **duas ou mais máquinas distintas**, na mesma rede local, documentando endereços e comandos reais.
- Preencher nomes e contribuições individuais no relatório.
- O Docker Compose usa múltiplos contêineres no mesmo host; isso demonstra processos isolados e tráfego pela rede de contêineres, mas não substitui a demonstração entre computadores físicos.
- A Entrega 1 não implementa consenso, tolerância a partições, replicação nem recuperação do estado de análises aceitas pelo líder que caiu.
