from django.contrib import admin
from django.db.models import TextField
from django.forms import Textarea
from django_fsm_log.admin import StateLogInline

from . import models


@admin.register(models.Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "state", "start", "end", "last_updated", "reference")
    list_filter = ("state", "start", "end", "last_updated")
    list_per_page = 50
    ordering = ("-last_updated",)
    search_fields = ("reference__startswith",)
    formfield_overrides = {TextField: {"widget": Textarea(attrs={"cols": "100", "rows": 1})}}
    readonly_fields = ("state", "start", "end", "reference", "last_updated", "reason")
    fields = ("state", "start", "end", "reference", "last_updated", "reason")
    inlines = [StateLogInline]
