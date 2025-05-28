from flask import Flask, request, jsonify, send_file
from flask_cors import CORS # Import CORS
from googletrans import Translator
from gtts import gTTS
import io
import os

app = Flask(__name__)
# Configure CORS to allow requests specifically from the GitHub Pages origin
CORS(app, resources={
    r"/translate": {"origins": "https://sandra-ai-br.github.io"},
    r"/audio_stream/*": {"origins": "https://sandra-ai-br.github.io"}
})

translator = Translator()

# Ensure the 'audio_files' directory exists
if not os.path.exists('audio_files'):
    os.makedirs('audio_files')

@app.route('/')
def home():
    return jsonify({"message": "API de Tradução e Síntese de Voz - PORTUGUÊS PARA ENGLISH - CORS Fixed v2"})

@app.route('/translate', methods=['POST'])
def translate_text():
    try:
        data = request.json
        text_pt = data.get('text')
        if not text_pt:
            return jsonify({"error": "Texto em português não fornecido"}), 400

        # Translate PT to EN
        translation = translator.translate(text_pt, src='pt', dest='en')
        text_en = translation.text

        # Generate audio EN
        # Sanitize filename based on translated text
        safe_base_filename = "".join(c for c in text_en if c.isalnum() or c in (' ', '-')).rstrip()
        safe_base_filename = safe_base_filename.replace(' ', '_').lower()
        if not safe_base_filename:
            safe_base_filename = 'audio' # Default if text is only special chars
        audio_filename = f"{safe_base_filename}.mp3"

        audio_path = os.path.join('audio_files', audio_filename)
        
        # Only generate if it doesn't exist to save time/resources
        if not os.path.exists(audio_path):
            tts = gTTS(text=text_en, lang='en', slow=False)
            tts.save(audio_path)

        # Construct audio URL relative to the API base
        audio_url = f"/audio_stream/{audio_filename}"

        return jsonify({
            "text_pt": text_pt,
            "text_en": text_en,
            "audio_url": audio_url 
        })

    except Exception as e:
        print(f"Erro na tradução/TTS: {e}") # Log error server-side
        return jsonify({"error": f"Erro interno no servidor: {e}"}), 500

@app.route('/audio_stream/<filename>')
def stream_audio(filename):
    try:
        # Security: Sanitize filename to prevent directory traversal
        safe_filename = os.path.basename(filename)
        if not safe_filename.endswith('.mp3'):
             return "Invalid file type", 400

        audio_path = os.path.join('audio_files', safe_filename)

        if not os.path.exists(audio_path):
            # Attempt to generate the audio file if it
