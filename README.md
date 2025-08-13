# LilyGo T-Display-S3 -> Top 20 Crypto Ticker

A CircuitPython-based cryptocurrency price ticker display project for the LilyGo T-Display-S3 that shows real-time prices and trends for your favorite cryptocurrencies.

# Project Gallery

<div align="center">

|  |  |  |
|:---------------:|:-------------:|:--------------:|
| <img src="/images/1.jpg" width="250" alt="Selection Screen"> | <img src="/images/2.jpg" width="250" alt="Price Display"> | <img src="/images/4.jpg" width="250" alt="Battery Status"> |

|  | |  |
|:------------:|:------------:|:-----------:|
| <img src="/images/5.jpg" width="250" alt="Price Changes"> | <img src="/images/6.jpg" width="250" alt="Display View"> | <img src="/images/7.jpg" width="250" alt="Full Device View"> |

</div>


## Features

- Real-time cryptocurrency price monitoring
- Top 20 cryptocurrencies selection
- 24-hour price change indicators
- Battery monitoring with charging status
- Display rotation support (180°)
- Persistent coin selection storage
- Battery level indicator with color coding

## Usage

### Initial Setup
1. Power on the device
2. Wait for WiFi connection
3. Select your desired cryptocurrencies from the top 20 list

### Controls
- Button 0:
  - Short press: Next coin
  - Long press (2s): Rotate display
- Button 1 (in selection mode):
  - Short press: Toggle coin selection
  - Long press (5s): Save selection and start monitoring

## Hardware Requirements

- T-Display-S3 board
- USB Type-C cable

## Software Requirements

- CircuitPython
- Required libraries:
  - adafruit_display_text
  - adafruit_requests
  - wifi
  - displayio
  - analogio (for battery monitoring)

## Installation

1. Install CircuitPython on your board
2. Copy the following files to your board:
   - code.py
   - All required libraries
3. Configure your WiFi credentials in code.py:
   ```python
   WIFI_SSID = "your_wifi_name"
   WIFI_PASSWORD = "your_wifi_password"
   ```
