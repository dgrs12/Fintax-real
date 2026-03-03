from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.db.models import Sum
from .models import Transaction, Category, SavingsGoal, Subscription
from .forms import RegistroForm
from datetime import datetime
from decimal import Decimal
import csv
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.contrib import messages
import requests
from .models import CustomNews
from django.contrib.auth.models import User


@login_required
def inicio(request):
    categorias = Category.objects.filter(user=request.user)

    # TRAER O CREAR LA META Y BÓVEDA
    meta_obj, created = SavingsGoal.objects.get_or_create(
        user=request.user, 
        defaults={'target_amount': 10000, 'name': 'Mi Meta de Ahorro', 'saved_amount': 0}
    )

    hoy = datetime.today()

    if request.method == 'POST':
        # 1. RECIBIR NUEVO REGISTRO (Ingreso o Gasto)
        amount = request.POST.get('amount')
        category_id = request.POST.get('category')
        date = request.POST.get('date')
        note = request.POST.get('note')

        if amount and category_id and date:
            categoria_obj = Category.objects.get(id=category_id, user=request.user)
            Transaction.objects.create(
                user=request.user, amount=amount, category=categoria_obj,
                is_expense=categoria_obj.is_expense, date=date, note=note
            )
            return redirect('inicio')

        # 2. ABONAR A LA BÓVEDA DE AHORRO
        savings_amount = request.POST.get('savings_amount')
        if savings_amount:
            meta_obj.saved_amount += Decimal(savings_amount)
            meta_obj.save()
            Transaction.objects.create(
                user=request.user, amount=savings_amount, date=hoy.date(), 
                is_expense=False, is_transfer=True, note="🎯 Abono a Bóveda"
            )
            return redirect('inicio')

        # 3. CONFIGURAR NUEVA META
        set_goal = request.POST.get('set_goal')
        if set_goal:
            meta_obj.name = request.POST.get('goal_name')
            meta_obj.target_amount = request.POST.get('target_amount')
            meta_obj.save()
            return redirect('inicio')

        # 🔥 4. PAGAR SUSCRIPCIÓN RÁPIDO (NUEVO) 🔥
        pay_sub_id = request.POST.get('pay_subscription')
        if pay_sub_id:
            sub = Subscription.objects.get(id=pay_sub_id, user=request.user)
            Transaction.objects.create(
                user=request.user, 
                amount=sub.amount, 
                category=sub.category,
                is_expense=True, 
                date=hoy.date(), 
                note=f"🔁 Pago de {sub.name}"
            )
            return redirect('inicio')

    # FILTROS DE MES Y AÑO
    mes_actual = int(request.GET.get('mes', hoy.month))
    anio_actual = int(request.GET.get('anio', hoy.year))

    # CÁLCULOS GLOBALES PARA EL SALDO
    transacciones_totales = Transaction.objects.filter(user=request.user)
    transacciones_reales = transacciones_totales.filter(is_transfer=False)
    ingresos_totales = transacciones_reales.filter(is_expense=False).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    gastos_totales = transacciones_reales.filter(is_expense=True).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    saldo_neto = ingresos_totales - gastos_totales - meta_obj.saved_amount

    # CÁLCULOS DEL MES SELECCIONADO
    transacciones_mes = transacciones_totales.filter(date__month=mes_actual, date__year=anio_actual).order_by('-date')
    trans_mes_reales = transacciones_mes.filter(is_transfer=False)
    ingresos_mes = trans_mes_reales.filter(is_expense=False).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    gastos_mes = trans_mes_reales.filter(is_expense=True).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)

    # GRÁFICA VISUAL (Distribución de gastos)
    gastos_por_cat = {}
    for g in trans_mes_reales.filter(is_expense=True):
        nombre_cat = g.category.name if g.category else "Otros"
        gastos_por_cat[nombre_cat] = gastos_por_cat.get(nombre_cat, 0) + float(g.amount)

    # PORCENTAJE DE AHORRO
    porcentaje = 0
    if meta_obj.target_amount > 0:
        porcentaje = min(int((meta_obj.saved_amount / meta_obj.target_amount) * 100), 100)

    # CÁLCULOS DE PRESUPUESTOS Y ALERTAS RF-20
    categorias_con_presupuesto = Category.objects.filter(user=request.user, is_expense=True, budget_limit__gt=0)
    datos_presupuestos = []

    for cat in categorias_con_presupuesto:
        gastado_cat = trans_mes_reales.filter(category=cat, is_expense=True).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        porc_gasto = int((gastado_cat / cat.budget_limit) * 100)
        
        color = "#2ecc71" # Verde normal
        
        # Lógica de notificaciones RF-20
        if porc_gasto >= 100:
            color = "#e74c3c" # Rojo (Te pasaste)
            messages.warning(request, f"⚠️ ¡Atención! Has superado tu límite de presupuesto para {cat.name}.")
        elif porc_gasto >= 80:
            color = "#e67e22" # Naranja (Peligro)
            messages.warning(request, f"⚠️ Cuidado, estás al {porc_gasto}% de tu presupuesto en {cat.name}.")

        datos_presupuestos.append({
            'nombre': cat.name,
            'limite': cat.budget_limit,
            'gastado': gastado_cat,
            'porcentaje': min(porc_gasto, 100), 
            'porcentaje_real': porc_gasto, 
            'color': color
        })
        
    # SUSCRIPCIONES
    suscripciones = Subscription.objects.filter(user=request.user, is_active=True)
    total_suscripciones = sum(sub.amount for sub in suscripciones)

    # Solo enviamos variables al context al final
    context = {
        'categorias': categorias,
        'transacciones': transacciones_mes,
        'saldo': saldo_neto,           
        'ingresos': ingresos_mes,
        'gastos': gastos_mes,
        'labels_categorias': list(gastos_por_cat.keys()),   
        'datos_categorias': list(gastos_por_cat.values()),  
        'porcentaje_ahorro': porcentaje,
        'meta_nombre': meta_obj.name,
        'meta_valor': meta_obj.target_amount,
        'saldo_restante': meta_obj.target_amount - meta_obj.saved_amount,
        'mes_actual': mes_actual,
        'anio_actual': anio_actual,
        'datos_presupuestos': datos_presupuestos,
        'suscripciones': suscripciones,
        'total_suscripciones': total_suscripciones,
    }
    
    return render(request, 'inicio.html', context)


