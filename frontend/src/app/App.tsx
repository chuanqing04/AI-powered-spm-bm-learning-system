import { Routes, Route } from "react-router-dom";
import LoginModal from "../components/shared/LoginModal";
import { useAuth } from "../context/AuthContext";
import HomePage from "../components/home/HomePage";
import QuizPage from "../components/quiz/QuizPage";
import DashboardPage from "../components/dashboard/DashboardPage";
import KaranganContohPage from "../components/home/Paper1/KaranganPanjangContohPage";
import KaranganPendekContohPage from "../components/home/Paper1/KaranganPendekContohPage";
import KaranganPanjangLatihanPage from "../components/home/Paper1/KaranganPanjangLatihanPage";
import KaranganPendekLatihanPage from "../components/home/Paper1/KaranganPendekLatihanPage";
import GolonganKataTipsPage from "../components/home/Paper2/GolonganKataTipsPage";
import GolonganKataLatihanPage from "../components/home/Paper2/GolonganKataLatihanPage";
import BinaAyatTipsPage from "../components/home/Paper2/BinaAyatTipsPage";
import BinaAyatLatihanPage from "../components/home/Paper2/BinaAyatLatihanPage";
import JenisAyatTipsPage from "../components/home/Paper2/JenisAyatTipsPage";
import JenisAyatLatihanPage from "../components/home/Paper2/JenisAyatLatihanPage";
import KesalahanBahasaTipsPage from "../components/home/Paper2/KesalahanBahasaTipsPage";
import KesalahanBahasaLatihanPage from "../components/home/Paper2/KesalahanBahasaLatihanPage";
import PemahamanTipsPage from "../components/home/Paper2/PemahamanTipsPage";
import PemahamanLatihanPage from "../components/home/Paper2/PemahamanLatihanPage";
import UjianBertuturTipsPage from "../components/home/Paper3/UjianBertuturTipsPage";
import UjianBertuturLatihanPage from "../components/home/Paper3/UjianBertuturLatihanPage";
import UjianMendengarTipsPage from "../components/home/Paper4/UjianMendengarTipsPage";
import UjianMendengarLatihanPage from "../components/home/Paper4/UjianMendengarLatihanPage";
import RumusanTipsPage from "../components/home/Paper2/RumusanTipsPage";
import RumusanLatihanPage from "../components/home/Paper2/RumusanLatihanPage";
import KaranganPanjangQuizPage from "../components/quiz/Paper1/KaranganPanjangQuizPage";
import KaranganPendekQuizPage from "../components/quiz/Paper1/KaranganPendekQuizPage";
import BinaAyatQuizPage from "../components/quiz/Paper2/BinaAyatQuizPage";
import GolonganKataQuizPage from "../components/quiz/Paper2/GolonganKataQuizPage";
import JenisAyatQuizPage from "../components/quiz/Paper2/JenisAyatQuizPage";
import KesalahanBahasaQuizPage from "../components/quiz/Paper2/KesalahanBahasaQuizPage";
import PemahamanQuizPage from "../components/quiz/Paper2/PemahamanQuizPage";
import RumusanQuizPage from "../components/quiz/Paper2/RumusanQuizPage";
import UjianBertuturQuizPage from "../components/quiz/Paper3/UjianBertuturQuizPage";
import UjianMendengarQuizPage from "../components/quiz/Paper4/UjianMendengarQuizPage";

export default function App() {
  const { user } = useAuth();

  return (
    <>
      <LoginModal isOpen={!user} />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/quiz" element={<QuizPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/karangan-panjang-contoh" element={<KaranganContohPage />} />
        <Route path="/karangan-pendek-contoh" element={<KaranganPendekContohPage />} />
        <Route path="/karangan-panjang-latihan" element={<KaranganPanjangLatihanPage />} />
        <Route path="/karangan-pendek-latihan" element={<KaranganPendekLatihanPage />} />
        <Route path="/golongan-kata-tips" element={<GolonganKataTipsPage />} />
        <Route path="/golongan-kata-latihan" element={<GolonganKataLatihanPage />} />
        <Route path="/bina-ayat-tips" element={<BinaAyatTipsPage />} />
        <Route path="/bina-ayat-latihan" element={<BinaAyatLatihanPage />} />
        <Route path="/jenis-ayat-tips" element={<JenisAyatTipsPage />} />
        <Route path="/jenis-ayat-latihan" element={<JenisAyatLatihanPage />} />
        <Route path="/kesalahan-bahasa-tips" element={<KesalahanBahasaTipsPage />} />
        <Route path="/kesalahan-bahasa-latihan" element={<KesalahanBahasaLatihanPage />} />
        <Route path="/pemahaman-tips" element={<PemahamanTipsPage />} />
        <Route path="/pemahaman-latihan" element={<PemahamanLatihanPage />} />
        <Route path="/ujian-bertutur-tips" element={<UjianBertuturTipsPage />} />
        <Route path="/ujian-bertutur-latihan" element={<UjianBertuturLatihanPage />} />
        <Route path="/ujian-mendengar-tips" element={<UjianMendengarTipsPage />} />
        <Route path="/ujian-mendengar-latihan" element={<UjianMendengarLatihanPage />} />
        <Route path="/rumusan-tips" element={<RumusanTipsPage />} />
        <Route path="/rumusan-latihan" element={<RumusanLatihanPage />} />
        <Route path="/karangan-panjang-quiz" element={<KaranganPanjangQuizPage />} />
        <Route path="/karangan-pendek-quiz" element={<KaranganPendekQuizPage />} />
        <Route path="/bina-ayat-quiz" element={<BinaAyatQuizPage />} />
        <Route path="/golongan-kata-quiz" element={<GolonganKataQuizPage />} />
        <Route path="/jenis-ayat-quiz" element={<JenisAyatQuizPage />} />
        <Route path="/kesalahan-bahasa-quiz" element={<KesalahanBahasaQuizPage />} />
        <Route path="/pemahaman-quiz" element={<PemahamanQuizPage />} />
        <Route path="/rumusan-quiz" element={<RumusanQuizPage />} />
        <Route path="/ujian-bertutur-quiz" element={<UjianBertuturQuizPage />} />
        <Route path="/ujian-mendengar-quiz" element={<UjianMendengarQuizPage />} />
      </Routes>
    </>
  );
}