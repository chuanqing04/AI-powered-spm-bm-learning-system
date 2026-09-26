import Layout from "../../shared/Layout";
import { useLanguage } from "../../../language";
import { useState } from "react";

export default function KaranganPanjangContohPage() {
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
        <div className="page-header">
          <h1>Karangan Contoh</h1>
          <p>Rujukan karangan cemerlang dengan struktur lengkap.</p>
        </div>

        {/* CONTROLS */}
        <div className="chapter-actions" style={{ marginBottom: "30px" }}>
          <button className="button1" onClick={() => setHighlightIsi(!highlightIsi)}>
            Highlight Isi
          </button>

          <button className="button2" onClick={() => setShowStructure(!showStructure)}>
            Lihat Struktur
          </button>
        </div>

        {/* ================= KARANGAN CARD ================= */}
        <div className="chapter-card card-base">

          <div className="chapter-top">PAPER 1</div>
          <h2 style={{ marginBottom: "20px" }}>
            Kepentingan Menjaga Alam Sekitar
          </h2>

          {/* PENDAHULUAN */}
          {showStructure && <p><strong>Pendahuluan</strong></p>}
          <p>
            Alam sekitar merupakan anugerah Tuhan yang tidak ternilai harganya dan menjadi
            tunjang kepada kesejahteraan hidup manusia serta hidupan lain. Namun begitu,
            dalam arus pemodenan yang kian rancak, isu pencemaran alam sekitar semakin
            meruncing bagai “api dalam sekam”. Jika masalah ini tidak ditangani dengan segera,
            implikasi negatifnya pasti menjejaskan keseimbangan ekosistem dan kualiti hidup
            manusia. Oleh itu, kepentingan menjaga alam sekitar perlu diberi perhatian serius
            oleh semua pihak.
          </p>

          {/* ISI 1 */}
          {showStructure && <p><strong>Isi 1: Menjamin Kesihatan Manusia</strong></p>}
          <p className={isiClass}>
            Salah satu kepentingan utama menjaga alam sekitar ialah dapat menjamin kesihatan manusia.
          </p>
          <p>
            Hal ini demikian kerana persekitaran yang bersih mampu mengurangkan risiko
            penularan penyakit berjangkit seperti demam denggi, leptospirosis dan penyakit
            respiratori. Kawasan yang dipenuhi sampah sarap akan menjadi tempat pembiakan
            nyamuk Aedes dan bakteria berbahaya. Sebagai contoh, longkang yang tersumbat
            akan menyebabkan air bertakung lalu menjadi habitat nyamuk.
          </p>
          <p>
            Jelaslah bahawa penjagaan alam sekitar memainkan peranan penting dalam memastikan
            masyarakat hidup dalam keadaan sihat dan bebas daripada penyakit.
          </p>

          {/* ISI 2 */}
          {showStructure && <p><strong>Isi 2: Mengekalkan Keseimbangan Ekosistem</strong></p>}
          <p className={isiClass}>
            Selain itu, pemeliharaan alam sekitar penting untuk mengekalkan keseimbangan ekosistem.
          </p>
          <p>
            Ekosistem yang stabil memastikan setiap hidupan menjalankan peranan masing-masing
            dalam rantaian makanan. Aktiviti seperti pembalakan haram dan pencemaran sungai
            akan memusnahkan habitat flora dan fauna serta mengganggu keseimbangan alam.
            Sebagai contoh, kepupusan spesies tertentu akan menyebabkan berlakunya gangguan
            kepada keseluruhan sistem ekologi.
          </p>
          <p>
            Oleh itu, usaha memelihara alam sekitar amat penting bagi menjamin kelangsungan
            hidupan di bumi ini.
          </p>

          {/* ISI 3 */}
          {showStructure && <p><strong>Isi 3: Meningkatkan Ekonomi Negara</strong></p>}
          <p className={isiClass}>
            Di samping itu, alam sekitar yang terpelihara dapat meningkatkan sektor pelancongan
            dan seterusnya menyumbang kepada ekonomi negara.
          </p>
          <p>
            Keindahan alam semula jadi seperti pantai yang bersih, hutan yang menghijau
            dan udara yang segar mampu menarik kedatangan pelancong dari dalam dan luar negara.
            Industri pelancongan yang berkembang pesat akan membuka peluang pekerjaan serta
            meningkatkan pendapatan negara.
          </p>
          <p>
            Sebagai contoh, destinasi pelancongan seperti pulau-pulau peranginan menjadi
            tarikan utama pelancong. Hal ini membuktikan bahawa penjagaan alam sekitar
            memberi manfaat ekonomi yang besar.
          </p>

          {/* PENUTUP */}
          {showStructure && <p><strong>Penutup</strong></p>}
          <p>
            Kesimpulannya, menjaga alam sekitar merupakan tanggungjawab bersama yang tidak
            boleh dipandang enteng. Semua pihak harus berganding bahu bagai “aur dengan tebing”
            dalam memastikan kelestarian alam sekitar terus terpelihara. Jika usaha ini
            dilaksanakan secara konsisten, sudah pasti kita dapat mewariskan bumi yang
            sejahtera kepada generasi akan datang.
          </p>

        </div>
      </div>
    </Layout>
  );
}