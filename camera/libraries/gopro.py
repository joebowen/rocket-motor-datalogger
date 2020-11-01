import logging
import time

from goprocam import GoProCamera, constants


class GoPro:
    def __init__(self, base_dir='/home/pi/Desktop/video'):
        self.camera = GoProCamera.GoPro()
        self.base_dir = base_dir

        self.camera.video_settings("1080p", "60")

    def start_recording(self):
        logging.info('Start recording...')
        self.camera.shoot_video()

    def stop_recording(self):
        logging.info('Stop recording...')
        if self.camera.IsRecording():
            self.camera.shutter(constants.stop)

            while self.camera.IsRecording():
                time.sleep(0.1)

            self.camera.downloadLastMedia(custom_filename=f'{self.base_dir}/gopro-{int(time.time())}.mp4')

