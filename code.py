import time, gc, os, ssl
import digitalio
import supervisor
import wifi, socketpool
import asyncio

from adafruit_datetime import timedelta
from adafruit_debouncer import Debouncer
from ringbuffer import RingBuffer
from blink import blink, Color
from mqtt import Mqtt

class LoopState:
    """
    Loop state for stopping all loops when necessary
    """
    def __init__(self):
        self.running = True
        self.mqtt = None
        # For debugging purposes
        self.msg_time = 0 
        self.uptime_time = 0
                
async def measure_uptime(state, counter):
    """
    Task for continuously measuring and reporting uptime to mqtt.
    """
    start_time = time.time()
    root_topic = os.getenv("mqtt_topic")
    uptime_topic = f"{root_topic}/uptime"
    while state.running:
        t = time.time()
        uptime = t - start_time
        
        try:
            uptime_str = str(timedelta(seconds=uptime))
            print(f"Publishing uptime { uptime_str }")
            if state.mqtt.on_connected.is_set():
                state.mqtt.publish(f"{uptime_topic}/seconds", uptime)
                state.mqtt.publish(f"{uptime_topic}/str", uptime_str)

            state.uptime_time = uptime # Store uptime in seconds

        except Exception as e:
            print(f"Failed to publish uptime: {repr(e)}")   

        # Report uptime in 10s intervals
        await asyncio.sleep(10)

class Counter:
    """
    Simple counter for counting pin edges.
    """
    def __init__(self):
        self.value = 0
        self.buffer = None
        self.pulses_per_unit = 1
        self.name = "Counter"
        self.counter_topic = "counter"
        self.value_topic = "value"
        self.std_dev_topic = "dev"
        
        
async def poll_pin(pin, state, counter, debounce_time):
    """
    Continuously measure pin counting pulses and pulse intervals.
    """
    input = digitalio.DigitalInOut(pin)
    input.direction = digitalio.Direction.INPUT
    input.pull = digitalio.Pull.UP
    debouncer = Debouncer(input, debounce_time)
    previous_time = 0
    print(f"Entering poller for { counter.name }")
    while state.running:
        debouncer.update()
        # Count both edges for better resolution
        if debouncer.fell or debouncer.rose:
            counter.value += 1
            current_time = supervisor.ticks_ms()
            timedelta = current_time - previous_time
            previous_time = current_time
            # Ignore negative timedelta occuring on ticks overflow
            if counter.buffer and timedelta > 0:
                counter.buffer.append(timedelta)
        
        await asyncio.sleep(0) # Poll as fast as we can

    print(f"Exiting poller for { counter.name }")


async def calculate_value(state, counter):
    """
    Calculate and report current value.
    """
    previous_value = counter.value
    previous_time = 0
    std_dev = 0
    total_units = 0
    
    print(f"Entering value loop for {counter.name}")
    while state.running:
        current_time = supervisor.ticks_ms()
        timedelta = current_time - previous_time
        if timedelta < 0: # Ticks overflow
            continue            
        previous_time = current_time
        # Calculate how many pulses we have counted since previous time
        current_value = counter.value
        pulses = current_value - previous_value
        previous_value = current_value
        
        std_dev = counter.buffer.std_dev
        pulses_per_s = 0
        
        if pulses >= 0:         
            avg_timedelta = timedelta                 # Measured actual time in milliseconds
            # avg_timedelta = state.buffer.avg        # Alternatively, get average from ring buffer
            avg_timedelta_s = avg_timedelta / 1000    # Measured actual time in seconds
            
            pulses_per_s = 0
            if avg_timedelta_s:
                pulses_per_s = pulses / avg_timedelta_s      
            
            pulses_per_min = pulses_per_s * 60
            
            units_per_min = pulses_per_min / counter.pulses_per_unit
            total_value_increment = pulses / counter.pulses_per_unit
            total_units += total_value_increment

            # For debugging
            print(f"Total pulses: {counter.value}") 
            print(f"Pulses measured: {pulses}") 
            print(f"Pulses / min: {pulses_per_min}")                  
            print(f"Units / min : {units_per_min}")
            print(f"Total units : {total_units}")
            print(f"Message time : {state.msg_time} s")
            print(f"Uptime time : {state.uptime_time} s")
            print(f"Dev : {std_dev}")

        # Send a new message
        pixel[0] = Color.BLUE      # Indicate we are sending message
        print(f"Sending {counter.name} values...")
        try:
            if state.mqtt.on_connected.is_set():
                state.mqtt.publish(counter.counter_topic, pulses_per_s)
                state.mqtt.publish(counter.value_topic, units_per_min)            
                state.mqtt.publish(counter.total_value_topic, total_units)
                state.mqtt.publish(counter.std_dev_topic, counter.buffer.std_dev)
                state.mqtt.publish(counter.reconnects_topic, state.mqtt.reconnects)
            else:
                print("Unable to send counter values: mqtt not connected.")

            pixel[0] = Color.BLACK # Indicate sending succeeded
        except Exception as e:
            print(f"Failed to send values for {counter.name}: {repr(e)}.")
                
        pixel[0] = Color.BLACK
        print(f"{counter.name} values sent.")

        end_time = supervisor.ticks_ms()
        time_elapsed = end_time - current_time  # Time elapsed while processing data in ms
        state.msg_time = time_elapsed / 1000    # For debugging, store time elapsed in s
        await asyncio.sleep(counter.interval)

    print(f"Exiting value loop for {counter.name}")


def create_tasks(state):
    """
    Create asynchronous tasks to be run continuously.
    """ 
    tasks = []
    
    counter = Counter()
    root_topic = os.getenv("root_topic")
    counter.name = os.getenv("counter_name")
    counter.counter_topic = f"{root_topic}/pulses"
    counter.value_topic = f"{root_topic}/value"
    counter.total_value_topic = f"{root_topic}/total"
    counter.std_dev_topic = f"{root_topic}/dev"
    counter.reconnects_topic = f"{root_topic}/reconnects"
    counter.pulses_per_unit = os.getenv("pulses_per_unit")  
    counter.interval = os.getenv("report_interval")
    counter.buffer = RingBuffer(os.getenv("ring_buffer_length"))
    counter.total_value_multiplier = os.getenv("total_value_multiplier")

    pin = eval(os.getenv("sensor_pin"))
    debounce_time = os.getenv("debounce_time_ms") / 1000
    tasks.append(asyncio.create_task(poll_pin(pin, state, counter, debounce_time=debounce_time)))
    tasks.append(asyncio.create_task(calculate_value(state, counter)))
    tasks.append(asyncio.create_task(measure_uptime(state, counter)))
    tasks.append(asyncio.create_task(state.mqtt.connect()))
    return tasks

def output_mem():
    # Show available memory
    print("Memory Info - gc.mem_free()")
    print("---------------------------")
    print("{} Bytes\n".format(gc.mem_free()))

    flash = os.statvfs('/')
    flash_size = flash[0] * flash[2]
    flash_free = flash[0] * flash[3]
    # Show flash size
    print("Flash - os.statvfs('/')")
    print("---------------------------")
    print("Size: {} Bytes\nFree: {} Bytes\n".format(flash_size, flash_free))

async def main():
    """
    Main entry point. 
    """
    output_mem()

    socket_pool = socketpool.SocketPool(wifi.radio)
    ssl_context = ssl.create_default_context()  

    state = LoopState()
    state.mqtt = Mqtt(socket_pool, ssl_context)
    tasks = create_tasks(state) # Create async tasks
    
    await asyncio.gather(*tasks)

asyncio.run(main())