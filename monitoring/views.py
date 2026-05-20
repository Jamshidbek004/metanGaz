import math
import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.utils import timezone
from .models import MethaneStation, StationWorkerProfile, StationSubmission

# --- GEOFENCING VA MASOFA HISOBLAGICH (HAVERSINE) ---
def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Ikki GPS nuqta orasidagi masofani kilometrda hisoblaydi.
    """
    R = 6371.0  # Erning o'rtacha radiusi (km)
    
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    
    a = math.sin(d_lat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


# --- SAHIFALAR KO'RINISHI (HTML RENDERING) ---

def driver_page(request):
    """
    Haydovchilar bosh sahifasi (PWA).
    """
    # Viloyatlar ro'yxatini olish (filtrlash uchun)
    regions = MethaneStation.objects.filter(is_approved=True).values_list('region', flat=True).distinct()
    districts = MethaneStation.objects.filter(is_approved=True).values_list('district', flat=True).distinct()
    
    context = {
        'regions': list(regions),
        'districts': list(districts)
    }
    return render(request, 'driver.html', context)


def cashier_page(request):
    """
    Kassirlar boshqaruv sahifasi.
    Agar foydalanuvchi login qilmagan bo'lsa, avtomatik login qismi ham shu yerda ko'rinadi.
    """
    if not request.user.is_authenticated:
        return render(request, 'cashier_login.html')
        
    try:
        profile = request.user.worker_profile
        station = profile.station
    except StationWorkerProfile.DoesNotExist:
        logout(request)
        return render(request, 'cashier_login.html', {'error': 'Sizga hech qanday zapravka biriktirilmagan!'})
        
    context = {
        'station': station,
        'profile': profile
    }
    return render(request, 'cashier.html', context)


@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard_page(request):
    """
    Adminlar uchun visual boshqaruv paneli.
    """
    stations = MethaneStation.objects.all()
    submissions = StationSubmission.objects.filter(is_processed=False)
    
    context = {
        'stations': stations,
        'submissions': submissions
    }
    return render(request, 'admin_dashboard.html', context)


# --- AUTHENTICATION (KASSIR LOGIN / LOGOUT) ---

@csrf_exempt
def cashier_login_api(request):
    """
    Kassirlarni tizimga kiritish API'si.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Faqat POST so\'rovi qabul qilinadi.'}, status=400)
        
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Noto\'g\'ri formatda ma\'lumot yuborildi.'}, status=400)
        
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        # Profil borligini tekshiramiz
        if hasattr(user, 'worker_profile'):
            return JsonResponse({'success': True, 'message': 'Muvaffaqiyatli kirdingiz!'})
        elif user.is_superuser:
            return JsonResponse({'success': True, 'message': 'Admin sifatida kirdingiz!', 'is_admin': True})
        else:
            logout(request)
            return JsonResponse({'success': False, 'error': 'Foydalanuvchiga zapravka biriktirilmagan!'})
    else:
        return JsonResponse({'success': False, 'error': 'Login yoki parol xato!'})


def cashier_logout(request):
    """
    Kassir chiqishi.
    """
    logout(request)
    return redirect('cashier_page')


# --- HAYDOVCHI API ENPOINTLARI ---

def api_stations_list(request):
    """
    Tasdiqlangan barcha zapravkalarni qaytaradi.
    Agar user GPS koordinatalarini yuborsa (lat/lng), masofani hisoblab eng yaqinini tepaga chiqaradi.
    """
    stations = MethaneStation.objects.filter(is_approved=True)
    
    # Filtrlash parametrlari
    search_query = request.GET.get('search', '')
    region_query = request.GET.get('region', '')
    district_query = request.GET.get('district', '')
    
    if search_query:
        stations = stations.filter(name__icontains=search_query) | stations.filter(address__icontains=search_query)
        
    if region_query:
        stations = stations.filter(region=region_query)
        
    if district_query:
        stations = stations.filter(district=district_query)
        
    # GPS koordinatalar bo'yicha masofa hisoblash
    user_lat = request.GET.get('lat')
    user_lng = request.GET.get('lng')
    
    results = []
    for station in stations:
        dist = None
        if user_lat and user_lng:
            try:
                dist = haversine_distance(
                    float(user_lat), float(user_lng), 
                    station.latitude, station.longitude
                )
            except ValueError:
                pass
                
        results.append({
            'id': station.id,
            'name': station.name,
            'address': station.address,
            'latitude': station.latitude,
            'longitude': station.longitude,
            'status': station.status,
            'status_display': station.get_status_display(),
            'has_power': station.has_power,
            'gas_pressure': station.gas_pressure,
            'gas_pressure_display': station.get_gas_pressure_display(),
            'price': station.price,
            'phone': station.phone or '',
            'region': station.region,
            'district': station.district,
            'estimated_wait': station.estimated_wait_time,
            'distance': round(dist, 2) if dist is not None else None,
            'last_updated': station.last_updated.strftime("%H:%M, %d-%m-%Y")
        })
        
    # Masofaga qarab saralash (agar GPS bo'lsa)
    if user_lat and user_lng:
        results.sort(key=lambda x: x['distance'] if x['distance'] is not None else 999999)
        
    return JsonResponse({'stations': results})


