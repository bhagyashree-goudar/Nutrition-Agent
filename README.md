# 🥗 AI-Powered Nutrition Agent
### IBM Watsonx.ai + IBM Granite  + IBM BOB · Python Flask · Modern Responsive UI 

AI-Powered Nutrition Agent is an intelligent virtual nutrition assistant built using IBM Watsonx.ai, IBM Granite, and IBM BOB. It provides personalized meal planning, nutrition guidance, BMI & TDEE calculations, family nutrition profiles, and AI-powered health recommendations based on user preferences, goals, and medical conditions.

---

## ✨ Features

| Feature | Description |
|---|---|
| 💬 **AI Chat** | Real-time nutrition Q&A powered by IBM Granite |
| 📊 **Dashboard** | Daily calorie & macro overview + nutrition tips |
| 📅 **Meal Planner** | AI-generated personalised meal plans (1–14 days) |
| ⚖️ **BMI & TDEE** | Body Mass Index + Total Daily Energy Expenditure calculator |
| 👨‍👩‍👧‍👦 **Family Profiles** | Multi-member profiles with per-person dietary plans |
| 🌙 **Dark Mode** | Toggle between light and dark themes |
| 📱 **Mobile-First** | Fully responsive Bootstrap 5 UI |
| 🥘 **Indian Foods** | Deep knowledge of Indian cuisine, regional dishes, spices |
| 🛡️ **Safety Rules** | Built-in medical disclaimer and escalation logic |
| 🎤 **Voice Input** | Speak naturally to interact with the AI Nutrition Agent using speech-to-text |
| 📷 **Food Image Analysis** | Upload food images for nutrition analysis with a user-assisted fallback when automatic recognition is unavailable |
| 🤖 **IBM BOB Agent** | AI agent built using IBM BOB for orchestrating personalized nutrition recommendations and user interactions. |


---

## 🗂️ Project Structure

```
Nutrition/
├── app.py                  ← Main Flask backend + AGENT_INSTRUCTIONS
├── templates/
│   └── index.html          ← Full-featured frontend (chat, dashboard, BMI, meal plan, profiles)
├── requirements.txt        ← Python dependencies
├── .env.template           ← Credential template (copy → .env)
├── README.md               ← This file
└── .gitignore
```

---

## 🚀 Quick Start

### 1. Clone & enter the project

```bash
cd /path/to/Nutrition
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure credentials

```bash
cp .env.template .env
```

Edit `.env` and fill in:

```dotenv
IBM_API_KEY=your_ibm_cloud_api_key_here
WATSONX_PROJECT_ID=your_watsonx_project_id_here
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-3-3-8b-instruct
FLASK_SECRET_KEY=generate_a_random_string_here
FLASK_ENV=development
PORT=8080
```

### 5. Run the app

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

---

## 🔑 Getting IBM Watsonx.ai Credentials

1. Sign up / log in at [cloud.ibm.com](https://cloud.ibm.com)
2. Create a **Watsonx.ai** service instance
3. Go to **Manage → Access (IAM) → API Keys** → create a new API key
4. Open your Watsonx.ai project → Settings → copy the **Project ID**
5. Paste both values into your `.env` file

> **Note**: The app runs in **demo mode** with helpful mock responses when no credentials are configured — great for UI testing.

> **Image Upload Note:** The application supports food image uploads for nutrition analysis. When automatic food recognition is unavailable in the current IBM Cloud Lite deployment, users can manually enter the detected food name to receive AI-powered nutrition analysis, contextual explanations, and personalized recommendations.
---

## 🧠 Customising the AI Agent

All agent behaviour is controlled through the `AGENT_INSTRUCTIONS` dictionary at the top of [`app.py`](app.py). You never need to touch the routing or AI logic — just edit this dict.

```python
AGENT_INSTRUCTIONS = {
    "persona": {
        "name": "NutriBot",
        "tone": "warm, encouraging, and science-backed",
        # Change the greeting shown at chat startup
        "greeting": "Hello! I'm NutriBot 🥗 ..."
    },
    "diet_specializations": [
        "Indian vegetarian and vegan diets",
        "Diabetic-friendly meal planning",
        # Add your own specialisations here
    ],
    "safety_rules": [
        "Always recommend consulting a doctor for medical conditions.",
        # Add custom safety constraints here
    ],
    "response_style": {
        "language": "English",
        "max_response_length": "150–350 words",
        "include_calorie_estimates": True,
    },
    "indian_food_preferences": {
        "staples": ["dal", "roti", "rice", ...],
        # Customise preferred ingredients, snacks, cuisines
    },
    "family_support": {
        "approach": "Generate a combined family meal plan ...",
        "shared_meals": True,
    }
}
```

---

## 🌐 Available API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/` | Main web UI |
| `POST` | `/api/chat` | Send message, get AI reply |
| `POST` | `/api/profile` | Save/update a profile |
| `GET`  | `/api/profile` | Get all family profiles |
| `POST` | `/api/bmi` | Calculate BMI |
| `POST` | `/api/tdee` | Calculate TDEE + macros |
| `POST` | `/api/meal-plan` | Generate AI meal plan |
| `GET`  | `/api/nutrition-tips` | Get daily nutrition tips |
| `POST` | `/api/clear-chat` | Clear chat history |
| `GET`  | `/api/health` | Health check / status |

---

## 🤖 IBM Technologies Used

- IBM watsonx.ai
- IBM Granite / Foundation Models
- IBM BOB
- IBM Cloud Lite
- IBM IAM Authentication

---

## 📦 Production Deployment

### Option A — Gunicorn (Linux/macOS)

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Option B — Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
```

Build & run:
```bash
docker build -t nutrition-agent .
docker run -p 5000:5000 --env-file .env nutrition-agent
```

### Option C — IBM Code Engine / Cloud Foundry

```bash
# IBM Cloud Code Engine
ibmcloud ce app create --name nutrition-agent \
  --image us.icr.io/yourns/nutrition-agent \
  --env-from-secret nutrition-secrets
```

### Environment variables for production

```dotenv
FLASK_ENV=production
FLASK_SECRET_KEY=<strong-random-secret>   # python -c "import secrets; print(secrets.token_hex(32))"
IBM_API_KEY=<your-key>
WATSONX_PROJECT_ID=<your-project-id>
```

---

## 🔒 Security Notes

- `.env` is listed in `.gitignore` — **never commit it**
- Session data is stored server-side (Flask session with secret key)
- All user inputs are HTML-escaped in the frontend
- API keys are loaded only from environment variables (never hardcoded)

---

## 📝 Requirements

- Python 3.10+
- IBM Cloud account with Watsonx.ai access
- Modern browser (Chrome, Firefox, Safari, Edge)

---

## 📄 License

MIT — free to use, modify, and distribute.

---

*Built with ❤️ using IBM Watsonx.ai · IBM Granite · IBM BOB · Flask · Bootstrap 5*
