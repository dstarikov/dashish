import serial

# Define the ports and baud rate
ARDUINO_PORT = '/dev/ttyACM0'
PROMICRO_PORT = '/dev/ttyACM1'
ELM327_PORT = '/dev/ttyUSB0'
BAUD_RATE = 115200

class SerialHandler:
    def __init__(self, port, baudrate=BAUD_RATE, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None
    
    def open_connection(self):
        try:
            self.connection = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            print(f"Connected to {self.port} at {self.baudrate} baud.")
        except serial.SerialException as e:
            print(f"Failed to connect to {self.port}: {e}")
            self.connection = None
    
    def is_connected(self):
        return self.connection is not None and self.connection.is_open
    
    def read_data(self):
        if self.is_connected():
            try:
                data = self.connection.readline().decode('utf-8').strip()
                if data:
                    print(f"Data received from {self.port}: {data}")
                return data
            except serial.SerialException as e:
                print(f"Error reading from {self.port}: {e}")
        return None
    
    def write_data(self, data):
        if self.is_connected():
            try:
                self.connection.write(data.encode())
                print(f"Data sent to {self.port}: {data}")
            except serial.SerialException as e:
                print(f"Error writing to {self.port}: {e}")
    
    def close(self):
        if self.is_connected():
            self.connection.close()
            print(f"Closed connection to {self.port}")
    
    def reconnect(self):
        if not self.is_connected():
            print(f"Attempting to reconnect to {self.port}...")
            self.open_connection()
