import sys
import pygame
from serial_com import SerialHandler, ARDUINO_PORT, PROMICRO_PORT, ELM327_PORT, BAUD_RATE
from obd_com import OBDHandler
from graphics import GraphicsHandler

# Data structure to hold sensor data
data = {
    "Pressure": [0] * 100,
    "CoolantTemp": [0] * 100,
    "OilTemp": [0] * 100,
    "Speed": [0] * 25,
    "RPM": 0,
    "ELM_CoolantTemp": 0,
    "ELM_IntakeTemp": 0,
    "ELM_TimingAdvance": 0,
    "ELM_EngineLoad": 0
}

def init_system():
    pygame.init()
    pygame.font.init()

    # Initialize Serial Handlers for Arduino and Pro Micro
    serial_arduino = SerialHandler(ARDUINO_PORT, BAUD_RATE)
    serial_pro_micro = SerialHandler(PROMICRO_PORT, BAUD_RATE)

    # Initialize OBD-II handler (ELM327)
    obd_handler = OBDHandler(ELM327_PORT)

    # Initialize graphics handler
    graphics = GraphicsHandler(
        '/home/cleanish/dash_ish/Graphics/dark mode/skin_dark.png',
        '/home/cleanish/dash_ish/Graphics/dark mode/rpm_wave.png',
        '/home/cleanish/dash_ish/Graphics/dark mode/bar_etc_dark.png'
    )

    return graphics, serial_arduino, serial_pro_micro, obd_handler

def update_sensor_data(serial_arduino, serial_pro_micro, obd_handler):
    # Priority 1 - Arduino Data Handling
    if serial_arduino.is_connected():
        line = serial_arduino.read_data()
        if line:
            try:
                sensor_data = eval(line)
                for key, value in sensor_data.items():
                    if key in data:
                        if key == "Speed":
                            # Convert the speed from km/h to mph
                            value = [v * 0.621371 for v in value]
                        if key == "RPM":
                            data[key] = value
                        else:
                            data[key].append(value)
                            if len(data[key]) > 25:
                                data[key].pop(0)
            except Exception as e:
                print(f"Error processing Arduino sensor data: {e}")

    # Priority 2 - ELM327 Data Handling (OBD-II)
    if obd_handler.is_connected():
        try:
            obd_data = obd_handler.query_data()
            if obd_data:
                data['ELM_CoolantTemp'] = obd_data.get('coolant_temp', data['ELM_CoolantTemp'])
                data['ELM_EngineLoad'] = obd_data.get('engine_load', data['ELM_EngineLoad'])
                data['ELM_IntakeTemp'] = obd_data.get('intake_temp', data['ELM_IntakeTemp'])
                data['ELM_TimingAdvance'] = obd_data.get('timing_advance', data['ELM_TimingAdvance'])
        except Exception as e:
            print(f"Error fetching OBD-II data: {e}")
    else:
        # If no ELM327 connection, continue without affecting the flow
        pass

    # Priority 3 - Pro Micro Data Handling (Send RPM to control LEDs)
    if serial_pro_micro.is_connected() and data['RPM'] is not None:
        try:
            # Send the RPM data to the Pro Micro, adding '\n' for correct formatting
            rpm_string = f"{data['RPM']}\n"
            print(f"Sending RPM to Pro Micro: {rpm_string}")  # Debugging line
            serial_pro_micro.write_data(rpm_string)
        except Exception as e:
            print(f"Error sending data to Pro Micro: {e}")
    else:
        serial_pro_micro.reconnect()

def main():
    graphics, serial_arduino, serial_pro_micro, obd_handler = init_system()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        # Update sensor data with priority system
        update_sensor_data(serial_arduino, serial_pro_micro, obd_handler)

        # Display updated data
        graphics.display_data(data)

        # Cap the frame rate
        graphics.clock.tick(60)

    graphics.clear()
    sys.exit()

if __name__ == "__main__":
    main()
