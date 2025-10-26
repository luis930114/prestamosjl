from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from datetime import timedelta, datetime
from decimal import Decimal

from .models import Cliente, Prestamo, CoDeudor
from .forms import ClienteForm, PrestamoForm, CoDeudorForm, PagoRapidoForm
from users.models import Prestamista
from payments.models import Pago


@login_required
def dashboard(request):
    """Dashboard principal con estadísticas"""
    
    # Obtener prestamista del usuario logueado
    try:
        prestamista = request.user.profile.prestamista
    except ValueError:
        prestamista = Prestamista.objects.first()
    
    # Estadísticas generales
    prestamos = Prestamo.objects.filter(prestamista=prestamista)
    from django.db.models import Sum
    stats = {
        'total_prestamos': prestamos.count(),
        'prestamos_activos': prestamos.filter(estado='ACTIVO').count(),
        'prestamos_mora': prestamos.filter(estado='MORA').count(),
        'prestamos_vencidos': prestamos.filter(estado='VENCIDO').count(),
        'prestamos_pagados': prestamos.filter(estado='PAGADO').count(),

        'total_prestado': prestamos.aggregate(Sum('saldo_actual'))['saldo_actual__sum'] or 0,
        'saldo_pendiente': prestamos.filter(
            estado__in=['ACTIVO', 'VENCIDO', 'MORA']
        ).aggregate(Sum('saldo_actual'))['saldo_actual__sum'] or 0,
        'total_clientes': Cliente.objects.filter(activo=True).count(),
    }
    
    # Préstamos recientes
    prestamos_recientes = prestamos.order_by('-created_at')[:5]
    
    # Préstamos por vencer (próximos 7 días)
    fecha_limite = timezone.now().date() + timedelta(days=7)
    prestamos_vencer = prestamos.filter(
        fecha_vencimiento__lte=fecha_limite,
        fecha_vencimiento__gte=timezone.now().date(),
        estado='ACTIVO'
    ).order_by('fecha_vencimiento')[:5]
    
    # Préstamos en mora
    prestamos_mora = prestamos.filter(estado='MORA').order_by('-fecha_prestamo')[:5]
    
    # Clientes con más deuda
    from django.db.models import Sum
    clientes_deuda = Cliente.objects.annotate(
        deuda=Sum('prestamos__saldo_actual',
                 filter=Q(prestamos__estado__in=['ACTIVO', 'VENCIDO', 'MORA']))
    ).filter(deuda__gt=0).order_by('-deuda')[:5]
    
    # Pagos recientes (hoy)
    pagos_hoy = Pago.objects.filter(
        fecha_pago=timezone.now().date(),
        anulado=False
    ).order_by('-created_at')[:5]
    
    context = {
        'stats': stats,
        'prestamos_recientes': prestamos_recientes,
        'prestamos_vencer': prestamos_vencer,
        'prestamos_mora': prestamos_mora,
        'clientes_deuda': clientes_deuda,
        'pagos_hoy': pagos_hoy,
        'prestamista': prestamista,
    }
    
    return render(request, 'loans/dashboard.html', context)


# ============= CLIENTES =============

@login_required
def cliente_lista(request):
    """Lista de clientes con búsqueda y filtros"""
    
    clientes = Cliente.objects.all().order_by('apellido', 'nombre')
    
    # Búsqueda
    search = request.GET.get('search', '')
    if search:
        clientes = clientes.filter(
            Q(nombre__icontains=search) |
            Q(apellido__icontains=search) |
            Q(cedula__icontains=search) |
            Q(celular__icontains=search)
        )
    
    # Filtro de estado
    estado = request.GET.get('estado', '')
    if estado == 'activos':
        clientes = clientes.filter(activo=True)
    elif estado == 'inactivos':
        clientes = clientes.filter(activo=False)
    
    context = {
        'clientes': clientes,
        'search': search,
        'estado': estado,
    }
    
    return render(request, 'loans/cliente_lista.html', context)


@login_required
def cliente_detalle(request, pk):
    """Detalle de un cliente con sus préstamos"""
    
    cliente = get_object_or_404(Cliente, pk=pk)
    prestamos = cliente.prestamos.all().order_by('-fecha_prestamo')
    codeudores = cliente.codeudores.all()
    
    # Estadísticas del cliente
    stats = {
        'total_prestamos': prestamos.count(),
        'prestamos_activos': prestamos.filter(estado='ACTIVO').count(),
        'prestamos_pagados': prestamos.filter(estado='PAGADO').count(),
        'deuda_total': prestamos.filter(
            estado__in=['ACTIVO', 'VENCIDO', 'MORA']
        ).aggregate(Sum('saldo_actual'))['saldo_actual__sum'] or 0,
    }
    
    context = {
        'cliente': cliente,
        'prestamos': prestamos,
        'codeudores': codeudores,
        'stats': stats,
    }
    
    return render(request, 'loans/cliente_detalle.html', context)


