import Layout from "../../shared/Layout";
import { useLanguage } from "../../../language";

export default function UjianMendengarTipsPage() {
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
          <h1>Ujian Mendengar</h1>
          <p>Panduan untuk menjawab soalan mendengar dengan tepat dan berkesan.</p>
        </div>

        {/* ================= STRATEGY ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">STRATEGY</div>
          <h2>Strategi Utama</h2>

          <ul>
            <li>Baca semua soalan sebelum audio dimainkan.</li>
            <li>Kenal pasti maklumat penting seperti nama, tempat dan sebab.</li>
            <li>Fokus sepenuhnya semasa mendengar audio.</li>
            <li>Jangan cuba memahami setiap perkataan, fokus kepada isi utama.</li>
          </ul>
        </div>

        {/* ================= TIPS ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">TIPS</div>
          <h2>Teknik Semasa Mendengar</h2>

          <ul>
            <li>Catat kata kunci seperti nombor, fakta dan isi penting.</li>
            <li>Kenal pasti jenis soalan (objektif, isi tempat kosong, KBAT).</li>
            <li>Elakkan gangguan dan kekalkan fokus sepanjang audio dimainkan.</li>
            <li>Dengar dengan teliti perubahan maklumat dalam audio.</li>
          </ul>
        </div>

        {/* ================= ANSWERING ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">ANSWERING</div>
          <h2>Teknik Menjawab</h2>

          <ul>
            <li>Jawab berdasarkan maklumat yang didengar sahaja.</li>
            <li>Gunakan ayat yang ringkas, jelas dan tepat.</li>
            <li>Elakkan menambah maklumat sendiri.</li>
            <li>Pastikan jawapan menepati kehendak soalan.</li>
          </ul>
        </div>

        {/* ================= TRAPS ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">COMMON TRAP</div>
          <h2>Perangkap Soalan</h2>

          <ul>
            <li>Maklumat awal mungkin diubah di akhir audio.</li>
            <li>Terdapat pilihan jawapan yang hampir sama.</li>
            <li>Audio mungkin mengandungi maklumat mengelirukan.</li>
            <li>Pilih jawapan berdasarkan keseluruhan konteks.</li>
          </ul>
        </div>

        {/* ================= FINAL CHECK ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "40px" }}>
          <div className="chapter-top">EXAM TIP</div>
          <h2>Semakan Akhir</h2>

          <ul>
            <li>Semak semula jawapan selepas audio tamat.</li>
            <li>Pastikan tiada kesalahan ejaan.</li>
            <li>Pastikan semua soalan dijawab.</li>
            <li>Periksa sama ada jawapan lengkap dan tepat.</li>
          </ul>
        </div>

      </div>
    </Layout>
  );
}