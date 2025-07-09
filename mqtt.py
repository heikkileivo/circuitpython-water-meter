import os
import asyncio
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from connect_wifi import connect_wifi
from blink import blink, Color

class Mqtt:
    """
    Implements self-reconnecting mqtt client.
    """
    def __init__(self, socket_pool, ssl_context):
        self.client = None
        self.on_connected = asyncio.Event()
        self.on_disconnected = asyncio.Event()
        self.pool = socket_pool
        self.ssl_context = ssl_context
        self.reconnects = -1
        
    async def connect(self):
        """
        Connect to MQTT server. Reconnect when on_disconnected signal is set.
        """
        print("Setting up mqtt...")
        if self.client and self.client.is_connected():
            print("Already connected.")
            return
    
        self.on_connected.clear()
        self.client = MQTT.MQTT(
            broker = os.getenv("mqtt_broker"),
            port = os.getenv("mqtt_port"),
            username = os.getenv("mqtt_user"),
            password = os.getenv("mqtt_pwd"),
            socket_pool = self.pool,
            ssl_context = self.ssl_context)
        
        def connected(client, userdata, flags, rc):
            print("Connected to mqtt broker.")
            self.reconnects += 1
            self.on_disconnected.clear()
            self.on_connected.set()
            asyncio.create_task(blink(Color.GREEN, 3))

        def disconnected(client, userdata, rc):
            print("Disconnected from mqtt broker.")
            self.on_disconnected.set()
            self.on_connected.clear()
            asyncio.create_task(blink(Color.ORANGE, 5))
        
        def message(client, topic, message):
            print(f"New message on topic {topic}: {message}")
            asyncio.create_task(blink(Color.GREEN, 2))

        print("Setting callbacks..")
        self.client.on_connect = connected
        self.client.on_disconnect = disconnected
        self.client.on_message = message

        print("Connecting to MQTT broker...")

        await blink(Color.BLUE, 3)
        await connect_wifi()
        await blink(Color.GREEN, 2)

        try:
            self.client.connect()
        except Exception as e:
            print(f"Failed to connect to MQTT: {repr(e)}")
            self.on_disconnected.set()

        # Wait here until on_disconnected event is set
        await self.on_disconnected.wait()

        # Notify user and try to reconnect
        await blink(Color.RED, 5)
        print("Mqtt disconnected, reconnnecting...")
        self.disconnect()
        asyncio.create_task(self.connect())    
                    
    def publish(self, channel, msg):
        """
        Publish message to a channel, try to reconnect on error.
        """
        if self.on_disconnected.is_set():
            print("Failed to send message, MQTT is not connected.")
        if self.client and self.on_connected.is_set() :
            try:
                self.client.publish(channel, msg)
            except Exception as e:
                print(f"Failed to send message: {repr(e)}.")
                # Release holding code in connect method to reconnect
                self.on_disconnected.set()        
        else:
            print(f"Failed to send message, MQTT is not connected.")
            
    def disconnect(self):
        """
        Disconnect from mqtt client
        """
        if self.client:
            try:
                self.client.disconnect()
            except Exception as e:
                print(f"Failed to disconnect MQTT: { e }")
            self.client = None