@csrf_exempt
def api_submit_station(request):
    """
    Haydovchi tomonidan yangi zapravka qo'shish arizasi.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Faqat POST so\'rovi qabul qilinadi.'}, status=400)
        
    try:
        data = json.loads(request.body)
        name = data.get('name')
        address = data.get('address')
        lat = float(data.get('latitude'))
        lng = float(data.get('longitude'))
        phone = data.get('phone', '')
        region = data.get('region', 'Toshkent shahri')
        district = data.get('district', '')
        
        if not name or not address or not lat or not lng:
            return JsonResponse({'success': False, 'error': 'Barcha majburiy maydonlarni to\'ldiring.'})
            
        submission = StationSubmission.objects.create(
            name=name,
            address=address,
            latitude=lat,
            longitude=lng,
            phone=phone,
            region=region,
            district=district
        )
        return JsonResponse({'success': True, 'message': 'Ariza muvaffaqiyatli yuborildi. Admin tasdiqlashini kuting!'})
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        return JsonResponse({'success': False, 'error': f"Xatolik: {str(e)}"}, status=400)


# --- KASSIR STATUSINI YANGILASH API ---

@csrf_exempt
@login_required
def api_cashier_update(request):
    """
    Kassir o'z stansiyasining holatini yangilaydi (GPS tekshiruvi orqali).
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Faqat POST so\'rovi qabul qilinadi.'}, status=400)
        
    try:
        profile = request.user.worker_profile
        station = profile.station
    except StationWorkerProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Sizga hech qanday stansiya biriktirilmagan.'}, status=403)
        
    try:
        data = json.loads(request.body)
        status = data.get('status')
        has_power = data.get('has_power', True)
        gas_pressure = data.get('gas_pressure', 'HIGH')
        price = data.get('price', station.price)
        
        # Geofencing parametrlari
        cashier_lat = data.get('lat')
        cashier_lng = data.get('lng')
        demo_override = data.get('demo_override', False)
        
        # GPS tekshiruvi (agar stansiyada koordinatalar bo'lsa va demo_override o'chirilgan bo'lsa)
        if not demo_override:
            if cashier_lat is None or cashier_lng is None:
                return JsonResponse({'success': False, 'error': 'GPS koordinatalaringiz topilmadi! Iltimos, joylashuvingizni ulashing.'})
            
            # Masofani hisoblash (metrda)
            distance = haversine_distance(
                float(cashier_lat), float(cashier_lng), 
                station.latitude, station.longitude
            ) * 1000.0  # km ni metrga o'tkazish
            
            # Agar 200 metrdan uzoq bo'lsa
            if distance > 200.0:
                return JsonResponse({
                    'success': False, 
                    'error': f'Siz zapravkadan juda uzoqdasiz ({round(distance, 1)} m)! Boshqarish uchun zapravka hududida (200m) bo\'lishingiz kerak.'
                })
                
        # Ma'lumotlarni yangilash
        if status in dict(MethaneStation.STATUS_CHOICES):
            station.status = status
        if gas_pressure in dict(MethaneStation.PRESSURE_CHOICES):
            station.gas_pressure = gas_pressure
            
        station.has_power = bool(has_power)
        station.price = int(price)
        station.last_updated = timezone.now()
        station.save()
        
        return JsonResponse({
            'success': True, 
            'message': 'Zapravka ma\'lumotlari real vaqtda yangilandi!',
            'estimated_wait': station.estimated_wait_time
        })
        
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        return JsonResponse({'success': False, 'error': f"Tizimda xatolik: {str(e)}"}, status=400)


# --- ADMIN API ENPOINTLARI (FAQAT SUPERUSER UCHUN) ---

@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def api_admin_approve_submission(request, sub_id):
    """
    Foydalanuvchi arizasini stansiya sifatida tasdiqlaydi.
    """
    try:
        submission = StationSubmission.objects.get(id=sub_id)
        
        # Arizadan haqiqiy zapravka yaratamiz
        station = MethaneStation.objects.create(
            name=submission.name,
            address=submission.address,
            latitude=submission.latitude,
            longitude=submission.longitude,
            phone=submission.phone,
            region=submission.region,
            district=submission.district,
            is_approved=True
        )
        
        submission.is_processed = True
        submission.save()
        
        return JsonResponse({'success': True, 'message': f"'{station.name}' stansiyasi muvaffaqiyatli tasdiqlandi!"})
    except StationSubmission.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Ariza topilmadi.'}, status=404)


@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def api_admin_reject_submission(request, sub_id):
    """
    Arizani rad etadi (o'chiradi).
    """
    try:
        submission = StationSubmission.objects.get(id=sub_id)
        name = submission.name
        submission.delete()
        return JsonResponse({'success': True, 'message': f"'{name}' stansiya arizasi o'chirildi."})
    except StationSubmission.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Ariza topilmadi.'}, status=404)


