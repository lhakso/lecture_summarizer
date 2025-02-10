import sounddevice as sd
import numpy as np
from scipy.signal import resample
from scipy.io.wavfile import write
import threading

class RecordingSession:

    def __init__(self, sample_rate=41000, dtype=np.int16, duration=60, today=None):
        self.sample_rate: int = sample_rate
        self.dtype: np.dtype = dtype
        self.output_file: str = f"raw_audio{today}.wav" 
        self.audio_buffer: np.ndarray = np.zeros((sample_rate * duration, 1), dtype=dtype)
        self.index: int = 0
        self.recording: bool = True 

    def wait_for_stop(self):
        """blocks until the user presses Enter then stops recording."""
        input("Press Enter to stop recording...\n")
        self.recording = False

    def resample_to_16khz(self, audio_data):
        """whisper transcription works best with 16khz"""
        new_sample_rate = 16000
        sample_rate = self.sample_rate
        num_samples = round(len(audio_data) * (new_sample_rate / sample_rate))
        return resample(audio_data, num_samples)

    def callback(self, indata: np.ndarray, frames: int, time: object, status: object):
        """callback func for sounddevice"""
        self.audio_buffer[self.index:self.index + frames] = indata
        self.index += frames

    def start_record(self):

        print("started recording, press Esc to stop")

        stopper_thread = threading.Thread(target=self.wait_for_stop)
        stopper_thread.start()

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype=self.dtype,
            callback=self.callback,
        ):
            while self.recording:
                sd.sleep(100)  # prevents cpu overload
                
        stopper_thread.join()

        respampled_audio = self.resample_to_16khz(self.audio_buffer[: self.index])

        write(self.output_file, 16000, respampled_audio)
        
        print(f"recording stopped, file saved as {self.output_file}")

        process_command = input("proceed with processing? y/n\n").strip().lower()
        
        if process_command != "y":
            print("processing cancelled")
            exit(0)