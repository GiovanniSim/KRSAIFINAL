import pdfplumber
import re


def baca_khs(file_pdf):
    teks_pdf = ""

    with pdfplumber.open(file_pdf) as pdf:
        for halaman in pdf.pages:
            teks = halaman.extract_text()

            if teks:
                teks_pdf += teks + "\n"

    return teks_pdf


def parse_khs(file_pdf):
    teks_pdf = baca_khs(file_pdf)

    data = {
        "npm": None,
        "nama": None,
        "prodi": None,
        "riwayat_nilai": []
    }

    # Identitas mahasiswa
    pola_npm = re.search(
        r"NPM\s*:\s*(\d+)",
        teks_pdf,
        re.IGNORECASE
    )

    pola_nama = re.search(
        r"NAMA\s*:\s*(.+)",
        teks_pdf,
        re.IGNORECASE
    )

    pola_prodi = re.search(
        r"PROGRAM STUDI\s*:\s*(.+)",
        teks_pdf,
        re.IGNORECASE
    )

    if pola_npm:
        data["npm"] = pola_npm.group(1)

    if pola_nama:
        data["nama"] = pola_nama.group(1).strip()

    if pola_prodi:
        data["prodi"] = pola_prodi.group(1).strip()

    # Memisahkan data berdasarkan semester
    for baris in teks_pdf.splitlines():
        baris = baris.strip()

        pola_semester = re.match(
            r"Semester\s+(\d+)\s+Semester\s+(\d+)$",
            baris,
            re.IGNORECASE
        )

        if pola_semester:
            semester_kiri = int(pola_semester.group(1))
            semester_kanan = int(pola_semester.group(2))
            continue

        if not re.match(r"^\d+\s+", baris):
            continue

        if "KODE MATA KULIAH" in baris:
            continue

        # Satu baris dapat berisi dua mata kuliah
        pola = re.compile(
            r"(\d+)\s+"
            r"([A-Z0-9]+)\s+"
            r"(.+?)\s+"
            r"(\d+)\s+"
            r"([A-F][+-]?)\s+"
            r"(\d+(?:\.\d+)?)"
            r"(?=\s+\d+\s+[A-Z0-9]+\s+|$)"
        )

        # Abaikan bagian IPS jika muncul setelah data mata kuliah
        baris_matkul = re.split(
            r"\s+IPS\s*:",
            baris,
            maxsplit=1,
            flags=re.IGNORECASE
        )[0]

        cocok = list(pola.finditer(baris_matkul))

        for i, hasil in enumerate(cocok):
            # Tentukan semester dari posisi mata kuliah
            semester = (
                semester_kiri if i == 0
                else semester_kanan
            )

            data["riwayat_nilai"].append({
                "kode_matkul": hasil.group(2),
                "nama_matkul": hasil.group(3).strip(),
                "semester": semester,
                "sks": int(hasil.group(4)),
                "nilai": hasil.group(5),
                "bobot": float(hasil.group(6))
            })

    return data