import json
import time
import gc
import board
import digitalio
import displayio
import wifi
import socketpool
import adafruit_requests
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
import terminalio

# Configurações do display
WIDTH = 320
HEIGHT = 170

# Configuração dos botões
button0 = digitalio.DigitalInOut(board.BUTTON0)
button0.direction = digitalio.Direction.INPUT
button0.pull = digitalio.Pull.UP

button1 = digitalio.DigitalInOut(board.BUTTON1)
button1.direction = digitalio.Direction.INPUT
button1.pull = digitalio.Pull.UP

display = board.DISPLAY

# Configurações WiFi (ALTERE ESTAS INFORMAÇÕES)
WIFI_SSID = ""
WIFI_PASSWORD = ""

# API para cotações (CoinGecko - gratuita)
API_URL = "http://api.coingecko.com/api/v3/simple/price"

# Moedas disponíveis
COINS = [
    {
        "id": "bitcoin",
        "symbol": "BTC",
        "name": "Bitcoin",
        "color": 0xFF9500
    },
    {
        "id": "monero", 
        "symbol": "XMR",
        "name": "Monero",
        "color": 0xFF6600
    },
    {
        "id": "ethereum",
        "symbol": "ETH",
        "name": "Ethereum",
        "color": 0x3C3C3D
    },
    {
        "id": "the-open-network",
        "symbol": "TON",
        "name": "Toncoin",
        "color": 0x2A9FFF
    }
]

