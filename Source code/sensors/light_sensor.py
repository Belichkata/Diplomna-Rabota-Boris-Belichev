import time
import board, busio
import adafruit_tsl2561

def read_ambient_lux(samples=10, delay=0.1):
    """
    Reads ambient light from TSL2561 sensor.
    Returns average lux or None if sensor fails.
    """
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        sensor = adafruit_tsl2561.TSL2561(i2c)

        readings = []
        for _ in range(samples):
            lux = sensor.lux
            if lux is not None:
                readings.append(lux)
            time.sleep(delay)

        if readings:
            avg_lux = sum(readings) / len(readings)
            print(f"💡 Ambient light (sensor): {avg_lux:.1f} lux")
            return avg_lux

    except Exception as e:
        print(f"⚠️ Lux sensor error: {e}")

    return None