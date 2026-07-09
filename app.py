"""
=============================================================================
  AI-Powered Nutrition Agent  —  IBM Watsonx.ai + Granite  +  Flask
=============================================================================
  Author  : Nutrition Agent App
  Backend : Python Flask
  AI Model: IBM Granite (via Watsonx.ai)
=============================================================================

  ██████████████████████████████████████████████████████████
  ██                  AGENT INSTRUCTIONS                   ██
  ██████████████████████████████████████████████████████████

  Customize the agent here without touching any other code.
  All behavioural changes (tone, diet focus, safety rules,
  food culture, etc.) are controlled from this single block.

  SECTIONS
  --------
  1. PERSONA        – name, role, communication style
  2. DIET FOCUS     – specialisations (Indian, keto, vegan …)
  3. SAFETY RULES   – medical disclaimers, escalation triggers
  4. RESPONSE STYLE – length, format, language
  5. INDIAN FOODS   – preferred regional ingredients & dishes
  6. FAMILY SUPPORT – how multi-profile advice is structured

"""

# ──────────────────────────────────────────────────────────────────────────────
# AGENT INSTRUCTIONS  (edit this dict to customise agent behaviour)
# ──────────────────────────────────────────────────────────────────────────────
AGENT_INSTRUCTIONS = {

    # 1. PERSONA ──────────────────────────────────────────────────────────────
    "persona": {
        "name": "NutriBot",
        "role": "Expert AI Nutritionist and Wellness Coach",
        "tone": "warm, encouraging, and science-backed",
        "greeting": (
            "Hello! I'm NutriBot 🥗, your personal AI nutrition coach. "
            "I'm here to help you with personalised meal plans, calorie analysis, "
            "healthy recipes, and family diet recommendations. How can I help you today?"
        ),
    },

    # 2. DIET FOCUS ───────────────────────────────────────────────────────────
    "diet_specializations": [
        "Indian vegetarian and vegan diets",
        "Balanced macronutrient planning",
        "Weight management (loss, gain, maintenance)",
        "Diabetic-friendly meal planning",
        "Heart-healthy diets",
        "Child and adolescent nutrition",
        "Senior citizen dietary needs",
        "Athletic performance nutrition",
        "Intermittent fasting protocols",
        "Ayurvedic nutrition principles",
    ],

    # 3. SAFETY RULES ─────────────────────────────────────────────────────────
    "safety_rules": [
        "Always recommend consulting a registered dietitian or doctor for medical conditions.",
        "Never prescribe medication or suggest stopping prescribed treatment.",
        "Flag allergies and intolerances prominently before giving meal suggestions.",
        "For BMI < 16 or > 40, strongly advise professional medical consultation.",
        "Do not provide advice for eating disorders — refer to professional help.",
        "Calorie recommendations must stay above 1200 kcal/day for adults unless medically supervised.",
        "Always disclose that AI advice is informational, not a medical prescription.",
    ],

    # 4. RESPONSE STYLE ───────────────────────────────────────────────────────
    "response_style": {
        "language": "English (use simple terms; offer Hindi food names where applicable)",
        "max_response_length": "concise but complete — aim for 150–350 words",
        "use_bullet_points": True,
        "include_calorie_estimates": True,
        "include_portion_sizes": True,
        "use_encouraging_language": True,
    },

    # 5. INDIAN FOOD PREFERENCES ──────────────────────────────────────────────
    "indian_food_preferences": {
        "staples": ["dal", "roti", "rice", "idli", "dosa", "poha", "upma", "khichdi"],
        "vegetables": ["palak", "methi", "lauki", "tinda", "karela", "bhindi", "brinjal"],
        "proteins": ["moong dal", "chana", "rajma", "paneer", "tofu", "curd", "eggs", "chicken"],
        "healthy_snacks": ["roasted chana", "makhana", "fruit chaat", "sprouts", "dhokla"],
        "spices_with_benefits": ["turmeric", "cumin", "fenugreek", "coriander", "ginger", "garlic"],
        "regional_cuisines": ["South Indian", "North Indian", "Gujarati", "Bengali", "Rajasthani"],
        "festivals_fasting_foods": ["sabudana khichdi", "kuttu roti", "singhara atta", "fruits"],
        "avoid_junk": ["maida-heavy items", "deep-fried snacks", "sugary drinks", "packaged foods"],
    },

    # 6. FAMILY SUPPORT ───────────────────────────────────────────────────────
    "family_support": {
        "profiles_supported": ["child (2–12)", "teenager (13–19)", "adult (20–59)", "senior (60+)"],
        "approach": (
            "Generate a combined family meal plan that respects each member's age, "
            "health conditions, and calorie needs. Highlight modifications per member "
            "using clear labels like [Child], [Senior], [Diabetic]."
        ),
        "shared_meals": True,          # suggest meals the whole family can enjoy
        "individual_portions": True,   # show per-member portion adjustments
    },
}
# ──────────────────────────────────────────────────────────────────────────────
# END OF AGENT INSTRUCTIONS
# ──────────────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
# NUTRITION MEMORY  — session-backed adaptive memory
#
# Automatically learns from every conversation turn:
#   • dislikes       – foods the user explicitly does not want
#   • favourites     – foods the user loves or requests often
#   • allergies      – foods/ingredients that cause allergic reactions
#   • conditions     – health conditions mentioned by the user
#   • meal_plan_log  – summaries of previously generated meal plans
#
# All data lives in Flask session (server-side).  Nothing is written to disk.
# ──────────────────────────────────────────────────────────────────────────────

SESSION_MEMORY_KEY = "nutrition_memory"

# Maximum items kept per list (prevents session bloat)
_MEM_MAX_ITEMS  = 30
_MEM_MAX_PLANS  = 5   # keep last N meal plan summaries


class NutritionMemory:
    """
    Thin wrapper around the Flask session that stores and retrieves all
    adaptive nutrition memory for the current user.

    Usage
    -----
    mem = NutritionMemory.load()      # read from session
    mem.add_dislike("broccoli")
    mem.add_favourite("paneer")
    mem.save()                        # write back to session
    """

    _EMPTY: dict = {
        "dislikes":    [],   # list[str]
        "favourites":  [],   # list[str]
        "allergies":   [],   # list[str]
        "conditions":  [],   # list[str]
        "meal_plan_log": [], # list[{"date": str, "summary": str, "days": int, "diet": str}]
    }

    def __init__(self, data: dict):
        self._data = data

    # ── factory ──────────────────────────────────────────────────────────────

    @classmethod
    def load(cls) -> "NutritionMemory":
        """Load from the active Flask session, initialising if absent."""
        raw = session.get(SESSION_MEMORY_KEY)
        if not isinstance(raw, dict):
            raw = {}
        # Merge with _EMPTY to ensure all keys exist even after schema changes
        data = {k: list(raw.get(k, [])) for k in cls._EMPTY}
        return cls(data)

    def save(self) -> None:
        """Persist current state back into the Flask session."""
        session[SESSION_MEMORY_KEY] = self._data
        session.modified = True

    # ── mutators ─────────────────────────────────────────────────────────────

    def _add_unique(self, key: str, value: str, maxlen: int = _MEM_MAX_ITEMS) -> bool:
        """Add *value* to list *key* (case-insensitive dedup). Returns True if added."""
        value = value.strip().lower()
        if not value or value in [x.lower() for x in self._data[key]]:
            return False
        self._data[key].append(value)
        self._data[key] = self._data[key][-maxlen:]
        return True

    def add_dislike(self, food: str)    -> bool: return self._add_unique("dislikes",   food)
    def add_favourite(self, food: str)  -> bool: return self._add_unique("favourites", food)
    def add_allergy(self, item: str)    -> bool: return self._add_unique("allergies",  item)
    def add_condition(self, cond: str)  -> bool: return self._add_unique("conditions", cond)

    def remove_dislike(self, food: str) -> None:
        self._data["dislikes"] = [x for x in self._data["dislikes"] if x.lower() != food.strip().lower()]

    def remove_favourite(self, food: str) -> None:
        self._data["favourites"] = [x for x in self._data["favourites"] if x.lower() != food.strip().lower()]

    def log_meal_plan(self, summary: str, days: int, diet: str) -> None:
        entry = {
            "date":    datetime.now().strftime("%Y-%m-%d %H:%M"),
            "summary": summary[:400],   # truncate long plans
            "days":    days,
            "diet":    diet,
        }
        self._data["meal_plan_log"].append(entry)
        self._data["meal_plan_log"] = self._data["meal_plan_log"][-_MEM_MAX_PLANS:]

    # ── accessors ─────────────────────────────────────────────────────────────

    @property
    def dislikes(self)    -> list: return list(self._data["dislikes"])
    @property
    def favourites(self)  -> list: return list(self._data["favourites"])
    @property
    def allergies(self)   -> list: return list(self._data["allergies"])
    @property
    def conditions(self)  -> list: return list(self._data["conditions"])
    @property
    def meal_plan_log(self) -> list: return list(self._data["meal_plan_log"])

    def to_dict(self) -> dict:
        return dict(self._data)

    def is_empty(self) -> bool:
        return not any(self._data[k] for k in self._EMPTY)

    # ── prompt block ──────────────────────────────────────────────────────────

    def as_prompt_block(self) -> str:
        """Return a formatted text block suitable for injection into the system prompt."""
        if self.is_empty():
            return ""

        lines = ["\nADAPTIVE NUTRITION MEMORY (MANDATORY — follow strictly)",
                 "-" * 56]

        if self.dislikes:
            lines.append("NEVER include these foods (user dislikes):")
            lines.extend(f"  ✗ {item}" for item in self.dislikes)

        if self.allergies:
            lines.append("NEVER include these ingredients (user allergies):")
            lines.extend(f"  ⚠ {item}" for item in self.allergies)

        if self.favourites:
            lines.append("PREFER these foods whenever possible (user favourites):")
            lines.extend(f"  ✓ {item}" for item in self.favourites)

        if self.conditions:
            lines.append("Tailor all advice to these health conditions:")
            lines.extend(f"  🩺 {cond}" for cond in self.conditions)

        if self.meal_plan_log:
            lines.append("Previous meal plans (avoid repetition, build on variety):")
            for p in self.meal_plan_log[-3:]:   # show last 3
                lines.append(f"  [{p['date']}] {p['days']}-day {p['diet']} plan — {p['summary'][:120]}")

        lines.append("-" * 56)
        lines.append("When recommending alternatives explain WHY they are healthier.")
        return "\n".join(lines)


import os
import io
import base64
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv

# ── Load environment variables ────────────────────────────────────────────────
load_dotenv()

# ── Flask app setup ───────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Watsonx.ai credentials ────────────────────────────────────────────────────
IBM_API_KEY       = os.getenv("IBM_API_KEY", "")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "")
WATSONX_URL       = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
WATSONX_MODEL_ID  = os.getenv("WATSONX_MODEL_ID", "ibm/granite-3-3-8b-instruct")

# ── Watsonx client (lazy-initialised) ────────────────────────────────────────
# _watsonx_client   — holds the live ModelInference object after a successful init
# _watsonx_init_failed — set to True after the first failed attempt so we never
#                        retry on every request (avoids log spam and latency)
_watsonx_client      = None
_watsonx_init_failed = False


def get_watsonx_client():
    """Return a cached Watsonx ModelInference client, initialising on first call.

    Returns None (and activates mock-response mode) when:
      - credentials are missing from the environment, OR
      - the project ID does not exist (404 from IBM), OR
      - any other initialisation error occurs.

    After the first failure the function returns None immediately on every
    subsequent call — it does NOT retry, preventing log spam.
    """
    global _watsonx_client, _watsonx_init_failed

    # Already initialised successfully
    if _watsonx_client is not None:
        return _watsonx_client

    # Already tried and failed — do not retry
    if _watsonx_init_failed:
        return None

    if not IBM_API_KEY or not WATSONX_PROJECT_ID:
        logger.warning(
            "IBM_API_KEY or WATSONX_PROJECT_ID not set — running in mock/demo mode. "
            "Add your credentials to the .env file to enable full AI responses."
        )
        _watsonx_init_failed = True
        return None

    try:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference

        credentials = Credentials(url=WATSONX_URL, api_key=IBM_API_KEY)
        _watsonx_client = ModelInference(
            model_id=WATSONX_MODEL_ID,
            credentials=credentials,
            project_id=WATSONX_PROJECT_ID,
            params={
                "max_new_tokens": 1024,
                "temperature": 0.7,
                "top_p": 0.9,
                "repetition_penalty": 1.1,
            },
        )
        logger.info("Watsonx.ai client initialised with model: %s", WATSONX_MODEL_ID)
        return _watsonx_client

    except Exception as exc:
        _watsonx_init_failed = True
        err_str = str(exc)
        # Produce an actionable error message for the most common failure modes
        if "not_found" in err_str or "404" in err_str or "Cannot set Project or Space" in err_str:
            logger.error(
                "Watsonx project not found (WATSONX_PROJECT_ID=%s). "
                "The project may have been deleted or the ID is incorrect. "
                "Open https://dataplatform.cloud.ibm.com/projects and update "
                "WATSONX_PROJECT_ID in your .env file. Running in mock/demo mode.",
                WATSONX_PROJECT_ID,
            )
        elif "401" in err_str or "Unauthorized" in err_str or "invalid_client" in err_str:
            logger.error(
                "Watsonx authentication failed — IBM_API_KEY may be expired or invalid. "
                "Regenerate it at https://cloud.ibm.com/iam/apikeys and update your .env file. "
                "Running in mock/demo mode."
            )
        else:
            logger.error("Failed to initialise Watsonx client: %s — running in mock/demo mode.", exc)
        return None


