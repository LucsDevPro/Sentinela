// Testes do Worker sem Cloudflare: KV falso (Map) e fetch do GitHub falso.
// Uso: node worker/test_worker.mjs
import worker, { validar } from "./index.js";

let falhas = 0;
const chk = (nome, cond, det = "") => { console.log(`${cond ? "[OK  ]" : "[FALHOU]"} ${nome}${!cond && det ? " — " + det : ""}`); if (!cond) falhas++; };

function novoKV() {
  const m = new Map();
  return { m,
    async get(k, tipo) { const v = m.get(k); if (v === undefined) return null; return tipo === "json" ? JSON.parse(v) : v; },
    async put(k, v) { m.set(k, v); }, async delete(k) { m.delete(k); } };
}
let chamadasGH = [], respostaGH = { ok: true, status: 204 };
globalThis.fetch = async (url, opts) => { chamadasGH.push({ url, opts }); return respostaGH; };

const ORIGEM = "https://sentinela.github.io";
const mkEnv = () => ({ PINS: JSON.stringify({ "1234": "Maria", "5678": "João" }), GH_TOKEN: "ghp_segredo", GH_REPO: "u/r",
  PUBLISH_TOKEN: "pub-123", ALLOWED_ORIGIN: ORIGEM, SENTINELA_KV: novoKV() });
const req = (path, { method = "GET", body, headers = {} } = {}) =>
  new Request("https://w.example" + path, { method, headers: { "Content-Type": "application/json", Origin: ORIGEM, "CF-Connecting-IP": "1.1.1.1", ...headers },
    body: body ? JSON.stringify(body) : undefined });
const call = async (env, path, opts) => { const r = await worker.fetch(req(path, opts), env); return { status: r.status, corpo: await r.json().catch(() => null), headers: r.headers }; };
const acao = (extra) => ({ pin: "1234", acao: "lancar", tipo: "folga", id_agente: 85, inicio: "10/10/2026", fim: "10/10/2026", ...extra });

// ---- validar() direto
chk("validar: tudo certo", validar(acao()) === null);
chk("validar: data inexistente", validar(acao({ inicio: "31/02/2026" })) !== null);
chk("validar: fim antes do início", validar(acao({ inicio: "10/10/2026", fim: "09/10/2026" })) !== null);
chk("validar: meia folga exige turno", validar(acao({ tipo: "meia_folga" })) !== null);
chk("validar: meia folga com turno ok", validar(acao({ tipo: "meia_folga", turno: "Manhã" })) === null);
chk("validar: férias > 30 dias recusadas", validar(acao({ tipo: "ferias", inicio: "01/09/2026", fim: "10/10/2026" })) !== null);
chk("validar: ação desconhecida", validar(acao({ acao: "apagar_tudo" })) !== null);
chk("validar: agente inválido", validar(acao({ id_agente: "x" })) !== null);

// ---- fluxo
let env = mkEnv();
let r = await call(env, "/ping");
chk("ping responde sem PIN", r.status === 200 && r.corpo.ok);
chk("CORS só para o site configurado", r.headers.get("Access-Control-Allow-Origin") === ORIGEM);

r = await call(env, "/acao", { method: "POST", body: acao({ pin: "0000" }) });
chk("PIN errado: 401 e nada enviado ao GitHub", r.status === 401 && chamadasGH.length === 0);

r = await call(env, "/acao", { method: "POST", body: acao() });
chk("lançamento válido: 200 e enviado ao GitHub", r.status === 200 && chamadasGH.length === 1, JSON.stringify(r));
const gh = chamadasGH[0];
const payload = JSON.parse(gh.opts.body);
chk("dispatch vai para o repositório certo com o token do segredo", gh.url === "https://api.github.com/repos/u/r/dispatches" && gh.opts.headers.Authorization === "Bearer ghp_segredo");
chk("payload leva o nome da coordenação, não o PIN", payload.client_payload.decisao.quem === "Maria" && !gh.opts.body.includes("1234"));
chk("event_type = decisao", payload.event_type === "decisao");

chamadasGH = [];
r = await call(env, "/acao", { method: "POST", body: acao({ tipo: "ferias", inicio: "01/01/2026", fim: "31/03/2026" }) });
chk("férias > 30 dias: 400 e nada enviado", r.status === 400 && chamadasGH.length === 0);