@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def api_admin_create_worker(request):
    """
    Yangi kassir foydalanuvchisini yaratadi va unga zapravka biriktiradi.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Faqat POST so\'rovi.'}, status=400)
        
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        station_id = data.get('station_id')
        
        if not username or not password or not station_id:
            return JsonResponse({'success': False, 'error': 'Barcha maydonlarni to\'ldiring.'})
            
        if User.objects.filter(username=username).exists():
            return JsonResponse({'success': False, 'error': 'Ushbu login band!'})
            
        station = MethaneStation.objects.get(id=station_id)
        user = User.objects.create_user(username=username, password=password)
        StationWorkerProfile.objects.create(user=user, station=station)
        
        return JsonResponse({
            'success': True, 
            'message': f"Kassir '{username}' muvaffaqiyatli yaratildi va '{station.name}'ga biriktirildi!"
        })
    except MethaneStation.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Zapravka topilmadi.'})
    except (json.JSONDecodeError, ValueError) as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def api_admin_add_station(request):
    """
    Admin tomonidan to'g'ridan-to'g'ri yangi zapravka qo'shish.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Faqat POST so\'rovi.'}, status=400)
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        address = data.get('address', '').strip()
        lat = float(data.get('latitude', 0))
        lng = float(data.get('longitude', 0))
        phone = data.get('phone', '')
        region = data.get('region', 'Toshkent shahri').strip()
        district = data.get('district', '').strip()
        price = int(data.get('price', 3800))

        if not name or not address or not lat or not lng:
            return JsonResponse({'success': False, 'error': 'Barcha majburiy maydonlarni to\'ldiring.'})

        station = MethaneStation.objects.create(
            name=name, address=address,
            latitude=lat, longitude=lng,
            phone=phone, region=region, district=district,
            price=price, is_approved=True
        )
        return JsonResponse({'success': True, 'message': f"'{station.name}' zapravkasi muvaffaqiyatli qo'shildi!", 'id': station.id})
    except (ValueError, TypeError) as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)



# --- SERVER SETUP (BIR MARTA) ---
def setup_server(request):
    """
    /setup/?key=metan2024 - migrations, seed, admin yaratish
    """
    from django.http import HttpResponse, HttpResponseForbidden
    if request.GET.get('key') != 'metan2024':
        return HttpResponseForbidden('Ruxsat yo\'q!')
    log = []
    try:
        from django.core.management import call_command
        import io
        buf = io.StringIO()
        call_command('migrate', '--run-syncdb', stdout=buf, stderr=buf)
        log.append('✅ migrate OK: ' + buf.getvalue()[-200:].strip())
    except Exception as e:
        log.append(f'❌ migrate xato: {e}')
    try:
        from django.core.management import call_command
        import io
        buf2 = io.StringIO()
        call_command('seed_data', stdout=buf2, stderr=buf2)
        log.append('✅ seed_data OK')
    except Exception as e:
        log.append(f'❌ seed_data: {e}')
    try:
        from django.contrib.auth.models import User
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@mail.com', 'admin123')
            log.append('✅ Admin: login=admin parol=admin123')
        else:
            log.append('ℹ️ Admin allaqachon bor')
    except Exception as e:
        log.append(f'❌ Admin: {e}')
    html = '<h1>Smart Metan Setup</h1><pre>' + '\n'.join(log) + '</pre><a href="/">Asosiy sahifaga</a>'
    return HttpResponse(html)

# --- SETUP (BIR MARTA BAJARISH) ---
def setup_server(request):
    from django.http import HttpResponse, HttpResponseForbidden
    SECRET = 'metan2024'
    if request.GET.get('key') != SECRET:
        return HttpResponseForbidden('Ruxsat yo\'q! ?key=metan2024 qo\'shing')
    log = []
    try:
        from django.core.management import call_command
        import io
        out = io.StringIO()
        call_command('migrate', '--run-syncdb', stdout=out, stderr=out)
        log.append('✅ migrate OK')
    except Exception as e:
        log.append(f'❌ migrate: {e}')
    try:
        from django.core.management import call_command
        import io
        out2 = io.StringIO()
        call_command('seed_data', stdout=out2, stderr=out2)
        log.append('✅ seed_data OK')
    except Exception as e:
        log.append(f'❌ seed_data: {e}')
    try:
        from django.contrib.auth.models import User
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@mail.com', 'admin123')
            log.append('✅ Admin: login=admin, parol=admin123')
        else:
            log.append('ℹ️ Admin allaqachon bor')
    except Exception as e:
        log.append(f'❌ admin: {e}')
    html = '<h2>✅ Smart Metan Setup</h2><pre style="font-size:18px">' + '\n'.join(log) + '</pre>'
    html += '<br><br><a href="/" style="font-size:20px">🏠 Asosiy sahifaga o\'ting</a>'
    return HttpResponse(html)
