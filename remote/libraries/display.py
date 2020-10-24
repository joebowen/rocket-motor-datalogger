import libraries.LCD_1in44 as LCD_1in44
import libraries.LCD_Config as LCD_Config

from PIL import Image, ImageDraw, ImageFont, ImageColor


class Display:
    def __init__(self, remote_id):
        self.LCD = LCD_1in44.LCD()
        Lcd_ScanDir = LCD_1in44.SCAN_DIR_DFT  # SCAN_DIR_DFT = D2U_L2R
        self.LCD.LCD_Init(Lcd_ScanDir)
        self.LCD.LCD_Clear()

        font_path = "fonts/FreeMonoBold.ttf"
        font_size = 16
        self.font = ImageFont.truetype(font_path, font_size)

        self.remote_id = remote_id

        self.image = Image.new('RGB', (self.LCD.width, self.LCD.height), 'WHITE')
        self.draw = ImageDraw.Draw(self.image)

        self.add_remote_id()
        self.refresh_display()

    def add_remote_id(self):
        self.draw.text((10, 10), f'ID - {self.remote_id}', fill='BLUE', font=self.font)

        self.refresh_display()

    def add_message(self, message):
        self.clear_message()

        self.draw.text((10, 64), message, fill='BLUE', font=self.font)

        self.refresh_display()

    def refresh_display(self):
        self.LCD.LCD_ShowImage(self.image, 0, 0)

    def clear_message(self):
        self.draw.rectangle([(0, 64), (self.LCD.width, self.LCD.height)], fill='WHITE')

