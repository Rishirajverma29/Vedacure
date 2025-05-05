from django.shortcuts import render

import json
import os
import ast
import logging

import google.generativeai as genai
from django.http import JsonResponse, FileResponse
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.conf import settings
import pdfkit
import tempfile
from datetime import datetime


def homepage(request):
    return render(request, 'main/homepage.html')

def test(request):
    return render(request, 'main/test.html')

# Configure logging
logging.basicConfig(
    filename='error.txt',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_API_KEY = 'AIzaSyAifE1Hqp-q8D_ifWGhPkmrk--p9sr1sGs'

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}
    
    # Configure API key from Django settings
genai.configure(api_key=GEMINI_API_KEY)

# Load CSV files (ensure these are in your project's static or media directory)
MEDICINE_FILE = settings.BASE_DIR / 'data' / 'Formulation-Indications.csv'
SYMPTOMS_FILE = settings.BASE_DIR / 'data' / 'ayurvedic_symptoms_desc.csv'

def load_data():
    """Load symptoms and medicine data as strings."""
    with open(MEDICINE_FILE, 'r') as file:
        medicine_data = file.read()
    with open(SYMPTOMS_FILE, 'r') as file:
        symptoms_data = file.read()
    return medicine_data, symptoms_data

def configure_gemini_model(medicine_data, symptoms_data):
    """Configure Gemini model with system instructions."""
    
    symptom_model = genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        generation_config=generation_config,
        system_instruction=f"Using the provided list of symptoms and their descriptions: {symptoms_data}, "
        "ask the user about their symptoms. Analyze the user's input"
        "containing a minimum of one symptom (preferred two and maximum 3) that match the user's response. "
        "Format the output strictly (nested list) as: ['symptom1', 'symptom2', ...]"
    )
    
    medicine_model = genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        generation_config=generation_config,
        system_instruction=f"Using the provided list of medicines, diseases, and their associated symptoms: {medicine_data}, "
        "analyze the symptoms identified. Compare the symptoms with the diseases in the table and suggest "
        "the 3 most suitable medicine(s). Return the output strictly in nested list format: "
        "['medicine1', 'Dose', 'dispensing Pack Size'], ['medicine2', 'Dose', 'dispensing Pack Size']"
    )
    
    return symptom_model, medicine_model

def generate_prescription_pdf(request):
    """
    Generate a PDF prescription based on symptoms and medicines.
    Expects the symptoms and medicines to be passed in the session or request.
    """
    try:
        symptoms = request.session.get('symptoms', []) or request.POST.getlist('symptoms', [])
        medicines = request.session.get('medicines', []) or request.POST.getlist('medicines', [])
        
        name = request.session.get('name', '') or request.POST.get('name', '')
        age = request.session.get('age', '') or request.POST.get('age', '')
        blood_group = request.session.get('blood_group', '') or request.POST.get('blood_group', '')
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Render HTML template
        html_content = render_to_string('main/prescription_template.html', {
            'symptoms': symptoms,
            'medicines': medicines,
            'name': name,
            'age': age,
            'blood_group': blood_group,
            'current_date': current_date
        })
        
        # Create a temporary file to store the PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
            pdfkit.from_string(html_content, temp_pdf.name, 
                               configuration=pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf'))
            
            temp_pdf = open(temp_pdf.name, 'rb')
            
            response = FileResponse(temp_pdf, 
                                    as_attachment=True, 
                                    filename='medical_recommendation.pdf')
            return response
    
    except Exception as e:
        logging.error(f"PDF Generation Error: {str(e)}")
        return render(request, 'main/error.html', {'error': str(e)})

@require_http_methods(["POST"])
def recommend_medicine(request):
    try:
        medicine_data, symptoms_data = load_data()
        logging.debug("Loaded data successfully")

        symptom_model, medicine_model = configure_gemini_model(medicine_data, symptoms_data)
        logging.debug("Configured Gemini models successfully")

        user_symptoms = request.POST.get('symptoms', '')
        logging.debug(f"User symptoms: {user_symptoms}")

        symptom_chat = symptom_model.start_chat(history=[])
        medicine_chat = medicine_model.start_chat(history=[])
        logging.debug("Started chat sessions")

        symptom_response = symptom_chat.send_message(user_symptoms)
        logging.debug(f"Symptom response: {symptom_response.text}")

        try:
            symptoms_str = symptom_response.text.strip('```json\n').strip('```')
            possible_symptoms = ast.literal_eval(symptoms_str)
        except (ValueError, SyntaxError) as e:
            logging.error(f"Error parsing symptoms: {str(e)}")
            possible_symptoms = []
        logging.debug(f"Possible symptoms: {possible_symptoms}")
        logging.debug(f"Data type of possible_symptoms: {type(possible_symptoms)}")

        medicine_response = medicine_chat.send_message(f"Symptoms: {', '.join(possible_symptoms)}")
        logging.debug(f"Medicine response: {medicine_response.text}")

        try:
            medicines_str = medicine_response.text.strip('```json\n').strip('```')
            recommended_medicines = ast.literal_eval(medicines_str)
        except (ValueError, SyntaxError) as e:
            logging.error(f"Error parsing medicines: {str(e)}")
            recommended_medicines = []
        logging.debug(f"Recommended medicines: {recommended_medicines}")

        user_name = request.POST.get('name', '')
        request.session['name'] = user_name

        user_age = request.POST.get('age', '')
        request.session['age'] = user_age

        user_blood_group = request.POST.get('blood_group', '')
        request.session['blood_group'] = user_blood_group

        request.session['symptoms'] = possible_symptoms
        request.session['medicines'] = recommended_medicines

        return render(request, 'main/recommendations_results.html', {
            'symptoms': possible_symptoms,
            'medicines': recommended_medicines
        })

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'symptoms': [],
            'medicines': []
        }, status=500)