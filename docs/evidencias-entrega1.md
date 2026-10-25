# Evidências de testes — DebugMesh, Entrega 1

Validação executada em **25/10/2026** na branch `release/primeira-entrega`.

## Testes automatizados
- [GitHub Actions: execução 40225688989](https://github.com/GhrCastro/TP01-Computacao-Distribuida/actions/runs/40225688989), commit `5ee014d3a268d8d9b77cc90046fbc7a35823f72f`, conclusão `success`.
- `python-tests (3.11)`: 6/6 testes aprovados.
- `python-tests (3.12)`: 6/6 testes aprovados.
- `compose-smoke`: aprovado, com build da imagem, orquestração dos serviços e teste de sucessão de líder.

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
