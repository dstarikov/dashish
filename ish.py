import sys
import serial
import pygame
from pygame.locals import *
import math
import obd
import time
import json
import os
#privet pidr
# Trip manager class to handle trip calculations
class TripManager:
    MILES_FILE = "total_miles.txt"

    def __init__(self):
        self.total_distance = self.load_total_miles_from_file()  # Load saved total miles
        self.last_update_time = time.time()  # Track time for 2.5-second updates
        self.last_lat = None
        self.last_lon = None
        

    def reset_trip(self):
        self.total_distance = 0.0
        self.last_lat = None
        self.last_lon = None
        self.save_total_miles_to_file(self.total_distance)  # Save reset state to file

    def update_trip(self, current_lat, current_lon):
        if self.last_lat is not None and self.last_lon is not None:
            # Calculate the distance from the last point to the current point
            distance = calculate_distance(self.last_lat, self.last_lon, current_lat, current_lon)
            self.total_distance += distance

        # Update the last known coordinates
        self.last_lat = current_lat
        self.last_lon = current_lon

        # Save the updated total distance to file
        self.save_total_miles_to_file(self.total_distance)

        return self.get_total_distance()

    def get_total_distance(self):
        return self.total_distance

    def load_total_miles_from_file(self):
        if os.path.exists(self.MILES_FILE):
            try:
                with open(self.MILES_FILE, "r") as file:
                    return float(file.read().strip())
            except (ValueError, IOError) as e:
                print(f"Error reading total miles from file: {e}")
                return 0.0
        return 0.0  # If file doesn't exist, return 0.0

    def save_total_miles_to_file(self, total_miles):
        try:
            with open(self.MILES_FILE, "w") as file:
                file.write(f"{total_miles}")
        except IOError as e:
            print(f"Error writing total miles to file: {e}")
    

# Function to calculate distance between two lat/long points using the Haversine formula
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 3958.8  # Radius of the Earth in miles. Use 6371 for kilometers.
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c  # Distance in miles
    return distance

# Instantiate the trip manager
trip_manager = TripManager()

# Function to fetch GPS data from Arduino
def get_gps_data_from_arduino():
    if arduino_connected and arduino.in_waiting > 0:
        try:
            line = arduino.readline().decode('utf-8').strip()
            gps_data = json.loads(line)  # Assuming the data is JSON formatted
            current_lat = gps_data.get('Latitude', None)
            current_lon = gps_data.get('Longitude', None)
            return current_lat, current_lon
        except json.JSONDecodeError:
            print(f"Error decoding GPS data: {line}")
            return None, None
    return None, None

# Function to update GPS data and manage the trip
# def update_gps_and_trip():
#     # Simulating GPS data (replace this with actual GPS data in your setup)
#     gps_data = {"lat": 37.7749, "lon": -122.4194}  # Example coordinates (San Francisco)
#     if gps_data:
#         current_lat = gps_data['lat']
#         current_lon = gps_data['lon']
        
#         # Update the trip distance every 2.5 seconds
#         trip_manager.update_trip(current_lat, current_lon)
        
#         return trip_manager.get_total_distance()

# Function to update GPS data and manage the trip
def update_gps_and_trip():
    current_lat, current_lon = get_gps_data_from_arduino()  # Fetch from Arduino
    if current_lat is not None and current_lon is not None:
        # Update the trip distance every 2.5 seconds
        trip_manager.update_trip(current_lat, current_lon)
    return trip_manager.get_total_distance()



# Helper function to draw the Trip Distance value with leading zero logic and label
def draw_trip_text(surface, trip_distance, font, label_font, color, dark_gray_color, position):
    # Draw the "Trip" label on the left side of the number value
    trip_label_surface = label_font.render("trip.", True, color)
    surface.blit(trip_label_surface, (position[0] - trip_label_surface.get_width() - 10, position[1]))

    # Format the trip distance as a 4-digit number with leading zeros
    trip_str = f"{trip_distance:05.1f}"

    # Logic to render each digit, ensuring leading zeros are gray and counting digits are white
    x_offset = 0
    for i, digit in enumerate(trip_str):
        if digit == '0' and i < len(trip_str) - 1:  # Leading zeros are dark gray, except the last zero before non-zero digits
            digit_surf = font.render(digit, True, dark_gray_color)
        else:
            digit_surf = font.render(digit, True, color)  # Non-zero or the rightmost zero

        # Render the digit and adjust position for the next one
        surface.blit(digit_surf, (position[0] + x_offset, position[1]))
        x_offset += digit_surf.get_width()

