from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class RegistroForm(UserCreationForm):
    # Aquí obligamos a que el correo sea necesario
    email = forms.EmailField(required=True, label="Correo electrónico")

    class Meta:
        model = User
        # Le decimos qué campos mostrar (las contraseñas se agregan solitas)
        fields = ['username', 'email']