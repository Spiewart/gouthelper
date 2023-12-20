from django.contrib import admin

from .models import AdminProfile, PatientProfile, ProviderProfile, PseudopatientProfile


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ("user",)


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "provider",
    )


@admin.register(ProviderProfile)
class ProviderProfileAdmin(admin.ModelAdmin):
    list_display = ("user",)


@admin.register(PseudopatientProfile)
class PseudopatientProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "provider",
    )
