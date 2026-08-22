import os
import re
import json
import requests
import time
from dotenv import load_dotenv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.http import HttpResponse
from django.db.models import Sum
from django.utils import timezone
from .models import Profile, MealLog, DietAndGroceryPlan, Medication, MedicationLog, EmergencyAlert
from .forms import SignUpForm, CredentialsForm
from .nutrition_db import NUTRITION_DB
from django.conf import settings
from google import genai
from google.genai import types

# Load environment variables from .env
load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_API_KEY") or getattr(settings, 'GEMINI_API_KEY', None)
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY") or getattr(settings, 'SPOONACULAR_API_KEY', None)
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# Word to number mapping for common written quantities
WORD_TO_NUM = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'a': 1, 'an': 1
}




def analyze_meal_description(description_text):
    totals = {"calories": 0.0, "protein": 0.0, "fats": 0.0, "carbs": 0.0}
    matched_any = False

    words = re.findall(r'\b\w+\b', description_text.lower())
    multiplier = 1.0

    print("\n--- MEAL ANALYSIS DEBUG ---")
    print(f"Input Text: '{description_text}'")
    print(f"Tokenized Words: {words}")

    for word in words:
        if word.isdigit():
            multiplier = float(word)
            print(f"Found digit: {word} -> Multiplier set to {multiplier}")
            continue
        elif word in WORD_TO_NUM:
            multiplier = float(WORD_TO_NUM[word])
            print(f"Found word number: {word} -> Multiplier set to {multiplier}")
            continue

        lookup_word = word
        if lookup_word not in NUTRITION_DB and lookup_word.endswith('s'):
            if lookup_word.endswith('es') and lookup_word[:-2] in NUTRITION_DB:
                lookup_word = lookup_word[:-2]
            elif lookup_word[:-1] in NUTRITION_DB:
                lookup_word = lookup_word[:-1]

        if lookup_word in NUTRITION_DB:
            item = NUTRITION_DB[lookup_word]
            cal_added = item["calories"] * multiplier
            totals["calories"] += cal_added
            totals["protein"] += item["protein"] * multiplier
            totals["fats"] += item["fats"] * multiplier
            totals["carbs"] += item.get("carbs", 0.0) * multiplier
            matched_any = True

            print(f"Matched '{lookup_word}' (multiplier: {multiplier}) -> Added {cal_added} kcal")
            multiplier = 1.0

    print(f"Final Aggregated Totals: {totals} | Matched local DB: {matched_any}\n---------------------------\n")
    return totals, matched_any


def home(request):
    return render(request, 'core/home.html')


def register_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            role = form.cleaned_data.get('role', 'patient')
            user_mobile = form.cleaned_data.get('mobile')
            user_address = form.cleaned_data.get('address')
            
            profile, created = Profile.objects.get_or_create(user=user)
            profile.role = role
            profile.mobile = user_mobile
            profile.address = user_address
            profile.save()
            
            login(request, user)
            
            if role == 'doctor':
                return redirect('doctor_dashboard')
            else:
                return redirect('complete_profile')
    else:
        form = SignUpForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def complete_profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = CredentialsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('patient_dashboard')
    else:
        form = CredentialsForm(instance=profile)
    
    return render(request, 'core/complete_profile.html', {'form': form})


