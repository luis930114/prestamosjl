""" User admin classes. """
#Django
from django.contrib import admin

#Models
from users.models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """ Profile admin. """

    list_display = ()
    list_display_links = ()
    list_editable = ()
    search_fields = (

    )
    list_filter = (

        )