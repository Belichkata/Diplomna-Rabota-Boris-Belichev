import time

try:
    import adafruit_tsl2561
    import board
    import busio
except ImportError:
    adafruit_tsl2561 = None
    board = None
    busio = None


def read_ambient_lux(samples=10, delay=0.1):
    if not all([adafruit_tsl2561, board, busio]):
        return None
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        sensor = adafruit_tsl2561.TSL2561(i2c, address=0x29)
        readings = []
        for _ in range(samples):
            lux = sensor.lux
            if lux is not None:
                readings.append(lux)
            time.sleep(delay)
        if not readings:
            return None
        return sum(readings) / len(readings)
    except Exception as error:
        print(f"Lux sensor error: {error}")
        return None