@login_required
def patient_dashboard(request):
    # Doctors landing here without a ?user= param shouldn't fall through
    # to the patient-only profile check below.
    if request.user.profile.role == 'doctor' and not request.GET.get('user'):
        return redirect('doctor_dashboard')

    target_username = request.GET.get('user')
    if target_username and request.user.profile.role == 'doctor':
        target_user = get_object_or_404(User, username=target_username)
        profile = target_user.profile
        if profile.doctor_id != request.user.id:
            return HttpResponseForbidden("Access Denied. This patient is not assigned to you.")
    else:
        target_user = request.user
        profile = target_user.profile
        if not profile.weight:
            return redirect('complete_profile')
    
    # Accurate Local Timezone Range for Today
    now = timezone.localtime(timezone.now())
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Filter meals logged within local start/end of today
    meals_today = MealLog.objects.filter(
        user=target_user, 
        timestamp__range=(start_of_day, end_of_day)
    ).order_by('-timestamp')
    
    # 1. Aggregate Daily Totals
    totals = meals_today.aggregate(
        total_fats=Sum('fats'),
        total_cal=Sum('calories'),
        total_prot=Sum('protein')
    )

    fats = totals['total_fats'] or 0.0
    calories = totals['total_cal'] or 0.0
    protein = totals['total_prot'] or 0.0

    fat_cal = round(fats * 9.0, 1)
    prot_cal = round(protein * 4.0, 1)
    carb_cal = max(round(calories - (fat_cal + prot_cal), 1), 0.0)
    carbs = round(carb_cal / 4.0, 1)

    # 2. Build Meal-Specific Breakdown for Chart
    meals_chart_data = []
    for meal in meals_today:
        m_fat_cal = round(meal.fats * 9.0, 1)
        m_prot_cal = round(meal.protein * 4.0, 1)
        m_carb_cal = max(round(meal.calories - (m_fat_cal + m_prot_cal), 1), 0.0)
        m_carbs = round(m_carb_cal / 4.0, 1)

        meals_chart_data.append({
            'id': meal.id,
            'description': meal.description or "Logged Meal",
            'time': timezone.localtime(meal.timestamp).strftime("%I:%M %p"),
            'calories': float(meal.calories),
            'fats': float(meal.fats),
            'protein': float(meal.protein),
            'carbs': float(m_carbs),
            'fat_cal': float(m_fat_cal),
            'prot_cal': float(m_prot_cal),
            'carb_cal': float(m_carb_cal),
        })

    latest_plan = DietAndGroceryPlan.objects.filter(patient=target_user).order_by('-created_at').first()
    latest_medication = Medication.objects.filter(patient=target_user).order_by('-created_at').first()

    context = {
        'meals': meals_today,
        'meals_json': json.dumps(meals_chart_data),
        'fats': round(fats, 1),
        'calories': round(calories, 1),
        'protein': round(protein, 1),
        'carbs': round(carbs, 1),
        'fat_cal': fat_cal,
        'prot_cal': prot_cal,
        'carb_cal': carb_cal,
        'profile': profile,
        'plan': latest_plan,
        'medication': latest_medication,
        'is_doctor_view': request.user.profile.role == 'doctor'
    }
    return render(request, 'core/patient_dashboard.html', context)


@login_required
def doctor_dashboard(request):
    if request.user.profile.role != 'doctor':
        return HttpResponseForbidden("Access Denied. Doctor privileges required.")

    patients = Profile.objects.filter(role='patient', doctor=request.user)
    unassigned_patients = Profile.objects.filter(role='patient', doctor__isnull=True)

    patient_data = []
    now = timezone.localtime(timezone.now())
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    for p in patients:
        today_meals = MealLog.objects.filter(user=p.user, timestamp__range=(start_of_day, end_of_day))
        agg = today_meals.aggregate(f=Sum('fats'), c=Sum('calories'), pr=Sum('protein'))

        patient_data.append({
            'user': p.user,
            'age': p.age,
            'weight': p.weight,
            'blood_pressure': p.blood_pressure,
            'fats': agg['f'] or 0,
            'calories': agg['c'] or 0,
            'protein': agg['pr'] or 0
        })

    context = {
        'patients': patient_data,
        'total_patients': patients.count(),
        'unassigned_patients': unassigned_patients,
    }
    return render(request, 'core/doctor_dashboard.html', context)


@login_required
def send_diet_plan(request):
    if request.method == 'POST' and request.user.profile.role == 'doctor':
        patient_username = request.POST.get('patient_username')
        diet_note = request.POST.get('diet_note')
        grocery_note = request.POST.get('grocery_list', '')

        patient_user = get_object_or_404(User, username=patient_username)
        if patient_user.profile.doctor_id != request.user.id:
            return HttpResponseForbidden("Access Denied. This patient is not assigned to you.")

        DietAndGroceryPlan.objects.create(
            patient=patient_user,
            doctor=request.user,
            meal_plan=diet_note,
            grocery_list=grocery_note
        )
        return redirect('doctor_dashboard')

    return HttpResponseForbidden("Invalid action.")

@login_required
def send_medication(request):
    if request.method == 'POST' and request.user.profile.role == 'doctor':
        patient_username = request.POST.get('patient_username')
        drug_name = request.POST.get('drug_name', '').strip()
        dosage = request.POST.get('dosage', '').strip()
        time_of_day = request.POST.get('time_of_day', '').strip()
        reminder_time = request.POST.get('reminder_time') or None
        notes = request.POST.get('medication_notes', '').strip()

        patient_user = get_object_or_404(User, username=patient_username)
        if patient_user.profile.doctor_id != request.user.id:
            return HttpResponseForbidden("Access Denied. This patient is not assigned to you.")

        Medication.objects.create(
            patient=patient_user,
            doctor=request.user,
            drug_name=drug_name,
            dosage=dosage,
            time_of_day=time_of_day,
            reminder_time=reminder_time,
            notes=notes
        )
        return redirect('doctor_dashboard')

    return HttpResponseForbidden("Invalid action.")

@login_required
def mark_medication_taken(request):
    if request.method == 'POST':
        MedicationLog.objects.create(patient=request.user)
        return JsonResponse({'status': 'ok'})
    return HttpResponseForbidden("Invalid action.")


