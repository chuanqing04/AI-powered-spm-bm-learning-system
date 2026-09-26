import Layout from "../../shared/Layout";
import { useLanguage } from "../../../language";

export default function PemahamanTipsPage() {
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
          <h1>Pemahaman</h1>
          <p>Strategi menjawab soalan pemahaman dengan tepat dan berkesan.</p>
        </div>

        {/* ================= STRATEGY ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">STRATEGY</div>
          <h2>Strategi Menjawab Pemahaman</h2>

          <p>
            Soalan pemahaman memerlukan pelajar membaca petikan dengan teliti
            dan mengenal pasti maklumat penting. Teknik yang betul dapat membantu
            menjawab dengan lebih cepat dan tepat.
          </p>

          <ul>
            <li>Baca semua soalan terlebih dahulu sebelum membaca petikan.</li>
            <li>Kenal pasti kata kunci dalam setiap soalan.</li>
            <li>Fokus kepada isi penting dalam petikan, bukan huraian panjang.</li>
            <li>Elakkan menyalin bulat-bulat tanpa memahami maksud.</li>
          </ul>
        </div>

        {/* ================= TIPS ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">TIPS</div>
          <h2>Teknik Menjawab Soalan</h2>

          <ul>
            <li>Jawab berdasarkan petikan kecuali jika diminta pendapat sendiri.</li>
            <li>Gunakan ayat lengkap dan gramatis.</li>
            <li>Elakkan jawapan terlalu panjang atau tidak berkaitan.</li>
            <li>Gunakan bahasa sendiri jika boleh untuk menunjukkan kefahaman.</li>
            <li>Pastikan ejaan dan tanda baca adalah betul.</li>
          </ul>
        </div>

        {/* ================= MARKING ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">EXAM TIP</div>
          <h2>Perhatikan Markah Soalan</h2>

          <ul>
            <li>1 markah → biasanya satu isi sahaja.</li>
            <li>2–3 markah → memerlukan lebih daripada satu isi.</li>
            <li>Markah tinggi → perlu isi + huraian yang jelas.</li>
            <li>Pastikan jumlah isi sepadan dengan markah.</li>
          </ul>
        </div>

        {/* ================= COMMON MISTAKES ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "40px" }}>
          <div className="chapter-top">COMMON MISTAKE</div>
          <h2>Kesalahan Biasa</h2>

          <ul>
            <li>Menyalin jawapan tanpa memahami maksud.</li>
            <li>Tidak menjawab mengikut kehendak soalan.</li>
            <li>Memberi jawapan terlalu umum atau tidak tepat.</li>
            <li>Tidak menggunakan ayat lengkap.</li>
          </ul>
        </div>

      </div>
    </Layout>
  );
}