respostaGH = { ok: false, status: 401 };
r = await call(env, "/acao", { method: "POST", body: acao({ inicio: "11/10/2026", fim: "11/10/2026" }) });
chk("GitHub recusou: 502 e log com erro", r.status === 502 && JSON.parse(env.SENTINELA_KV.m.get("log"))[0].status === "erro");
respostaGH = { ok: true, status: 204 };

// ---- sugestões
const sugestoes = { gerado_em: "29/10/2026 05:00", itens: [
  { id_agente: 85, nome: "Fulano", equipe: "Equipe 1", inicio: "06/10/2026", fim: "08/10/2026", sugestao: "x",
    dias: [{ dia: "06/10/2026", turnos: ["Manhã", "Tarde"] }, { dia: "07/10/2026", turnos: ["Manhã", "Tarde"] }, { dia: "08/10/2026", turnos: ["Tarde"] }] },
  { id_agente: 86, nome: "Ciclana", equipe: "Equipe 2", inicio: "13/10/2026", fim: "13/10/2026", sugestao: "y",
    dias: [{ dia: "13/10/2026", turnos: ["Manhã"] }] }] };
env = mkEnv(); chamadasGH = [];
r = await call(env, "/publicar-sugestoes", { method: "POST", body: sugestoes });
chk("publicar sem token: 401", r.status === 401);
r = await call(env, "/publicar-sugestoes", { method: "POST", body: sugestoes, headers: { Authorization: "Bearer pub-123" } });
chk("publicar com token: ok", r.status === 200 && r.corpo.itens === 2);
r = await call(env, "/sugestoes");
chk("sugestões sem PIN: 401", r.status === 401);
r = await call(env, "/sugestoes", { headers: { "X-PIN": "1234" } });
chk("sugestões com PIN: lista completa", r.status === 200 && r.corpo.itens.length === 2 && r.corpo.quem === "Maria");

r = await call(env, "/acao", { method: "POST", body: acao({ acao: "falta", inicio: "06/10/2026", fim: "06/10/2026" }) });
chk("falta: não vai ao GitHub (fica só no Worker)", r.status === 200 && chamadasGH.length === 0);
r = await call(env, "/sugestoes", { headers: { "X-PIN": "1234" } });
const it85 = r.corpo.itens.find(i => i.id_agente === 85);
chk("falta confirmada some da lista e o período encolhe", it85.dias.length === 2 && it85.inicio === "07/10/2026", JSON.stringify(it85));

r = await call(env, "/acao", { method: "POST", body: acao({ id_agente: 86, inicio: "13/10/2026", fim: "13/10/2026", tipo: "meia_folga", turno: "Manhã" }) });
r = await call(env, "/sugestoes", { headers: { "X-PIN": "1234" } });
chk("lançamento classificado some da lista na hora", !r.corpo.itens.some(i => i.id_agente === 86));

r = await call(env, "/acao", { method: "POST", body: acao({ acao: "falta_remover", inicio: "06/10/2026", fim: "06/10/2026" }) });
r = await call(env, "/sugestoes", { headers: { "X-PIN": "1234" } });
chk("desfazer falta traz o dia de volta", r.corpo.itens.find(i => i.id_agente === 85).dias.length === 3);

// ---- log e resultado
r = await call(env, "/log", { headers: { "X-PIN": "5678" } });
chk("log só com PIN e mostra quem decidiu", r.status === 200 && r.corpo.quem === "João" && r.corpo.log.some(l => l.quem === "Maria"));
const idLog = r.corpo.log.find(l => l.status === "enviado").id;
r = await call(env, "/resultado", { method: "POST", body: { decisao_id: idLog, ok: true, msg: "✅ aplicado" }, headers: { Authorization: "Bearer pub-123" } });
r = await call(env, "/log", { headers: { "X-PIN": "1234" } });
chk("workflow informa o resultado e o log vira ok", r.corpo.log.find(l => l.id === idLog).status === "ok");

// ---- força bruta e limite
env = mkEnv(); let ultimo;
for (let i = 0; i < 9; i++) ultimo = await call(env, "/acao", { method: "POST", body: acao({ pin: "9999" }), headers: { "CF-Connecting-IP": "2.2.2.2" } });
chk("muitos PINs errados bloqueiam o IP (429)", ultimo.status === 429);
r = await call(env, "/acao", { method: "POST", body: acao(), headers: { "CF-Connecting-IP": "2.2.2.2" } });
chk("IP bloqueado não entra nem com PIN certo", r.status === 429);
env = mkEnv(); let c429 = 0;
for (let i = 0; i < 45; i++) { const x = await call(env, "/sugestoes", { headers: { "X-PIN": "1234", "CF-Connecting-IP": "3.3.3.3" } }); if (x.status === 429) c429++; }
chk("limite de requisições por minuto", c429 >= 4, String(c429));