@login_required
def trigger_emergency_alert(request):
    if request.method == 'POST':
        profile = request.user.profile
        if not profile.doctor:
            return JsonResponse({'status': 'error', 'message': 'No doctor assigned yet.'})

        already_active = EmergencyAlert.objects.filter(patient=request.user, resolved=False).exists()
        if already_active:
            return JsonResponse({
                'status': 'already_active',
                'message': "Your doctor's already been alerted and hasn't responded yet — sit tight."
            })

        EmergencyAlert.objects.create(patient=request.user, doctor=profile.doctor)
        return JsonResponse({'status': 'ok'})

    return HttpResponseForbidden("Invalid action.")


@login_required
def resolve_emergency_alert(request, alert_id):
    if request.method == 'POST' and request.user.profile.role == 'doctor':
        alert = get_object_or_404(EmergencyAlert, id=alert_id, doctor=request.user)
        alert.resolved = True
        alert.resolved_at = timezone.now()
        alert.save()
        return JsonResponse({'status': 'ok'})
    return HttpResponseForbidden("Invalid action.")


@login_required
def poll_emergency_alerts(request):
    """Lightweight endpoint the doctor dashboard polls for new alerts."""
    if request.user.profile.role != 'doctor':
        return HttpResponseForbidden("Access Denied.")
    alerts = EmergencyAlert.objects.filter(doctor=request.user, resolved=False).order_by('-created_at')
    data = [{
        'id': a.id,
        'patient': a.patient.username,
        'created_at': timezone.localtime(a.created_at).strftime("%I:%M %p"),
    } for a in alerts]
    return JsonResponse({'alerts': data})


@login_required
def ai_assistant_response(request):
    first_name = request.user.first_name or request.user.username.split('@')[0]

    try:
        user_msg = ""
        if request.body:
            try:
                data = json.loads(request.body.decode('utf-8'))
                user_msg = data.get('message') or data.get('msg') or ""
            except Exception:
                pass

        if not user_msg:
            user_msg = (
                request.POST.get('message') or
                request.POST.get('msg') or
                request.GET.get('message') or
                request.GET.get('msg') or ''
            )

        user_msg = user_msg.strip()

        if not user_msg:
            return JsonResponse({'reply': f"Hello {first_name}! I'm right beside you. What's on your mind today?"})

        # Daily context
        now = timezone.localtime(timezone.now())
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        from .models import MealLog
        totals = MealLog.objects.filter(
            user=request.user,
            timestamp__range=(start_of_day, end_of_day)
        ).aggregate(c=Sum('calories'), p=Sum('protein'), f=Sum('fats'))

        daily_cal = totals['c'] or 0
        daily_prot = totals['p'] or 0

        sys_instruction = (
            "You are 'Mindful Buddy', an intelligent, warm, and deeply knowledgeable AI companion on the ARV Fuel platform. "
            "You are NOT limited to a fixed topic list — treat yourself as a full general-purpose assistant with a health & wellness specialty.\n\n"
            "WHAT YOU CAN HELP WITH (non-exhaustive):\n"
            "- Nutrition & calories: any food, drink, or dish — calories, macros, micronutrients, portion sizes, comparisons.\n"
            "- Fitness: workout ideas, exercise form basics, recovery, injury-safe alternatives (never replace a doctor for injuries).\n"
            "- Sleep, hydration, stress management, habit-building, and general healthy lifestyle questions.\n"
            "- Motivation & emotional support: encouragement, reframing setbacks, celebrating wins, gentle accountability.\n"
            "- Anything else the user brings up in conversation — small talk, general knowledge, productivity tips, or just listening. "
            "Answer naturally rather than redirecting back to 'health topics only'.\n\n"
            "TONE RULES:\n"
            "- Sad/stressed/anxious/tired → gentle, comforting, validating.\n"
            "- Happy/proud/excited → energetic, celebratory.\n"
            "- Neutral/factual questions → clear and direct, still warm.\n\n"
            "STYLE:\n"
            "- Keep replies concise: 2-5 sentences unless the user asks for detail (e.g. a full meal plan or workout routine).\n"
            "- Use the user's logged daily totals only when relevant to what they're asking — don't force it in.\n"
            "- Never claim to be a doctor; suggest professional care for medical concerns beyond general wellness advice.\n"
            "- Occasional light emoji is fine, don't overdo it."
        )

        user_prompt = f"User Name: {first_name}\nLogged Today: {daily_cal} kcal ({daily_prot}g protein)\nUser Message: {user_msg}"

        if not client:
            return JsonResponse({'reply': "API Key missing in environment! Please check your .env file."})

        response = None
        last_error = None
        for attempt in range(2):  # try once, retry once on transient errors
            try:
                response = client.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=sys_instruction,
                        temperature=0.7,
                    )
                )
                break
            except Exception as api_err:
                last_error = api_err
                error_str = str(api_err)
                if '503' in error_str or 'UNAVAILABLE' in error_str:
                    print(f"!!! GEMINI 503, retrying (attempt {attempt + 1}) !!!")
                    time.sleep(1.5)
                    continue
                raise

        if response is None:
            raise last_error

        reply = response.text.strip()
        return JsonResponse({'reply': reply})

    except Exception as e:
        print(f"!!! GEMINI API ERROR: {e} !!!")
        return JsonResponse({'reply': f"I'm right here with you, {first_name}! Let's try that query again."})

