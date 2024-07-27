import axios from "axios";
import { useState, useEffect } from "react";
import { ShootingStars } from "./components/ui/shooting-stars";
import { StarsBackground } from "./components/ui/stars-background";
import Lottie from "lottie-react";
import phishingAnimation from "./assets/lottie/phising.json";
import legitimateAnimation from "./assets/lottie/legitimate.json";

function App() {
  const [status, setStatus] = useState<string | null>(null);
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    const predict = async (url: string) => {
      try {
        const response = await axios.post("https://phis-x-latest.onrender.com/predict", { url });
        setStatus(response.data.prediction);
      } catch (error) {
        console.error("Error:", error);
      }
    };

    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0] && tabs[0].url) {
        setUrl(tabs[0].url);
        predict(tabs[0].url);
      }
    });
  }, []);

  return (
    <div className="h-[20rem] w-[30rem] bg-neutral-900 flex flex-col items-center justify-center relative p-5">
      <div className="relative z-10 flex flex-col items-center text-center">
        <h2 className="text-3xl md:text-5xl md:leading-tight max-w-5xl mx-auto tracking-tight font-medium bg-clip-text text-transparent bg-gradient-to-b from-neutral-800 via-white to-white mb-4">
          PhisX
        </h2>
        {url ? (
          <span className="text-sm text-white mb-2">
            <span className="font-semibold">Current URL: </span>
            <span className="text-gray-300 break-all">{url}</span>
          </span>
        ) : (
          <span className="text-sm text-gray-500 mb-2">No URL detected</span>
        )}
        {status ? (
          <>
            <span className="text-sm mb-2">
              <span className="font-semibold text-white">Status: </span>
              <span className={status === "Legitimate website" ? 'text-green-400' : 'text-red-400'}>
                {status}
              </span>
            </span>
            <div className="w-32 h-32">
              <Lottie 
                animationData={status === "Legitimate website" ? legitimateAnimation : phishingAnimation}
                loop={true}
                autoplay={true}
              />
            </div>
          </>
        ) : (
          <span className="text-sm text-gray-500">Loading...</span>
        )}
      </div>
      <ShootingStars />
      <StarsBackground />
    </div>
  );
}

export default App;