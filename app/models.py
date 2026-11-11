from database import db
import json

class MataKuliah(db.Model):
    __tablename__ = "mata_kuliah"

    kode = db.Column(db.String(20), primary_key=True)
    matkul = db.Column(db.String(100))
    sks = db.Column(db.Integer)
    semester = db.Column(db.Integer)
    fakultas = db.Column(db.String(100))
    prodi = db.Column(db.String(100))
    minimal_sks = db.Column(db.Integer, nullable=True, default=None)
    semua_prasyarat = db.relationship("PrasyaratMatkul",
        foreign_keys="PrasyaratMatkul.kode_matkul",
        backref="mata_kuliah",
        cascade="all, delete-orphan"
    )

class PrasyaratMatkul(db.Model):
    __tablename__ = "prasyarat_matkul"

    id = db.Column(db.Integer, primary_key=True)

    kode_matkul = db.Column(
        db.String(20),
        db.ForeignKey("mata_kuliah.kode"),
        nullable=False
    )

    kode_prasyarat = db.Column(
        db.String(20),
        db.ForeignKey("mata_kuliah.kode"),
        nullable=False
    )

class KelompokPilihan(db.Model):
    __tablename__ = "kelompok_pilihan"

    id = db.Column(db.Integer, primary_key=True)
    nama_kelompok = db.Column(db.String(100), nullable=False)
    fakultas = db.Column(db.String(100), nullable=False)
    prodi = db.Column(db.String(100), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    jumlah_wajib_dipilih = db.Column(db.Integer, nullable=True)

class AnggotaKelompokPilihan(db.Model):
    __tablename__ = "anggota_kelompok_pilihan"

    id = db.Column(db.Integer, primary_key=True)

    kelompok_id = db.Column(
        db.Integer,
        db.ForeignKey("kelompok_pilihan.id"),
        nullable=False
    )

    kode_matkul = db.Column(
        db.String(20),
        db.ForeignKey("mata_kuliah.kode"),
        nullable=False
    )

class Mahasiswa(db.Model):
    __tablename__ = "mahasiswa"

    npm = db.Column(db.Integer, primary_key =True)
    nama = db.Column(db.String(100))
    fakultas = db.Column(db.String(100))
    prodi = db.Column(db.String(100))
    kelas = db.Column(db.String(100))
    password = db.Column(db.String(100))
    foto = db.Column(db.String(100))
    role = db.Column(db.String(20), default="mahasiswa")

class ChatSession(db.Model):
    __tablename__ = "chat_sessions"

    id = db.Column(db.Integer, primary_key=True)
    npm = db.Column(db.Integer, db.ForeignKey("mahasiswa.npm"))
    judul = db.Column(db.String(100))
    tanggal = db.Column(db.DateTime, default=db.func.current_timestamp())

class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("chat_sessions.id"))
    role = db.Column(db.String(20))
    message = db.Column(db.Text)
    tanggal = db.Column(db.DateTime, default=db.func.current_timestamp())
    # Jenis pesan: text atau recommendation
    tipe = db.Column(db.String(20), default="text", nullable=False)
    # Menyimpan data rekomendasi KRS dalam format JSON
    data_json = db.Column(db.Text, nullable=True)

    @property
    def data_hasil(self):
        if not self.data_json:
            return None

        try:
            return json.loads(self.data_json)
        except (ValueError, TypeError):
            return None

class RiwayatNilai(db.Model):
    __tablename__ = "riwayat_nilai"

    id = db.Column(db.Integer, primary_key=True)
    npm = db.Column(
        db.Integer,
        db.ForeignKey("mahasiswa.npm"),
        nullable=False
    )
    kode_matkul = db.Column(
        db.String(20),
        db.ForeignKey("mata_kuliah.kode"),
        nullable=False
    )
    semester = db.Column(db.Integer, nullable=False)
    sks = db.Column(db.Integer, nullable=False)
    nilai = db.Column(db.String(2), nullable=False)
    bobot = db.Column(db.Float)