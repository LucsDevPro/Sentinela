// Sentinela — serviço intermediário (Cloudflare Worker, plano gratuito).
//
// A página validar.html (site público) NÃO tem acesso ao GitHub. Ela fala com
// este Worker, que confere o PIN da coordenação e, se estiver tudo certo,
// dispara o workflow "Aplicar decisão" no GitHub. O token do GitHub e os PINs
// ficam como SEGREDOS do Worker — nunca na página, nunca no repositório.
//
// Configuração (painel da Cloudflare → Workers → este Worker → Settings):
//   Variables/Secrets:
//     PINS            JSON  {"1234":"Maria","5678":"João"}   (PIN → nome da coordenação)
//     GH_TOKEN        token do GitHub (fine-grained, só este repositório,
//                     permissão "Contents: Read and write")
//     GH_REPO         "usuario/nome-do-repositorio"
//     PUBLISH_TOKEN   senha longa; usada pelo workflow para enviar sugestões/resultados
//     ALLOWED_ORIGIN  endereço do site, ex.: https://usuario.github.io
//   KV namespace binding:  SENTINELA_KV
//
// Privacidade (repositório público): a lista de dias sem trabalho e o histórico
// de decisões ficam SÓ aqui (KV), nunca no repositório.

const ACOES = new Set(["ferias_confirmar", "ferias_nao", "ferias_ajustar", "lancar", "remover", "falta", "falta_remover",
  "ajuste", "ajuste_remover", "parada", "parada_remover", "fechar_mes", "reabrir_mes", "contestacao_responder"]);
const ACOES_SEM_AGENTE = new Set(["parada", "parada_remover", "fechar_mes", "reabrir_mes"]);
const LIMITE_AJUSTE = 20;
const LIMITE_PARADA = 30;
const PARADAS = new Set(["Chuva", "Reunião/Treinamento", "Levantamento de Índice", "Instalação de Ovitrampa",
  "Recolha de Ovitrampa", "Recuperação de Casas"]);
// O motivo do ajuste aparece no Extrato PÚBLICO: nada de dado de saúde.
const PROIBIDO_MOTIVO = /atestad|\bcid\b|doen[çc]|diagn[óo]s|m[ée]dic|sa[úu]de|laudo|cirurgi|depress|ansied/i;
const RE_MES = /^[A-Za-zÀ-ÿ]{3,12}\/\d{4}$/;

export function limparMotivo(txt) {
  return String(txt ?? "").replace(/[\u0000-\u001f<>]/g, " ").replace(/\s+/g, " ").trim();
}
const TIPOS = new Set(["ferias", "ausencia_justificada", "folga", "meia_folga", "meia_ausencia_justificada"]);
const TIPOS_COM_TURNO = new Set(["meia_folga", "meia_ausencia_justificada"]);
const TURNOS = new Set(["Manhã", "Tarde"]);
const LIMITE_FERIAS = 30;
const LIMITE_PERIODO = 60;
const LIMITE_REQ_MIN = 40;
const MAX_ERROS_PIN = 8;

function cors(env, req) {
  const origem = req.headers.get("Origin") || "";
  const permitido = (env.ALLOWED_ORIGIN || "").trim();
  return {
    "Access-Control-Allow-Origin": permitido && origem === permitido ? origem : (permitido || "null"),
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,X-PIN,Authorization",
    "Vary": "Origin",
  };
}

function json(env, req, corpo, status = 200) {
  return new Response(JSON.stringify(corpo), {
    status, headers: { "Content-Type": "application/json; charset=utf-8", ...cors(env, req) },
  });
}

function igual(a, b) {                    // comparação em tempo constante
  a = String(a); b = String(b);
  let r = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) r |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  return r === 0;
}

function parseData(txt) {
  const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(String(txt || ""));
  if (!m) return null;
  const d = new Date(Date.UTC(+m[3], +m[2] - 1, +m[1]));
  return d.getUTCFullYear() === +m[3] && d.getUTCMonth() === +m[2] - 1 && d.getUTCDate() === +m[1] ? d : null;
}