// ================= Sessões 8 e 9 =================
const aj = (extra) => ({ pin: "1234", acao: "ajuste", id_agente: 85, data: "15/10/2026", pontos: 2, motivo: "Instabilidade do e-Visita", ...extra });
chk("ajuste: válido", validar(aj()) === null);
chk("ajuste: acima do limite", validar(aj({ pontos: 25 })) !== null);
chk("ajuste: zero recusado", validar(aj({ pontos: 0 })) !== null);
chk("ajuste: motivo curto", validar(aj({ motivo: "ab" })) !== null);
chk("ajuste: motivo com dado de saúde", validar(aj({ motivo: "atestado médico" })) !== null);
chk("ajuste: motivo longo", validar(aj({ motivo: "x".repeat(81) })) !== null);
chk("ajuste: reverter usa os mesmos campos", validar(aj({ acao: "ajuste_remover" })) === null);
const pa = (extra) => ({ pin: "1234", acao: "parada", alvo: "equipe", equipe: "Equipe 1", motivo: "Chuva", inicio: "20/10/2026", fim: "20/10/2026", ...extra });
chk("parada: por equipe", validar(pa()) === null);
chk("parada: todos com turno", validar(pa({ alvo: "todos", turno: "Tarde" })) === null);
chk("parada: motivo inválido", validar(pa({ motivo: "Churrasco" })) !== null);
chk("parada: equipe vazia", validar(pa({ equipe: "" })) !== null);
chk("parada: turno inválido", validar(pa({ turno: "Noite" })) !== null);
chk("parada: > 30 dias", validar(pa({ fim: "30/11/2026" })) !== null);
chk("fechar_mes: ok", validar({ acao: "fechar_mes", mes: "Outubro/2026" }) === null);
chk("reabrir_mes exige digitar o nome", validar({ acao: "reabrir_mes", mes: "Outubro/2026", confirmacao: "" }) !== null);
chk("reabrir_mes com nome certo", validar({ acao: "reabrir_mes", mes: "Outubro/2026", confirmacao: "outubro/2026" }) === null);

env = mkEnv(); chamadasGH = [];
r = await call(env, "/acao", { method: "POST", body: aj() });
chk("ajuste vai ao GitHub com os campos certos", r.status === 200 && JSON.parse(chamadasGH.at(-1).opts.body).client_payload.decisao.pontos === 2);
r = await call(env, "/acao", { method: "POST", body: aj({ pontos: 99 }) });
chk("ajuste fora do limite não chega ao GitHub", r.status === 400);
chamadasGH = [];
r = await call(env, "/acao", { method: "POST", body: pa({ alvo: "todos" }) });
chk("parada coletiva despachada sem agente", r.status === 200 && JSON.parse(chamadasGH.at(-1).opts.body).client_payload.decisao.alvo === "todos");

// fechar mês: bloqueia com dia pendente / sem checklist, libera com tudo certo
r = await call(env, "/acao", { method: "POST", body: { pin: "1234", acao: "fechar_mes", mes: "Outubro/2026" } });
chk("fechar mês sem checklist publicado → 409", r.status === 409);
await call(env, "/publicar-sugestoes", { method: "POST", headers: { Authorization: "Bearer pub-123" }, body: {
  gerado_em: "x", itens: [{ id_agente: 85, nome: "A", dias: [{ dia: "20/10/2026" }] }],
  checklist: { mes: "Outubro/2026", periodo: "28/09/2026 a 30/10/2026", itens: [{ id: "semanas", ok: true, texto: "ok" }, { id: "dias", ok: null, texto: "x" }] } } });
