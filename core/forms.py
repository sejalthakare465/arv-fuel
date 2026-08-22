from django import forms
from django.contrib.auth.models import User
from .models import Profile

# STEP 1: Basic Account Creation (Name, Email, Mobile, Address)
class SignUpForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'sketch-border p-2 w-full mb-4', 'placeholder': 'Password'})
    )
    role = forms.ChoiceField(
        choices=Profile.ROLE_CHOICES, 
        widget=forms.RadioSelect(attrs={'class': 'flex gap-4 mb-4'})
    )
    
    # These extra fields populate Profile during register_view
    mobile = forms.CharField(
        max_length=15, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'sketch-border p-2 w-full mb-4', 'placeholder': 'Mobile No.'})
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'sketch-border p-2 w-full mb-4', 'rows': 3, 'placeholder': 'Address'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'sketch-border p-2 w-full mb-4', 'placeholder': 'Username'}),
            'first_name': forms.TextInput(attrs={'class': 'sketch-border p-2 w-full mb-4', 'placeholder': 'Full Name'}),
            'email': forms.EmailInput(attrs={'class': 'sketch-border p-2 w-full mb-4', 'placeholder': 'Email Address'}),
        }

    # 🔑 Fix: Properly hash password before saving User
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


# STEP 2: Establishing the Baseline (Age, Weight, Height, BP)
class CredentialsForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['age', 'weight', 'height', 'blood_pressure'] 
        widgets = {
            'age': forms.NumberInput(attrs={'class': 'sketch-border p-2 w-full mb-4', 'placeholder': 'Age'}),
            'weight': forms.NumberInput(attrs={'class': 'sketch-border p-2 w-full mb-4', 'placeholder': 'Weight (kg)'}),
            'height': forms.NumberInput(attrs={'class': 'sketch-border p-2 w-full mb-4', 'placeholder': 'Height (cm)'}),
            'blood_pressure': forms.TextInput(attrs={'class': 'sketch-border p-2 w-full mb-4', 'placeholder': 'e.g. 120/80'}),
        }