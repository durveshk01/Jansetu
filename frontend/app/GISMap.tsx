'use client';
import {MapContainer,TileLayer,Marker,Popup} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
const colors:Record<string,string>={Critical:'#c62828',High:'#ef6c00',Medium:'#d4a900',Low:'#1976d2'};
function icon(color:string){return L.divIcon({className:'',html:`<span style="display:block;width:15px;height:15px;background:${color};border:2px solid white;border-radius:50%;box-shadow:0 1px 5px #333"></span>`,iconSize:[15,15],iconAnchor:[7,7]})}
export default function GISMap({features}:{features:any[]}){return <MapContainer center={[19.076,72.877]} zoom={12} scrollWheelZoom className="leaflet-map"><TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"/>{features.map((f:any)=><Marker key={f.properties.id} position={[f.geometry.coordinates[1],f.geometry.coordinates[0]]} icon={icon(colors[f.properties.priority]||colors.Low)}><Popup><b>{f.properties.tracking_id}</b><br/>{f.properties.title}<br/>{f.properties.category}<br/>{f.properties.priority} · {f.properties.status}</Popup></Marker>)}</MapContainer>}
