import mlx_whisper
import re
import ollama
import subprocess
import time
from docx import Document
from docx.shared import Pt
from datetime import date
from pathlib import Path
import smtplib
from email.message import EmailMessage
from recorder import RecordingSession
import os
from dotenv import load_dotenv

load_dotenv()
today = date.today()
target_word_count = "1500"
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVERS = os.getenv("EMAIL_RECEIVERS")

def entry():
    record_new = input("do you want to record a new lecture? y/n\n")

    if record_new != "y":
        print("using previous recording")
    else:
        session = RecordingSession(today=today)
        session.start_record()

    # start ollama in background
    ollama_process = subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("ollama server started!")
    time.sleep(2)  # give time to initialize
    
    try:
        summary = create_summary()
        path = create_doc(summary)
        send_email(path)

    finally:
        ollama_process.terminate()
        print("ollama server stopped.")

def clean_filler_words(text: str) -> str:
    fillers = ["um", "uh", "you know", "like", "kind of", "sort of", "I mean"]
    pattern = r'\s*\b(?:' + '|'.join(fillers) + r')[,.\s]*\b'
    cleaned_text = re.sub(pattern, ' ', text, flags=re.IGNORECASE)
    return cleaned_text

def send_email(path: Path) -> None:
    email_sender = EMAIL_SENDER
    email_password = EMAIL_PASSWORD
    email_receivers = EMAIL_RECEIVERS
    file_path = Path(path)

    msg = EmailMessage()
    msg["Subject"] = "Lecture Summary"
    msg["From"] = email_sender
    msg["To"] = email_receivers
    msg.set_content(f"Notes for {today.strftime("%B %d, %Y")} lecture")

    with open(file_path, 'rb') as file:
        msg.add_attachment(    
        file.read(),
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=file_path.name)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(email_sender, email_password)
        smtp.send_message(msg)
    print("successfully sent email")

def create_summary() -> str:
    file = Path(f'transcripts/transcript{today}.txt')

    if not file.exists():
        transcript = mlx_whisper.transcribe(
            f"audio/raw_audio{today}.wav",
            path_or_hf_repo="mlx-community/whisper-turbo"
        )["text"]

        with open(f"transcripts/transcript{today}.txt", "w") as file:
            file.write(transcript)
        print("successfully transcribed")
    else:
        print("skipped transcribe")
        with open(f"transcripts/transcript{today}.txt", "r") as file:
            transcript = file.read() 


    cleaned_transcript = clean_filler_words(transcript)
    print("cleaned transcript")
    response = ollama.chat(
    model='llama3:70b',
    #adjust message prompt as desired - second commented one is for testing
    messages=[{'role': 'user', 'content': f'Please summarize the following lecture transcript into a comprehensive note-style summary that is approximately {target_word_count} words long. The summary should use a mixed format:\nBullet Points: Use bullet points to list the key ideas, main topics, and critical concepts from the lecture. Each bullet point should be concise and capture the essential information.\nExplanatory Paragraphs: In addition to the bullet points, include paragraphs that provide additional context, elaborate on the bullet points, and explain examples or complex ideas in detail.\n\nYour summary should be organized, clear, and easy to scan, enabling quick reference while still offering enough detail for deep understanding. Ensure that the overall structure is logical—group related bullet points together, and follow them with paragraphs that discuss those points in more detail. \nHere is the lecture transcript:\n{cleaned_transcript}\nGenerate a summary that captures all major points and presents the material in a structured, readable note-style format."'}],
    #messages=[{'role': 'user', 'content':f"please summarize this shortly: \n{cleaned_transcript}"}],
    stream=False,
    )
    summary = response['message']['content']
    return(summary)

def create_doc(summary: str) -> str:

    doc_path = os.getenv("DOC_PATH") + f"lecture_{today}.docx"

    doc = Document()

    doc.add_heading(f'Lecture Summary from {today.strftime("%B %d, %Y")}', level=1)

    code_paragraph = doc.add_paragraph()
    code_paragraph.alignment = 0  # left align
    code_run = code_paragraph.add_run(summary)
    code_paragraph.style = 'Normal'
    code_run.font.size = Pt(11)
    doc.save(doc_path)
    return doc_path

if __name__ == "__main__":
    entry()