import { useState } from "react";
import "./Navbar.css";
import "@fortawesome/fontawesome-free/css/all.min.css";

const Navbar = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen);
  };

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <div
          className={`menu-icon ${isMenuOpen ? "open" : ""}`}
          onClick={toggleMenu}
        >
          <i className={isMenuOpen ? "fas fa-times" : "fas fa-bars"}></i>
        </div>
        <ul className={isMenuOpen ? "nav-menu active" : "nav-menu"}>
          <li className="nav-item">
            <a href="/" className="nav-link">
              HOME
            </a>
          </li>
          <li className="nav-item">
            <a href="/login" className="nav-link">
              LOGIN
            </a>
          </li>
          <li className="nav-item">
            <a href="/signup" className="nav-link">
              SIGN UP
            </a>
          </li>
        </ul>
      </div>
    </nav>
  );
};

export default Navbar;
