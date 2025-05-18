from django.contrib import admin
from .models import CustomUser, AuthorProfile, EditorProfile, AdminProfile

# Register your models here.
admin.site.register(CustomUser)

@admin.register(AuthorProfile)
class AuthorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'approval_status', 'approved_by')
    list_filter = ('approval_status',)
    actions = ['approve_authors', 'reject_authors']

    def approve_authors(self, request, queryset):
        for profile in queryset:
            profile.approval_status = 'approved'
            profile.user.is_active = True
            profile.user.save()
            profile.save()
    approve_authors.short_description = "Approve selected authors"

    def reject_authors(self, request, queryset):
        for profile in queryset:
            profile.approval_status = 'rejected'
            profile.user.is_active = False
            profile.user.save()
            profile.save()
    reject_authors.short_description = "Reject selected authors"

@admin.register(EditorProfile)
class EditorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'approval_status', 'approved_by')
    list_filter = ('approval_status',)
    actions = ['approve_editors', 'reject_editors']

    def approve_editors(self, request, queryset):
        for profile in queryset:
            profile.approval_status = 'approved'
            profile.user.is_active = True
            profile.user.save()
            profile.save()
    approve_editors.short_description = "Approve selected editors"

    def reject_editors(self, request, queryset):
        for profile in queryset:
            profile.approval_status = 'rejected'
            profile.user.is_active = False
            profile.user.save()
            profile.save()
    reject_editors.short_description = "Reject selected editors"

@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ('user',)
    actions = ['approve_admins', 'reject_admins']

    def approve_admins(self, request, queryset):
        for profile in queryset:
            if hasattr(profile, 'approval_status'):
                profile.approval_status = 'approved'
                profile.user.is_active = True
                profile.user.save()
                profile.save()
            else:
                self.message_user(request, 'Add approval_status field to AdminProfile model for full functionality.', level='warning')
    approve_admins.short_description = "Approve selected admin profiles"

    def reject_admins(self, request, queryset):
        for profile in queryset:
            if hasattr(profile, 'approval_status'):
                profile.approval_status = 'rejected'
                profile.user.is_active = False
                profile.user.save()
                profile.save()
            else:
                self.message_user(request, 'Add approval_status field to AdminProfile model for full functionality.', level='warning')
    reject_admins.short_description = "Reject selected admin profiles"