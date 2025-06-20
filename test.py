# Import necessary libraries
from selenium import webdriver  # For automating browser interaction
from selenium.webdriver.chrome.service import Service  # For setting up Chrome WebDriver service
from selenium.webdriver.chrome.options import Options  # For customizing Chrome options
from selenium.webdriver.common.by import By  # For specifying element search strategies
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException, StaleElementReferenceException  # For handling common Selenium exceptions
from kokoro import KPipeline  # Text-to-speech pipeline from kokoro
from IPython.display import display, Audio  # For displaying audio playback in notebooks
import time  # For adding delays
import soundfile as sf  # For saving audio files
import re  # For regular expressions
import os  # For file and directory handling
import numpy as np  # For numerical operations (used in audio concatenation)

# Define patterns to remove lines made of decorative characters only
DECORATIVE_PATTERNS = [
    r'^\s*[=~\-*_\.]{3,}\s*$',  # Match lines of 3+ symbols only
]

# Precompile regex patterns for faster matching
compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in DECORATIVE_PATTERNS]

# Pattern to recognize chapter headers in the format "Book X and Chapter Y"
chapter_header_pattern = re.compile(r"^Book (\d+) and Chapter (\d+)")

# Clean text: remove decorative lines, convert shorthand chapter formats like B3C12
# Returns cleaned version of input text

def clean_text(text):
    cleaned_lines = []  # Holds non-decorative cleaned lines
    for line in text.splitlines():
        stripped_line = line.strip()  # Remove leading/trailing spaces
        if any(pattern.match(stripped_line) for pattern in compiled_patterns):
            print(f"Skipping decorative line: {line}")  # Debug output
            continue  # Skip decorative lines
        # Expand shorthand chapter codes to full format (e.g., B3C12 -> Book 3 and Chapter 12)
        line = re.sub(r'\bB(\d+)(C(\d+))?\b', lambda m: f"Book {m.group(1)}" + (f" and Chapter {m.group(3)}" if m.group(3) else ""), line)
        cleaned_lines.append(line)  # Append cleaned line
    cleaned_text = "\n".join(cleaned_lines)  # Join lines back into full text
    return cleaned_text

# Split and title chapters in one pass
# Returns two lists: ordered_titles and ordered_chapters

def extract_chapters_and_titles(text):
    ordered_titles = []  # Stores chapter titles
    ordered_chapters = []  # Stores corresponding chapter text
    current = []  # Accumulates current chapter's lines
    current_title = None  # Current chapter's title

    for line in text.splitlines():
        match = chapter_header_pattern.match(line)  # Check if line is a chapter header
        if match:
            if current:
                ordered_chapters.append("\n".join(current))  # Save current chapter
                ordered_titles.append(current_title or "segment")  # Save its title
                current = []
            current_title = f"Book_{match.group(1)}_Chapter_{match.group(2)}"  # Generate chapter title
        current.append(line)  # Add line to current chapter

    if current:
        ordered_chapters.append("\n".join(current))  # Save last chapter
        ordered_titles.append(current_title or "segment")

    return ordered_titles, ordered_chapters

# Function to scrape the book content using Selenium
# Downloads and cleans chapters, writes cleaned output to file

def download_book(url, title_selector, content_selector, next_button_selector):
    options = Options()
    options.add_argument("--headless")  # Run in headless mode (no browser UI)
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")  # Set window size
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)  # Launch browser
    driver.get(url)  # Navigate to initial chapter
    time.sleep(1)  # Wait for page to load

    os.makedirs("book", exist_ok=True)  # Ensure output directory exists
    book_path = os.path.join("book", "book.txt")  # Path to save scraped content

    with open(book_path, "w", encoding="utf-8") as f:
        while True:
            try:
                title_elem = driver.find_element(By.CSS_SELECTOR, title_selector)  # Get chapter title
                title = f"{title_elem.text}"

                content_elem = driver.find_element(By.CSS_SELECTOR, content_selector)  # Get chapter content
                content = content_elem.text

                formatted_title = re.sub(r'\bB(\d+)(C(\d+))?\b', lambda m: f"Book {m.group(1)}" + (f" and Chapter {m.group(3)}" if m.group(3) else ""), title)  # Normalize title

                full_text = f"{formatted_title}\n\n{content}"  # Combine title and content
                cleaned_text = clean_text(full_text)  # Clean the combined text
                f.write(cleaned_text + "\n\n" + "="*80 + "\n\n")  # Write to file with divider
                print(f"Appended: {formatted_title}")  # Debug output

                next_button = driver.find_element(By.CSS_SELECTOR, next_button_selector)  # Find 'Next' button
                driver.execute_script("arguments[0].click();", next_button)  # Click it
                time.sleep(1)  # Wait for next chapter to load

            except (NoSuchElementException, ElementNotInteractableException, StaleElementReferenceException):
                print("No more chapters or button is not clickable.")  # Stop if no next chapter
                break
    driver.quit()  # Close browser

