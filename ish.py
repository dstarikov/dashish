import sys
import serial
import pygame
from pygame.locals import *
import math
import obd
import time
import json
import os
from collections import deque
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Constants for serial ports and baud rate
ARDUINO_PORT = '/dev/arduino'  # Sensor data
PROMICRO_PORT = '/dev/pico'    # RPM light
ELM327_PORT = '/dev/ch340'     # OBD2 ELM327 adapter
BAUD_RATE = 115200             # Baud rate for all serial devices

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (169, 169, 169)
DARK_GRAY = (50, 50, 50)

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption('Vehicle Data Display')
pygame.mouse.set_visible(False)
clock = pygame.time.Clock()

# Screen dimensions
SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_size()

# Load images
def load_and_scale_image(path, size):
    image = pygame.image.load(path)
    return pygame.transform.scale(image, size)

# Background images
BACKGROUND_IMAGE = load_and_scale_image('/home/cleanish/dashish/graphics/face.png', (SCREEN_WIDTH, SCREEN_HEIGHT))
RPM_BACKGROUND_IMAGE = load_and_scale_image('/home/cleanish/dashish/graphics/wave2.png', (SCREEN_WIDTH, 130))
SMALL_BAR_IMAGE = pygame.image.load('/home/cleanish/dashish/graphics/etc_ot.png')
OIL_PRESSURE_BAR_IMAGE = pygame.image.load('/home/cleanish/dashish/graphics/op.png')
FUEL_BAR_IMAGE = pygame.image.load('/home/cleanish/dashish/graphics/gas.png')

# Loading screen image
LOADING_SCREEN_IMAGE = load_and_scale_image('/home/cleanish/dashish/graphics/loading_screen.png', (SCREEN_WIDTH, SCREEN_HEIGHT))

# Load fonts (using the same fonts as originally)
def load_font(path, size):
    try:
        return pygame.font.Font(path, size)
    except IOError as e:
        logging.error(f"Unable to load font '{path}': {e}")
        sys.exit(1)

FONT_PATHS = {
    'custom': '/home/cleanish/dashish/Fonts/ZeroAthletics.ttf',
    'rpm': '/home/cleanish/dashish/Fonts/ZeroAthletics.ttf',
    'elm': '/home/cleanish/dashish/Fonts/Orbitron-Black.ttf',
    'unit': '/home/cleanish/dashish/Fonts/Orbitron-Black.ttf',
    'trip': '/home/cleanish/dashish/Fonts/Orbitron-Black.ttf',
    'fuel_level': '/home/cleanish/dashish/Fonts/Orbitron-Black.ttf',
}

FONTS = {
    'value': load_font(FONT_PATHS['custom'], 45),
    'rpm': load_font(FONT_PATHS['rpm'], 65),
    'speed': load_font(FONT_PATHS['rpm'], 80),
    'unit': load_font(FONT_PATHS['unit'], 20),
    'trip': load_font(FONT_PATHS['trip'], 27),
    'fuel_level': load_font(FONT_PATHS['fuel_level'], 20),
    'elm': {
        'coolant_temp': load_font(FONT_PATHS['elm'], 25),
        'intake_temp': load_font(FONT_PATHS['elm'], 25),
        'timing_advance': load_font(FONT_PATHS['elm'], 25),
        'engine_load': load_font(FONT_PATHS['elm'], 25),
        'unit': load_font(FONT_PATHS['elm'], 20),
    },
    'pressure_coolant_oil': load_font(FONT_PATHS['custom'], 45),
}

# Data structure for storing sensor data
class SensorData:
    def __init__(self):
        self.data = {
            "Pressure": deque(maxlen=100),
            "CoolantTemp": deque(maxlen=100),
            "OilTemp": deque(maxlen=100),
            "Speed": deque(maxlen=25),
            "Latitude": None,
            "Longitude": None,
            "Distance": 0.0,
            "RPM": 0,
            "FuelLevel": 100.0,
            "Ax": deque(maxlen=25),
            "Ay": deque(maxlen=25),
            "Az": deque(maxlen=25),
            "Gx": deque(maxlen=25),
            "Gy": deque(maxlen=25),
            "Gz": deque(maxlen=25),
            "ELM_CoolantTemp": 0.0,
            "ELM_IntakeTemp": 0.0,
            "ELM_TimingAdvance": 0.0,
            "ELM_EngineLoad": 0.0,
        }
        self.filtered_fuel_values = deque(maxlen=10)

    def update(self, key, value):
        if key in self.data:
            if isinstance(self.data[key], deque):
                self.data[key].append(value)
            else:
                self.data[key] = value

    def get_average(self, key):
        if key in self.data and isinstance(self.data[key], deque):
            values = self.data[key]
            return sum(values) / len(values) if values else 0.0
        return self.data.get(key, 0.0)

    def get_filtered_fuel_level(self, new_value):
        self.filtered_fuel_values.append(new_value)
        return sum(self.filtered_fuel_values) / len(self.filtered_fuel_values)

