// SVG shape components for different node types - simplified for better readability

export const DatabaseShape = ({ color, label, type }) => (
  <svg width="250" height="100" viewBox="0 0 250 100">
    {/* Simple database cylinder */}
    <ellipse cx="125" cy="25" rx="90" ry="12" fill={color} stroke="#000" strokeWidth="2" />
    <rect x="35" y="25" width="180" height="50" fill={color} stroke="none" />
    <ellipse cx="125" cy="75" rx="90" ry="12" fill={color} stroke="#000" strokeWidth="2" />
    <line x1="35" y1="25" x2="35" y2="75" stroke="#000" strokeWidth="2" />
    <line x1="215" y1="25" x2="215" y2="75" stroke="#000" strokeWidth="2" />

    {/* Text with white background for better readability */}
    <rect x="60" y="38" width="130" height="30" fill="rgba(255, 255, 255, 0.95)" rx="4" />
    <text x="125" y="52" textAnchor="middle" fill="#000" fontSize="15" fontWeight="600">{label}</text>
    <text x="125" y="66" textAnchor="middle" fill="#000" fontSize="11" fontWeight="500" opacity="0.7">{type.toUpperCase()}</text>
  </svg>
);

export const CloudShape = ({ color, label, type }) => (
  <svg width="250" height="100" viewBox="0 0 250 100">
    {/* Simple cloud shape for CDN/LoadBalancer */}
    <path
      d="M 60,50 Q 60,30 80,30 Q 80,15 100,15 Q 120,15 125,25 Q 135,20 145,25 Q 155,15 170,25 Q 190,25 190,45 Q 200,45 200,60 Q 200,75 185,75 L 65,75 Q 50,75 50,60 Q 50,50 60,50 Z"
      fill={color}
      stroke="#000"
      strokeWidth="2"
    />

    {/* Text with white background */}
    <rect x="85" y="40" width="80" height="28" fill="rgba(255, 255, 255, 0.95)" rx="4" />
    <text x="125" y="53" textAnchor="middle" fill="#000" fontSize="15" fontWeight="600">{label}</text>
    <text x="125" y="66" textAnchor="middle" fill="#000" fontSize="11" fontWeight="500" opacity="0.7">{type.toUpperCase()}</text>
  </svg>
);

export const HexagonShape = ({ color, label, type }) => (
  <svg width="250" height="100" viewBox="0 0 250 100">
    {/* Hexagon for API/Gateway/Cache */}
    <polygon
      points="50,50 80,15 170,15 200,50 170,85 80,85"
      fill={color}
      stroke="#000"
      strokeWidth="2"
    />

    {/* Text with white background */}
    <rect x="85" y="36" width="80" height="28" fill="rgba(255, 255, 255, 0.95)" rx="4" />
    <text x="125" y="50" textAnchor="middle" fill="#000" fontSize="15" fontWeight="600">{label}</text>
    <text x="125" y="63" textAnchor="middle" fill="#000" fontSize="11" fontWeight="500" opacity="0.7">{type.toUpperCase()}</text>
  </svg>
);

export const QueueShape = ({ color, label, type }) => (
  <svg width="250" height="100" viewBox="0 0 250 100">
    {/* Simplified queue - single rectangle with arrow */}
    <rect x="50" y="25" width="100" height="50" fill={color} stroke="#000" strokeWidth="2" rx="6" />

    {/* Arrow pointing right */}
    <path d="M 160,50 L 190,50 M 185,43 L 195,50 L 185,57" stroke="#000" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />

    {/* Text with white background */}
    <rect x="60" y="36" width="80" height="28" fill="rgba(255, 255, 255, 0.95)" rx="4" />
    <text x="100" y="50" textAnchor="middle" fill="#000" fontSize="15" fontWeight="600">{label}</text>
    <text x="100" y="63" textAnchor="middle" fill="#000" fontSize="11" fontWeight="500" opacity="0.7">{type.toUpperCase()}</text>
  </svg>
);

export const ServerShape = ({ color, label, type }) => (
  <svg width="250" height="100" viewBox="0 0 250 100">
    {/* Simple server rack - cleaner design */}
    <rect x="50" y="15" width="150" height="20" fill={color} stroke="#000" strokeWidth="2" rx="4" />
    <rect x="50" y="40" width="150" height="20" fill={color} stroke="#000" strokeWidth="2" rx="4" />
    <rect x="50" y="65" width="150" height="20" fill={color} stroke="#000" strokeWidth="2" rx="4" />

    {/* Minimal indicator dots - only on middle rack */}
    <circle cx="60" cy="50" r="2.5" fill="#000" opacity="0.3" />
    <circle cx="68" cy="50" r="2.5" fill="#000" opacity="0.3" />

    {/* Text with white background */}
    <rect x="85" y="36" width="80" height="28" fill="rgba(255, 255, 255, 0.95)" rx="4" />
    <text x="125" y="50" textAnchor="middle" fill="#000" fontSize="15" fontWeight="600">{label}</text>
    <text x="125" y="63" textAnchor="middle" fill="#000" fontSize="11" fontWeight="500" opacity="0.7">{type.toUpperCase()}</text>
  </svg>
);

export const StorageShape = ({ color, label, type }) => (
  <svg width="250" height="100" viewBox="0 0 250 100">
    {/* Simple storage box */}
    <rect x="50" y="25" width="150" height="50" fill={color} stroke="#000" strokeWidth="2" rx="6" />

    {/* Text with white background */}
    <rect x="85" y="36" width="80" height="28" fill="rgba(255, 255, 255, 0.95)" rx="4" />
    <text x="125" y="50" textAnchor="middle" fill="#000" fontSize="15" fontWeight="600">{label}</text>
    <text x="125" y="63" textAnchor="middle" fill="#000" fontSize="11" fontWeight="500" opacity="0.7">{type.toUpperCase()}</text>
  </svg>
);

export const DefaultShape = ({ color, label, type }) => (
  <svg width="250" height="100" viewBox="0 0 250 100">
    {/* Default rounded rectangle */}
    <rect x="40" y="20" width="170" height="60" fill={color} stroke="#000" strokeWidth="2" rx="8" />

    {/* Text with white background */}
    <rect x="75" y="36" width="100" height="28" fill="rgba(255, 255, 255, 0.95)" rx="4" />
    <text x="125" y="50" textAnchor="middle" fill="#000" fontSize="15" fontWeight="600">{label}</text>
    <text x="125" y="63" textAnchor="middle" fill="#000" fontSize="11" fontWeight="500" opacity="0.7">{type.toUpperCase()}</text>
  </svg>
);
