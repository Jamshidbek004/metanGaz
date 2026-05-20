from django.contrib import admin
from .models import MethaneStation, StationWorkerProfile, StationSubmission


@admin.register(MethaneStation)
class MethaneStationAdmin(admin.ModelAdmin):
    list_display = ['name', 'region', 'district', 'status', 'has_power', 'gas_pressure', 'price', 'is_approved', 'last_updated']
    list_filter = ['status', 'region', 'is_approved', 'has_power', 'gas_pressure']
    search_fields = ['name', 'address', 'region', 'district']
    list_editable = ['status', 'has_power', 'is_approved', 'price']
    ordering = ['-last_updated']
    readonly_fields = ['last_updated', 'created_at']


@admin.register(StationWorkerProfile)
class StationWorkerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'station']
    list_filter = ['station__region']
    search_fields = ['user__username', 'station__name']


@admin.register(StationSubmission)
class StationSubmissionAdmin(admin.ModelAdmin):
    list_display = ['name', 'region', 'district', 'phone', 'created_at', 'is_processed']
    list_filter = ['is_processed', 'region']
    search_fields = ['name', 'address']
    ordering = ['-created_at']
