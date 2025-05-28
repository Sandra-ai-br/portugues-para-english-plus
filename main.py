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
audio_dir = 'audio_files'
if not os.path.exists(audio_dir):
    os.makedirs(audio_dir)

@app.route('/')
def home():
    return jsonify({"message": "API de Tradução e Síntese de Voz - PORTUGUÊS PARA ENGLISH - CORS Fixed v3"}) # Updated version marker

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

        audio_path = os.path.join(audio_dir, audio_filename)

        # Only generate if it doesn't exist to save time/resources
        if not os.path.exists(audio_path):
            try:
                tts = gTTS(text=text_en, lang='en', slow=False)
                tts.save(audio_path)
            except Exception as tts_error:
                print(f"Erro ao gerar áudio com gTTS: {tts_error}")
                return jsonify({"error": f"Erro ao gerar áudio: {tts_error}"}), 500


        # Construct audio URL relative to the API base
        audio_url = f"/audio_stream/{audio_filename}" # Use the generated filename

        return jsonify({
            "text_pt": text_pt,
            "text_en": text_en,
            "audio_url": audio_url
        })

    except Exception as e:
        print(f"Erro na tradução: {e}") # Log error server-side
        return jsonify({"error": f"Erro interno no servidor durante tradução: {e}"}), 500

@app.route('/audio_stream/<filename>')
def stream_audio(filename):
    try:
        # Security: Basic sanitization using os.path.basename
        safe_filename = os.path.basename(filename)

        # Double-check it's an mp3 file
        if not safe_filename.endswith('.mp3'):
             return jsonify({"error": "Tipo de arquivo inválido"}), 400

        audio_path = os.path.join(audio_dir, safe_filename)

        # Check if file exists before attempting to send
        if not os.path.exists(audio_path):
            # Corrected block for the IndentationError
            print(f"Arquivo de áudio não encontrado: {audio_path}")
            return jsonify({"error": "Arquivo de áudio não encontrado"}), 404

        # Serve the file
        return send_file(audio_path, mimetype='audio/mpeg')

    except Exception as e:
        print(f"Erro ao servir áudio {filename}: {e}") # Log error server-side
        return jsonify({"error": f"Erro interno no servidor ao servir áudio: {e}"}), 500

if __name__ == '__main__':
    # Use environment variable for port if available (Render standard)
    port = int(os.environ.get("PORT", 5000)) # Default to 5000 or common Render port
    # Listen on all interfaces, crucial for Render
    app.run(host='0.0.0.0', port=port)

