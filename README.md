# Zara Stock Monitor → Discord (via GitHub Actions)

Monitoriza o stock de vários produtos da Zara e envia um alerta para o Discord quando o stock muda — sem precisares de nenhum computador ligado. Quem corre o script periodicamente é o GitHub, de graça.

## Estrutura do projeto

```
zara-stock-monitor-github-actions/
├── zara_stock_monitor.py          # script principal (corre uma vez por execução)
├── requirements.txt                # dependências
├── state.json                      # criado automaticamente na 1ª execução (guarda o estado anterior)
├── README.md
└── .github/
    └── workflows/
        └── check-stock.yml         # define quando e como o script corre no GitHub
```

## Passo a passo da configuração

### 1. Criar o repositório no GitHub
1. Cria uma conta no GitHub (se não tiveres) em github.com.
2. Cria um repositório novo, **privado** (recomendado, já que vai lá ficar o teu webhook indiretamente referenciado).
3. Faz upload de todos os ficheiros desta pasta para esse repositório (podes arrastar os ficheiros na interface web do GitHub, ou usar `git push` se preferires linha de comandos).

### 2. Editar a lista de produtos
Abre `zara_stock_monitor.py` e edita a lista `PRODUCTS`:

```python
PRODUCTS = [
    {"name": "Camisola X", "url": "https://www.zara.com/pt/pt/...-p00000001.html", "size_filter": None},
    {"name": "Calças Y", "url": "https://www.zara.com/pt/pt/...-p00000002.html", "size_filter": "M"},
]
```

### 3. Criar o webhook do Discord
No teu servidor Discord: **Definições do Canal → Integrações → Webhooks → Novo Webhook** → copia o URL.

### 4. Guardar o webhook como "secret" no GitHub
Por segurança, o webhook **não** vai escrito no código — vai como secret:

1. No repositório do GitHub: **Settings → Secrets and variables → Actions → New repository secret**
2. Nome: `DISCORD_WEBHOOK_URL`
3. Valor: cola o URL do webhook do Discord
4. Guarda.

### 5. Ajustar a frequência (opcional)
No ficheiro `.github/workflows/check-stock.yml`, a linha:
```yaml
- cron: "*/15 * * * *"
```
corre a cada 15 minutos. Podes mudar para `*/30 * * * *` (30 min), `0 * * * *` (de hora a hora), etc. Não convém correr com intervalos muito curtos, para não sobrecarregar o site da Zara nem esgotar os minutos gratuitos do GitHub Actions.

## Como sei que está a funcionar?

1. **Vai ao separador "Actions"** do teu repositório no GitHub (menu no topo da página do repo).
2. Deves ver o workflow **"Zara Stock Check"** listado. Se ainda não correu nenhuma vez, clica nele e depois em **"Run workflow"** (botão à direita) para o forçar a correr imediatamente, sem esperar pelo cron.
3. Clica na execução mais recente para veres os logs em tempo real. Devias ver linhas como:
   ```
   A iniciar verificação de stock da Zara...
   Produtos a verificar: 2
   [Camisola X] Primeira verificação — estado inicial guardado, sem alerta.
   [Camisola X] Verificação concluída: {'S': False, 'M': True, 'L': False}
   Verificação concluída. Estado guardado em state.json.
   ```
4. Se aparecer um ✅ verde no final da execução, correu tudo bem. Um ❌ vermelho significa que houve um erro (normalmente porque a estrutura da página da Zara mudou, ou o URL do produto está errado) — os logs dizem exatamente onde falhou.
5. **Nota importante:** na primeira execução, o script está só a "aprender" o estado atual dos tamanhos (não sabe se mudou algo, porque não há histórico ainda) — por isso não envia alerta nessa primeira vez, mesmo que um tamanho já esteja disponível. A partir da segunda execução em diante é que compara com o estado anterior e avisa se algo mudou.
6. Depois de correr, repara que aparece um novo commit no repositório chamado *"Atualizar estado de stock"* — isso confirma que o `state.json` foi atualizado com sucesso.
7. **Para testares o Discord isoladamente** (sem esperar pelo stock mudar), podes testar o webhook diretamente no terminal:
   ```bash
   curl -X POST -H "Content-Type: application/json" \
        -d '{"content": "Teste de webhook 🎉"}' \
        "COLA_AQUI_O_TEU_WEBHOOK_URL"
   ```
   Se receberes a mensagem no Discord, o webhook está bem configurado.

## Testar localmente antes de subir para o GitHub (opcional)

```bash
pip install -r requirements.txt

# macOS/Linux
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
python zara_stock_monitor.py

# Windows PowerShell
$env:DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
python zara_stock_monitor.py
```
Corre o script duas vezes seguidas — na segunda vez, se mudares manualmente algo no `state.json` (ex: pores um tamanho a `false`), deves receber um alerta no Discord, confirmando que a lógica de comparação funciona.

## Se o script parar de funcionar

A Zara altera a estrutura da página com alguma frequência. Se os logs mostrarem *"Não foi possível extrair os dados do produto"*:

1. Abre a página do produto no browser.
2. F12 → separador **Network** → recarrega a página → procura pedidos com "product" ou "availability" no nome, a devolver JSON.
3. Ajusta `extract_product_data()` e `get_stock_status()` no script conforme o novo formato encontrado.

## Nota

Este projeto faz scraping de páginas públicas para uso pessoal (acompanhar disponibilidade de artigos). Mantém um intervalo razoável entre verificações para não sobrecarregar o site nem correres risco de bloqueio.