# ── Smart Food Swap engine ────────────────────────────────────────────────────
#
# Two-tier system:
#   1. IBM Granite  — asked to reason about meals in the response and produce
#                     structured JSON swap recommendations.
#   2. _SWAP_DB     — static fallback covering the most common Indian foods,
#                     used when Granite is unavailable or returns invalid JSON.
#
# Each swap entry shape:
#   {
#     "original":    str,          # food to replace
#     "swap":        str,          # healthier alternative
#     "reasons":     list[str],    # 2-4 short reasons
#     "benefit_tag": str,          # one-word benefit label (e.g. "High Fibre")
#     "kcal_saved":  int | None,   # estimated kcal saved per serving (can be None)
#   }
# ──────────────────────────────────────────────────────────────────────────────

_SWAP_DB: dict[str, dict] = {
    # Grains & Carbs
    "white rice": {
        "swap": "Brown Rice",
        "reasons": ["Higher fibre (3× more)", "Lower glycaemic index", "Better for diabetes management", "Keeps you full longer"],
        "benefit_tag": "High Fibre",
        "kcal_saved": 10,
    },
    "maida": {
        "swap": "Whole Wheat Flour (Atta)",
        "reasons": ["More fibre and nutrients", "Lower GI prevents sugar spikes", "Better digestive health"],
        "benefit_tag": "Whole Grain",
        "kcal_saved": 5,
    },
    "white bread": {
        "swap": "Multigrain or Whole Wheat Bread",
        "reasons": ["Higher fibre content", "More micronutrients", "Slower energy release"],
        "benefit_tag": "Whole Grain",
        "kcal_saved": 20,
    },
    "pasta": {
        "swap": "Whole Wheat Pasta",
        "reasons": ["Higher fibre", "More protein", "Lower glycaemic response"],
        "benefit_tag": "Whole Grain",
        "kcal_saved": 15,
    },
    # Fats & Oils
    "butter": {
        "swap": "Ghee (in moderation) or Olive Oil",
        "reasons": ["Healthier fat profile", "Rich in butyrate (gut health)", "Anti-inflammatory properties"],
        "benefit_tag": "Heart Healthy",
        "kcal_saved": None,
    },
    "refined oil": {
        "swap": "Cold-Pressed Mustard or Coconut Oil",
        "reasons": ["No trans fats", "Better omega-3 to omega-6 ratio", "Higher smoke point"],
        "benefit_tag": "Heart Healthy",
        "kcal_saved": None,
    },
    # Dairy
    "full fat milk": {
        "swap": "Toned or Skimmed Milk",
        "reasons": ["Lower saturated fat", "Same calcium content", "Fewer calories per glass"],
        "benefit_tag": "Lower Fat",
        "kcal_saved": 60,
    },
    "cream": {
        "swap": "Low-Fat Curd (Greek Style)",
        "reasons": ["High protein content", "Probiotics for gut health", "Significantly fewer calories"],
        "benefit_tag": "High Protein",
        "kcal_saved": 150,
    },
    # Sweeteners
    "sugar": {
        "swap": "Jaggery (Gud) or Dates",
        "reasons": ["Contains iron and minerals", "Slightly lower GI than refined sugar", "Natural and unprocessed"],
        "benefit_tag": "Natural",
        "kcal_saved": 5,
    },
    # Proteins
    "red meat": {
        "swap": "Chicken Breast or Fish",
        "reasons": ["Lower saturated fat", "Higher lean protein ratio", "Better for heart health"],
        "benefit_tag": "Lean Protein",
        "kcal_saved": 80,
    },
    "deep fried": {
        "swap": "Air-Fried or Baked",
        "reasons": ["Up to 70% less fat", "No trans fats", "Same crunch with far fewer calories"],
        "benefit_tag": "Low Fat",
        "kcal_saved": 150,
    },
    "samosa": {
        "swap": "Baked Whole-Wheat Samosa",
        "reasons": ["No deep-frying fat", "More fibre from whole wheat", "Similar taste, much healthier"],
        "benefit_tag": "Low Fat",
        "kcal_saved": 120,
    },
    "chips": {
        "swap": "Roasted Makhana or Chana",
        "reasons": ["High protein", "Low glycaemic", "Rich in magnesium and calcium"],
        "benefit_tag": "High Protein",
        "kcal_saved": 100,
    },
    "cold drink": {
        "swap": "Nimbu Pani or Coconut Water",
        "reasons": ["Zero added sugar", "Natural electrolytes", "Hydrating and refreshing"],
        "benefit_tag": "Zero Sugar",
        "kcal_saved": 140,
    },
    "fruit juice": {
        "swap": "Whole Fruit",
        "reasons": ["Fibre preserved", "Lower sugar per serving", "More satiating and filling"],
        "benefit_tag": "High Fibre",
        "kcal_saved": 50,
    },
    # Indian specifics
    "poori": {
        "swap": "Phulka / Chapati",
        "reasons": ["Not deep-fried", "Much lower calorie count", "Better for weight management"],
        "benefit_tag": "Low Cal",
        "kcal_saved": 180,
    },
    "biryani": {
        "swap": "Vegetable Pulao with Brown Rice",
        "reasons": ["More fibre from brown rice", "Less oil and spice load", "Rich in vegetables and nutrients"],
        "benefit_tag": "Balanced",
        "kcal_saved": 120,
    },
    "paneer butter masala": {
        "swap": "Palak Paneer",
        "reasons": ["Spinach adds iron and vitamins A/C", "Lower saturated fat", "More micronutrients"],
        "benefit_tag": "Nutrient Dense",
        "kcal_saved": 80,
    },
    "white poha": {
        "swap": "Oats Poha or Millets Upma",
        "reasons": ["Higher fibre content", "Lower glycaemic index", "More minerals"],
        "benefit_tag": "Whole Grain",
        "kcal_saved": 30,
    },
}

# Keywords that indicate a response contains meal suggestions
_MEAL_KEYWORDS = [
    "breakfast", "lunch", "dinner", "snack", "meal plan", "recipe",
    "eat", "food", "roti", "dal", "rice", "sabzi", "curry", "idli",
    "dosa", "upma", "poha", "khichdi",
]


def _swaps_from_db(text: str) -> list[dict]:
    """Scan *text* for foods that appear in _SWAP_DB and return matching swap dicts."""
    t = text.lower()
    seen: set[str] = set()
    result: list[dict] = []
    for key, entry in _SWAP_DB.items():
        if key in t and key not in seen:
            seen.add(key)
            result.append({"original": key.title(), **entry})
    return result[:4]  # cap at 4 cards per response


def generate_food_swaps(ai_text: str, context: str = "") -> list[dict]:
    """
    Ask IBM Granite to identify unhealthy foods in *ai_text* and suggest swaps.
    Falls back to _SWAP_DB keyword scan if Granite is unavailable or returns
    invalid JSON.

    Returns a list of swap dicts (may be empty if no swaps found).
    """
    client = get_watsonx_client()
    if client is None:
        return _swaps_from_db(ai_text)

    swap_prompt = f"""You are a nutrition expert. Read the following meal suggestion text and identify up to 4 foods that have a healthier alternative.

Meal text:
\"\"\"{ai_text[:800]}\"\"\"

{f'User context: {context}' if context else ''}

Respond ONLY with a valid JSON array — no markdown, no extra text. If no unhealthy foods are found, return [].

Return exactly this structure for each swap (up to 4 items):
[
  {{
    "original":    "White Rice",
    "swap":        "Brown Rice",
    "reasons":     ["Higher fibre (3× more)", "Lower glycaemic index", "Better for diabetes"],
    "benefit_tag": "High Fibre",
    "kcal_saved":  10
  }}
]

Rules:
- Only suggest swaps for foods explicitly mentioned in the meal text.
- reasons must be a list of 2–4 short phrases (under 8 words each).
- benefit_tag must be 1–3 words (e.g. "High Fibre", "Low Fat", "Heart Healthy").
- kcal_saved is the estimated calories saved per serving (integer or null).
- If no meaningful swap exists for a food, skip it.
- Never suggest a swap for water, spices, or herbs.
"""
    try:
        raw = client.generate_text(prompt=swap_prompt) or "[]"
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        swaps = json.loads(raw)
        if not isinstance(swaps, list):
            raise ValueError("expected list")
        # Validate each entry has required keys
        validated: list[dict] = []
        for s in swaps:
            if isinstance(s, dict) and "original" in s and "swap" in s and "reasons" in s:
                validated.append({
                    "original":    str(s.get("original", "")),
                    "swap":        str(s.get("swap", "")),
                    "reasons":     [str(r) for r in s.get("reasons", [])[:4]],
                    "benefit_tag": str(s.get("benefit_tag", "Healthier")),
                    "kcal_saved":  int(s["kcal_saved"]) if s.get("kcal_saved") else None,
                })
        return validated[:4] if validated else _swaps_from_db(ai_text)
    except Exception as exc:
        logger.warning("Food swap Granite parse failed (%s) — using DB fallback.", exc)
        return _swaps_from_db(ai_text)


def _is_meal_response(text: str) -> bool:
    """Return True if *text* appears to contain a meal suggestion."""
    t = text.lower()
    return sum(1 for kw in _MEAL_KEYWORDS if kw in t) >= 2


# ── Memory extraction ─────────────────────────────────────────────────────────

# Keyword maps for fast rule-based extraction (used when Granite is unavailable)
_DISLIKE_TRIGGERS  = ["don't like", "dont like", "hate", "dislike", "not a fan of",
                      "avoid", "can't stand", "cannot stand", "never eat", "no more"]
_FAVOURITE_TRIGGERS = ["love", "favourite", "favorite", "enjoy", "like eating",
                       "prefer", "i always eat", "my go-to", "i enjoy"]
_ALLERGY_TRIGGERS  = ["allergic to", "allergy to", "intolerant to", "intolerance",
                      "makes me sick", "i react to", "cannot eat", "can't eat"]
_CONDITION_TRIGGERS = ["i have", "diagnosed with", "i am diabetic", "i'm diabetic",
                       "hypertension", "thyroid", "pcos", "pcod", "cholesterol",
                       "heart condition", "kidney", "anemia", "anaemia", "ibs",
                       "celiac", "coeliac", "fatty liver", "arthritis", "gout"]

# Foods / ingredients we watch for in rule-based extraction
_COMMON_FOODS = [
    "onion", "garlic", "mushroom", "brinjal", "eggplant", "bitter gourd", "karela",
    "okra", "bhindi", "spinach", "methi", "capsicum", "tomato", "potato", "carrot",
    "cauliflower", "cabbage", "peas", "corn", "lentils", "dal", "rajma", "chickpeas",
    "chana", "paneer", "tofu", "eggs", "chicken", "fish", "mutton", "beef", "pork",
    "milk", "curd", "yogurt", "ghee", "butter", "cream", "cheese", "rice", "roti",
    "bread", "pasta", "noodles", "oats", "millet", "bajra", "ragi", "wheat",
    "peanuts", "nuts", "cashew", "almond", "walnut", "sesame", "coconut",
    "sugar", "jaggery", "honey", "chocolate", "sweets", "fried food", "maida",
]


