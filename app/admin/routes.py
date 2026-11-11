from flask import render_template, request, redirect, url_for, session, flash
from app.admin import admin_bp
from database import db
from collections import Counter
from app.models import Mahasiswa, MataKuliah, PrasyaratMatkul, KelompokPilihan, AnggotaKelompokPilihan, ChatSession, ChatMessage, RiwayatNilai


def buat_struktur(mahasiswa):
    hasil = {}

    for m in mahasiswa:
        fakultas = m.fakultas or "Belum ada fakultas"
        prodi = m.prodi or "Belum ada prodi"
        kelas = m.kelas or "Belum ada kelas"

        if fakultas not in hasil:
            hasil[fakultas] = {}

        if prodi not in hasil[fakultas]:
            hasil[fakultas][prodi] = set()

        hasil[fakultas][prodi].add(kelas)

    return [
        {
            "nama": nama_fakultas,
            "prodi": [
                {
                    "nama": nama_prodi,
                    "kelas": sorted(daftar_kelas)
                }
                for nama_prodi, daftar_kelas
                in sorted(daftar_prodi.items())
            ]
        }
        for nama_fakultas, daftar_prodi
        in sorted(hasil.items())
    ]

# Route untuk halaman admin
@admin_bp.route("/")
def admin():
    if "npm" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    # Ambil semua mahasiswa, tanpa akun admin
    semua_mahasiswa = Mahasiswa.query.filter(
        Mahasiswa.role != "admin"
    ).all()

    # Ambil filter dari URL
    fakultas = request.args.get("fakultas", "")
    prodi = request.args.get("prodi", "")
    kelas = request.args.get("kelas", "")

    # Filter tabel mahasiswa
    query = Mahasiswa.query.filter(
        Mahasiswa.role != "admin"
    )

    if fakultas:
        query = query.filter(
            Mahasiswa.fakultas == fakultas
        )

    if prodi:
        query = query.filter(
            Mahasiswa.prodi == prodi
        )

    if kelas:
        query = query.filter(
            Mahasiswa.kelas == kelas
        )

    mahasiswa = query.all()

    # Statistik dihitung dari seluruh mahasiswa
    total_mahasiswa = len(semua_mahasiswa)

    total_fakultas = len(set(
        m.fakultas for m in semua_mahasiswa
        if m.fakultas
    ))

    total_prodi = len(set(
        (m.fakultas, m.prodi)
        for m in semua_mahasiswa
        if m.fakultas and m.prodi
    ))

    total_kelas = len(set(
        (m.fakultas, m.prodi, m.kelas)
        for m in semua_mahasiswa
        if m.fakultas and m.prodi and m.kelas
    ))
    judul_halaman = "Dashboard"
    if fakultas:
        judul_halaman = fakultas

    if prodi:
        judul_halaman = f"{fakultas} — {prodi}"

    if kelas:
        judul_halaman = f"{fakultas} — {prodi} — {kelas}"

    return render_template(
        "admin/dashboard.html",
        mahasiswa=mahasiswa,
        struktur=buat_struktur(semua_mahasiswa),
        judul_halaman=judul_halaman,
        nama_admin=session.get("nama", "Administrator"),
        total_mahasiswa=total_mahasiswa,
        total_fakultas=total_fakultas,
        total_prodi=total_prodi,
        total_kelas=total_kelas,
        filter_fakultas=fakultas,
        filter_prodi=prodi,
        filter_kelas=kelas
    )

# Edit data mahasiswa
@admin_bp.route("/update/<npm>", methods=["POST"])
def admin_update(npm):
    if "npm" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    data = Mahasiswa.query.filter_by(npm=npm).first()

    if data is None or data.role == "admin":
        return "Data mahasiswa tidak ditemukan.", 404

    data.nama = request.form["nama"]
    data.fakultas = request.form["fakultas"]
    data.prodi = request.form["prodi"]
    data.kelas = request.form["kelas"]

    db.session.commit()

    return redirect(url_for("admin.admin"))

