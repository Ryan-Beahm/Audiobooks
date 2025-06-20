import os  # For creating directories and file paths
import numpy as np  # For handling audio arrays
import soundfile as sf  # For writing audio files
from kokoro import KPipeline  # Text-to-speech pipeline
from IPython.display import display, Audio  # For playing audio in Jupyter

def generate_audio_segments(ordered_titles, ordered_chapters):
    pipeline = KPipeline(lang_code='a', device='cuda')  # Create a TTS pipeline instance for a specific language
    os.makedirs("audio", exist_ok=True)  # Create 'audio' directory if it doesn't exist



    segment_audio = []  # Stores audio segments for writing to file
    segment_titles = []  # Stores corresponding chapter titles
    timestamp_log = []  # Stores timestamps for each chapter
    cumulative_samples = 0  # Total audio samples accumulated so far
    sample_rate = 24000  # Fixed audio sample rate in Hz

    # Iterate through each chapter and title pair
    for idx, (title, chapter_text) in enumerate(zip(ordered_titles, ordered_chapters)):
        chapter_audio = []  # Stores audio chunks for current chapter
        chapter_start = cumulative_samples / sample_rate  # Start time (in seconds) for current chapter

        # Generate audio chunks using the pipeline
        for i, (gs, ps, audio) in enumerate(pipeline(chapter_text, voice='am_onyx', speed=1.25, )):
            print(f"Chapter {idx + 1}, chunk {i}:", gs, ps)
            display(Audio(data=audio, rate=sample_rate, autoplay=(idx == 0 and i == 0)))
            chapter_audio.append(audio)  # Append audio without checks

        concatenated = np.concatenate(chapter_audio)  # Merge all audio chunks into one array
        segment_audio.append(concatenated)  # Add to segment batch
        segment_titles.append(title)  # Add title to segment batch
        chapter_duration = len(concatenated)  # Number of samples in this chapter
        timestamp_log.append((title, chapter_start))  # Log timestamp for this chapter
        cumulative_samples += chapter_duration  # Update total samples

        # If 20 chapters accumulated or end of input, write to file
        if len(segment_audio) == 10 or idx == len(ordered_chapters) - 1:
            # Sanitize file name from title
            segment_title = segment_titles[0].replace(" ", "_").replace("/", "_")
            segment_path = os.path.join("audio", f"{segment_title}.wav")  # Audio file path
            timestamp_path = os.path.join("audio", f"{segment_title}_timestamps.txt")  # Timestamp log path

            # Delete existing files if present
            if os.path.exists(segment_path):
                os.remove(segment_path)
            if os.path.exists(timestamp_path):
                os.remove(timestamp_path)

            # Write combined audio to file
            with sf.SoundFile(segment_path, mode='w', samplerate=sample_rate, channels=1) as writer:
                for audio_data in segment_audio:
                    writer.write(audio_data)

            # Write timestamps to file in HH:MM:SS format
            with open(timestamp_path, "w") as ts_file:
                for title, start in timestamp_log:
                    minutes, seconds = divmod(int(start), 60)
                    hours, minutes = divmod(minutes, 60)
                    ts_file.write(f"{hours:02d}:{minutes:02d}:{seconds:02d} {title}\n")

            # Reset for next batch
            segment_audio, segment_titles, timestamp_log = [], [], []
            cumulative_samples = 0
