import OpeningPage from "./components/Op";
import "./App.css";

function App() {
  return (
    <>
      <div className="relative z-10 flex h-full flexcol items-center justify-center px-4">
        <div className="max-w-3xl text-center">
          <OpeningPage />
        </div>
      </div>
    </>
  );
}

export default App;
