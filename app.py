from flask import Flask, request, jsonify, render_template
import os
import logging
import pyttsx3
from pydub import AudioSegment
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Initialize Flask app
app = Flask(__name__)

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)

# Ensure the static folder exists if not
if not os.path.exists('static'):
    os.makedirs('static')

# Function to split text into manageable chunks for pyttsx3
def split_text(text, max_length=200):
    words = text.split()
    chunks = []
    current_chunk = []

    for word in words:
        if len(" ".join(current_chunk) + " " + word) <= max_length:
            current_chunk.append(word)
        else:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks

# Function to set the voice to female
def set_female_voice(engine):
    voices = engine.getProperty('voices')
    for voice in voices:
        if "female" in voice.name.lower():
            engine.setProperty('voice', voice.id)
            logging.debug(f"Female voice selected: {voice.name}")
            return
    logging.debug("No female voice found, using default voice.")

# Generate audio for lengthy text with emotion-specific tone
def generate_audio(text, audio_path, emotion):
    chunks = split_text(text)
    combined_audio = AudioSegment.empty()

    # Initialize pyttsx3 engine
    engine = pyttsx3.init()

    # Set voice to female
    set_female_voice(engine)

    for i, chunk in enumerate(chunks):
        logging.debug(f"Generating audio for chunk {i + 1}/{len(chunks)}")

        # Adjust speech parameters based on emotion
        if emotion == "Positive":
            engine.setProperty('rate', 150)  # Faster rate for a happy tone
            engine.setProperty('pitch', 150)  # Higher pitch for a happy tone
            engine.setProperty('volume', 1.0)  # Normal volume
        elif emotion == "Negative":
            engine.setProperty('rate', 90)  # Slower rate for a sad tone
            engine.setProperty('pitch', 50)  # Lower pitch for a sad tone
            engine.setProperty('volume', 0.7)  # Lower volume for sadness
        else:
            engine.setProperty('rate', 120)  # Default rate for neutral tone
            engine.setProperty('pitch', 100)  # Default pitch
            engine.setProperty('volume', 1.0)  # Normal volume

        chunk_path = os.path.join("static", f"chunk_{i}.mp3")
        engine.save_to_file(chunk, chunk_path)
        engine.runAndWait()

        # Load the chunk audio and append to the combined audio
        chunk_audio = AudioSegment.from_file(chunk_path)
        combined_audio += chunk_audio

        # Delete the temporary chunk file
        os.remove(chunk_path)

    # Export the combined audio
    combined_audio.export(audio_path, format="wav")
    logging.debug(f"Audio successfully generated and saved to {audio_path}")

# Emotion detection function using VaderSentiment
def detect_emotion(text):
    analyzer = SentimentIntensityAnalyzer()
    sentiment_score = analyzer.polarity_scores(text)
    compound_score = sentiment_score['compound']
    
    if compound_score >= 0.05:
        return "Positive"
    elif compound_score <= -0.05:
        return "Negative"
    else:
        return "Neutral"

# Serve the HTML file for the frontend
@app.route('/')
def home():
    return render_template('index.html')  # Ensure `index.html` is in the `templates` folder

# Endpoint to generate audio based on the text
@app.route('/generate-audio', methods=['POST'])
def generate_audio_media():
    logging.debug("Received request to generate audio")
    data = request.get_json()
    text = data.get('text', '')

    # Ensure text is provided
    if not text:
        logging.error("Text is missing.")
        return jsonify({"error": "Text is required"}), 400

    try:
        # Detect emotion
        emotion = detect_emotion(text)
        logging.debug(f"Detected emotion: {emotion}")

        # Generate audio with emotion-specific tone
        logging.debug(f"Generating audio for text: {text}")
        audio_path = os.path.join('static', "output.wav")  # Save audio in the static folder
        generate_audio(text, audio_path, emotion)

        # Create a response with audio file path and detected emotion
        response = jsonify({
            "audio_path": f"/static/output.wav",
            "emotion": emotion  # Include detected emotion in the response
        })
        return response
    except Exception as e:
        logging.error(f"Error generating audio: {str(e)}")
        return jsonify({"error": f"Error: {str(e)}"}), 500

# Run the app
if __name__ == '__main__':
    logging.debug("Starting Flask app on port 5007")
    app.run(debug=True, port=5002)

