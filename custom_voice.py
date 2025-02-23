from pydub import AudioSegment
import librosa

# Carica il file audio
audio_path = 'audio_samples/test1.wav'
audio = AudioSegment.from_wav(audio_path)

# Pre-elabora l'audio (opzionale)
samples, sample_rate = librosa.load(audio_path, sr=None)
import nemo.collections.tts as nemo_tts
import torch

# Carica i modelli pre-addestrati
tacotron2 = nemo_tts.models.Tacotron2Model.from_pretrained(model_name="Tacotron2")
waveglow = nemo_tts.models.WaveGlowModel.from_pretrained(model_name="WaveGlow")

# Testo da convertire in audio
text = "Ciao, questo è un test della mia voce sintetizzata."

# Genera mel-spectrogram
parsed = tacotron2.parse(text)
spectrogram = tacotron2.generate_spectrogram(tokens=parsed)

# Genera audio
audio = waveglow.convert_spectrogram_to_audio(spec=spectrogram)
audio = audio.to('cpu').numpy()

# Salva l'audio generato
import soundfile as sf
sf.write('audio_samples/test1.wav', audio, 22050)
