"""
Zara Stock Monitor -> Discord Webhook (versão GitHub Actions)
================================================================

Diferença em relação à versão "loop infinito":
- Este script corre UMA VEZ e termina (não fica em loop).
- É o GitHub Actions que o volta a correr de X em X minutos (cron job),
  por isso não precisas de nenhum computador ligado.
- O estado anterior (para saber se algo mudou desde a última verificação)
  é guardado no ficheiro state.json, que o workflow do GitHub Actions
  grava de volta no repositório entre execuções.

Não precisas de editar nada de "loop" aqui — só a lista PRODUCTS abaixo.
O webhook do Discord vem da variável de ambiente DISCORD_WEBHOOK_URL,
configurada como secret no GitHub (ver README.md).
"""

import requests
import json
import re
import os
import sys
import logging

# ==================== CONFIGURAÇÃO ====================

# Lista de produtos a monitorizar.
# - "name": nome à tua escolha, só para aparecer nas notificações/logs
# - "url": link da página do produto na Zara
# - "size_filter": tamanho específico a monitorizar (ex: "M"), ou None para todos
PRODUCTS = [
    {
        "name": "CALÇÕES COMBINADOS COM RENDA BORDADOS",
        "url": "https://www.zara.com/pt/pt/calcoes-combinados-com-renda-bordada-p05416103.html",
        "size_filter": None,
    },
    {
        "name": "VESTIDO COMPRIDO FRANJAS ZW COLLECTION",
        "url": "https://www.zara.com/pt/pt/vestido-comprido-de-franjas-zw-collection-p03210102.html",
        "size_filter": None,
    },
]
    # Adiciona aqui quantos produtos quiseres, seguindo o mesmo formato.

# O webhook vem de uma variável de ambiente (definida como secret no GitHub).
# Para testares localmente, podes definir a variável no terminal antes de correr:
#   export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."   (macOS/Linux)
#   $env:DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."     (Windows PowerShell)
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

STATE_FILE = "state.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pt-PT,pt;q=0.9",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# ==================== FUNÇÕES ====================


def send_discord_alert(message: str) -> None:
    """Envia uma mensagem para o webhook do Discord configurado."""
    if not DISCORD_WEBHOOK_URL:
        logging.error("DISCORD_WEBHOOK_URL não está definido — não é possível enviar alerta.")
        return
    payload = {"content": message}
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Erro ao enviar notificação para o Discord: {e}")


def extract_product_data(html: str):
    """
    A Zara embebe os dados do produto (tamanhos, disponibilidade, etc.)
    num bloco de JavaScript/JSON dentro do HTML da página.
    """
    match = re.search(r"window\.zara\.viewPayload\s*=\s*({.*?});", html, re.DOTALL)

    if not match:
        match = re.search(
            r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',
            html,
            re.DOTALL,
        )

    if not match:
        return None

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def get_stock_status(product_url: str) -> dict:
    """Devolve um dicionário {tamanho: disponível(bool)} para o produto."""
    resp = requests.get(product_url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    data = extract_product_data(resp.text)
    if not data:
        raise ValueError(
            "Não foi possível extrair os dados do produto. "
            "A estrutura da página pode ter mudado."
        )

    sizes = {}
    try:
        colors = data["product"]["detail"]["colors"]
        for size_info in colors[0]["sizes"]:
            name = size_info.get("name")
            available = size_info.get("availability") == "in_stock"
            sizes[name] = available
    except (KeyError, IndexError, TypeError):
        raise ValueError(
            "Estrutura de dados inesperada dentro do JSON extraído."
        )

    return sizes


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def check_product(product: dict, previous_status: dict) -> dict:
    """
    Verifica um único produto, compara com o estado anterior e envia
    alertas para o Discord se algo mudou. Devolve o novo estado.
    """
    name = product["name"]
    url = product["url"]
    size_filter = product.get("size_filter")

    current_status = get_stock_status(url)

    if size_filter:
        current_status = {size_filter: current_status.get(size_filter, False)}

    is_first_check = len(previous_status) == 0

    for size, available in current_status.items():
        was_available = previous_status.get(size)

        if was_available is not None and available != was_available:
            if available:
                send_discord_alert(
                    f"🟢 **[{name}]** Em stock! Tamanho **{size}** disponível agora.\n{url}"
                )
                logging.info(f"[{name}] Tamanho {size} ficou disponível.")
            else:
                send_discord_alert(
                    f"🔴 **[{name}]** Tamanho **{size}** esgotou.\n{url}"
                )
                logging.info(f"[{name}] Tamanho {size} esgotou.")

    if is_first_check:
        logging.info(f"[{name}] Primeira verificação — estado inicial guardado, sem alerta.")

    logging.info(f"[{name}] Verificação concluída: {current_status}")
    return current_status


def main() -> None:
    logging.info("A iniciar verificação de stock da Zara...")
    logging.info(f"Produtos a verificar: {len(PRODUCTS)}")

    state = load_state()
    had_error = False

    for product in PRODUCTS:
        url = product["url"]
        previous_status = state.get(url, {})
        try:
            new_status = check_product(product, previous_status)
            state[url] = new_status
        except Exception as e:
            had_error = True
            logging.error(f"[{product['name']}] Erro durante a verificação: {e}")

    save_state(state)
    logging.info("Verificação concluída. Estado guardado em state.json.")

    if had_error:
        sys.exit(1)  # marca a execução do GitHub Actions como "failed" para dares por isso


if __name__ == "__main__":
    main()