# Serial port configuration
ARDUINO_PORT = '/dev/arduino'  # sensor data
PROMICRO_PORT = '//dev/pico'  # rpm light
ELM327_PORT = '/dev/ch340'  # obd2 elm327 adapter
BAUD_RATE = 115200  # Baud rate for both serial devices

# Attempt to connect to the Arduino Uno serial port
try:
    arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
    arduino_connected = True
except serial.SerialException:
    arduino_connected = False

# Attempt to connect to the Pro Micro serial port
try:
    pro_micro = serial.Serial(PROMICRO_PORT, BAUD_RATE, timeout=1)
    pro_micro_connected = True
except serial.SerialException:
    pro_micro_connected = False

# Connect to the ELM327 OBD-II adapter
try:
    elm327_connection = obd.Async(portstr=ELM327_PORT, protocol="3")  # ISO 9141-2 protocol
    elm327_connected = True

    # Start watching OBD-II commands
    elm327_connection.watch(obd.commands.COOLANT_TEMP)
    elm327_connection.watch(obd.commands.ENGINE_LOAD)
    elm327_connection.watch(obd.commands.INTAKE_TEMP)
    elm327_connection.watch(obd.commands.MAF)
    elm327_connection.watch(obd.commands.TIMING_ADVANCE)
    elm327_connection.start()
except Exception as e:
    print(f"Failed to connect to ELM327 adapter: {e}")
    elm327_connected = False

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption('Vehicle Data Display')

# Hide the cursor
pygame.mouse.set_visible(False)

# Get screen size
screen_width, screen_height = screen.get_size()

# Load and scale the background image
background = pygame.image.load('/home/cleanish/r4/skin1.png')
background = pygame.transform.scale(background, (screen_width, screen_height))

# Load and scale the RPM bar background image
rpm_background = pygame.image.load('/home/cleanish/dashish/graphics/rpm_wave2.png')
rpm_bar_height = 130  # Height for the RPM bar
rpm_background = pygame.transform.scale(rpm_background, (screen_width, rpm_bar_height))

# Load the small bar image for coolant, oil temperature, and oil pressure bars (no distortion)
small_bar_background = pygame.image.load('/home/cleanish/r4/dark mode/bar_etc_dark.png')
small_bar_size = (150, 17)  # Size for the small bars

# Load a new image for the oil pressure bar
oil_pressure_bar_background = pygame.image.load('/home/cleanish/r4/dark mode/bar_op_dark.png')

# Load the custom fonts
custom_font_path = '/home/cleanish/r4/ZeroAthletics.ttf'
rpm_font_path = '/home/cleanish/r4/ZeroAthletics.ttf'
elm_font_path = '/home/cleanish/r4/Orbitron-Black.ttf'  # Font for ELM values
pressure_coolant_oil_font_path = '/home/cleanish/r4/ZeroAthletics.ttf'  # Font for pressure, coolant temp, oil temp
custom_unit_font = '/home/cleanish/dash_/Fonts/Orbitron-Black.ttf'
custom_trip_font = '/home/cleanish/dash_/Fonts/Orbitron-Black.ttf'

# Colors
white = (255, 255, 255)
black = (0, 0, 0)
gray = (169, 169, 169)  # Dark gray color for the leading zero in RPM
dark_gray = (50, 50, 50)  # Much darker gray for the leading zero in speed

clock = pygame.time.Clock()