@login_required
def cliente_crear(request):
    """Crear nuevo cliente"""
    
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save()
            messages.success(request, f'Cliente {cliente.nombre_completo} creado exitosamente')
            return redirect('loans:cliente_detalle', pk=cliente.pk)
    else:
        form = ClienteForm()
    
    context = {'form': form, 'titulo': 'Crear Cliente'}
    return render(request, 'loans/cliente_form.html', context)


@login_required
def cliente_editar(request, pk):
    """Editar cliente existente"""
    
    cliente = get_object_or_404(Cliente, pk=pk)
    
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            cliente = form.save()
            messages.success(request, f'Cliente {cliente.nombre_completo} actualizado exitosamente')
            return redirect('loans:cliente_detalle', pk=cliente.pk)
    else:
        form = ClienteForm(instance=cliente)
    
    context = {'form': form, 'titulo': 'Editar Cliente', 'cliente': cliente}
    return render(request, 'loans/cliente_form.html', context)


@login_required
def cliente_eliminar(request, pk):
    """Eliminar/Desactivar cliente"""
    
    cliente = get_object_or_404(Cliente, pk=pk)
    
    if request.method == 'POST':
        # No eliminar, solo desactivar
        cliente.activo = False
        cliente.save()
        messages.warning(request, f'Cliente {cliente.nombre_completo} desactivado')
        return redirect('loans:cliente_lista')
    
    context = {'cliente': cliente}
    return render(request, 'loans/cliente_eliminar.html', context)


@login_required
def codeudor_crear(request, cliente_pk):
    """Agregar co-deudor a un cliente"""
    
    cliente = get_object_or_404(Cliente, pk=cliente_pk)
    
    if request.method == 'POST':
        form = CoDeudorForm(request.POST)
        if form.is_valid():
            codeudor = form.save(commit=False)
            codeudor.cliente = cliente
            codeudor.save()
            messages.success(request, f'Co-deudor {codeudor.nombre_completo} agregado')
            return redirect('loans:cliente_detalle', pk=cliente.pk)
    else:
        form = CoDeudorForm()
    
    context = {'form': form, 'cliente': cliente}
    return render(request, 'loans/codeudor_form.html', context)


# ============= PRÉSTAMOS =============

@login_required
def prestamo_lista(request):
    """Lista de préstamos con filtros"""
    
    """try:
        prestamista = request.user.profile.prestamista
    except:
        prestamista = Prestamista.objects.first()"""
    
    #prestamos = Prestamo.objects.filter(prestamista=prestamista).select_related('cliente')
    prestamos = Prestamo.objects.all()
    
    # Filtros
    estado = request.GET.get('estado', '')
    if estado:
        prestamos = prestamos.filter(estado=estado)
    
    search = request.GET.get('search', '')
    if search:
        prestamos = prestamos.filter(
            Q(codigo__icontains=search) |
            Q(cliente__nombre__icontains=search) |
            Q(cliente__apellido__icontains=search) |
            Q(cliente__cedula__icontains=search)
        )
    
    # Ordenar
    orden = request.GET.get('orden', '-fecha_prestamo')
    prestamos = prestamos.order_by(orden)
    print(f"prestamos: {prestamos}")
    context = {
        'prestamos': prestamos,
        'estado': estado,
        'search': search,
        'orden': orden,
    }
    
    return render(request, 'loans/prestamo_lista.html', context)


@login_required
def prestamo_detalle(request, pk):
    """Detalle de un préstamo"""
    
    prestamo = get_object_or_404(
        Prestamo.objects.select_related('cliente', 'prestamista', 'codeudor'),
        pk=pk
    )
    
    # Pagos del préstamo
    pagos = prestamo.pagos.filter(anulado=False).order_by('-fecha_pago')
    
    # Calcular totales
    totales = {
        'total_pagado': pagos.aggregate(Sum('valor_total'))['valor_total__sum'] or 0,
        'total_intereses': pagos.aggregate(Sum('valor_interes'))['valor_interes__sum'] or 0,
        'total_capital': pagos.aggregate(Sum('valor_capital'))['valor_capital__sum'] or 0,
    }
    
    context = {
        'prestamo': prestamo,
        'pagos': pagos,
        'totales': totales,
    }
    
    return render(request, 'loans/prestamo_detalle.html', context)


@login_required
def prestamo_crear(request):
    """Crear nuevo préstamo"""
    
    if request.method == 'POST':
        form = PrestamoForm(request.POST, request.FILES)
        if form.is_valid():
            prestamo = form.save(commit=False)
            
            # Asignar prestamista del usuario logueado
            #try:
            #    prestamo.prestamista = request.user.profile.prestamista
            #except:
            #    prestamo.prestamista = Prestamista.objects.first()
            
            prestamo.save()
            messages.success(request, f'Préstamo {prestamo.codigo} creado exitosamente')
            return redirect('loans:prestamo_detalle', pk=prestamo.pk)
    else:
        # Pre-llenar prestamista
        try:
            prestamista = request.user.profile.prestamista
            form = PrestamoForm(initial={'prestamista': prestamista})
        except:
            form = PrestamoForm()
    
    context = {'form': form, 'titulo': 'Crear Préstamo'}
    return render(request, 'loans/prestamo_form.html', context)


