import Layout from "../../shared/Layout";
import { useLanguage } from "../../../language";

export default function GolonganKataTipsPage() {
  const { t } = useLanguage();

  return (
    <Layout>
      <div className="container no-top-gap">

        {/* BACK */}
        <button className="update-btn button1" onClick={() => window.history.back()}>
          {t("backToHome")}
        </button>

        {/* HERO */}
        <div className="hero">
          <h1>Golongan Kata</h1>
          <p>Nota dan tips untuk memahami golongan kata dalam Bahasa Melayu.</p>
        </div>

        {/* ================= PENGENALAN ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">NOTES</div>
          <h2>Pengenalan</h2>
          <p>
            Golongan kata ialah kategori perkataan berdasarkan fungsinya dalam ayat.
            Penguasaan golongan kata amat penting untuk membina ayat yang gramatis
            dan jelas dalam penulisan serta pertuturan.
          </p>
        </div>

        {/* ================= SENARAI ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">NOTES</div>
          <h2>Senarai Golongan Kata</h2>

          <ul>
            <li><strong>Kata Nama:</strong> orang, rumah, meja</li>
            <li><strong>Kata Kerja:</strong> makan, tidur, menulis</li>
            <li><strong>Kata Adjektif:</strong> cantik, besar, tinggi</li>
            <li><strong>Kata Adverba:</strong> cepat, lambat, dengan hati-hati</li>
            <li><strong>Kata Hubung:</strong> dan, tetapi, kerana</li>
            <li><strong>Kata Ganti Nama:</strong> saya, dia, mereka</li>
            <li><strong>Kata Bilangan:</strong> satu, dua, tiga</li>
          </ul>
        </div>

        {/* ================= TIPS ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">TIPS</div>
          <h2>Tips Mengenal Golongan Kata</h2>

          <ul>
            <li>Kata nama merujuk kepada orang, tempat atau benda.</li>
            <li>Kata kerja menunjukkan perbuatan atau keadaan.</li>
            <li>Kata adjektif menerangkan sifat sesuatu kata nama.</li>
            <li>Kata adverba menerangkan cara sesuatu perbuatan dilakukan.</li>
            <li>Kata hubung menghubungkan perkataan atau ayat.</li>
            <li>Kata ganti nama menggantikan kata nama.</li>
            <li>Kata bilangan menunjukkan jumlah atau bilangan.</li>
          </ul>
        </div>

        {/* ================= CONTOH ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "40px" }}>
          <div className="chapter-top">EXAMPLE</div>
          <h2>Contoh Ayat</h2>

          <p>
            <strong>Ali</strong> (Kata Nama) <strong>membaca</strong> (Kata Kerja)
            <strong> buku baru</strong> (Kata Nama + Adjektif)
            <strong> dengan cepat</strong> (Kata Adverba).
          </p>

          <p>
            <strong>Dia</strong> (Kata Ganti Nama)
            <strong> pergi ke sekolah</strong> (Kata Kerja + Kata Nama)
            <strong> dan</strong> (Kata Hubung)
            <strong> belajar dengan tekun</strong> (Kata Kerja + Kata Adverba).
          </p>
        </div>

      </div>
    </Layout>
  );
}