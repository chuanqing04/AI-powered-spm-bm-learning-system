import Layout from "../../shared/Layout";
import { useLanguage } from "../../../language";

export default function RumusanTipsPage() {
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
          <h1>Rumusan</h1>
          <p>Kuasa teknik menulis rumusan yang padat, tepat dan cemerlang SPM.</p>
        </div>

        {/* ================= STRATEGY ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">STRATEGI</div>
          <h2>Strategi Menulis Rumusan</h2>
          <p>
            Rumusan memerlukan pelajar mengenal pasti isi penting daripada petikan dan menulis
            secara padat tanpa menyalin bulat-bulat. Teknik yang betul membantu menulis dengan cepat dan tepat.
          </p>
          <ul>
            <li>Baca petikan dengan teliti dan fahami isi utama.</li>
            <li>Kenal pasti 5–6 isi tersurat dan 1–2 isi tersirat.</li>
            <li>Gunakan bahasa sendiri, jangan salin ayat bulat-bulat.</li>
            <li>Susun isi dengan logik dan jelas.</li>
          </ul>
        </div>

        {/* ================= TIPS ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">TIPS</div>
          <h2>Teknik Menulis Rumusan</h2>
          <ul>
            <li>Mula dengan pendahuluan ringkas (1 ayat).</li>
            <li>Ambil isi penting sahaja daripada petikan (isi tersurat).</li>
            <li>Tambah idea sendiri jika perlu (isi tersirat).</li>
            <li>Gunakan ayat lengkap dan gramatis.</li>
            <li>Pastikan ejaan, tanda baca dan bahasa betul.</li>
            <li>Jangan terlalu panjang atau terlalu pendek – sasaran 80–100 patah perkataan.</li>
          </ul>
        </div>

        {/* ================= EXAM TIP ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">EXAM TIP</div>
          <h2>Perhatikan Markah</h2>
          <ul>
            <li>1–2 markah → fokus kepada 1 isi utama sahaja.</li>
            <li>3–5 markah → perlu beberapa isi tersurat dan satu isi tersirat.</li>
            <li>Markah tinggi → pastikan isi lengkap + huraian jelas + bahasa matang.</li>
          </ul>
        </div>

        {/* ================= COMMON MISTAKES ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "40px" }}>
          <div className="chapter-top">COMMON MISTAKE</div>
          <h2>Kesalahan Biasa</h2>
          <ul>
            <li>Menyalin ayat daripada petikan tanpa ubah suai.</li>
            <li>Tidak menambah isi tersirat yang relevan.</li>
            <li>Susunan isi tidak logik atau bercampur.</li>
            <li>Ayat tidak lengkap atau tidak gramatis.</li>
            <li>Tidak mematuhi had perkataan.</li>
          </ul>
        </div>

      </div>
    </Layout>
  );
}