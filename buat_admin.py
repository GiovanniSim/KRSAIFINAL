
from app import app
from database import db
from app.models import Mahasiswa

with app.app_context():
    npm = input("Masukkan NPM admin (angka): ").strip()
    nama = input("Masukkan nama admin: ").strip()
    password = input("Masukkan password admin: ").strip()

    if not npm.isdigit():
        print("NPM harus berupa angka.")
    elif not nama or not password:
        print("Nama dan password tidak boleh kosong.")
    elif Mahasiswa.query.filter_by(npm=int(npm)).first():
        print("NPM sudah terdaftar. Gunakan NPM lain.")
    else:
        admin = Mahasiswa(
            npm=int(npm),
            nama=nama,
            fakultas="Administrator",
            prodi="Administrator",
            kelas="-",
            password=password,
            foto=None,
            role="admin"
        )

        db.session.add(admin)
        db.session.commit()

        print("Akun admin berhasil dibuat!")
        print("NPM:", npm)
