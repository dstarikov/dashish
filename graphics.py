import pygame

class GraphicsHandler:
    def __init__(self, background_image, rpm_image, small_bar_image):
        pygame.init()
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.display.set_caption('Vehicle Data Display')
        pygame.mouse.set_visible(False)
        self.screen_width, self.screen_height = self.screen.get_size()

        # Load images
        self.background = pygame.image.load(background_image)
        self.background = pygame.transform.scale(self.background, (self.screen_width, self.screen_height))
        self.rpm_image = pygame.image.load(rpm_image)
        self.small_bar_image = pygame.image.load(small_bar_image)

        # Fonts
        try:
            self.fonts = {
                'value_font': pygame.font.Font('/home/cleanish/r4/ZeroAthletics.ttf', 45),
                'rpm_font': pygame.font.Font('/home/cleanish/r4/ZeroAthletics.ttf', 60),
                'speed_font': pygame.font.Font('/home/cleanish/r4/ZeroAthletics.ttf', 75),
                'elm_font': pygame.font.Font('/home/cleanish/r4/Orbitron-Black.ttf', 25),
                'unit_font': pygame.font.Font('/home/cleanish/r4/ZeroAthletics.ttf', 20),
                'elm_unit_font': pygame.font.Font('/home/cleanish/r4/Orbitron-Black.ttf', 20)
            }
        except Exception as e:
            print(f"Error loading fonts: {e}")

        self.clock = pygame.time.Clock()

        # Define the positions
        self.positions = {
            "rpm_bar": (0, self.screen_height - 125),
            "rpm_text": (15, 460),
            "speed_text": (830, 15),
            "pressure_text": (695, 340),
            "coolant_temp_text": (685, 60),
            "oil_temp_text": (685, 205),
            "coolant_temp_bar": (583, 114),
            "oil_temp_bar": (583, 257),
            "pressure_bar": (583, 395),
            "elm_coolant_temp": (945, 160),
            "elm_intake_temp": (945, 218),
            "elm_timing_advance": (940, 276),
            "elm_engine_load": (948, 327)
        }

        self.unit_offsets = {
            "pressure_text": {"x_offset": 5, "y_offset": -3},
            "coolant_temp_text": {"x_offset": 5, "y_offset": -3},
            "oil_temp_text": {"x_offset": 5, "y_offset": -3},
            "elm_coolant_temp": {"x_offset": 5, "y_offset": -2},
            "elm_intake_temp": {"x_offset": 5, "y_offset": -2},
            "elm_timing_advance": {"x_offset": 5, "y_offset": -2},
            "elm_engine_load": {"x_offset": 5, "y_offset": -2},
        }

    def get_average(self, values):
        return sum(values) / len(values)

    def draw_background(self):
        self.screen.blit(self.background, (0, 0))

    def draw_rpm_bar(self, rpm_value, max_rpm):
        position = self.positions['rpm_bar']
        size = (self.screen_width, 125)
        width, height = size
        fill_width = int((rpm_value / max_rpm) * width)
        scaled_rpm_background = pygame.transform.scale(self.rpm_image, size)
        self.screen.blit(scaled_rpm_background, position)
        if fill_width < width:
            pygame.draw.rect(self.screen, (0, 0, 0), (position[0] + fill_width, position[1], width - fill_width, height))

    def draw_small_bar(self, value, max_value, bar_type):
        position = self.positions[bar_type]
        size = (150, 15)
        width, height = size
        fill_width = int((value / max_value) * width)
        scaled_background = pygame.transform.scale(self.small_bar_image, size)
        self.screen.blit(scaled_background, position)
        if fill_width < width:
            pygame.draw.rect(self.screen, (0, 0, 0), (position[0] + fill_width, position[1], width - fill_width, height))

    def draw_text_with_unit(self, value, unit, value_font, unit_font, color, text_type):
        position = self.positions[text_type]
        
        value_surf = value_font.render(value, True, color)
        unit_surf = unit_font.render(unit, True, color)
        
        unit_y_position = position[1] + value_surf.get_height() - unit_surf.get_height()
        
        total_width = value_surf.get_width() + (unit_surf.get_width() if unit else 0)
        
        adjusted_position = (position[0] - total_width, position[1])
        
        self.screen.blit(value_surf, adjusted_position)
        
        x_offset = self.unit_offsets[text_type].get("x_offset", 0)
        y_offset = self.unit_offsets[text_type].get("y_offset", 0)
        
        self.screen.blit(unit_surf, (adjusted_position[0] + value_surf.get_width() + x_offset, unit_y_position + y_offset))

    def draw_rpm_text(self, rpm, font, color, gray_color):
        position = self.positions['rpm_text']
        rpm_str = f"{rpm:04d}"
        leading_zero_color = gray_color if rpm < 1000 else color
        leading_zero_surf = font.render(rpm_str[0], True, leading_zero_color)
        self.screen.blit(leading_zero_surf, position)
        remaining_digits_surf = font.render(rpm_str[1:], True, color)
        self.screen.blit(remaining_digits_surf, (position[0] + leading_zero_surf.get_width(), position[1]))
        rpm_label_font = pygame.font.Font('/home/cleanish/r4/ZeroAthletics.ttf', 30)
        rpm_label_surf = rpm_label_font.render("RPM.", True, gray_color)
        self.screen.blit(rpm_label_surf, (position[0] + 145, position[1] + 30))

    def draw_speed_text(self, speed, font, color, gray_color):
        position = self.positions['speed_text']
        speed_str = f"{speed:03d}"
        leading_zero_color = gray_color if speed < 100 else color
        leading_zero_surf = font.render(speed_str[0], True, leading_zero_color)
        self.screen.blit(leading_zero_surf, position)
        remaining_digits_surf = font.render(speed_str[1:], True, color)
        self.screen.blit(remaining_digits_surf, (position[0] + leading_zero_surf.get_width(), position[1]))

    def update_display(self):
        pygame.display.update()

    def clear(self):
        pygame.quit()

    def display_data(self, data):
        self.draw_background()

        # Draw RPM progress bar
        self.draw_rpm_bar(data["RPM"], 6800)

        # Draw RPM text
        self.draw_rpm_text(data["RPM"], self.fonts['rpm_font'], (255, 255, 255), (169, 169, 169))

        # Draw speed text
        self.draw_speed_text(int(data["Speed"][0]), self.fonts['speed_font'], (255, 255, 255), (50, 50, 50))

        # Draw additional data for Pressure, Coolant Temp, and Oil Temp
        self.draw_text_with_unit(f"{self.get_average(data['Pressure']):.1f}", "psi", self.fonts['value_font'], self.fonts['unit_font'], (255, 255, 255), 'pressure_text')
        self.draw_text_with_unit(f"{self.get_average(data['CoolantTemp']):.1f}", "f", self.fonts['value_font'], self.fonts['unit_font'], (255, 255, 255), 'coolant_temp_text')
        self.draw_text_with_unit(f"{self.get_average(data['OilTemp']):.1f}", "f", self.fonts['value_font'], self.fonts['unit_font'], (255, 255, 255), 'oil_temp_text')

        # Draw small progress bars
        self.draw_small_bar(self.get_average(data["CoolantTemp"]), 205, 'coolant_temp_bar')
        self.draw_small_bar(self.get_average(data["OilTemp"]), 220, 'oil_temp_bar')
        self.draw_small_bar(self.get_average(data["Pressure"]), 100, 'pressure_bar')

        # Draw ELM327 data with checks for None
        coolant_temp = data['ELM_CoolantTemp'] if data['ELM_CoolantTemp'] is not None else 0.0
        self.draw_text_with_unit(f"{coolant_temp:.1f}", "f", self.fonts['elm_font'], self.fonts['elm_unit_font'], (255, 255, 255), 'elm_coolant_temp')

        intake_temp = data['ELM_IntakeTemp'] if data['ELM_IntakeTemp'] is not None else 0.0
        self.draw_text_with_unit(f"{intake_temp:.1f}", "f", self.fonts['elm_font'], self.fonts['elm_unit_font'], (255, 255, 255), 'elm_intake_temp')

        timing_advance = data['ELM_TimingAdvance'] if data['ELM_TimingAdvance'] is not None else 0.0
        self.draw_text_with_unit(f"{timing_advance:.1f}", "°", self.fonts['elm_font'], self.fonts['elm_unit_font'], (255, 255, 255), 'elm_timing_advance')

        engine_load = data['ELM_EngineLoad'] if data['ELM_EngineLoad'] is not None else 0.0
        self.draw_text_with_unit(f"{engine_load:.1f}", "%", self.fonts['elm_font'], self.fonts['elm_unit_font'], (255, 255, 255), 'elm_engine_load')

        self.update_display()
