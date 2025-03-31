import React, { useState } from "react";

import axios from "axios";

import Navbar from "./Navbar";

import PdfResult from "./PdfResult";

import "./Analyze.css";

interface AnalysisResult {
  extractedText: string;

  summary: string;

  text_length: number;
}
interface Message {
  role: "user" | "assistant";
  content: string;
}

const ResourceAnalysis: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"pdf" | "youtube">("pdf");

  const [pdfFile, setPdfFile] = useState<File | null>(null);

  const [youtubeLink, setYoutubeLink] = useState<string>("");

  const [message, setMessage] = useState<string>("");

  const [messages, setMessages] = useState<Message[]>([]);

  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(
    null
  );

  const [isLoading, setIsLoading] = useState<boolean>(false);

  const [chatQuery, setChatQuery] = useState<string>("");

  const handlePdfUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];

    if (file) {
      if (file.type !== "application/pdf") {
        setMessage("Invalid file type. Please upload a PDF.");

        return;
      }

      const maxSizeInBytes = 10 * 1024 * 1024; // 10MB

      if (file.size > maxSizeInBytes) {
        setMessage("File size exceeds 10MB limit.");

        return;
      }

      setPdfFile(file);

      setMessage("PDF file ready for analysis");
    }
  };

  const handleYoutubeLinkChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const link = event.target.value;

    const youtubeRegex = /^(https?\:\/\/)?(www\.youtube\.com|youtu\.?be)\/.+$/;

    if (link && !youtubeRegex.test(link)) {
      setMessage("Please enter a valid YouTube link");
    } else {
      setMessage("");

      setYoutubeLink(link);
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    setIsLoading(true);

    setMessage("");

    try {
      if (activeTab === "pdf" && pdfFile) {
        const formData = new FormData();
        formData.append("pdf", pdfFile);

        const response = await fetch("http://localhost:5000/extract-text", {
          method: "POST",
          body: formData,
        });

        const data = await response.json();
        console.log(data.summary);

        setAnalysisResult(data);

        setMessage("PDF analyzed successfully");
      } else if (activeTab === "youtube" && youtubeLink) {
        const response = await axios.post("/api/analyze-youtube", {
          videoUrl: youtubeLink,
        });

        setMessage(response.data.message || "Video analyzed successfully");
      } else {
        setMessage("Please provide a resource to analyze");
      }
    } catch (error) {
      console.error("Analysis Error:", error);

      setMessage("Analysis failed: An unexpected error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  const handleChatQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatQuery.trim() || isLoading) return;

    const newMessage: Message = { role: "user", content: chatQuery };
    setMessages((prev) => [...prev, newMessage]);
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:5000/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: chatQuery,
          extractedText: analysisResult?.extractedText || "",
        }),
      });

      const data = await response.json();
      const assistantMessage: Message = {
        role: "assistant",
        content: data.answer,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Error generating response:", error);
    } finally {
      setIsLoading(false);
      setChatQuery("");
    }
  };
  const handleBack = () => {
    setAnalysisResult(null);
  };

  if (analysisResult) {
    return (
      <>
        <Navbar />

        <PdfResult data={analysisResult} />

        <div className="space-y-4 h-96 overflow-y-auto p-10 bg-[#202020] border-3 border-[#2f2f2f] rounded-lg">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`p-4 rounded-lg ${
                message.role === "user"
                  ? "bg-[#202020] border border-[#a09a8dff] ml-auto max-w-[80%]"
                  : "bg-[#202020] border border-[#a09a8dff] max-w-[80%]"
              }`}
            >
              {message.content}
            </div>
          ))}

          {/* Query Input */}
          <form
            onSubmit={handleChatQuery}
            className="flex space-x-2 border border-[#a09a8dff] p-2"
          >
            <textarea
              value={chatQuery}
              onChange={(e) => setChatQuery(e.target.value)}
              placeholder="Ask a question about the PDF..."
              className="flex-1"
              disabled={isLoading || analysisResult.extractedText.length === 0}
            />
            <button
              className="bg-[#bd5743] p-2 rounded-lg"
              type="submit"
              disabled={isLoading || analysisResult.extractedText.length === 0}
            >
              Send
            </button>
          </form>
        </div>
        <br></br>
        <button className="button button2" onClick={handleBack}>
          Back
        </button>
      </>
    );
  }

  return (
    <>
      <h2 className="title stitle">Resource Analysis</h2>

      <div className="page-container">
        <div className="tab-container">
          <button
            className={`tab ${activeTab === "pdf" ? "active" : ""} rounded-lg`}
            onClick={() => setActiveTab("pdf")}
          >
            PDF Analysis
          </button>

          <button
            className={`tab ${
              activeTab === "youtube" ? "active" : ""
            } rounded-lg`}
            onClick={() => setActiveTab("youtube")}
          >
            Video Analysis
          </button>
        </div>

        <div className="form-container">
          <form onSubmit={handleSubmit}>
            {activeTab === "pdf" && (
              <div className="file-upload-container">
                <label htmlFor="pdf-upload">Upload PDF:</label>

                <input
                  className="input-field"
                  type="file"
                  id="pdf-upload"
                  accept=".pdf"
                  onChange={handlePdfUpload}
                  disabled={isLoading}
                />
              </div>
            )}

            {activeTab === "youtube" && (
              <div className="file-upload-container">
                <label htmlFor="youtube-link">YouTube Video Link:</label>

                <input
                  className="input-field"
                  type="text"
                  id="youtube-link"
                  value={youtubeLink}
                  onChange={handleYoutubeLinkChange}
                  placeholder="Paste YouTube video link"
                  disabled={isLoading}
                />
              </div>
            )}

            <button
              className="submit-button"
              type="submit"
              disabled={
                isLoading || (activeTab === "pdf" ? !pdfFile : !youtubeLink)
              }
            >
              {isLoading ? "Analyzing..." : "Analyze Resource"}
            </button>
          </form>

          {message && (
            <div
              className={`message-box ${
                message.includes("failed") ? "error" : "success"
              }`}
            >
              {message}
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default ResourceAnalysis;