@login_required
def eliminar_transaccion(request, id):
    transaccion = get_object_or_404(Transaction, id=id, user=request.user)
    transaccion.delete()
    return redirect('inicio')

def registro(request):
    if request.method == 'POST':
        # 1. Capturamos los datos del post
        data = request.POST.copy()
        u = data.get('username')
        e = data.get('email')
        p = data.get('password') # El que viene del HTML

        # 2. Forzamos los nombres que Django quiere para el RegistroForm
        data['password1'] = p
        data['password2'] = p

        form = RegistroForm(data)

        # 3. Validaciones manuales rápidas antes de procesar el form
        if User.objects.filter(username=u).exists():
            messages.error(request, "Ese nombre de usuario ya está en uso.")
            return render(request, 'registro.html', {'form': form})
        
        if User.objects.filter(email=e).exists():
            messages.error(request, "Ese correo ya tiene una cuenta activa.")
            return render(request, 'registro.html', {'form': form})

        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.email = e # Aseguramos que el email se guarde
            usuario.save()
            
            login(request, usuario)
            messages.success(request, "¡Billetera creada! Bienvenido a Fintax.")
            return redirect('inicio')
        else:
            # Si el form falla (ej: contraseña muy corta), sacamos los errores
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
    else:
        form = RegistroForm()
        
    return render(request, 'registro.html', {'form': form})

@login_required
def gestionar_categorias(request):
    if request.method == 'POST':
        nombre = request.POST.get('name')
        es_gasto = request.POST.get('is_expense') == 'on' 
        limite = request.POST.get('budget_limit') or 0
        
        if nombre:
            Category.objects.create(
                user=request.user, 
                name=nombre, 
                is_expense=es_gasto,
                budget_limit=limite
            )
        return redirect('categorias') 
        
    categorias = Category.objects.filter(user=request.user)
    return render(request, 'categorias.html', {'categorias': categorias})


@login_required
def eliminar_categoria(request, id):
    categoria = get_object_or_404(Category, id=id, user=request.user)
    categoria.delete()
    return redirect('categorias')


