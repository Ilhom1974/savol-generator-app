# app.py
# Asosiy veb-ilova fayli. Faqat Flask yo'nalishlari (routes) uchun mas'ul.

import os
import sys
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template

# O'zimizning modullarimizni import qilamiz
try:
    from config import API_KEY_ENV_VAR, MODEL_NAME
    from utils import get_text_from_file, create_dynamic_prompt
except ImportError:
    print("XATOLIK: config.py yoki utils.py fayllari topilmadi.")
    sys.exit(1)

# Flask ilovasini yaratamiz
app = Flask(__name__)

# --- 1. API Kalitini Sozlash ---
API_KEY = os.environ.get(API_KEY_ENV_VAR)
if not API_KEY:
    print(f"XATOLIK: {API_KEY_ENV_VAR} tizim o'zgaruvchisi topilmadi.")
    sys.exit(1)

try:
    genai.configure(api_key=API_KEY)
except Exception as e:
    print(f"API kalitini sozlashda xatolik: {e}")
    sys.exit(1)

# --- 2. Modelni Yuklash ---
try:
    model = genai.GenerativeModel(MODEL_NAME)
    print(f"'{MODEL_NAME}' modeli muvaffaqiyatli yuklandi.")
except Exception as e:
    print(f"Modelni yuklashda xatolik: {e}")
    sys.exit(1)

# --- 3. Asosiy Sahifa (Frontend) uchun Yo'nalish (Route) ---
@app.route('/')
def index():
    """Foydalanuvchiga asosiy 'index.html' sahifasini ko'rsatadi."""
    return render_template('index.html')

# --- 4. Savol Generatsiya Qiladigan API Yo'nalishi (Route) ---
@app.route('/api/generate', methods=['POST'])
def api_generate():
    """Frontenddan ma'lumotlarni qabul qiladi, ularni qayta ishlaydi va natijani qaytaradi."""
    try:
        # Sozlamalarni Form'dan o'qiymiz
        q_type = request.form.get('q_type', 'hammasi')
        q_difficulty = request.form.get('q_difficulty', "o'rta")
        q_count = request.form.get('q_count', 5)
        test_format = request.form.get('test_format', 'oddiy')
        output_language = request.form.get('output_language', 'uz')

        print(f"Yangi so'rov: Til={output_language}, Turi={q_type}, Format={test_format}")

        lecture_text = ""
        file = request.files.get('file')

        if file and file.filename != '':
            # Agar fayl bo'lsa, matnni utils yordamida olamiz
            print(f"Fayl qabul qilindi: {file.filename}")
            try:
                lecture_text = get_text_from_file(file)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
        else:
            # Agar fayl bo'lmasa, matn maydonini tekshiramiz
            lecture_text = request.form.get('text')
            if not lecture_text or lecture_text.strip() == "":
                 return jsonify({"error": "Matn taqdim etilmagan"}), 400
            print("Oddiy matn qabul qilindi.")
        
        # Dinamik promptni utils yordamida yaratamiz
        prompt = create_dynamic_prompt(
            q_type, q_difficulty, q_count, test_format, output_language, lecture_text
        )
        
        # Modelga so'rov yuborish
        response = model.generate_content(prompt)
        
        # Natijani qaytarish
        return jsonify({"questions": response.text})

    except Exception as e:
        print(f"Generatsiya xatoligi: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": f"Model bilan ishlashda kutilmagan xatolik yuz berdi."}), 500

# --- 5. Mahalliy Sinov Uchun Ishga Tushirish ---
#if __name__ == '__main__':
    # Bu qism faqat mahalliy kompyuterda (python app.py) ishga tushirganda ishlaydi
    # Render.com (gunicorn) bu qismni e'tiborsiz qoldiradi.
#    app.run(debug=True, port=5000)
