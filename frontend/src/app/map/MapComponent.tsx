"use client";

import { useEffect } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-defaulticon-compatibility/dist/leaflet-defaulticon-compatibility.css"; 
import "leaflet-defaulticon-compatibility";

export default function MapComponent({ mapData, formatPKR }: any) {
  return (
    <MapContainer center={[30.3753, 69.3451]} zoom={5} style={{ height: "100%", width: "100%", zIndex: 1 }}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {mapData.map((d: any, i: number) => {
        // Calculate circle size based on high risk count
        // and color based on total hidden income
        const radius = Math.max(10, Math.min(30, d.highRiskCount / 50));
        
        let color = "#ef4444"; // red-500
        if (d.totalHidden > 10000000000) color = "#991b1b"; // red-800
        else if (d.totalHidden > 1000000000) color = "#dc2626"; // red-600
        else if (d.totalHidden < 10000000) color = "#f87171"; // red-400

        return (
          <CircleMarker
            key={i}
            center={[d.lat, d.lon]}
            pathOptions={{ color, fillColor: color, fillOpacity: 0.7, weight: 1 }}
            radius={radius}
          >
            <Popup>
              <div className="flex flex-col gap-1 p-1 min-w-[150px]">
                <strong className="text-sm border-b pb-1 mb-1">{d.city}</strong>
                <div className="flex justify-between text-xs">
                  <span>High Risk:</span>
                  <span className="font-bold text-red-600">{d.highRiskCount}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span>Hidden Income:</span>
                  <span className="font-mono">{formatPKR(d.totalHidden)}</span>
                </div>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
