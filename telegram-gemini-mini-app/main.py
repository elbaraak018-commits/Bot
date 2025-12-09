from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from fastapi.responses import HTMLResponse

# --- الإعداد الأولي ---

app = FastAPI()

# ⚠️ إعداد CORS: السماح بالوصول من أي مكان (ضروري لتطبيقات الويب المصغرة)
origins = ["*"] 

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# إعداد Gemini Client
# يبحث تلقائيًا عن مفتاح GEMINI_API_KEY في متغيرات البيئة (التي ستضيفها في Render)
try:
    client = genai.Client()
    model = 'gemini-2.5-flash' 
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    client = None

# نموذج البيانات المتوقع استقبالها
class ChatRequest(BaseModel):
    message: str

# --- نقاط النهاية (Endpoints) ---

# نقطة النهاية الرئيسية: لعرض الواجهة الأمامية (ملف index.html)
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """يعرض ملف index.html للواجهة الأمامية."""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Frontend file not found! Please check index.html path.</h1>", status_code=404)


# نقطة نهاية API للدردشة
@app.post("/api/chat")
async def chat_handler(request: ChatRequest):
    """يتلقى رسالة المستخدم ويرسلها إلى Gemini API للحصول على الرد."""
    if not client:
        raise HTTPException(status_code=500, detail="Gemini API is not initialized. Check your GEMINI_API_KEY.")

    try:
        # إرسال الرسالة إلى نموذج Gemini
        response = client.models.generate_content(
            model=model,
            contents=request.message
        )
        
        # إرجاع الرد
        return {"response": response.text}

    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        raise HTTPException(status_code=500, detail="Failed to communicate with AI model. Check logs.")