class CryptoTicker:
    def __init__(self):
        self.current_coin_index = 0
        self.last_update = 0
        self.last_coin_change = 0
        self.update_interval = 300  # Atualizar preços a cada 300 segundos
        self.coin_change_interval = 10  # Alternar moeda a cada 3 segundos
        self.prices = {}
        self.main_group = displayio.Group()
        self.setup_display()
        self.connect_wifi()
        self.setup_requests()
        
    def setup_display(self):
        """Configura o display inicial"""
        display.root_group = self.main_group
        
        # Fundo preto
        background = displayio.Bitmap(WIDTH, HEIGHT, 1)
        background_palette = displayio.Palette(1)
        background_palette[0] = 0x000000
        background_sprite = displayio.TileGrid(background, pixel_shader=background_palette)
        self.main_group.append(background_sprite)
        
        # Texto de carregamento
        loading_text = label.Label(
            terminalio.FONT,
            text="Conectando WiFi...",
            color=0xFFFFFF,
            anchor_point=(0.5, 0.5),
            anchored_position=(WIDTH//2, HEIGHT//2)
        )
        self.main_group.append(loading_text)
        display.refresh()
        
    def connect_wifi(self):
        """Conecta ao WiFi"""
        try:
            print(f"Conectando ao WiFi: {WIFI_SSID}")
            wifi.radio.connect(WIFI_SSID, WIFI_PASSWORD)
            print(f"Conectado! IP: {wifi.radio.ipv4_address}")
            
            # Atualiza texto de status
            self.update_status_text("WiFi Conectado!")
            time.sleep(1)
            
        except Exception as e:
            print(f"Erro ao conectar WiFi: {e}")
            self.update_status_text("Erro WiFi!")
            time.sleep(2)
    
    def setup_requests(self):
        """Configura cliente HTTP"""
        import ssl
        self.pool = socketpool.SocketPool(wifi.radio)
        ssl_context = ssl.create_default_context()
        self.requests = adafruit_requests.Session(self.pool, ssl_context)
        
    def update_status_text(self, text):
        """Atualiza texto de status na tela"""
        if len(self.main_group) > 1:
            self.main_group.pop()
        
        status_text = label.Label(
            terminalio.FONT,
            text=text,
            color=0xFFFFFF,
            anchor_point=(0.5, 0.5),
            anchored_position=(WIDTH//2, HEIGHT//2)
        )
        self.main_group.append(status_text)
        display.refresh()
        
    def fetch_prices(self):
        """Busca preços das moedas na API"""
        try:
            # Busca preços para todas as moedas configuradas
            
            coin_ids = ",".join(coin["id"] for coin in COINS)            
            url = f"{API_URL}?vs_currencies=usd&include_24hr_change=true&ids={coin_ids}"
            print("URL da API:", url)
            
            print(f"Buscando preços para: {coin_ids}")
            response = self.requests.get(url)
            
            print("Response status:", response.status_code)
            if response.status_code == 200:
                data = response.json()
                print("Dados recebidos:", data)  # Adiciona log dos dados
                self.prices = data
                self.last_update = time.monotonic()
                print("Preços atualizados com sucesso!")
                return True
            else:
                print(f"Erro na API: Status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Erro ao buscar preços: {str(e)}")
            self.update_status_text(f"Erro: {str(e)}")  # Mostra erro na tela
            return False
        finally:
            gc.collect()
            
    def format_price(self, price):
        """Formata preço para exibição"""
        if price >= 1000:
            return f"${price:,.0f}"
        elif price >= 1:
            return f"${price:.2f}"
        else:
            return f"${price:.4f}"
            
    def format_price_brl(self, price):
        """Formata preço em BRL para exibição"""
        if price >= 1000:
            return f"R${price:,.0f}"
        else:
            return f"R${price:.2f}"
            
    def create_coin_display(self):
        """Cria display para moeda atual"""
        # Limpa display atual
        while len(self.main_group) > 1:  # Mantém apenas o fundo
            self.main_group.pop()
            
        coin = COINS[self.current_coin_index]
        coin_data = self.prices.get(coin["id"], {})
        
        if not coin_data:
            self.update_status_text("Carregando preços...")
            return
            
        usd_price = coin_data.get("usd", 0)
        change_24h = coin_data.get("usd_24h_change", 0)
        
        # Grupo principal da moeda
        coin_group = displayio.Group()
        
        # Logo/Símbolo da moeda (texto grande colorido) - Lado esquerdo
        symbol_text = label.Label(
            terminalio.FONT,
            text=coin["symbol"],
            scale=4,  # Símbolo ainda maior
            color=coin["color"],
            anchor_point=(0.0, 0.5),  # Alinhado à esquerda
            anchored_position=(20, HEIGHT//2)  # Centralizado verticalmente
        )
        coin_group.append(symbol_text)
        
        # Nome da moeda - Lado direito superior
        name_text = label.Label(
            terminalio.FONT,
            text=coin["name"],
            scale=2,
            color=0xFFFFFF,
            anchor_point=(1.0, 0.0),  # Alinhado à direita
            anchored_position=(WIDTH - 20, 20)
        )
        coin_group.append(name_text)
        
        # Preço em USD - Lado direito centro
        usd_text = label.Label(
            terminalio.FONT,
            text=f"{self.format_price(usd_price)}",
            scale=4,  # Preço maior
            color=0x00FF00,
            anchor_point=(1.0, 0.5),  # Alinhado à direita
            anchored_position=(WIDTH - 20, HEIGHT//2)
        )
        coin_group.append(usd_text)
        
        # Variação 24h - Lado direito inferior
        change_color = 0x00FF00 if change_24h >= 0 else 0xFF0000  # Verde se positivo, vermelho se negativo
        change_text = label.Label(
            terminalio.FONT,
            text=f"{change_24h:+.2f}%",  # +/- na frente do número
            scale=3,
            color=change_color,
            anchor_point=(1.0, 1.0),  # Alinhado à direita
            anchored_position=(WIDTH - 20, HEIGHT - 20)
        )
        coin_group.append(change_text)
        
        # Timestamp da última atualização - Pequeno no canto inferior esquerdo
        time_text = label.Label(
            terminalio.FONT,
            text=f"{time.monotonic() - self.last_update:.0f}s",
            color=0x666666,
            scale=2,
            anchor_point=(0.0, 1.0),
            anchored_position=(20, HEIGHT - 10)
        )
        coin_group.append(time_text)
        
        self.main_group.append(coin_group)
        display.refresh()
        
    def next_coin(self):
        """Vai para próxima moeda"""
        self.current_coin_index = (self.current_coin_index + 1) % len(COINS)
        self.create_coin_display()
        
    def previous_coin(self):
        """Vai para moeda anterior"""
        self.current_coin_index = (self.current_coin_index - 1) % len(COINS)
        self.create_coin_display()
        
    def should_update_prices(self):
        """Verifica se deve atualizar preços"""
        return (time.monotonic() - self.last_update) > self.update_interval
    
    def should_change_coin(self):
        """Verifica se deve alternar para próxima moeda"""
        return (time.monotonic() - self.last_coin_change) > self.coin_change_interval
    
    def auto_change_coin(self):
        """Alterna automaticamente para próxima moeda"""
        self.next_coin()
        self.last_coin_change = time.monotonic()
        
    def run(self):
        """Loop principal da aplicação"""
        # Busca preços iniciais
        self.update_status_text("Buscando preços...")
        if self.fetch_prices():
            self.create_coin_display()
        else:
            self.update_status_text("Erro ao buscar preços")
            
        # Estados dos botões para debounce
        last_button0_state = True
        last_button1_state = True
        
        while True:
            try:
                # Verifica botão 0 (próxima moeda)
                current_button0_state = button0.value
                if last_button0_state and not current_button0_state:
                    print("Botão 0 pressionado - Próxima moeda")
                    self.next_coin()
                    time.sleep(0.2)  # Debounce
                last_button0_state = current_button0_state
                
                # Verifica botão 1 (moeda anterior)
                current_button1_state = button1.value
                if last_button1_state and not current_button1_state:
                    print("Botão 1 pressionado - Moeda anterior")
                    self.previous_coin()
                    time.sleep(0.2)  # Debounce
                last_button1_state = current_button1_state
                
                # Atualiza preços se necessário
                if self.should_update_prices():
                    print("Atualizando preços...")
                    if self.fetch_prices():
                        self.create_coin_display()
                    else:
                        print("Falha ao atualizar preços")
                
                # Altera moeda automaticamente se necessário
                if self.should_change_coin():
                    print("Mudando para próxima moeda automaticamente...")
                    self.auto_change_coin()
                
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
                
            except Exception as e:
                print(f"Erro no loop principal: {e}")
                time.sleep(1)

# Execução principal
if __name__ == "__main__":
    print("Iniciando Crypto Ticker...")
    ticker = CryptoTicker()
    ticker.run() # type: ignore