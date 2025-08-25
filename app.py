import os
import stat # <- পারমিশন পরিবর্তনের জন্য নতুন মডিউল ইম্পোর্ট করা হলো
import subprocess
import uuid
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

@app.errorhandler(Exception)
def handle_exception(e):
    response = {
        "error": f"সার্ভারে একটি অপ্রত্যাশিত সমস্যা হয়েছে: {str(e)}"
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

    if not code.strip():
        return jsonify({'error': 'কোড লেখার বক্সটি খালি। অনুগ্রহ করে C কোড লিখুন।'}), 400

    # Termux-এর home ডিরেক্টরির ভেতরে একটি নিরাপদ পাথ তৈরি করা হচ্ছে
    # যাতে পারমিশন সংক্রান্ত সমস্যা এড়ানো যায়।
    # HOME এনভায়রনমেন্ট ভ্যারিয়েবল থেকে পাথ নেওয়া হচ্ছে।
    home_dir = os.environ.get('HOME', '.')
    unique_id = str(uuid.uuid4())
    source_file = os.path.join(home_dir, f'{unique_id}.c')
    output_file = os.path.join(home_dir, unique_id)
    
    try:
        with open(source_file, 'w', encoding='utf-8') as f:
            f.write(code)

        compile_command = ['clang', '-Wall', source_file, '-o', output_file, '-lm']
        
        compile_process = subprocess.run(
            compile_command, 
            capture_output=True, 
            text=True,
            timeout=10
        )

        if compile_process.returncode != 0:
            return jsonify({'error': f"কম্পাইলেশন এরর:\n\n{compile_process.stderr}"})

        # ======================= মূল সমাধান এখানে =======================
        # তৈরি হওয়া আউটপুট ফাইলটিকে এক্সিকিউট করার পারমিশন দেওয়া হচ্ছে।
        # os.chmod() ফাংশন ফাইলের মোড পরিবর্তন করে।
        # stat.S_IEXEC ফ্ল্যাগটি এক্সিকিউট পারমিশন যোগ করে।
        st = os.stat(output_file)
        os.chmod(output_file, st.st_mode | stat.S_IEXEC)
        # =============================================================

        run_process = subprocess.run(
            [output_file], # সরাসরি পাথ ব্যবহার করা হচ্ছে
            input=user_input,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        final_output = run_process.stdout
        if run_process.stderr:
            final_output += f"\nরানটাইম এরর (stderr):\n{run_process.stderr}"
            
        return jsonify({'output': final_output})

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'কোডটি রান হতে অনেক বেশি সময় নিচ্ছে। অসীম লুপ (infinite loop) আছে কিনা তা পরীক্ষা করুন।'})
    
    finally:
        if os.path.exists(source_file):
            os.remove(source_file)
        if os.path.exists(output_file):
            os.remove(output_file)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)