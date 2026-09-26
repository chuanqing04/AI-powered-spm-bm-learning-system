import Layout from "../../shared/Layout";
import { useLanguage } from "../../../language";

export default function UjianBertuturTipsPage() {
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
          <h1>Ujian Bertutur</h1>
          <p>Panduan untuk bercakap dengan yakin dan tersusun dalam SPM.</p>
        </div>

        {/* ================= PENGENALAN ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">NOTES</div>
          <h2>Pengenalan</h2>

          <p>
            Ujian bertutur menilai keupayaan pelajar menyampaikan idea secara
            lisan dengan jelas, tersusun dan yakin. Pelajar perlu menunjukkan
            penggunaan bahasa yang gramatis serta mampu memberikan pendapat
            yang matang dan relevan.
          </p>
        </div>

        {/* ================= FORMAT ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">FORMAT</div>
          <h2>Format Ujian Bertutur</h2>

          <ul>
            <li><strong>Bahagian A:</strong> Individu – bercakap berdasarkan stimulus.</li>
            <li><strong>Bahagian B:</strong> Perbincangan kumpulan.</li>
            <li>Perlu memberikan isi, huraian dan contoh.</li>
            <li>Gunakan bahasa yang jelas dan ayat yang gramatis.</li>
          </ul>
        </div>

        {/* ================= TIPS ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">TIPS</div>
          <h2>Tips Menjawab</h2>

          <ul>
            <li>Fahami stimulus sebelum mula bercakap.</li>
            <li>Susun idea secara logik (isi → huraian → contoh).</li>
            <li>Gunakan ayat lengkap dan mudah difahami.</li>
            <li>Bercakap dengan yakin dan suara yang jelas.</li>
            <li>Elakkan terlalu banyak “erm” atau berhenti terlalu lama.</li>
          </ul>
        </div>

        {/* ================= STRUCTURE ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">STRUCTURE</div>
          <h2>Cara Menyusun Jawapan</h2>

          <ul>
            <li><strong>Isi:</strong> Nyatakan idea utama.</li>
            <li><strong>Huraian:</strong> Terangkan idea dengan jelas.</li>
            <li><strong>Contoh:</strong> Berikan situasi atau bukti yang sesuai.</li>
            <li><strong>Penegasan:</strong> Rumuskan idea (optional, untuk skor tinggi).</li>
          </ul>
        </div>

        {/* ================= EXAMPLE ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">EXAMPLE</div>
          <h2>Contoh Jawapan Cemerlang</h2>

          <p>
            Pada pendapat saya, membaca buku amat penting dalam kalangan pelajar.
            Hal ini demikian kerana amalan membaca dapat menambah ilmu pengetahuan
            dan meluaskan pemikiran seseorang.
          </p>

          <p>
            Sebagai contoh, pelajar yang gemar membaca buku ilmiah dapat memahami
            pelbagai bidang seperti sains dan teknologi. Oleh itu, amalan membaca
            harus dipupuk sejak kecil agar melahirkan generasi berilmu.
          </p>
        </div>

        {/* ================= EXAM TIP ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "40px" }}>
          <div className="chapter-top">EXAM TIP</div>
          <h2>Tip Skor Tinggi</h2>

          <ul>
            <li>Gunakan penanda wacana seperti “selain itu”, “seterusnya”.</li>
            <li>Berikan sekurang-kurangnya 2–3 isi yang jelas.</li>
            <li>Pastikan setiap isi ada huraian dan contoh.</li>
            <li>Elakkan ayat terlalu pendek atau terlalu ringkas.</li>
          </ul>
        </div>

      </div>
    </Layout>
  );
}