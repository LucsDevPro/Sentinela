# Regras de negócio — explicações e histórico das correções

> Migrado do `README.md` em 03/11/2026 sem remover informação. Onde havia texto desatualizado ele foi corrigido
> (lista em `docs/DECISOES.md`, entrada de 03/11/2026). Em caso de dúvida valem `CLAUDE.md` e `docs/REGRAS.md`.
> Versão longa e explicativa. A tabela atual de pontos e constantes está em `docs/REGRAS.md`.

## Ranking normalizado "por mês" — funciona igual em qualquer período

`PONTOS_INICIAIS` (100) foi calibrado pra um período de ~`DIAS_UTEIS_MES`
(22) dias úteis trabalhados. Sem correção, avaliar um agente num período
maior (o Acumulado, por exemplo, somando vários meses) acumula 3-4x mais
ocorrências brutas de cada critério — mais dias sem meta, mais visitas fora
do expediente etc. — e a pontuação desabava pro chão mesmo com o
desempenho diário exatamente igual (comprovei: mesmo padrão de desempenho
dava 102 pontos avaliado como 1 mês, e virava 0 avaliado como 4 meses
seguidos, sem essa correção).

Agora cada contagem é projetada pra uma "taxa equivalente por mês" antes
de aplicar o peso — então o tamanho do período avaliado (1 semana, 1 mês,
ou o histórico inteiro acumulado) não muda mais o resultado, só a TAXA de
ocorrências por dia trabalhado importa. Reproduzi o cenário com dados
sintéticos e confirmei: mesmo padrão de desempenho dá a mesma pontuação
tanto em 1 mês quanto em 4 meses seguidos.

**Teto de segurança (`TETO_FATOR_NORMALIZACAO`, padrão 2x):** sem um
limite, o efeito inverso acontecia com quem trabalhou POUCOS dias no
período — por exemplo, alguém de férias quase o mês inteiro, com só 2 dias
realmente trabalhados. Sem teto, o fator seria 22/2 = 11x, e um punhado de
visitas rápidas nesses 2 dias virava um mês inteiro péssimo (comprovado:
6 visitas rápidas — 1,8 ponto normal — viravam quase 20 pontos perdidos).
Com o teto em 2x, o mesmo caso vira só 3,6 pontos — ainda descontado, mas
proporcional à amostra pequena, sem extrapolar demais.

**Contagem de ausências por ID, não por nome:** a pontuação contava
ausências agrupando pelo NOME do agente — se dois agentes tivessem o
mesmo nome (comum em equipes grandes), as ausências de um contaminavam a
pontuação do outro. Corrigido pra agrupar por ID (que é único de verdade).
Testei com dois agentes chamados "Maria Silva" (IDs diferentes, uma sem
nenhuma falta e outra com falta frequente) e confirmei: pontuações
completamente independentes agora. O mesmo bug existia na lista "Top 15
com mais ausências" do dashboard — corrigido junto (a planilha agora tem
uma coluna "ID Agente" na aba Ausências, só pra isso).

**Decisões antigas que ficaram desatualizadas por uma correção:** se você
já tinha CONFIRMADO uma detecção (férias ou paralisação) antes de alguma
dessas correções, e o padrão que gerou ela não é mais detectado do jeito
certo, o sistema não desfaz a decisão sozinho (pode ser arriscado) — em
vez disso, marca com `"revisao_necessaria": true` e um aviso explicando o
motivo. No `deteccao_editor.html`, esses itens aparecem destacados no topo
da lista, com um botão "🗑️ Remover (não era válido)". A exclusão continua
valendo até você decidir algo — só fica sinalizada pra você conferir.

## Teto de duração por visita — cada visita conta no máximo 20 minutos nos cálculos

Visitas com mais de 20 minutos de duração (`TETO_DURACAO_MEDIA_MIN`, em
`scripts/coletar_evisita.py`) são comuns quando o lançamento é feito pela
web em vez de no momento real da visita — a duração fica artificialmente
longa e distorce médias, estatísticas e gráficos. Caso real que motivou
esse teto: um lançamento do agente Gabriel de **2.888 minutos** numa única
visita, que estava entrando "normalmente" nos cálculos. Pra neutralizar
isso, qualquer visita acima do teto conta como se tivesse durado
exatamente o teto (ex.: 2.888min → considerado como 20min) — visitas de
até 20min entram com o valor real, sem alteração nenhuma.

