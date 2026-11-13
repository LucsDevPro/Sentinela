# Regras de negócio (valores conferidos no código em 02/11/2026)

Fonte única dos valores: `scripts/coleta/` (`pontos.py`, `parametros.py`, `deteccao.py`, `calculos.py`: ranking, ausências) e `scripts/generate_dashboard.py` (custos).

## Pontuação (base 100, piso 0, teto 100)
Faixas: **≥ 90 Excelente · 75–89,9 Bom · 60–74,9 Atenção · < 60 Crítico**.

| Critério | Pontos | Constante |
|---|---|---|
| Turno sem lançamento | −1,5 por turno | `PONTOS_PERDA_TURNO_SEM_LANCAMENTO` |
| Dia inteiro sem lançamento (2 turnos) | −1,0 a mais (dia = −4,0) | `PONTOS_PERDA_DIA_INTEIRO_SEM_LANCAMENTO` |
| Início da manhã após 08:30 / fim antes de 10:00 | −0,3 por dia, cada | `PONTOS_PERDA_INICIO/FIM_MANHA_*` |
| Início da tarde após 14:30 / fim antes de 16:00 | −0,3 por dia, cada | `PONTOS_PERDA_INICIO/FIM_TARDE_*` |
| Visita rápida (< 3 min) | −0,2 por visita | `PONTOS_PERDA_VISITA_RAPIDA` |
| Visita duplicada | −0,3 | `PONTOS_PERDA_VISITA_DUPLICADA` |
| Sequência suspeita (visitas < 50 s uma da outra) | −1 por visita | `PONTOS_PERDA_SEQUENCIA_SUSPEITA` |
| Visita fora do expediente / fim de semana | −0,5 | `PONTOS_PERDA_FORA_EXPEDIENTE` |
| Dia que não bateu a meta | −0,5 | `PONTOS_PERDA_DIA_SEM_META` |
| Dia que bateu a meta | +1 | `PONTOS_GANHO_DIA_COM_META` |
| Bônus únicos: sem visita rápida (+5), sem turno sem lançamento (+5), pontualidade perfeita (+3) | | `PONTOS_GANHO_*` |
Desligados (0): visita longa (> 30 min), duração negativa, visita no almoço. Meta diária padrão: 20 visitas (`META_VISITAS_DIA`; por equipe em `data/metas_equipes.json`).
Expediente: manhã 07–11h, tarde 13–17h (`HORA_EXPEDIENTE_*`).

## Ausência: Turno sem Lançamento × Possível Evento (desde 02/11/2026)
1. **Padrão:** turno sem nenhuma visita = **Turno sem Lançamento** → desconta.
2. **Antes de descontar** confere o cronograma (`MOTIVOS_CRONOGRAMA`): Chuva, Folga, Meia folga, Ausência justificada (atestado),
   Meia ausência justificada, Reunião/Treinamento, Férias, Levantamento de Índice, Ovitrampa, Recuperação de Casas. Coberto = não desconta.
   Feriado nacional sem visita não conta.
3. **Chuva automática / Possível Evento** (sem desconto), nesta ordem, no mesmo dia e turno:
   - **Regra suprema (08/11/2026):** `LIMITE_AGENTES_EVENTO_TURNO` (**23**) ou mais agentes, de qualquer equipe, sem lançamento = **Chuva**,
     confirmada automaticamente (sem validação manual, sem desconto; não depende de `EVENTO_COLETIVO_A_PARTIR_DE`). A contagem inclui quem já
     está coberto por chuva/reunião no cronograma (`CONTAR_COBERTOS_POR_EVENTO_NO_LIMITE = True`); férias, folga e atestado não entram;
   - **22 ou menos, regra da equipe:** **todos** os agentes ativos da equipe (2 ou mais) sem lançamento = Possível Evento (chuva isolada ou
     reunião; sem desconto, a coordenação confirma o motivo). Ativo = não coberto pelo cronograma no turno;
   - **senão:** Turno sem Lançamento (falta; desconta).
   Equipes sob demanda ficam fora. Vale para todos os períodos (`EVENTO_COLETIVO_A_PARTIR_DE = None`).
4. Cada agente só é avaliado a partir da **própria** 1ª visita se começou dentro do período; quem já trabalhava antes é avaliado desde o 1º dia.
5. Reverter um evento que foi falta: ajuste manual em `data/ajustes_ranking.json` (não existe, ainda, "forçar desconto").

## Detecção automática (`data/deteccoes_pendentes.json`)
- **Férias/atestado individual:** ≥ `LIMITE_DIAS_UTEIS_FERIAS` (**7**) dias úteis seguidos sem lançamento. Ocorrência máx. 30 dias corridos
  (`LIMITE_DIAS_CORRIDOS_OCORRENCIA`); excesso vira **falta**. Agentes em `data/agentes_sem_abono.json` entram como falta.
- **Paralisação coletiva:** todos os agentes ativos da equipe sem lançamento no dia. **Desde 13/11/2026 nasce `confirmada` como Chuva,
  sem validação manual** (`CONFIRMAR_CHUVA_AUTOMATICAMENTE = True`); a coordenação ainda pode trocar o motivo ou marcar falta no editor.
- **Férias/atestado individual** novos entram `pendente` (continuam descontando) até a coordenação confirmar; decisões antigas (`confirmada`/`falta`) não mudam.
  Confirmar férias sozinho: `CONFIRMAR_FERIAS_AUTOMATICAMENTE = True`. Exigir validação manual da paralisação de novo: `CONFIRMAR_CHUVA_AUTOMATICAMENTE = False`.
- Períodos que se tocam em até 3 dias (`TOLERANCIA_DIAS_MESMO_EVENTO`) são o mesmo evento.

## Dias esperados e ranking
- **Dias esperados** = dias úteis do período − dias justificados pelo cronograma em que o agente não trabalhou (meia folga = 0,5; turno de possível evento = 0,5).
- Períodos de até 45 dias (todos os meses): **sem fator de normalização**; presença mínima: abaixo de 50% de dias trabalhados/esperados a nota é proporcional (`PRESENCA_MINIMA_FRACAO`).
- **Acumulado** (> 45 dias): método antigo, com fator de normalização por mês (teto 2,0 — `TETO_FATOR_NORMALIZACAO`).
- Aviso "possível afastamento não registrado": poucos dias trabalhados + ≥ 4 turnos sem lançamento → conferir férias/atestado no cronograma.

## Custos & Produtividade (`generate_dashboard.py`)
- Salário do agente = 3 × R$ 1.621,00 = **R$ 4.863,00**; mês de referência = 22 dias úteis (`DIAS_UTEIS_MES_REF`).
- **Hora útil** = tempo dentro dos imóveis; cada visita conta no máximo **20 min** (`TETO_DURACAO_MEDIA_MIN`).
- **Custo no ritmo** = salário ÷ (horas úteis/dia × 22) — só vale nos dias trabalhados.
- **Custo real** = custo no ritmo × (dias esperados ÷ dias trabalhados, máx. 1): inclui só a falta sem justificativa (férias, atestado,
  folga, treinamento e paralisações já saem dos dias esperados). É o que vale para comparar agentes.
- Médias gerais = folha ÷ horas úteis de todos (não a média dos custos individuais). Faixas: verde ≤ R$ 100, amarelo ≤ R$ 150, vermelho acima; gráfico corta em R$ 300.
- Tabela mensal por agente: mesmo cálculo, mês a mês (cada mês usa a aba Ranking do próprio mês).

> Explicações longas e o histórico das correções do ranking e da ausência: `docs/REGRAS_DETALHADAS.md`.
