import Layout from "../../shared/Layout";
import { useLanguage } from "../../../language";

export default function KesalahanBahasaTipsPage() {
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
          <h1>Kesalahan Bahasa</h1>
          <p>Panduan mengenal pasti dan membetulkan kesalahan bahasa peringkat SPM.</p>
        </div>

        {/* ================= JENIS ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">NOTES</div>
          <h2>Jenis-Jenis Kesalahan Bahasa</h2>

          <p>Kesalahan bahasa yang sering diuji dalam peperiksaan termasuk:</p>

          <ul>
            <li><strong>Kesalahan ejaan</strong> – ejaan perkataan tidak tepat.</li>
            <li><strong>Kesalahan imbuhan</strong> – penggunaan awalan atau akhiran yang salah.</li>
            <li><strong>Kesalahan kata sendi nama</strong> – seperti <strong>di</strong>, <strong>ke</strong>, dan <strong>dari</strong>.</li>
            <li><strong>Kesalahan struktur ayat</strong> – ayat tidak gramatis atau tidak lengkap.</li>
            <li><strong>Kesalahan penggunaan kata</strong> – perkataan tidak sesuai dengan konteks.</li>
          </ul>
        </div>

        {/* ================= TIPS ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">TIPS</div>
          <h2>Tips Mengesan Kesalahan</h2>

          <ul>
            <li>Baca ayat dengan teliti dan kenal pasti bahagian yang janggal.</li>
            <li>Perhatikan penggunaan imbuhan seperti <strong>me-</strong>, <strong>ber-</strong>, <strong>di-</strong>, dan <strong>ter-</strong>.</li>
            <li>Pastikan kata sendi nama digunakan dengan betul seperti <strong>di rumah</strong> dan <strong>ke sekolah</strong>.</li>
            <li>Semak sama ada ayat mempunyai subjek dan predikat yang lengkap.</li>
            <li>Pastikan setiap perkataan sesuai dengan maksud ayat.</li>
          </ul>
        </div>

        {/* ================= CONTOH ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">EXAMPLE</div>
          <h2>Contoh Kesalahan dan Pembetulan</h2>

          <p>
            <strong>Contoh 1:</strong><br />
            Salah: Mereka sedang bermain bola di padang sekolah itu dengan gembira sekali.<br />
            Betul: Mereka bermain bola di padang sekolah itu dengan gembira.
          </p>

          <p>
            <strong>Contoh 2:</strong><br />
            Salah: Ali pergi disekolah setiap hari.<br />
            Betul: Ali pergi ke sekolah setiap hari.
          </p>

          <p>
            <strong>Contoh 3:</strong><br />
            Salah: Dia telah meminjamkan buku itu kepada saya semalam hari.<br />
            Betul: Dia telah meminjamkan buku itu kepada saya semalam.
          </p>
        </div>

        {/* ================= SKOR ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "40px" }}>
          <div className="chapter-top">EXAM TIP</div>
          <h2>Tip Skor Cemerlang</h2>

          <ul>
            <li>Kenal pasti perkataan yang salah sebelum membuat pembetulan.</li>
            <li>Elakkan mengubah keseluruhan ayat jika hanya satu kesalahan.</li>
            <li>Pastikan maksud asal ayat dikekalkan.</li>
            <li>Biasakan diri dengan struktur ayat Bahasa Melayu yang betul.</li>
          </ul>
        </div>

      </div>
    </Layout>
  );
}