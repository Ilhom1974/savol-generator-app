from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import os
import sys
import io

try:
    import docx
except ImportError:
    print("XATOLIK: 'python-docx' kutubxonasi topilmadi.")
    print("Iltimos, terminalda 'pip install python-docx' buyrug'ini ishga tushiring.")
    sys.exit(1)


# Flask ilovasini yaratamiz
app = Flask(__name__)

# --- 1. API Kalitini Sozlash ---
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("XATOLIK: GEMINI_API_KEY tizim o'zgaruvchisi topilmadi.")
    sys.exit(1)

try:
    genai.configure(api_key=API_KEY)
except Exception as e:
    print(f"API kalitini sozlashda xatolik: {e}")
    sys.exit(1)

# --- 2. Modelni Yuklash ---
MODEL_NAME = "models/gemini-flash-latest" 
try:
    model = genai.GenerativeModel(MODEL_NAME)
    print(f"'{MODEL_NAME}' modeli muvaffaqiyatli yuklandi.")
except Exception as e:
    print(f"Modelni yuklashda xatolik: {e}")
    sys.exit(1)


# --- Faylni matnga o'girish funksiyasi (O'zgarishsiz) ---
def get_text_from_file(file_storage):
    filename = file_storage.filename
    if filename.endswith('.docx'):
        try:
            doc = docx.Document(io.BytesIO(file_storage.read()))
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)
            return '\n'.join(full_text)
        except Exception as e:
            raise ValueError(f".docx faylni o'qishda xatolik: {e}")
            
    elif filename.endswith('.txt'):
        try:
            text = file_storage.read().decode('utf-8')
            return text
        except Exception as e:
            raise ValueError(f".txt faylni o'qishda xatolik: {e}")
    else:
        raise ValueError("Faqat .txt va .docx formatidagi fayllar qabul qilinadi.")
# ---------------------------------------------


# --- 3. Asosiy Sahifa (Frontend) (O'zgarishsiz) ---
@app.route('/')
def index():
    return render_template('index.html')


