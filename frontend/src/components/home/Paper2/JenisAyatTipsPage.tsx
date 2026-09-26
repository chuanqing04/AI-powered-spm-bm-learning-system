import Layout from "../../shared/Layout";
import { useLanguage } from "../../../language";

export default function JenisAyatTipsPage() {
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
          <h1>Jenis Ayat</h1>
          <p>Panduan lengkap untuk mengenal pasti dan menukar jenis ayat dalam Bahasa Melayu.</p>
        </div>

        {/* ================= AKTIF & PASIF ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">FORMAT</div>
          <h2>Ayat Aktif dan Ayat Pasif</h2>

          <p>
            <strong>Ayat aktif</strong> ialah ayat yang menekankan pelaku sebagai subjek,
            manakala <strong>ayat pasif</strong> menekankan objek sebagai subjek ayat.
          </p>

          <h3>Tips Menukar Ayat Aktif kepada Ayat Pasif</h3>
          <ul>
            <li>Objek dalam ayat aktif dijadikan subjek dalam ayat pasif.</li>
            <li>Kata kerja biasanya menerima imbuhan <strong>di-</strong>.</li>
            <li>Pelaku diletakkan selepas kata kerja dan boleh didahului oleh <strong>oleh</strong>.</li>
            <li>Pastikan ayat kekal gramatis dan jelas.</li>
          </ul>

          <p>
            <strong>Contoh:</strong><br />
            Aktif: Ali membaca buku itu.<br />
            Pasif: Buku itu dibaca oleh Ali.
          </p>
        </div>

        {/* ================= CAKAP AJUK ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <div className="chapter-top">FORMAT</div>
          <h2>Cakap Ajuk dan Cakap Pindah</h2>

          <p>
            <strong>Cakap ajuk</strong> mengekalkan kata-kata asal dan menggunakan tanda petikan,
            manakala <strong>cakap pindah</strong> melaporkan percakapan tanpa tanda petikan.
          </p>

          <h3>Tips Menukar Cakap Ajuk kepada Cakap Pindah</h3>
          <ul>
            <li>Buang tanda petikan.</li>
            <li>Tukar kata ganti diri mengikut konteks.</li>
            <li>Gunakan kata hubung seperti <strong>bahawa</strong> jika perlu.</li>
            <li>Pastikan maksud asal tidak berubah.</li>
          </ul>

          <p>
            <strong>Contoh:</strong><br />
            Cakap Ajuk: "Saya akan belajar bersungguh-sungguh," kata Amir.<br />
            Cakap Pindah: Amir berkata bahawa dia akan belajar bersungguh-sungguh.
          </p>
        </div>

        {/* ================= JENIS AYAT ================= */}
        <div className="chapter-card card-base" style={{ marginBottom: "40px" }}>
          <div className="chapter-top">NOTES</div>
          <h2>Jenis-Jenis Ayat</h2>

          <p>Dalam Bahasa Melayu, terdapat empat jenis ayat utama:</p>

          <ul>
            <li><strong>Ayat Penyata</strong> – menyampaikan maklumat.</li>
            <li><strong>Ayat Tanya</strong> – bertanya sesuatu.</li>
            <li><strong>Ayat Perintah</strong> – memberi arahan atau permintaan.</li>
            <li><strong>Ayat Seruan</strong> – meluahkan perasaan.</li>
          </ul>

          <h3>Tips Mengenal Pasti Jenis Ayat</h3>
          <ul>
            <li>Perhatikan tanda baca seperti (?) dan (!).</li>
            <li>Kenal pasti tujuan ayat.</li>
            <li>Lihat penggunaan kata seperti <strong>jangan</strong>, <strong>sila</strong>, dan <strong>wah</strong>.</li>
          </ul>

          <p>
            <strong>Contoh:</strong><br />
            Penyata: Mereka sedang bermain bola di padang.<br />
            Tanya: Adakah kamu sudah menyiapkan kerja sekolah?<br />
            Perintah: Sila tutup pintu itu.<br />
            Seruan: Wah, cantiknya pemandangan di sini!
          </p>
        </div>

      </div>
    </Layout>
  );
}