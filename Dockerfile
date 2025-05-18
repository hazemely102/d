# استخدم صورة بايثون رسمية كنقطة انطلاق
FROM python:3.11-slim

# تعيين دليل العمل داخل الحاوية
WORKDIR /app

# نسخ ملف المتطلبات أولاً للاستفادة من التخزين المؤقت لطبقات Docker
COPY requirements.txt .

# تثبيت أي تبعيات نظام قد تحتاجها بعض مكتبات بايثون (إذا لزم الأمر)
# RUN apt-get update && apt-get install -y --no-install-recommends some-package && rm -rf /var/lib/apt/lists/*

# تثبيت تبعيات بايثون
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي كود التطبيق إلى دليل العمل
COPY . .

# تعيين متغيرات البيئة التي قد يحتاجها التطبيق (Gunicorn سيستخدم PORT)
# Render سيوفر متغير PORT تلقائيًا
ENV PORT 8080
# يمكنك إضافة متغيرات أخرى هنا إذا أردت، لكن من الأفضل إدارتها عبر واجهة Render
# ENV TELEGRAM_BOT_TOKEN your_token_here # لا تفعل هذا! استخدم متغيرات بيئة Render

# تحديد البورت الذي سيستمع عليه التطبيق داخل الحاوية
EXPOSE 8080

# الأمر الافتراضي لتشغيل التطبيق عند بدء الحاوية
# Gunicorn هو خادم WSGI موصى به للإنتاج
# Render سيتجاهل هذا إذا حددت "Start Command" في واجهته،
# ولكن من الجيد وضعه كأمر افتراضي للحاوية.
# استخدم نفس الأمر الذي ستضعه في "Start Command" في Render.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "main:flask_app"]
