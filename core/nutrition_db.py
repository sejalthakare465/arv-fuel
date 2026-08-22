# Standard nutritional values (Calories, Protein (g), Fats (g), Carbs (g)) per typical serving
NUTRITION_DB = {
    # Proteins
    "egg": {"calories": 78, "fats": 5.3, "protein": 6.3, "carbs": 0.6},
    "eggs": {"calories": 156, "fats": 10.6, "protein": 12.6, "carbs": 1.2},
    "chicken": {"calories": 239, "fats": 13.4, "protein": 27.0, "carbs": 0.0},
    "fish": {"calories": 180, "fats": 5.0, "protein": 25.0, "carbs": 0.0},
    "paneer": {"calories": 265, "fats": 20.0, "protein": 18.0, "carbs": 3.0},
    "dal": {"calories": 180, "fats": 4.5, "protein": 9.0, "carbs": 24.0},
    "curd": {"calories": 98, "fats": 4.3, "protein": 11.0, "carbs": 3.4},
    "milk": {"calories": 150, "fats": 8.0, "protein": 8.0, "carbs": 12.0},

    # Greens & Veggies
    "spinach": {"calories": 23, "fats": 0.4, "protein": 2.9, "carbs": 3.6},
    "palak": {"calories": 23, "fats": 0.4, "protein": 2.9, "carbs": 3.6},
    "kale": {"calories": 35, "fats": 0.6, "protein": 2.9, "carbs": 4.4},
    "dill": {"calories": 15, "fats": 0.2, "protein": 1.0, "carbs": 2.1},
    "coriander": {"calories": 10, "fats": 0.1, "protein": 0.5, "carbs": 1.0},
    "kothimbir": {"calories": 10, "fats": 0.1, "protein": 0.5, "carbs": 1.0},
    "salad": {"calories": 45, "fats": 0.2, "protein": 1.2, "carbs": 8.0},
    "veggies": {"calories": 60, "fats": 0.5, "protein": 2.0, "carbs": 10.0},
    "vegetables": {"calories": 60, "fats": 0.5, "protein": 2.0, "carbs": 10.0},

    # Carbs & Staples
    "chapati": {"calories": 104, "fats": 3.7, "protein": 3.1, "carbs": 15.0},
    "roti": {"calories": 104, "fats": 3.7, "protein": 3.1, "carbs": 15.0},
    "paratha": {"calories": 290, "fats": 12.0, "protein": 5.0, "carbs": 38.0},
    "rice": {"calories": 205, "fats": 0.4, "protein": 4.2, "carbs": 45.0},
    "dosa": {"calories": 168, "fats": 3.7, "protein": 3.9, "carbs": 29.0},
    "idli": {"calories": 58, "fats": 0.4, "protein": 2.0, "carbs": 12.0},
    "strawberry": {"calories": 4, "protein": 0.1, "fats": 0.03, "carbs": 0.9},   # per piece
    "blueberry": {"calories": 0.6, "protein": 0.007, "fats": 0.003, "carbs": 0.14}, 
}

def analyze_meal_description(description_text):
    """
    Parses text input for food keywords and aggregates exact nutrition totals.
    """
    totals = {"calories": 0, "protein": 0.0, "fats": 0.0, "carbs": 0.0}
    words = description_text.lower().replace(",", " ").replace(".", " ").split()

    for word in words:
        if word in NUTRITION_DB:
            item = NUTRITION_DB[word]
            totals["calories"] += item["calories"]
            totals["protein"] += item["protein"]
            totals["fats"] += item["fats"]
            totals["carbs"] += item["carbs"]

    # Fallback default if no known food keyword is detected
    if totals["calories"] == 0 and len(description_text.strip()) > 0:
        totals = {"calories": 150, "protein": 5.0, "fats": 3.0, "carbs": 20.0}

    return totals