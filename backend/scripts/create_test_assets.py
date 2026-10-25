import os
import wave
import struct
import math
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

os.makedirs("data/samples", exist_ok=True)
os.makedirs("../src/assets/brain_scans", exist_ok=True)

def generate_brain_mri(lesion_type="glioma", size=(256, 256)):
    img = Image.new("L", size, color=8)
    draw = ImageDraw.Draw(img)
    w, h = size
    cx, cy = w // 2, h // 2

    # Draw skull contour (outer cranium)
    draw.ellipse([cx - 105, cy - 118, cx + 105, cy + 118], fill=28, outline=160, width=4)
    # Draw brain parenchyma
    draw.ellipse([cx - 100, cy - 112, cx + 100, cy + 112], fill=55)

    # Ventricular system (bilateral lateral ventricles)
    if lesion_type == "normal":
        # Symmetrical lateral ventricles (dark CSF)
        draw.ellipse([cx - 32, cy - 35, cx - 12, cy + 25], fill=16)
        draw.ellipse([cx + 12, cy - 35, cx + 32, cy + 25], fill=16)
        # Midline third ventricle
        draw.line([cx, cy - 15, cx, cy + 20], fill=18, width=3)
    elif lesion_type == "glioma":
        # Compressed ipsilateral ventricle due to mass effect
        draw.ellipse([cx - 35, cy - 30, cx - 18, cy + 20], fill=16) # Left ventricle
        draw.ellipse([cx + 18, cy - 20, cx + 25, cy + 10], fill=22) # Compressed Right ventricle
        # Glioma: Infiltrative hyperintense mass in right parietal/temporal lobe
        for r in range(40, 10, -5):
            draw.ellipse([cx + 25 - r, cy - 10 - r, cx + 25 + r, cy - 10 + r], fill=110 + (40 - r) * 3)
        # Necrotic center
        draw.ellipse([cx + 20, cy - 15, cx + 32, cy - 5], fill=45)
    elif lesion_type == "meningioma":
        # Symmetrical ventricles with slight displacement
        draw.ellipse([cx - 30, cy - 30, cx - 12, cy + 25], fill=16)
        draw.ellipse([cx + 12, cy - 28, cx + 30, cy + 25], fill=16)
        # Meningioma: Extra-axial circumscribed hyperintense mass along convexity/dura
        draw.ellipse([cx - 95, cy - 40, cx - 45, cy + 20], fill=210, outline=245, width=2)
        # Dural tail sign
        draw.polygon([(cx - 98, cy - 50), (cx - 93, cy - 40), (cx - 95, cy - 30)], fill=230)
    elif lesion_type == "pituitary":
        # Central sellar mass
        draw.ellipse([cx - 28, cy - 40, cx - 10, cy + 15], fill=16)
        draw.ellipse([cx + 10, cy - 40, cx + 28, cy + 15], fill=16)
        # Suprasellar / sellar figure-of-8 expansion
        draw.ellipse([cx - 22, cy + 5, cx + 22, cy + 45], fill=185, outline=220, width=2)

    # Interhemispheric fissure
    draw.line([cx, cy - 110, cx, cy - 35], fill=22, width=2)
    draw.line([cx, cy + 30, cx, cy + 110], fill=22, width=2)

    # Smooth Gaussian blur for realistic MRI soft-tissue appearance
    img = img.filter(ImageFilter.GaussianBlur(radius=1.8))
    return img

# Generate all 4 cases
scans = {
    "sample_brain_glioma.png": generate_brain_mri("glioma"),
    "sample_brain_meningioma.png": generate_brain_mri("meningioma"),
    "sample_brain_pituitary.png": generate_brain_mri("pituitary"),
    "sample_brain_normal.png": generate_brain_mri("normal"),
}

for name, img in scans.items():
    img.save(f"data/samples/{name}")
    img.save(f"../src/assets/brain_scans/{name}")
    if name == "sample_brain_glioma.png":
        img.save("../test_image.jpg")
        img.save("test_image.jpg")

print("Generated 4 Brain MRI sample datasets.")

# Generate real 16kHz mono audio WAV
sample_rate = 16000
duration = 2.0 # seconds
freq = 440.0 # Hz
num_samples = int(sample_rate * duration)

with wave.open("data/samples/sample_speech_dysarthria.wav", "wb") as wav_file:
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(sample_rate)
    for i in range(num_samples):
        # Audio modulation with speech pauses
        t = float(i) / sample_rate
        envelope = 0.5 * (1.0 + math.sin(2.0 * math.pi * 2.0 * t)) if (t < 0.8 or t > 1.2) else 0.05
        value = int(32767.0 * 0.3 * envelope * math.sin(2.0 * math.pi * freq * t))
        data = struct.pack("<h", value)
        wav_file.writeframesraw(data)

with open("data/samples/sample_speech_dysarthria.wav", "rb") as f:
    audio_data = f.read()

with open("../test_audio.wav", "wb") as f:
    f.write(audio_data)
with open("test_audio.wav", "wb") as f:
    f.write(audio_data)

print("Generated valid 16kHz speech audio samples.")