# Initialize variables
data = {
    "Pressure": [0] * 100,
    "CoolantTemp": [0] * 100,
    "OilTemp": [0] * 100,
    "Speed": [0] * 25,
    "Latitude": 0.0,
    "Longitude": 0.0,
    "Distance": 0.0,
    "RPM": 0,  # Direct RPM value as an integer
    "Ax": [0] * 25,
    "Ay": [0] * 25,
    "Az": [0] * 25,
    "Gx": [0] * 25,
    "Gy": [0] * 25,
    "Gz": [0] * 25,
    "ELM_CoolantTemp": 0,
    "ELM_IntakeTemp": 0,
    "ELM_TimingAdvance": 0,
    "ELM_EngineLoad": 0
}

# Variables for sweeping values (adjusted font sizes)
values_font_size = 45  # Smaller value font size
rpm_font_size = 65  # Smaller RPM font size
speed_font_size = 80  # Smaller Speed font size
units_font_size = 20  # Smaller font size for units
trip_font_size = 25  # Adjust this value as needed for the desired size

# Load custom fonts
custom_value_font = pygame.font.Font(custom_font_path, values_font_size)
custom_rpm_font = pygame.font.Font(rpm_font_path, rpm_font_size)
custom_speed_font = pygame.font.Font(rpm_font_path, speed_font_size)
custom_unit_font = pygame.font.Font(custom_font_path, units_font_size)
custom_trip_font = pygame.font.Font(custom_trip_font, trip_font_size )

# Define custom sizes for each ELM value
elm_coolant_temp_font_size = 25
elm_intake_temp_font_size = 25
elm_maf_font_size = 25
elm_engine_load_font_size = 25

# Load fonts for each ELM value with separate sizes
elm_coolant_temp_font = pygame.font.Font(elm_font_path, elm_coolant_temp_font_size)
elm_intake_temp_font = pygame.font.Font(elm_font_path, elm_intake_temp_font_size)
elm_maf_font = pygame.font.Font(elm_font_path, elm_maf_font_size)
elm_engine_load_font = pygame.font.Font(elm_font_path, elm_engine_load_font_size)
elm_unit_font = pygame.font.Font(elm_font_path, units_font_size)  # ELM-specific unit font
pressure_coolant_oil_font = pygame.font.Font(pressure_coolant_oil_font_path, values_font_size)  # New font for specific values

# Text elements with individual settings
text_elements = {
    "pressure": {
        "title": "",
        "value": lambda: f"{get_average(data['Pressure']):.1f}",  # Keep the decimal for pressure
        "unit": "psi.",
        "value_font": pressure_coolant_oil_font,  # Use the new font for pressure
        "unit_font": custom_unit_font,
        "color": white,
        "position": (700, 343),  # Fixed on the right, will expand left
    },
    "coolant_temp": {
        "title": "",
        "value": lambda: f"{int(get_average(data['CoolantTemp']))}",  # Remove decimal for coolant temp
        "unit": "f.",
        "value_font": pressure_coolant_oil_font,  # Use the new font for coolant temp
        "unit_font": custom_unit_font,
        "color": white,
        "position": (670, 60),  # Fixed on the right, will expand left
    },
    "oil_temp": {
        "title": "",
        "value": lambda: f"{int(get_average(data['OilTemp']))}",  # Remove decimal for oil temp
        "unit": "f.",
        "value_font": pressure_coolant_oil_font,  # Use the new font for oil temp
        "unit_font": custom_unit_font,
        "color": white,
        "position": (670, 205),  # Fixed on the right, will expand left
    },
    "speed": {
        "title": "",
        "value": lambda: int(kmh_to_mph(get_average(data['Speed']))),
        "value_font": custom_speed_font,
        "unit_font": None,  # No unit for speed
        "color": white,
        "position": (830 , 20),  # You can adjust this as needed
    },
    "rpm": {
        "title": "",
        "value": lambda: data['RPM'],
        "value_font": custom_rpm_font,
        "unit_font": None,  # No unit for RPM
        "color": white,
        "position": (15, 461),  # You can adjust this as needed
    },
    "elm_coolant_temp": {
        "title": "Coolant Temp",
        "value": lambda: f"{data['ELM_CoolantTemp']:.1f}",
        "unit": "f.",
        "value_font": elm_coolant_temp_font,  # Adjusted font size
        "unit_font": elm_unit_font,
        "color": white,
        "position": (945, 160),
    },
    "elm_intake_temp": {
        "title": "Intake Temp",
        "value": lambda: f"{data['ELM_IntakeTemp']:.1f}",
        "unit": "f.",
        "value_font": elm_intake_temp_font,  # Adjusted font size
        "unit_font": elm_unit_font,
        "color": white,
        "position": (945, 218),
    },
    "elm_timing_advance": {
        "title": "Timing Advance",
        "value": lambda: f"{data['ELM_TimingAdvance']:.1f}",
        "unit": "°",
        "value_font": elm_maf_font,  # Use the same font as before
        "unit_font": elm_unit_font,
        "color": white,
        "position": (940, 277),
    },
    "elm_engine_load": {
        "title": "Engine Load",
        "value": lambda: f"{data['ELM_EngineLoad']:.1f}",
        "unit": "%",
        "value_font": elm_engine_load_font,  # Adjusted font size
        "unit_font": elm_unit_font,
        "color": white,
        "position": (948, 335),
    }
}

