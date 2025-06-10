#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, url_for, send_file
from flask_cors import CORS
from googletrans import Translator
from gtts import gTTS
import os
import logging
from retrying import retry
import epitran
import glob
import time

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Ajustar para produção

# Initialize Translator
try:
    translator = Translator(timeout=10)
    logging.info("Translator initialized successfully.")
except Exception as e:
    logging.error(f"Error initializing Translator: {e}")
    translator = None

# Initialize Epitran
try:
    epitran_converter = epitran.Epitran('eng-Latn')
    logging.info("Epitran initialized successfully.")
except Exception as e:
    logging.error(f"Error initializing Epitran: {e}")
    epitran_converter = None

# Clean old audio files to save disk space
def clean_old_audio_files(max_age_seconds=3600):
    for file in glob.glob("translation_*.mp3"):
        if os.path.getmtime(file) < time.time() - max_age_seconds:
            try:
                os.remove(file)
                logging.info(f"Deleted old audio file: {file}")
            except Exception as e:
                logging.error(f"Error deleting file {file}: {e}")

# Retry decorator for rate limits
def retry_if_rate_limit(exception):
    return "429" in str(exception)

@app.route('/translate', methods=['POST'])
@retry(stop_max_attempt_number=3, wait_fixed=2000, retry_on_exception=retry_if_rate_limit)
def translate_text():
    if translator is None:
        logging.error("Translator not initialized.")
        return jsonify({"error": "Translator service not available"}), 500
    if epitran_converter is None:
        logging.error("Epitran not initialized.")
        return jsonify({"error": "Phonetic service not available"}), 500

    data = request.get_json()
    text_to_translate = data.get('text')
    src_lang = data.get('src_lang', 'pt')  # Default: Português
    dest_lang = data.get('dest_lang', 'en')  # Default: Inglês

    if not text_to_translate:
        logging.warning("No text provided for translation.")
        return jsonify({"error": "No text provided"}), 400

    try:
        # Clean old audio files
        clean_old_audio_files()

        # Tradução
        logging.info(f"Translating: '{text_to_translate}' from {src_lang} to {dest_lang}")
        translation = translator.translate(text_to_translate, src=src_lang, dest=dest_lang)
        translated_text = translation.text
        logging.info(f"Translation successful: {translated_text}")

        # Fonética
        phonetic = epitran_converter.transliterate(translated_text)
        logging.info(f"Phonetic transcription: {phonetic}")

        # Text-to-Speech
        tts = gTTS(text=translated_text, lang=dest_lang)
        audio_filename = f"translation_{hash(translated_text)}.mp3"
        tts.save(audio_filename)

        # URL do áudio
        audio_url = url_for('serve_audio', filename=audio_filename, _external=True)

        return jsonify({
            "translation": translated_text,
            "phonetic": phonetic,
            "audio_url": audio_url
        })

    except Exception as e:
        logging.error(f"Error during translation/TTS/phonetic: {e}")
        return jsonify({"error": "Failed to process request"}), 500

@app.route('/audio/<filename>')
def serve_audio(filename):
    try:
        return send_file(filename, mimetype="audio/mpeg")
    except Exception as e:
        logging.error(f"Error serving audio {filename}: {e}")
        return jsonify({"error": "Audio not found"}), 404

@app.route('/')
def index():
    return send_file('index.html')

if __name__ == '__main__':
    if translator is None or epitran_converter is None:
        logging.error("Services failed to initialize. Cannot start server.")
    else:
        port = int(os.getenv('PORT', 8080))
        app.run(host='0.0.0.0', port=port)