from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now

# 1. EL NUEVO MODELO DE CATEGORÍAS (CON PRESUPUESTO)
class Category(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    is_expense = models.BooleanField(default=True) 
    
    # 🔥 NUEVO: Límite mensual (RF-17). Si está en 0, significa que no hay límite.
    budget_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.name
# 2. TU MODELO DE TRANSACCIONES (CORREGIDO)
class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Dejamos UNA SOLA categoría, permitiendo que esté en blanco para los ahorros
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    
    is_expense = models.BooleanField(default=True)
    date = models.DateField(default=now) 
    note = models.CharField(max_length=150, blank=True, null=True)
    
    # 🔥 ESTA ES LA LÍNEA QUE FALTABA (La que marca el error rojo) 🔥
    is_transfer = models.BooleanField(default=False) 

    def __str__(self):
        cat_name = self.category.name if self.category else "Sin categoría"
        return f"{cat_name} - ${self.amount}"

# 3. TU MODELO DE AHORROS
class SavingsGoal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2, default=10000)
    name = models.CharField(max_length=100, default="Mi Meta")
    saved_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.name} - ${self.target_amount}"
    
    # 4. EL NUEVO MODELO DE SUSCRIPCIONES / GASTOS FIJOS 🔁
class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)  # Ej. Netflix, Renta, Gym
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    billing_day = models.IntegerField(help_text="Día del mes en que se cobra (1-31)")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - ${self.amount}"

class CustomNews(models.Model):
    title = models.CharField(max_length=200, verbose_name="Título")
    description = models.TextField(verbose_name="Descripción breve")
    link = models.URLField(blank=True, null=True, verbose_name="Link de la noticia o video")
    image_url = models.URLField(blank=True, null=True, verbose_name="Link de la imagen")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title