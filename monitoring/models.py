from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class MethaneStation(models.Model):
    STATUS_CHOICES = [
        ('GREEN', '🟢 Yashil (1-5 ta mashina)'),
        ('YELLOW', '🟡 Sariq (6-15 ta mashina)'),
        ('RED', '🔴 Qizil (15+ mashina)'),
        ('BLACK', '⚫ Yopiq / Ishlamayapti'),
        ('WHITE', '⚪ Ma\'lumot yo\'q'),
    ]

    PRESSURE_CHOICES = [
        ('HIGH', 'Yaxshi (Normal)'),
        ('LOW', 'Past (Bosim kam)'),
        ('NONE', 'Bosim yo\'q (Gaz yo\'q)'),
    ]

    name = models.CharField(max_length=150, verbose_name="Zapravka nomi")
    address = models.TextField(verbose_name="Manzili")
    latitude = models.FloatField(verbose_name="Kenglik (Latitude)")
    longitude = models.FloatField(verbose_name="Uzunlik (Longitude)")
    
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='WHITE', 
        verbose_name="Navbat holati"
    )
    has_power = models.BooleanField(default=True, verbose_name="Elektr energiyasi (Svet)")
    gas_pressure = models.CharField(
        max_length=10, 
        choices=PRESSURE_CHOICES, 
        default='HIGH', 
        verbose_name="Gaz bosimi"
    )
    price = models.IntegerField(default=3800, verbose_name="1 m³ gaz narxi (so'm)")
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Aloqa telefoni")
    
    region = models.CharField(max_length=100, verbose_name="Viloyat")
    district = models.CharField(max_length=100, verbose_name="Tuman")
    
    is_approved = models.BooleanField(default=False, verbose_name="Tasdiqlangan stansiya")
    
    last_updated = models.DateTimeField(auto_now=True, verbose_name="Oxirgi yangilanish vaqti")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")

    class Meta:
        verbose_name = "Metan Zapravka"
        verbose_name_plural = "Metan Zapravkalar"
        ordering = ['-last_updated']

    def __str__(self):
        return f"{self.name} ({self.region}, {self.district})"

    @property
    def estimated_wait_time(self):
        """
        Navbat, svet va bosim holatidan kelib chiqib, taxminiy kutish vaqtini daqiqalarda hisoblaydi.
        """
        if not self.has_power:
            return "Elektr yo'q (Svet o'chgan)"
        
        if self.gas_pressure == 'NONE':
            return "Gaz bosimi yo'q (Ishlamayapti)"
            
        if self.status == 'BLACK':
            return "Yopiq / Ishlamayapti"
            
        if self.status == 'WHITE':
            return "Ma'lumot yo'q"
            
        # Gaz bosimi past bo'lsa, navbat sekinroq yuradi (vaqt 2 barobar ko'payadi)
        multiplier = 2.0 if self.gas_pressure == 'LOW' else 1.0
        
        if self.status == 'GREEN':
            return f"~{int(10 * multiplier)} daqiqa kutish"
        elif self.status == 'YELLOW':
            return f"~{int(30 * multiplier)} daqiqa kutish"
        elif self.status == 'RED':
            return f"~{int(75 * multiplier)} daqiqadan ko'p kutish"
            
        return "Ma'lumot yo'q"


class StationWorkerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='worker_profile')
    station = models.ForeignKey(MethaneStation, on_delete=models.CASCADE, related_name='workers', verbose_name="Ish joyi (Zapravka)")

    class Meta:
        verbose_name = "Kassir Profili"
        verbose_name_plural = "Kassirlar Profillari"

    def __str__(self):
        return f"{self.user.username} - {self.station.name}"


class StationSubmission(models.Model):
    name = models.CharField(max_length=150, verbose_name="Taqdim etilgan zapravka nomi")
    address = models.TextField(verbose_name="Manzili")
    latitude = models.FloatField(verbose_name="Kenglik (Latitude)")
    longitude = models.FloatField(verbose_name="Uzunlik (Longitude)")
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Aloqa raqami")
    
    region = models.CharField(max_length=100, verbose_name="Viloyat")
    district = models.CharField(max_length=100, verbose_name="Tuman")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yuborilgan vaqti")
    is_processed = models.BooleanField(default=False, verbose_name="Ko'rib chiqildi")

    class Meta:
        verbose_name = "Yangi Zapravka Arizasi"
        verbose_name_plural = "Yangi Zapravka Arizalari"
        ordering = ['-created_at']

    def __str__(self):
        return f"Ariza: {self.name} ({self.region})"