def _extract_memory_rule_based(text: str, mem: NutritionMemory) -> list[str]:
    """
    Fast rule-based fallback for memory extraction when Granite is offline.
    Returns a list of human-readable strings describing what was learned.
    """
    t = text.lower()
    learned: list[str] = []

    # Allergies (check first — highest priority)
    for trigger in _ALLERGY_TRIGGERS:
        if trigger in t:
            for food in _COMMON_FOODS:
                if food in t:
                    if mem.add_allergy(food):
                        learned.append(f"allergy noted: {food}")

    # Dislikes
    for trigger in _DISLIKE_TRIGGERS:
        if trigger in t:
            for food in _COMMON_FOODS:
                if food in t:
                    if mem.add_dislike(food):
                        learned.append(f"dislike noted: {food}")

    # Favourites
    for trigger in _FAVOURITE_TRIGGERS:
        if trigger in t:
            for food in _COMMON_FOODS:
                if food in t:
                    if mem.add_favourite(food):
                        learned.append(f"favourite noted: {food}")

    # Health conditions
    for trigger in _CONDITION_TRIGGERS:
        if trigger in t:
            condition = trigger.replace("i have", "").replace("i am", "").replace("i'm", "").strip()
            if condition:
                if mem.add_condition(condition):
                    learned.append(f"condition noted: {condition}")

    return learned


def _extract_memory_with_granite(text: str, mem: NutritionMemory, client) -> list[str]:
    """
    Use IBM Granite to extract food preferences and health signals from a
    free-form user message.  Falls back to rule-based if parsing fails.
    """
    extraction_prompt = f"""You are a nutrition data extractor. Analyse this user message and extract food preferences.
Respond ONLY with a valid JSON object — no markdown, no extra text.

User message: "{text}"

Return exactly this JSON (use empty lists if nothing is found):
{{
  "dislikes":   ["<food1>", "<food2>"],
  "favourites": ["<food1>", "<food2>"],
  "allergies":  ["<ingredient1>"],
  "conditions": ["<health condition1>"]
}}

Rules:
- Only extract items explicitly mentioned.
- Keep food names short (e.g. "broccoli", not "I don't like broccoli").
- For conditions include: diabetes, hypertension, PCOS, thyroid, cholesterol, IBS, etc.
- Return empty lists if no relevant information is found.
"""
    try:
        raw = client.generate_text(prompt=extraction_prompt) or "{}"
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        extracted = json.loads(raw)
    except Exception:
        return _extract_memory_rule_based(text, mem)

    learned: list[str] = []
    for food in extracted.get("dislikes", []):
        if isinstance(food, str) and mem.add_dislike(food):
            learned.append(f"dislike noted: {food}")
    for food in extracted.get("favourites", []):
        if isinstance(food, str) and mem.add_favourite(food):
            learned.append(f"favourite noted: {food}")
    for item in extracted.get("allergies", []):
        if isinstance(item, str) and mem.add_allergy(item):
            learned.append(f"allergy noted: {item}")
    for cond in extracted.get("conditions", []):
        if isinstance(cond, str) and mem.add_condition(cond):
            learned.append(f"condition noted: {cond}")
    return learned


def extract_and_update_memory(user_message: str, mem: NutritionMemory) -> list[str]:
    """
    Public entry point.  Chooses Granite extraction when available,
    rule-based otherwise.  Returns list of learned signals (for debug logging).
    """
    client = get_watsonx_client()
    if client is not None:
        return _extract_memory_with_granite(user_message, mem, client)
    return _extract_memory_rule_based(user_message, mem)


# ── Adaptive feedback ─────────────────────────────────────────────────────────

SESSION_FEEDBACK_KEY = "user_feedback"
_FEEDBACK_MAX        = 20   # cap stored entries to prevent session bloat


def _feedback_prompt_block() -> str:
    """Return a prompt block from session feedback, or empty string if none."""
    try:
        from flask import session as _session
        entries = _session.get(SESSION_FEEDBACK_KEY) or []
    except RuntimeError:
        # Outside request context (e.g. tests) — skip silently
        return ""
    if not entries:
        return ""
    lines = ["\n\nUser feedback (apply these preferences to every recommendation):", "-" * 56]
    for e in entries[-10:]:   # last 10 only
        note = (e.get("feedback") or "").strip()
        if note:
            lines.append(f"  - {note}")
    if len(lines) == 2:       # only the header, no actionable notes
        return ""
    lines.append("-" * 56)
    lines.append("Generate recommendations considering these preferences.")
    return "\n".join(lines)


# ── System prompt builder ─────────────────────────────────────────────────────

def build_system_prompt(user_profile: dict | None = None,
                        memory: "NutritionMemory | None" = None) -> str:
    """Assemble the full system prompt from AGENT_INSTRUCTIONS + optional user profile + memory."""
    ai = AGENT_INSTRUCTIONS
    persona = ai["persona"]
    safety  = "\n".join(f"  • {r}" for r in ai["safety_rules"])
    diets   = "\n".join(f"  • {d}" for d in ai["diet_specializations"])
    indian  = ai["indian_food_preferences"]
    family  = ai["family_support"]
    style   = ai["response_style"]

    profile_block = ""
    if user_profile:
        profile_block = f"""
USER PROFILE
------------
Name        : {user_profile.get('name', 'User')}
Age         : {user_profile.get('age', 'unknown')}
Gender      : {user_profile.get('gender', 'unknown')}
Weight      : {user_profile.get('weight', 'unknown')} kg
Height      : {user_profile.get('height', 'unknown')} cm
Goal        : {user_profile.get('goal', 'healthy eating')}
Activity    : {user_profile.get('activity', 'moderate')}
Allergies   : {user_profile.get('allergies', 'none')}
Conditions  : {user_profile.get('conditions', 'none')}
Diet Type   : {user_profile.get('diet_type', 'balanced')}
"""

    memory_block = memory.as_prompt_block() if memory else ""

    return f"""You are {persona['name']}, {persona['role']}.
Tone: {persona['tone']}.

SPECIALIZATIONS
---------------
{diets}

RESPONSE STYLE
--------------
  • Language         : {style['language']}
  • Length           : {style['max_response_length']}
  • Use bullet points: {style['use_bullet_points']}
  • Include calories : {style['include_calorie_estimates']}
  • Include portions : {style['include_portion_sizes']}
  • Encouraging tone : {style['use_encouraging_language']}

INDIAN FOOD KNOWLEDGE
---------------------
  Staples   : {', '.join(indian['staples'])}
  Vegetables: {', '.join(indian['vegetables'])}
  Proteins  : {', '.join(indian['proteins'])}
  Snacks    : {', '.join(indian['healthy_snacks'])}
  Key Spices: {', '.join(indian['spices_with_benefits'])}
  Cuisines  : {', '.join(indian['regional_cuisines'])}

FAMILY PLAN APPROACH
--------------------
  {family['approach']}
  Shared meals      : {family['shared_meals']}
  Individual portions: {family['individual_portions']}

SAFETY RULES (MANDATORY)
-------------------------
{safety}
{profile_block}{memory_block}{_feedback_prompt_block()}
Always respond helpfully, accurately, and safely. End responses with a brief motivational note. 🌟"""


# ── AI response generator ─────────────────────────────────────────────────────

def generate_ai_response(user_message: str, conversation_history: list,
                         user_profile: dict | None = None,
                         memory: "NutritionMemory | None" = None) -> str:
    """Send the conversation to Watsonx.ai and return the assistant reply."""
    client = get_watsonx_client()

    system_prompt = build_system_prompt(user_profile, memory)

    # Build conversation context (last 12 turns to stay within token budget)
    context_turns = conversation_history[-12:] if len(conversation_history) > 12 else conversation_history
    context = "\n".join(
        f"{'User' if m['role'] == 'user' else 'NutriBot'}: {m['content']}"
        for m in context_turns
    )

    full_prompt = f"""{system_prompt}

CONVERSATION HISTORY
--------------------
{context}

User: {user_message}
NutriBot:"""

    if client is None:
        return _mock_response(user_message)

    try:
        response = client.generate_text(prompt=full_prompt)
        return response.strip() if response else "I'm here to help! Could you rephrase your question?"
    except Exception as exc:
        logger.error("Watsonx generation error: %s", exc)
        return f"I encountered a temporary issue connecting to the AI service. Please try again in a moment. (Error: {exc})"


def _mock_response(message: str) -> str:
    """Return a helpful mock response when Watsonx credentials are not configured."""
    msg_lower = message.lower()
    if any(w in msg_lower for w in ["meal plan", "diet plan", "weekly plan"]):
        return (
            "**Sample 7-Day Indian Meal Plan** 🥗\n\n"
            "**Day 1**\n"
            "• Breakfast: Oats poha with veggies (~280 kcal)\n"
            "• Lunch: Dal + roti + sabzi + curd (~550 kcal)\n"
            "• Snack: Roasted chana + green tea (~120 kcal)\n"
            "• Dinner: Khichdi + raita (~400 kcal)\n\n"
            "**Tip**: Stay hydrated — aim for 8–10 glasses of water daily! 💧\n\n"
            "🌟 *Note: This is a demo response. Add your IBM API key for personalised AI-powered plans!*"
        )
    if any(w in msg_lower for w in ["bmi", "weight"]):
        return (
            "**BMI Guidelines** 📊\n\n"
            "• < 18.5 — Underweight\n"
            "• 18.5–24.9 — Normal weight ✅\n"
            "• 25–29.9 — Overweight\n"
            "• ≥ 30 — Obese\n\n"
            "Use the BMI calculator on the right to check yours!\n\n"
            "🌟 *Note: This is a demo response. Configure your IBM API key for full AI support!*"
        )
    if any(w in msg_lower for w in ["calori", "calorie", "kcal"]):
        return (
            "**Calorie Estimates for Common Indian Foods** 🍽️\n\n"
            "• 1 medium roti (~6-inch): ~70 kcal\n"
            "• 1 cup cooked dal: ~150 kcal\n"
            "• 1 cup cooked rice: ~200 kcal\n"
            "• 1 bowl sabzi (mixed veg): ~100–150 kcal\n"
            "• 1 cup curd (plain): ~60 kcal\n"
            "• 100g paneer: ~265 kcal\n\n"
            "🌟 *Add your IBM API key for personalised calorie tracking and AI meal recommendations!*"
        )
    return (
        "Hello! I'm **NutriBot** 🥗, your AI nutrition coach.\n\n"
        "I can help you with:\n"
        "• 🍽️ Personalised meal plans\n"
        "• 📊 Calorie analysis\n"
        "• 💪 Weight management tips\n"
        "• 👨‍👩‍👧‍👦 Family diet recommendations\n"
        "• 🥘 Indian food & recipe suggestions\n\n"
        "**To unlock full AI capabilities**, add your IBM Watsonx.ai credentials to the `.env` file.\n\n"
        "🌟 *Stay consistent — small healthy choices add up to big results!*"
    )


# ── Nutrition calculation helpers ─────────────────────────────────────────────

def calculate_bmi(weight_kg: float, height_cm: float) -> dict:
    if height_cm <= 0:
        return {"error": "Invalid height"}
    height_m = height_cm / 100
    bmi = round(weight_kg / (height_m ** 2), 1)
    if bmi < 18.5:
        category, advice = "Underweight", "Focus on nutrient-dense foods to gain healthy weight."
    elif bmi < 25:
        category, advice = "Normal weight", "Great job! Maintain your balanced diet and active lifestyle."
    elif bmi < 30:
        category, advice = "Overweight", "Consider a calorie-deficit diet with regular exercise."
    else:
        category, advice = "Obese", "Please consult a healthcare professional for a personalised plan."
    return {"bmi": bmi, "category": category, "advice": advice}


def calculate_tdee(weight_kg: float, height_cm: float, age: int, gender: str, activity: str) -> dict:
    """Calculate Total Daily Energy Expenditure using Mifflin-St Jeor equation."""
    if gender.lower() in ("male", "m"):
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    activity_map = {
        "sedentary": 1.2, "light": 1.375, "moderate": 1.55,
        "active": 1.725, "very_active": 1.9,
    }
    multiplier = activity_map.get(activity.lower(), 1.55)
    tdee = round(bmr * multiplier)

    return {
        "bmr": round(bmr),
        "tdee": tdee,
        "weight_loss": tdee - 500,
        "weight_gain": tdee + 500,
        "maintenance": tdee,
    }


def get_macro_split(goal: str, tdee: int) -> dict:
    """Return recommended macro-nutrient grams for a given goal and TDEE."""
    splits = {
        "weight_loss":    {"carbs": 0.40, "protein": 0.35, "fat": 0.25},
        "weight_gain":    {"carbs": 0.50, "protein": 0.25, "fat": 0.25},
        "muscle_building":{"carbs": 0.45, "protein": 0.35, "fat": 0.20},
        "maintenance":    {"carbs": 0.50, "protein": 0.25, "fat": 0.25},
    }
    s = splits.get(goal, splits["maintenance"])
    return {
        "carbs_g":   round((tdee * s["carbs"]) / 4),
        "protein_g": round((tdee * s["protein"]) / 4),
        "fat_g":     round((tdee * s["fat"]) / 9),
        "calories":  tdee,
    }


