import os
from werkzeug.utils import secure_filename
from flask import render_template, request, redirect, url_for, session
from app import app
from database import db
from app.models import Mahasiswa, MataKuliah, RiwayatNilai, ChatSession, ChatMessage
from app.parse import parse_khs
from app.local_ai import tanya_ai
import json
from app.recomendation import analisis_krs

# LOGIN
@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        npm = request.form["npm"]
        password = request.form["password"]

        mahasiswa = Mahasiswa.query.filter_by(npm=npm).first()

        if mahasiswa and mahasiswa.password == password:

            session["npm"] = mahasiswa.npm
            session["nama"] = mahasiswa.nama
            session["role"] = mahasiswa.role

            if mahasiswa.role == "admin":
                return redirect(url_for("admin.admin"))

            else:
                return redirect(url_for("dashboard"))

        return "NPM atau password salah"

    return render_template("login.html")

# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        npm = request.form["npm"]
        nama = request.form["nama"]
        fakultas = request.form["fakultas"]
        prodi = request.form["prodi"]
        kelas = request.form["kelas"]
        password = request.form["password"]

        # Cek apakah NPM sudah terdaftar
        cek_npm = Mahasiswa.query.filter_by(npm=npm).first()

        if cek_npm:
            return "NPM sudah terdaftar."

        foto = request.files.get("foto")
        nama_foto = None

        if foto and foto.filename != "":
            nama_asli = secure_filename(foto.filename)

            if not nama_asli.lower().endswith((".jpg", ".jpeg")):
                return "Format foto harus JPG/JPEG."

            nama_foto = nama_asli

            folder_foto = os.path.join(
                app.static_folder,
                "uploads",
                "foto"
            )

            os.makedirs(folder_foto, exist_ok=True)

            foto.save(
                os.path.join(folder_foto, nama_foto)
            )

        mahasiswa = Mahasiswa(
            npm=npm,
            nama=nama,
            fakultas=fakultas,
            prodi=prodi,
            kelas=kelas,
            password=password,
            foto="uploads/foto/" + nama_foto if nama_foto else None,
            role="mahasiswa"
        )

        db.session.add(mahasiswa)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")

# DASHBOARD
@app.route("/dashboard")
def dashboard():
    if "npm" not in session:
        return redirect(url_for("login"))

    mahasiswa = Mahasiswa.query.filter_by(
        npm=session["npm"]
    ).first()

    rekomendasi_terakhir = ChatMessage.query.join(
        ChatSession,
        ChatMessage.session_id == ChatSession.id
    ).filter(
        ChatSession.npm == session["npm"],
        ChatMessage.tipe == "recommendation"
    ).order_by(
        ChatMessage.id.desc()
    ).first()

    hasil_rekomendasi = (
        rekomendasi_terakhir.data_hasil
        if rekomendasi_terakhir else None
    )

    return render_template(
        "dashboard.html",
        mahasiswa=mahasiswa,
        hasil_rekomendasi=hasil_rekomendasi,
        rekomendasi_terakhir=rekomendasi_terakhir
    )

# SESI CHAT
@app.route("/chat")
def chat():
    if "npm" not in session:
        return redirect(url_for("login"))

    mahasiswa = Mahasiswa.query.filter_by(
        npm=session["npm"]
    ).first()

    return render_template(
        "sesichat.html",
        mahasiswa=mahasiswa,
        chat_session=None,
        messages=[]
    )

