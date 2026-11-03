# Instalação, execução local e Worker

> Migrado do `README.md` em 03/11/2026 sem remover informação. Onde havia texto desatualizado ele foi corrigido
> (lista em `docs/DECISOES.md`, entrada de 03/11/2026). Em caso de dúvida valem `CLAUDE.md` e `docs/REGRAS.md`.
> Passo a passo de configuração (Secrets, Pages, Cloudflare Worker) e como testar na própria máquina.

## Passo a passo — configurar pela primeira vez

### 1. Criar o repositório no GitHub
1. Entre em [github.com/new](https://github.com/new).
2. Dê um nome (o deste projeto é `sentinelaprime`).
3. Deixe **Public** (necessário para o GitHub Pages gratuito) ou **Private**
   se você tiver GitHub Pro/Team/Enterprise.
4. Não marque nenhuma opção de inicialização (README, .gitignore etc.) —
   vamos enviar os arquivos prontos.
5. Clique em **Create repository**.

### 2. Enviar estes arquivos para o repositório
A forma mais simples, sem instalar nada:
1. Na página do repositório recém-criado, clique em **uploading an existing file**.
2. Arraste **todas** as pastas e arquivos deste pacote (mantendo a estrutura
   de pastas: `data/`, `assets/`, `scripts/`, `.github/`, `requirements.txt`).
   O GitHub aceita arrastar pastas inteiras direto do seu computador.
3. Escreva uma mensagem de commit (ex.: "Primeira versão") e clique em
   **Commit changes**.

*(Se preferir usar Git pela linha de comando, veja a seção "Via linha de
comando" mais abaixo.)*

### 3. Cadastrar o CPF e a senha do e-Visita como Secrets

**Nunca coloque CPF/senha direto no código** — o repositório é público, então
qualquer texto commitado fica visível pra qualquer pessoa. O script já lê as
credenciais de variáveis de ambiente; no GitHub isso vem dos **Secrets**:

1. No repositório, vá em **Settings → Secrets and variables → Actions**.
2. Clique em **New repository secret**.
3. Crie um secret chamado `EVISITA_CPF` com o CPF de login.
4. Crie outro chamado `EVISITA_SENHA` com a senha.

> ⚠️ Se essa senha já foi compartilhada em algum chat, e-mail ou documento
> fora de um cofre de senhas, o ideal é trocá-la no e-Visita antes de seguir
> — trate-a como exposta.

### 4. Dar permissão de escrita para o workflow
1. No repositório, vá em **Settings → Actions → General**.
2. Em **Workflow permissions**, marque **Read and write permissions**.
3. Clique em **Save**.

*(Isso é necessário porque o workflow precisa commitar a planilha nova e o
`index.html` atualizado de volta no repositório.)*

### 5. Ativar o GitHub Pages
1. Vá em **Settings → Pages**.
2. Em **Source**, selecione **GitHub Actions** (não "Deploy from a branch").
3. Pronto — não precisa configurar mais nada aqui.

### 6. Rodar a primeira vez
1. Vá na aba **Actions** do repositório.
2. Clique no workflow **Coletar e Atualizar Dashboard** na lista à esquerda.
3. Clique em **Run workflow**. Deixe a opção "Coletar dados novos no e-Visita"
   marcada e confirme.
4. Aguarde — a coleta de todos os agentes pode levar alguns minutos (é a
   mesma coleta que já era feita, só que rodando no GitHub em vez da sua
   máquina). Quando os passos `build` e `deploy` ficarem verdes, vá em
   **Settings → Pages** — o link do seu dashboard vai aparecer no topo, algo
   como: `https://lucsdevpro.github.io/sentinelaprime/` (confirme em Settings → Pages)

## Testar localmente antes de subir (opcional)

Se tiver Python instalado:

```bash
pip install -r requirements.txt

# Coleta (precisa das credenciais como variável de ambiente):
export EVISITA_CPF="seu-cpf"
export EVISITA_SENHA="sua-senha"
python scripts/coletar_evisita.py --saida data

# Geração do HTML:
python scripts/generate_dashboard.py
```

Isso gera o `index.html` na raiz do projeto — só abrir no navegador para
conferir antes de enviar para o GitHub.

## Via linha de comando (alternativa ao passo 2)

```bash
git init
git add .
git commit -m "Primeira versão"
git branch -M main
git remote add origin https://github.com/LucsDevPro/sentinelaprime.git
git push -u origin main
```

---

## Validação pela página (`validar.html`) — para a coordenação, sem mexer no GitHub

Página com botões grandes: **Férias** (✅ está certo / ✏️ ajustar datas / ❌ não é férias),
**Dias sem trabalho** (sugestões: Ausência justificada, Folga, Meia folga ou Falta),
**Novo lançamento** e **Histórico**. Cada pessoa entra com o **próprio PIN**.

Como funciona: `validar.html` → Cloudflare Worker (confere o PIN, grava o histórico) →
GitHub (`repository_dispatch`) → `aplicar-decisao.yml` → commit → site atualizado em poucos minutos.
O Worker é gratuito (plano Free) e guarda os dados sensíveis (lista de sugestões, faltas, histórico);
o repositório público só recebe o rótulo neutro "Ausência justificada" — **nunca digite CID/diagnóstico**.

### Configurar (uma vez, ~20 min)
1. Crie conta grátis em cloudflare.com → **Workers & Pages → Create → Worker**. Cole o conteúdo de `worker/index.js`.
2. **KV**: Workers → KV → crie um namespace e ligue ao Worker com o nome `SENTINELA_KV` (Settings → Bindings).
3. Em **Settings → Variables and Secrets** do Worker, crie:
   - `PINS` = `{"4821":"Maria","7305":"João"}` (PIN → nome de quem usa; um por pessoa)
   - `GH_TOKEN` = token do GitHub (Settings → Developer settings → Fine-grained token, só este repositório, permissão **Contents: Read and write** e **Actions: Read and write**)
   - `GH_REPO` = `LucsDevPro/sentinelaprime`
   - `PUBLISH_TOKEN` = uma senha longa inventada por você
   - `ALLOWED_ORIGIN` = `https://lucsdevpro.github.io`
4. No GitHub: **Settings → Secrets and variables → Actions** → crie `SENTINELA_WORKER_URL` (endereço do Worker, ex.: `https://sentinela.xxx.workers.dev`) e `SENTINELA_PUBLISH_TOKEN` (o mesmo valor de `PUBLISH_TOKEN`).
5. Edite `data/config_worker.json` e coloque `{"url": "https://sentinela.xxx.workers.dev"}`.
6. Rode o workflow *Atualizar dashboard* uma vez (envia as primeiras sugestões) e abra `validar.html`.

Segurança: PIN e token ficam só como segredos do Worker; 8 PINs errados bloqueiam o IP por 15 min;
limite de 40 pedidos/min. Para trocar/remover alguém, edite `PINS`.
Testes: `node worker/test_worker.mjs` e `python scripts/test_decisao.py` (rodam no workflow).
Limites: meia folga tira só o turno sem lançamento e conta 0,5 dia esperado (não perdoa atraso/“dia sem meta” desse turno).