r = await call(env, "/checklist", { headers: { "X-PIN": "1234" } });
chk("checklist soma o dia pendente", r.corpo.itens.find(i => i.id === "dias").ok === false && r.corpo.pronto === false);
r = await call(env, "/acao", { method: "POST", body: { pin: "1234", acao: "fechar_mes", mes: "Outubro/2026" } });
chk("fechar mês com dia pendente → 409", r.status === 409);
await call(env, "/acao", { method: "POST", body: { pin: "1234", acao: "falta", id_agente: 85, inicio: "20/10/2026", fim: "20/10/2026" } });
r = await call(env, "/checklist", { headers: { "X-PIN": "1234" } });
chk("depois de classificar, checklist fica pronto", r.corpo.pronto === true);
chamadasGH = [];
r = await call(env, "/acao", { method: "POST", body: { pin: "1234", acao: "fechar_mes", mes: "Outubro/2026" } });
chk("fechar mês completo é despachado", r.status === 200 && JSON.parse(chamadasGH.at(-1).opts.body).client_payload.decisao.acao === "fechar_mes");
r = await call(env, "/checklist");
chk("checklist exige PIN", r.status === 401);

// contestações
const ct = (extra) => ({ id_agente: 85, criterio: "Turno sem lançamento", texto: "Estava em reunião no turno da manhã.", mes: "Outubro/2026", ...extra });
env = mkEnv();
r = await call(env, "/contestar", { method: "POST", body: ct() });
chk("contestação válida gera código", r.status === 200 && /^[A-Z0-9]{8}$/.test(r.corpo.codigo));
const cod = r.corpo.codigo;
r = await call(env, "/contestar", { method: "POST", body: ct({ texto: "curto" }) });
chk("contestação com texto curto é recusada", r.status === 400);
r = await call(env, "/contestar", { method: "POST", body: ct({ texto: "veja http://spam.com agora mesmo" }) });
chk("contestação com link é recusada", r.status === 400);
r = await call(env, "/contestar", { method: "POST", body: ct({ hp: "robo" }) });
chk("honeypot: finge sucesso mas não grava", r.status === 200 && (JSON.parse(env.SENTINELA_KV.m.get("contestacoes")).length === 1));
let q = 0, c429b = 0;
for (let i = 0; i < 6; i++) { const x = await call(env, "/contestar", { method: "POST", body: ct({ id_agente: 90 + i }) }); if (x.status === 429) c429b++; }
chk("spam: limite por IP/hora (429)", c429b >= 2, String(c429b));
r = await call(env, `/contestacao?codigo=${cod}`);
chk("agente consulta pelo código (sem PIN, sem texto pessoal)", r.status === 200 && r.corpo.status === "aberta" && !("texto" in r.corpo));
r = await call(env, "/contestacoes");
chk("lista de contestações exige PIN", r.status === 401);
r = await call(env, "/contestacoes", { headers: { "X-PIN": "1234" } });
chk("coordenação vê as contestações", r.status === 200 && r.corpo.itens.length >= 1);
chamadasGH = [];
r = await call(env, "/acao", { method: "POST", body: { pin: "1234", acao: "contestacao_responder", codigo: cod, decisao: "recusar", resposta: "Reunião não consta na agenda." } });
chk("recusar registra resposta sem acionar o GitHub", r.status === 200 && chamadasGH.length === 0);
r = await call(env, `/contestacao?codigo=${cod}`);
chk("agente vê a resposta curta", r.corpo.status === "recusada" && r.corpo.resposta.includes("agenda"));
r = await call(env, "/acao", { method: "POST", body: { pin: "1234", acao: "contestacao_responder", codigo: cod, decisao: "aceitar", resposta: "ok, tudo certo" } });
chk("não responde duas vezes", r.status === 409);
r = await call(env, "/contestar", { method: "POST", body: ct({ id_agente: 77 }), headers: { "CF-Connecting-IP": "9.9.9.9" } });
const cod2 = r.corpo.codigo; chamadasGH = [];
r = await call(env, "/acao", { method: "POST", body: { pin: "1234", acao: "contestacao_responder", codigo: cod2, decisao: "aceitar", resposta: "Procede, ajustado.", pontos: 1.5, data: "10/10/2026", motivo: "Contestação aceita" } });
const dec2 = chamadasGH.length ? JSON.parse(chamadasGH.at(-1).opts.body).client_payload.decisao : {};
chk("aceitar com pontos cria o ajuste do agente certo", r.status === 200 && dec2.acao === "ajuste" && dec2.id_agente === 77 && dec2.pontos === 1.5);

console.log(falhas ? `\n❌ ${falhas} falha(s)` : "\n✅ Todos os testes do Worker passaram.");
process.exit(falhas ? 1 : 0);