@login_required
def editar_transaccion(request, id):
    transaccion = get_object_or_404(Transaction, id=id, user=request.user)
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        category_id = request.POST.get('category')
        date = request.POST.get('date')
        note = request.POST.get('note')

        if amount and category_id and date:
            categoria_obj = get_object_or_404(Category, id=category_id, user=request.user)
            
            transaccion.amount = amount
            transaccion.category = categoria_obj
            transaccion.is_expense = categoria_obj.is_expense
            transaccion.date = date
            transaccion.note = note
            transaccion.save() 
            
            return redirect('inicio')
            
    categorias = Category.objects.filter(user=request.user)
    return render(request, 'editar.html', {
        't': transaccion,
        'categorias': categorias
    })


@login_required
def exportar_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="mis_movimientos.csv"'
    response.write(b'\xef\xbb\xbf')

    writer = csv.writer(response)
    writer.writerow(['Fecha', 'Tipo', 'Categoría', 'Monto', 'Nota'])

    transacciones = Transaction.objects.filter(user=request.user).order_by('-date')

    for t in transacciones:
        if t.is_transfer:
            tipo = "Abono a Bóveda"
            categoria = "Bóveda"
        else:
            tipo = "Gasto" if t.is_expense else "Ingreso"
            categoria = t.category.name if t.category else "N/A"
            
        writer.writerow([t.date, tipo, categoria, t.amount, t.note])

    return response


@login_required
def exportar_pdf(request):
    transacciones = Transaction.objects.filter(user=request.user).order_by('-date')
    
    template_path = 'reporte_pdf.html'
    context = {'transacciones': transacciones}
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="mis_movimientos.pdf"'
    
    template = get_template(template_path)
    html = template.render(context)
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Hubo un error al crear el PDF')
        
    return response


# ==========================================
# VISTAS DE SUSCRIPCIONES
# ==========================================

@login_required
def gestionar_suscripciones(request):
    if request.method == 'POST':
        nombre = request.POST.get('name')
        monto = request.POST.get('amount')
        fecha_cobro = request.POST.get('billing_day')
        category_id = request.POST.get('category')
        
        if nombre and monto and fecha_cobro and category_id:
            categoria_obj = get_object_or_404(Category, id=category_id, user=request.user)
            Subscription.objects.create(
                user=request.user,
                name=nombre,
                amount=monto,
                billing_day=fecha_cobro,  # 🔥 ¡AQUÍ ESTÁ LA MAGIA CORREGIDA! 🔥
                category=categoria_obj
            )
        return redirect('suscripciones')

    suscripciones = Subscription.objects.filter(user=request.user)
    categorias = Category.objects.filter(user=request.user, is_expense=True)
    return render(request, 'suscripciones.html', {
        'suscripciones': suscripciones,
        'categorias': categorias
    })

@login_required
def eliminar_suscripcion(request, id):
    sub = get_object_or_404(Subscription, id=id, user=request.user)
    sub.delete()
    return redirect('suscripciones')

@login_required
def educacion(request):
    api_key = "c0150a73398a45a3b1c248906dc722a6" 
    
    # 🔥 EL CAMBIO ESTÁ AQUÍ: Buscamos "finanzas" en todo el mundo hispano
  # 🔥 Afinando la puntería: Solo temas 100% financieros
    url = f"https://newsapi.org/v2/everything?q=\"finanzas personales\"+OR+inversiones+OR+\"bolsa de valores\"+OR+criptomonedas&language=es&sortBy=publishedAt&apiKey={api_key}"
    
    cabeceras = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    api_news = []
    try:
        response = requests.get(url, headers=cabeceras, timeout=7)
        
        if response.status_code == 200:
            datos = response.json()
            todas_las_noticias = datos.get('articles', [])
            
            # Esto imprimirá en tu consola negra cuántas encontró
            print(f"✅ Noticias totales recibidas de la API: {len(todas_las_noticias)}")
            
            # Filtramos las que tienen foto
            noticias_con_foto = [n for n in todas_las_noticias if n.get('urlToImage')]
            api_news = noticias_con_foto[:15] 
        else:
            print(f"🔥 ERROR API DETECTADO: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"🔥 Error de conexión: {e}")

    if not api_news:
        api_news = [
            {'title': 'Respaldo 1', 'urlToImage': 'https://via.placeholder.com/400x200/2c3e50/ffffff?text=Finanzas', 'url': '#'},
            {'title': 'Respaldo 2', 'urlToImage': 'https://via.placeholder.com/400x200/2c3e50/ffffff?text=Noticias', 'url': '#'}
        ]

    mis_noticias = CustomNews.objects.all().order_by('-created_at')
    
    return render(request, 'educacion.html', {
        'custom_news': mis_noticias,
        'api_news': api_news
    })