function validarNova(corpo) {
  const acao = corpo.acao;
  if (acao === "fechar_mes" || acao === "reabrir_mes") {
    if (!RE_MES.test(String(corpo.mes || ""))) return "Mês inválido.";
    if (acao === "reabrir_mes" && String(corpo.confirmacao || "").trim().toLowerCase() !== String(corpo.mes).toLowerCase())
      return "Para reabrir, digite o nome do mês exatamente.";
    return null;
  }
  if (acao === "ajuste" || acao === "ajuste_remover") {
    const id = Number(corpo.id_agente);
    if (!Number.isInteger(id) || id <= 0) return "Agente inválido.";
    if (!parseData(corpo.data)) return "Data inválida (use dd/mm/aaaa).";
    const pts = Number(corpo.pontos);
    if (!Number.isFinite(pts) || pts === 0 || Math.abs(pts) > LIMITE_AJUSTE) return `Os pontos devem ser diferentes de zero e no máximo ±${LIMITE_AJUSTE}.`;
    const m = limparMotivo(corpo.motivo);
    if (m.length < 3) return "Escreva o motivo (pelo menos 3 letras).";
    if (m.length > 80) return "Motivo muito longo (máximo 80 letras).";
    if (PROIBIDO_MOTIVO.test(m)) return "O motivo aparece publicamente no Extrato: não escreva dados de saúde nem atestado.";
    return null;
  }
  // parada / parada_remover
  const ini = parseData(corpo.inicio), fim = parseData(corpo.fim);
  if (!ini || !fim) return "Datas inválidas (use dd/mm/aaaa).";
  if (fim < ini) return "O último dia não pode ser antes do primeiro dia.";
  if (Math.round((fim - ini) / 86400000) + 1 > LIMITE_PARADA) return `Parada maior que ${LIMITE_PARADA} dias.`;
  if (!PARADAS.has(corpo.motivo)) return "Motivo da parada inválido.";
  if (corpo.alvo === "equipe") {
    const e = String(corpo.equipe || "");
    if (!e || e.length > 60 || /[<>]/.test(e)) return "Escolha a equipe.";
  } else if (corpo.alvo !== "todos") return "Escolha uma equipe ou todas.";
  if (corpo.turno && !TURNOS.has(corpo.turno)) return "Turno inválido.";
  return null;
}

export function validar(corpo) {
  const acao = corpo.acao;
  if (!ACOES.has(acao)) return "Ação desconhecida.";
  if (acao === "contestacao_responder") return validarResposta(corpo);
  if (ACOES_SEM_AGENTE.has(acao) || acao === "ajuste" || acao === "ajuste_remover") return validarNova(corpo);
  const id = Number(corpo.id_agente);
  if (!Number.isInteger(id) || id <= 0) return "Agente inválido.";
  const ini = parseData(corpo.inicio), fim = parseData(corpo.fim);
  if (!ini || !fim) return "Datas inválidas (use dd/mm/aaaa).";
  if (fim < ini) return "O último dia não pode ser antes do primeiro dia.";
  const dias = Math.round((fim - ini) / 86400000) + 1;
  if (dias > 366) return "Período maior que 1 ano.";
  if (acao === "lancar" || acao === "remover") {
    if (!TIPOS.has(corpo.tipo)) return "Tipo de lançamento inválido.";
    if (TIPOS_COM_TURNO.has(corpo.tipo) && !TURNOS.has(corpo.turno)) return "Escolha o turno (Manhã ou Tarde).";
    if (corpo.tipo === "ferias" && acao === "lancar" && dias > LIMITE_FERIAS)
      return "Férias têm no máximo 30 dias corridos. Lance até 30 dias; o que passar disso conta como falta.";
    if (corpo.tipo !== "ferias" && dias > LIMITE_PERIODO) return `Período maior que ${LIMITE_PERIODO} dias.`;
  }
  if (acao === "ferias_ajustar" && dias > LIMITE_FERIAS)
    return "Férias têm no máximo 30 dias corridos. Lance até 30 dias; o que passar disso conta como falta.";
  return null;
}

async function kvGet(env, chave, padrao) {
  const v = await env.SENTINELA_KV.get(chave, "json");
  return v === null || v === undefined ? padrao : v;
}

async function limitar(env, ip) {
  const chave = `rl:${ip}:${Math.floor(Date.now() / 60000)}`;
  const n = Number((await env.SENTINELA_KV.get(chave)) || 0) + 1;
  await env.SENTINELA_KV.put(chave, String(n), { expirationTtl: 120 });
  return n <= LIMITE_REQ_MIN;
}

