"""Deterministic analyzers, no external LLM or network dependencies."""
import re
from .generated import debugmesh_pb2 as pb

# Order matters: one finding per matching log line; categories stay predictable.
RULES = [
    (re.compile(r'(ModuleNotFoundError|ImportError|cannot find module|package .* not found)',re.I),'build','Dependência ou módulo indisponível','Verificar dependências, instalação e nomes dos módulos','Executar build em ambiente limpo',0.91),
    (re.compile(r'(compilation failed|syntaxerror|error:.*(?:undeclared|undefined reference)|build failed)',re.I),'build','Falha de compilação ou sintaxe','Inspecionar linha indicada e configurações do compilador','Executar novamente o comando de compilação',0.88),
    (re.compile(r'(assertionerror|test .* failed|FAILED\s+tests?/|\btest failure\b)',re.I),'tests','Falha em teste automatizado','Reproduzir teste e inspecionar asserção e fixture','Executar somente o teste que falhou',0.89),
    (re.compile(r'(timeout|timed out|connection refused|connection reset)',re.I),'infrastructure','Timeout ou falha de conectividade','Inspecionar disponibilidade, DNS, portas e prazos','Testar conectividade e repetir em ambiente controlado',0.84),
    (re.compile(r'(nullpointerexception|traceback|unhandled exception|exception:)',re.I),'exception','Exceção em tempo de execução','Analisar stack trace e entradas que causaram a exceção','Criar teste de regressão para o cenário',0.88),
    (re.compile(r'\b(error|fatal|failed)\b',re.I),'general','Erro não classificado','Inspecionar contexto e causa indicada no log','Reproduzir a falha com logging detalhado',0.60),
]


def analyze(lines, task_id, worker_id, timestamp_fn):
    results=[]
    for line in lines:
        value=line.text.strip()
        for expression,category,hypothesis,fix,test,confidence in RULES:
            if expression.search(value):
                results.append(pb.Finding(
                    task_id=task_id, worker_id=worker_id, category=category,
                    evidence=[f'line {line.line_number}: {value[:400]}'],
                    root_cause_hypothesis=hypothesis,
                    suggested_fix=fix, suggested_test=test,
                    confidence=confidence, logical_timestamp=timestamp_fn(),
                ))
                break
    return results
