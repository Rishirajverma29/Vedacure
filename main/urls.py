from django.urls import path
from .views import homepage, test, recommend_medicine, generate_prescription_pdf

urlpatterns = [
    path('', homepage, name='homepage'),
    path('test/', test, name='test'),
    path('recommend-medicine/', recommend_medicine, name='recommend_medicine'),
    path('generate-prescription/', generate_prescription_pdf, name='generate_prescription'),
]