# ── Flask routes ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html",
                           agent_name=AGENT_INSTRUCTIONS["persona"]["name"],
                           greeting=AGENT_INSTRUCTIONS["persona"]["greeting"])


@app.route("/api/chat", methods=["POST"])
def chat():
    """Main chat endpoint — receives user message, returns AI response."""
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    # Retrieve or initialise conversation history in session
    if "conversation" not in session:
        session["conversation"] = []

    conversation = session["conversation"]
    user_profile = session.get("user_profile")

    # ── Memory: extract signals from this message then inject into prompt ──
    mem = NutritionMemory.load()
    learned = extract_and_update_memory(user_message, mem)
    if learned:
        logger.info("Memory updated — %s", "; ".join(learned))
    mem.save()

    # Append user turn
    conversation.append({"role": "user", "content": user_message, "timestamp": datetime.now().isoformat()})

    # Generate AI response (memory-aware)
    ai_reply = generate_ai_response(user_message, conversation, user_profile, mem)

    # ── Smart Food Swaps: generate only when the reply contains meal content ──
    swaps: list[dict] = []
    if _is_meal_response(ai_reply):
        goal_ctx = (session.get("user_profile") or {}).get("goal", "")
        swaps = generate_food_swaps(ai_reply, context=goal_ctx)

    # Append assistant turn
    conversation.append({"role": "assistant", "content": ai_reply, "timestamp": datetime.now().isoformat()})

    # Persist (cap at 50 messages to avoid session bloat)
    session["conversation"] = conversation[-50:]
    session.modified = True

    return jsonify({
        "response": ai_reply,
        "timestamp": datetime.now().strftime("%H:%M"),
        "model": WATSONX_MODEL_ID,
        "memory_learned": learned,
        "swaps": swaps,             # empty list when no meal content detected
        "show_feedback": _is_meal_response(ai_reply),  # flag for feedback buttons
    })


@app.route("/api/profile", methods=["POST"])
def save_profile():
    """Save or update a user / family member profile."""
    data = request.get_json(silent=True) or {}
    profiles = session.get("family_profiles", {})
    member_id = data.get("id", "primary")
    profiles[member_id] = {
        "id":         member_id,
        "name":       data.get("name", "User"),
        "age":        data.get("age", 25),
        "gender":     data.get("gender", "male"),
        "weight":     data.get("weight", 70),
        "height":     data.get("height", 170),
        "goal":       data.get("goal", "maintenance"),
        "activity":   data.get("activity", "moderate"),
        "allergies":  data.get("allergies", "none"),
        "conditions": data.get("conditions", "none"),
        "diet_type":  data.get("diet_type", "balanced"),
    }
    session["family_profiles"] = profiles
    # Set primary profile as active
    if member_id == "primary":
        session["user_profile"] = profiles[member_id]
    session.modified = True
    return jsonify({"success": True, "profile": profiles[member_id]})


@app.route("/api/profile", methods=["GET"])
def get_profiles():
    profiles = session.get("family_profiles", {})
    return jsonify({"profiles": list(profiles.values())})


@app.route("/api/bmi", methods=["POST"])
def bmi_endpoint():
    data = request.get_json(silent=True) or {}
    try:
        weight = float(data["weight"])
        height = float(data["height"])
    except (KeyError, ValueError):
        return jsonify({"error": "Provide weight (kg) and height (cm)"}), 400
    return jsonify(calculate_bmi(weight, height))


@app.route("/api/tdee", methods=["POST"])
def tdee_endpoint():
    data = request.get_json(silent=True) or {}
    try:
        result = calculate_tdee(
            float(data["weight"]),
            float(data["height"]),
            int(data["age"]),
            str(data.get("gender", "male")),
            str(data.get("activity", "moderate")),
        )
        goal = data.get("goal", "maintenance")
        result["macros"] = get_macro_split(goal, result["tdee"])
        return jsonify(result)
    except (KeyError, ValueError) as exc:
        return jsonify({"error": f"Invalid input: {exc}"}), 400


@app.route("/api/meal-plan", methods=["POST"])
def meal_plan():
    """Generate a memory-aware meal plan via IBM Granite."""
    data = request.get_json(silent=True) or {}
    user_profile = session.get("user_profile") or data

    days        = data.get("days", 7)
    preferences = data.get("preferences", "balanced Indian vegetarian")
    goal        = data.get("goal", user_profile.get("goal", "maintenance"))

    # Load memory and build explicit constraint lines for the prompt
    mem = NutritionMemory.load()

    never_lines = ""
    if mem.dislikes:
        never_lines += f"\nNEVER include (dislikes): {', '.join(mem.dislikes)}."
    if mem.allergies:
        never_lines += f"\nSTRICTLY AVOID (allergies): {', '.join(mem.allergies)}."

    prefer_lines = ""
    if mem.favourites:
        prefer_lines = f"\nPREFER these foods whenever suitable: {', '.join(mem.favourites)}."

    condition_lines = ""
    all_conditions = list(mem.conditions)
    if user_profile.get("conditions") and user_profile["conditions"] != "none":
        all_conditions.append(user_profile["conditions"])
    if all_conditions:
        condition_lines = f"\nTailor the plan for these health conditions: {', '.join(all_conditions)}."

    variety_hint = ""
    if mem.meal_plan_log:
        prev = mem.meal_plan_log[-1]
        variety_hint = (
            f"\nThe last plan ({prev['date']}) was a {prev['days']}-day {prev['diet']} plan. "
            "Ensure variety — avoid repeating the same meals."
        )

    prompt = (
        f"Create a {days}-day meal plan for the following profile:\n"
        f"Name: {user_profile.get('name', 'User')}, "
        f"Age: {user_profile.get('age', 25)}, "
        f"Goal: {goal}, "
        f"Diet: {user_profile.get('diet_type', preferences)}, "
        f"Allergies: {user_profile.get('allergies', 'none')}."
        f"{never_lines}{prefer_lines}{condition_lines}{variety_hint}\n"
        "Include breakfast, lunch, snack, and dinner for each day with calorie estimates. "
        "Focus on Indian foods and practical, easy-to-cook meals. "
        "For each meal that uses a favourite food, note it with ✓. "
        "When a healthier alternative is suggested, briefly explain why it is better."
    )

    conversation = [{"role": "user", "content": prompt}]
    reply = generate_ai_response(prompt, conversation, user_profile, mem)

    # ── Smart Food Swaps for meal plan ────────────────────────────────────────
    swap_context = f"{goal} diet, {preferences}"
    swaps = generate_food_swaps(reply, context=swap_context)

    # Log this plan in memory for future variety tracking
    summary = reply[:300].replace("\n", " ")
    mem.log_meal_plan(summary, days, preferences)
    mem.save()

    return jsonify({"meal_plan": reply, "swaps": swaps})


@app.route("/api/food-swaps", methods=["POST"])
def food_swaps_endpoint():
    """
    Standalone endpoint — generate smart food swaps for any given text.

    POST body (JSON):
    {
        "text":    "I usually eat white rice and poori for lunch",
        "context": "weight loss"   // optional
    }
    """
    data    = request.get_json(silent=True) or {}
    text    = (data.get("text") or "").strip()
    context = (data.get("context") or "").strip()
    if not text:
        return jsonify({"error": "Provide a 'text' field"}), 400
    swaps = generate_food_swaps(text, context=context)
    return jsonify({"swaps": swaps})


@app.route("/api/nutrition-tips", methods=["GET"])
def nutrition_tips():
    """Return a set of static nutrition tips (no AI call needed)."""
    tips = [
        {"icon": "🥗", "title": "Eat the Rainbow", "tip": "Include vegetables of 5+ colours daily for diverse micronutrients."},
        {"icon": "💧", "title": "Hydration First", "tip": "Drink 8–10 glasses of water per day; more on active days."},
        {"icon": "⏰", "title": "Meal Timing", "tip": "Eat every 3–4 hours to keep metabolism steady and energy stable."},
        {"icon": "🫘", "title": "Protein at Every Meal", "tip": "Include dal, paneer, curd, eggs, or legumes to stay full longer."},
        {"icon": "🌾", "title": "Whole Grains", "tip": "Replace maida with whole wheat, millets (ragi, bajra) or oats."},
        {"icon": "🍬", "title": "Limit Added Sugar", "tip": "Cut down on sugary drinks and sweets; opt for jaggery in moderation."},
        {"icon": "🧘", "title": "Mindful Eating", "tip": "Eat slowly without screen distractions to prevent overeating."},
        {"icon": "🥜", "title": "Healthy Fats", "tip": "Include a handful of nuts and seeds — almonds, walnuts, flaxseeds daily."},
    ]
    return jsonify({"tips": tips})


# ── Food image analysis ───────────────────────────────────────────────────────

# Allowed upload extensions
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
# Max upload size: 5 MB
MAX_IMAGE_BYTES = 5 * 1024 * 1024