async function autenticar(env, req, pinInformado) {
  const ip = req.headers.get("CF-Connecting-IP") || "?";
  const chaveErro = `pf:${ip}`;
  const erros = Number((await env.SENTINELA_KV.get(chaveErro)) || 0);
  if (erros >= MAX_ERROS_PIN) return { bloqueado: true };
  let pins = {};
  try { pins = JSON.parse(env.PINS || "{}"); } catch { /* sem PINs válidos */ }
  for (const [pin, nome] of Object.entries(pins)) {
    if (pinInformado && igual(pin, pinInformado)) {
      await env.SENTINELA_KV.delete(chaveErro);
      return { nome: String(nome) };
    }
  }
  await env.SENTINELA_KV.put(chaveErro, String(erros + 1), { expirationTtl: 900 });
  return { nome: null };
}

function cobre(lista, id, dia) {          // dia = "dd/mm/aaaa"; lista = [{id_agente,inicio,fim}]
  const d = parseData(dia);
  return lista.some(x => x.id_agente === id && parseData(x.inicio) <= d && d <= parseData(x.fim));
}

async function registrarLog(env, entrada) {
  const log = await kvGet(env, "log", []);
  log.unshift(entrada);
  await env.SENTINELA_KV.put("log", JSON.stringify(log.slice(0, 300)));
}

function resumo(c) {
  if (c.acao === "ajuste" || c.acao === "ajuste_remover")
    return `${c.acao}: agente ${c.id_agente}, ${c.data}, ${c.pontos} pts — ${limparMotivo(c.motivo)}`;
  if (c.acao === "parada" || c.acao === "parada_remover")
    return `${c.acao}: ${c.motivo}, ${c.alvo === "equipe" ? c.equipe : "todas as equipes"}, ${c.inicio} a ${c.fim}${c.turno ? " (" + c.turno + ")" : ""}`;
  if (c.acao === "fechar_mes" || c.acao === "reabrir_mes") return `${c.acao}: ${c.mes}`;
  if (c.acao === "contestacao_responder") return `contestação ${c.codigo}: ${c.decisao}`;
  const t = c.tipo ? ` — ${c.tipo}${c.turno ? " (" + c.turno + ")" : ""}` : "";
  return `${c.acao}${t}: agente ${c.id_agente}, ${c.inicio} a ${c.fim}`;
}

// ---------- contestações (públicas, sem PIN) ----------
const ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
const LIM_CONTEST_IP_HORA = 4;
const LIM_CONTEST_AGENTE_DIA = 3;
const MAX_CONTESTACOES = 400;
const MAX_ABERTAS = 150;

function novoCodigo() {
  const b = crypto.getRandomValues(new Uint8Array(8));
  return Array.from(b, x => ALFABETO[x % ALFABETO.length]).join("");
}

export function validarContestacao(c) {
  if (c.site || c.hp) return "spam";                         // campo-isca (honeypot): gente de verdade não preenche
  const id = Number(c.id_agente);
  if (!Number.isInteger(id) || id <= 0 || id > 999999) return "Agente inválido.";
  const criterio = limparMotivo(c.criterio);
  if (criterio.length < 3 || criterio.length > 80) return "Escolha o critério contestado.";
  const texto = limparMotivo(c.texto);
  if (texto.length < 10) return "Explique em uma frase (pelo menos 10 letras).";
  if (texto.length > 240) return "Texto muito longo (máximo 240 letras).";
  if (/https?:|www\./i.test(texto)) return "Não coloque links no texto.";
  if (!RE_MES.test(String(c.mes || ""))) return "Mês inválido.";
  return null;
}

export function validarResposta(c) {
  if (!/^[A-Z0-9]{8}$/.test(String(c.codigo || ""))) return "Código inválido.";
  if (c.decisao !== "aceitar" && c.decisao !== "recusar") return "Escolha aceitar ou recusar.";
  const r = limparMotivo(c.resposta);
  if (r.length < 3) return "Escreva uma resposta curta.";
  if (r.length > 240) return "Resposta muito longa (máximo 240 letras).";
  if (c.decisao === "aceitar" && c.pontos !== undefined && c.pontos !== null && c.pontos !== "") {
    const e = validarNova({ acao: "ajuste", id_agente: 1, data: c.data, pontos: c.pontos, motivo: c.motivo });
    if (e) return e;
  }
  return null;
}

async function limiteSimples(env, chave, max, ttl) {
  const n = Number((await env.SENTINELA_KV.get(chave)) || 0) + 1;
  await env.SENTINELA_KV.put(chave, String(n), { expirationTtl: ttl });
  return n <= max;
}

