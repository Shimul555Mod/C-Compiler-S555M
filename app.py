# ----------[app.py]----------
import os
import stat
import subprocess
import uuid
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# একটি অপ্রত্যাশিত সার্ভার এরর হ্যান্ডেল করার জন্য
@app.errorhandler(Exception)
def handle_exception(e):
    # ডিবাগিংয়ের জন্য সার্ভার কনসোলে সম্পূর্ণ এরর প্রিন্ট করা হবে
    print(f"Unhandled Exception: {e}") 
    response = {
        "error": f"সার্ভারে একটি অপ্রত্যাশিত সমস্যা হয়েছে। অনুগ্রহ করে কিছুক্ষণ পর আবার চেষ্টা করুন।"
    }
    return jsonify(response), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/compile', methods=['POST'])
def compile_code():
    data = request.get_json()
    code = data.get('code', '')
    user_input = data.get('input', '')
    c_standard = data.get('standard', 'c17') # ডিফল্ট C17
    warnings = data.get('warnings', '-Wall') # ডিফল্ট -Wall

    if not code.strip():
        return jsonify({'error': 'কোড লেখার বক্সটি খালি। অনুগ্রহ করে C কোড লিখুন।'}), 400

    # অনুমোদিত স্ট্যান্ডার্ড এবং ওয়ার্নিং ফ্ল্যাগের একটি তালিকা তৈরি করা হয়েছে
    # এটি নিরাপত্তা বাড়াতে সাহায্য করবে (Command Injection প্রতিরোধ)
    allowed_standards = ['c89', 'c99', 'c11', 'c17', 'c2x']
    allowed_warnings = ['-Wall', '-Wextra', '-Wpedantic', '-w']

    if c_standard not in allowed_standards or warnings not in allowed_warnings:
        return jsonify({'error': 'অবৈধ কম্পাইলেশন ফ্ল্যাগ ব্যবহার করা হয়েছে।'}), 400

    # Termux-এর home ডিরেক্টরির পরিবর্তে /tmp ব্যবহার করা হচ্ছে, যা আরও নিরাপদ
    temp_dir = '/dev/shm' if os.path.exists('/dev/shm') else '/tmp'
    unique_id = str(uuid.uuid4())
    source_file = os.path.join(temp_dir, f'{unique_id}.c')
    output_file = os.path.join(temp_dir, unique_id)
    
    try:
        with open(source_file, 'w', encoding='utf-8') as f:
            f.write(code)

        # ব্যবহারকারীর নির্বাচিত অপশন দিয়ে কম্পাইল কমান্ড তৈরি
        compile_command = ['clang', f'-std={c_standard}', warnings, source_file, '-o', output_file, '-lm']
        
        compile_process = subprocess.run(
            compile_command, 
            capture_output=True, 
            text=True,
            timeout=10 # কম্পাইলেশনের জন্য ১০ সেকেন্ড সময়সীমা
        )

        # যদি কম্পাইলেশনে কোনো এরর থাকে
        if compile_process.returncode != 0:
            # কম্পাইলেশন এররকে stderr থেকে আলাদা করে দেখানো হচ্ছে
            return jsonify({'error': f"কম্পাইলেশন এরর:\n\n{compile_process.stderr}"})

        # আউটপুট ফাইলকে এক্সিকিউট করার পারমিশন দেওয়া হচ্ছে
        st = os.stat(output_file)
        os.chmod(output_file, st.st_mode | stat.S_IEXEC)

        # কোড রান করার প্রসেস
        run_process = subprocess.run(
            [output_file],
            input=user_input,
            capture_output=True,
            text=True,
            timeout=15 # রান করার জন্য ১৫ সেকেন্ড সময়সীমা
        )
        
        # আউটপুট এবং রানটাইম এরর (যদি থাকে) একত্রিত করে পাঠানো হচ্ছে
        output = run_process.stdout
        error_output = run_process.stderr
            
        return jsonify({'output': output, 'error': error_output})

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'কোডটি রান হতে অনেক বেশি সময় নিচ্ছে। অসীম লুপ (infinite loop) আছে কিনা তা পরীক্ষা করুন।'})
    
    finally:
        # রান শেষে অস্থায়ী ফাইলগুলো মুছে ফেলা হচ্ছে
        if os.path.exists(source_file):
            os.remove(source_file)
        if os.path.exists(output_file):
            os.remove(output_file)

if __name__ == '__main__':
    # প্রোডাকশনের জন্য host='0.0.0.0' এবং debug=False রাখা উচিত
    app.run(host='0.0.0.0', port=5000)