# ── Realistic nutrition database ──────────────────────────────────────────────
# Values are per standard serving size listed alongside each entry.
# healthier_alternatives:
#   - For healthy whole foods  → complementary pairings
#   - For processed / fried    → healthier substitutes with explanations
_NUTRITION_DB: dict[str, dict] = {
    # ── Fruits ────────────────────────────────────────────────────────────
    "apple": {
        "serving_size": "1 medium (182g)", "calories": 95,
        "protein_g": 0.5, "carbs_g": 25.0, "fat_g": 0.3, "fibre_g": 4.4,
        "health_score": 9, "weight_loss_suitable": True, "diabetic_friendly": True,
        "weight_loss_reason": "Low in calories, high in fibre — keeps you full with minimal calorie cost.",
        "diabetic_reason": "Low GI fruit; fibre slows glucose absorption and helps manage blood sugar.",
        "is_healthy": True,
        "healthier_alternatives": [
            {"name": "Apple + Peanut Butter", "reason": "Adds healthy fats and protein for a more balanced, satiating snack."},
            {"name": "Apple + Greek Yogurt", "reason": "Combining fibre-rich apple with protein-packed yogurt stabilises blood sugar and boosts fullness."},
        ],
        "ai_explanation": "Apples are rich in quercetin, catechin, and chlorogenic acid — powerful antioxidants linked to reduced risk of heart disease and type 2 diabetes. The soluble fibre pectin feeds beneficial gut bacteria.",
        "tips": "Eat the skin — it contains up to 50% of the apple's fibre and most of its antioxidants.",
    },
    "banana": {
        "serving_size": "1 medium (118g)", "calories": 105,
        "protein_g": 1.3, "carbs_g": 27.0, "fat_g": 0.4, "fibre_g": 3.1,
        "health_score": 8, "weight_loss_suitable": True, "diabetic_friendly": True,
        "weight_loss_reason": "Natural sugars with fibre provide sustained energy without a heavy calorie load.",
        "diabetic_reason": "Unripe bananas have a lower GI; pair with protein to further blunt glucose response.",
        "is_healthy": True,
        "healthier_alternatives": [
            {"name": "Banana + Almond Butter", "reason": "Healthy fats from almond butter slow sugar absorption and extend satiety."},
            {"name": "Banana + Oats Smoothie", "reason": "Combining banana with oats adds beta-glucan fibre for long-lasting energy."},
        ],
        "ai_explanation": "Bananas are an excellent source of potassium and vitamin B6. They contain resistant starch (especially when unripe) that acts as prebiotic fibre, supporting gut health.",
        "tips": "Slightly unripe bananas have a lower glycaemic index — a good choice for diabetics and those watching blood sugar.",
    },
    "orange": {
        "serving_size": "1 medium (131g)", "calories": 62,
        "protein_g": 1.2, "carbs_g": 15.4, "fat_g": 0.2, "fibre_g": 3.1,
        "health_score": 9, "weight_loss_suitable": True, "diabetic_friendly": True,
        "weight_loss_reason": "Very low calorie density with high water content and fibre for excellent satiety.",
        "diabetic_reason": "Moderate GI with fibre; vitamin C and flavonoids support insulin sensitivity.",
        "is_healthy": True,
        "healthier_alternatives": [
            {"name": "Orange + Cottage Cheese", "reason": "Protein from cottage cheese pairs with vitamin C to boost iron absorption and satiety."},
            {"name": "Orange + Mixed Nuts", "reason": "Healthy fats from nuts slow sugar absorption and provide complementary micronutrients."},
        ],
        "ai_explanation": "Oranges are powerhouses of vitamin C (70mg per fruit), folate, and hesperidin — a flavonoid that supports heart health and reduces inflammation.",
        "tips": "Eat the whole fruit rather than juicing — you keep all the fibre and avoid concentrated sugar.",
    },
    "mango": {
        "serving_size": "1 cup sliced (165g)", "calories": 99,
        "protein_g": 1.4, "carbs_g": 25.0, "fat_g": 0.6, "fibre_g": 2.6,
        "health_score": 7, "weight_loss_suitable": True, "diabetic_friendly": False,
        "weight_loss_reason": "Moderate calories with vitamins A and C; portion control is key.",
        "diabetic_reason": "Higher natural sugar content — moderate portions and pairing with protein is advised.",
        "is_healthy": True,
        "healthier_alternatives": [
            {"name": "Mango + Greek Yogurt Parfait", "reason": "Yogurt's protein slows mango's sugar absorption, creating a balanced snack."},
            {"name": "Mango + Chia Seeds", "reason": "Chia seeds add omega-3s and fibre that offset mango's glycaemic impact."},
        ],
        "ai_explanation": "Mangoes are rich in beta-carotene, vitamin C, and folate. They contain amylase enzymes that aid digestion, and their polyphenols may support gut microbiome diversity.",
        "tips": "Enjoy mango as part of a meal with protein to prevent blood sugar spikes.",
    },
    # ── Vegetables ────────────────────────────────────────────────────────
    "salad": {
        "serving_size": "2 cups mixed greens (100g)", "calories": 20,
        "protein_g": 1.5, "carbs_g": 3.5, "fat_g": 0.3, "fibre_g": 2.0,
        "health_score": 10, "weight_loss_suitable": True, "diabetic_friendly": True,
        "weight_loss_reason": "Extremely low calorie density with high volume; excellent for weight management.",
        "diabetic_reason": "Non-starchy vegetables have negligible impact on blood sugar and are highly recommended.",
        "is_healthy": True,
        "healthier_alternatives": [
            {"name": "Salad + Grilled Chicken", "reason": "Adding lean protein transforms the salad into a complete, muscle-supporting meal."},
            {"name": "Salad + Chickpeas & Olive Oil", "reason": "Legumes add protein and fibre; olive oil provides heart-healthy monounsaturated fats."},
        ],
        "ai_explanation": "Mixed greens are exceptionally nutrient-dense — high in vitamins K, A, C, folate, and antioxidants while being virtually calorie-free. Regular salad consumption is associated with reduced cardiovascular disease risk.",
        "tips": "Use a dressing with olive oil to boost absorption of fat-soluble vitamins A, D, E, and K from the greens.",
    },
    # ── Grains & Breads ───────────────────────────────────────────────────
    "white bread": {
        "serving_size": "2 slices (56g)", "calories": 160,
        "protein_g": 6.0, "carbs_g": 30.0, "fat_g": 2.0, "fibre_g": 2.0,
        "health_score": 4, "weight_loss_suitable": False, "diabetic_friendly": False,
        "weight_loss_reason": "Refined flour has a high GI causing rapid sugar spikes and rebound hunger.",
        "diabetic_reason": "Rapidly digested refined starch elevates blood glucose quickly — not recommended for diabetics.",
        "is_healthy": False,
        "healthier_alternatives": [
            {"name": "Whole Wheat Bread", "reason": "Contains the entire wheat grain — more fibre (3×), B vitamins, iron, and a lower GI that prevents blood sugar spikes."},
            {"name": "Multigrain Bread", "reason": "Multiple grains provide diverse fibre, antioxidants, and a richer nutrient profile compared to refined white bread."},
        ],
        "ai_explanation": "White bread is made from refined flour stripped of the bran and germ, removing most fibre and nutrients. Its high glycaemic index (75) causes rapid blood glucose spikes, promoting fat storage and increased hunger.",
        "tips": "If switching to whole wheat bread, look for 'whole wheat flour' as the first ingredient — not just 'wheat flour' which can still mean refined.",
    },
    "brown bread": {
        "serving_size": "2 slices (56g)", "calories": 138,
        "protein_g": 7.0, "carbs_g": 24.0, "fat_g": 2.0, "fibre_g": 4.0,
        "health_score": 7, "weight_loss_suitable": True, "diabetic_friendly": True,
        "weight_loss_reason": "Higher fibre content increases satiety and reduces overall calorie intake.",
        "diabetic_reason": "Lower GI than white bread; fibre slows glucose absorption for steadier blood sugar.",
        "is_healthy": True,
        "healthier_alternatives": [
            {"name": "Whole Wheat Bread + Avocado", "reason": "Avocado's healthy fats further lower the GI and provide heart-healthy monounsaturated fats."},
            {"name": "Whole Wheat Bread + Eggs", "reason": "Adding protein dramatically increases satiety and provides essential amino acids."},
        ],
        "ai_explanation": "Whole wheat bread retains the bran and germ, delivering fibre, magnesium, B vitamins and antioxidants absent in white bread. Studies link whole grain consumption to lower risk of heart disease and type 2 diabetes.",
        "tips": "Pair with protein and healthy fat (eggs, nut butter, avocado) to create a balanced meal with sustained energy.",
    },
    "white rice": {
        "serving_size": "1 cup cooked (186g)", "calories": 242,
        "protein_g": 4.4, "carbs_g": 53.2, "fat_g": 0.4, "fibre_g": 0.6,
        "health_score": 5, "weight_loss_suitable": False, "diabetic_friendly": False,
        "weight_loss_reason": "High GI refined carb promotes fat storage; low fibre means limited satiety per calorie.",
        "diabetic_reason": "Refined starch raises blood glucose rapidly (GI ~72); diabetics should limit portions.",
        "is_healthy": False,
        "healthier_alternatives": [
            {"name": "Brown Rice", "reason": "3× more fibre, lower GI (50 vs 72), richer in magnesium, phosphorus, and B vitamins."},
            {"name": "Millets (Bajra/Jowar)", "reason": "Much lower GI, higher protein content, rich in iron and calcium — excellent for diabetics and weight management."},
        ],
        "ai_explanation": "White rice is a polished grain with the bran and germ removed, resulting in a lower nutrient profile. While it provides quick energy, its low fibre content means limited satiety and rapid glucose absorption.",
        "tips": "Cool cooked rice before eating — this forms resistant starch that lowers the glycaemic impact by up to 50%.",
    },
    "brown rice": {
        "serving_size": "1 cup cooked (195g)", "calories": 218,
        "protein_g": 4.5, "carbs_g": 45.8, "fat_g": 1.6, "fibre_g": 3.5,
        "health_score": 8, "weight_loss_suitable": True, "diabetic_friendly": True,
        "weight_loss_reason": "Higher fibre and nutrient density support satiety; lower GI reduces fat storage.",
        "diabetic_reason": "Lower GI (50) compared to white rice (72); fibre moderates blood glucose response.",
        "is_healthy": True,
        "healthier_alternatives": [
            {"name": "Brown Rice + Dal", "reason": "Combining with lentils creates a complete protein and adds iron and folate."},
            {"name": "Brown Rice + Stir-Fried Vegetables", "reason": "Vegetables add micronutrients and fibre while keeping the meal balanced and colourful."},
        ],
        "ai_explanation": "Brown rice retains its bran layer, providing significantly more fibre, magnesium, phosphorus, and antioxidants. Regular consumption is associated with reduced risk of type 2 diabetes and heart disease.",
        "tips": "Soak brown rice for 30 minutes before cooking to reduce phytic acid and improve mineral absorption.",
    },
    "roti": {
        "serving_size": "2 medium rotis (60g)", "calories": 160,
        "protein_g": 5.0, "carbs_g": 32.0, "fat_g": 2.0, "fibre_g": 3.5,
        "health_score": 8, "weight_loss_suitable": True, "diabetic_friendly": True,
        "weight_loss_reason": "Whole wheat roti is low in fat, high in complex carbs and fibre for sustained energy.",
        "diabetic_reason": "Whole wheat atta has moderate GI; fibre slows glucose absorption better than maida.",
        "is_healthy": True,
        "healthier_alternatives": [
            {"name": "Roti + Dal + Sabzi", "reason": "Complete balanced meal with protein from dal and micronutrients from vegetables."},
            {"name": "Jowar/Bajra Roti", "reason": "Millet rotis have higher fibre, lower GI, and more minerals than wheat — excellent for diabetics."},
        ],
        "ai_explanation": "Whole wheat roti is a staple rich in complex carbohydrates, dietary fibre, B vitamins, and iron. The fibre in whole wheat atta supports digestive health and helps maintain stable blood sugar.",
        "tips": "Use minimum ghee or oil while cooking. Pairing roti with dal provides all essential amino acids.",
    },
    "oats": {
        "serving_size": "1/2 cup dry (40g)", "calories": 150,
        "protein_g": 5.0, "carbs_g": 27.0, "fat_g": 2.5, "fibre_g": 4.0,
        "health_score": 9, "weight_loss_suitable": True, "diabetic_friendly": True,
        "weight_loss_reason": "Beta-glucan fibre promotes prolonged fullness and reduces total calorie intake.",
        "diabetic_reason": "Beta-glucan fibre significantly lowers post-meal blood glucose response; GI ~55.",
        "is_healthy": True,
        "healthier_alternatives": [
            {"name": "Oats + Berries + Nuts", "reason": "Berries add antioxidants; nuts provide healthy fats for a nutritionally complete breakfast."},
            {"name": "Overnight Oats with Greek Yogurt", "reason": "Adding yogurt boosts protein content and probiotics while maintaining the fibre benefits."},
        ],
        "ai_explanation": "Oats are one of the most nutritious grains available — their unique soluble fibre beta-glucan lowers LDL cholesterol, improves insulin sensitivity, and feeds beneficial gut bacteria. Clinical studies show regular oat consumption reduces cardiovascular disease risk.",
        "tips": "Choose rolled or steel-cut oats over instant varieties — they have more fibre and a lower GI.",
    },
    # ── Proteins ──────────────────────────────────────────────────────────
    "egg": {
        "serving_size": "2 large eggs (100g)", "calories": 143,
        "protein_g": 12.6, "carbs_g": 0.7, "fat_g": 9.5, "fibre_g": 0.0,
        "health_score": 8, "weight_loss_suitable": True, "diabetic_friendly": True,
        "weight_loss_reason": "Very high satiety per calorie; high protein reduces overall calorie intake throughout the day.",
        "diabetic_reason": "Negligible carbohydrate content with high protein; does not raise blood glucose.",
        "is_healthy": True,
        "healthier_alternatives": [
            {"name": "Eggs + Whole Wheat Toast", "reason": "Adding complex carbs creates a balanced meal with sustained energy release."},
            {"name": "Eggs + Sautéed Vegetables", "reason": "Vegetables add fibre, vitamins, and antioxidants to make a complete nutritious meal."},
        ],
        "ai_explanation": "Eggs are a nutritional powerhouse — complete protein with all essential amino acids, plus choline for brain health, lutein for eye health, and vitamin D. Despite early concerns, moderate egg consumption does not increase cardiovascular risk in healthy individuals.",
        "tips": "Boiled or poached eggs are healthiest — frying adds unnecessary calories. The yolk contains most of the nutrients.",
    },
    "paneer": {
        "serving_size": "100g", "calories": 265,
        "protein_g": 18.3, "carbs_g": 3.4, "fat_g": 20.8, "fibre_g": 0.0,
        "health_score": 7, "weight_loss_suitable": True, "diabetic_friendly": True,
        "weight_loss_reason": "High protein content promotes satiety and muscle preservation during calorie restriction.",
        "diabetic_reason": "Minimal carbohydrates; protein and fat combination does not spike blood glucose.",
        "is_healthy": True,
        "healthier_alternatives": [
            {"name": "Paneer + Spinach (Palak Paneer)", "reason": "Spinach adds iron, folate, and vitamins A and C — transforming paneer into a nutrient-dense dish."},
            {"name": "Paneer + Bell Peppers", "reason": "Bell peppers add vitamin C which enhances calcium absorption from paneer, plus antioxidants."},
        ],
        "ai_explanation": "Paneer is an excellent vegetarian protein source rich in calcium and phosphorus for bone health. Its high protein content (18g/100g) makes it ideal for vegetarians seeking muscle-supporting nutrition.",
        "tips": "Choose low-fat paneer or tofu to reduce saturated fat while maintaining high protein content.",
    },
    "chicken": {
        "serving_size": "100g cooked breast", "calories": 165,
        "protein_g": 31.0, "carbs_g": 0.0, "fat_g": 3.6, "fibre_g": 0.0,
        "health_score": 8, "weight_loss_suitable": True, "diabetic_friendly": True,
        "weight_loss_reason": "Lean protein with very low fat; high thermic effect means more calories burned digesting it.",
        "diabetic_reason": "Zero carbohydrates — does not affect blood glucose; excellent protein source for diabetics.",
        "is_healthy": True,
        "healthier_alternatives": [
            {"name": "Grilled Chicken + Quinoa", "reason": "Quinoa adds complete plant protein, fibre, and minerals for a nutritionally complete meal."},
            {"name": "Chicken + Roasted Vegetables", "reason": "Vegetables provide fibre and micronutrients to complement the lean protein."},
        ],
        "ai_explanation": "Grilled chicken breast is one of the leanest protein sources available. Its high protein content (31g/100g) supports muscle building, satiety, and metabolic health with minimal fat.",
        "tips": "Grilling, baking or steaming chicken preserves nutrients while avoiding the excess calories from frying.",
    },
    "dal": {
        "serving_size": "1 cup cooked (198g)", "calories": 230,
        "protein_g": 17.9, "carbs_g": 39.9, "fat_g": 0.8, "fibre_g": 15.6,
        "health_score": 9, "weight_loss_suitable": True, "diabetic_friendly": True,
        "weight_loss_reason": "Exceptionally high in protein and fibre, providing outstanding satiety per calorie.",
        "diabetic_reason": "Low GI (~29); high fibre slows glucose absorption significantly — ideal for diabetics.",
        "is_healthy": True,
        "healthier_alternatives": [
            {"name": "Dal + Brown Rice", "reason": "Together they form a complete protein with all essential amino acids and complementary fibre."},
            {"name": "Dal + Whole Wheat Roti", "reason": "Classic combination providing balanced macros, B vitamins, and sustained energy."},
        ],
        "ai_explanation": "Dal (lentils) is a nutritional champion — rich in plant protein, soluble and insoluble fibre, iron, folate, and potassium. Regular lentil consumption is strongly associated with reduced risk of heart disease, diabetes, and improved gut health.",
        "tips": "Adding a squeeze of lemon to dal improves iron absorption by 3–4× due to the vitamin C content.",
    },
    # ── Snacks & Processed Foods ──────────────────────────────────────────
    "samosa": {
        "serving_size": "2 medium samosas (120g)", "calories": 400,
        "protein_g": 6.0, "carbs_g": 44.0, "fat_g": 22.0, "fibre_g": 2.5,
        "health_score": 3, "weight_loss_suitable": False, "diabetic_friendly": False,
        "weight_loss_reason": "Deep-fried in refined oil with a maida crust — very high in unhealthy fats and calories.",
        "diabetic_reason": "Refined flour causes rapid glucose spikes; high fat content leads to unpredictable glucose response.",
        "is_healthy": False,
        "healthier_alternatives": [
            {"name": "Baked Whole-Wheat Samosa", "reason": "Eliminates trans fats from deep frying; whole wheat adds fibre and lowers GI significantly — saves ~120 kcal."},
            {"name": "Air-Fried Dhokla", "reason": "Fermented chickpea snack with protein, probiotics, and 70% fewer calories than a fried samosa."},
        ],
        "ai_explanation": "Traditional deep-fried samosas are made with maida (refined flour) and cooked in oil that may contain trans fats. The combination of refined carbs and saturated/trans fats promotes inflammation and weight gain.",
        "tips": "Make samosas at home using whole wheat flour and air-fry or bake them for a much healthier version.",
    },
    "chips": {
        "serving_size": "1 small bag (28g)", "calories": 152,
        "protein_g": 2.0, "carbs_g": 15.0, "fat_g": 10.0, "fibre_g": 1.4,
        "health_score": 2, "weight_loss_suitable": False, "diabetic_friendly": False,
        "weight_loss_reason": "High calorie density with low satiety; easy to overconsume — 100g provides ~535 kcal.",
        "diabetic_reason": "Refined starch plus sodium triggers both glucose spikes and water retention.",
        "is_healthy": False,
        "healthier_alternatives": [
            {"name": "Roasted Makhana (Fox Nuts)", "reason": "Low calorie (347 kcal/100g vs 535 for chips), high protein, rich in magnesium and calcium, and crispy."},
            {"name": "Roasted Chana", "reason": "High protein and fibre snack that fills you up with fewer calories and no trans fats."},
        ],
        "ai_explanation": "Potato chips are one of the most calorie-dense, nutrient-poor snacks available. They are high in sodium, refined starch, and often contain trans fats or acrylamide from high-temperature frying.",
        "tips": "When craving crunch, try roasted makhana or chana — they satisfy the same urge with a fraction of the calories.",
    },
    "pizza": {
        "serving_size": "2 slices (200g)", "calories": 500,
        "protein_g": 20.0, "carbs_g": 58.0, "fat_g": 20.0, "fibre_g": 3.0,
        "health_score": 3, "weight_loss_suitable": False, "diabetic_friendly": False,
        "weight_loss_reason": "High calorie density combining refined carbs, saturated fat, and sodium promotes overconsumption.",
        "diabetic_reason": "Refined flour base spikes blood glucose; high fat delays and prolongs glucose absorption unpredictably.",
        "is_healthy": False,
        "healthier_alternatives": [
            {"name": "Whole Wheat Thin-Crust Pizza with Vegetables", "reason": "Whole wheat adds fibre; vegetable toppings add nutrients while reducing calorie density vs cheese-heavy versions."},
            {"name": "Cauliflower Crust Pizza", "reason": "Very low carb alternative; cauliflower provides fibre and micronutrients with dramatically fewer calories."},
        ],
        "ai_explanation": "Commercial pizza combines refined flour crust (high GI), processed cheese (high saturated fat), and often processed meat toppings (high sodium). The combination is calorie-dense with limited satiety.",
        "tips": "Choose thin-crust, load with vegetables, go light on cheese, and add grilled chicken for a more balanced pizza.",
    },
    "burger": {
        "serving_size": "1 medium burger (200g)", "calories": 480,
        "protein_g": 25.0, "carbs_g": 42.0, "fat_g": 22.0, "fibre_g": 2.0,
        "health_score": 3, "weight_loss_suitable": False, "diabetic_friendly": False,
        "weight_loss_reason": "High in saturated fat, refined carbs, and sodium — calorie-dense with limited nutrient value.",
        "diabetic_reason": "White bun causes rapid glucose spikes; high fat and sodium are problematic for metabolic health.",
        "is_healthy": False,
        "healthier_alternatives": [
            {"name": "Whole Wheat Bun Grilled Chicken Burger", "reason": "Lean protein instead of red/processed meat; whole wheat bun adds fibre and a lower GI."},
            {"name": "Lettuce-Wrap Veggie Burger", "reason": "Eliminates refined carbs entirely; plant-based patty provides fibre and reduces saturated fat."},
        ],
        "ai_explanation": "Fast food burgers combine processed red meat, refined flour buns, and high-sodium condiments. Regular consumption is associated with increased risk of obesity, heart disease, and type 2 diabetes.",
        "tips": "When eating out, choose grilled over fried, whole wheat bun, extra vegetables, and skip the fries.",
    },
    # ── Dairy ─────────────────────────────────────────────────────────────
    "curd": {
        "serving_size": "1 cup (245g)", "calories": 150,
        "protein_g": 8.5, "carbs_g": 11.4, "fat_g": 8.0, "fibre_g": 0.0,
        "health_score": 8, "weight_loss_suitable": True, "diabetic_friendly": True,
        "weight_loss_reason": "High protein promotes satiety; probiotics support gut health and metabolism.",
        "diabetic_reason": "Low GI (~35); protein and fat moderate glucose response from natural sugars.",
        "is_healthy": True,
        "healthier_alternatives": [
            {"name": "Curd + Fruit Bowl", "reason": "Combining curd with fruit adds fibre, vitamins and antioxidants for a nutritionally complete snack."},
            {"name": "Curd + Flaxseeds", "reason": "Flaxseeds add omega-3 fatty acids and lignans that amplify curd's gut health benefits."},
        ],
        "ai_explanation": "Curd (dahi) is an excellent probiotic food that supports gut microbiome diversity, immune function, and calcium intake. The fermentation process increases bioavailability of several nutrients.",
        "tips": "Choose plain curd over flavoured varieties — flavoured yogurts often contain 4–5 teaspoons of added sugar.",
    },
    "milk": {
        "serving_size": "1 glass (240ml)", "calories": 149,
        "protein_g": 8.0, "carbs_g": 12.0, "fat_g": 8.0, "fibre_g": 0.0,
        "health_score": 7, "weight_loss_suitable": True, "diabetic_friendly": True,
        "weight_loss_reason": "High protein and calcium support lean muscle maintenance during weight loss.",
        "diabetic_reason": "Low GI (~27); protein content moderates glucose response from lactose.",
        "is_healthy": True,
        "healthier_alternatives": [
            {"name": "Milk + Turmeric (Golden Milk)", "reason": "Turmeric adds potent anti-inflammatory curcumin, transforming milk into a therapeutic beverage."},
            {"name": "Low-Fat Milk + Protein", "reason": "Skimmed milk reduces saturated fat while maintaining high calcium and protein content."},
        ],
        "ai_explanation": "Milk is a complete food providing high-quality protein, calcium, phosphorus, vitamins D and B12, and riboflavin. It plays a crucial role in bone health, muscle recovery, and overall growth.",
        "tips": "Toned or skimmed milk provides the same calcium and protein as full-fat milk with significantly less saturated fat.",
    },
    # ── Beverages ─────────────────────────────────────────────────────────
    "cold drink": {
        "serving_size": "1 can (355ml)", "calories": 155,
        "protein_g": 0.0, "carbs_g": 39.0, "fat_g": 0.0, "fibre_g": 0.0,
        "health_score": 1, "weight_loss_suitable": False, "diabetic_friendly": False,
        "weight_loss_reason": "Liquid calories with zero satiety — 39g of sugar that does not reduce hunger.",
        "diabetic_reason": "Extremely high in sugar causing immediate, severe blood glucose spikes — completely avoid.",
        "is_healthy": False,
        "healthier_alternatives": [
            {"name": "Nimbu Pani (Lemon Water)", "reason": "Zero added sugar, natural electrolytes, vitamin C, and refreshing — replaces soda perfectly."},
            {"name": "Coconut Water", "reason": "Natural electrolytes (potassium, sodium), low calories, and natural sweetness without refined sugar."},
        ],
        "ai_explanation": "Carbonated soft drinks are among the most harmful beverages for metabolic health. Their high fructose corn syrup content is directly linked to non-alcoholic fatty liver disease, obesity, and type 2 diabetes.",
        "tips": "Replace soda with sparkling water + a slice of lemon for the same fizzy satisfaction with zero sugar.",
    },
}