async function sugestoesAbertas(env) {
  const sug = await kvGet(env, "sugestoes", { gerado_em: "", itens: [] });
  const ocultar = [...await kvGet(env, "faltas", []), ...await kvGet(env, "classificadas", [])];
  const itens = [];
  for (const it of sug.itens) {
    const dias = it.dias.filter(d => !cobre(ocultar, it.id_agente, d.dia));
    if (!dias.length) continue;
    itens.push({ ...it, dias, inicio: dias[0].dia, fim: dias[dias.length - 1].dia });
  }
  return { gerado_em: sug.gerado_em, itens };
}

// Dias ainda sem classificação dentro de [ini, fim] (datas dd/mm/aaaa)
export function contarDiasPendentes(itens, ini, fim) {
  const a = parseData(ini), b = parseData(fim);
  if (!a || !b) return 0;
  let n = 0;
  for (const it of itens) for (const d of it.dias) { const x = parseData(d.dia); if (x && x >= a && x <= b) n++; }
  return n;
}

export default {
  async fetch(req, env) {
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(env, req) });
    const url = new URL(req.url);
    const ip = req.headers.get("CF-Connecting-IP") || "?";
    try {
      if (url.pathname === "/ping") return json(env, req, { ok: true });

      // --- rotas do workflow (token de publicação) ---
      if (url.pathname === "/publicar-sugestoes" || url.pathname === "/resultado") {
        const auth = req.headers.get("Authorization") || "";
        if (!env.PUBLISH_TOKEN || !igual(auth, `Bearer ${env.PUBLISH_TOKEN}`)) return json(env, req, { erro: "não autorizado" }, 401);
        const corpo = await req.json();
        if (url.pathname === "/publicar-sugestoes") {
          if (!Array.isArray(corpo.itens)) return json(env, req, { erro: "formato inválido" }, 400);
          await env.SENTINELA_KV.put("sugestoes", JSON.stringify({ gerado_em: corpo.gerado_em || "", itens: corpo.itens }));
          if (corpo.checklist && typeof corpo.checklist === "object")
            await env.SENTINELA_KV.put("checklist", JSON.stringify(corpo.checklist));
          // classificações antigas já foram aplicadas pelo workflow: limpa as com mais de 3 dias
          const corte = Date.now() - 3 * 86400000;
          const cls = (await kvGet(env, "classificadas", [])).filter(x => x.ts > corte);
          await env.SENTINELA_KV.put("classificadas", JSON.stringify(cls));
          return json(env, req, { ok: true, itens: corpo.itens.length });
        }
        const log = await kvGet(env, "log", []);
        const alvo = log.find(l => l.id === corpo.decisao_id);
        if (alvo) { alvo.status = corpo.ok ? "ok" : "erro"; alvo.msg = String(corpo.msg || "").slice(0, 300); }
        await env.SENTINELA_KV.put("log", JSON.stringify(log));
        return json(env, req, { ok: true });
      }

      // --- rotas da coordenação (PIN) ---
      if (!(await limitar(env, ip))) return json(env, req, { erro: "Muitas tentativas. Aguarde 1 minuto." }, 429);

      // --- contestação pública (sem PIN, com freio) ---
      if (url.pathname === "/contestar" && req.method === "POST") {
        const c = await req.json().catch(() => ({}));
        const erro = validarContestacao(c);
        if (erro === "spam") return json(env, req, { ok: true, codigo: novoCodigo() });   // finge que deu certo
        if (erro) return json(env, req, { erro }, 400);
        const hora = Math.floor(Date.now() / 3600000), dia = Math.floor(Date.now() / 86400000);
        if (!(await limiteSimples(env, `ct:ip:${ip}:${hora}`, LIM_CONTEST_IP_HORA, 7200)))
          return json(env, req, { erro: "Muitos pedidos seus em pouco tempo. Tente de novo mais tarde." }, 429);
        if (!(await limiteSimples(env, `ct:ag:${Number(c.id_agente)}:${dia}`, LIM_CONTEST_AGENTE_DIA, 172800)))
          return json(env, req, { erro: "Esse agente já fez o máximo de pedidos de hoje." }, 429);
        const lista = await kvGet(env, "contestacoes", []);
        if (lista.filter(x => x.status === "aberta").length >= MAX_ABERTAS)
          return json(env, req, { erro: "A fila de pedidos está cheia. Fale com a coordenação." }, 429);
        const codigo = novoCodigo();
        lista.unshift({ codigo, ts: Date.now(), quando: new Date().toISOString(), id_agente: Number(c.id_agente),
          criterio: limparMotivo(c.criterio), texto: limparMotivo(c.texto), mes: String(c.mes), status: "aberta" });
        await env.SENTINELA_KV.put("contestacoes", JSON.stringify(lista.slice(0, MAX_CONTESTACOES)));
        return json(env, req, { ok: true, codigo });
      }
      if (url.pathname === "/contestacao") {
        const cod = String(url.searchParams.get("codigo") || "").toUpperCase();
        if (!/^[A-Z0-9]{8}$/.test(cod)) return json(env, req, { erro: "Código inválido." }, 400);
        if (!(await limiteSimples(env, `ct:q:${ip}:${Math.floor(Date.now() / 3600000)}`, 60, 7200)))
          return json(env, req, { erro: "Muitas consultas. Tente mais tarde." }, 429);
        const c = (await kvGet(env, "contestacoes", [])).find(x => x.codigo === cod);
        if (!c) return json(env, req, { erro: "Não encontrei esse código." }, 404);
        return json(env, req, { codigo: c.codigo, status: c.status, criterio: c.criterio, mes: c.mes,
          decisao: c.decisao || null, resposta: c.resposta || null, respondida_em: c.respondida_em || null });
      }

      if (url.pathname === "/sugestoes" || url.pathname === "/log" || url.pathname === "/checklist" || url.pathname === "/contestacoes") {
        const au = await autenticar(env, req, req.headers.get("X-PIN") || "");
        if (au.bloqueado) return json(env, req, { erro: "Muitos PINs errados. Tente de novo em 15 minutos." }, 429);
        if (!au.nome) return json(env, req, { erro: "PIN incorreto." }, 401);
        if (url.pathname === "/log") return json(env, req, { quem: au.nome, log: await kvGet(env, "log", []) });
        if (url.pathname === "/contestacoes") return json(env, req, { quem: au.nome, itens: await kvGet(env, "contestacoes", []) });
        if (url.pathname === "/checklist") {
          const ck = await kvGet(env, "checklist", null);
          if (!ck) return json(env, req, { quem: au.nome, vazio: true });
          const sug = await sugestoesAbertas(env);
          const [ini, fim] = String(ck.periodo || " a ").split(" a ");
          const n = contarDiasPendentes(sug.itens, ini, fim);
          const itens = (ck.itens || []).map(i => i.id === "dias"
            ? { ...i, ok: n === 0, texto: n === 0 ? "Nenhum dia sem trabalho esperando classificação." : `${n} dia(s) sem trabalho ainda esperam classificação.` }
            : i);
          return json(env, req, { quem: au.nome, ...ck, itens, pronto: itens.every(i => i.ok === true) });
        }
        const sug = await sugestoesAbertas(env);
        return json(env, req, { quem: au.nome, gerado_em: sug.gerado_em, itens: sug.itens });
      }

      if (url.pathname === "/acao" && req.method === "POST") {
        const corpo = await req.json();
        const au = await autenticar(env, req, String(corpo.pin || ""));
        if (au.bloqueado) return json(env, req, { erro: "Muitos PINs errados. Tente de novo em 15 minutos." }, 429);
        if (!au.nome) return json(env, req, { erro: "PIN incorreto." }, 401);
        const erro = validar(corpo);
        if (erro) return json(env, req, { erro }, 400);
        const id = crypto.randomUUID();
        const base = { id, ts: Date.now(), quando: new Date().toISOString(), quem: au.nome, resumo: resumo(corpo),
          dados: { acao: corpo.acao, tipo: corpo.tipo || null, turno: corpo.turno || null,
                   id_agente: Number(corpo.id_agente) || null, inicio: corpo.inicio || corpo.data || null, fim: corpo.fim || null } };

        let decisaoNova = null;
        if (corpo.acao === "contestacao_responder") {
          const lista = await kvGet(env, "contestacoes", []);
          const c = lista.find(x => x.codigo === corpo.codigo);
          if (!c) return json(env, req, { erro: "Pedido não encontrado." }, 404);
          if (c.status !== "aberta") return json(env, req, { erro: "Esse pedido já foi respondido." }, 409);
          if (corpo.decisao === "aceitar" && corpo.pontos !== undefined && corpo.pontos !== null && corpo.pontos !== "") {
            decisaoNova = { acao: "ajuste", quem: au.nome, id_agente: c.id_agente, data: corpo.data,
              pontos: Number(corpo.pontos), motivo: limparMotivo(corpo.motivo) };
          }
          c.status = corpo.decisao === "aceitar" ? "aceita" : "recusada";
          c.decisao = corpo.decisao; c.resposta = limparMotivo(corpo.resposta);
          c.respondida_em = new Date().toISOString().slice(0, 10); c.respondida_por = au.nome;
          await env.SENTINELA_KV.put("contestacoes", JSON.stringify(lista));
          if (!decisaoNova) {
            await registrarLog(env, { ...base, status: "ok", msg: "Resposta registrada no Worker" });
            return json(env, req, { ok: true, id });
          }
        } else if (corpo.acao === "fechar_mes") {
          const ck = await kvGet(env, "checklist", null);
          if (!ck || ck.mes !== corpo.mes) return json(env, req, { erro: "A lista de conferência deste mês ainda não foi gerada. Rode a atualização e tente de novo." }, 409);
          const [ini, fim] = String(ck.periodo || " a ").split(" a ");
          const n = contarDiasPendentes((await sugestoesAbertas(env)).itens, ini, fim);
          if (n > 0) return json(env, req, { erro: `Ainda há ${n} dia(s) sem classificação neste mês.` }, 409);
        }

        if (corpo.acao === "falta" || corpo.acao === "falta_remover") {   // só no Worker: nunca vai ao repositório
          let faltas = await kvGet(env, "faltas", []);
          const reg = { id_agente: Number(corpo.id_agente), inicio: corpo.inicio, fim: corpo.fim };
          if (corpo.acao === "falta") faltas.push({ ...reg, quem: au.nome, ts: Date.now() });
          else faltas = faltas.filter(f => !(f.id_agente === reg.id_agente && f.inicio === reg.inicio && f.fim === reg.fim));
          await env.SENTINELA_KV.put("faltas", JSON.stringify(faltas));
          await registrarLog(env, { ...base, status: "ok", msg: "Registrado no Worker" });
          return json(env, req, { ok: true, id });
        }

        if (corpo.acao === "lancar" && corpo.tipo !== "ferias") {         // some da lista de sugestões na hora
          const cls = await kvGet(env, "classificadas", []);
          cls.push({ id_agente: Number(corpo.id_agente), inicio: corpo.inicio, fim: corpo.fim, ts: Date.now() });
          await env.SENTINELA_KV.put("classificadas", JSON.stringify(cls));
        }
        let decisao = {
          acao: corpo.acao, quem: au.nome, id_agente: Number(corpo.id_agente), inicio: corpo.inicio, fim: corpo.fim,
          ...(corpo.tipo ? { tipo: corpo.tipo } : {}), ...(corpo.turno ? { turno: corpo.turno } : {}),
        };
        if (decisaoNova) decisao = decisaoNova;
        else if (corpo.acao === "ajuste" || corpo.acao === "ajuste_remover")
          decisao = { acao: corpo.acao, quem: au.nome, id_agente: Number(corpo.id_agente), data: corpo.data,
            pontos: Number(corpo.pontos), motivo: limparMotivo(corpo.motivo) };
        else if (corpo.acao === "parada" || corpo.acao === "parada_remover")
          decisao = { acao: corpo.acao, quem: au.nome, alvo: corpo.alvo, ...(corpo.alvo === "equipe" ? { equipe: corpo.equipe } : {}),
            motivo: corpo.motivo, inicio: corpo.inicio, fim: corpo.fim, ...(corpo.turno ? { turno: corpo.turno } : {}) };
        else if (corpo.acao === "fechar_mes" || corpo.acao === "reabrir_mes")
          decisao = { acao: corpo.acao, quem: au.nome, mes: corpo.mes, ...(corpo.confirmacao ? { confirmacao: corpo.confirmacao } : {}) };
        const r = await fetch(`https://api.github.com/repos/${env.GH_REPO}/dispatches`, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${env.GH_TOKEN}`, "Accept": "application/vnd.github+json",
            "User-Agent": "sentinela-worker", "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json",
          },
          body: JSON.stringify({ event_type: "decisao", client_payload: { decisao: decisao, decisao_id: id } }),
          signal: AbortSignal.timeout(10000),   // GitHub lento não pode prender o pedido
        });
        if (!r.ok) {
          await registrarLog(env, { ...base, status: "erro", msg: `GitHub respondeu ${r.status}` });
          return json(env, req, { erro: "Não consegui avisar o GitHub. Tente de novo em instantes." }, 502);
        }
        await registrarLog(env, { ...base, status: "enviado", msg: "Aguardando o GitHub aplicar" });
        return json(env, req, { ok: true, id });
      }
      return json(env, req, { erro: "não encontrado" }, 404);
    } catch (e) {
      return json(env, req, { erro: "Erro interno." }, 500);
    }
  },
};