@login_required
def prestamo_editar(request, pk):
    """Editar préstamo existente"""
    
    prestamo = get_object_or_404(Prestamo, pk=pk)
    
    if request.method == 'POST':
        form = PrestamoForm(request.POST, request.FILES, instance=prestamo)
        if form.is_valid():
            prestamo = form.save()
            messages.success(request, f'Préstamo {prestamo.codigo} actualizado')
            return redirect('loans:prestamo_detalle', pk=prestamo.pk)
    else:
        form = PrestamoForm(instance=prestamo)
    
    context = {'form': form, 'titulo': 'Editar Préstamo', 'prestamo': prestamo}
    return render(request, 'loans/prestamo_form.html', context)


@login_required
def prestamo_simular(request):
    """Simulador de préstamos"""
    
    resultado = None
    
    if request.method == 'POST':
        valor = Decimal(request.POST.get('valor', 0))
        tasa = Decimal(request.POST.get('tasa', 4))
        plazo = int(request.POST.get('plazo', 12))
        
        # Calcular cuotas
        interes_mensual = valor * tasa / 100
        cuota_capital = valor / plazo
        
        plan = []
        saldo = valor
        
        for mes in range(1, plazo + 1):
            interes = saldo * tasa / 100
            capital = cuota_capital
            cuota_total = interes + capital
            saldo -= capital
            
            plan.append({
                'mes': mes,
                'cuota': round(cuota_total, 2),
                'interes': round(interes, 2),
                'capital': round(capital, 2),
                'saldo': round(max(0, saldo), 2)
            })
        
        total_intereses = sum(p['interes'] for p in plan)
        
        resultado = {
            'valor': valor,
            'tasa': tasa,
            'plazo': plazo,
            'interes_mensual': round(interes_mensual, 2),
            'total_intereses': round(total_intereses, 2),
            'total_pagar': round(valor + total_intereses, 2),
            'plan': plan
        }
    
    context = {'resultado': resultado}
    return render(request, 'loans/prestamo_simular.html', context)


# ============= REPORTES =============

@login_required
def reportes(request):
    """Página de reportes"""
    
    try:
        prestamista = request.user.profile.prestamista
    except:
        prestamista = Prestamista.objects.first()
    
    # Reporte por fechas
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    
    if fecha_desde and fecha_hasta:
        prestamos = Prestamo.objects.filter(
            prestamista=prestamista,
            fecha_prestamo__gte=fecha_desde,
            fecha_prestamo__lte=fecha_hasta
        )
        
        reporte = {
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'total_prestamos': prestamos.count(),
            'monto_total': prestamos.aggregate(Sum('valor_inicial'))['valor_inicial__sum'] or 0,
            'por_estado': {}
        }
        
        for estado, _ in Prestamo.ESTADO_CHOICES:
            count = prestamos.filter(estado=estado).count()
            monto = prestamos.filter(estado=estado).aggregate(Sum('valor_inicial'))['valor_inicial__sum'] or 0
            reporte['por_estado'][estado] = {'cantidad': count, 'monto': monto}
    else:
        reporte = None
        prestamos = []
    
    context = {
        'reporte': reporte,
        'prestamos': prestamos,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    }
    
    return render(request, 'loans/reportes.html', context)


@login_required
def prestamos_mora(request):
    """Lista de préstamos en mora"""
    
    try:
        prestamista = request.user.profile.prestamista
    except:
        prestamista = Prestamista.objects.first()
    
    prestamos = Prestamo.objects.filter(
        prestamista=prestamista,
        estado='MORA'
    ).select_related('cliente').order_by('-fecha_vencimiento')
    
    context = {'prestamos': prestamos}
    return render(request, 'loans/prestamos_mora.html', context)


@login_required
def prestamos_vencer(request):
    """Préstamos próximos a vencer"""
    
    try:
        prestamista = request.user.profile.prestamista
    except:
        prestamista = Prestamista.objects.first()
    
    dias = int(request.GET.get('dias', 7))
    fecha_limite = timezone.now().date() + timedelta(days=dias)
    
    prestamos = Prestamo.objects.filter(
        prestamista=prestamista,
        fecha_vencimiento__lte=fecha_limite,
        fecha_vencimiento__gte=timezone.now().date(),
        estado='ACTIVO'
    ).select_related('cliente').order_by('fecha_vencimiento')
    
    context = {'prestamos': prestamos, 'dias': dias}
    return render(request, 'loans/prestamos_vencer.html', context)

# Create your views here.
