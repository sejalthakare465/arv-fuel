from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    # This adds columns to the list view so you can see details at a glance
    list_display = ('user_name', 'role', 'mobile', 'weight', 'blood_pressure')
    
    # This adds a "Filter" sidebar on the right! 
    # You can click "Doctor" or "Patient" to see them separately.
    list_filter = ('role',)
    
    # This adds a search bar to look up patients by name or phone
    search_fields = ('user__username', 'mobile')

    # Helper method to show the username in the list
    def user_name(self, obj):
        return obj.user.username
    user_name.short_description = 'User Name'

# If you haven't registered your MealLog yet, do it here too:
# admin.site.register(MealLog)