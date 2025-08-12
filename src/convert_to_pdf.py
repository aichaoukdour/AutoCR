from logging import config
import pdfkit

config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')

def convert_html_to_pdf(html_content: str, output_path: str, video_name: str):
    try:
        print(f"🔄 Converting HTML to PDF for video '{video_name}'...")
        
        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None,
            'enable-local-file-access': None,
        }
        
        pdfkit.from_string(html_content, output_path, configuration=config, options=options)
        print(f"✅ PDF successfully created at: {output_path}")
        return True
    except Exception as e:
        print(f"❌ PDF conversion failed: {e}")
        print("💡 Please ensure wkhtmltopdf is installed and accessible.")
        return False