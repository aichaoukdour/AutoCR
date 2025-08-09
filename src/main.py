from drive.auth import authenticate
from drive.fetch_videos import get_video_files
from storage.save_video import save_video_metadata
from storage.db import collection
from download import download_video
from audio.convert import extract_audio
from transcription.transcribe import transcribe_audio
from datetime import datetime
import os
import time
import requests
# PDF conversion library will be imported when needed

API_KEY = os.getenv('GEMINI_API_KEY')
CHECK_INTERVAL_SECONDS = 30
DOWNLOADS_DIR = "downloads"
AUDIOS_DIR = "audios"
GENERATED_DOCS_DIR = "generated_documents"

def generate_pdf_document_with_gemini(transcription_text: str, video_name: str) -> str:
    """Ask Gemini to generate HTML that will be converted to PDF"""
    if not API_KEY:
        raise Exception("GEMINI_API_KEY environment variable not set")
    
    print(f"📡 Asking Gemini to create PDF-ready HTML document...")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}"
    
    prompt = f"""
Tu es un expert en création de documents professionnels. Crée un document HTML COMPLET et professionnel à partir de la transcription de cette vidéo: "{video_name}".

IMPORTANT: Génère SEULEMENT du HTML propre, sans aucun texte explicatif avant ou après. Le HTML doit être prêt à être converti en PDF.

Exigences pour le HTML:
1. Structure complète avec <!DOCTYPE html>, <head>, et <body>
2. CSS intégré dans <style> pour un design professionnel
3. Couleurs professionnelles (bleu foncé, gris, blanc)
4. Typographie claire et lisible
5. Sections bien organisées avec titres et sous-titres
6. Résumé exécutif en début
7. Points clés mis en évidence
8. Conclusion claire
9. Design responsive et clean
10. Marges et espacements appropriés pour impression PDF

Structure suggérée:
- En-tête avec titre principal et informations vidéo
- Résumé exécutif (encadré coloré)
- Sections principales du contenu
- Points clés (liste numérotée ou à puces)
- Conclusion
- Pied de page avec date de génération

Transcription à analyser et structurer:
{transcription_text}

Génère maintenant le HTML complet:
    """
    
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "maxOutputTokens": 4000,
            "temperature": 0.2
        }
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=90)
        
        print(f"📡 Gemini API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    generated_html = candidate['content']['parts'][0]['text']
                    
                    # Clean the HTML - remove markdown code blocks if present
                    if '```html' in generated_html:
                        start = generated_html.find('```html') + 7
                        end = generated_html.rfind('```')
                        if end > start:
                            generated_html = generated_html[start:end].strip()
                    elif '```' in generated_html:
                        # Remove any code blocks
                        start = generated_html.find('```')
                        if start != -1:
                            # Find the end of first code block
                            end = generated_html.find('```', start + 3)
                            if end != -1:
                                generated_html = generated_html[start+3:end].strip()
                    
                    # Ensure we have proper HTML
                    if not generated_html.strip().startswith('<!DOCTYPE') and not generated_html.strip().startswith('<html'):
                        generated_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analyse - {video_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .content {{ max-width: 800px; margin: 0 auto; }}
    </style>
</head>
<body>
    <div class="content">
        {generated_html}
    </div>
</body>
</html>"""
                    
                    print(f"✅ Generated HTML document: {len(generated_html)} characters")
                    return generated_html
                else:
                    raise Exception(f"Unexpected response structure: {result}")
            else:
                raise Exception(f"No candidates in response: {result}")
        else:
            error_detail = response.text
            raise Exception(f"API Error {response.status_code}: {error_detail}")
            
    except requests.exceptions.Timeout:
        raise Exception("API request timed out after 90 seconds")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error: {str(e)}")

def convert_html_to_pdf(html_content: str, output_path: str, video_name: str):
    """Convert HTML to PDF using available library or skip if none available"""
    try:
        print(f"🔄 Attempting to convert HTML to PDF...")
        
        # Method 1: Using pdfkit
        try:
            import pdfkit
            options = {
                'page-size': 'A4',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': "UTF-8",
                'no-outline': None,
                'enable-local-file-access': None
            }
            pdfkit.from_string(html_content, output_path, options=options)
            print(f"✅ PDF created successfully with pdfkit: {output_path}")
            return True
            
        except ImportError:
            print("⚠️ pdfkit not available")
            
        # Method 2: Try WeasyPrint (if available)
        try:
            import weasyprint
            html_with_title = html_content.replace(
                '<title>', 
                f'<title>Analyse Vidéo - {video_name}</title><meta name="author" content="Système IA">'
            )
            weasyprint.HTML(string=html_with_title).write_pdf(output_path)
            print(f"✅ PDF created successfully with WeasyPrint: {output_path}")
            return True
            
        except ImportError:
            print("⚠️ WeasyPrint not available")
            
        print("⚠️ No PDF conversion library available. HTML file will be generated instead.")
        print("💡 You can manually convert HTML to PDF using your browser (Print > Save as PDF)")
        return False
                
    except Exception as e:
        print(f"❌ PDF conversion failed: {e}")
        print("💡 HTML file is still available for manual conversion")
        return False

def process_video_pipeline(service, video_info):
    """Process a single video through the entire pipeline"""
    v = video_info
    print(f"\n{'='*50}")
    print(f"🎬 Processing video: {v['name']}")
    print(f"📁 Video ID: {v['id']}")
    
    file_path = os.path.join(DOWNLOADS_DIR, v['name'])
    audio_name = os.path.splitext(v['name'])[0] + ".wav"
    audio_path = os.path.join(AUDIOS_DIR, audio_name)
    
    # Get current status from database
    doc = collection.find_one({"file_id": v["id"]}) or {"status": {}}
    current_status = doc.get("status", {})
    
    print(f"📊 Current status: {current_status}")
    
    # Check if final document already exists
    if current_status.get("document_generated", False):
        print(f"✅ Document already generated for: {v['name']}")
        return
    
    # Step 1: Download video if needed
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
    
    # Step 2: Extract audio if needed
    if not current_status.get("audio_extracted", False):
        try:
            print(f"🔊 Extracting audio to: {audio_path}")
            extract_audio(file_path, audio_path)
            
            if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
                raise Exception(f"Audio extraction failed - file not found or empty: {audio_path}")
            
            print(f"✅ Audio extracted: {os.path.getsize(audio_path)} bytes")
            
            # Update status
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
    
    # Step 3: Transcribe audio if needed
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
            
            # Update status
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
        # Get existing transcription from database
        doc = collection.find_one({"file_id": v["id"]})
        transcription_text = doc.get("transcription", "")
        print(f"✅ Using existing transcription: {len(transcription_text)} characters")
    
    # Step 4: Generate PDF document with Gemini
    if not current_status.get("document_generated", False):
        try:
            if not transcription_text:
                raise Exception("No transcription text available for document generation")
            
            print("🤖 Asking Gemini to create professional HTML document...")
            html_content = generate_pdf_document_with_gemini(transcription_text, v['name'])
            
            if not html_content or len(html_content.strip()) == 0:
                raise Exception("Gemini returned empty HTML content")
            
            # Save HTML file for debugging
            base_name = os.path.splitext(v['name'])[0]
            html_filename = base_name + "_generated.html"
            html_filepath = os.path.join(GENERATED_DOCS_DIR, html_filename)
            
            with open(html_filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            print(f"📄 HTML file saved: {html_filepath}")
            
            # Convert HTML to PDF
            pdf_filename = base_name + "_analysis.pdf"
            pdf_filepath = os.path.join(GENERATED_DOCS_DIR, pdf_filename)
            
            pdf_success = convert_html_to_pdf(html_content, pdf_filepath, v['name'])
            
            if pdf_success:
                # Update database
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
                print("⚠️ PDF conversion failed, but HTML file is available")
            
        except Exception as e:
            print(f"❌ Document generation failed: {e}")
            return
    
    print(f"🎉 Pipeline complete for: {v['name']}")

def main():
    print("🚀 Starting Google Drive monitoring with Gemini PDF generation...")
    
    # Check API key
    if not API_KEY:
        print("❌ GEMINI_API_KEY environment variable not set!")
        print("Please set it with: export GEMINI_API_KEY=your_api_key")
        return
    
    # Check PDF conversion libraries
    print("🔧 Checking PDF conversion capabilities...")
    try:
        import pdfkit
        print("✅ pdfkit available for PDF conversion")
    except ImportError:
        try:
            import weasyprint
            print("✅ WeasyPrint available for PDF conversion")
        except ImportError:
            print("⚠️ No PDF conversion library found.")
            print("💡 HTML files will be generated. You can convert them manually:")
            print("   1. Open HTML file in browser")
            print("   2. Press Ctrl+P (Print)")
            print("   3. Choose 'Save as PDF'")
            print("   Alternative: Install pdfkit with: pip install pdfkit")
    
    # Authenticate
    try:
        service = authenticate()
        print("✅ Authentication successful")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return

    # Create directories
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