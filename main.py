#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from googletrans import Translator
from gtts import gTTS
import io
import logging
import httpx # Added import for httpx

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize Translator with timeout
try:
    # Use httpx timeout object
    translator = Translator(timeout=httpx.Timeout(10.0))
    logging.info("Translator initialized successfully.")
except Exception as e:
    logging.error(f"Error initializing Translator: {e}")
    # Set translator to None or handle the error appropriately
    # For now, let's allow the app to start but log the error
    translator = None

@app.route('/translate', methods=['POST'])
def translate_text():
    if translator is None:
        logging.error("Translator not initialized.")
        return jsonify({"error": "Translator service not available"}), 500

    data = request.get_json()
    text_to_translate = data.get('text')
    logging.info(f"Received for translation: {text_to_translate}")

    if not text_to_translate:
        logging.warning("No text provided for translation.")
        return jsonify({"error": "No text provided"}), 400

    try:
        # Translation
        logging.info("Attempting translation...")
        translation = translator.translate(text_to_translate, src='pt', dest='en')
        translated_text = translation.text
        logging.info(f"Translation successful: {translated_text}")

        # Text-to-Speech
        logging.info("Attempting text-to-speech...")
        tts = gTTS(text=translated_text, lang='en')
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        logging.info("Text-to-speech successful.")

        # Send audio file
        return send_file(
            audio_fp,
            mimetype="audio/mpeg",
            as_attachment=True,
            download_name="translation.mp3"
        )

    except Exception as e:
        logging.error(f"Error during translation/TTS: {e}")
        return jsonify({"error": "Failed to process request"}), 500

if __name__ == '__main__':
    # Check if translator initialized correctly before running
    if translator is None:
        logging.error("Translator failed to initialize. Cannot start server.")
    else:
        # Use 0.0.0.0 to be accessible externally, Render uses PORT env var
        app.run(host='0.0.0.0', port=8080)

