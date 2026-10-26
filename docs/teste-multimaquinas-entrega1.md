# Teste em rede — primeira entrega

## Objetivo
Demonstrar gRPC entre nós em sistemas distintos, processamento paralelo, relógios lógicos de Lamport e eleição após a parada do coordenador principal. Este roteiro usa endereços **ilustrativos**: substitua pelos IPs reais.

## Sem duas máquinas físicas
**Opção 1 — Docker Compose no mesmo computador:** execute `docker compose up --build -d`, `python -m debugmesh submit --coordinator localhost:50051 --file samples/ci_pipeline.log --wait`, `docker compose stop coordinator-a` e repita a submissão na porta `50052`. Documente resultados em `docker compose logs`. Isso prova tráfego entre contêineres, **não dois computadores físicos**.

**Opção 2 — duas VMs Linux:** crie duas máquinas virtuais (VirtualBox, VMware ou Hyper-V) conectadas à mesma rede virtual host-only/interna. Exemplo de IPs: VM A `192.168.56.11`, VM B `192.168.56.12`. Configure adaptador NAT adicional se precisar de internet para instalar dependências. Use os comandos abaixo com os IPs das VMs. Uma máquina física com duas VMs ainda não equivale a dois computadores físicos: confirme a aceitação desse cenário com o professor.

## Dois computadores reais na LAN
Exemplo: A = `192.168.1.10`, B = `192.168.1.20`. Em **ambos**, faça clone da branch `release/primeira-entrega` e execute `python -m pip install -e '.[dev]'`. Confirme endereços (`ip -4 addr` no Linux; `ipconfig` no Windows), conectividade e firewall. Liberar TCP 50051/50061 em A e TCP 50052/50062 em B. Não exponha o gRPC inseguro à internet.

Abra dois terminais em cada computador. Primeiro, inicie os workers:

**A, terminal 1:**
```bash
python -m debugmesh worker --id worker-a --bind 0.0.0.0:50061
```

**B, terminal 1:**
```bash
python -m debugmesh worker --id worker-b --bind 0.0.0.0:50062
```

Depois, inicie os coordenadores:

**A, terminal 2:**
```bash
python -m debugmesh coordinator --id coordinator-a --bind 0.0.0.0:50051 --priority 20 --peers coordinator-b@10@192.168.1.20:50052 --workers 192.168.1.10:50061,192.168.1.20:50062 --batch-size 3
```

**B, terminal 2:**
```bash
python -m debugmesh coordinator --id coordinator-b --bind 0.0.0.0:50052 --priority 10 --peers coordinator-a@20@192.168.1.10:50051 --workers 192.168.1.10:50061,192.168.1.20:50062 --batch-size 3
```

**A, novo terminal:** 
```bash
python -m debugmesh submit --coordinator 192.168.1.10:50051 --file samples/ci_pipeline.log --wait
```

Confira `ANALYSIS_COMPLETED` e `worker_id` dos **dois** workers. Interrompa **somente** `coordinator-a` (Ctrl+C no terminal 2 de A), mantendo `worker-a` em execução. Após o B registrar `leader_unreachable` e `elected`, envie nova análise para `192.168.1.20:50052`.

## Evidências mínimas
1. Prints/logs de IPs e testes de conexão em máquinas diferentes.
2. `analysis_id`, diagnósticos e dois `worker_id` diferentes.
3. Logs `send` e `receive` com `logical_timestamp`; no recebimento, o relógio local torna-se maior que o timestamp remoto.
4. Log de eleição inicial e da sucessão após a parada do coordenador A.
5. Testes `python -m pytest -q` e GitHub Actions aprovados.

**Limitações:** não há consenso, replicação nem recuperação das análises em memória do coordenador que caiu; se um worker ficar indisponível, a análise termina como `ANALYSIS_FAILED`. A opção com uma só máquina comprova rede virtual mas não substitui uma exigência literal de duas máquinas físicas.
