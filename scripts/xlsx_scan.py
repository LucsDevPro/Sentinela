import atexit
import os
from functools import lru_cache

import openpyxl
import pandas as pd

def scan_tables(ws, max_col=32):
    tables = []
    current_header = None
    current_data = []
    def finalize():
        nonlocal current_header, current_data
        if current_header is not None and current_data:
            tables.append((current_header, current_data))
        current_header = None
        current_data = []
    # iter_rows(values_only=True) lê a planilha em fluxo; o laço antigo com
    # ws.cell(r, c) criava um objeto Cell por célula e era o gargalo do dashboard.
    for linha in ws.iter_rows(min_row=1, max_col=max_col, values_only=True):
        vals = list(linha[:max_col])
        if len(vals) < max_col:  # no modo read_only as linhas curtas não vêm completas
            vals.extend([None] * (max_col - len(vals)))
        is_header = (('Agente' in vals) and ('Equipe' in vals)) or (('Motivo' in vals) and ('Quem' in vals))
        non_null = sum(v is not None for v in vals)
        first = vals[0]
        is_total = isinstance(first, str) and first.strip().upper().startswith('TOTAL')
        is_title_or_blank = non_null <= 1
        if is_header:
            finalize()
            current_header = vals
            continue
        if is_title_or_blank or is_total:
            finalize()
            continue
        if current_header is not None:
            current_data.append(vals)
    finalize()
    return tables

def tables_to_dfs(tables):
    dfs = []
    for header, data in tables:
        n = len(header)
        while n > 0 and header[n-1] is None:
            n -= 1
        header = header[:n]
        rows = [row[:n] for row in data]
        df = pd.DataFrame(rows, columns=header)
        dfs.append(df)
    return dfs

@lru_cache(maxsize=4)
def _abrir(path, mtime_ns, tamanho):
    # mtime/tamanho entram na chave: se o arquivo mudar (testes, regeneração),
    # o cache não devolve uma versão velha. Abre UMA vez por planilha, em vez
    # de uma vez por aba lida.
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    _abertas.append(wb)
    return wb


# No modo read_only o openpyxl mantém o arquivo aberto até close(). Fecha tudo ao sair do processo,
# para não deixar o .xlsx travado (no Windows um arquivo aberto não pode ser apagado nem sobrescrito).
_abertas = []


@atexit.register
def _fechar_planilhas():
    for wb in _abertas:
        try:
            wb.close()
        except Exception:
            pass

def get_tables(path, sheet_name):
    st = os.stat(path)
    wb = _abrir(os.fspath(path), st.st_mtime_ns, st.st_size)
    return tables_to_dfs(scan_tables(wb[sheet_name]))

def get_table(path, sheet_name, index=0):
    return get_tables(path, sheet_name)[index]