# Helper function to update the display text
def draw_text_with_unit(surface, value, unit, value_font, unit_font, color, position):
    # Render the value and unit separately
    value_surf = value_font.render(value, True, color)
    unit_surf = unit_font.render(unit, True, color) if unit_font is not None and unit else None
    
    # Calculate the total width of the text (value + unit)
    total_width = value_surf.get_width() + (unit_surf.get_width() if unit_surf else 0)
    
    # Adjust the x-position so that the text expands to the left, staying fixed on the right
    adjusted_position = (position[0] - total_width, position[1])
    
    # Blit the value surface
    surface.blit(value_surf, adjusted_position)
    
    # Blit the unit surface if available
    if unit_surf:
        surface.blit(unit_surf, (adjusted_position[0] + value_surf.get_width() + 5, adjusted_position[1] + value_surf.get_height() - unit_surf.get_height()))

# Helper function to draw the RPM value with leading zero logic
def draw_rpm_text(surface, rpm, font, color, gray_color, position):
    rpm_str = f"{rpm:04d}"
    leading_zero_color = gray_color if rpm < 1000 else color

    # Render leading zero
    leading_zero_surf = font.render(rpm_str[0], True, leading_zero_color)
    surface.blit(leading_zero_surf, position)

    # Render the rest of the digits
    remaining_digits_surf = font.render(rpm_str[1:], True, color)
    surface.blit(remaining_digits_surf, (position[0] + leading_zero_surf.get_width(), position[1]))

    # Draw the "RPM." text separately, ensuring it does not move
    rpm_label_font = pygame.font.Font(rpm_font_path, 30)  # Smaller font size for "RPM."
    rpm_label_surf = rpm_label_font.render("RPM.", True, gray)
    surface.blit(rpm_label_surf, (position[0] + 156, position[1]+ 34))  # Adjust as necessary

# Helper function to draw the Speed value with leading zero logic
def draw_speed_text(surface, speed, font, color, dark_gray_color, position):
    speed_str = f"{speed:03d}"  # Format speed with leading zeros
    leading_zero_color = dark_gray_color if speed < 100 else color  # Darken leading zero only if speed < 100

    # Render leading zero
    leading_zero_surf = font.render(speed_str[0], True, leading_zero_color)
    surface.blit(leading_zero_surf, position)

    # Render the rest of the digits
    remaining_digits_surf = font.render(speed_str[1:], True, color)
    surface.blit(remaining_digits_surf, (position[0] + leading_zero_surf.get_width(), position[1]))

# Helper function to draw the RPM progress bar (matching small bars style)
def draw_rpm_bar(surface, rpm, max_rpm, position, size):
    width, height = size
    fill_width = int((rpm / max_rpm) * width)

    # Scale the RPM background image to match the size of the RPM bar
    scaled_rpm_background = pygame.transform.scale(rpm_background, size)
    
    # Blit the full background image onto the surface
    surface.blit(scaled_rpm_background, position)
    
    # Draw a rectangle to cover the unfilled portion of the RPM bar
    if fill_width < width:
        pygame.draw.rect(surface, black, (position[0] + fill_width, position[1], width - fill_width, height))

