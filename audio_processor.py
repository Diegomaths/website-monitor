from pydub import AudioSegment
from math import floor
from gtts import gTTS
import os
import torchaudio.transforms as T
import torchaudio
from pydub import AudioSegment
from math import ceil
import logging
import torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
import pickle

os.makedirs("logs", exist_ok=True)
logging.basicConfig(filename='logs/transcriptor.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', filemode="w")
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('')



logger.info("Starting to load model and processor...")
class AudioConverter():
    def __init__(self):
        self.sounds_dir = "audio_samples"
        self.output_dir = f"{self.sounds_dir}/tmp"
        self.final_dir = f"{self.sounds_dir}/transcriptions"
        self.max_size = 20 #limit in MB
        os.makedirs(self.sounds_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.final_dir, exist_ok=True)
        os.makedirs("models", exist_ok=True)
        model_path = "models/model_and_preprocessor.pkl"
        refresh_model = True
        if os.path.exists(model_path):
            refresh_model = False
        self.load_model(refresh=refresh_model)
    
    def get_file(self, file_name):
        self.fn = os.path.join(os.getcwd(), self.sounds_dir, file_name)
        self.n_segments = ceil(os.path.getsize(self.fn)/1024**2/self.max_size)
        self.file_name_noext = os.path.splitext(file_name)[0]
        self.file_extension = os.path.splitext(file_name)[1]
        
    def process_audio(self, file_name):
        self.get_file(file_name)
        segments = self.split_audio(self.fn)
        self.save_splitted_audio(segments)
        file_names = os.listdir(self.output_dir)
        for i in range(len(file_names)):
            audio_transcription = self.transcript(os.path.join(self.output_dir, file_names[i]))
            self.text_to_audio(audio_transcription)
        for filename in os.listdir(self.output_dir):
            os.remove(os.path.join(self.output_dir, filename))

    def load_model(self, refresh=False):
        model_file = 'models/model_and_preprocessor.pkl'
        model_name = "facebook/wav2vec2-large-xlsr-53-italian"

        if refresh:
            try:
                logger.info(f"Loading processor from {model_name}...")
                self.processor = Wav2Vec2Processor.from_pretrained(model_name)
                logger.info("Processor loaded.")

                logger.info(f"Loading model from {model_name}...")
                self.model = Wav2Vec2ForCTC.from_pretrained(model_name)
                logger.info("Model loaded.")

                mod_pr = {
                    "model_state_dict": self.model.state_dict(),
                    "processor": self.processor
                }

                
                with open(model_file, 'wb') as outp:
                    pickle.dump(mod_pr, outp, pickle.HIGHEST_PROTOCOL)
                logger.info("Model and processor saved to disk.")

            except Exception as e:
                logger.error(f"Failed to load or save model and processor: {e}")

        else:
            try:
                logger.info("Loading model and processor from disk...")
                with open(model_file, 'rb') as inp:
                    mod_pr = pickle.load(inp)
                    self.processor = mod_pr["processor"]
                    self.model = Wav2Vec2ForCTC.from_pretrained(model_name)
                    self.model.load_state_dict(mod_pr["model_state_dict"])
                logger.info("Model and processor loaded from disk.")
            except Exception as e:
                logger.error(f"Failed to load model and processor from disk: {e}")
        logger.info("Model and processor are ready to use.")

    @staticmethod
    def get_audio_segment(audio_file_path, lower=0, upper=10):
        audio = AudioSegment.from_file(audio_file_path)
        lower_ms = lower * 60 * 1000  # PyDub handles time in milliseconds
        upper_ms = upper * 60 * 1000  # PyDub handles time in milliseconds
        segment = audio[lower_ms:upper_ms]
        return segment
    @staticmethod
    def get_audio_duration(audio_file_path):
        audio = AudioSegment.from_file(audio_file_path)
        return len(audio) / (1000*60)

    def split_audio(self, audio_file_path):
        duration = self.get_audio_duration(audio_file_path)
        segments = []
        for j in range(self.n_segments):
            t0 = floor(j * duration / self.n_segments)
            t1 = floor((j + 1) * duration / self.n_segments)
            if self.n_segments==1: t1 = duration
            audio = self.get_audio_segment(audio_file_path, lower=t0, upper=t1)
            segments.append(audio)
        return segments

    def convert_to_wav(self, file_name):
        if self.file_extension != ".wav":
            try:
                audio = AudioSegment.from_file(self.fn)
                fn = os.path.join(os.getcwd(), "audio_samples", self.file_name_noext + ".wav")
                audio.export(fn, format="wav")
                logger.info(f"File converted successfully: {fn}")
                
            except Exception as e:
                logger.error(f"An error occurred: {e}")

    def save_splitted_audio(self, segments):
        for j in range(self.n_segments):
            segment = segments[j]
            filename = os.path.join(self.output_dir, f"{self.file_name_noext}_p{j+1}.wav")
            # Verifica che il segmento non sia vuoto
            if len(segment) > 0:
                segment.export(filename, format="wav")
            else:
                logger.warning(f"Segment {j+1} is empty, skipping export.")
        logger.info(f"files saved in directory {self.output_dir}")

    def transcript(self, file_path):
        transcription = "NO TRANSCRIPTION"
        try:
            waveform, sample_rate = torchaudio.load(file_path, backend='soundfile')
            logger.info(f"Loaded file {file_path} successfully.")
            logger.debug(f"Waveform shape: {waveform.shape}, Sample rate: {sample_rate}")
        except RuntimeError as e:
            logger.error(f"RuntimeError: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        try:
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
                logger.debug(f"Converted waveform to mono. New shape: {waveform.shape}")

            target_sample_rate = 16000
            if sample_rate != target_sample_rate:
                resampler = T.Resample(orig_freq=sample_rate, new_freq=target_sample_rate)
                waveform = resampler(waveform)
                sample_rate = target_sample_rate
                logger.debug(f"Resampled waveform to {sample_rate} Hz")

            waveform = waveform.squeeze() 
            input_values = self.processor(waveform, return_tensors="pt", sampling_rate=sample_rate).input_values

            with torch.no_grad():
                logits = self.model(input_values).logits

            predicted_ids = torch.argmax(logits, dim=-1)
            transcription = self.processor.batch_decode(predicted_ids)[0]

        except RuntimeError as e:
            logger.error(f"RuntimeError: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        return transcription

    def text_to_audio(self, text_to_be_converted, language='it'):
        self.output_file_path = os.path.join(self.final_dir, "transcription.txt")
        with open(self.output_file_path, "w", encoding="utf-8") as f:
            f.write(text_to_be_converted)

        output_file_path = f"{self.final_dir}/audio_from_text.wav"
        try:
            tts = gTTS(text=text_to_be_converted, lang=language)
            tts.save(output_file_path)
            logger.info(f"File audio salvato in: {output_file_path}")
        except Exception as e:
            logger.error(f"Errore durante la conversione del testo in audio: {e}")


if __name__ == "__main__":
    file_name = "test.mp3"
    ac = AudioConverter()
    ac.process_audio(file_name)

