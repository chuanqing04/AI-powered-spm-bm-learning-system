import { useLocation } from "react-router-dom";
import Navbar from "./Navbar";
import AIChatBar from "./AIChatBar";

export default function Layout({ children }: any) {
  const location = useLocation();

  const isQuizPage = location.pathname.endsWith("-quiz");

  return (
    <>
      <Navbar />
      <main className="container">{children}</main>
      {!isQuizPage && <AIChatBar />}
    </>
  );
}