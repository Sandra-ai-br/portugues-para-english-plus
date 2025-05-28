from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from googletrans import Translator, LANGUAGES
from gtts import gTTS
import io
import os
import traceback # Import traceback for detailed error logging

app = Flask(__name__)
CORS(app, resources={
    r"/translate": {"origins": "https://sandra-ai-br.github.io"},
    r"/audio_stream/*": {"origins": "https://sandra-ai-br.github.io"}
})

# Initialize translator with a timeout
translator = Translator(timeout=httpx.Timeout(10.0)) # Add timeout

# Ensure the 'audio_files' directory exists
audio_dir = 'audio_files'
if not os.path.exists(audio_dir):
    try:
        os.makedirs(audio_dir)
    except OSError as e:
        print(f"Erro ao criar diretório {audio_dir}: {e}")
        # Handle error appropriately, maybe exit or log critical failure

@app.route('/')
def home():
    return jsonify({"message": "API de Tradução e Síntese de Voz - PORTUGUÊS PARA ENGLISH - Error 500 Fix v1"}) # Updated version marker

@app.route('/translate', methods=['POST'])
def translate_text():
    try:
        data = request.json
        text_pt = data.get('text')
        if not text_pt:
            print("Erro: Texto em português não fornecido na requisição.")
            return jsonify({"error": "Texto em português não fornecido"}), 400

        print(f"Recebido para traduzir: {text_pt}")

        # --- Translation Block ---
        text_en = None
        try:
            # Explicitly check if source language is supported before translating
            if 'pt' not in LANGUAGES:
                 print("Erro: Português (pt) não está listado como suportado pelo googletrans.")
                 return jsonify({"error": "Erro interno: Idioma de origem não suportado."}), 500
            
            translation = translator.translate(text_pt, src='pt', dest='en')
            text_en = translation.text
            if not text_en:
                 print("Erro: Tradução resultou em texto vazio.")
                 return jsonify({"error": "Erro interno: Falha na tradução."}), 500
            print(f"Traduzido para: {text_en}")
        except Exception as trans_error:
            print(f"Erro específico na tradução com googletrans: {trans_error}")
            print(traceback.format_exc()) # Log detailed traceback
            return jsonify({"error": f"Erro ao tentar traduzir: {trans_error}"}), 500
        # --- End Translation Block ---

        # --- Filename Sanitization ---
        try:
            safe_base_filename = "".join(c for c in text_en if c.isalnum() or c in (' ', '-')).rstrip()
            safe_base_filename = safe_base_filename.replace(' ', '_').lower()
            if not safe_base_filename:
                safe_base_filename = 'audio' # Default if text is only special chars
            audio_filename = f"{safe_base_filename}.mp3"
            audio_path = os.path.join(audio_dir, audio_filename)
            print(f"Caminho do arquivo de áudio: {audio_path}")
        except Exception as fname_error:
             print(f"Erro ao sanitizar nome do arquivo: {fname_error}")
             print(traceback.format_exc())
             return jsonify({"error": f"Erro ao preparar nome do arquivo de áudio: {fname_error}"}), 500
        # --- End Filename Sanitization ---

        # --- TTS Generation Block ---
        # Only generate if it doesn't exist to save time/resources
        if not os.path.exists(audio_path):
            print(f"Gerando novo arquivo de áudio: {audio_filename}")
            try:
                tts = gTTS(text=text_en, lang='en', slow=False)
                tts.save(audio_path)
                print("Arquivo de áudio salvo com sucesso.")
            except Exception as tts_error:
                print(f"Erro específico ao gerar/salvar áudio com gTTS: {tts_error}")
                print(traceback.format_exc())
                # Attempt to clean up potentially corrupted file if save failed partially
                if os.path.exists(audio_path):
                    try:
                        os.remove(audio_path)
                        print(f"Arquivo parcial/corrompido removido: {audio_path}")
                    except OSError as rm_error:
                        print(f"Erro ao remover arquivo parcial/corrompido: {rm_error}")
                return jsonify({"error": f"Erro ao gerar áudio: {tts_error}"}), 500
        else:
             print(f"Arquivo de áudio já existe: {audio_filename}")
        # --- End TTS Generation Block ---

        # Construct audio URL relative to the API base
        audio_url = f"/audio_stream/{audio_filename}"

        print("Retornando sucesso.")
        return jsonify({
            "text_pt": text_pt,
            "text_en": text_en,
            "audio_url": audio_url
        })

    except Exception as e:
        # General catch-all for unexpected errors in the main try block
        print(f"Erro geral inesperado na rota /translate: {e}")
        print(traceback.format_exc())
        return jsonify({"error": f"Erro interno inesperado no servidor: {e}"}), 500

@app.route('/audio_stream/<filename>')
def stream_audio(filename):
    try:
        # Security: Basic sanitization using os.path.basename
        safe_filename = os.path.basename(filename)

        # Double-check it's an mp3 file
        if not safe_filename.endswith('.mp3'):
             print(f"Erro: Tipo de arquivo inválido solicitado: {safe_filename}")
             return jsonify({"error": "Tipo de arquivo inválido"}), 400

        audio_path = os.path.join(audio_dir, safe_filename)
        print(f"Tentando servir arquivo: {audio_path}")

        # Check if file exists before attempting to send
        if not os.path.exists(audio_path):
            print(f"Erro: Arquivo de áudio não encontrado para servir: {audio_path}")
            return jsonify({"error": "Arquivo de áudio não encontrado"}), 404

        # Serve the file
        print("Servindo arquivo de áudio.")
        return send_file(audio_path, mimetype='audio/mpeg')

    except Exception as e:
        print(f"Erro inesperado ao servir áudio {filename}: {e}")
        print(traceback.format_exc())
        return jsonify({"error": f"Erro interno no servidor ao servir áudio: {e}"}), 500

# Add httpx import for Translator timeout
import httpx

if __name__ == '__main__':
    # Use environment variable for port if available (Render standard)
    port = int(os.environ.get("PORT", 10000)) # Render standard port
    # Listen on all interfaces, crucial for Render
    print(f"Iniciando servidor Flask na porta {port}")
    app.run(host='0.0.0.0', port=port)

