# Trabalho Prático - Computação Distribuída

Pontifícia Universidade Católica de Minas Gerais - Instituto de Ciências Exatas e Informática  
Computação Distribuída - Ciência da Computação, Coração Eucarístico, 2026.2  
Professor: Luigi D. C. Soares

## Proposta do projeto

- [Documento detalhado em Markdown](docs/proposta-debugmesh.md)
- [Versão web da proposta](https://ghrcastro.github.io/TP01-Computacao-Distribuida/)

## Objetivo

Este trabalho prático tem o objetivo de aprofundar o estudo e o desenvolvimento de sistemas distribuídos. O grupo deverá projetar e implementar uma solução distribuída para resolver um problema de sua escolha dentro desse contexto.

## Formação de grupos

Os grupos devem ter de **4 a 6 pessoas**. Cada grupo escolherá um tema para o desenvolvimento do sistema distribuído.

## Escolha do tema

O tema é escolhido pelo grupo, dentre as sugestões abaixo ou uma alternativa aprovada pelo professor. O sistema deve resolver um problema computacional complexo que possa ser dividido em unidades de trabalho executadas de forma distribuída em máquinas diferentes.

Temas sugeridos:

1. Algoritmo genético distribuído.
2. Algoritmo de colônia de formigas distribuído.
3. Segmentação de imagens distribuída, por exemplo com SLIC.
4. Simulação de comunicação entre nós distribuídos, como uma rede de sensores.
5. Resolução distribuída de um problema de otimização.
6. Algoritmos de machine learning distribuídos.
7. Sistema de banco de dados distribuído com replicação e consistência.
8. Jogo online multiplayer com estado compartilhado entre servidores distribuídos.
9. Sistema de recomendação distribuído.

## Requisitos gerais

1. O sistema deve ser distribuído e ter pelo menos dois nós, executáveis em máquinas conectadas a uma rede local.
2. Deve realizar operações paralelizadas de forma eficiente e lidar com falhas de comunicação entre os nós.
3. Bibliotecas de comunicação podem ser usadas, mas alguns algoritmos/protocolos devem ser implementados manualmente de acordo com cada entrega.

## Entrega 1

### Requisitos

Incorporar pelo menos dois dos itens abaixo:

- RPC (sugestão: gRPC);
- sincronização de relógios físicos;
- sincronização de relógios lógicos;
- eleição de líder;
- controle de concorrência ou exclusão mútua distribuída;
- web services.

### Relatório

Entregar um relatório PDF de até **4 páginas**, no template de artigo da SBC, contendo no mínimo:

- explicação do problema escolhido;
- arquitetura do sistema: entidades, mensagens e papéis;
- implementação dos requisitos escolhidos;
- desafios e problemas encontrados;
- papel de cada integrante no trabalho.

## Entrega 2

### Requisitos

Evoluir a base da primeira entrega com métodos adequados para tratamento de falhas. Além disso, escolher ao menos um item:

- controle de réplicas;
- consistência em transações distribuídas, por exemplo Two-Phase Commit (2PC);
- análise de desempenho em comparação com uma execução em uma única máquina, quando aplicável.

### Artefatos

- Expandir o relatório para até **6 páginas**, mantendo e atualizando as seções da primeira entrega.
- Detalhar o tratamento de falhas, testes, expansão escolhida, conclusão e melhorias futuras.
- Enviar código-fonte e instruções de execução.
- Realizar apresentação de até **10 minutos**, demonstrando arquitetura, funcionamento e resultados.

## Avaliação

Serão avaliadas a clareza da documentação técnica, originalidade e complexidade do tema, cumprimento dos requisitos, funcionamento do sistema distribuído, qualidade da apresentação e domínio do grupo sobre o sistema e as partes em que cada pessoa atuou.

Ferramentas de IA podem auxiliar a escrita, mas textos praticamente gerados de forma automática serão desconsiderados. A organização das ideias pelo grupo também é avaliada.

## Datas e pontuação

- Entrega 1: 10 pontos; data a consultar no Canvas.
- Entrega 2: 20 pontos; data e apresentação a consultar no Canvas e no plano de disciplina.
