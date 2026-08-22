from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    ROLE_CHOICES = [
        ('patient', 'Patient'),
        ('doctor', 'Doctor/Nutritionist'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='patient')
    
    # Registration & Contact Info (Page 1)
    mobile = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    # Baseline Health Data (Page 2)
    age = models.IntegerField(null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)
    blood_pressure = models.CharField(max_length=20, null=True, blank=True)

    # Doctor-Patient Assignment Link
    doctor = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_patients'
    )

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class MealLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meal_logs')
    # Made image optional so text-only meal entries don't raise validation errors
    image = models.ImageField(upload_to='meal_selfies/', blank=True, null=True)
    description = models.TextField(blank=True) 
    
    # Nutrition Breakdown (Page 2 Pie Chart Data)
    fats = models.FloatField(default=0)
    calories = models.FloatField(default=0)
    protein = models.FloatField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    # Doctor Review & Approval Status (Page 3)
    is_approved = models.BooleanField(default=False)
    doctor_feedback = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Meal by {self.user.username} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class DietAndGroceryPlan(models.Model):
    """
    Directly supports Page 4 requirements:
    - Meal plan creation for each patient and sending it
    - Grocery list creation and sending
    """
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_plans')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_plans')
    
    meal_plan = models.TextField(help_text="Daily meal guide created by doctor")
    grocery_list = models.TextField(blank=True, null=True, help_text="Grocery items recommended by doctor")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Plan for {self.patient.username} by Dr. {self.doctor.username}"

class Medication(models.Model):
    """
    Doctor-managed ARV medication regimen for a patient. HIV regimens are
    often combination therapies, so drug name and dosage are kept as
    separate fields — doctors frequently prescribe fixed-dose combination
    pills (e.g. TLD, Biktarvy) with dosing instructions that vary by drug.
    """
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medications')
    doctor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='prescribed_medications')

    drug_name = models.TextField(help_text="e.g. 'Biktarvy (Bictegravir/Emtricitabine/TAF)' or 'TLD (Tenofovir/Lamivudine/Dolutegravir)'")
    dosage = models.TextField(help_text="e.g. '1 tablet, once daily, with food'")
    time_of_day = models.CharField(max_length=100, blank=True, help_text="e.g. '10:00 AM' or 'Every evening'")
    notes = models.TextField(blank=True, help_text="Additional instructions from the doctor")
    reminder_time = models.TimeField(null=True, blank=True, help_text="Structured time for reminder logic (separate from the display text above)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.drug_name} — {self.patient.username}"

class MedicationLog(models.Model):
    """Records when a patient confirms they've taken their dose."""
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medication_logs')
    taken_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.username} took meds at {self.taken_at}"


class EmergencyAlert(models.Model):
    """Patient-triggered emergency alert to their assigned doctor."""
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='emergency_alerts')
    doctor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='received_alerts')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        status = "resolved" if self.resolved else "ACTIVE"
        return f"Alert from {self.patient.username} ({status})"    