sensor_data = SensorData()

# Trip manager class
class TripManager:
    MILES_FILE = "total_miles.txt"

    def __init__(self):
        self.total_distance = self.load_total_miles_from_file()
        self.last_lat = None
        self.last_lon = None

    def reset_trip(self):
        self.total_distance = 0.0
        self.last_lat = None
        self.last_lon = None
        self.save_total_miles_to_file(self.total_distance)

    def update_trip(self, current_lat, current_lon):
        if current_lat is None or current_lon is None:
            return self.total_distance

        if self.last_lat is not None and self.last_lon is not None:
            distance = calculate_distance(self.last_lat, self.last_lon, current_lat, current_lon)
            if distance > 0.01:
                self.total_distance += distance

        self.last_lat = current_lat
        self.last_lon = current_lon
        self.save_total_miles_to_file(self.total_distance)

        return self.total_distance

    def load_total_miles_from_file(self):
        if os.path.exists(self.MILES_FILE):
            try:
                with open(self.MILES_FILE, "r") as file:
                    return float(file.read().strip())
            except (ValueError, IOError) as e:
                logging.error(f"Error reading total miles from file: {e}")
                return 0.0
        return 0.0

    def save_total_miles_to_file(self, total_miles):
        try:
            with open(self.MILES_FILE, "w") as file:
                file.write(f"{total_miles}")
        except IOError as e:
            logging.error(f"Error writing total miles to file: {e}")

trip_manager = TripManager()

def calculate_distance(lat1, lon1, lat2, lon2):
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 0.0
    if abs(lat1 - lat2) < 0.00001 and abs(lon1 - lon2) < 0.00001:
        return 0.0

    R = 3958.8  # Radius of Earth in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

# Serial communication handlers
class SerialConnection:
    def __init__(self, port, baud_rate, name):
        self.port = port
        self.baud_rate = baud_rate
        self.name = name
        self.connection = None
        self.connected = False
        self.connect()

    def connect(self):
        try:
            self.connection = serial.Serial(self.port, self.baud_rate, timeout=1)
            self.connected = True
            logging.info(f"Connected to {self.name} on {self.port}")
        except serial.SerialException as e:
            logging.error(f"Failed to connect to {self.name} on {self.port}: {e}")
            self.connected = False

    def read_line(self):
        if self.connected and self.connection.in_waiting > 0:
            try:
                line = self.connection.readline().decode('utf-8', errors='ignore').strip()
                return line
            except Exception as e:
                logging.error(f"Error reading from {self.name}: {e}")
        return None

    def write(self, data):
        if self.connected:
            try:
                self.connection.write(data.encode())
            except Exception as e:
                logging.error(f"Error writing to {self.name}: {e}")

    def close(self):
        if self.connected:
            self.connection.close()
            self.connected = False
            logging.info(f"Closed connection to {self.name}")

# Instantiate SerialConnection objects
arduino = SerialConnection(ARDUINO_PORT, BAUD_RATE, "Arduino")
pro_micro = SerialConnection(PROMICRO_PORT, BAUD_RATE, "Pro Micro")

