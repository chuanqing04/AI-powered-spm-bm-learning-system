import Layout from "../../shared/Layout";
import { useLanguage } from "../../../language";

export default function BinaAyatTipsPage() {
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
          <h1>Bina Ayat</h1>
          <p>Tips dan panduan membina ayat cemerlang peringkat SPM.</p>
        </div>

        {/* ================= PENGENALAN ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">NOTES</div>
          <h2>Pengenalan</h2>
          <p>
            Kemahiran membina ayat merupakan aspek penting dalam penulisan Bahasa Melayu.
            Pada peringkat SPM, pelajar perlu menghasilkan ayat yang gramatis, jelas dan
            bervariasi dari segi struktur. Penggunaan ayat yang tepat akan membantu
            menyampaikan idea dengan lebih berkesan dan matang.
          </p>
        </div>

        {/* ================= TIPS ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">TIPS</div>
          <h2>Tips Membina Ayat Cemerlang</h2>

          <ul>
            <li>Gunakan pelbagai jenis ayat seperti ayat mudah, ayat majmuk dan ayat pasif.</li>
            <li>Pastikan struktur ayat lengkap iaitu mempunyai subjek dan predikat yang jelas.</li>
            <li>Gunakan penanda wacana seperti “selain itu”, “walau bagaimanapun” dan “seterusnya”.</li>
            <li>Elakkan pengulangan perkataan dengan menggunakan sinonim yang sesuai.</li>
            <li>Variasikan permulaan ayat untuk menjadikan penulisan lebih menarik.</li>
            <li>Gunakan kata adjektif dan adverba untuk memperkayakan ayat.</li>
            <li>Pastikan penggunaan tanda baca dan ejaan adalah tepat.</li>
          </ul>
        </div>

        {/* ================= POLA AYAT ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">FORMAT</div>
          <h2>Pola Ayat Cemerlang</h2>

          <ul>
            <li><strong>Ayat Mudah:</strong> Pelajar menyiapkan tugasan tepat pada masanya.</li>
            <li><strong>Ayat Majmuk:</strong> Pelajar menyiapkan tugasan tepat pada masanya dan guru memberikan pujian.</li>
            <li><strong>Ayat Pasif:</strong> Tugasan itu disiapkan oleh pelajar dengan penuh dedikasi.</li>
            <li><strong>Ayat Majmuk Bertingkat:</strong> Walaupun hujan lebat, pelajar tetap hadir ke sekolah kerana komitmen mereka terhadap pelajaran.</li>
          </ul>
        </div>

        {/* ================= CONTOH ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "40px" }}>
          <div className="chapter-top">EXAMPLE</div>
          <h2>Contoh Ayat Cemerlang</h2>

          <p>
            1. Kerajaan telah melaksanakan pelbagai inisiatif kebersihan, selain itu,
            masyarakat juga digalakkan untuk menyertai kempen kesedaran alam sekitar.
          </p>

          <p>
            2. Walaupun menghadapi pelbagai cabaran, keluarga itu tetap menitikberatkan
            pendidikan anak-anak mereka demi masa depan yang cerah.
          </p>

          <p>
            3. Sekolah tersebut telah dianugerahkan sebagai sekolah cemerlang kerana
            pencapaian akademik dan kokurikulum yang membanggakan.
          </p>

          <p>
            4. Buku rujukan itu dibaca oleh pelajar dengan teliti supaya setiap ilmu
            yang terkandung dapat difahami sepenuhnya.
          </p>
        </div>

      </div>
    </Layout>
  );
}