from django.test import TestCase, Client
from django.urls import reverse

class MedicineRecommendationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('recommend_medicine')

    def test_recommend_medicine(self):
        # Simulate a POST request with symptoms
        response = self.client.post(self.url, {'symptoms': 'fever, cough'})
        
        # Check that the response is 200 OK
        if response.status_code != 200:
            print("Response status code:", response.status_code)
            print("Response content:", response.content)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that the response contains the expected keys
        response_data = response.json()
        self.assertIn('symptoms', response_data)
        self.assertIn('medicines', response_data)
        
        # Check that the symptoms and medicines are not empty
        self.assertTrue(len(response_data['symptoms']) > 0)
        self.assertTrue(len(response_data['medicines']) > 0)
        
class PDFGenerationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('generate_prescription')
        
        # Set up session data
        session = self.client.session
        session['symptoms'] = ['fever', 'cough']
        session['medicines'] = [['Paracetamol', '500mg', '10 tablets'], ['Cough Syrup', '10ml', '1 bottle']]
        session['name'] = 'John Doe'
        session['age'] = '30'
        session['blood_group'] = 'O+'
        session.save()

    def test_generate_prescription_pdf(self):
        # Simulate a GET request to generate the PDF
        response = self.client.get(self.url)
        
        # Check that the response is 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Check that the response is a file response with PDF content
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith('attachment; filename="medical_recommendation.pdf"'))