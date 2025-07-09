import os
import asyncio
import wifi
from blink import blink, pixel, Color # For indicating connection status

async def connect_wifi():
    """
    Loop until wifi connection succeeds.
    """
    if wifi.radio.connected:
        print(f"Already connected to wifi.")
        return
    
    ssid = os.getenv("CIRCUITPY_WIFI_SSID")
    pwd = os.getenv("CIRCUITPY_WIFI_PASSWORD")
    while True:    
        print("Connecting Wifi...")    
        pixel[0] = Color.BLUE
        try:
            for network in wifi.radio.start_scanning_networks():
                print(f"\t{network.ssid}\t\tRSSI: {network.rssi:d}\tChannel: {network.channel:d}")
            
            wifi.radio.stop_scanning_networks()
            wifi.radio.connect(ssid, pwd)
            print("Connected to wifi.")
            pixel[0] = Color.BLACK
            await blink(Color.GREEN, 3)
            return

        except Exception as e:
            print(f"Connecting to wifi {ssid} failed: {e}")
            if "Unknown failure" in e.errno:
                # Blink to indicate error code returned
                code = int(e.errno[e.errno.rfind(" "):])
                await blink(Color.ORANGE, code)
            else:
                await blink(Color.RED, 3)
