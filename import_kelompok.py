
import os
import shutil
from datetime import datetime

import pandas as pd

from app import app
from database import db
from app.models import (
    MataKuliah,
    KelompokPilihan,
    AnggotaKelompokPilihan
)


FILE_EXCEL = "datasetMatakuliah.xlsx"


def bersihkan(nilai):
    if pd.isna(nilai):
        return ""
    return str(nilai).strip()


def import_kelompok_pilihan():
    if not os.path.exists(FILE_EXCEL):
        print("File Excel tidak ditemukan:", FILE_EXCEL)
        return

    # Membaca sheet kelompok pilihan
    data = pd.read_excel(
        FILE_EXCEL,
        sheet_name="Kelompok Pilihan"
    )

    kolom_wajib = [
        "kelompok_id",
        "prodi",
        "semester",
        "nama_kelompok",
        "jumlah_wajib_dipilih",
        "kode"
    ]

    if not all(kolom in data.columns for kolom in kolom_wajib):
        print("Kolom Excel tidak sesuai.")
        print("Kolom ditemukan:", list(data.columns))
        return

    # Membersihkan data
    for kolom in ["kelompok_id", "prodi", "nama_kelompok", "kode"]:
        data[kolom] = data[kolom].map(bersihkan)

    if (
        (data["kelompok_id"] == "").any()
        or (data["prodi"] == "").any()
        or (data["nama_kelompok"] == "").any()
        or (data["kode"] == "").any()
    ):
        print("Ada data kelompok atau kode mata kuliah yang kosong.")
        return

    # Validasi sebelum database diubah
    with app.app_context():
        try:
            kode_excel = set(data["kode"])

            kode_database = {
                matkul.kode
                for matkul in MataKuliah.query.all()
            }

            kode_tidak_ada = sorted(kode_excel - kode_database)

            if kode_tidak_ada:
                print("Kode mata kuliah tidak ditemukan di database:")
                print(kode_tidak_ada)
                return

            # Backup database
            uri = app.config["SQLALCHEMY_DATABASE_URI"]

            if not uri.startswith("sqlite:///"):
                print("Backup otomatis hanya mendukung SQLite.")
                return

            nama_db = uri.replace("sqlite:///", "", 1)

            if not os.path.isabs(nama_db):
                nama_db = os.path.join(app.instance_path, nama_db)

            if os.path.exists(nama_db):
                backup = nama_db + "." + datetime.now().strftime(
                    "%Y%m%d_%H%M%S"
                ) + ".bak"

                shutil.copy2(nama_db, backup)
                print("Backup database dibuat:", backup)

            # 1. Membuat kelompok yang belum ada
            kelompok_db = {}
            jumlah_kelompok_baru = 0

            for _, baris in data.iterrows():
                id_excel = bersihkan(baris["kelompok_id"])
                nama_kelompok = bersihkan(baris["nama_kelompok"])
                prodi = bersihkan(baris["prodi"])

                try:
                    semester = int(baris["semester"])
                except (ValueError, TypeError):
                    raise ValueError(
                        f"Semester tidak valid: {id_excel}"
                    )

                matkul = MataKuliah.query.filter_by(
                    kode=bersihkan(baris["kode"])
                ).first()

                if matkul is None:
                    raise ValueError(
                        f"Mata kuliah tidak ditemukan: {baris['kode']}"
                    )

                # ID Excel membantu membedakan kelompok
                kunci = (
                    id_excel,
                    nama_kelompok,
                    matkul.fakultas,
                    prodi,
                    semester
                )

                if kunci in kelompok_db:
                    continue

                kelompok = KelompokPilihan.query.filter_by(
                    nama_kelompok=nama_kelompok,
                    fakultas=matkul.fakultas,
                    prodi=prodi,
                    semester=semester
                ).first()

                if kelompok is None:
                    kelompok = KelompokPilihan(
                        nama_kelompok=nama_kelompok,
                        fakultas=matkul.fakultas,
                        prodi=prodi,
                        semester=semester
                    )

                    db.session.add(kelompok)
                    db.session.flush()
                    jumlah_kelompok_baru += 1

                jumlah = baris["jumlah_wajib_dipilih"]

                if pd.notna(jumlah):
                    jumlah = int(jumlah)

                    if jumlah > 0:
                        kelompok.jumlah_wajib_dipilih = jumlah

                kelompok_db[kunci] = kelompok

            db.session.flush()

            # 2. Menghubungkan mata kuliah ke kelompok
            jumlah_anggota_baru = 0

            for _, baris in data.iterrows():
                id_excel = bersihkan(baris["kelompok_id"])
                nama_kelompok = bersihkan(baris["nama_kelompok"])
                prodi = bersihkan(baris["prodi"])
                kode = bersihkan(baris["kode"])
                semester = int(baris["semester"])

                matkul = MataKuliah.query.filter_by(
                    kode=kode
                ).first()

                kunci = (
                    id_excel,
                    nama_kelompok,
                    matkul.fakultas,
                    prodi,
                    semester
                )

                kelompok = kelompok_db[kunci]

                anggota = AnggotaKelompokPilihan.query.filter_by(
                    kelompok_id=kelompok.id,
                    kode_matkul=kode
                ).first()

                if anggota is None:
                    db.session.add(
                        AnggotaKelompokPilihan(
                            kelompok_id=kelompok.id,
                            kode_matkul=kode
                        )
                    )
                    jumlah_anggota_baru += 1

            # 3. Menyimpan seluruh perubahan
            db.session.commit()

            print("\nIMPORT KELOMPOK PILIHAN BERHASIL!")
            print("Kelompok baru ditambahkan:", jumlah_kelompok_baru)
            print("Anggota baru ditambahkan:", jumlah_anggota_baru)
            print(
                "Total kelompok dalam database:",
                KelompokPilihan.query.count()
            )
            print(
                "Total anggota kelompok:",
                AnggotaKelompokPilihan.query.count()
            )

        except Exception as error:
            db.session.rollback()
            print("IMPORT GAGAL:", error)


if __name__ == "__main__":
    import_kelompok_pilihan()
