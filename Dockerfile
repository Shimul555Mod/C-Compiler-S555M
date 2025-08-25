# Step 1: বেস ইমেজ হিসেবে অফিসিয়াল পাইথন 3.11 বেছে নেওয়া হলো
FROM python:3.11-slim

# Step 2: সিস্টেম প্যাকেজ আপডেট করা এবং clang ইনস্টল করা
# এই পরিবেশটি Read-only নয়, তাই এখানে এটি কাজ করবে
RUN apt-get update && apt-get install -y clang

# Step 3: অ্যাপের জন্য একটি ওয়ার্কিং ডিরেক্টরি তৈরি করা
WORKDIR /app

# Step 4: লোকাল ফোল্ডার থেকে সব ফাইল কন্টেইনারের /app ফোল্ডারে কপি করা
COPY . .

# Step 5: পাইথনের প্রয়োজনীয় লাইব্রেরিগুলো ইনস্টল করা
RUN pip install --no-cache-dir -r requirements.txt

# Step 6: অ্যাপটি চালানোর জন্য gunicorn সার্ভার চালু করার কমান্ড
# Render এই কমান্ডটি ব্যবহার করে আপনার অ্যাপ চালাবে
CMD ["gunicorn", "--worker-tmp-dir", "/dev/shm", "--bind", "0.0.0.0:10000", "app:app"]