import React from "react";
import "./PdfResult.css";

interface PdfResultProps {
  data: {
    extractedText: string;

    summary: string;

    text_length: number;
  };
}

const PdfResult: React.FC<PdfResultProps> = ({ data }) => {
  return (
    <div className="pdf-result-container border-3 border-[#2f2f2f] rounded-lg border-b-0">
      <h3>PDF Analysis Summary</h3>

      <div className="summary-section">
        <h4>Summary:</h4>

        <p>{data.summary}</p>
      </div>

      <div className="text-length-section mt-5">
        <h4>Text Length:</h4>

        <p>{data.text_length} characters</p>
      </div>
    </div>
  );
};

export default PdfResult;
