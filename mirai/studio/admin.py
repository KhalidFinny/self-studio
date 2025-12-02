from django.contrib import admin
from .models import Capture

@admin.register(Capture)
class CaptureAdmin(admin.ModelAdmin):
    list_display = ('id', 'timestamp', 'gesture')
    list_filter = ('timestamp', 'gesture')
    search_fields = ('gesture',)
