import Layout from "../../shared/Layout";
import { useLanguage } from "../../../language";
import { useState } from "react";

export default function KaranganPendekContohPage() {
  const [highlightIsi, setHighlightIsi] = useState(false);
  const [showStructure, setShowStructure] = useState(false);

  const isiClass = highlightIsi ? "highlight-isi" : "";
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
          <h1>Karangan Pendek Contoh</h1>
          <p>Contoh karangan pendek SPM berkualiti tinggi.</p>
        </div>

        {/* TOGGLES */}
        <div className="chapter-actions" style={{ marginBottom: "30px" }}>
          <button className="button1" onClick={() => setHighlightIsi(!highlightIsi)}>
            Highlight Isi
          </button>

          <button className="button2" onClick={() => setShowStructure(!showStructure)}>
            Lihat Struktur
          </button>
        </div>

        {/* ================= KARANGAN ================= */}
        <div className="chapter-card card-base">

          <div className="chapter-top">PAPER 1</div>
          <h2 style={{ marginBottom: "20px" }}>
            Kepentingan Menjaga Alam Sekitar
          </h2>

          {/* PENDAHULUAN */}
          {showStructure && <p><strong>Pendahuluan</strong></p>}
          <p>
            Alam sekitar merupakan anugerah Tuhan yang tidak ternilai harganya dan menjadi
            asas kepada kehidupan manusia. Namun begitu, dalam era pembangunan yang pesat,
            masalah pencemaran alam sekitar semakin membimbangkan. Oleh itu, kepentingan
            menjaga alam sekitar perlu diberi perhatian oleh semua pihak.
          </p>

          {/* ISI */}
          {showStructure && <p><strong>Isi</strong></p>}
          <p className={isiClass}>
            Antara kepentingan menjaga alam sekitar ialah dapat menjamin kesihatan manusia.
          </p>
          <p>
            Hal ini demikian kerana persekitaran yang bersih mampu mengelakkan penularan
            penyakit seperti demam denggi dan penyakit pernafasan. Kawasan yang dipenuhi
            sampah sarap akan menjadi tempat pembiakan nyamuk Aedes yang berbahaya.
            Sebagai contoh, longkang yang tersumbat akan menyebabkan air bertakung dan
            seterusnya meningkatkan risiko penyakit berjangkit.
          </p>

          {/* PENUTUP */}
          {showStructure && <p><strong>Penutup</strong></p>}
          <p>
            Kesimpulannya, menjaga alam sekitar merupakan tanggungjawab bersama yang tidak
            boleh dipandang ringan. Semua pihak harus berganding bahu bagai “aur dengan tebing”
            bagi memastikan alam sekitar sentiasa terpelihara demi kesejahteraan hidup.
          </p>

        </div>
      </div>
    </Layout>
  );
}