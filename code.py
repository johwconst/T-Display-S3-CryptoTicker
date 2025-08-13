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
import terminalio

# Display Config
WIDTH = 320
HEIGHT = 170

button0 = digitalio.DigitalInOut(board.BUTTON0)
button0.direction = digitalio.Direction.INPUT
button0.pull = digitalio.Pull.UP

button1 = digitalio.DigitalInOut(board.BUTTON1)
button1.direction = digitalio.Direction.INPUT
button1.pull = digitalio.Pull.UP

display = board.DISPLAY

# Config Your Wifi Here
WIFI_SSID = "CHANGE-FOR-YOUR-WIFI"
WIFI_PASSWORD = "CHANGE-FOR-YOUR-PASSWORD"

# CoinGecko API
MARKET_API_URL = "http://api.coingecko.com/api/v3/coins/markets"
PRICE_API_URL = "http://api.coingecko.com/api/v3/simple/price"

try:
    import json
    with open("/selected_coins.json", "r") as f:
        SAVED_COINS = json.load(f)
except:
    SAVED_COINS = []

class CryptoTicker:
    def __init__(self):
        self.current_coin_index = 0
        self.last_update = 0
        self.last_coin_change = 0
        self.update_interval = 300  # Interval to Update Price 300 seconds
        self.coin_change_interval = 10  # Change coin every 10 seconds
        self.prices = {}
        self.available_coins = []  # List of all available coins
        self.selected_coins = []  # List of selected coins
        self.is_selection_mode = True  # Start in selection mode
        self.main_group = displayio.Group()
        self.is_display_rotated = True
        self.button_press_start = None
        display.rotation = 180
        self.setup_display()
        self.connect_wifi()
        self.setup_requests()
        
    def fetch_top_coins(self):
        try:
            print("Getting top 20 coins...")
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 20,
                "page": 1,
                "sparkline": False
            }
            url = f"{MARKET_API_URL}?vs_currency={params['vs_currency']}&order={params['order']}&per_page={params['per_page']}&page={params['page']}"
            response = self.requests.get(url)
            
            if response.status_code == 200:
                coins = response.json()
                self.available_coins = [{
                    "id": coin["id"],
                    "symbol": coin["symbol"].upper(),
                    "name": coin["name"],
                    "color": 0x00FF00
                } for coin in coins]
                
                if SAVED_COINS:
                    self.selected_coins = [coin for coin in self.available_coins 
                                         if coin["id"] in SAVED_COINS]

                print(f"Found {len(self.available_coins)} coins")
                return True
            else:
                print(f"API Error: Status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error fetching coins: {str(e)}")
            self.update_status_text(f"Error: {str(e)}")
            return False

    def save_selected_coins(self):
        try:
            selected_ids = [coin["id"] for coin in self.selected_coins]
            with open("/selected_coins.json", "w") as f:
                json.dump(selected_ids, f)
            print("Coins saved successfully!")
            return True
        except Exception as e:
            print(f"Error saving coins: {str(e)}")
            return False

    def show_selection_screen(self):
        while len(self.main_group) > 1:
            self.main_group.pop()
            
        coin = self.available_coins[self.current_coin_index]
        is_selected = any(sc["id"] == coin["id"] for sc in self.selected_coins)
        
        info_group = displayio.Group()
        
        title_text = label.Label(
            terminalio.FONT,
            text="SELECT COINS",
            scale=2,
            color=0x00FF00,
            anchor_point=(0.5, 0.0),
            anchored_position=(WIDTH//2, 10)
        )
        info_group.append(title_text)
        
        counter_text = label.Label(
            terminalio.FONT,
            text=f"({self.current_coin_index + 1}/{len(self.available_coins)})",
            scale=1,
            color=0x888888,
            anchor_point=(0.5, 0.0),
            anchored_position=(WIDTH//2, 35)
        )
        info_group.append(counter_text)
        
        symbol_text = label.Label(
            terminalio.FONT,
            text=coin["symbol"],
            scale=4,
            color=0xFFFFFF,
            anchor_point=(0.5, 0.5),
            anchored_position=(WIDTH//2, HEIGHT//2 - 15)
        )
        info_group.append(symbol_text)
        
        name_text = label.Label(
            terminalio.FONT,
            text=coin["name"],
            scale=2,
            color=0xFFFFFF,
            anchor_point=(0.5, 0.5),
            anchored_position=(WIDTH//2, HEIGHT//2 + 20)
        )
        info_group.append(name_text)
        
        status_text = label.Label(
            terminalio.FONT,
            text="[OK]" if is_selected else "[ ]",
            scale=1,
            color=0x00FF00 if is_selected else 0xFF0000,
            anchor_point=(0.5, 1.0),
            anchored_position=(WIDTH//2, HEIGHT - 40)
        )
        info_group.append(status_text)
        
        instructions_text = label.Label(
            terminalio.FONT,
            text="← NEXT | SELECT → (Hold 5s to confirm)",
            scale=1,
            color=0x888888,
            anchor_point=(0.5, 1.0),
            anchored_position=(WIDTH//2, HEIGHT - 10)
        )
        info_group.append(instructions_text)
        
        self.main_group.append(info_group)
        display.refresh()

    def toggle_current_coin(self):
        coin = self.available_coins[self.current_coin_index]
        # If already selected, remove
        if any(sc["id"] == coin["id"] for sc in self.selected_coins):
            self.selected_coins = [sc for sc in self.selected_coins if sc["id"] != coin["id"]]
        # If not selected, add
        else:
            self.selected_coins.append(coin)
        self.show_selection_screen()
        
    def setup_display(self):
        display.root_group = self.main_group
        
        background = displayio.Bitmap(WIDTH, HEIGHT, 1)
        background_palette = displayio.Palette(1)
        background_palette[0] = 0x000000
        background_sprite = displayio.TileGrid(background, pixel_shader=background_palette)
        self.main_group.append(background_sprite)
        
        loading_text = label.Label(
            terminalio.FONT,
            text="Connecting to WiFi...",
            scale=3,
            color=0xFFFFFF,
            anchor_point=(0.5, 0.5),
            anchored_position=(WIDTH//2, HEIGHT//2)
        )
        self.main_group.append(loading_text)
        display.refresh()
        
    def connect_wifi(self):
        try:
            print(f"Connecting to WiFi: {WIFI_SSID}")
            wifi.radio.connect(WIFI_SSID, WIFI_PASSWORD)
            print(f"Connected! IP: {wifi.radio.ipv4_address}")
            
            self.update_status_text("WiFi Connected!")
            time.sleep(1)
            
        except Exception as e:
            print(f"Error connecting to WiFi: {e}")
            self.update_status_text("WiFi Error!")
            time.sleep(2)
    
    def setup_requests(self):
        import ssl
        self.pool = socketpool.SocketPool(wifi.radio)
        ssl_context = ssl.create_default_context()
        self.requests = adafruit_requests.Session(self.pool, ssl_context)
        
    def update_status_text(self, text):
        if len(self.main_group) > 1:
            self.main_group.pop()
        
        status_text = label.Label(
            terminalio.FONT,
            text=text,
            scale=3,
            color=0xFFFFFF,
            anchor_point=(0.5, 0.5),
            anchored_position=(WIDTH//2, HEIGHT//2)
        )
        self.main_group.append(status_text)
        display.refresh()
        
    def fetch_prices(self):
        try:
            if not self.selected_coins:
                return False
                
            coin_ids = ",".join(coin["id"] for coin in self.selected_coins)
            url = f"{PRICE_API_URL}?vs_currencies=usd&include_24hr_change=true&ids={coin_ids}"
            print("API URL:", url)

            print(f"Fetching prices for: {coin_ids}")
            response = self.requests.get(url)
            
            if response.status_code == 200:
                self.prices = response.json()
                self.last_update = time.monotonic()
                print("Prices updated successfully!")
                return True
            else:
                print(f"API Error: Status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error fetching prices: {str(e)}")
            self.update_status_text(f"Error: {str(e)}")
            return False
        finally:
            gc.collect()
            
    def format_price(self, price):
        return f"${price:,.2f}"
            
    def create_coin_display(self):
        """Creates display for current coin"""
        if not self.selected_coins:
            self.update_status_text("No coin selected")
            return

        # Clear current display
        while len(self.main_group) > 1:
            self.main_group.pop()
            
        coin = self.selected_coins[self.current_coin_index]
        coin_data = self.prices.get(coin["id"], {})
        
        if not coin_data:
            self.update_status_text("Loading prices...")
            return
            
        usd_price = coin_data.get("usd", 0)
        change_24h = coin_data.get("usd_24h_change", 0)
        
        # Grupo principal da moeda
        coin_group = displayio.Group()
        
        # Barra superior com nome da moeda
        name_bg = displayio.Bitmap(WIDTH, 30, 1)
        name_palette = displayio.Palette(1)
        name_palette[0] = coin["color"]
        name_bg_sprite = displayio.TileGrid(name_bg, pixel_shader=name_palette)
        coin_group.append(name_bg_sprite)
        
        name_text = label.Label(
            terminalio.FONT,
            text=f"{coin['name']} ({coin['symbol']})",
            scale=2,
            color=0x000000,
            anchor_point=(0.5, 0.5),
            anchored_position=(WIDTH//2, 15)
        )
        coin_group.append(name_text)
        
        usd_text = label.Label(
            terminalio.FONT,
            text=self.format_price(usd_price),
            scale=5, 
            color=0x00FF00,
            anchor_point=(0.5, 0.5),
            anchored_position=(WIDTH//2, HEIGHT//2)
        )
        coin_group.append(usd_text)
        
        arrow = "+" if change_24h >= 0 else "-"
        change_color = 0x00FF00 if change_24h >= 0 else 0xFF0000
        change_text = label.Label(
            terminalio.FONT,
            text=f"{arrow}{abs(change_24h):.2f}%",
            scale=3,
            color=change_color,
            anchor_point=(0.5, 1.0),
            anchored_position=(WIDTH//2, HEIGHT - 20)
        )
        coin_group.append(change_text)
        
        counter_text = label.Label(
            terminalio.FONT,
            text=f"{self.current_coin_index + 1}/{len(self.selected_coins)}",
            scale=1,
            color=0x888888,
            anchor_point=(1.0, 0.0),
            anchored_position=(WIDTH - 5, 35)
        )
        coin_group.append(counter_text)
        
        update_text = label.Label(
            terminalio.FONT,
            text=f"Last Update: {int(time.monotonic() - self.last_update)}s",
            scale=1,
            color=0x888888,
            anchor_point=(0.0, 0.0),
            anchored_position=(5, 35)
        )
        coin_group.append(update_text)
        
        self.main_group.append(coin_group)
        display.refresh()
        
    def next_coin(self):
        self.current_coin_index = (self.current_coin_index + 1) % len(self.selected_coins)
        self.create_coin_display()
        
    def previous_coin(self):
        self.current_coin_index = (self.current_coin_index - 1) % len(self.selected_coins)
        self.create_coin_display()
        
    def should_update_prices(self):
        return (time.monotonic() - self.last_update) > self.update_interval
    
    def should_change_coin(self):
        return (time.monotonic() - self.last_coin_change) > self.coin_change_interval
    
    def auto_change_coin(self):
        self.next_coin()
        self.last_coin_change = time.monotonic()
        
    def toggle_display_rotation(self):
        self.is_display_rotated = not self.is_display_rotated
        display.rotation = 180 if self.is_display_rotated else 0
        display.refresh()
        
    def run(self):
        self.update_status_text("Loading coins...")
        if not self.fetch_top_coins():
            self.update_status_text("Error loading coins")
            return

        if not self.selected_coins:
            self.is_selection_mode = True
            self.show_selection_screen()
        else:
            self.is_selection_mode = False
            if self.fetch_prices():
                self.create_coin_display()
            else:
                self.update_status_text("Error loading prices")

        last_button0_state = True
        last_button1_state = True
        selection_hold_start = None
        
        while True:
            try:
                current_button0_state = button0.value
                current_button1_state = button1.value
                current_time = time.monotonic()
                
                if self.is_selection_mode:
                    if last_button0_state and not current_button0_state:
                        self.current_coin_index = (self.current_coin_index + 1) % len(self.available_coins)
                        self.show_selection_screen()
                        time.sleep(0.2)
                    
                    if last_button1_state and not current_button1_state:
                        selection_hold_start = current_time
                    elif not last_button1_state and current_button1_state:
                        if selection_hold_start and (current_time - selection_hold_start < 5):
                            self.toggle_current_coin()
                        selection_hold_start = None
                    elif not current_button1_state and selection_hold_start:
                        if current_time - selection_hold_start >= 5:
                            if len(self.selected_coins) > 0:
                                self.save_selected_coins()
                                self.is_selection_mode = False
                                self.current_coin_index = 0
                                if self.fetch_prices():
                                    self.create_coin_display()
                            selection_hold_start = None
                
                else:
                    if last_button0_state and not current_button0_state:
                        self.button_press_start = current_time
                    elif not last_button0_state and current_button0_state:
                        if self.button_press_start is not None:
                            if current_time - self.button_press_start < 2:
                                print("Next coin")
                                self.current_coin_index = (self.current_coin_index + 1) % len(self.selected_coins)
                                self.create_coin_display()
                            self.button_press_start = None
                        time.sleep(0.2)
                    elif not current_button0_state and self.button_press_start is not None:
                        if current_time - self.button_press_start >= 2:
                            print("Rotating display")
                            self.toggle_display_rotation()
                            self.button_press_start = None
                            time.sleep(0.2)
                    
                    if self.should_update_prices():
                        print("Updating prices...")
                        if self.fetch_prices():
                            self.create_coin_display()
                    
                    if self.should_change_coin():
                        self.current_coin_index = (self.current_coin_index + 1) % len(self.selected_coins)
                        self.create_coin_display()
                        self.last_coin_change = current_time
                
                last_button0_state = current_button0_state
                last_button1_state = current_button1_state
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(1)

# Main execution
if __name__ == "__main__":
    print("Starting Crypto Ticker...")
    ticker = CryptoTicker()
    ticker.run() # type: ignore