from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from monitoring.models import MethaneStation, StationWorkerProfile

class Command(BaseCommand):
    help = 'Boshlang\'ich test metan zapravkalar va kassir foydalanuvchilarini yaratadi.'

    def handle(self, *args, **options):
        self.stdout.write("Boshlang'ich ma'lumotlar yuklanmoqda...")

        # 1. Superuser yaratish (agar mavjud bo'lmasa)
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@smartmetan.uz', 'adminpass123')
            self.stdout.write(self.style.SUCCESS("Superadmin yaratildi: admin / adminpass123"))
        else:
            self.stdout.write("Superadmin 'admin' allaqachon mavjud.")

        # 2. Zapravkalar ma'lumotlarini yaratish
        stations_data = [
            {
                'name': 'Yunusobod Metan (Oazis)',
                'address': 'Toshkent shahri, Yunusobod tumani, A.Temur ko\'chasi, 12-uy',
                'latitude': 41.3643,
                'longitude': 69.2872,
                'status': 'GREEN',
                'has_power': True,
                'gas_pressure': 'HIGH',
                'price': 3800,
                'phone': '+998901234567',
                'region': 'Toshkent shahri',
                'district': 'Yunusobod tumani',
                'is_approved': True
            },
            {
                'name': 'Chilonzor Gaz Servis',
                'address': 'Toshkent shahri, Chilonzor tumani, Lutfiy ko\'chasi, 45-uy',
                'latitude': 41.2721,
                'longitude': 69.2032,
                'status': 'YELLOW',
                'has_power': True,
                'gas_pressure': 'LOW',
                'price': 3750,
                'phone': '+998931112233',
                'region': 'Toshkent shahri',
                'district': 'Chilonzor tumani',
                'is_approved': True
            },
            {
                'name': 'Sergeli Metan-1',
                'address': 'Toshkent shahri, Sergeli tumani, Yangi Sergeli yo\'li ko\'chasi',
                'latitude': 41.2289,
                'longitude': 69.2223,
                'status': 'RED',
                'has_power': True,
                'gas_pressure': 'HIGH',
                'price': 3800,
                'phone': '+998944445566',
                'region': 'Toshkent shahri',
                'district': 'Sergeli tumani',
                'is_approved': True
            },
            {
                'name': 'Qoraqamish Gaz stansiyasi',
                'address': 'Toshkent shahri, Olmazor tumani, Qoraqamish-3 daxasi',
                'latitude': 41.3551,
                'longitude': 69.2148,
                'status': 'BLACK',
                'has_power': False,
                'gas_pressure': 'NONE',
                'price': 3800,
                'phone': '+998956667788',
                'region': 'Toshkent shahri',
                'district': 'Olmazor tumani',
                'is_approved': True
            },
            {
                'name': 'Qo\'yliq Metan Shoxobchasi',
                'address': 'Toshkent shahri, Bektemir tumani, Farg\'ona yo\'li ko\'chasi',
                'latitude': 41.2412,
                'longitude': 69.3242,
                'status': 'WHITE',
                'has_power': True,
                'gas_pressure': 'HIGH',
                'price': 3780,
                'phone': '+998978889900',
                'region': 'Toshkent shahri',
                'district': 'Bektemir tumani',
                'is_approved': True
            }
        ]

        created_stations = []
        for data in stations_data:
            station, created = MethaneStation.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            created_stations.append(station)
            if created:
                self.stdout.write(f"Stansiya yaratildi: {station.name}")
            else:
                # Agar bor bo'lsa ma'lumotlarni qayta yangilaymiz test uchun qulay bo'lishi uchun
                for key, val in data.items():
                    setattr(station, key, val)
                station.save()
                self.stdout.write(f"Stansiya yangilandi: {station.name}")

        # 3. Kassirlarni yaratish va bog'lash
        # Kassir 1 -> Yunusobod Metan
        if not User.objects.filter(username='kassir1').exists():
            user1 = User.objects.create_user('kassir1', 'kassir1@metan.uz', 'kassirpass123')
            StationWorkerProfile.objects.create(user=user1, station=created_stations[0])
            self.stdout.write(self.style.SUCCESS("Kassir 1 yaratildi: kassir1 / kassirpass123 -> Yunusobod Metan"))
        else:
            self.stdout.write("Kassir 1 'kassir1' allaqachon bor.")

        # Kassir 2 -> Chilonzor Gaz Servis
        if not User.objects.filter(username='kassir2').exists():
            user2 = User.objects.create_user('kassir2', 'kassir2@metan.uz', 'kassirpass123')
            StationWorkerProfile.objects.create(user=user2, station=created_stations[1])
            self.stdout.write(self.style.SUCCESS("Kassir 2 yaratildi: kassir2 / kassirpass123 -> Chilonzor Gaz"))
        else:
            self.stdout.write("Kassir 2 'kassir2' allaqachon bor.")

        self.stdout.write(self.style.SUCCESS("Boshlang'ich ma'lumotlar muvaffaqiyatli yuklandi!"))
