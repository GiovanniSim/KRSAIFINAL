
import os
import shutil
from datetime import datetime

import pandas as pd

from app import app
from database import db
from app.models import MataKuliah, PrasyaratMatkul


FILE_EXCEL = "datasetMatakuliah.xlsx"


def bersihkan(nilai):
    if pd.isna(nilai):
        return ""
    return str(nilai).strip()


def import_matkul():
    if not os.path.exists(FILE_EXCEL):
        print("File Excel tidak ditemukan:", FILE_EXCEL)
        return

    # Membaca sheet mata kuliah
    data = pd.read_excel(
        FILE_EXCEL,
        sheet_name="Mata Kuliah"
    )

    kolom_wajib = [
        "kode", "matkul", "sks", "semester",
        "fakultas", "prodi", "prasyarat"
    ]

    if not all(kolom in data.columns for kolom in kolom_wajib):
        print("Kolom Excel tidak sesuai dengan yang dibutuhkan.")
        print("Kolom yang ditemukan:", list(data.columns))
        return

    # Validasi kode sebelum menyentuh database
    data["kode"] = data["kode"].map(bersihkan)

    if (data["kode"] == "").any():
        print("Ada kode mata kuliah yang kosong.")
        return

    if data["kode"].duplicated().any():
        print("Ada kode mata kuliah duplikat.")
        print(data[data["kode"].duplicated(keep=False)]["kode"])
        return

    with app.app_context():
        # Backup database jika file SQLite ditemukan
        uri = app.config["SQLALCHEMY_DATABASE_URI"]
        nama_db = uri.replace("sqlite:///", "", 1)

        if not os.path.isabs(nama_db):
            nama_db = os.path.join(app.instance_path, nama_db)

        if os.path.exists(nama_db):
            backup = nama_db + "." + datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            ) + ".bak"
            shutil.copy2(nama_db, backup)
            print("Backup database dibuat:", backup)

        kode_tersedia = set(data["kode"])
        kode_prasyarat_tidak_cocok = []

        try:
            # 1. Import mata kuliah
            for _, baris in data.iterrows():
                kode = bersihkan(baris["kode"])
                nama = bersihkan(baris["matkul"])
                fakultas = bersihkan(baris["fakultas"])
                prodi = bersihkan(baris["prodi"])

                try:
                    sks = int(baris["sks"])
                    semester = int(baris["semester"])
                except (ValueError, TypeError):
                    raise ValueError(
                        f"SKS/semester tidak valid untuk {kode}"
                    )

                if (
                    not nama
                    or not fakultas
                    or not prodi
                    or sks <= 0
                    or semester <= 0
                ):
                    raise ValueError(
                        f"Data tidak lengkap atau tidak valid: {kode}"
                    )

                matkul = MataKuliah.query.filter_by(
                    kode=kode
                ).first()

                if matkul is None:
                    matkul = MataKuliah(kode=kode)
                    db.session.add(matkul)

                matkul.matkul = nama
                matkul.sks = sks
                matkul.semester = semester
                matkul.fakultas = fakultas
                matkul.prodi = prodi
                # Minimal SKS dikosongkan dulu
                matkul.minimal_sks = None

            db.session.flush()

            # 2. Ganti prasyarat hanya untuk mata kuliah
            # yang terdapat di file Excel ini.
            PrasyaratMatkul.query.filter(
                PrasyaratMatkul.kode_matkul.in_(
                    list(kode_tersedia)
                )
            ).delete(synchronize_session=False)

            for _, baris in data.iterrows():
                kode_matkul = bersihkan(baris["kode"])
                teks_prasyarat = bersihkan(baris["prasyarat"])

                if not teks_prasyarat:
                    continue

                daftar_prasyarat = (
                    teks_prasyarat.replace(";", ",").split(",")
                )

                for kode_pra in daftar_prasyarat:
                    kode_pra = kode_pra.strip()

                    if not kode_pra:
                        continue

                    if kode_pra not in kode_tersedia:
                        kode_prasyarat_tidak_cocok.append(
                            f"{kode_matkul} -> {kode_pra}"
                        )
                        continue

                    if kode_pra == kode_matkul:
                        kode_prasyarat_tidak_cocok.append(
                            f"{kode_matkul} -> dirinya sendiri"
                        )
                        continue

                    db.session.add(
                        PrasyaratMatkul(
                            kode_matkul=kode_matkul,
                            kode_prasyarat=kode_pra
                        )
                    )

            db.session.commit()

            print("\nIMPORT BERHASIL!")
            print("Jumlah baris mata kuliah:", len(data))

            jumlah_db = MataKuliah.query.count()
            print("Total mata kuliah dalam database:", jumlah_db)

            if kode_prasyarat_tidak_cocok:
                with open(
                    "prasyarat_perlu_dicek.txt",
                    "w",
                    encoding="utf-8"
                ) as file:
                    file.write(
                        "\n".join(kode_prasyarat_tidak_cocok)
                    )

                print(
                    "Ada prasyarat yang belum cocok."
                    " Cek file prasyarat_perlu_dicek.txt"
                )

        except Exception as error:
            db.session.rollback()
            print("IMPORT GAGAL:", error)


if __name__ == "__main__":
    import_matkul()
