from django.contrib import admin

from .models import User, Seeder, Setting, Target_User, Follower, Following

admin.site.register(User)
admin.site.register(Target_User)
admin.site.register(Follower)
admin.site.register(Following)
admin.site.register(Setting)
admin.site.register(Seeder)