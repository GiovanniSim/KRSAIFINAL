import ollama


def tanya_ai(pesan_user, riwayat=None, konteks_krs=""):
    messages = [
        {
            "role": "system",
            "content": (
                "Kamu adalah KRS-AI, asisten akademik mahasiswa. "
                "Jawab menggunakan bahasa Indonesia yang ramah, "
                "jelas, dan mudah dipahami. "
                "Bantu mahasiswa memahami mata kuliah, nilai, "
                "IPS, IPK, SKS, dan pengambilan KRS. "
                "Berikan jawaban secara terstruktur dan tidak bertele-tele. "
                "Jangan mengarang nilai atau data akademik mahasiswa. "
                "Jika data akademik tidak tersedia, katakan dengan jujur."
            )
        }
    ]

    # Menambahkan hasil analisis rule-based jika tersedia
    if konteks_krs:
        messages.append({
            "role": "system",
            "content": (
                "Berikut adalah hasil analisis sistem KRS:\n"
                + konteks_krs
                + "\nGunakan data ini untuk menjawab pertanyaan. "
                "Jangan mengubah hasil perhitungan sistem."
            )
        })

    # Menambahkan riwayat percakapan jika tersedia
    if riwayat:
        messages.extend(riwayat)

    # Menambahkan pertanyaan mahasiswa
    messages.append({
        "role": "user",
        "content": pesan_user
    })

    # Meminta jawaban dari model AI lokal
    response = ollama.chat(
        model="llama3.2:3b",
        messages=messages
    )

    return response["message"]["content"]