# ELM327 OBD-II adapter handler with reconnection logic
class ELM327Adapter:
    RECONNECT_INTERVAL = 5  # seconds

    def __init__(self, port):
        self.port = port
        self.connection = None
        self.connected = False
        self.connecting = False
        self.last_attempt_time = 0

    def connect(self):
        current_time = time.time()
        if self.connecting or (current_time - self.last_attempt_time) < self.RECONNECT_INTERVAL:
            return
        self.connecting = True
        self.last_attempt_time = current_time
        try:
            self.connection = obd.Async(portstr=self.port, protocol="3")  # ISO 9141-2 protocol
            self.connected = True
            logging.info(f"Connected to ELM327 adapter on {self.port}")

            # Start watching OBD-II commands
            self.connection.watch(obd.commands.COOLANT_TEMP)
            self.connection.watch(obd.commands.ENGINE_LOAD)
            self.connection.watch(obd.commands.INTAKE_TEMP)
            self.connection.watch(obd.commands.TIMING_ADVANCE)
            self.connection.start()
        except Exception as e:
            logging.error(f"Failed to connect to ELM327 adapter: {e}")
            self.connected = False
            if self.connection:
                self.connection.stop()
                self.connection = None
        finally:
            self.connecting = False

    def disconnect(self):
        if self.connected and self.connection is not None:
            self.connection.stop()
            self.connected = False
            self.connection = None
            logging.info("Disconnected from ELM327 adapter")

    def query(self, command):
        if self.connected and self.connection is not None:
            try:
                response = self.connection.query(command)
                return response
            except Exception as e:
                logging.error(f"Error querying ELM327 adapter: {e}")
                self.connected = False
                if self.connection:
                    self.connection.stop()
                    self.connection = None
        else:
            self.connect()
        return None

    def stop(self):
        self.disconnect()

elm327_adapter = ELM327Adapter(ELM327_PORT)

def kmh_to_mph(kmh):
    return kmh * 0.621371

def update_sensor_data():
    # Read data from Arduino
    line = arduino.read_line()
    if line:
        try:
            sensor_values = json.loads(line)
            process_sensor_data(sensor_values)
        except json.JSONDecodeError:
            logging.error(f"JSON decode error for line: {line}")

    # Read data from ELM327 adapter
    update_elm327_data()

    # Read data from Pro Micro
    line = pro_micro.read_line()
    if line and line == 'trip_reset':
        trip_manager.reset_trip()
        logging.info("Trip manager state reset")

def process_sensor_data(sensor_values):
    for key, value in sensor_values.items():
        if key == "FuelLevel":
            filtered_value = sensor_data.get_filtered_fuel_level(value)
            sensor_data.update("FuelLevel", filtered_value)
        elif key in ["RPM", "Latitude", "Longitude"]:
            sensor_data.update(key, value)
        elif key in sensor_data.data:
            sensor_data.update(key, value)
    # Update trip distance
    if "Latitude" in sensor_values and "Longitude" in sensor_values:
        lat = sensor_values["Latitude"]
        lon = sensor_values["Longitude"]
        sensor_data.update("Distance", trip_manager.update_trip(lat, lon))
    # Send RPM data to Pro Micro
    if pro_micro.connected:
        pro_micro.write(f"{sensor_data.data['RPM']}\n")

def update_elm327_data():
    if not elm327_adapter.connected:
        elm327_adapter.connect()
        if not elm327_adapter.connected:
            return  # Skip updating if still not connected
    commands = {
        'ELM_CoolantTemp': obd.commands.COOLANT_TEMP,
        'ELM_EngineLoad': obd.commands.ENGINE_LOAD,
        'ELM_IntakeTemp': obd.commands.INTAKE_TEMP,
        'ELM_TimingAdvance': obd.commands.TIMING_ADVANCE,
    }
    for key, command in commands.items():
        response = elm327_adapter.query(command)
        if response and not response.is_null():
            value = response.value.magnitude
            if 'temp' in key.lower():
                value = value * 9 / 5 + 32  # Convert to Fahrenheit
            sensor_data.update(key, value)
        else:
            logging.debug(f"No valid response for {key}")

# Drawing functions
def draw_text_with_unit(surface, value, unit, value_font, unit_font, color, position):
    value_surf = value_font.render(value, True, color)
    unit_surf = unit_font.render(unit, True, color) if unit else None
    total_width = value_surf.get_width() + (unit_surf.get_width() if unit_surf else 0)
    adjusted_position = (position[0] - total_width, position[1])
    surface.blit(value_surf, adjusted_position)
    if unit_surf:
        unit_position = (adjusted_position[0] + value_surf.get_width() + 5,
                         adjusted_position[1] + value_surf.get_height() - unit_surf.get_height())
        surface.blit(unit_surf, unit_position)

