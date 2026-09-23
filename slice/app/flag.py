"""Feature flag por percentual — CTX-11.

Existe porque a restrição é "primeira melhoria em produção em 30 dias, **sem
janela de indisponibilidade**". Sem flag, a alternativa seria migração com
janela de manutenção — que o enunciado proíbe.

Duas propriedades, e a segunda é a que não é óbvia:

1. **Rollback sem deploy.** Desligar a flag reverte o roteamento na hora.
   É critério do gate G30, não conveniência.

2. **Roteamento DETERMINÍSTICO pela chave.** O mesmo pedido não pode alternar
   de caminho entre um retry e outro. Se o roteamento fosse aleatório, um
   retry poderia cair no legado e criar duplicata **apesar** da idempotência
   do caminho novo — a proteção da ADR-0001 valeria só dentro do caminho que
   a implementa.
"""
import hashlib

_percentual = 0


def definir(percentual: int) -> None:
    """0 = tudo no legado · 100 = tudo no caminho novo."""
    global _percentual
    _percentual = max(0, min(100, int(percentual)))


def percentual() -> int:
    return _percentual


def desligar() -> None:
    """Rollback. Sem deploy, sem migração reversa."""
    definir(0)


def usa_caminho_novo(chave: str) -> bool:
    if _percentual <= 0:
        return False
    if _percentual >= 100:
        return True
    balde = int(hashlib.sha256(chave.encode("utf-8")).hexdigest()[:8], 16) % 100
    return balde < _percentual
