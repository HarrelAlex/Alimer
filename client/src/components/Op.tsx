import { useState } from "react";
import Navbar from "./Navbar";
import "./Op.css";
import SelectionPage from "./Selection";

const OpeningPage = () => {
  const [selectedSyllabus, setSelectedSyllabus] = useState<string | null>(null);

  const handleSyllabusChoice = (syllabus: string) => {
    setSelectedSyllabus(syllabus);

    console.log(`Selected syllabus: ${syllabus}`);
  };

  const handleBack = () => {
    setSelectedSyllabus(null);
  };

  if (selectedSyllabus === "OTHER") {
    return (
      <>
        <Navbar />
        <SelectionPage onBack={handleBack} />
      </>
    );
  }

  if (selectedSyllabus == "KTU") {
    return (
      <>
        <div className="container">
          <h2 className="selection-message">
            You selected: {selectedSyllabus}
          </h2>
          <button onClick={handleBack} className="back-button">
            Back to Selection
          </button>
        </div>
      </>
    );
  }

  return (
    <>
      <Navbar />
      <div className="container">
        <h1 className="title font-bold mb-8 [text-shadow:2px_2px_4px_rgba(0,0,0,0.1)] animate-fadeInDown text-transparent bg-clip-text bg-gradient-to-r from-[#E44C9D] to-[#F59C20]">
          ALIMER
        </h1>
        <h3 className="head">YOUR APP FOR EFFICIENT LEARNING</h3>
        <div className="button-container">
          <button
            onClick={() => handleSyllabusChoice("OTHER")}
            className="button secondary"
          >
            START
          </button>
        </div>
      </div>
    </>
  );
};

export default OpeningPage;