def draw_progress_bar(surface, value, max_value, position, size, background_image):
    width, height = size
    fill_width = int((value / max_value) * width)
    scaled_background = pygame.transform.scale(background_image, size)
    surface.blit(scaled_background, position)
    if fill_width < width:
        pygame.draw.rect(surface, BLACK, (position[0] + fill_width, position[1], width - fill_width, height))

def draw_rpm_bar(surface):
    rpm = sensor_data.data['RPM']
    max_rpm = 6800
    position = (0, SCREEN_HEIGHT - 130)
    size = (SCREEN_WIDTH, 130)
    draw_progress_bar(surface, rpm, max_rpm, position, size, RPM_BACKGROUND_IMAGE)

def draw_small_bars(surface):
    bars = [
        ('CoolantTemp', 205, (583, 113)),
        ('OilTemp', 220, (583, 256)),
    ]
    for key, max_value, position in bars:
        value = sensor_data.get_average(key)
        draw_progress_bar(surface, value, max_value, position, (150, 17), SMALL_BAR_IMAGE)

def draw_oil_pressure_bar(surface):
    value = sensor_data.get_average('Pressure')
    max_value = 100
    position = (583, 395)
    draw_progress_bar(surface, value, max_value, position, (150, 17), OIL_PRESSURE_BAR_IMAGE)