# Halaman kelola mata kuliah
@admin_bp.route("/mata-kuliah")
def admin_mata_kuliah():
    if "npm" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    semua_matkul = MataKuliah.query.order_by(
        MataKuliah.semester,
        MataKuliah.kode
    ).all()

    total_per_fakultas = dict(
        Counter(m.fakultas for m in semua_matkul)
    )

    total_per_prodi = dict(
        Counter(
            f"{m.prodi} ({m.fakultas})"
            for m in semua_matkul
        )
    )

    return render_template(
        "admin/mata_kuliah.html",
        semua_matkul=semua_matkul,
        daftar_prasyarat=semua_matkul,
        nama_admin=session.get("nama", "Administrator"),
        total_per_fakultas=total_per_fakultas,
        total_per_prodi=total_per_prodi
    )

@admin_bp.route("/mata-kuliah/tambah", methods=["POST"])
def tambah_matakuliah():
    if "npm" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    kode = request.form.get("kode", "").strip()
    matkul = request.form.get("matkul", "").strip()
    sks = request.form.get("sks", "").strip()
    semester = request.form.get("semester", "").strip()
    fakultas = request.form.get("fakultas", "").strip()
    prodi = request.form.get("prodi", "").strip()

    # Mengambil beberapa pilihan prasyarat dari dropdown
    daftar_prasyarat = list(dict.fromkeys(
        kode_prasyarat.strip()
        for kode_prasyarat in request.form.getlist("prasyarat")
        if kode_prasyarat.strip()
    ))

    if not all([kode, matkul, sks, semester, fakultas, prodi]):
        flash("Semua data wajib diisi.", "error")
        return redirect(url_for("admin.admin_mata_kuliah"))

    if MataKuliah.query.filter_by(kode=kode).first():
        flash("Kode mata kuliah sudah digunakan.", "error")
        return redirect(url_for("admin.admin_mata_kuliah"))

    if kode in daftar_prasyarat:
        flash(
            "Mata kuliah tidak boleh menjadi prasyarat dirinya sendiri.",
            "error"
        )
        return redirect(url_for("admin.admin_mata_kuliah"))

    try:
        sks = int(sks)
        semester = int(semester)

        if sks <= 0 or semester <= 0:
            raise ValueError

    except ValueError:
        flash("SKS dan semester harus berupa angka positif.", "error")
        return redirect(url_for("admin.admin_mata_kuliah"))

    # Memastikan semua kode prasyarat benar-benar tersedia
    if daftar_prasyarat:
        jumlah_valid = MataKuliah.query.filter(
            MataKuliah.kode.in_(daftar_prasyarat)
        ).count()

        if jumlah_valid != len(daftar_prasyarat):
            flash("Ada kode prasyarat yang tidak ditemukan.", "error")
            return redirect(url_for("admin.admin_mata_kuliah"))

    data_baru = MataKuliah(
        kode=kode,
        matkul=matkul,
        sks=sks,
        semester=semester,
        fakultas=fakultas,
        prodi=prodi
    )

    try:
        db.session.add(data_baru)
        db.session.flush()

        for kode_prasyarat in daftar_prasyarat:
            data_prasyarat = PrasyaratMatkul(
                kode_matkul=kode,
                kode_prasyarat=kode_prasyarat
            )
            db.session.add(data_prasyarat)

        db.session.commit()
        flash("Mata kuliah berhasil ditambahkan.", "success")

    except Exception:
        db.session.rollback()
        flash("Gagal menyimpan mata kuliah.", "error")

    return redirect(url_for("admin.admin_mata_kuliah"))

