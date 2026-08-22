from django.contrib import admin
from django.urls import path
from core import views
from django.conf import settings
from django.contrib.auth import views as auth_views
from django.conf.urls.static import static

urlpatterns = [
    # Home & Auth
    path('', views.home, name='home'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('service-worker.js', views.service_worker, name='service_worker'),
    
    # Patient Flow (Matches your sketchbook Page 2 & 3)
    path('setup/', views.complete_profile, name='complete_profile'), # The Baseline Setup
    path('dashboard/', views.patient_dashboard, name='patient_dashboard'), # The Nutrition Track
    path('upload-meal/', views.upload_meal, name='upload_meal'),
    path('delete-meal/<int:meal_id>/', views.delete_meal, name='delete_meal'), # Deletes meal log & recalcs macros
    path('ai-chat/', views.ai_assistant_response, name='ai_chat'),
    
    # Doctor Flow (Matches your Command Center sketches)
    path('doctor-dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('send-diet-plan/', views.send_diet_plan, name='send_diet_plan'),
    path('assign-patient/<int:patient_id>/', views.assign_patient, name='assign_patient'),
    path('unassign-patient/<int:patient_id>/', views.unassign_patient, name='unassign_patient'),
    path('send-medication/', views.send_medication, name='send_medication'),
    path('mark-medication-taken/', views.mark_medication_taken, name='mark_medication_taken'),
    path('emergency-alert/', views.trigger_emergency_alert, name='trigger_emergency_alert'),
    path('resolve-alert/<int:alert_id>/', views.resolve_emergency_alert, name='resolve_emergency_alert'),
    path('poll-alerts/', views.poll_emergency_alerts, name='poll_emergency_alerts'),
    # Admin
    path('admin/', admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)