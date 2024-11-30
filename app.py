from flask import Flask, render_template, request, Response, redirect, url_for
import subprocess
import os
import threading

app = Flask(__name__)
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Lưu trữ process hiện tại
current_process = None
process_lock = threading.Lock()


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        command = request.form.get("command")
        directory = request.form.get("directory")
        if command and directory:
            return redirect(url_for("stream_output", command=command, directory=directory))
    return render_template("index.html")


@app.route("/stream/<path:directory>/<command>")
def stream_output(command, directory):
    def generate():
        global current_process
        try:
            with process_lock:
                if not os.path.isdir(directory):
                    yield f"data: ERROR: Directory {directory} does not exist.\n\n"
                    return

                current_process = subprocess.Popen(
                    command, 
                    shell=True, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True, 
                    cwd=directory  # Chạy lệnh trong thư mục chỉ định
                )
            for line in iter(current_process.stdout.readline, ""):
                yield f"data: {line}\n\n"
            current_process.stdout.close()
            current_process.wait()
            if current_process.returncode != 0:
                for line in iter(current_process.stderr.readline, ""):
                    yield f"data: ERROR: {line}\n\n"
            current_process.stderr.close()
        except Exception as e:
            yield f"data: ERROR: {str(e)}\n\n"
        finally:
            with process_lock:
                current_process = None
            yield "data: Process finished.\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/stop", methods=["POST"])
def stop_process():
    global current_process
    with process_lock:
        if current_process and current_process.poll() is None:  # Kiểm tra nếu process đang chạy
            current_process.terminate()  # Dừng process
            current_process = None
            return "Process terminated", 200
    return "No process to terminate", 400


@app.route("/upload", methods=["POST", "GET"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            return "No file part", 400
        file = request.files["file"]
        if file.filename == "":
            return "No selected file", 400
        file.save(os.path.join(UPLOAD_FOLDER, file.filename))
        return f"File uploaded to {UPLOAD_FOLDER}/{file.filename}", 200
    return render_template("upload.html")


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=2308)