Isso afeta o **Tempo Médio/Mediana** (Resumo Geral, Por Área e Ponto
Estratégico), as **Horas Trab/Dia**, **Horas Trab/Semana** e o **Custo
Hora Útil**, e qualquer gráfico que use esses números — todos calculados a
partir do valor CAPADO. O lançamento original nunca é alterado nem
excluído: a aba/alerta "Acima de 20min (auditoria)" continua mostrando a
duração REAL de cada visita acima do teto (é justamente a lista pra
auditar um lançamento manipulado, então precisa do valor de verdade, não
do capado). Já "Visitas Suspeitas" é um alerta diferente (sequência de
lançamentos muito próximos no tempo) e não usa esse teto.

Esse teto é recalculado a cada consolidação a partir da duração bruta
guardada no cache (`data/semanas/`) — se o valor de `TETO_DURACAO_MEDIA_MIN`
mudar de novo no futuro, basta rodar a coleta/geração de novo (sem precisar
recoletar nada do e-Visita) que TODO o histórico já cacheado é
recalculado com o teto novo.

## Regras de ausência e férias (atualização de Outubro/2026)

- **Dia inteiro sem lançamento** (os 2 turnos vazios) perde 1,0 ponto a mais, além dos 2 turnos
  (−1,5 cada): o dia custa −4,0. Vale só do método novo (Outubro/2026 em diante); meses antigos e o
  Acumulado antigo não mudam. Constante: `PONTOS_PERDA_DIA_INTEIRO_SEM_LANCAMENTO`.
- **Feriado nacional não conta como ausência** (antes contava como 2 turnos sem lançamento).
- **Agente que já trabalhava antes do mês** é avaliado desde o 1º dia do mês, mesmo que a primeira visita
  dele no mês tenha sido tarde (antes esses dias eram ignorados). Só quem de fato começou depois do
  início do mês é poupado. Equipes sob demanda (`EQUIPES_SEM_DETECCAO_AUTOMATICA`, ex.: Bloqueio) seguem
  a regra antiga e não recebem o desconto extra de dia inteiro.
- **Férias têm no máximo 30 dias corridos.** Na detecção automática só o 1º pedaço (até 30 dias) vira férias;
  o que passar disso entra como **falta** (`status: "falta"`).
- **Agentes sem abono automático:** `data/agentes_sem_abono.json` →
  `{"2951": {"desde": "01/10/2026", "motivo": "texto sem dado de saúde"}}`. A detecção desses agentes vira
  **falta** a partir da data; só vira abono quando a coordenação lançar à mão.

### Turno sem Lançamento × Possível Evento Externo/Interno (regra de 02/11/2026)

- **Padrão:** toda ausência sem lançamento é **Turno sem Lançamento** e desconta pontos (−1,5 por turno).
- **Antes de descontar** o sistema confere o cronograma: chuva, treinamento (`Reunião/Treinamento`), atestado
  (`Ausência justificada`), férias, folga e reunião. Turno coberto por qualquer um deles não desconta.
- **Evento coletivo, classificado sozinho como "Possível Evento Externo ou Interno" (sem desconto):**
  1. `LIMITE_AGENTES_EVENTO_TURNO` (20) ou mais agentes, de qualquer equipe, sem lançamento no mesmo dia e turno;
  2. todos os agentes ativos de uma equipe (2 ou mais) sem lançamento no turno. "Ativo" = não coberto pelo
     cronograma naquele turno (quem está de férias não conta).
  Equipes sob demanda (Bloqueio) ficam fora das duas regras. A aba Ausências mostra a classificação no começo
  da Observação. Se o evento for de fato falta, lance um ajuste em `data/ajustes_ranking.json`.
- **Detecção automática** (`data/deteccoes_pendentes.json`): detecções NOVAS de férias e de paralisação coletiva
  entram como `pendente` e continuam contando como turno sem lançamento até a coordenação confirmar (antes,
  entravam já confirmadas). Decisões antigas não mudam. Voltar ao modo antigo:
  `CONFIRMAR_FERIAS_AUTOMATICAMENTE` / `CONFIRMAR_CHUVA_AUTOMATICAMENTE = True`.
- **Desde quando vale:** `EVENTO_COLETIVO_A_PARTIR_DE = None` — vale para **todos os períodos**, inclusive os meses
  fechados (Maio a Setembro). Para poupar o passado de novo, use `date(2026, 10, 4)` (a semana de 04/10 abre Outubro).
- **Painel de custos:** os dias esperados do custo real já descontam férias, atestado, folga e paralisações.
- Testes: `python3 scripts/test_turno_evento.py`.

