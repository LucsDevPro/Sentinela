"""Gera .github/ISSUE_TEMPLATE/atestado.yml com a lista de agentes de
data/agentes_nomes.json. Rode de novo quando entrar/sair agente:
    python scripts/gerar_form_atestado.py
"""
import json, os, sys

def rotulo(id_agente, info):
    nome = (info.get("nome") or "").strip() or f"Agente {id_agente}"
    equipe = (info.get("equipe") or "").strip()
    return f"{nome} — {equipe + ' ' if equipe else ''}(ID {id_agente})"

def gerar(caminho_nomes="data/agentes_nomes.json",
          saida=".github/ISSUE_TEMPLATE/atestado.yml"):
    with open(caminho_nomes, encoding="utf-8") as f:
        nomes = json.load(f)
    opcoes = sorted((rotulo(i, v) for i, v in nomes.items()), key=str.casefold)
    linhas = [
        "name: Lançar atestado",
        "description: Registra o(s) dia(s) de atestado de um agente (sem desconto de pontos).",
        'title: "Atestado: "',
        "labels: [atestado]",
        "body:",
        "  - type: markdown",
        "    attributes:",
        "      value: |",
        "        Preencha só o agente e as datas. **Não escreva CID, diagnóstico nem o",
        "        conteúdo do atestado** — o sistema guarda apenas as datas.",
        "  - type: dropdown",
        "    id: agente",
        "    attributes:",
        "      label: Agente",
        "      options:",
    ] + [f"        - {json.dumps(o, ensure_ascii=False)}" for o in opcoes] + [
        "    validations:",
        "      required: true",
        "  - type: input",
        "    id: inicio",
        "    attributes:",
        "      label: Primeiro dia do atestado",
        "      description: Formato dd/mm/aaaa",
        "      placeholder: 27/10/2026",
        "    validations:",
        "      required: true",
        "  - type: input",
        "    id: fim",
        "    attributes:",
        "      label: Último dia do atestado",
        "      description: Formato dd/mm/aaaa. Para um dia só, repita a data do primeiro dia.",
        "      placeholder: 27/10/2026",
        "    validations:",
        "      required: true",
        "  - type: checkboxes",
        "    id: confirmo",
        "    attributes:",
        "      label: Confirmação",
        "      options:",
        "        - label: Não informei CID nem diagnóstico neste formulário.",
        "          required: true",
    ]
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    with open(saida, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
    return len(opcoes)

if __name__ == "__main__":
    print(f"✅ Formulário gerado com {gerar()} agentes.")
