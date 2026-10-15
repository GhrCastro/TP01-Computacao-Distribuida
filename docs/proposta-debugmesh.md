# DebugMesh

## Pipeline distribuído de análise de logs e orquestração de agentes de diagnóstico

**Disciplina:** Computação Distribuída — Ciência da Computação, PUC Minas  
**Professor:** Luigi D. C. Soares  
**Período:** 2026.2

## 1. Resumo da proposta

O DebugMesh é um sistema distribuído que recebe logs de aplicações, divide a análise em lotes e os distribui para agentes especializados. Cada agente identifica evidências de falha em uma categoria — exceções, testes, infraestrutura ou desempenho — e envia um diagnóstico estruturado ao coordenador. Um agregador correlaciona os resultados e apresenta uma hipótese de causa raiz, evidências, grau de confiança e sugestões de correção e testes.

A proposta não pretende executar alterações automaticamente no código. A automação produz **propostas revisáveis por pessoas**, preservando segurança e permitindo que a qualidade da recomendação seja avaliada no contexto do trabalho.

## 2. Problema

Logs de sistemas reais costumam ser extensos, distribuídos entre serviços e difíceis de analisar manualmente durante incidentes. Uma falha pode aparecer como exceção em um serviço, teste quebrado em outro e timeout em um terceiro. Processar tudo sequencialmente torna o diagnóstico lento e dificulta a correlação de eventos.

O problema tratado é: **como analisar lotes de logs concorrentemente, manter uma ordenação observável dos eventos e consolidar diagnósticos mesmo quando um nó de processamento deixa de responder?**

## 3. Objetivos

### Objetivo geral

Construir um pipeline distribuído, com pelo menos dois nós, para analisar logs e consolidar diagnósticos técnicos.

### Objetivos específicos

- dividir uma coleção de logs em tarefas independentes;
- distribuir as tarefas entre agentes workers por RPC;
- manter relógios lógicos nos eventos e nas mensagens;
- eleger um coordenador líder para distribuir tarefas;
- consolidar resultados em um diagnóstico rastreável;
- detectar indisponibilidade e reatribuir tarefas em uma evolução posterior;
- comparar o processamento distribuído com a execução local, quando aplicável.

## 4. Escopo do MVP

O MVP processará arquivos de logs simulados ou gerados por uma aplicação de exemplo. Cada diagnóstico retornará os campos abaixo:

```json
{
  "incidentId": "inc-042",
  "category": "exception",
  "evidence": ["NullPointerException em PaymentService:88"],
  "rootCauseHypothesis": "customerId ausente no fluxo de checkout",
  "suggestedFix": "validar customerId antes de consultar o repositório",
  "suggestedTest": "checkout sem customerId deve retornar HTTP 400",
  "confidence": 0.82,
  "logicalTimestamp": 41
}
```

Na primeira versão, os agentes poderão combinar regras determinísticas e dados simulados. Um adaptador para um provedor de IA pode ser incluído como extensão opcional, mas o funcionamento do sistema não dependerá de uma API paga ou de credenciais externas.

## 5. Arquitetura proposta

```text
Fonte de logs / GitHub Actions (opcional)
                    |
                    v
         +-----------------------+
         | Coordenador líder     |
         | fila, partição,       |
         | estado das tarefas    |
         +----------+------------+
                    | gRPC
      +-------------+-------------+
      |             |             |
      v             v             v
+-----------+ +-----------+ +-----------+
| Agente de | | Agente de | | Agente de |
| exceções  | | testes    | | infra/    |
|           | |           | | desempenho|
+-----+-----+ +-----+-----+ +-----+-----+
      \             |             /
       \            |            /
        v           v           v
         +-----------------------+
         | Agregador de          |
         | diagnósticos          |
         +----------+------------+
                    |
                    v
          CLI ou painel de consulta
```

### Componentes

| Componente | Responsabilidade |
|---|---|
| Cliente/fonte | Envia um conjunto de logs e consulta o resultado. Pode ser uma CLI; GitHub Actions será apenas uma fonte opcional de eventos. |
| Coordenador | Cria tarefas, particiona os logs, registra status, escolhe workers e consolida a execução. |
| Agentes workers | Processam lotes e retornam diagnósticos estruturados em categorias distintas. |
| Agregador | Agrupa evidências, remove duplicações e cria o diagnóstico final. Pode iniciar acoplado ao coordenador. |
| Registro de estado | Mantém tarefas, tentativas, resultados e eventos para demonstração. Na primeira entrega pode ser memória/arquivo; na segunda pode ser replicado. |

## 6. Comunicação e dados

A comunicação será feita por **gRPC**. As operações iniciais previstas são:

- `SubmitLogs`: cria uma análise a partir de um conjunto de logs;
- `AssignTask`: envia um lote de logs a um worker;
- `SubmitFinding`: entrega o diagnóstico parcial do worker;
- `GetAnalysisStatus`: consulta estado, resultados e timestamps;
- `Heartbeat`: informa que um nó continua disponível;
- `ElectLeader`: troca mensagens para eleger o coordenador.

Cada mensagem transportará `requestId`, identificador do nó emissor, timestamp lógico e, quando aplicável, a tentativa da tarefa. Isso permite registrar uma linha do tempo coerente mesmo que a ordem física de chegada varie.

