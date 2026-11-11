from app.models import (
    Mahasiswa,
    MataKuliah,
    PrasyaratMatkul,
    RiwayatNilai,
    AnggotaKelompokPilihan,
)
from sqlalchemy import or_

# BATAS SKS BERDASARKAN IPS
def batas_sks(ips, semester_tujuan):
    if ips < 0 or ips > 4:
        raise ValueError("IPS harus berada di antara 0 sampai 4.")

    # Menentukan jatah SKS berdasarkan IPS
    if ips < 1.50:
        max_sks = 12
    elif ips < 2.00:
        max_sks = 15
    elif ips < 2.50:
        max_sks = 18
    elif ips < 3.00:
        max_sks = 21
    else:
        max_sks = 24

    # Khusus KRS semester 2, maksimal pengambilan 20 SKS
    if semester_tujuan == 2:
        max_sks = min(max_sks, 20)

    return max_sks

# KONVERSI NILAI
def konversi_nilai(nilai):
    nilai = (nilai or "").strip().upper()

    data_nilai = {
        "A": {"bobot": 4, "keterangan": "Baik sekali"},
        "B": {"bobot": 3, "keterangan": "Baik"},
        "C": {"bobot": 2, "keterangan": "Cukup"},
        "D": {"bobot": 1, "keterangan": "Kurang"},
        "E": {"bobot": 0, "keterangan": "Sangat kurang"},
    }

    if nilai not in data_nilai:
        return {
            "bobot": None,
            "keterangan": "Nilai tidak tersedia",
            "status": "Belum diketahui",
        }

    hasil = data_nilai[nilai]

    return {
        "bobot": hasil["bobot"],
        "keterangan": hasil["keterangan"],
        "status": (
            "Lulus" if nilai in ["A", "B", "C"]
            else "Tidak lulus"
        ),
    }


# AMBIL RIWAYAT NILAI MAHASISWA
def ambil_riwayat_mahasiswa(npm):
    riwayat = (
        RiwayatNilai.query
        .filter_by(npm=npm)
        .order_by(
            RiwayatNilai.semester.asc(),
            RiwayatNilai.id.asc()
        )
        .all()
    )

    hasil = []

    for data in riwayat:
        matkul = MataKuliah.query.filter_by(
            kode=data.kode_matkul
        ).first()

        hasil.append({
            "kode_matkul": data.kode_matkul,
            "nama_matkul": (
                matkul.matkul if matkul
                else "Tidak diketahui"
            ),
            "semester": data.semester,
            "sks": data.sks,
            "nilai": data.nilai,
            "bobot": data.bobot,
        })

    return hasil


# HITUNG IPS, IPK, DAN TOTAL SKS LULUS
def hitung_nilai(riwayat):
    if not riwayat:
        return {
            "ips": 0.0,
            "ipk": 0.0,
            "lulus_sks": 0,
            "semester_terakhir": 0,
        }

    semester_terakhir = max(
        data["semester"] for data in riwayat
    )

    total_mutu_ips = 0
    total_sks_ips = 0

    total_mutu_ipk = 0
    total_sks_ipk = 0

    lulus_sks = 0

    for data in riwayat:
        sks = data["sks"]
        nilai = (data["nilai"] or "").strip().upper()
        nilai_mutu = data["bobot"]

        # Total SKS lulus
        if nilai in ["A", "B", "C"]:
            lulus_sks += sks

        # Total IPK seluruh semester
        if nilai_mutu is not None:
            total_mutu_ipk += nilai_mutu
            total_sks_ipk += sks

        # Total IPS semester terakhir
        if data["semester"] == semester_terakhir:
            if nilai_mutu is not None:
                total_mutu_ips += nilai_mutu
                total_sks_ips += sks

    ips = (
        total_mutu_ips / total_sks_ips
        if total_sks_ips else 0.0
    )

    ipk = (
        total_mutu_ipk / total_sks_ipk
        if total_sks_ipk else 0.0
    )

    return {
        "ips": round(ips, 2),
        "ipk": round(ipk, 2),
        "lulus_sks": lulus_sks,
        "semester_terakhir": semester_terakhir,
    }