# Foods considered inherently healthy — these get pairing suggestions, not substitutes
_HEALTHY_FOOD_KEYWORDS = {
    "apple", "banana", "orange", "mango", "papaya", "guava", "kiwi", "strawberry",
    "blueberry", "watermelon", "grapes", "pear", "pineapple",
    "salad", "spinach", "broccoli", "carrot", "cucumber", "tomato",
    "oats", "brown rice", "roti", "chapati", "dal", "lentil",
    "egg", "paneer", "chicken breast", "grilled chicken", "tofu",
    "curd", "yogurt", "milk", "cottage cheese",
    "nuts", "almonds", "walnuts", "flaxseeds", "chia",
}


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _lookup_nutrition_db(food_name: str) -> dict | None:
    """Look up a food in the static nutrition DB (case-insensitive, partial match)."""
    fl = food_name.lower().strip()
    # Exact match first
    if fl in _NUTRITION_DB:
        return _NUTRITION_DB[fl]
    # Partial keyword match
    for key, entry in _NUTRITION_DB.items():
        if key in fl or fl in key:
            return entry
    return None


def _is_healthy_food(food_name: str) -> bool:
    """Return True if the food is inherently healthy based on its name."""
    fl = food_name.lower()
    return any(kw in fl for kw in _HEALTHY_FOOD_KEYWORDS)


def _build_vision_recognition_prompt(image_b64: str, mime: str) -> str:
    """Build a prompt for vision-capable models to identify the food in an image."""
    return f"""You are a food identification expert. Look at this food image and identify what food is shown.

Respond ONLY with a valid JSON object — no markdown, no extra text:
{{
  "food_name": "<specific food name, e.g. 'Apple', 'White Bread', 'Chicken Biryani'>",
  "confidence": "<high|medium|low>",
  "description": "<one sentence describing what you see>"
}}

Rules:
- Be specific (e.g. 'Banana' not 'fruit', 'White Rice' not 'grain')
- If you cannot identify the food, set food_name to null and confidence to "low"
- Do not use the image filename — identify based on actual visual content"""


