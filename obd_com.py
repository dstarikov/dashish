import obd

class OBDHandler:
    def __init__(self, port):
        self.connection = None
        try:
            self.connection = obd.Async(portstr=port)
            self.connection.watch(obd.commands.COOLANT_TEMP)
            self.connection.watch(obd.commands.ENGINE_LOAD)
            self.connection.watch(obd.commands.INTAKE_TEMP)
            self.connection.watch(obd.commands.TIMING_ADVANCE)
            self.connection.start()
            print(f"Connected to OBD-II adapter at {port}")
        except Exception as e:
            print(f"Failed to connect to OBD-II adapter at {port}: {e}")
            self.connection = None
    
    def is_connected(self):
        return self.connection is not None and self.connection.is_connected()

    def query_data(self):
        if self.is_connected():
            try:
                return {
                    "coolant_temp": self.connection.query(obd.commands.COOLANT_TEMP).value,
                    "engine_load": self.connection.query(obd.commands.ENGINE_LOAD).value,
                    "intake_temp": self.connection.query(obd.commands.INTAKE_TEMP).value,
                    "timing_advance": self.connection.query(obd.commands.TIMING_ADVANCE).value
                }
            except Exception as e:
                print(f"Error querying OBD-II data: {e}")
        return None
    
    def stop(self):
        if self.is_connected():
            self.connection.stop()
            print("Stopped OBD-II connection")
    
    def close(self):
        if self.is_connected():
            self.connection.close()
            print("Closed OBD-II connection")
