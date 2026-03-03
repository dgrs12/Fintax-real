from django.contrib import admin
from .models import Category, Transaction, SavingsGoal
from .models import CustomNews # Asegúrate de importar esto


# Registramos las tablas para verlas en el panel
admin.site.register(Category)
admin.site.register(Transaction)
admin.site.register(SavingsGoal)
admin.site.register(CustomNews)