# Helper function to draw small progress bars using the new small bar image
def draw_small_bar(surface, value, max_value, position, size):
    width, height = size
    fill_width = int((value / max_value) * width)

    # Scale the small bar image to match the size of the small bar
    scaled_background = pygame.transform.scale(small_bar_background, size)
    
    # Blit the full background image onto the surface
    surface.blit(scaled_background, position)

    # Draw a rectangle to cover the unfilled portion of the small bar
    if fill_width < width:
        pygame.draw.rect(surface, black, (position[0] + fill_width, position[1], width - fill_width, height))

# Helper function to draw a color bar for oil pressure using the new small bar image
def draw_oil_pressure_bar(surface, value, max_value, position, size):
    width, height = size
    fill_width = int((value / max_value) * width)

    # Scale the new image to match the size of the bar
    scaled_background = pygame.transform.scale(oil_pressure_bar_background, size)
    
    # Blit the full background image onto the surface
    surface.blit(scaled_background, position)

    # Draw a rectangle to cover the unfilled portion of the small bar
    if fill_width < width:
        pygame.draw.rect(surface, black, (position[0] + fill_width, position[1], width - fill_width, height))

# Function to get the average of the last N samples
def display_data():
    # Draw the background image
    screen.blit(background, (0, 0))

def get_average(values):
    return sum(values) / len(values)

def format_to_digits(number, digits=3):
    integer_part = int(number)
    formatted_number = f"{integer_part:0{digits}d}"
    return formatted_number

def kmh_to_mph(kmh, digits=3):
    mph = kmh * 0.621371
    if digits is not None and digits > 0:
        return format_to_digits(int(mph), digits)
    else:
        return int(mph)

def update_sensor_data():
    if arduino_connected and arduino.in_waiting > 0:
        try:
            line = arduino.readline().decode('utf-8').strip()
            print(line)
            sensor_data = json.loads(line)
            for key, value in sensor_data.items():
                if key in data:
                    if key == "RPM" or key == "Latitude" or key == "Longitude":
                        data[key] = value
                    else:
                        data[key].append(value)
                        if len(data[key]) > 25:
                            data[key].pop(0)
            if "Latitude" in sensor_data and "Longitude" in sensor_data:
                data["Distance"] = trip_manager.update_trip(sensor_data["Latitude"], sensor_data["Longitude"])
            if pro_micro_connected:
                pro_micro.write(f"{data['RPM']}\n".encode())
        except json.JSONDecodeError:
            print(f'Error: Failed to decode JSON from Arduino line: {line}')
        except Exception as e:
            print(f'Error: {e}')

    if elm327_connected:
        try:
            # Query all OBD-II data at once
            response_coolant_temp = elm327_connection.query(obd.commands.COOLANT_TEMP)
            response_engine_load = elm327_connection.query(obd.commands.ENGINE_LOAD)
            response_intake_temp = elm327_connection.query(obd.commands.INTAKE_TEMP)
            response_timing_advance = elm327_connection.query(obd.commands.TIMING_ADVANCE)

            # Check and process each response
            if response_coolant_temp and not response_coolant_temp.is_null():
                data['ELM_CoolantTemp'] = response_coolant_temp.value.magnitude * 9 / 5 + 32  # Convert from Celsius to Fahrenheit
            if response_engine_load and not response_engine_load.is_null():
                data['ELM_EngineLoad'] = response_engine_load.value.magnitude
            if response_intake_temp and not response_intake_temp.is_null():
                data['ELM_IntakeTemp'] = response_intake_temp.value.magnitude * 9 / 5 + 32  # Convert from Celsius to Fahrenheit
            if response_timing_advance and not response_timing_advance.is_null():
                data['ELM_TimingAdvance'] = response_timing_advance.value.magnitude  # Update Timing Advance value
        except Exception as e:
            print(f'Error fetching OBD-II data: {e}')

    if pro_micro_connected and pro_micro.in_waiting > 0:
        try:
            line = pro_micro.readline().decode('utf-8').strip()
            print(line)
            if line == 'trip_reset':
                trip_manager.reset_trip()
                print("Reset the trip_manager state")
        except Exception as e:
            print(f'Error: {e}')