# --- 4. Savol Generatsiya Qiladigan API Yo'nalishi ---
# --- QISMI TO'LIQ YANGILANDI (HEMIS MANTIG'I QO'SHILDI) ---
@app.route('/api/generate', methods=['POST'])
def api_generate():
    try:
        # --- Sozlamalarni Form'dan o'qiymiz ---
        q_type = request.form.get('q_type', 'hammasi')
        q_difficulty = request.form.get('q_difficulty', "o'rta")
        q_count = request.form.get('q_count', 5)
        test_format = request.form.get('test_format', 'oddiy') # YANGI SOZLAMA

        print(f"Yangi so'rov: Turi={q_type}, Murakkablik={q_difficulty}, Soni={q_count}, Test Formati={test_format}")

        lecture_text = ""
        file = request.files.get('file')

        if file and file.filename != '':
            print(f"Fayl qabul qilindi: {file.filename}")
            try:
                lecture_text = get_text_from_file(file)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
        else:
            lecture_text = request.form.get('text')
            if not lecture_text or lecture_text.strip() == "":
                 return jsonify({"error": "Matn taqdim etilmagan"}), 400
            print("Oddiy matn qabul qilindi.")
        
        # --- Dinamik Promptni Yaratish (HEMIS MANTIG'I BILAN) ---
        
        type_instruction = ""
        format_instruction = ""
        test_format_instruction = "" # Test formatini tushuntiradi

        # 1. Test formatini aniqlash (agar test so'ralgan bo'lsa)
        if q_type != 'faqat_nazariy':
            if test_format == 'hemis':
                test_format_instruction = """
        TEST SAVOLLARI UCHUN FORMAT: Test savollari uchun *faqat* va *aniq* quyidagi maxsus HEMIS formatidan foydalaning:
        [Savol matni 1]
        ====
        [Variant A]
        ====
        #[To'g'ri javob varianti]
        ====
        [Variant C]
        ====
        [Variant D]
        ++++
        [Savol matni 2]
        ====
        [Variant A]
        ====
        [Variant B]
        ====
        #[To'g'ri javob varianti]
        ... va hokazo.
        
        QOIDALAR (JUDA MUHIM!):
        1. Har bir savol, javob va bo'luvchi '====' o'z alohida qatorida bo'lsin.
        2. To'g'ri javob variantidan oldin *faqat* '#' belgisini qo'ying (boshqa belgi yo'q).
        3. Har bir savol bloki orasini *faqat* '++++' belgisi bilan ajrating.
        4. Boshqa hech qanday raqamlash (1., 2.) yoki harf belgilash (a), b)) ISHLATMANG.
        """
            else: # 'oddiy' format
                test_format_instruction = "TEST SAVOLLARI UCHUN FORMAT: Test savollarini standart (a, b, c, d) variantlari bilan yarating."

        # 2. Savol turini va Yakuniy Formatni aniqlash
        if q_type == 'faqat_nazariy':
            type_instruction = "Faqat Nazariy (ochiq) savollar yarating. TEST SAVOLLARI YARATMA."
            format_instruction = "### I. Nazariy (Ochiq) Savollar"
        
        elif q_type == 'faqat_test':
            type_instruction = "Faqat Test (yopiq, variantli) savollar yarating. NAZARIY SAVOLLAR YARATMA."
            if test_format == 'hemis':
                format_instruction = "" # Sarlavha kerak emas, to'g'ridan-to'g'ri HEMIS formatni boshlasin
            else:
                format_instruction = "### II. Test (Yopiq) Savollari"
        
        else: # 'hammasi' (aralash)
            type_instruction = "Nazariy (ochiq) va Test (yopiq, variantli) savollarni aralash yarating."
            if test_format == 'hemis':
                format_instruction = "### I. Nazariy (Ochiq) Savollar\n\n(Nazariy savollardan keyin, yangi qatordan HEMIS formatidagi testlarni joylashtiring)"
            else:
                format_instruction = "### I. Nazariy (Ochiq) Savollar\n\n### II. Test (Yopiq) Savollari"
        
        # 3. Murakkablik bo'yicha ko'rsatma (o'zgarishsiz)
        if q_difficulty == 'oson':
            difficulty_instruction = "Savollar oson, faqat asosiy terminlar va ta'riflarga e'tibor qaratsin."
        elif q_difficulty == 'qiyin':
            difficulty_instruction = "Savollar qiyin, tahlil qilishni va taqqoslashni talab qiladigan bo'lsin."
        else:
            difficulty_instruction = "Savollar o'rta murakkablikda bo'lsin."

        # 4. Son bo'yicha ko'rsatma (o'zgarishsiz)
        count_instruction = f"Jami taxminan {q_count} ta savol generatsiya qiling."

        # --- YAKUNIY PROMPT ---
        prompt = f"""
        Siz O'zbekistondagi universitet o'qituvchilari uchun yordamchi AI'siz. 
        Vazifangiz - taqdim etilgan ma'ruza matnini tahlil qilib, ko'rsatilgan talablar asosida savollar yaratish.

        MATN:
        ---
        {lecture_text}
        ---

         bajarilishi shart bo'lgan KO'RSATMALAR:
        1. SAVOL TURI: {type_instruction}
        2. MURAKKABLIK: {difficulty_instruction}
        3. SAVOLLAR SONI: {count_instruction}
        4. {test_format_instruction}
        
        Barcha savollar faqat va faqat yuqorida berilgan matn mazmuniga asoslansin.
        Javobni quyidagi formatda qaytaring (agar sarlavha ko'rsatilgan bo'lsa, unga rioya qiling, agar HEMIS formati so'ralgan bo'lsa, faqat o'sha formatni qaytaring):
        {format_instruction}
        """
        # -------------------------------
        
        response = model.generate_content(prompt)
        
        return jsonify({"questions": response.text})

    except Exception as e:
        print(f"Generatsiya xatoligi: {e}")
        return jsonify({"error": f"Model bilan ishlashda xatolik: {str(e)}"}), 500