import os
import re
import tempfile
import pdfkit

# Path to wkhtmltopdf executable
WKHTMLTOPDF_PATH = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"

config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)

def sanitize_filename(filename: str) -> str:
    """
    Removes unsafe characters from filenames for compatibility with wkhtmltopdf.
    """
    return re.sub(r'[^\w\-_\. ]', '_', filename)

def convert_html_to_pdf(html_content: str, output_path: str, video_name: str):
    try:
        print(f"🔄 Converting HTML to PDF for video '{video_name}'...")

        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Sanitize the output file name
        safe_output_path = sanitize_filename(output_path)

        # Save HTML to a temporary file for debugging
        temp_html_path = os.path.join(tempfile.gettempdir(), f"{sanitize_filename(video_name)}.html")
        with open(temp_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"📝 Temporary HTML saved for debugging at: {temp_html_path}")

        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': '',
            'enable-local-file-access': ''  # IMPORTANT for local images/CSS
        }

        # Debug: Print exact command
        wk_command = f'"{WKHTMLTOPDF_PATH}" --enable-local-file-access "{temp_html_path}" "{safe_output_path}"'
        print(f"🐞 Debug command: {wk_command}")

        # Convert HTML to PDF
        pdfkit.from_file(temp_html_path, safe_output_path, configuration=config, options=options)

        print(f"✅ PDF successfully created at: {safe_output_path}")
        return True

    except Exception as e:
        print(f"❌ PDF conversion failed: {e}")
        print("💡 Please ensure wkhtmltopdf is installed and accessible.")
        return False