def fetch_spoonacular_nutrition(desc):
    """Fetch accurate macros from Spoonacular API based on a free-text ingredient description"""
    url = "https://api.spoonacular.com/recipes/parseIngredients"
    params = {
        'apiKey': SPOONACULAR_API_KEY,
        'includeNutrition': 'true'
    }

    try:
        response = requests.post(
            url,
            params=params,
            data={'ingredientList': desc, 'servings': 1},
            timeout=5
        )

        if response.status_code == 200:
            parsed = response.json()
            if not parsed:
                return 250.0, 8.0, 10.0, 30.0

            total_cal, total_prot, total_fat, total_carb = 0.0, 0.0, 0.0, 0.0

            for item in parsed:
                nutrients = item.get('nutrition', {}).get('nutrients', [])
                for n in nutrients:
                    name = n.get('name', '').lower()
                    amount = n.get('amount', 0.0)
                    if name == 'calories':
                        total_cal += amount
                    elif name == 'protein':
                        total_prot += amount
                    elif name == 'fat':
                        total_fat += amount
                    elif name == 'carbohydrates':
                        total_carb += amount

            if total_cal == 0 and total_prot == 0 and total_fat == 0:
                return 250.0, 8.0, 10.0, 30.0
            if total_cal < 15:
                print(f"!!! SPOONACULAR SUSPICIOUS LOW RESULT ({total_cal} kcal) for '{desc}' — using fallback !!!")
                return 250.0, 8.0, 10.0, 30.0

            return round(total_cal, 1), round(total_prot, 1), round(total_fat, 1), round(total_carb, 1)

    except requests.exceptions.RequestException as e:
        print(f"!!! SPOONACULAR API ERROR: {e} !!!")
    except (KeyError, ValueError, TypeError) as e:
        print(f"!!! SPOONACULAR PARSE ERROR: {e} !!!")

    return 250.0, 8.0, 10.0, 30.0


@login_required
def upload_meal(request):
    if request.method == 'POST':
        raw_description = request.POST.get('description', '').strip()
        meal_image = request.FILES.get('meal_image', None)

        nutrition, matched = analyze_meal_description(raw_description)

        # Fall back to Spoonacular if the local DB didn't recognize anything
        if not matched and raw_description:
            print(f"No local DB match for '{raw_description}' — trying Spoonacular...")
            cal, prot, fat, carb = fetch_spoonacular_nutrition(raw_description)
            nutrition = {
                "calories": cal,
                "protein": prot,
                "fats": fat,
                "carbs": carb
    }

        MealLog.objects.create(
            user=request.user,
            description=raw_description if raw_description else "Photo Meal Log",
            image=meal_image,
            calories=nutrition["calories"],
            protein=nutrition["protein"],
            fats=nutrition["fats"]
        )

        return redirect('patient_dashboard')

    return redirect('patient_dashboard')



@login_required
def delete_meal(request, meal_id):
    meal = get_object_or_404(MealLog, id=meal_id, user=request.user)
    if request.method == 'POST':
        if meal.image:
            meal.image.delete(save=False)
        meal.delete()
    return redirect('patient_dashboard')

@login_required
def assign_patient(request, patient_id):
    if request.user.profile.role != 'doctor':
        return HttpResponseForbidden("Access Denied. Doctor privileges required.")

    if request.method == 'POST':
        patient_profile = get_object_or_404(Profile, user__id=patient_id, role='patient')

        # Prevent hijacking a patient already assigned to another doctor
        if patient_profile.doctor is not None and patient_profile.doctor != request.user:
            return HttpResponseForbidden("This patient is already assigned to another doctor.")

        patient_profile.doctor = request.user
        patient_profile.save()

    return redirect('doctor_dashboard')


@login_required
def unassign_patient(request, patient_id):
    if request.user.profile.role != 'doctor':
        return HttpResponseForbidden("Access Denied. Doctor privileges required.")

    if request.method == 'POST':
        patient_profile = get_object_or_404(Profile, user__id=patient_id, role='patient', doctor=request.user)
        patient_profile.doctor = None
        patient_profile.save()

    return redirect('doctor_dashboard')

def service_worker(request):
    path = os.path.join(settings.BASE_DIR, 'core', 'static', 'service-worker.js')
    with open(path, 'r') as f:
        content = f.read()
    return HttpResponse(content, content_type='application/javascript')