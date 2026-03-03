from django.contrib import admin
from django.urls import path
from wallet import views 
from django.contrib.auth import views as auth_views
from wallet import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.inicio, name='inicio'),
    
    path('categorias/', views.gestionar_categorias, name='categorias'),
    path('categorias/eliminar/<int:id>/', views.eliminar_categoria, name='eliminar_categoria'),
    
    # Rutas de Autenticación
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),

    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # Rutas de la Wallet
    path('eliminar/<int:id>/', views.eliminar_transaccion, name='eliminar'),
    
    # Ruta para el registro
    path('registro/', views.registro, name='registro'),

    # RUTAS PARA RECUPERAR CONTRASEÑA (RF-03)
    path('recuperar/', auth_views.PasswordResetView.as_view(template_name='recuperar.html'), name='password_reset'),
    path('recuperar/enviado/', auth_views.PasswordResetDoneView.as_view(template_name='recuperar_enviado.html'), name='password_reset_done'),
    path('recuperar/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='recuperar_confirmar.html'), name='password_reset_confirm'),
    path('recuperar/completo/', auth_views.PasswordResetCompleteView.as_view(template_name='recuperar_completo.html'), name='password_reset_complete'),
    path('editar/<int:id>/', views.editar_transaccion, name='editar'),
    path('exportar/csv/', views.exportar_csv, name='exportar_csv'),
    path('exportar/pdf/', views.exportar_pdf, name='exportar_pdf'),
    path('suscripciones/', views.gestionar_suscripciones, name='suscripciones'),
    path('suscripciones/eliminar/<int:id>/', views.eliminar_suscripcion, name='eliminar_suscripcion'),
    path('educacion/', views.educacion, name='educacion'),
    path('inicio/', views.inicio, name='inicio'),
]




