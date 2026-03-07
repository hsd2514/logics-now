import React, { useEffect, useRef, useState } from 'react';
import Globe from 'react-globe.gl';
import { getCityCoords, parseRoute, getRiskColor } from '../lib/cityCoordinates';
import { Card } from './ui/card';

/**
 * 3D Globe visualization showing vendor shipping routes
 * @param {Object} props
 * @param {Array} props.vendors - Array of vendor profiles with route_patterns
 * @param {number} props.height - Globe height in pixels (default: 600)
 */
export function VendorRouteGlobe({ vendors = [], height = 600 }) {
  const globeEl = useRef();
  const [arcsData, setArcsData] = useState([]);
  const [pointsData, setPointsData] = useState([]);

  useEffect(() => {
    // Auto-rotate globe
    if (globeEl.current) {
      globeEl.current.controls().autoRotate = true;
      globeEl.current.controls().autoRotateSpeed = 0.5;
    }
  }, []);

  useEffect(() => {
    if (!vendors || vendors.length === 0) return;

    // Build arcs data from vendor routes
    const arcs = [];
    const citySet = new Set();

    vendors.forEach(vendor => {
      const routes = vendor.route_patterns || [];
      
      routes.forEach(routeInfo => {
        const parsed = parseRoute(routeInfo.route);
        if (!parsed) return;

        const startCoords = getCityCoords(parsed.origin);
        const endCoords = getCityCoords(parsed.destination);

        if (startCoords && endCoords) {
          arcs.push({
            startLat: startCoords.lat,
            startLng: startCoords.lng,
            endLat: endCoords.lat,
            endLng: endCoords.lng,
            color: getRiskColor(vendor.risk_score),
            vendor: vendor.vendor_name,
            route: routeInfo.route,
            count: routeInfo.count,
            riskScore: vendor.risk_score
          });

          // Track cities for points
          citySet.add(parsed.origin);
          citySet.add(parsed.destination);
        }
      });
    });

    // Build points data from unique cities
    const points = Array.from(citySet).map(city => {
      const coords = getCityCoords(city);
      if (!coords) return null;

      // Count routes through this city
      const routeCount = arcs.filter(
        arc => 
          (arc.startLat === coords.lat && arc.startLng === coords.lng) ||
          (arc.endLat === coords.lat && arc.endLng === coords.lng)
      ).length;

      return {
        lat: coords.lat,
        lng: coords.lng,
        city,
        size: Math.max(0.5, routeCount * 0.3),
        color: '#60a5fa'
      };
    }).filter(Boolean);

    setArcsData(arcs);
    setPointsData(points);
  }, [vendors]);

  if (!vendors || vendors.length === 0) {
    return (
      <Card className="p-6">
        <div className="text-center text-muted-foreground">
          No vendor route data available
        </div>
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden">
      <div style={{ height: `${height}px`, width: '100%' }}>
        <Globe
          ref={globeEl}
          globeImageUrl="//unpkg.com/three-globe/example/img/earth-night.jpg"
          backgroundColor="rgba(0,0,0,0)"
          
          // Arc (route) configuration
          arcsData={arcsData}
          arcColor="color"
          arcDashLength={0.4}
          arcDashGap={0.2}
          arcDashAnimateTime={2000}
          arcStroke={0.5}
          arcAltitudeAutoScale={0.3}
          arcLabel={d => `
            <div style="background: rgba(0,0,0,0.8); padding: 8px; border-radius: 4px; color: white;">
              <strong>${d.vendor}</strong><br/>
              ${d.route}<br/>
              Shipments: ${d.count}<br/>
              Risk Score: ${d.riskScore.toFixed(1)}
            </div>
          `}
          
          // Point (city) configuration
          pointsData={pointsData}
          pointLat="lat"
          pointLng="lng"
          pointColor="color"
          pointAltitude={0}
          pointRadius="size"
          pointLabel={d => `
            <div style="background: rgba(0,0,0,0.8); padding: 6px; border-radius: 4px; color: white;">
              <strong>${d.city}</strong>
            </div>
          `}
          
          // Atmosphere
          atmosphereColor="#3b82f6"
          atmosphereAltitude={0.15}
        />
      </div>
      
      {/* Legend */}
      <div className="p-4 bg-muted/50 border-t flex items-center justify-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-8 h-1 bg-green-500 rounded"></div>
          <span>Low Risk (&lt;40)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-1 bg-orange-500 rounded"></div>
          <span>Medium Risk (40-70)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-1 bg-red-500 rounded"></div>
          <span>High Risk (&gt;70)</span>
        </div>
      </div>
    </Card>
  );
}

export default VendorRouteGlobe;
