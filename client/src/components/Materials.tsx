import React, { useState, useEffect } from "react";
import axios from "axios";
import "./Materials.css";

// API base URL - change this to match your Flask server
const API_BASE_URL = "http://localhost:5000";

// Define all possible material types that will always be shown
const ALL_MATERIAL_TYPES = [
  "all",
  "article",
  "video",
  "tutorial",
  "documentation",
  "course",
  "book",
  "blog",
];

interface Material {
  url: string;
  title: string;
  description: string;
  author: string;
  date: string;
  material_type: string;
  complexity: number;
  complexity_confidence: number;
  complexity_factors: Record<string, any>;
  preview_text: string;
}

interface LearningMaterialsProps {
  topic: string;
  competenceScore: number;
}

const LearningMaterials: React.FC<LearningMaterialsProps> = ({
  topic,
  competenceScore,
}) => {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("all");
  const [filteredMaterialTypes, setFilteredMaterialTypes] =
    useState<string[]>(ALL_MATERIAL_TYPES);

  useEffect(() => {
    if (topic && competenceScore) {
      fetchMaterials();
    }
  }, [topic, competenceScore]);

  const fetchMaterials = async () => {
    setIsLoading(true);
    setError("");

    try {
      const response = await axios.post(`${API_BASE_URL}/materials`, {
        topic,
        competence_score: competenceScore,
        material_types: filteredMaterialTypes.includes("all")
          ? []
          : filteredMaterialTypes, // Request all material types
        num_results: 10,
      });

      setMaterials(response.data.materials);

      // Track which material types have actual content
      const availableTypes = new Set(
        response.data.materials.map((m: Material) => m.material_type)
      );

      // We'll keep this to mark which tabs have content, but we don't use it to filter displayed tabs
      setFilteredMaterialTypes(
        ALL_MATERIAL_TYPES.filter(
          (type) => type === "all" || availableTypes.has(type)
        )
      );
    } catch (err) {
      console.error("Error fetching learning materials:", err);
      setError("Failed to fetch learning materials. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const getComplexityLabel = (level: number): string => {
    const labels = [
      "Beginner",
      "Elementary",
      "Intermediate",
      "Advanced",
      "Expert",
    ];
    return labels[level - 1] || "Unknown";
  };

  const getMaterialTypeIcon = (type: string): string => {
    switch (type.toLowerCase()) {
      case "article":
        return "📄";
      case "video":
        return "🎬";
      case "tutorial":
        return "📚";
      case "documentation":
        return "📑";
      case "course":
        return "🎓";
      case "book":
        return "📕";
      case "blog":
        return "✍️";
      default:
        return "📌";
    }
  };

  // Get actual materials for the active tab
  const filteredMaterials =
    activeTab === "all"
      ? materials
      : materials.filter((m) => m.material_type === activeTab);

  // Check if the current tab has any materials
  const hasContentForTab = (tabType: string) => {
    if (tabType === "all") return materials.length > 0;
    return materials.some((m) => m.material_type === tabType);
  };

  return (
    <div className="learning-materials-container">
      <div className="learning-materials-card">
        <div className="card-header">
          <h2 className="card-title">Learning Resources for {topic}</h2>
          <p className="card-description">
            Personalized resources based on your competence score of{" "}
            {competenceScore}/100
          </p>
        </div>

        <div className="tabs-container">
          {ALL_MATERIAL_TYPES.map((type) => (
            <button
              key={type}
              className={`tab-button ${activeTab === type ? "active" : ""} ${
                hasContentForTab(type) ? "" : "empty-tab"
              }`}
              onClick={() => setActiveTab(type)}
            >
              {type === "all" ? (
                "All Resources"
              ) : (
                <>
                  {getMaterialTypeIcon(type)}{" "}
                  {type.charAt(0).toUpperCase() + type.slice(1)}s
                </>
              )}
              {hasContentForTab(type) ? "" : " (0)"}
            </button>
          ))}
        </div>

        <div className="card-content">
          {isLoading ? (
            <div className="loading-message">
              Finding the best learning resources for you...
            </div>
          ) : error ? (
            <div className="error-message">{error}</div>
          ) : filteredMaterials.length === 0 ? (
            <div className="no-results-message">
              {activeTab === "all"
                ? "No learning materials found. Try adjusting your topic or competence level."
                : `No ${activeTab} resources available for this topic and competence level.`}
            </div>
          ) : (
            <div className="materials-list">
              {filteredMaterials.map((material, index) => (
                <div key={index} className="material-item">
                  <div className="material-header">
                    <div className="material-type-icon">
                      {getMaterialTypeIcon(material.material_type)}
                    </div>
                    <h3 className="material-title">
                      <a
                        href={material.url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {material.title || "No Title Available"}
                      </a>
                    </h3>
                  </div>

                  <div className="material-meta">
                    <span className="material-complexity">
                      Level: {getComplexityLabel(material.complexity)}
                    </span>
                    {material.author && (
                      <span className="material-author">
                        By: {material.author}
                      </span>
                    )}
                    {material.date && (
                      <span className="material-date">{material.date}</span>
                    )}
                  </div>

                  <p className="material-description">
                    {material.description ||
                      material.preview_text ||
                      "No description available."}
                  </p>

                  <div className="material-actions">
                    <a
                      href={material.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="view-material-button"
                    >
                      View Resource
                    </a>
                    <button className="save-material-button">
                      Save for Later
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LearningMaterials;