def draw_fuel_bar(surface):
    fuel_level = sensor_data.data['FuelLevel']
    max_fuel = 100.0
    # Adjusted fuel bar ratio to make it 25% larger
    fuel_bar_ratio = 1.0 / 5.6  # Increased size by 25%
    size = (int(930 * fuel_bar_ratio), int(218 * fuel_bar_ratio))
    position = (0, 0)
    width, height = size
    fill_width = int((fuel_level / max_fuel) * width)
    scaled_fuel_bar = pygame.transform.scale(FUEL_BAR_IMAGE, size)
    surface.blit(scaled_fuel_bar, position)
    # Draw the filled portion from left to right
    if fill_width > 0:
        surface.blit(scaled_fuel_bar, position, (0, 0, fill_width, height))
    # Cover the unfilled portion on the right
    if fill_width < width:
        pygame.draw.rect(surface, BLACK, (position[0] + fill_width, position[1], width - fill_width, height))
    fuel_percentage_text = f"{int(round(fuel_level))}%"
    percentage_font = FONTS['fuel_level']
    fuel_percentage_surf = percentage_font.render(fuel_percentage_text, True, WHITE)
    surface.blit(fuel_percentage_surf, (position[0] + width + 10,
                                        position[1] + (height // 2) - (fuel_percentage_surf.get_height() // 2)))

def draw_trip_text(surface):
    trip_distance = sensor_data.data['Distance']
    font = FONTS['trip']
    label_font = FONTS['unit']
    color = WHITE
    dark_gray_color = DARK_GRAY
    position = (865, 400)
    trip_label_surface = label_font.render("trip.", True, color)
    surface.blit(trip_label_surface, (position[0] - trip_label_surface.get_width() - 10, position[1]))
    trip_str = f"{trip_distance:05.1f}"
    x_offset = 0
    for i, digit in enumerate(trip_str):
        # TODO: This is where leading zeroes should be getting colored dark gay, but they are not.
        digit_color = dark_gray_color if digit == '0' and i < len(trip_str) - 1 else color
        digit_surf = font.render(digit, True, digit_color)
        surface.blit(digit_surf, (position[0] + x_offset, position[1]))
        x_offset += digit_surf.get_width()

def draw_rpm_text(surface):
    rpm = sensor_data.data['RPM']
    rpm_str = f"{rpm:04d}"
    leading_zero_color = GRAY if rpm < 1000 else WHITE
    position = (15, 461)
    font = FONTS['rpm']
    leading_zero_surf = font.render(rpm_str[0], True, leading_zero_color)
    surface.blit(leading_zero_surf, position)
    remaining_digits_surf = font.render(rpm_str[1:], True, WHITE)
    surface.blit(remaining_digits_surf, (position[0] + leading_zero_surf.get_width(), position[1]))
    rpm_label_font = pygame.font.Font(FONT_PATHS['rpm'], 30)
    rpm_label_surf = rpm_label_font.render("RPM.", True, GRAY)
    surface.blit(rpm_label_surf, (position[0] + 156, position[1] + 34))

def draw_speed_text(surface):
    speed = int(kmh_to_mph(sensor_data.get_average('Speed')))
    speed_str = f"{speed:03d}"
    leading_zero_color = DARK_GRAY if speed < 100 else WHITE
    position = (865, -1)
    font = FONTS['speed']
    leading_zero_surf = font.render(speed_str[0], True, leading_zero_color)
    surface.blit(leading_zero_surf, position)
    remaining_digits_surf = font.render(speed_str[1:], True, WHITE)
    surface.blit(remaining_digits_surf, (position[0] + leading_zero_surf.get_width(), position[1]))
    # Optionally, display the unit "mph" somewhere if desired

def draw_text_elements(surface):
    elements = {
        "pressure": {
            "value": f"{sensor_data.get_average('Pressure'):.1f}",
            "unit": "psi",
            "value_font": FONTS['pressure_coolant_oil'],
            "unit_font": FONTS['unit'],
            "position": (700, 343),
        },
        "coolant_temp": {
            "value": f"{int(sensor_data.get_average('CoolantTemp'))}",
            "unit": "°F",
            "value_font": FONTS['pressure_coolant_oil'],
            "unit_font": FONTS['unit'],
            "position": (670, 60),
        },
        "oil_temp": {
            "value": f"{int(sensor_data.get_average('OilTemp'))}",
            "unit": "°F",
            "value_font": FONTS['pressure_coolant_oil'],
            "unit_font": FONTS['unit'],
            "position": (670, 205),
        },
        "elm_coolant_temp": {
            "value": f"{sensor_data.data['ELM_CoolantTemp']:.1f}",
            "unit": "°F",
            "value_font": FONTS['elm']['coolant_temp'],
            "unit_font": FONTS['elm']['unit'],
            "position": (964, 160),
        },
        "elm_intake_temp": {
            "value": f"{sensor_data.data['ELM_IntakeTemp']:.1f}",
            "unit": "°F",
            "value_font": FONTS['elm']['intake_temp'],
            "unit_font": FONTS['elm']['unit'],
            "position": (965, 218),
        },
        "elm_timing_advance": {
            "value": f"{sensor_data.data['ELM_TimingAdvance']:.1f}",
            "unit": "°",
            "value_font": FONTS['elm']['timing_advance'],
            "unit_font": FONTS['elm']['unit'],
            "position": (960, 277),
        },
        "elm_engine_load": {
            "value": f"{sensor_data.data['ELM_EngineLoad']:.1f}",
            "unit": "%",
            "value_font": FONTS['elm']['engine_load'],
            "unit_font": FONTS['elm']['unit'],
            "position": (965, 335),
        },
    }
    for key, settings in elements.items():
        draw_text_with_unit(
            surface,
            settings["value"],
            settings["unit"],
            settings["value_font"],
            settings["unit_font"],
            WHITE,
            settings["position"]
        )

def display_data():
    screen.blit(BACKGROUND_IMAGE, (0, 0))
    draw_rpm_bar(screen)
    draw_small_bars(screen)
    draw_oil_pressure_bar(screen)
    draw_fuel_bar(screen)
    draw_trip_text(screen)
    draw_rpm_text(screen)
    draw_speed_text(screen)
    draw_text_elements(screen)
    pygame.display.update()

def show_loading_screen():
    screen.blit(LOADING_SCREEN_IMAGE, (0, 0))
    pygame.display.update()

def initialize_system():
    # Initialize serial connections
    global arduino, pro_micro, elm327_adapter

    # Re-initialize SerialConnection instances to ensure they are connected
    arduino = SerialConnection(ARDUINO_PORT, BAUD_RATE, "Arduino")
    pro_micro = SerialConnection(PROMICRO_PORT, BAUD_RATE, "Pro Micro")
    elm327_adapter = ELM327Adapter(ELM327_PORT)

    # Simulate initialization delay (adjusted to 3.5 seconds)
    time.sleep(3.5)

def main():
    # Display loading screen
    show_loading_screen()

    # Perform initializations
    initialize_system()

    # Main loop
    running = True
    while running:
        try:
            for event in pygame.event.get():
                if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                    running = False

            update_sensor_data()
            display_data()
            clock.tick(60)  # Limit to 60 FPS

        except Exception as e:
            logging.error(f"An error occurred in the main loop: {e}")
            time.sleep(1)  # Optional: pause before continuing

    # Cleanup
    arduino.close()
    pro_micro.close()
    elm327_adapter.stop()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