@app.route("/chat", methods=["POST"])
@app.route("/chat/<int:session_id>", methods=["POST"])
def send_message(session_id=None):
    if "npm" not in session:
        return redirect(url_for("login"))

    npm = session["npm"]
    pesan_user = request.form.get("message", "").strip()
    file_khs = request.files.get("khs")
    ada_file = file_khs is not None and file_khs.filename != ""

    if not pesan_user and not ada_file:
        if session_id is not None:
            return redirect(url_for("open_chat", session_id=session_id))
        return redirect(url_for("chat"))

    data_khs = None

    # 1. Validasi dan baca KHS
    if ada_file:
        if not file_khs.filename.lower().endswith(".pdf"):
            return "File harus berformat PDF."

        try:
            data_khs = parse_khs(file_khs)

            if not data_khs.get("riwayat_nilai"):
                return "Tidak ada data nilai yang berhasil dibaca dari PDF."

            if str(data_khs.get("npm")) != str(npm):
                return "NPM pada KHS tidak sesuai dengan akun yang login."

            for item in data_khs["riwayat_nilai"]:
                matkul = MataKuliah.query.filter_by(
                    kode=item["kode_matkul"]
                ).first()

                if not matkul:
                    return (
                        f"Kode mata kuliah {item['kode_matkul']} "
                        "belum terdaftar di database."
                    )

        except Exception as e:
            print("Error membaca KHS:", e)
            return f"Gagal membaca KHS: {e}"

        if not pesan_user:
            pesan_user = "Analisis KHS saya dan rekomendasikan KRS."

    # 2. Buat atau ambil sesi chat
    if session_id is None:
        chat_session = ChatSession(
            npm=npm,
            judul="Analisis KHS" if ada_file else (
                pesan_user[:100] or "Chat Baru"
            )
        )
        db.session.add(chat_session)
        db.session.flush()
    else:
        chat_session = ChatSession.query.filter_by(
            id=session_id,
            npm=npm
        ).first()

        if chat_session is None:
            return "Sesi chat tidak ditemukan.", 404

    try:
        # 3. Simpan pesan pengguna
        pesan_tampil = pesan_user

        if ada_file:
            pesan_tampil += (
                f"\n\n📎 KHS: {secure_filename(file_khs.filename)}"
            )

            # Ganti riwayat lama dengan data KHS terbaru
            RiwayatNilai.query.filter_by(npm=npm).delete()

            for item in data_khs["riwayat_nilai"]:
                db.session.add(RiwayatNilai(
                    npm=npm,
                    kode_matkul=item["kode_matkul"],
                    semester=item["semester"],
                    sks=item["sks"],
                    nilai=item["nilai"],
                    bobot=item["bobot"]
                ))

            # Pastikan riwayat baru tersedia untuk analisis
            db.session.flush()

        db.session.add(ChatMessage(
            session_id=chat_session.id,
            role="user",
            message=pesan_tampil
        ))

        # 4. Upload KHS: hitung dan simpan rekomendasi
        if ada_file:
            hasil = analisis_krs(npm)

            print("DEBUG HASIL:", hasil)
            print("DEBUG JSON:", json.dumps(hasil, ensure_ascii=False))

            # Simpan dashboard rekomendasi ke database
            db.session.add(ChatMessage(
                session_id=chat_session.id,
                role="ai",
                message="",
                tipe="recommendation",
                data_json=json.dumps(
                    hasil,
                    ensure_ascii=False,
                    default=str
                )
            ))

            # AI menjelaskan hasil analisis
            konteks = (
                "Hasil analisis KRS dari sistem:\n"
                + json.dumps(hasil, ensure_ascii=False, default=str)
                + "\nJelaskan hasil ini dengan ramah dalam bahasa Indonesia. "
                "Jangan mengubah angka atau mengarang rekomendasi."
            )

            try:
                jawaban_ai = tanya_ai(
                    pesan_user,
                    konteks_krs=konteks
                )
            except Exception as e:
                print("Error AI lokal:", e)
                jawaban_ai = (
                    "Analisis KHS selesai. Dashboard rekomendasi "
                    "KRS sudah dihitung oleh sistem."
                )


        # 5. Chat teks biasa: tetap gunakan Ollama
        else:
            try:
                jawaban_ai = tanya_ai(pesan_user)
            except Exception as e:
                print("Error AI lokal:", e)
                jawaban_ai = (
                    "Maaf, AI lokal sedang mengalami kendala. "
                    "Pastikan Ollama aktif dan model sudah terpasang."
                )

            db.session.add(ChatMessage(
                session_id=chat_session.id,
                role="ai",
                message=jawaban_ai,
                tipe="text"
            ))

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print("Error memproses chat/KHS:", e)
        return (
            "Gagal memproses chat atau rekomendasi KRS. "
            "Periksa terminal untuk melihat detail kesalahan."
        )

    return redirect(url_for(
        "open_chat",
        session_id=chat_session.id
    ))

@app.route("/chat/<int:session_id>")
def open_chat(session_id):

    if "npm" not in session:
        return redirect(url_for("login"))

    mahasiswa = Mahasiswa.query.filter_by(
        npm=session["npm"]
    ).first()

    chat_session = ChatSession.query.filter_by(
        id=session_id,
        npm=session["npm"]
    ).first()

    if chat_session is None:
        return "Chat tidak ditemukan."

    messages = ChatMessage.query.filter_by(
        session_id=session_id
    ).order_by(
        ChatMessage.id.asc()
    ).all()

    for message in messages:
        print(
            "DEBUG PESAN:",
            message.id,
            message.role,
            message.tipe,
            bool(message.data_json),
            bool(message.data_hasil)
        )

    return render_template(
        "sesichat.html",
        mahasiswa=mahasiswa,
        chat_session=chat_session,
        messages=messages
    )

@app.route("/histori")
def histori():

    if "npm" not in session:
        return redirect(url_for("login"))

    mahasiswa = Mahasiswa.query.filter_by(
        npm=session["npm"]
    ).first()

    chat_sessions = ChatSession.query.filter_by(
        npm=session["npm"]
    ).order_by(
        ChatSession.tanggal.desc()
    ).all()

    return render_template(
        "histori.html",
        mahasiswa=mahasiswa,
        chat_sessions=chat_sessions
    )

@app.route("/edit-data")
def edit_data():
    if "npm" not in session:
        return redirect(url_for("login"))

    return "Halaman Edit Data Mahasiswa"

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))