# Audio generation function
# Uses kokoro TTS to create audio, groups chapters in 20s, writes timestamps

def generate_audio_segments(ordered_titles, ordered_chapters):
    pipeline = KPipeline(lang_code='a')  # Initialize TTS engine
    os.makedirs("audio", exist_ok=True)  # Ensure output folder exists
    segment_audio = []  # Accumulate audio for current segment
    segment_titles = []  # Track titles in current segment
    timestamp_log = []  # Track timestamps for chapters
    cumulative_samples = 0  # Running total of audio length (in samples)
    sample_rate = 24000  # Audio sample rate

    for idx, (title, chapter_text) in enumerate(zip(ordered_titles, ordered_chapters)):
        chapter_audio = []  # Audio chunks for one chapter
        chapter_start = cumulative_samples / sample_rate  # Start timestamp in seconds

        for i, (gs, ps, audio) in enumerate(pipeline(chapter_text, voice='am_onyx', speed=1.25)):
            print(f"Chapter {idx + 1}, chunk {i}:", gs, ps)
            display(Audio(data=audio, rate=sample_rate, autoplay=(idx == 0 and i == 0)))

            if isinstance(audio, np.ndarray) and audio.size > 0:
                chapter_audio.append(audio)
            else:
                print(f"Warning: Empty or invalid audio in Chapter {idx + 1}, chunk {i}. Skipping.")


        if not chapter_audio:
            print(f"No valid audio chunks for chapter {title}, skipping.")
            continue

        concatenated = np.concatenate(chapter_audio)  # Combine all valid chunks
        segment_audio.append(concatenated)  # Add to segment
        segment_titles.append(title)  # Add title to current segment
        chapter_duration = len(concatenated)  # Length of audio in samples
        timestamp_log.append((title, chapter_start))  # Record start time
        cumulative_samples += chapter_duration  # Update running total

        # Write out file every 20 chapters or at the end
        if len(segment_audio) == 20 or idx == len(ordered_chapters) - 1:
            segment_title = segment_titles[0]  # Use first title for filename
            segment_path = os.path.join("audio", f"Audio_{segment_title}.wav")  # Path to save audio
            timestamp_path = os.path.join("audio", f"Audio_{segment_title}_timestamps.txt")  # Path for timestamps

            if os.path.exists(segment_path):
                os.remove(segment_path)  # Remove existing file if present
            if os.path.exists(timestamp_path):
                os.remove(timestamp_path)

            with sf.SoundFile(segment_path, mode='w', samplerate=sample_rate, channels=1) as writer:
                for audio_data in segment_audio:
                    writer.write(audio_data)  # Write audio to file

            with open(timestamp_path, "w") as ts_file:
                for title, start in timestamp_log:
                    minutes, seconds = divmod(int(start), 60)
                    hours, minutes = divmod(minutes, 60)
                    ts_file.write(f"{hours:02d}:{minutes:02d}:{seconds:02d} {title}\n")  # Write formatted timestamp

            # Reset segment data
            segment_audio = []
            segment_titles = []
            timestamp_log = []
            cumulative_samples = 0

# Main execution
if __name__ == "__main__":
    # Define the selectors and initial URL to scrape
    url = "https://www.royalroad.com/fiction/47038/book-of-the-dead/chapter/1224156/b3-prelude"  # Starting URL
    title_selector = "div.row.fic-header h1"  # CSS selector for title
    content_selector = "div.chapter-inner.chapter-content"  # CSS selector for chapter content
    next_button_selector = "div.portlet-body > div.row.nav-buttons > div.col-xs-6.col-md-4.col-md-offset-4.col-lg-3.col-lg-offset-6 > a"  # CSS selector for next button

    # Start the scraping process (disabled for safety)
    download_book(url, title_selector, content_selector, next_button_selector)

    # Read and clean the downloaded text
    book_path = os.path.join("book", "book.txt")  # Path to book file
    with open(book_path, "r") as file:
        raw_text = file.read()  # Read full file
        used_text = clean_text(raw_text)  # Clean text
        ordered_titles, ordered_chapters = extract_chapters_and_titles(used_text)  # Split into titles and chapters

    # Generate audio segments
    generate_audio_segments(ordered_titles, ordered_chapters)
