import sys
import serial
import pygame
from pygame.locals import *
import math
import obd
import time

# Serial port configuration
ARDUINO_PORT = '/dev/ttyACM0'  # Port for Arduino Uno
PROMICRO_PORT = '/dev/ttyACM1'  # Port for Pro Micro controlling LEDs
ELM327_PORT = '/dev/ttyUSB0'  # Port for ELM327 adapter
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
rpm_background = pygame.image.load('/home/cleanish/r4/dark mode/rpm_wave.png')
rpm_bar_height = 125  # Height for the RPM bar
rpm_background = pygame.transform.scale(rpm_background, (screen_width, rpm_bar_height))

# Load the small bar image for coolant, oil temperature, and oil pressure bars (no distortion)
small_bar_background = pygame.image.load('/home/cleanish/r4/dark mode/bar_etc_dark.png')
small_bar_size = (150, 15)  # Size for the small bars

# Create a mirrored version of the small bar image for the oil pressure bar
mirrored_small_bar_background = pygame.transform.flip(small_bar_background, True, False)

# Load the custom fonts
custom_font_path = '/home/cleanish/r4/ZeroAthletics.ttf'
rpm_font_path = '/home/cleanish/r4/ZeroAthletics.ttf'
elm_font_path = '/home/cleanish/r4/Orbitron-Black.ttf'  # Font for ELM values
pressure_coolant_oil_font_path = '/home/cleanish/r4/ZeroAthletics.ttf'  # Font for pressure, coolant temp, oil temp

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
rpm_font_size = 60  # Smaller RPM font size
speed_font_size = 75  # Smaller Speed font size
units_font_size = 20  # Smaller font size for units

# Load custom fonts
custom_value_font = pygame.font.Font(custom_font_path, values_font_size)
custom_rpm_font = pygame.font.Font(rpm_font_path, rpm_font_size)
custom_speed_font = pygame.font.Font(rpm_font_path, speed_font_size)
custom_unit_font = pygame.font.Font(custom_font_path, units_font_size)

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
        "position": (695, 340),  # Fixed on the right, will expand left
    },
    "coolant_temp": {
        "title": "",
        "value": lambda: f"{int(get_average(data['CoolantTemp']))}",  # Remove decimal for coolant temp
        "unit": "f.",
        "value_font": pressure_coolant_oil_font,  # Use the new font for coolant temp
        "unit_font": custom_unit_font,
        "color": white,
        "position": (665, 60),  # Fixed on the right, will expand left
    },
    "oil_temp": {
        "title": "",
        "value": lambda: f"{int(get_average(data['OilTemp']))}",  # Remove decimal for oil temp
        "unit": "f.",
        "value_font": pressure_coolant_oil_font,  # Use the new font for oil temp
        "unit_font": custom_unit_font,
        "color": white,
        "position": (665, 205),  # Fixed on the right, will expand left
    },
    "speed": {
        "title": "",
        "value": lambda: int(kmh_to_mph(get_average(data['Speed']))),
        "value_font": custom_speed_font,
        "unit_font": None,  # No unit for speed
        "color": white,
        "position": (830 , 15),  # You can adjust this as needed
    },
    "rpm": {
        "title": "",
        "value": lambda: data['RPM'],
        "value_font": custom_rpm_font,
        "unit_font": None,  # No unit for RPM
        "color": white,
        "position": (15, 460),  # You can adjust this as needed
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
        "position": (940, 276),
    },
    "elm_engine_load": {
        "title": "Engine Load",
        "value": lambda: f"{data['ELM_EngineLoad']:.1f}",
        "unit": "%",
        "value_font": elm_engine_load_font,  # Adjusted font size
        "unit_font": elm_unit_font,
        "color": white,
        "position": (948, 327),
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
    surface.blit(rpm_label_surf, (position[0] + 145, position[1]+ 30))  # Adjust as necessary

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

# Helper function to draw a mirrored color bar for oil pressure using the new small bar image
def draw_mirrored_color_bar(surface, value, max_value, position, size):
    width, height = size
    fill_width = int((value / max_value) * width)

    # Scale the mirrored small bar image to match the size of the small bar
    scaled_background = pygame.transform.scale(mirrored_small_bar_background, size)
    
    # Blit the full background image onto the surface
    surface.blit(scaled_background, position)

    # Draw a rectangle to cover the unfilled portion of the small bar
    if fill_width < width:
        pygame.draw.rect(surface, black, (position[0] + fill_width, position[1], width - fill_width, height))

# Function to get the average of the last N samples
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

# Update the sensor data
def update_sensor_data():
    if arduino_connected and arduino.in_waiting > 0:
        try:
            line = arduino.readline().decode('utf-8').strip()
            print(line)
            sensor_data = eval(line)
            for key, value in sensor_data.items():
                if key in data:
                    if key == "RPM":
                        data[key] = value
                    else:
                        data[key].append(value)
                        if len(data[key]) > 25:
                            data[key].pop(0)
            # Send RPM value to Pro Micro
            if pro_micro_connected:
                pro_micro.write(f"{data['RPM']}\n".encode())
        except Exception as e:
            print(f'Error: {e}')

    if elm327_connected:
        try:
            response_coolant_temp = elm327_connection.query(obd.commands.COOLANT_TEMP)
            response_engine_load = elm327_connection.query(obd.commands.ENGINE_LOAD)
            response_intake_temp = elm327_connection.query(obd.commands.INTAKE_TEMP)
            response_maf = elm327_connection.query(obd.commands.TIMING_ADVANCE)

            if not response_coolant_temp.is_null():
                data['ELM_CoolantTemp'] = response_coolant_temp.value.magnitude * 9 / 5 + 32  # Convert from Celsius to Fahrenheit
            if not response_engine_load.is_null():
                data['ELM_EngineLoad'] = response_engine_load.value.magnitude
            if not response_intake_temp.is_null():
                data['ELM_IntakeTemp'] = response_intake_temp.value.magnitude * 9 / 5 + 32  # Convert from Celsius to Fahrenheit
            if not response_timing_advance.is_null():
                data['ELM_TimingAdvance'] = response_timing_advance.value.magnitude  # Update Timing Advance value
        except Exception as e:
            print(f'Error fetching OBD-II data: {e}')

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
    draw_small_bar(screen, get_average(data['CoolantTemp']), 205, (583, 114), small_bar_size)
    draw_small_bar(screen, get_average(data['OilTemp']), 220, (583, 257), small_bar_size)
   
    # Draw mirrored color bar for oil pressure using the new small bar image
    draw_mirrored_color_bar(screen, get_average(data['Pressure']), 100, (583, 395), small_bar_size)

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

    pygame.display.update()  # Update the display

# Main loop
def main():
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                running = False

        # Update sensor data
        update_sensor_data()

        # Display updated data
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