@admin_bp.route("/mata-kuliah/<kode>/edit", methods=["POST"])
def edit_matakuliah(kode):
    # Cek login
    if "npm" not in session:
        return redirect(url_for("login"))

    # Hanya admin yang boleh mengedit
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    matkul = MataKuliah.query.filter_by(kode=kode).first()

    if matkul is None:
        flash("Mata kuliah tidak ditemukan.", "error")
        return redirect(url_for("admin.admin_mata_kuliah"))

    try:
        # Ambil data dari form
        nama = request.form.get("matkul", "").strip()
        fakultas = request.form.get("fakultas", "").strip()
        prodi = request.form.get("prodi", "").strip()

        sks = int(request.form.get("sks", ""))
        semester = int(request.form.get("semester", ""))

        nilai_minimal = request.form.get("minimal_sks", "").strip()
        minimal_sks = int(nilai_minimal) if nilai_minimal else None

        # Validasi data
        if not nama or not fakultas or not prodi:
            raise ValueError("Nama, fakultas, dan prodi wajib diisi.")

        if sks <= 0 or semester <= 0:
            raise ValueError("SKS dan semester harus lebih dari 0.")

        if minimal_sks is not None and minimal_sks <= 0:
            raise ValueError("Minimal SKS harus lebih dari 0.")

        # Ambil pilihan mata kuliah prasyarat dari modal
        daftar_kode = request.form.getlist("prasyarat")

        # Cegah mata kuliah menjadi prasyarat dirinya sendiri
        if kode in daftar_kode:
            raise ValueError(
                "Mata kuliah tidak boleh menjadi prasyarat dirinya sendiri."
            )

        # Pastikan semua kode prasyarat tersedia
        for kode_pra in daftar_kode:
            ada = MataKuliah.query.filter_by(kode=kode_pra).first()

            if ada is None:
                raise ValueError(
                    f"Mata kuliah prasyarat {kode_pra} tidak ditemukan."
                )

        # Perbarui data mata kuliah
        matkul.matkul = nama
        matkul.sks = sks
        matkul.semester = semester
        matkul.fakultas = fakultas
        matkul.prodi = prodi
        matkul.minimal_sks = minimal_sks

        # Ganti daftar prasyarat lama dengan pilihan terbaru
        PrasyaratMatkul.query.filter_by(
            kode_matkul=kode
        ).delete(synchronize_session=False)

        for kode_pra in daftar_kode:
            db.session.add(
                PrasyaratMatkul(
                    kode_matkul=kode,
                    kode_prasyarat=kode_pra
                )
            )

        db.session.commit()
        flash("Data mata kuliah berhasil diperbarui.", "success")

    except ValueError as e:
        db.session.rollback()
        flash(str(e), "error")

    except Exception:
        db.session.rollback()
        flash("Gagal memperbarui data mata kuliah.", "error")

    return redirect(url_for("admin.admin_mata_kuliah"))


# Hapus data mahasiswa beserta seluruh data terkait
@admin_bp.route("/delete/<npm>", methods=["POST"])
def admin_delete(npm):
    if "npm" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    data = Mahasiswa.query.filter_by(npm=npm).first()

    if data is None or data.role == "admin":
        return "Data mahasiswa tidak ditemukan.", 404

    try:
        # 1. Ambil semua sesi chat mahasiswa
        sesi_chat = ChatSession.query.filter_by(npm=npm).all()

        # 2. Hapus semua pesan dalam sesi chat
        for sesi in sesi_chat:
            ChatMessage.query.filter_by(
                session_id=sesi.id
            ).delete(synchronize_session=False)

        # 3. Hapus seluruh sesi chat mahasiswa
        ChatSession.query.filter_by(npm=npm).delete(
            synchronize_session=False
        )

        # 4. Hapus seluruh riwayat nilai mahasiswa
        RiwayatNilai.query.filter_by(npm=npm).delete(
            synchronize_session=False
        )

        # 5. Hapus data mahasiswa
        db.session.delete(data)

        # 6. Simpan semua perubahan
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print("Error menghapus mahasiswa:", e)
        return "Gagal menghapus data mahasiswa.", 500

    return redirect(url_for("admin.admin"))
