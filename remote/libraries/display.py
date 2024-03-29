import remote.libraries.LCD_1in44 as LCD_1in44
import remote.libraries.LCD_Config as LCD_Config

from PIL import Image, ImageDraw, ImageFont, ImageColor


class Display:
    def __init__(self, remote_id):
        self.LCD = LCD_1in44.LCD()
        Lcd_ScanDir = LCD_1in44.SCAN_DIR_DFT  # SCAN_DIR_DFT = D2U_L2R
        self.LCD.LCD_Init(Lcd_ScanDir)
        self.LCD.LCD_Clear()

        font_path = "fonts/FreeMonoBold.ttf"
        self.small_font = ImageFont.truetype(font_path, 20)
        self.large_font = ImageFont.truetype(font_path, 35)

        self.remote_id = remote_id

        self.image = Image.new('RGB', (self.LCD.width, self.LCD.height), 'WHITE')
        self.draw = ImageDraw.Draw(self.image)

        self.add_remote_id()
        self.refresh_display()

    def add_remote_id(self):
        self.draw.text((0, 0), f'ID', fill='BLUE', font=self.small_font)
        self.draw.text((30, 0), f'{self.remote_id}', fill='BLUE', font=self.large_font)

        self.refresh_display()

    def add_message(self, message):
        self.clear_message()

        self.draw.text((0, 40), message, fill='BLUE', font=self.large_font)

        self.refresh_display()

    def refresh_display(self):
        self.LCD.LCD_ShowImage(self.image, 0, 0)

    def clear_message(self):
        self.draw.rectangle([(0, 40), (self.LCD.width, self.LCD.height)], fill='WHITE')