# Main display function
def display_data():
    # Draw the background image
    screen.blit(background, (0, 0))

    # Draw the RPM progress bar using the new RPM bar image
    draw_rpm_bar(screen, data["RPM"], 6800, (0, screen.get_height() - rpm_bar_height), (screen.get_width(), rpm_bar_height))

    # Draw each text element based on its settings
    for key, settings in text_elements.items():
        if key == "rpm":
            draw_rpm_text(
                screen,
                settings["value"](),
                settings["value_font"],
                settings["color"],
                dark_gray,
                settings["position"]
            )
        elif key == "speed":
            draw_speed_text(
                screen,
                settings["value"](),
                settings["value_font"],
                settings["color"],
                dark_gray,
                settings["position"]
            )
        else:
            draw_text_with_unit(
                screen,
                settings["value"](),
                settings.get("unit", ""),
                settings["value_font"],
                settings["unit_font"],
                settings["color"],
                settings["position"]
            )

    # Draw small progress bars for coolant and oil temperature using the new small bar image
    draw_small_bar(screen, get_average(data['CoolantTemp']), 205, (583, 113), small_bar_size)
    draw_small_bar(screen, get_average(data['OilTemp']), 220, (583, 256), small_bar_size)
   
    # Draw mirrored color bar for oil pressure using the new small bar image
    draw_oil_pressure_bar(screen, get_average(data['Pressure']), 100, (583, 395), small_bar_size)

   # Draw the trip distance on the screen with the smaller font
    draw_trip_text(screen, data["Distance"], custom_trip_font, custom_unit_font, white, dark_gray, (865, 400))

    pygame.display.update()  # Update the display

    # Display additional ELM327 data if connected
    if elm327_connected:
        draw_text_with_unit(
            screen,
            text_elements['elm_coolant_temp']['value'](),
            text_elements['elm_coolant_temp']['unit'],
            text_elements['elm_coolant_temp']['value_font'],
            text_elements['elm_coolant_temp']['unit_font'],
            text_elements['elm_coolant_temp']['color'],
            text_elements['elm_coolant_temp']['position']
        )
        draw_text_with_unit(
            screen,
            text_elements['elm_intake_temp']['value'](),
            text_elements['elm_intake_temp']['unit'],
            text_elements['elm_intake_temp']['value_font'],
            text_elements['elm_intake_temp']['unit_font'],
            text_elements['elm_intake_temp']['color'],
            text_elements['elm_intake_temp']['position']
        )
        draw_text_with_unit(
            screen,
            text_elements['elm_timing_advance']['value'](),
            text_elements['elm_timing_advance']['unit'],
            text_elements['elm_timing_advance']['value_font'],
            text_elements['elm_timing_advance']['unit_font'],
            text_elements['elm_timing_advance']['color'],
            text_elements['elm_timing_advance']['position']
        )
        draw_text_with_unit(
            screen,
            text_elements['elm_engine_load']['value'](),
            text_elements['elm_engine_load']['unit'],
            text_elements['elm_engine_load']['value_font'],
            text_elements['elm_engine_load']['unit_font'],
            text_elements['elm_engine_load']['color'],
            text_elements['elm_engine_load']['position']
        )

# Main loop
def main():
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                running = False

        # Update sensor data
        update_sensor_data()

        # Display updated data including trip distance
        display_data()

        # Update the display
        pygame.display.update()

        # Cap the frame rate
        clock.tick(60)  # 60 FPS

    if elm327_connected:
        elm327_connection.stop()

    pygame.quit()
    sys.exit()

# Run the main loop
if __name__ == "__main__":
    main()