# PERIKSA PRASYARAT MATA KULIAH
def cek_prasyarat(matkul, kode_lulus):
    prasyarat = PrasyaratMatkul.query.filter_by(
        kode_matkul=matkul.kode
    ).all()

    for syarat in prasyarat:
        if syarat.kode_prasyarat not in kode_lulus:
            return False

    return True


# BENTUK DATA MATA KULIAH UNTUK HASIL REKOMENDASI
def data_matkul(matkul, alasan):
    return {
        "kode": matkul.kode,
        "nama": matkul.matkul,
        "matkul": matkul.matkul,
        "sks": matkul.sks or 0,
        "semester": matkul.semester,
        "reasoning": alasan,
    }

# ANALISIS KRS MAHASISWA
def analisis_krs(npm):
    mahasiswa = Mahasiswa.query.filter_by(npm=npm).first()

    if not mahasiswa:
        raise ValueError("Data mahasiswa tidak ditemukan.")

    riwayat = ambil_riwayat_mahasiswa(npm)
    statistik = hitung_nilai(riwayat)

    ips = statistik["ips"]
    ipk = statistik["ipk"]
    lulus_sks = statistik["lulus_sks"]
    semester_terakhir = statistik["semester_terakhir"]

    semester_tujuan = (
        semester_terakhir + 1 if semester_terakhir > 0 else 1
    )

    max_sks = batas_sks(ips, semester_tujuan)

    # Simpan nilai terakhir setiap mata kuliah.
    nilai_terakhir = {}

    for data in riwayat:
        kode = data["kode_matkul"]
        nilai_terakhir[kode] = (data["nilai"] or "").strip().upper()

    kode_lulus = {
        kode for kode, nilai in nilai_terakhir.items()
        if nilai in ["A", "B", "C"]
    }

    matkul_gagal = {
        kode: data
        for kode, data in (
            (data["kode_matkul"], data) for data in riwayat
        )
        if (data["nilai"] or "").strip().upper() in ["D", "E"]
        and kode not in kode_lulus
    }

    katalog = MataKuliah.query.filter(
        or_(
            MataKuliah.fakultas == mahasiswa.fakultas,
            MataKuliah.fakultas.is_(None),
            MataKuliah.fakultas == "",
        ),
        or_(
            MataKuliah.prodi == mahasiswa.prodi,
            MataKuliah.prodi.is_(None),
            MataKuliah.prodi == "",
        ),
    ).order_by(
        MataKuliah.semester.asc(),
        MataKuliah.kode.asc()
    ).all()

    katalog_dict = {matkul.kode: matkul for matkul in katalog}

    # Hitung kesiapan berdasarkan nilai prasyarat.
    def nilai_prasyarat(matkul):
        prasyarat = PrasyaratMatkul.query.filter_by(
            kode_matkul=matkul.kode
        ).all()

        jumlah_lulus = 0
        total_bobot = 0

        bobot_nilai = {
            "A": 4,
            "B": 3,
            "C": 2,
        }

        for syarat in prasyarat:
            nilai = nilai_terakhir.get(syarat.kode_prasyarat)

            if nilai not in ["A", "B", "C"]:
                return False, 0, 0

            jumlah_lulus += 1
            total_bobot += bobot_nilai[nilai]

        rata_bobot = (
            total_bobot / jumlah_lulus if jumlah_lulus else 0
        )

        return True, jumlah_lulus, rata_bobot

    kandidat = []

    for matkul in katalog:
        if matkul.semester is None:
            continue

        # Hanya semester dengan ganjil/genap yang sama.
        if matkul.semester % 2 != semester_tujuan % 2:
            continue

        if matkul.kode in kode_lulus:
            continue

        # Periksa minimal SKS yang harus sudah lulus.
        if (
            matkul.minimal_sks is not None
            and lulus_sks < matkul.minimal_sks
        ):
            continue

        prasyarat_ok, jumlah_prasyarat, rata_bobot = (
            nilai_prasyarat(matkul)
        )

        if not prasyarat_ok:
            continue

        # Periksa apakah mata kuliah termasuk kelompok pilihan.
        anggota_pilihan = AnggotaKelompokPilihan.query.filter_by(
            kode_matkul=matkul.kode
        ).first()

        is_pilihan = anggota_pilihan is not None

        # Tentukan jenis kandidat.
        if matkul.kode in matkul_gagal:
            jenis = "mengulang"
            alasan = (
                "Prioritas mengulang karena nilai sebelumnya D/E."
            )
        elif matkul.semester == semester_tujuan:
            jenis = "semester_berjalan"
            alasan = (
                "Mata kuliah semester berjalan dan prasyarat terpenuhi."
            )
        else:
            jenis = "tambahan"
            alasan = (
                "Kandidat tambahan dengan prasyarat terpenuhi."
            )

        # Prioritas utama: mata kuliah wajib.
        # Di dalam kategori yang sama, semester berjalan
        # dan mata kuliah mengulang tetap diprioritaskan.
        if not is_pilihan:
            prioritas_jenis = 0
        else:
            prioritas_jenis = 1

        if jenis == "semester_berjalan":
            prioritas_semester = 0
        elif jenis == "mengulang":
            prioritas_semester = 1
        else:
            prioritas_semester = 2

        jarak_semester = abs(matkul.semester - semester_tujuan)

        skor = (
            rata_bobot * 10
            + jumlah_prasyarat * 2
            - jarak_semester
        )

        item = data_matkul(matkul, alasan)
        item["jenis"] = jenis
        item["prioritas_skor"] = round(skor, 2)
        item["jumlah_prasyarat_lulus"] = jumlah_prasyarat
        item["rata_bobot_prasyarat"] = round(rata_bobot, 2)

        kandidat.append({
            "data": item,
            "prioritas_jenis": prioritas_jenis,
            "prioritas_semester": prioritas_semester,
            "skor": skor,
        })

    # Semester berjalan terlebih dahulu.
    # Dalam kelompok yang sama, skor tertinggi lebih dahulu.
    kandidat.sort(
        key=lambda item: (
            item["prioritas_jenis"],
            item["prioritas_semester"],
            -item["skor"],
            item["data"]["semester"],
            item["data"]["kode"],
        )
    )

    # Semua kandidat yang memenuhi syarat tetap ditampilkan.
    semua_kandidat = [item["data"] for item in kandidat]

    # Pilih rekomendasi utama sesuai batas SKS.
    direkomendasikan = []
    total_sks = 0

    for item in semua_kandidat:
        sks = item["sks"]

        if sks <= 0:
            continue

        if total_sks + sks > max_sks:
            continue

        direkomendasikan.append(item)
        total_sks += sks

    kode_rekomendasi = {
        item["kode"] for item in direkomendasikan
    }

    # Kandidat yang belum masuk rekomendasi utama,
    # beserta alasan mengapa belum dipilih.
    tidak_boleh_diambil = []

    for item in semua_kandidat:
        if item["kode"] in kode_rekomendasi:
            continue

        alasan = (
            "Kandidat memenuhi syarat, tetapi tidak masuk "
            "kuota SKS rekomendasi utama."
        )

        data = dict(item)
        data["reasoning"] = alasan
        tidak_boleh_diambil.append(data)

    sudah_lulus = [
        {
            "kode": data["kode_matkul"],
            "nama": data["nama_matkul"],
            "matkul": data["nama_matkul"],
            "sks": data["sks"],
            "nilai": data["nilai"],
            "semester": data["semester"],
        }
        for data in riwayat
        if (data["nilai"] or "").strip().upper()
        in ["A", "B", "C"]
    ]

    return {
        "semester": semester_tujuan,
        "ips": ips,
        "ipk": ipk,
        "max_sks": max_sks,
        "total_sks": total_sks,
        "lulus_sks": lulus_sks,
        "direkomendasikan": direkomendasikan,
        "prioritas_mengulang": [
            item for item in semua_kandidat
            if item["jenis"] == "mengulang"
        ],
        "semua_kandidat": semua_kandidat,
        "tidak_boleh_diambil": tidak_boleh_diambil,
        "sudah_lulus": sudah_lulus,
    }