def _build_food_recognition_prompt_text(context_hint: str = "") -> str:
    """
    Build a text-only Granite prompt to identify a food from a contextual hint.
    Used when vision is unavailable and user has provided a description.
    """
    context_section = f"\nContext hint from user: {context_hint}" if context_hint else ""
    return f"""You are a food identification assistant.{context_section}

A user has uploaded a food image. Based on any available context, identify the most likely food shown.

Respond ONLY with a valid JSON object — no markdown, no extra text:
{{
  "food_name": "<specific food name>",
  "confidence": "<high|medium|low>",
  "needs_user_input": <true if you cannot identify with reasonable confidence, else false>
}}

Rules:
- Only use the context hint if it clearly names a food (ignore generic filenames like 'Screenshot', 'IMG_1234', 'photo', 'image')
- If the hint is a generic filename or timestamp, set needs_user_input to true
- Provide a specific food name, not a generic category"""


def _build_food_analysis_prompt(food_name: str, db_entry: dict | None = None) -> str:
    """Return a structured Granite prompt that produces a JSON nutrition analysis."""
    # Seed the model with DB values when available for accuracy
    seed_section = ""
    if db_entry:
        seed_section = f"""
Use these verified nutrition values (do not significantly deviate):
- serving_size: {db_entry['serving_size']}
- calories: {db_entry['calories']}
- protein_g: {db_entry['protein_g']}
- carbs_g: {db_entry['carbs_g']}
- fat_g: {db_entry['fat_g']}
- fibre_g: {db_entry['fibre_g']}
- health_score: {db_entry['health_score']}
- weight_loss_suitable: {str(db_entry['weight_loss_suitable']).lower()}
- diabetic_friendly: {str(db_entry['diabetic_friendly']).lower()}
"""

    is_healthy = _is_healthy_food(food_name)
    alternatives_instruction = (
        "Since this is already a healthy food, suggest complementary PAIRINGS that enhance its nutrition "
        "(e.g. 'Apple + Greek Yogurt' — do NOT suggest unrelated alternatives like salads or generic vegetable bowls)."
        if is_healthy else
        "Since this is a processed or less-healthy food, suggest genuinely HEALTHIER SUBSTITUTES and explain "
        "specifically why each substitute is healthier (fibre content, GI, fat type, etc.)."
    )

    return f"""You are NutriBot, an expert AI nutritionist. Analyse the following food and respond ONLY with a valid JSON object — no markdown, no extra text.

Food: {food_name}
{seed_section}
Return exactly this JSON structure (fill every field with realistic, scientifically accurate values):
{{
  "food_name": "<clean food name>",
  "serving_size": "<typical serving size>",
  "calories": <number>,
  "protein_g": <number>,
  "carbs_g": <number>,
  "fat_g": <number>,
  "fibre_g": <number>,
  "health_score": <integer 1-10>,
  "weight_loss_suitable": <true|false>,
  "diabetic_friendly": <true|false>,
  "weight_loss_reason": "<one sentence>",
  "diabetic_reason": "<one sentence>",
  "ai_explanation": "<2-3 sentences explaining the food's nutritional profile, key nutrients, and health impact>",
  "healthier_alternatives": [
    {{
      "name": "<alternative or pairing name>",
      "reason": "<specific reason why this alternative/pairing is beneficial>"
    }},
    {{
      "name": "<second alternative or pairing>",
      "reason": "<specific reason>"
    }}
  ],
  "tips": "<one practical healthy-eating tip>"
}}

{alternatives_instruction}"""


def _mock_food_analysis(food_name: str) -> dict:
    """
    Return a plausible mock analysis using the nutrition DB or keyword matching.
    Used when Watsonx is not configured.
    """
    # Try exact DB lookup first
    entry = _lookup_nutrition_db(food_name)
    if entry:
        return {
            "food_name": food_name.strip().title(),
            "serving_size": entry["serving_size"],
            "calories": entry["calories"],
            "protein_g": entry["protein_g"],
            "carbs_g": entry["carbs_g"],
            "fat_g": entry["fat_g"],
            "fibre_g": entry["fibre_g"],
            "health_score": entry["health_score"],
            "weight_loss_suitable": entry["weight_loss_suitable"],
            "diabetic_friendly": entry["diabetic_friendly"],
            "weight_loss_reason": entry["weight_loss_reason"],
            "diabetic_reason": entry["diabetic_reason"],
            "ai_explanation": entry.get("ai_explanation", ""),
            "healthier_alternatives": entry["healthier_alternatives"],
            "tips": entry.get("tips", ""),
        }

    # Keyword-based fallback matching
    fl = food_name.lower()
    if any(w in fl for w in ["rice", "biryani", "pulao", "fried rice"]):
        return {
            "food_name": food_name.strip().title(),
            "serving_size": "1 cup cooked (186g)",
            "calories": 242, "protein_g": 4.4, "carbs_g": 53.0, "fat_g": 0.4, "fibre_g": 0.6,
            "health_score": 5, "weight_loss_suitable": False, "diabetic_friendly": False,
            "weight_loss_reason": "High GI refined carb promotes fat storage; low fibre means limited satiety.",
            "diabetic_reason": "Refined starch raises blood glucose rapidly; diabetics should limit portions.",
            "ai_explanation": "White rice is a refined grain with most of its fibre and nutrients removed. Its high glycaemic index (72) causes rapid blood glucose spikes. Combining with dal and vegetables significantly improves its nutritional profile.",
            "healthier_alternatives": [
                {"name": "Brown Rice", "reason": "3× more fibre, lower GI (50 vs 72), and significantly richer in B vitamins and minerals."},
                {"name": "Millets (Bajra/Jowar)", "reason": "Much lower GI, higher protein, more minerals — excellent for diabetics and weight management."},
            ],
            "tips": "Cool cooked rice before eating to form resistant starch, lowering its glycaemic impact by up to 50%.",
        }
    if any(w in fl for w in ["samosa", "pakora", "vada", "poori", "bhatura"]):
        return {
            "food_name": food_name.strip().title(),
            "serving_size": "2 pieces (~120g)",
            "calories": 400, "protein_g": 6.0, "carbs_g": 44.0, "fat_g": 22.0, "fibre_g": 2.5,
            "health_score": 3, "weight_loss_suitable": False, "diabetic_friendly": False,
            "weight_loss_reason": "Deep-fried in refined oil — very high in unhealthy fats and calories.",
            "diabetic_reason": "Refined flour causes rapid glucose spikes; high fat leads to unpredictable glucose response.",
            "ai_explanation": "Deep-fried snacks made with maida are high in refined carbohydrates and trans fats. Regular consumption is linked to weight gain, elevated LDL cholesterol, and increased cardiovascular risk.",
            "healthier_alternatives": [
                {"name": "Baked Whole-Wheat Version", "reason": "Eliminates trans fats; whole wheat adds fibre and lowers GI — saves ~120 kcal per serving."},
                {"name": "Air-Fried Dhokla", "reason": "Fermented chickpea snack with protein, probiotics, and 70% fewer calories."},
            ],
            "tips": "Make these at home using whole wheat flour and air-fry or bake for a much healthier version.",
        }
    if any(w in fl for w in ["bread", "toast"]):
        return {
            "food_name": food_name.strip().title(),
            "serving_size": "2 slices (56g)",
            "calories": 160, "protein_g": 6.0, "carbs_g": 30.0, "fat_g": 2.0, "fibre_g": 2.0,
            "health_score": 4, "weight_loss_suitable": False, "diabetic_friendly": False,
            "weight_loss_reason": "Refined flour has a high GI causing rapid sugar spikes and rebound hunger.",
            "diabetic_reason": "Rapidly digested refined starch elevates blood glucose — not recommended for diabetics.",
            "ai_explanation": "White bread is made from refined flour stripped of the bran and germ, removing most fibre and nutrients. Its high glycaemic index (75) causes rapid blood glucose spikes and promotes fat storage.",
            "healthier_alternatives": [
                {"name": "Whole Wheat Bread", "reason": "Contains the entire wheat grain — 3× more fibre, B vitamins, iron, and a lower GI (69 vs 75) that prevents blood sugar spikes."},
                {"name": "Multigrain Bread", "reason": "Multiple grains provide diverse fibre, antioxidants, and a richer nutrient profile than refined white bread."},
            ],
            "tips": "Look for 'whole wheat flour' as the first ingredient — not just 'wheat flour' which may still be refined.",
        }
    if any(w in fl for w in ["fruit", "apple", "banana", "mango", "orange", "guava", "papaya"]):
        return {
            "food_name": food_name.strip().title(),
            "serving_size": "1 medium / 1 cup (150g)",
            "calories": 80, "protein_g": 1.0, "carbs_g": 20.0, "fat_g": 0.3, "fibre_g": 3.0,
            "health_score": 9, "weight_loss_suitable": True, "diabetic_friendly": True,
            "weight_loss_reason": "Low calorie density with high fibre and water content — excellent for weight management.",
            "diabetic_reason": "Natural sugars with fibre moderate blood glucose response better than refined sugars.",
            "ai_explanation": "Fresh fruits are nutrient-dense foods rich in vitamins, minerals, antioxidants, and dietary fibre. They provide natural sweetness with significantly better nutritional value than processed sweets.",
            "healthier_alternatives": [
                {"name": f"{food_name.strip().title()} + Greek Yogurt", "reason": "Adding protein from yogurt slows sugar absorption and makes a nutritionally complete snack."},
                {"name": f"{food_name.strip().title()} + Mixed Nuts", "reason": "Healthy fats and protein from nuts complement the fruit's fibre for better satiety and blood sugar control."},
            ],
            "tips": "Eat fruits whole rather than juicing — juicing removes fibre and concentrates natural sugars.",
        }
    # Generic fallback — balanced meal
    is_healthy = _is_healthy_food(food_name)
    return {
        "food_name": food_name.strip().title(),
        "serving_size": "1 serving (~150g)",
        "calories": 220, "protein_g": 10.0, "carbs_g": 28.0, "fat_g": 7.0, "fibre_g": 3.5,
        "health_score": 6,
        "weight_loss_suitable": True,
        "diabetic_friendly": True,
        "weight_loss_reason": "Moderate calorie density with balanced macros can fit a calorie-controlled diet.",
        "diabetic_reason": "Balanced carbohydrate and fibre content helps maintain relatively stable blood glucose.",
        "ai_explanation": "This food provides a balanced mix of macronutrients. Including a variety of whole foods, lean proteins, and vegetables in your diet supports overall health and helps maintain a healthy weight.",
        "healthier_alternatives": (
            [
                {"name": f"{food_name.strip().title()} + Greek Yogurt", "reason": "Adding protein boosts satiety and provides probiotics for gut health."},
                {"name": f"{food_name.strip().title()} + Mixed Nuts", "reason": "Healthy fats and protein complement this food for a more nutritionally complete snack."},
            ] if is_healthy else [
                {"name": "Grilled Vegetables & Legumes", "reason": "Rich in fibre and plant protein with fewer calories and no processed ingredients."},
                {"name": "Whole Grain Alternative", "reason": "Swapping refined grains for whole grains increases fibre, vitamins, and lowers glycaemic impact."},
            ]
        ),
        "tips": "Pair this food with a source of protein and colourful vegetables to boost its overall nutritional profile.",
    }


