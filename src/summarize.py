

import os
import requests


API_KEY = os.getenv('GEMINI_API_KEY')

def generate_pdf_document_with_gemini(transcription_text: str, video_name: str) -> str:
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
                    
                    # Clean HTML code block markers if present
                    if '```html' in generated_html:
                        start = generated_html.find('```html') + 7
                        end = generated_html.rfind('```')
                        if end > start:
                            generated_html = generated_html[start:end].strip()
                    elif '```' in generated_html:
                        start = generated_html.find('```')
                        if start != -1:
                            end = generated_html.find('```', start + 3)
                            if end != -1:
                                generated_html = generated_html[start+3:end].strip()
                    
                    # Ensure proper HTML structure
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