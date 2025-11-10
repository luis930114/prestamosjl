"""
Vistas del sistema de pagos
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.utils import timezone
from django.http import HttpResponse
from datetime import timedelta, datetime
from decimal import Decimal

from .models import Pago, PlanPago
from loans.models import Prestamo
from loans.forms import PagoRapidoForm

# Para generar PDFs
"""from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from io import BytesIO"""


@login_required
def pago_lista(request):
    """Lista de pagos con filtros"""
    
    pagos = Pago.objects.select_related(
        'prestamo', 'prestamo__cliente', 'created_by'
    ).filter(anulado=False).order_by('-fecha_pago', '-created_at')
    
    # Filtros
    search = request.GET.get('search', '')
    if search:
        pagos = pagos.filter(
            Q(recibo_numero__icontains=search) |
            Q(prestamo__codigo__icontains=search) |
            Q(prestamo__cliente__nombre__icontains=search) |
            Q(prestamo__cliente__apellido__icontains=search)
        )
    
    metodo = request.GET.get('metodo', '')
    if metodo:
        pagos = pagos.filter(metodo_pago=metodo)
    
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    
    if fecha_desde:
        pagos = pagos.filter(fecha_pago__gte=fecha_desde)
    if fecha_hasta:
        pagos = pagos.filter(fecha_pago__lte=fecha_hasta)
    
    # Totales
    totales = pagos.aggregate(
        total_recaudado=Sum('valor_total'),
        total_intereses=Sum('valor_interes'),
        total_capital=Sum('valor_capital')
    )
    
    context = {
        'pagos': pagos[:50],  # Limitar a 50 para performance
        'search': search,
        'metodo': metodo,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'totales': totales,
        'metodos_pago': Pago.METODO_PAGO_CHOICES,
    }
    
    return render(request, 'payments/pago_lista.html', context)


@login_required
def pago_detalle(request, pk):
    """Detalle de un pago"""
    
    pago = get_object_or_404(
        Pago.objects.select_related('prestamo', 'prestamo__cliente', 'created_by'),
        pk=pk
    )
    
    context = {'pago': pago}
    return render(request, 'payments/pago_detalle.html', context)


@login_required
def pago_crear(request):
    """Crear nuevo pago (vista completa)"""
    
    if request.method == 'POST':
        form = PagoRapidoForm(request.POST, request.FILES)
        if form.is_valid():
            pago = form.save(commit=False)
            pago.created_by = request.user
            pago.save()
            
            messages.success(
                request, 
                f'Pago {pago.recibo_numero} registrado exitosamente'
            )
            return redirect('payments:pago_detalle', pk=pago.pk)
    else:
        # Pre-llenar fecha actual
        form = PagoRapidoForm(initial={'fecha_pago': timezone.now().date()})
    
    context = {
        'form': form,
        'titulo': 'Registrar Pago'
    }
    return render(request, 'payments/pago_form.html', context)


@login_required
def pago_rapido(request):
    """Interfaz de pago rápido optimizada"""
    
    if request.method == 'POST':
        prestamo_id = request.POST.get('prestamo_id')
        valor_total = request.POST.get('valor_total')
        metodo_pago = request.POST.get('metodo_pago', 'EFECTIVO')
        
        if not prestamo_id or not valor_total:
            messages.error(request, 'Debe seleccionar un préstamo y un valor')
            return redirect('payments:pago_rapido')
        
        try:
            prestamo = Prestamo.objects.get(id=prestamo_id)
            valor_total = Decimal(valor_total)
            
            # Calcular automáticamente interés y capital
            interes_mensual = prestamo.interes_mensual
            valor_interes = min(interes_mensual, valor_total)
            valor_capital = valor_total - valor_interes
            
            # Validar que no exceda el saldo
            if valor_capital > prestamo.saldo_actual:
                messages.error(
                    request,
                    f'El pago de capital (${valor_capital:,.0f}) excede el saldo (${prestamo.saldo_actual:,.0f})'
                )
                return redirect('payments:pago_rapido')
            
            # Crear pago
            pago = Pago.objects.create(
                prestamo=prestamo,
                valor_total=valor_total,
                valor_interes=valor_interes,
                valor_capital=valor_capital,
                metodo_pago=metodo_pago,
                fecha_pago=timezone.now().date(),
                created_by=request.user
            )
            
            messages.success(
                request,
                f'✅ Pago registrado: {pago.recibo_numero} - ${valor_total:,.0f}'
            )
            
            # Redirigir al recibo
            #return redirect('payments:pago_recibo_pdf', pk=pago.pk)
            
        except Prestamo.DoesNotExist:
            messages.error(request, 'Préstamo no encontrado')
        except ValueError:
            messages.error(request, 'Valor inválido')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
        
        return redirect('payments:pago_rapido')
    
    # GET - Mostrar formulario
    prestamos_activos = Prestamo.objects.filter(
        estado__in=['ACTIVO', 'VENCIDO', 'MORA']
    ).select_related('cliente').order_by('-fecha_prestamo')[:20]
    
    # Pagos del día
    pagos_hoy = Pago.objects.filter(
        fecha_pago=timezone.now().date(),
        anulado=False
    ).select_related('prestamo', 'prestamo__cliente').order_by('-created_at')[:10]
    
    # Total recaudado hoy
    total_hoy = pagos_hoy.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    
    context = {
        'prestamos_activos': prestamos_activos,
        'pagos_hoy': pagos_hoy,
        'total_hoy': total_hoy,
        'metodos_pago': Pago.METODO_PAGO_CHOICES,
    }
    
    return render(request, 'payments/pago_rapido.html', context)


@login_required
def pago_anular(request, pk):
    """Anular un pago"""
    
    pago = get_object_or_404(Pago, pk=pk)
    
    if pago.anulado:
        messages.warning(request, 'Este pago ya está anulado')
        return redirect('payments:pago_detalle', pk=pago.pk)
    
    if request.method == 'POST':
        motivo = request.POST.get('motivo', '')
        
        if not motivo:
            messages.error(request, 'Debe proporcionar un motivo de anulación')
            return redirect('payments:pago_anular', pk=pk)
        
        # Anular el pago
        pago.anular(motivo, request.user)
        
        messages.success(
            request,
            f'Pago {pago.recibo_numero} anulado exitosamente'
        )
        return redirect('payments:pago_detalle', pk=pago.pk)
    
    context = {'pago': pago}
    return render(request, 'payments/pago_anular.html', context)


'''@login_required
def pago_recibo_pdf(request, pk):
    """Generar recibo de pago en PDF"""
    
    pago = get_object_or_404(
        Pago.objects.select_related('prestamo', 'prestamo__cliente', 'prestamo__prestamista'),
        pk=pk
    )
    
    # Crear PDF en memoria
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Configuración
    p.setTitle(f"Recibo {pago.recibo_numero}")
    
    # Encabezado
    p.setFont("Helvetica-Bold", 20)
    p.drawString(1*inch, height - 1*inch, "RECIBO DE PAGO")
    
    # Línea decorativa
    p.setStrokeColor(colors.HexColor('#0d6efd'))
    p.setLineWidth(3)
    p.line(1*inch, height - 1.2*inch, width - 1*inch, height - 1.2*inch)
    
    # Información del recibo
    y = height - 1.6*inch
    p.setFont("Helvetica-Bold", 12)
    p.drawString(1*inch, y, f"Recibo No: {pago.recibo_numero}")
    
    p.setFont("Helvetica", 10)
    y -= 0.25*inch
    p.drawString(1*inch, y, f"Fecha de Pago: {pago.fecha_pago.strftime('%d/%m/%Y')}")
    y -= 0.2*inch
    p.drawString(1*inch, y, f"Método de Pago: {pago.get_metodo_pago_display()}")
    
    if pago.anulado:
        p.setFillColor(colors.red)
        p.setFont("Helvetica-Bold", 16)
        p.drawString(width - 3*inch, height - 1*inch, "*** ANULADO ***")
        p.setFillColor(colors.black)
    
    # Información del préstamo
    y -= 0.5*inch
    p.setFont("Helvetica-Bold", 14)
    p.drawString(1*inch, y, "INFORMACIÓN DEL PRÉSTAMO")
    
    p.setFont("Helvetica", 10)
    y -= 0.3*inch
    p.drawString(1*inch, y, f"Préstamo: {pago.prestamo.codigo}")
    y -= 0.2*inch
    p.drawString(1*inch, y, f"Cliente: {pago.prestamo.cliente.nombre_completo}")
    y -= 0.2*inch
    p.drawString(1*inch, y, f"Cédula: {pago.prestamo.cliente.cedula}")
    y -= 0.2*inch
    p.drawString(1*inch, y, f"Teléfono: {pago.prestamo.cliente.celular}")
    
    # Detalles del pago
    y -= 0.5*inch
    p.setFont("Helvetica-Bold", 14)
    p.drawString(1*inch, y, "DETALLES DEL PAGO")
    
    # Tabla con detalles
    y -= 0.3*inch
    data = [
        ['Concepto', 'Valor'],
        ['Pago a Interés', f'${pago.valor_interes:,.2f}'],
        ['Pago a Capital', f'${pago.valor_capital:,.2f}'],
        ['', ''],
        ['TOTAL PAGADO', f'${pago.valor_total:,.2f}'],
    ]
    
    tabla = Table(data, colWidths=[3*inch, 2*inch])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9ecef')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#198754')),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
    ]))
    
    tabla.wrapOn(p, width, height)
    tabla.drawOn(p, 1*inch, y - 2*inch)
    
    # Saldo restante
    y -= 2.5*inch
    p.setFont("Helvetica-Bold", 12)
    p.setFillColor(colors.HexColor('#0d6efd'))
    p.drawString(1*inch, y, f"Saldo Restante del Préstamo: ${pago.prestamo.saldo_actual:,.2f}")
    p.setFillColor(colors.black)
    
    # Observaciones
    if pago.observaciones:
        y -= 0.4*inch
        p.setFont("Helvetica", 9)
        p.drawString(1*inch, y, f"Observaciones: {pago.observaciones[:100]}")
    
    # Pie de página
    p.setFont("Helvetica", 8)
    p.setFillColor(colors.grey)
    y = 1.2*inch
    p.drawString(1*inch, y, f"Prestamista: {pago.prestamo.prestamista.nombre_completo}")
    y -= 0.15*inch
    p.drawString(1*inch, y, f"Generado: {timezone.now().strftime('%d/%m/%Y %H:%M')}")
    y -= 0.15*inch
    p.drawString(1*inch, y, f"Usuario: {pago.created_by.username if pago.created_by else 'Sistema'}")
    
    # Línea final
    p.setStrokeColor(colors.grey)
    p.setLineWidth(1)
    p.line(1*inch, 0.9*inch, width - 1*inch, 0.9*inch)
    
    p.setFont("Helvetica-Oblique", 8)
    p.drawCentredString(width/2, 0.7*inch, "Sistema de Préstamos JL - www.prestamosjl.com")
    
    # Finalizar PDF
    p.showPage()
    p.save()
    
    # Marcar como impreso
    pago.recibo_impreso = True
    pago.save()
    
    # Retornar PDF
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="recibo_{pago.recibo_numero}.pdf"'
    
    return response
'''

@login_required
def reporte_diario(request):
    """Reporte de pagos del día"""
    
    # Fecha seleccionada o hoy
    fecha_str = request.GET.get('fecha', timezone.now().date().isoformat())
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except:
        fecha = timezone.now().date()
    
    # Pagos del día
    pagos = Pago.objects.filter(
        fecha_pago=fecha,
        anulado=False
    ).select_related('prestamo', 'prestamo__cliente').order_by('created_at')
    
    # Resumen
    resumen = {
        'fecha': fecha,
        'total_pagos': pagos.count(),
        'total_recaudado': pagos.aggregate(Sum('valor_total'))['valor_total__sum'] or 0,
        'total_intereses': pagos.aggregate(Sum('valor_interes'))['valor_interes__sum'] or 0,
        'total_capital': pagos.aggregate(Sum('valor_capital'))['valor_capital__sum'] or 0,
        'por_metodo': {}
    }
    
    # Agrupar por método de pago
    for metodo, nombre in Pago.METODO_PAGO_CHOICES:
        pagos_metodo = pagos.filter(metodo_pago=metodo)
        if pagos_metodo.exists():
            resumen['por_metodo'][nombre] = {
                'cantidad': pagos_metodo.count(),
                'monto': pagos_metodo.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
            }
    
    context = {
        'fecha': fecha,
        'pagos': pagos,
        'resumen': resumen,
    }
    
    return render(request, 'payments/reporte_diario.html', context)


@login_required
def estadisticas_pagos(request):
    """Estadísticas generales de pagos"""
    
    # Rango de fechas
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    
    pagos = Pago.objects.filter(anulado=False)
    
    if fecha_desde:
        pagos = pagos.filter(fecha_pago__gte=fecha_desde)
    if fecha_hasta:
        pagos = pagos.filter(fecha_pago__lte=fecha_hasta)
    
    # Estadísticas
    stats = {
        'total_pagos': pagos.count(),
        'total_recaudado': pagos.aggregate(Sum('valor_total'))['valor_total__sum'] or 0,
        'total_intereses': pagos.aggregate(Sum('valor_interes'))['valor_interes__sum'] or 0,
        'total_capital': pagos.aggregate(Sum('valor_capital'))['valor_capital__sum'] or 0,
        'pagos_hoy': pagos.filter(fecha_pago=timezone.now().date()).count(),
        'recaudado_hoy': pagos.filter(
            fecha_pago=timezone.now().date()
        ).aggregate(Sum('valor_total'))['valor_total__sum'] or 0,
    }
    
    # Últimos 7 días
    ultimos_7_dias = []
    for i in range(6, -1, -1):
        dia = timezone.now().date() - timedelta(days=i)
        pagos_dia = pagos.filter(fecha_pago=dia)
        ultimos_7_dias.append({
            'fecha': dia,
            'cantidad': pagos_dia.count(),
            'monto': pagos_dia.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
        })
    
    context = {
        'stats': stats,
        'ultimos_7_dias': ultimos_7_dias,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    }
    
    return render(request, 'payments/estadisticas.html', context)


# ========== AJAX / API Helpers ==========

@login_required
def obtener_info_prestamo(request, prestamo_id):
    """Endpoint AJAX para obtener info de un préstamo"""
    from django.http import JsonResponse
    
    try:
        prestamo = Prestamo.objects.get(id=prestamo_id)
        data = {
            'codigo': prestamo.codigo,
            'cliente': prestamo.cliente.nombre_completo,
            'saldo_actual': float(prestamo.saldo_actual),
            'interes_mensual': float(prestamo.interes_mensual),
            'porcentaje_interes': float(prestamo.porcentaje_interes),
            'dias_mora': prestamo.dias_mora,
            'estado': prestamo.estado,
        }
        return JsonResponse(data)
    except Prestamo.DoesNotExist:
        return JsonResponse({'error': 'Préstamo no encontrado'}, status=404)