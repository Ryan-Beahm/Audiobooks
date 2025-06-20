#!/usr/bin/env python3
from text_scraper import download_book, clean_text, extract_chapters_and_titles
from audio_generator import generate_audio_segments
import os

if __name__ == "__main__":
    # Define scraping configuration
    url = "https://www.royalroad.com/fiction/47038/book-of-the-dead/chapter/1224156/b3-prelude"
    title_selector = "div.row.fic-header h1"
    content_selector = "div.chapter-inner.chapter-content"
    next_button_selector = "div.portlet-body > div.row.nav-buttons > div.col-xs-6.col-md-4.col-md-offset-4.col-lg-3.col-lg-offset-6 > a"

    # Step 1: Download and clean the book content
    #download_book(url, title_selector, content_selector, next_button_selector)

    # Step 2: Load and clean the downloaded book text
    book_path = os.path.join("book", "book.txt")
    with open(book_path, "r", encoding="utf-8") as file:
        raw_text = file.read()
    cleaned_text = clean_text(raw_text)

    # Step 3: Extract chapter titles and content
    ordered_titles, ordered_chapters = extract_chapters_and_titles(cleaned_text)

    # Step 4: Generate audio from chapters
    generate_audio_segments(ordered_titles, ordered_chapters)

    print("Processing complete. Audio files saved to ./audio/")