def _try_vision_recognition(image_bytes: bytes, mime: str) -> str | None:
    """
    Attempt to identify the food in the image using a vision-capable IBM model.
    Returns the food name string, or None if recognition failed / unavailable.
    """
    if not IBM_API_KEY or not WATSONX_PROJECT_ID:
        return None

    # Vision model IDs to try in order of preference
    vision_model_ids = [
        "meta-llama/llama-3-2-11b-vision-instruct",
        "ibm/granite-vision-3-2-2b",
        "ibm/granite-vision-3-1-2b",
    ]

    try:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference

        credentials = Credentials(url=WATSONX_URL, api_key=IBM_API_KEY)
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        for model_id in vision_model_ids:
            try:
                vision_client = ModelInference(
                    model_id=model_id,
                    credentials=credentials,
                    project_id=WATSONX_PROJECT_ID,
                    params={"max_new_tokens": 200, "temperature": 0.1},
                )
                # Use messages API for vision models (multimodal)
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime};base64,{image_b64}"},
                            },
                            {
                                "type": "text",
                                "text": (
                                    "What food is shown in this image? "
                                    "Respond ONLY with a JSON object: "
                                    '{"food_name": "<specific food name>", "confidence": "<high|medium|low>"}'
                                ),
                            },
                        ],
                    }
                ]
                raw = vision_client.chat(messages=messages)
                # Extract content from response
                if isinstance(raw, dict):
                    content = (
                        raw.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                else:
                    content = str(raw)

                content = content.strip()
                if content.startswith("```"):
                    content = content.split("```")[1].lstrip("json").strip()

                parsed = json.loads(content)
                food_name = parsed.get("food_name", "").strip()
                confidence = parsed.get("confidence", "low")

                if food_name and confidence in ("high", "medium"):
                    logger.info("Vision model %s identified: %s (%s)", model_id, food_name, confidence)
                    return food_name

            except Exception as ve:
                logger.debug("Vision model %s failed: %s", model_id, ve)
                continue

    except Exception as exc:
        logger.debug("Vision recognition unavailable: %s", exc)

    return None


def _try_text_recognition(context_hint: str) -> tuple[str | None, bool]:
    """
    Use IBM Granite text model to identify a food from a context hint.
    Returns (food_name_or_None, needs_user_input_bool).
    """
    client = get_watsonx_client()
    if client is None:
        return None, True

    # Reject obviously non-food filenames (screenshots, generic names, timestamps)
    hint_lower = context_hint.lower().strip()
    generic_patterns = [
        "screenshot", "img_", "image", "photo", "pic_", "dsc_",
        "untitled", "file", "download", "whatsapp", "camera",
    ]
    # Also reject if hint contains mostly digits/dashes (timestamp-like)
    import re as _re
    if (
        any(pat in hint_lower for pat in generic_patterns)
        or _re.match(r'^[\d\s\-_\.]+$', hint_lower)
        or len(hint_lower) < 3
    ):
        return None, True

    prompt = _build_food_recognition_prompt_text(context_hint)
    try:
        raw = client.generate_text(prompt=prompt) or "{}"
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        parsed = json.loads(raw)
        food_name = (parsed.get("food_name") or "").strip()
        needs_input = bool(parsed.get("needs_user_input", False))
        confidence = parsed.get("confidence", "low")

        if food_name and not needs_input and confidence in ("high", "medium"):
            return food_name, False
        return None, True
    except Exception as exc:
        logger.warning("Text food recognition failed: %s", exc)
        return None, True


def analyse_food_with_ai(food_name: str) -> dict:
    """
    Use IBM Granite to produce a structured JSON nutrition analysis.
    Seeded with realistic nutrition DB values when available.
    Falls back to mock data when Watsonx is not configured.
    """
    # Look up DB entry first (for value seeding)
    db_entry = _lookup_nutrition_db(food_name)

    client = get_watsonx_client()
    if client is None:
        return _mock_food_analysis(food_name)

    prompt = _build_food_analysis_prompt(food_name, db_entry)
    try:
        raw = client.generate_text(prompt=prompt) or ""
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        result = json.loads(raw)
        # Ensure every expected key exists
        required = ["food_name", "serving_size", "calories", "protein_g", "carbs_g",
                    "fat_g", "fibre_g", "health_score", "weight_loss_suitable",
                    "diabetic_friendly", "healthier_alternatives"]
        if all(k in result for k in required):
            # If we have DB values, override with known-accurate values
            if db_entry:
                result["calories"]            = db_entry["calories"]
                result["protein_g"]           = db_entry["protein_g"]
                result["carbs_g"]             = db_entry["carbs_g"]
                result["fat_g"]               = db_entry["fat_g"]
                result["fibre_g"]             = db_entry["fibre_g"]
                result["serving_size"]        = db_entry["serving_size"]
                result["health_score"]        = db_entry["health_score"]
                result["weight_loss_suitable"] = db_entry["weight_loss_suitable"]
                result["diabetic_friendly"]   = db_entry["diabetic_friendly"]
                if db_entry.get("healthier_alternatives"):
                    result["healthier_alternatives"] = db_entry["healthier_alternatives"]
                if db_entry.get("ai_explanation") and not result.get("ai_explanation"):
                    result["ai_explanation"] = db_entry["ai_explanation"]
            return result
        logger.warning("Granite response missing keys — falling back to mock.")
        return _mock_food_analysis(food_name)
    except (json.JSONDecodeError, Exception) as exc:
        logger.error("Food analysis parse error: %s", exc)
        return _mock_food_analysis(food_name)


@app.route("/api/analyze-food", methods=["POST"])
def analyze_food():
    """
    Accept a food image (multipart/form-data) or a plain text description.

    Flow:
    1. If image uploaded → try IBM vision model to identify food.
    2. If vision unavailable → check if user provided a clear food description.
    3. If hint is generic (filename/timestamp) → return needs_identification=True
       so the frontend can ask the user what the food is.
    4. Once food is identified → generate realistic nutrition analysis via Granite.
    """
    preview_url = None
    image_bytes = None
    mime = "image/jpeg"

    # ── Path A: image file uploaded ───────────────────────────────────────
    if "image" in request.files:
        file = request.files["image"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400
        if not _allowed_file(file.filename):
            return jsonify({"error": "Only JPG, JPEG and PNG images are accepted"}), 400

        image_bytes = file.read()
        if len(image_bytes) > MAX_IMAGE_BYTES:
            return jsonify({"error": "Image exceeds 5 MB limit"}), 400

        # Encode image as base64 for returning a preview URL to the client
        mime = "image/jpeg" if file.filename.lower().endswith(("jpg", "jpeg")) else "image/png"
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        preview_url = f"data:{mime};base64,{image_b64}"

        # User-supplied text description (explicitly typed by the user after being prompted)
        user_desc = (request.form.get("description") or "").strip()
        raw_filename_hint = os.path.splitext(file.filename)[0].replace("_", " ").replace("-", " ").strip()

        # ── Step 0: If the user already told us what the food is, use it directly ──
        # This covers the fallback path where needs_identification was returned and
        # the user typed a food name into the prompt.
        if user_desc:
            db_hit = _lookup_nutrition_db(user_desc)
            if db_hit:
                # Known food — skip all recognition and analyse immediately
                identified_food = user_desc
            else:
                # User typed something but it's not in our DB
                logger.info("Food not found in DB: %s", user_desc)
                return jsonify({
                    "success": False,
                    "error": f"Sorry, I don't have nutrition data for \"{user_desc}\" yet. "
                             "Please try a common food name (e.g. Apple, Banana, White Bread, Samosa).",
                    "timestamp": datetime.now().strftime("%H:%M"),
                })
        else:
            # ── Step 1: Try vision model recognition ─────────────────────────
            identified_food = _try_vision_recognition(image_bytes, mime)

            # ── Step 2: Fall back to text-based recognition ───────────────────
            if not identified_food:
                identified_food, needs_user_input = _try_text_recognition(raw_filename_hint)

                if needs_user_input or not identified_food:
                    # Ask the user to identify the food
                    logger.info("Could not auto-identify food from image — prompting user.")
                    return jsonify({
                        "success": True,
                        "needs_identification": True,
                        "preview_url": preview_url,
                        "message": (
                            "I couldn't confidently identify the food from this image. "
                            "Please enter the food name."
                        ),
                        "timestamp": datetime.now().strftime("%H:%M"),
                    })

    else:
        # ── Path B: text-only description (direct food name from user prompt) ──
        data = request.get_json(silent=True) or {}
        identified_food = (data.get("description") or data.get("food_name") or "").strip()
        if not identified_food:
            return jsonify({"error": "Provide an image file or a food description"}), 400
        # Require the food to be present in _NUTRITION_DB
        if not _lookup_nutrition_db(identified_food):
            logger.info("Food not found in DB (Path B): %s", identified_food)
            return jsonify({
                "success": False,
                "error": f"Sorry, I don't have nutrition data for \"{identified_food}\" yet. "
                         "Please try a common food name (e.g. Apple, Banana, White Bread, Samosa).",
                "timestamp": datetime.now().strftime("%H:%M"),
            })

    logger.info("Analysing food: %s", identified_food)
    analysis = analyse_food_with_ai(identified_food)

    # Append the analysis as an assistant message in the chat session
    summary = (
        f"📸 **Food Image Analysis — {analysis.get('food_name', identified_food)}**\n\n"
        f"Here is the nutrition breakdown for your uploaded food:"
    )
    if "conversation" not in session:
        session["conversation"] = []
    session["conversation"].append({
        "role": "assistant",
        "content": summary,
        "timestamp": datetime.now().isoformat(),
    })
    session.modified = True

    return jsonify({
        "success": True,
        "needs_identification": False,
        "analysis": analysis,
        "preview_url": preview_url,
        "timestamp": datetime.now().strftime("%H:%M"),
    })


@app.route("/api/memory", methods=["GET"])
def get_memory():
    """Return the current nutrition memory for the session."""
    mem = NutritionMemory.load()
    return jsonify({"memory": mem.to_dict()})


@app.route("/api/memory", methods=["POST"])
def update_memory():
    """
    Manually update nutrition memory.

    Accepted JSON body (all fields optional):
    {
      "add_dislike":     "broccoli",
      "remove_dislike":  "broccoli",
      "add_favourite":   "paneer",
      "remove_favourite":"paneer",
      "add_allergy":     "peanuts",
      "add_condition":   "diabetes",
      "clear":           true          // wipe all memory
    }
    """
    data = request.get_json(silent=True) or {}
    mem  = NutritionMemory.load()

    if data.get("clear"):
        session.pop(SESSION_MEMORY_KEY, None)
        session.modified = True
        return jsonify({"success": True, "message": "Memory cleared.", "memory": NutritionMemory.load().to_dict()})

    changed: list[str] = []
    if v := data.get("add_dislike"):
        if mem.add_dislike(str(v)):    changed.append(f"added dislike: {v}")
    if v := data.get("remove_dislike"):
        mem.remove_dislike(str(v));    changed.append(f"removed dislike: {v}")
    if v := data.get("add_favourite"):
        if mem.add_favourite(str(v)):  changed.append(f"added favourite: {v}")
    if v := data.get("remove_favourite"):
        mem.remove_favourite(str(v));  changed.append(f"removed favourite: {v}")
    if v := data.get("add_allergy"):
        if mem.add_allergy(str(v)):    changed.append(f"added allergy: {v}")
    if v := data.get("add_condition"):
        if mem.add_condition(str(v)):  changed.append(f"added condition: {v}")

    mem.save()
    return jsonify({"success": True, "changed": changed, "memory": mem.to_dict()})


@app.route("/api/feedback", methods=["POST"])
def save_feedback():
    """
    Store a single feedback entry in the session.

    POST body (JSON):
    {
        "response":    "<the AI response text being rated>",
        "rating":      "helpful" | "not_helpful",
        "improvement": "<optional free-text from the user>"   // only for not_helpful
    }
    """
    data   = request.get_json(silent=True) or {}
    rating = (data.get("rating") or "").strip()
    if rating not in ("helpful", "not_helpful"):
        return jsonify({"error": "rating must be 'helpful' or 'not_helpful'"}), 400

    entry = {
        "rating":    rating,
        "feedback":  str(data.get("feedback") or "").strip()[:200],
        "timestamp": datetime.now().isoformat(),
    }

    feedback_list = session.get(SESSION_FEEDBACK_KEY) or []
    feedback_list.append(entry)
    session[SESSION_FEEDBACK_KEY] = feedback_list[-_FEEDBACK_MAX:]
    session.modified = True

    logger.info("Feedback saved — rating=%s feedback=%r", rating, entry["feedback"])
    return jsonify({"success": True})


@app.route("/api/clear-chat", methods=["POST"])
def clear_chat():
    session.pop("conversation", None)
    session.modified = True
    return jsonify({"success": True})


@app.route("/api/health")
def health_check():
    mem = NutritionMemory.load()
    return jsonify({
        "status": "ok",
        "model": WATSONX_MODEL_ID,
        "watsonx_configured": bool(IBM_API_KEY and WATSONX_PROJECT_ID),
        "memory_active": not mem.is_empty(),
        "memory_summary": {
            "dislikes":   len(mem.dislikes),
            "favourites": len(mem.favourites),
            "allergies":  len(mem.allergies),
            "conditions": len(mem.conditions),
            "plans_logged": len(mem.meal_plan_log),
        },
        "timestamp": datetime.now().isoformat(),
    })


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    debug = os.getenv("FLASK_ENV", "development") == "development"
    logger.info("Starting Nutrition Agent on port %d (debug=%s)", port, debug)
    app.run(host="0.0.0.0", port=port, debug=debug)
