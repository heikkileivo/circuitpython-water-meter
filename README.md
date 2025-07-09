# circuitpython-water-meter
This is a simple water meter using circuitpython and [TinyS3](https://esp32s3.com/tinys3.html) board. The code can be used to count pulses measured from a mechanical water meter. The pulses are converted to units / minute and total units. The results are reported periodically to a MQTT server, and the values can be then used in e.g. [Home Assistant](https://www.home-assistant.io/).
## Background
I implemented this water meter inspired by a Finnish [blog](https://hyotynen.iki.fi/kotiautomaatio/vedenkulutuksen-seurantaa/) describing similar project, built using Arduino. The blog describes a method for measuring pulses from a mechanical water meter using LED laser and photodiode. Counting pulses in the described way works perfectly. The blog contains link the authors [GitHub repo](https://github.com/hyotynen/hass), which includes even [3d models](https://github.com/hyotynen/hass/tree/master/3d-models/Water%20consumption%20sensor) for attaching the sensor to the water meter.

Instead of using Arduino I prefer using CircuitPython, as it allows fast development cycle. One downside of CircuitPython is that so far it does not support using interrupts in counting pulse edges. However, this can be easily circumvented by using polling and asynchronous code. Using a [debouncer](https://docs.circuitpython.org/projects/debouncer/en/latest/) helps ignoring false readings from the sensor.

## Requirements
For the code to work, install following Adafruit depenencies to your board:

- [Asyncio](https://docs.circuitpython.org/projects/asyncio/en/latest/)
- [MiniMQTT](https://docs.circuitpython.org/projects/minimqtt/en/stable/api.html)
- [Connection Manager](https://docs.circuitpython.org/projects/connectionmanager/en/latest/)
- [Datetime](https://docs.circuitpython.org/projects/datetime/en/latest/)
- [Debouncer](https://docs.circuitpython.org/projects/debouncer/en/latest/)
- [Ticks](https://docs.circuitpython.org/projects/ticks/en/latest/)

Pre-built dependencies can be found in the [Adafruit libraries bundle] (https://circuitpython.org/libraries) for your board version.

## Notes
If you are using some other board than TinyS3, modify blink.py to initialize the led, depending on how it is implemented on your board.