        // DOM elementlari
        const generateBtn = document.getElementById('generateBtn');
        const lectureText = document.getElementById('lectureText');
        const manualInputLabel = document.getElementById('manualInputLabel');
        const resultsDiv = document.getElementById('results');
        const loadingDiv = document.getElementById('loading');
        const downloadBtn = document.getElementById('downloadBtn');
        const generationTimeSpan = document.getElementById('generationTime');

        // Sozlamalar
        const qTypeSelect = document.getElementById('q_type');
        const qDifficultySelect = document.getElementById('q_difficulty');
        const qCountInput = document.getElementById('q_count');
        const fileInput = document.getElementById('fileInput');
        const clearFileBtn = document.getElementById('clearFileBtn');
        const testFormatSelect = document.getElementById('test_format');
        const outputLanguageSelect = document.getElementById('output_language');

        // Vaqtni o'lchash va generatsiya
        generateBtn.addEventListener('click', async () => {
            const startTime = performance.now();
            generationTimeSpan.textContent = '';

            const selectedFile = fileInput.files[0];
            const textContent = lectureText.value;
            const selectedLanguage = outputLanguageSelect.value;

            if (!selectedFile && textContent.trim() === "") {
                resultsDiv.innerText = "Iltimos, avval fayl yuklang YOKI matn kiriting.";
                return;
            }

            const formData = new FormData();
            formData.append('q_type', qTypeSelect.value);
            formData.append('q_difficulty', qDifficultySelect.value);
            formData.append('q_count', qCountInput.value);
            formData.append('test_format', testFormatSelect.value);
            formData.append('output_language', selectedLanguage);

            if (selectedFile) {
                formData.append('file', selectedFile);
            } else {
                formData.append('text', textContent);
            }

            resultsDiv.innerText = "";
            resultsDiv.style.display = 'none';
            downloadBtn.style.display = 'none';
            loadingDiv.style.display = 'block';
            generateBtn.disabled = true;

            try {
                const response = await fetch('/api/generate', {
                    method: 'POST',
                    body: formData,
                });
                const data = await response.json();

                if (response.ok) {
                    resultsDiv.innerText = data.questions;
                    downloadBtn.style.display = 'block';
                } else {
                    resultsDiv.innerText = `Serverda xatolik yuz berdi: ${data.error}`;
                }
            } catch (error) {
                resultsDiv.innerText = `Server bilan bog'lanishda kutilmagan xatolik: ${error}. Server ishlayotganiga ishonch hosil qiling.`;
            } finally {
                const endTime = performance.now();
                const timeTaken = ((endTime - startTime) / 1000).toFixed(2);
                generationTimeSpan.textContent = `(${timeTaken} soniya)`;
                loadingDiv.style.display = 'none';
                resultsDiv.style.display = 'block';
                generateBtn.disabled = false;
            }
        });

        // Fayl tanlanganda/tozalanganda UI o'zgarishlari
        fileInput.addEventListener('change', () => {
            const hasFile = fileInput.files.length > 0;
            lectureText.classList.toggle('hidden', hasFile);
            manualInputLabel.classList.toggle('hidden', hasFile);
            clearFileBtn.style.display = hasFile ? 'inline-block' : 'none';
        });
        clearFileBtn.addEventListener('click', () => {
            fileInput.value = null;
            const changeEvent = new Event('change');
            fileInput.dispatchEvent(changeEvent);
        });

        // Savol turi o'zgarganda Test formatini yoqish/o'chirish
        qTypeSelect.addEventListener('change', () => {
            testFormatSelect.disabled = (qTypeSelect.value === 'faqat_nazariy');
        });
        document.addEventListener('DOMContentLoaded', () => {
             testFormatSelect.disabled = (qTypeSelect.value === 'faqat_nazariy');
        });

        // Yuklab olish (fayl nomini so'rash bilan)
        downloadBtn.addEventListener('click', () => {
            const textToSave = resultsDiv.innerText;
            if (!textToSave) return;
            let suggestedName = "savollar.txt";
            if (fileInput.files.length > 0) {
                 const originalFileName = fileInput.files[0].name;
                 suggestedName = originalFileName.substring(0, originalFileName.lastIndexOf('.')) + "_savollar.txt";
            }
            const fileName = prompt("Fayl nomini kiriting:", suggestedName);
            if (fileName === null || fileName.trim() === "") { return; }
            const blob = new Blob([textToSave], { type: 'text/plain;charset=utf-8' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = fileName.endsWith('.txt') ? fileName : fileName + '.txt';
            document.body.appendChild(a); a.click(); document.body.removeChild(a);
            URL.revokeObjectURL(a.href);
        });
