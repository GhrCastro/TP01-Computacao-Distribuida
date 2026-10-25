# DebugMesh — MVP executável (Entrega 1)

Sistema distribuído para análise de logs de CI/CD com **gRPC**, **relógios lógicos de Lamport** e **eleição Bully simplificada**. Funciona sem IA, credenciais externas ou integração obrigatória com GitHub Actions. Veja `docs/architecture-entrega1.md` para os contratos e limites.

> ATENÇÃO: a primeira entrega não inclui replicação, consenso, persistência nem reprocessamento automático após falhas. O estado reside na memória do coordenador ativo. A eleição é uma demonstração didática para uma rede local sem partições adversariais.

## Pré-requisitos
- Python >= 3.10; instalar `pip install -e '.[dev]'` a partir da raiz; ou Docker Engine e Compose Plugin.
- Em ambientes restritos, comandos Python podem usar `PYTHONPATH=src python -m debugmesh ...` após instalar `grpcio` e `protobuf`.

## Execução com Docker Compose

```bash
docker compose up --build -d
docker compose logs -f coordinator-a coordinator-b worker-a worker-b worker-c
```

Após a eleição estabilizar, enviar uma análise para o coordenador de maior prioridade:

```bash
# Docker instalado na máquina cliente, Python instalado localmente
python -m debugmesh submit --coordinator localhost:50051 --file samples/ci_pipeline.log --wait
```

O retorno contém `analysis_id`, estado e findings com `worker_id` (mostrando participação de múltiplos nós) e `logical_timestamp` (Lamport). Para consultar outra vez:

```bash
python -m debugmesh status --coordinator localhost:50051 --analysis-id ID
```

### Demonstração de eleição

```bash
docker compose stop coordinator-a
# Espere o coordenador B detectar a queda do A e realizar nova eleição.
python -m debugmesh submit --coordinator localhost:50052 --file samples/ci_pipeline.log --wait
docker compose logs coordinator-b
docker compose down
```

**Importante:** ao cair o líder, análises armazenadas na memória desse processo são perdidas; somente análises novas podem ser submetidas ao líder sucessor. Essa limitação será tratada na Entrega 2.

## Execução sem Docker (cinco terminais)

```bash
python -m debugmesh worker --id worker-a --bind 127.0.0.1:50061
python -m debugmesh worker --id worker-b --bind 127.0.0.1:50062
python -m debugmesh worker --id worker-c --bind 127.0.0.1:50063
python -m debugmesh coordinator --id coordinator-a --bind 127.0.0.1:50051 --priority 20 --peers coordinator-b@10@127.0.0.1:50052 --workers 127.0.0.1:50061,127.0.0.1:50062,127.0.0.1:50063
python -m debugmesh coordinator --id coordinator-b --bind 127.0.0.1:50052 --priority 10 --peers coordinator-a@20@127.0.0.1:50051 --workers 127.0.0.1:50061,127.0.0.1:50062,127.0.0.1:50063
```

Cada linha roda em terminal separado, sem encerrar os processos anteriores. Comando de envio acima. Para outros computadores na LAN, publicar as portas dos servidores e substituir `127.0.0.1` por IPs alcançáveis em **todos** os endereços anunciados; não confundir endereço de bind com destino das chamadas RPC. gRPC sem TLS é permitido apenas para demonstração em rede confiável.

## Testes e resultados

```bash
python -m pytest -q
```

Testes de unidade + integração cobrem análise de logs, Protobuf, Lamport, três workers com processos distintos, chamadas gRPC, entradas inválidas, análise não encontrada, timeout/worker offline, eleição e troca de líder com queda simulada. Arquivos em `tests/`.

## Como observar os mecanismos distribuídos
- **RPC:** `SubmitLogs` e `GetAnalysisStatus` expostos no coordenador; `AssignTask` nos workers.
- **Paralelismo:** jobs particionados em lotes, chamadas `AssignTask` concorrentes pelo coordenador e `worker_id` em cada finding.
- **Lamport:** eventos de `send`/`receive` incluem `logical_timestamp`, atualizados por `max(local, recebido)+1`.
- **Eleição:** candidatos configurados com prioridades únicas; maior prioridade viva anuncia-se como líder; os outros rejeitam escrita com `FAILED_PRECONDITION`.
- **Falha:** um worker indisponível leva a `ANALYSIS_FAILED` e erro observável, sem ocultar resultados parciais.

## Escopo e entregáveis
| Agora (Entrega 1) | Depois (Entrega 2) |
|---|---|
| gRPC, Lamport, eleição simples, workers e agregação, testes | Replicação, reatribuição/retries, tolerância robusta, avaliação de desempenho ampliada |

Arquitetura: `docs/architecture-entrega1.md`; contrato: `proto/debugmesh/v1/debugmesh.proto`; relatório inicial: `docs/relatorio-entrega1.tex`.

## Limites e segurança
- Regras determinísticas de diagnóstico; hipóteses e confiança são heurísticas, não verdades confirmadas.
- Protocolo utiliza gRPC sem autenticação/TLS na demo, **não expor à internet**.
- Teste apenas com logs sintéticos ou anonimizados. Evidências podem conter conteúdo sensível.
- A eleição simplificada não é consenso: em partições de rede pode haver split-brain.
