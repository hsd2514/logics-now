// Indian city coordinates for 3D globe visualization
export const CITY_COORDINATES = {
  // Major cities
  'Mumbai': { lat: 19.0760, lng: 72.8777 },
  'Delhi': { lat: 28.7041, lng: 77.1025 },
  'Bangalore': { lat: 12.9716, lng: 77.5946 },
  'Hyderabad': { lat: 17.3850, lng: 78.4867 },
  'Chennai': { lat: 13.0827, lng: 80.2707 },
  'Kolkata': { lat: 22.5726, lng: 88.3639 },
  'Pune': { lat: 18.5204, lng: 73.8567 },
  'Ahmedabad': { lat: 23.0225, lng: 72.5714 },
  'Jaipur': { lat: 26.9124, lng: 75.7873 },
  'Surat': { lat: 21.1702, lng: 72.8311 },
  
  // Additional cities
  'Lucknow': { lat: 26.8467, lng: 80.9462 },
  'Kanpur': { lat: 26.4499, lng: 80.3319 },
  'Nagpur': { lat: 21.1458, lng: 79.0882 },
  'Indore': { lat: 22.7196, lng: 75.8577 },
  'Thane': { lat: 19.2183, lng: 72.9781 },
  'Bhopal': { lat: 23.2599, lng: 77.4126 },
  'Visakhapatnam': { lat: 17.6868, lng: 83.2185 },
  'Patna': { lat: 25.5941, lng: 85.1376 },
  'Vadodara': { lat: 22.3072, lng: 73.1812 },
  'Ghaziabad': { lat: 28.6692, lng: 77.4538 },
};

/**
 * Get coordinates for a city name (case-insensitive)
 * @param {string} cityName - City name
 * @returns {{lat: number, lng: number} | null} Coordinates or null if not found
 */
export function getCityCoords(cityName) {
  if (!cityName) return null;
  
  // Normalize city name (trim, capitalize)
  const normalized = cityName.trim();
  
  // Try exact match first
  if (CITY_COORDINATES[normalized]) {
    return CITY_COORDINATES[normalized];
  }
  
  // Try case-insensitive match
  const key = Object.keys(CITY_COORDINATES).find(
    k => k.toLowerCase() === normalized.toLowerCase()
  );
  
  return key ? CITY_COORDINATES[key] : null;
}

/**
 * Parse route string (e.g., "Mumbai-Delhi") into origin and destination
 * @param {string} routeStr - Route string in format "Origin-Destination"
 * @returns {{origin: string, destination: string} | null}
 */
export function parseRoute(routeStr) {
  if (!routeStr || typeof routeStr !== 'string') return null;
  
  const parts = routeStr.split('-').map(s => s.trim());
  if (parts.length >= 2) {
    return {
      origin: parts[0],
      destination: parts[1]
    };
  }
  
  return null;
}

/**
 * Get color based on risk score (0-100)
 * @param {number} riskScore - Risk score
 * @returns {string} Hex color
 */
export function getRiskColor(riskScore) {
  if (riskScore >= 70) return '#ef4444'; // Red (high risk)
  if (riskScore >= 40) return '#f59e0b'; // Orange (medium risk)
  return '#10b981'; // Green (low risk)
}