## 7. Mecanismos distribuídos

### RPC/gRPC

O coordenador e os workers serão processos independentes. gRPC definirá contratos, serialização e comunicação entre os nós. O uso será demonstrado com, no mínimo, um coordenador e um worker em execução simultânea.

### Relógios lógicos de Lamport

Cada nó manterá um contador. Ele é incrementado em eventos locais e no envio de mensagens; no recebimento, o contador passa a ser `max(local, recebido) + 1`. Os diagnósticos e logs de execução mostrarão o timestamp, evidenciando a ordenação causal.

### Eleição de líder

Os coordenadores candidatos terão identificadores únicos. Em caso de inicialização concorrente ou indisponibilidade do líder, será executado um algoritmo simples e documentado de eleição, adequado à topologia escolhida. O líder eleito será o único responsável por atribuir novas tarefas.

## 8. Plano da primeira entrega — 1º de novembro de 2026

### Resultado esperado

- tema e cenário de logs definidos;
- dois ou mais processos/nós em execução;
- comunicação gRPC funcional;
- relógios lógicos integrados às mensagens;
- eleição de líder demonstrável;
- processamento de lote com diagnóstico estruturado;
- relatório SBC de até quatro páginas.

### Divisão inicial de responsabilidades

| Responsável | Entrega |
|---|---|
| Integrante 1 | Tema, escopo, conjunto de logs e estrutura do relatório. |
| Integrante 2 | Arquitetura, contrato gRPC e coordenador. |
| Integrante 3 | Relógios lógicos, instrumentação e testes de ordenação. |
| Integrante 4 | Eleição de líder, integração e roteiro de demonstração. |

As tarefas rastreáveis estão nas issues [#7](https://github.com/GhrCastro/TP01-Computacao-Distribuida/issues/7), [#8](https://github.com/GhrCastro/TP01-Computacao-Distribuida/issues/8), [#9](https://github.com/GhrCastro/TP01-Computacao-Distribuida/issues/9) e [#10](https://github.com/GhrCastro/TP01-Computacao-Distribuida/issues/10).

## 9. Evolução para a segunda entrega

| Evolução | Como será aplicada |
|---|---|
| Tratamento de falhas | Heartbeats, timeouts, detecção de worker indisponível e reatribuição de tarefas não concluídas. |
| Controle de réplicas | Replicar o registro de tarefas entre coordenadores ou manter uma réplica de leitura do estado. |
| Consistência | Garantir que uma tarefa tenha somente um resultado aceito, apesar de retry ou reexecução. |
| Desempenho | Comparar tempo de análise sequencial e distribuída com diferentes números de workers. |

## 10. Evolução desejada

Em uma evolução posterior, os agentes poderão ganhar autonomia controlada para investigar uma hipótese de correção em um ambiente isolado. O fluxo desejado é:

1. o diagnóstico consolidado gera uma proposta de alteração, sempre revisável por uma pessoa;
2. um agente cria uma branch de trabalho específica para o incidente;
3. o agente instancia um ambiente isolado para aplicar a proposta e executar os testes relevantes;
4. os resultados — diff, logs de teste, diagnóstico e limitações — são anexados à proposta para revisão humana.

O ambiente isolado poderá ser uma sandbox baseada em containers, uma microVM ou outra solução apropriada. A tecnologia será escolhida futuramente após avaliar isolamento, custo, tempo de inicialização, suporte às linguagens do projeto e facilidade de reprodução. Esta evolução **não** autoriza merge, deploy ou alteração automática na branch principal: a aprovação humana continuará obrigatória.

## 11. GitHub Actions: papel opcional

GitHub Actions não será o sistema distribuído. Ele pode ser usado como gatilho de integração: após uma falha de testes ou execução manual, o workflow coleta logs e chama a API do coordenador. Isso aproxima a solução de um fluxo de desenvolvimento real, mas o sistema continuará executável localmente, inclusive sem acesso ao GitHub.

## 12. Demonstração planejada

1. Iniciar um coordenador e três workers com Docker Compose ou comandos locais.
2. Submeter um arquivo contendo logs de exceção, falhas de teste e timeout.
3. Observar a distribuição dos lotes, timestamps lógicos e resultados parciais.
4. Consultar o diagnóstico consolidado.
5. Interromper um worker ou o líder e demonstrar a eleição/recuperação prevista para cada entrega.

## 13. Riscos e limites

- **Dependência de IA externa:** mitigada por agentes determinísticos que mantêm a demonstração reproduzível.
- **Escopo excessivo:** o MVP não edita nem executa código automaticamente.
- **Dados sensíveis em logs:** os dados usados na demonstração serão sintéticos ou anonimizados.
- **Complexidade de consenso:** a primeira entrega usará um algoritmo de eleição simples; mecanismos robustos de réplica ficam para a evolução.
- **Execução de código sugerido:** qualquer teste futuro ocorrerá somente em ambiente isolado e descartável, sem credenciais de produção e com aprovação humana antes de alterações permanentes.

## 14. Critérios de sucesso

O projeto será considerado bem-sucedido quando for possível executar o sistema localmente com múltiplos nós, processar uma entrada dividida entre agentes, observar os mecanismos distribuídos escolhidos e obter um diagnóstico consolidado com evidências rastreáveis.
