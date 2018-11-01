from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from solo.admin import SingletonModelAdmin
from .models import Configuration, AUVLog

admin.site.register(Configuration, SingletonModelAdmin)
admin.site.register(AUVLog, admin.ModelAdmin)

# remove auth models from admin
admin.site.unregister(User)
admin.site.unregister(Group)
