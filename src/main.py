from drive.auth import authenticate
from drive.fetch_videos import get_video_files
from storage.save_video import save_video_metadata
from storage.db import collection
from download import download_video
from summarize import generate_pdf_document_with_gemini
from audio.convert import extract_audio
from convert_to_pdf import convert_html_to_pdf
from transcription.transcribe import transcribe_audio
from datetime import datetime
import os
import time
import pdfkit

# Set wkhtmltopdf executable path here:
config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')

API_KEY = os.getenv('GEMINI_API_KEY')
CHECK_INTERVAL_SECONDS = 30
DOWNLOADS_DIR = "downloads"
AUDIOS_DIR = "audios"
GENERATED_DOCS_DIR = "generated_documents"


def process_video_pipeline(service, video_info):
    v = video_info
    print(f"\n{'='*50}")
    print(f"🎬 Processing video: {v['name']}")
    print(f"📁 Video ID: {v['id']}")
    
    file_path = os.path.join(DOWNLOADS_DIR, v['name'])
    audio_name = os.path.splitext(v['name'])[0] + ".wav"
    audio_path = os.path.join(AUDIOS_DIR, audio_name)
    
    doc = collection.find_one({"file_id": v["id"]}) or {"status": {}}
    current_status = doc.get("status", {})
    
    print(f"📊 Current status: {current_status}")
    
    if current_status.get("document_generated", False):
        print(f"✅ Document already generated for: {v['name']}")
        return
    
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        try:
            print("⬇️ Downloading video...")
            download_video(service, v['id'], v['name'])
            time.sleep(2)
            
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                raise Exception(f"Download failed - file not found or empty: {file_path}")
                
            print(f"✅ Download complete: {os.path.getsize(file_path)} bytes")
        except Exception as e:
            print(f"❌ Download failed: {e}")
            return
    else:
        print(f"✅ Video already downloaded: {os.path.getsize(file_path)} bytes")
    
    if not current_status.get("audio_extracted", False):
        try:
            print(f"🔊 Extracting audio to: {audio_path}")
            extract_audio(file_path, audio_path)
            
            if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
                raise Exception(f"Audio extraction failed - file not found or empty: {audio_path}")
            
            print(f"✅ Audio extracted: {os.path.getsize(audio_path)} bytes")
            
            collection.update_one(
                {"file_id": v["id"]},
                {"$set": {
                    "status.downloaded": True,
                    "status.audio_extracted": True,
                    "audio_path": audio_path,
                    "last_updated": datetime.utcnow()
                }},
                upsert=True
            )
        except Exception as e:
            print(f"❌ Audio extraction failed: {e}")
            return
    else:
        print(f"✅ Audio already extracted")
    
    transcription_text = None
    if not current_status.get("transcribed", False):
        try:
            if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
                raise Exception(f"Audio file not found or empty: {audio_path}")
            
            print(f"📝 Transcribing audio: {audio_path}")
            transcription_text = transcribe_audio(audio_path)
            
            if not transcription_text or len(transcription_text.strip()) == 0:
                raise Exception("Transcription returned empty text")
            
            print(f"✅ Transcription complete: {len(transcription_text)} characters")
            
            collection.update_one(
                {"file_id": v["id"]},
                {"$set": {
                    "status.transcribed": True,
                    "transcription": transcription_text,
                    "last_updated": datetime.utcnow()
                }},
                upsert=True
            )
        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            return
    else:
        doc = collection.find_one({"file_id": v["id"]})
        transcription_text = doc.get("transcription", "")
        print(f"✅ Using existing transcription: {len(transcription_text)} characters")
    
    if not current_status.get("document_generated", False):
        try:
            if not transcription_text:
                raise Exception("No transcription text available for document generation")
            
            print("🤖 Asking Gemini to create professional HTML document...")
            html_content = generate_pdf_document_with_gemini(transcription_text, v['name'])
            
            if not html_content or len(html_content.strip()) == 0:
                raise Exception("Gemini returned empty HTML content")
            
            base_name = os.path.splitext(v['name'])[0]
            html_filename = base_name + "_generated.html"
            html_filepath = os.path.join(GENERATED_DOCS_DIR, html_filename)
            
            with open(html_filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            print(f"📄 HTML file saved: {html_filepath}")
            
            pdf_filename = base_name + "_analysis.pdf"
            pdf_filepath = os.path.join(GENERATED_DOCS_DIR, pdf_filename)
            
            pdf_success = convert_html_to_pdf(html_content, pdf_filepath, v['name'])
            
            if pdf_success:
                collection.update_one(
                    {"file_id": v["id"]},
                    {"$set": {
                        "document_generated": True,
                        "generated_html": html_content,
                        "html_file_path": html_filepath,
                        "pdf_file_path": pdf_filepath,
                        "last_updated": datetime.utcnow()
                    }},
                    upsert=True
                )
                print(f"✅ Professional PDF generated by Gemini: {pdf_filepath}")
                print(f"📄 HTML source available at: {html_filepath}")
            else:
                print("⚠️ PDF generation failed, but HTML file is available.")
            
        except Exception as e:
            print(f"❌ Document generation failed: {e}")
            return
    
    print(f"🎉 Pipeline complete for: {v['name']}")

def main():
    print("🚀 Starting Google Drive monitoring with Gemini PDF generation...")
    
    if not API_KEY:
        print("❌ GEMINI_API_KEY environment variable not set!")
        print("Please set it with: export GEMINI_API_KEY=your_api_key")
        return
    
    try:
        service = authenticate()
        print("✅ Authentication successful")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return

    for dir_path in [DOWNLOADS_DIR, AUDIOS_DIR, GENERATED_DOCS_DIR]:
        os.makedirs(dir_path, exist_ok=True)
        print(f"📁 Directory ready: {dir_path}")

    while True:
        try:
            print(f"\n{'='*70}")
            print("🔍 Checking for new videos...")
            
            videos = get_video_files(service)
            print(f"📊 Found {len(videos)} video(s)")
            
            if not videos:
                print("📭 No videos found")
            else:
                for video in videos:
                    try:
                        save_video_metadata(video)
                        process_video_pipeline(service, video)
                    except Exception as e:
                        print(f"❌ Failed to process video {video.get('name', 'unknown')}: {e}")
                        continue
            
            print(f"\n⏰ Waiting {CHECK_INTERVAL_SECONDS} seconds before next check...")
            time.sleep(CHECK_INTERVAL_SECONDS)
            
        except KeyboardInterrupt:
            print("\n👋 Service stopped by user")
            break
        except Exception as e:
            print(f"❌ Unexpected error in main loop: {e}")
            print("🔄 Continuing after 10 seconds...")
            time.sleep(10)

if __name__ == "__main__":
    main()
