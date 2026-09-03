"use client"

export default function AnimatedLumi({ isThinking = false, className = "w-48 h-48" }: { isThinking?: boolean, className?: string }) {
  return (
    <div className={`relative flex items-center justify-center ${className}`}>
      {/* Advanced CSS Animations */}
      <style>{`
        @keyframes float-body {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-8px); }
        }
        @keyframes float-head {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-2px) rotate(1deg); }
        }
        @keyframes blink-realistic {
          0%, 3%, 100% { transform: scaleY(1); }
          1.5% { transform: scaleY(0.05); }
        }
        @keyframes look-around {
          0%, 10% { transform: translateX(0px); }
          15%, 35% { transform: translateX(-4px); }
          40%, 60% { transform: translateX(4px); }
          65%, 100% { transform: translateX(0px); }
        }
        @keyframes think-look {
          0%, 100% { transform: translate(0px, 0px); }
          25% { transform: translate(4px, -6px); }
          75% { transform: translate(-4px, -6px); }
        }
        @keyframes breathe {
          0%, 100% { transform: scale(1, 1); }
          50% { transform: scale(1.02, 0.98); }
        }
        @keyframes scan-glass {
          0% { transform: translateY(-5px) translateX(-5px) rotate(-10deg); }
          50% { transform: translateY(8px) translateX(8px) rotate(10deg); }
          100% { transform: translateY(-5px) translateX(-5px) rotate(-10deg); }
        }
        @keyframes pulse-glow {
          0%, 100% { opacity: 0.3; transform: scale(1); }
          50% { opacity: 0.6; transform: scale(1.1); }
        }
        @keyframes pulse-fast {
          0%, 100% { opacity: 0.5; transform: scale(1); }
          50% { opacity: 0.8; transform: scale(1.15); }
        }
        
        .anim-float { animation: float-body 5s ease-in-out infinite; transform-origin: bottom center; }
        .anim-breathe { animation: breathe 5s ease-in-out infinite; transform-origin: bottom center; }
        .anim-head { animation: float-head 5s ease-in-out infinite; transform-origin: center 120px; }
        .anim-blink { animation: blink-realistic 5s infinite; transform-origin: center; }
        .anim-look { animation: look-around 8s infinite ease-in-out; }
        .anim-look-think { animation: think-look 4s infinite ease-in-out; }
        .anim-scan { animation: scan-glass 4s ease-in-out infinite; transform-origin: 55px 135px; }
      `}</style>

      {/* Background Glow */}
      <div 
        className="absolute inset-0 bg-teal-500 rounded-full blur-2xl transition-all duration-500"
        style={{ animation: isThinking ? 'pulse-fast 1.5s ease-in-out infinite' : 'pulse-glow 4s ease-in-out infinite' }}
      ></div>

      {/* 2D Vector SVG Character */}
      <div className="relative z-10 w-full h-full anim-float flex items-center justify-center">
        <svg viewBox="0 0 200 200" className="w-full h-full drop-shadow-[0_10px_20px_rgba(0,0,0,0.3)]">
          <defs>
            {/* Skin Gradient */}
            <radialGradient id="skinGrad" cx="50%" cy="40%" r="60%">
              <stop offset="0%" stopColor="#fde0c4" />
              <stop offset="70%" stopColor="#f1c27d" />
              <stop offset="100%" stopColor="#d29658" />
            </radialGradient>
            
            {/* Hair Gradient */}
            <linearGradient id="hairGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#334155" />
              <stop offset="50%" stopColor="#1e293b" />
              <stop offset="100%" stopColor="#0f172a" />
            </linearGradient>

            {/* Polo Gradient */}
            <linearGradient id="poloGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#1e293b" />
              <stop offset="100%" stopColor="#020617" />
            </linearGradient>

            {/* Eye Gradient */}
            <radialGradient id="eyeGrad" cx="50%" cy="50%" r="50%">
              <stop offset="60%" stopColor="#0ea5e9" />
              <stop offset="100%" stopColor="#0369a1" />
            </radialGradient>
            
            {/* Drop Shadow for hair/chin */}
            <filter id="dropShadow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="4" stdDeviation="3" floodOpacity="0.2" />
            </filter>
            
            <filter id="hairShadow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="2" floodOpacity="0.3" />
            </filter>
          </defs>

          {/* --- BODY (ANIMATES WITH BREATHING) --- */}
          <g className="anim-breathe">
            {/* Neck */}
            <path d="M 85 120 L 115 120 L 115 150 L 85 150 Z" fill="url(#skinGrad)" filter="url(#dropShadow)" />
            
            {/* Shoulders & Torso (Cool Polo) */}
            <path d="M 70 135 L 45 185 Q 100 215 155 185 L 130 135 Q 100 150 70 135" fill="url(#poloGrad)" filter="url(#dropShadow)" />
            
            {/* Cyan Polo Accents */}
            <path d="M 55 165 L 48 186 M 145 165 L 152 186" stroke="#0ea5e9" strokeWidth="3" opacity="0.8" />
            <path d="M 60 135 L 45 185 M 140 135 L 155 185" stroke="#38bdf8" strokeWidth="1" opacity="0.3" />
            
            {/* Polo Collar */}
            <path d="M 85 135 L 65 150 L 100 160 Z" fill="#334155" filter="url(#dropShadow)" />
            <path d="M 115 135 L 135 150 L 100 160 Z" fill="#1e293b" filter="url(#dropShadow)" />
            
            {/* Polo Placket */}
            <rect x="96" y="145" width="8" height="30" fill="#0f172a" rx="2" />
            <circle cx="100" cy="152" r="1.5" fill="#0ea5e9" />
            <circle cx="100" cy="165" r="1.5" fill="#0ea5e9" />
          </g>

          {/* --- HEAD (ANIMATES WITH BOBBING) --- */}
          <g className="anim-head">
            {/* Ears */}
            <circle cx="55" cy="95" r="8" fill="url(#skinGrad)" filter="url(#dropShadow)" />
            <circle cx="145" cy="95" r="8" fill="url(#skinGrad)" filter="url(#dropShadow)" />
            
            {/* Inner Ear Detail */}
            <path d="M 53 92 Q 57 95 53 98" stroke="#d29658" strokeWidth="1.5" fill="none" strokeLinecap="round" />
            <path d="M 147 92 Q 143 95 147 98" stroke="#d29658" strokeWidth="1.5" fill="none" strokeLinecap="round" />

            {/* Head Shape */}
            <path d="M 60 90 Q 60 145 100 145 Q 140 145 140 90 Q 140 45 100 45 Q 60 45 60 90 Z" fill="url(#skinGrad)" filter="url(#dropShadow)" />

            {/* Eyebrows */}
            <g style={{ transition: "all 0.3s" }} transform={isThinking ? "translate(0, -3)" : "translate(0, 0)"}>
              <path d="M 68 72 Q 78 68 88 74" stroke="#1e293b" strokeWidth="3" fill="none" strokeLinecap="round" />
              <path d="M 132 72 Q 122 68 112 74" stroke="#1e293b" strokeWidth="3" fill="none" strokeLinecap="round" />
            </g>

            {/* Realistic BIG Eyes */}
            <g className="anim-blink">
              {/* White Sclera */}
              <circle cx="78" cy="95" r="15" fill="white" filter="url(#dropShadow)" />
              <circle cx="122" cy="95" r="15" fill="white" filter="url(#dropShadow)" />
              
              {/* Eye Shadow (Top inside rim) */}
              <path d="M 63 95 A 15 15 0 0 1 93 95" fill="none" stroke="#e2e8f0" strokeWidth="3" />
              <path d="M 107 95 A 15 15 0 0 1 137 95" fill="none" stroke="#e2e8f0" strokeWidth="3" />

              {/* Pupils Group - Animates Looking */}
              <g className={isThinking ? "anim-look-think" : "anim-look"}>
                {/* Left Iris & Pupil */}
                <circle cx="78" cy="95" r="9" fill="url(#eyeGrad)" />
                <circle cx="78" cy="95" r="4.5" fill="#020617" />
                <circle cx="81" cy="92" r="3" fill="white" />
                <circle cx="75" cy="98" r="1.5" fill="white" />
                
                {/* Right Iris & Pupil */}
                <circle cx="122" cy="95" r="9" fill="url(#eyeGrad)" />
                <circle cx="122" cy="95" r="4.5" fill="#020617" />
                <circle cx="125" cy="92" r="3" fill="white" />
                <circle cx="119" cy="98" r="1.5" fill="white" />
              </g>
            </g>

            {/* Subtle Nose */}
            <path d="M 98 108 Q 100 112 103 108" stroke="#d29658" strokeWidth="2" fill="none" strokeLinecap="round" />
            
            {/* Mouth */}
            {isThinking ? (
              <path d="M 95 125 Q 100 128 105 125" stroke="#b45309" strokeWidth="2" fill="none" strokeLinecap="round" />
            ) : (
              <path d="M 92 122 Q 100 130 108 122" stroke="#b45309" strokeWidth="2.5" fill="none" strokeLinecap="round" />
            )}

            {/* Curly Boy Hair (Realistic gradient & shadowing) */}
            <g filter="url(#hairShadow)">
              {/* Base hair silhouette */}
              <path d="M 55 80 Q 55 45 100 40 Q 145 45 145 80 Q 140 55 100 55 Q 60 55 55 80" fill="url(#hairGrad)" />
              
              {/* Fluffy Curls */}
              <circle cx="100" cy="40" r="18" fill="url(#hairGrad)" />
              <circle cx="75" cy="45" r="17" fill="url(#hairGrad)" />
              <circle cx="125" cy="45" r="17" fill="url(#hairGrad)" />
              <circle cx="60" cy="60" r="15" fill="url(#hairGrad)" />
              <circle cx="140" cy="60" r="15" fill="url(#hairGrad)" />
              
              {/* Front Curls falling over forehead */}
              <circle cx="85" cy="55" r="13" fill="url(#hairGrad)" />
              <circle cx="115" cy="55" r="13" fill="url(#hairGrad)" />
              <circle cx="100" cy="60" r="12" fill="url(#hairGrad)" />
              <circle cx="72" cy="72" r="10" fill="url(#hairGrad)" />
              <circle cx="128" cy="72" r="10" fill="url(#hairGrad)" />
            </g>
            
            {/* Hair highlight */}
            <path d="M 75 45 Q 85 40 95 45" stroke="#38bdf8" strokeWidth="2" fill="none" strokeLinecap="round" opacity="0.6" />
            <path d="M 115 50 Q 120 45 130 48" stroke="#38bdf8" strokeWidth="1.5" fill="none" strokeLinecap="round" opacity="0.6" />

            {/* AI Headset */}
            <path d="M 145 75 Q 160 85 145 110" stroke="#64748b" strokeWidth="3.5" fill="none" strokeLinecap="round" filter="url(#dropShadow)" />
            <circle cx="145" cy="110" r="4.5" fill="#0ea5e9" filter="url(#dropShadow)">
              {isThinking && (
                <animate attributeName="opacity" values="0.3;1;0.3" dur="0.8s" repeatCount="indefinite" />
              )}
            </circle>
          </g>
          
          {/* Glowing Magnifying Glass (Independent Animation) */}
          <g className="anim-scan">
            {/* Handle */}
            <line x1="30" y1="160" x2="52" y2="138" stroke="#64748b" strokeWidth="7" strokeLinecap="round" filter="url(#dropShadow)" />
            <line x1="32" y1="158" x2="50" y2="140" stroke="#94a3b8" strokeWidth="3" strokeLinecap="round" />
            
            {/* Glass frame */}
            <circle cx="58" cy="132" r="16" fill="rgba(14, 165, 233, 0.15)" stroke="#0ea5e9" strokeWidth="4.5" filter="url(#dropShadow)" />
            <circle cx="58" cy="132" r="13" fill="none" stroke="#38bdf8" strokeWidth="1.5" opacity="0.8" />
            
            {/* Scanning radar effect */}
            {isThinking && (
              <circle cx="58" cy="132" r="10" fill="none" stroke="#2dd4bf" strokeWidth="2">
                <animate attributeName="r" values="0;22" dur="1.2s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="1;0" dur="1.2s" repeatCount="indefinite" />
              </circle>
            )}
            
            {/* Glass reflection line */}
            <path d="M 47 122 Q 53 118 62 120" stroke="white" strokeWidth="2" fill="none" strokeLinecap="round" opacity="0.6" />
          </g>

        </svg>
      </div>
    </div>
  );
}