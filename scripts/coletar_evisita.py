# -*- coding: utf-8 -*-
# ============================================================
# ANÁLISE DE TEMPO DE VISITAS - E-VISITA (SES/MS)
# Coleta pendência "Não" + tipo_visita=0 (normal + recuperação)
# Nome após todas páginas + Duplicadas + Horários por Turno
# ============================================================
"""Fachada do coletor. O código fica no pacote `scripts/coleta/` (um módulo por assunto,
em camadas: cada módulo só importa dos anteriores da lista abaixo). Este arquivo:

  * mantém `python scripts/coletar_evisita.py ...` e `import coletar_evisita as C` funcionando;
  * reexporta TODOS os nomes dos módulos (`C.calcular_pontuacao`, `C.CPF`, `C._hoje_local`...);
  * repassa atribuições (`C.HOJE_OVERRIDE = ...`, usado nos testes) para os módulos em que o
    nome vive, para que a função que lê a variável enxergue o novo valor.

Onde mexer: parâmetros em coleta/parametros.py e coleta/pontos.py; regras em
coleta/calculos.py e coleta/deteccao.py; veja docs/MAPA.md (índice função -> arquivo:linha).
"""
import logging
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("evisita")

# Ordem = camadas (cada módulo só depende dos anteriores).
from coleta import parametros as _parametros
from coleta import pontos as _pontos
from coleta import auxiliares as _auxiliares
from coleta import deteccao as _deteccao
from coleta import sessao as _sessao
from coleta import calculos as _calculos
from coleta import colunas as _colunas
from coleta import estilo_excel as _estilo_excel
from coleta import abas as _abas
from coleta import ausencias_ranking as _ausencias_ranking
from coleta import saida_excel as _saida_excel
from coleta import processamento as _processamento
from coleta import cache_semanas as _cache_semanas
from coleta import consolidacao as _consolidacao
from coleta import historico as _historico
from coleta import execucao as _execucao

_MODULOS = [_parametros, _pontos, _auxiliares, _deteccao, _sessao, _calculos, _colunas, _estilo_excel, _abas, _ausencias_ranking, _saida_excel, _processamento, _cache_semanas, _consolidacao, _historico, _execucao]

for _m in _MODULOS:
    for _nome, _valor in vars(_m).items():
        if not (_nome.startswith("__") and _nome.endswith("__")):
            globals().setdefault(_nome, _valor)


class _Fachada(types.ModuleType):
    """Atribuir `C.X = valor` também atualiza X em cada módulo do pacote que o possui."""

    def __setattr__(self, nome, valor):
        for m in _MODULOS:
            if nome in m.__dict__:
                setattr(m, nome, valor)
        super().__setattr__(nome, valor)


sys.modules[__name__].__class__ = _Fachada

from coleta.execucao import main  # noqa: E402,F401  (também reexportado acima)

if __name__ == "__main__":
    main()
