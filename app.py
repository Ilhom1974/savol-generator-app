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
# --- QISMI TO'LIQ YANGILANDI (TIL MANTIG'I QO'SHILDI) ---
@app.route('/api/generate', methods=['POST'])
def api_generate():
    try:
        # --- Sozlamalarni Form'dan o'qiymiz ---
        q_type = request.form.get('q_type', 'hammasi')
        q_difficulty = request.form.get('q_difficulty', "o'rta")
        q_count = request.form.get('q_count', 5)
        test_format = request.form.get('test_format', 'oddiy')
        output_language = request.form.get('output_language', 'uz') # YANGI TIL PARAMETRI

        print(f"Yangi so'rov: Turi={q_type}, Murakkablik={q_difficulty}, Soni={q_count}, Test Formati={test_format}, Natija Tili={output_language}")

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

        # --- Dinamik Promptni Yaratish (TILGA QARAB) ---

        # Tilga bog'liq matnlar
        if output_language == 'ru':
            lang_instructions = {
                "role": "Вы - ИИ-помощник для преподавателей университетов Узбекистана.",
                "task": "Ваша задача - проанализировать предоставленный текст лекции и сгенерировать вопросы для проверки знаний студентов в соответствии с указанными требованиями.",
                "source_text_header": "ТЕКСТ:",
                "requirements_header": "ТРЕБОВАНИЯ, которые необходимо выполнить:",
                "q_type_label": "1. ТИП ВОПРОСОВ:",
                "difficulty_label": "2. СЛОЖНОСТЬ:",
                "count_label": "3. КОЛИЧЕСТВО ВОПРОСОВ:",
                "test_format_label": "4. ФОРМАТ ТЕСТОВ:",
                "based_on_text": "Все вопросы должны основываться только и исключительно на содержании предоставленного выше текста.",
                "no_reference": "ПРИ СОСТАВЛЕНИИ ВОПРОСОВ НИКОГДА НЕ ИСПОЛЬЗУЙТЕ фразы, прямо ссылающиеся на источник, такие как \"согласно источнику\", \"как сказано в тексте\", \"основываясь на приведенном тексте\". Вопросы должны быть понятны сами по себе, без необходимости читать исходный текст.",
                "output_format_header": "Верните ответ в следующем формате (включайте только запрошенные типы):",
                "final_instruction": f"ВЕСЬ ОТВЕТ ДОЛЖЕН БЫТЬ СГЕНЕРИРОВАН НА РУССКОМ ЯЗЫКЕ.",
                "type_all": "Сгенерируйте смесь теоретических (открытых) и тестовых (закрытых, с вариантами) вопросов.",
                "type_theory": "Сгенерируйте только теоретические (открытые) вопросы. НЕ СОЗДАВАЙТЕ ТЕСТОВЫЕ ВОПРОСЫ.",
                "type_test": "Сгенерируйте только тестовые (закрытые, с вариантами) вопросы. НЕ СОЗДАВАЙТЕ ТЕОРЕТИЧЕСКИЕ ВОПРОСЫ.",
                "difficulty_easy": "Вопросы должны быть легкими, сосредоточенными только на основных терминах и определениях.",
                "difficulty_medium": "Вопросы должны быть средней сложности.",
                "difficulty_hard": "Вопросы должны быть сложными, требующими анализа и сравнения.",
                "count_text": f"Сгенерируйте примерно {q_count} вопросов(а) всего.",
                "format_theory_header": "### I. Теоретические (Открытые) Вопросы",
                "format_test_header": "### II. Тестовые (Закрытые) Вопросы",
                "hemis_instruction": """
        ФОРМАТ ДЛЯ ТЕСТОВЫХ ВОПРОСОВ: Для тестовых вопросов используйте *только* и *строго* следующий специальный формат HEMIS (БЕЗ скобок [ ] вокруг вариантов):

        Текст вопроса 1
        ====
        Вариант А
        ====
        #Правильный вариант ответа
        ====
        Вариант C
        ====
        Вариант D
        ++++
        Текст вопроса 2
        ====
        Вариант А
        ====
        Вариант B
        ====
        #Правильный вариант ответа
        ... и так далее.

        ПРАВИЛА (ОЧЕНЬ ВАЖНО!):
        1. Текст вопроса, каждый вариант и разделитель '====' должны быть на отдельной строке.
        2. Перед правильным вариантом ответа ставьте *только* знак '#'.
        3. Разделяйте блоки вопросов *только* знаком '++++'.
        4. НЕ ИСПОЛЬЗУЙТЕ никакой другой нумерации (1., 2.) или буквенных обозначений (а), б)).
        5. НЕ ИСПОЛЬЗУЙТЕ скобки ([ ]) вокруг вариантов или текста вопроса.
        """,
                "normal_test_format": "ФОРМАТ ДЛЯ ТЕСТОВЫХ ВОПРОСОВ: Создайте тестовые вопросы со стандартными вариантами (а, б, в, г)."
            }
        else: # output_language == 'uz' (Standart)
            lang_instructions = {
                "role": "Siz O'zbekistondagi universitet o'qituvchilari uchun yordamchi AI'siz.",
                "task": "Vazifangiz - taqdim etilgan ma'ruza matnini tahlil qilib, ko'rsatilgan talablar asosida savollar yaratish.",
                "source_text_header": "MATN:",
                "requirements_header": "bajarilishi shart bo'lgan KO'RSATMALAR:",
                "q_type_label": "1. SAVOL TURI:",
                "difficulty_label": "2. MURAKKABLIK:",
                "count_label": "3. SAVOLLAR SONI:",
                "test_format_label": "4. TEST FORMATI:",
                "based_on_text": "Barcha savollar faqat va faqat yuqorida berilgan matn mazmuniga asoslansin.",
                "no_reference": "SAVOLLARNI TUZISHDA HECH QACHON \"manbaga ko'ra\", \"matnda aytilishicha\", \"keltirilgan matnga asoslanib\" kabi manbaga to'g'ridan-to'g'ri ishora qiluvchi iboralarni ISHLATMANG. Savollar mustaqil, manbani o'qimasdan ham tushunarli bo'lsin.",
                "output_format_header": "Javobni quyidagi formatda qaytaring (faqat so'ralgan turlarni kiriting):",
                "final_instruction": "", # O'zbek tili uchun qo'shimcha buyruq shart emas
                "type_all": "Nazariy (ochiq) va Test (yopiq, variantli) savollarni aralash yarating.",
                "type_theory": "Faqat Nazariy (ochiq) savollar yarating. TEST SAVOLLARI YARATMA.",
                "type_test": "Faqat Test (yopiq, variantli) savollar yarating. NAZARIY SAVOLLAR YARATMA.",
                "difficulty_easy": "Savollar oson, faqat asosiy terminlar va ta'riflarga e'tibor qaratsin.",
                "difficulty_medium": "Savollar o'rta murakkablikda bo'lsin.",
                "difficulty_hard": "Savollar qiyin, tahlil qilishni va taqqoslashni talab qiladigan bo'lsin.",
                "count_text": f"Jami taxminan {q_count} ta savol generatsiya qiling.",
                "format_theory_header": "### I. Nazariy (Ochiq) Savollar",
                "format_test_header": "### II. Test (Yopiq) Savollari",
                "hemis_instruction": """
        TEST SAVOLLARI UCHUN FORMAT: Test savollari uchun *faqat* va *aniq* quyidagi maxsus HEMIS formatidan foydalan (variantlar atrofida [ ] belgilari BO'LMASIN):

        Savol matni 1
        ====
        Variant A
        ====
        #To'g'ri javob varianti
        ====
        Variant C
        ====
        Variant D
        ++++
        Savol matni 2
        ====
        Variant A
        ====
        Variant B
        ====
        #To'g'ri javob varianti
        ... va hokazo.

        QOIDALAR (JUDA MUHIM!):
        1. Savol matni, har bir variant va '====' bo'luvchisi alohida qatorda bo'lsin.
        2. To'g'ri javob variantidan oldin faqat '#' belgisi ishlatilsin.
        3. Har bir savol bloki orasini faqat '++++' belgisi bilan ajrat.
        4. Boshqa hech qanday raqamlash (1., 2.) yoki (a), b)) kabi harf bilan belgilash ISHLATILMASIN.
        5. Variantlar yoki savol matni atrofida boshqa belgilar ISHLATILMASIN.
        """,
                "normal_test_format": "TEST SAVOLLARI UCHUN FORMAT: Test savollarini standart (a, b, c, d) variantlari bilan yarating."
            }

        # Prompt qismlarini shakllantirish
        type_instruction = ""
        format_instruction = ""
        test_format_instruction = ""

        if q_type != 'faqat_nazariy':
            if test_format == 'hemis':
                test_format_instruction = lang_instructions["hemis_instruction"]
            else:
                test_format_instruction = lang_instructions["normal_test_format"]

        if q_type == 'faqat_nazariy':
            type_instruction = lang_instructions["type_theory"]
            format_instruction = lang_instructions["format_theory_header"]
        elif q_type == 'faqat_test':
            type_instruction = lang_instructions["type_test"]
            if test_format == 'hemis' and output_language == 'ru':
                 format_instruction = "" # Rus tilida HEMIS uchun sarlavha yo'q
            elif test_format == 'hemis' and output_language == 'uz':
                 format_instruction = "" # O'zbek tilida HEMIS uchun sarlavha yo'q
            else:
                format_instruction = lang_instructions["format_test_header"]
        else: # 'hammasi'
            type_instruction = lang_instructions["type_all"]
            if test_format == 'hemis':
                 # HEMIS formatida testlar boshlanishidan oldin nazariy savollar sarlavhasi
                 format_instruction = f"{lang_instructions['format_theory_header']}\n\n({lang_instructions['role'].split('.')[0]}, {lang_instructions['task'].split('.')[0].lower()}dan keyin, yangi qatordan HEMIS formatidagi testlarni joylashtiring)" # Ruscha/O'zbekcha moslashuv
            else:
                format_instruction = f"{lang_instructions['format_theory_header']}\n\n{lang_instructions['format_test_header']}"

        difficulty_instruction = lang_instructions.get(f"difficulty_{q_difficulty}", lang_instructions["difficulty_medium"])
        count_instruction = lang_instructions["count_text"]

        # --- YAKUNIY PROMPT (TILGA MOSLASHTIRILGAN) ---
        prompt = f"""{lang_instructions["role"]}
{lang_instructions["task"]}

{lang_instructions["source_text_header"]}
---
{lecture_text}
---

{lang_instructions["requirements_header"]}
{lang_instructions["q_type_label"]} {type_instruction}
{lang_instructions["difficulty_label"]} {difficulty_instruction}
{lang_instructions["count_label"]} {count_instruction}
{lang_instructions["test_format_label"]} {test_format_instruction}

{lang_instructions["based_on_text"]}
{lang_instructions["no_reference"]}
{lang_instructions["output_format_header"]}
{format_instruction}

{lang_instructions["final_instruction"]}
        """
        # -------------------------------

        response = model.generate_content(prompt)
        return jsonify({"questions": response.text})

    except Exception as e:
        print(f"Generatsiya xatoligi: {e}")
        # Batafsilroq xato xabarini ko'rsatish (ishlab chiqish uchun foydali)
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": f"Model bilan ishlashda kutilmagan xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring."}), 500
