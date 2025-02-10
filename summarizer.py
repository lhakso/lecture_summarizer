import mlx_whisper
import re
import ollama
from docx import Document
from docx.shared import Pt
from datetime import date
from pathlib import Path
import smtplib
from email.message import EmailMessage
from recorder import RecordingSession
import os
from dotenv import load_dotenv

today = date.today()
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

def clean_filler_words(text: str) -> str:
    fillers = ["um", "uh", "you know", "like", "kind of", "sort of", "I mean"]
    pattern = r'\s*\b(?:' + '|'.join(fillers) + r')[,.\s]*\b'
    cleaned_text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    return cleaned_text

def send_email(path: Path) -> None:
    email_sender = EMAIL_SENDER
    email_password = EMAIL_PASSWORD
    email_receiver = EMAIL_RECEIVER
    file_path = Path(path)

    msg = EmailMessage()
    msg["Subject"] = "Lecture Summary"
    msg["From"] = email_sender
    msg["To"] = email_receiver
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
    #replace when in production
    file = Path(f'transcript{today}.txt')

    if not file.exists():
        transcript = mlx_whisper.transcribe(
            f"raw_audio{today}.wav",
            path_or_hf_repo="mlx-community/whisper-turbo"
        )["text"]

        with open(f"transcript{today}.txt", "w") as file:
            file.write(transcript)
        print("successfully transcribed")
    else:
        print("skipped transcribe")
        with open(f"transcript{today}.txt", "r") as file:
            transcript = file.read() 


    cleaned_transcript = clean_filler_words(transcript)
    print("cleaned transcript")
    target_word_count = "1000"

    response = ollama.chat(
    model='llama3:70b',
    #adjust message prompt as desired
    messages=[{'role': 'user', 'content': f'Summarize this section of my college anthropology lecture in around {target_word_count} words for me please:\r{cleaned_transcript}'}],
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

record_new = input("do you want to record a new lecture? y/n\n")

if record_new != "y":
    print("using previous recording")
else:
    session = RecordingSession(today=today)
    session.start_record()

summary = create_summary()
path = create_doc(summary)
send_email(path)