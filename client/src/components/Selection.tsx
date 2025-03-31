import "./Selection.css";
import { useState } from "react";
import Navbar from "./Navbar";
import ResourceAnalysis from "./Analyze";
import Recommend from "./Recommend";

const SelectionPage = ({ onBack }: { onBack: () => void }) => {
  const [selectedMethod, setSelectedMethod] = useState<string | null>(null);
  const handleMethodChoice = (method: string) => {
    setSelectedMethod(method);
  };
  if (selectedMethod === "Analyze") {
    return (
      <>
        <Navbar />
        <ResourceAnalysis />
      </>
    );
  }

  if (selectedMethod === "Recommend") {
    return (
      <>
        <Navbar />
        <Recommend />
      </>
    );
  }
  return (
    <div className="container">
      <div className="text-center mb-8">
        <h2 className="title stitle">Select a Service</h2>
        <p className="head shead">Choose the service you want to use</p>
      </div>

      <div className="select1">
        <div className="border border-[#393731] h-[220px] text-[#a09a8d] bg-[#202020] m-8 rounded-lg shadow-lg transition-shadow duration-150 ease-in-out p-10">
          <h3 className="subhead">Resource Recommendation</h3>
          <div className="text-center text-white pb-5">
            Get personalized learning resources based on your interests and
            learning style.
          </div>
          <button
            className="button button2"
            onClick={() => handleMethodChoice("Recommend")}
          >
            Select
          </button>
        </div>

        <div className="border border-[#393731] h-[200px] text-[#a09a8d] bg-[#202020] m-8 rounded-lg shadow-lg transition-shadow duration-150 ease-in-out p-10">
          <h3 className="subhead m-auto">Material Analyzer</h3>
          <p className="message ml-10">
            Analyze and extract key information from your learning materials
          </p>
          <button
            className="button button2"
            onClick={() => handleMethodChoice("Analyze")}
          >
            Select
          </button>
        </div>
      </div>

      <button onClick={onBack} className="button button2">
        Back to Home
      </button>
    </div>
  );
};

export default SelectionPage;
