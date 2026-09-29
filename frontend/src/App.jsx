import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import Home from "./farmer/Home.jsx";
import CropPest from "./farmer/CropPest.jsx";
import ScanPacket from "./farmer/ScanPacket.jsx";
import Result from "./farmer/Result.jsx";
import Bill from "./farmer/Bill.jsx";
import Mix from "./farmer/Mix.jsx";
import Sos from "./farmer/Sos.jsx";
import Sprays from "./farmer/Sprays.jsx";
import Passport from "./passport/Passport.jsx";

// Map + chart libraries load only for the officer dashboard, not on the farmer's phone.
const Officer = lazy(() => import("./officer/Officer.jsx"));

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/crop" element={<CropPest />} />
      <Route path="/scan" element={<ScanPacket />} />
      <Route path="/result" element={<Result />} />
      <Route path="/bill" element={<Bill />} />
      <Route path="/mix" element={<Mix />} />
      <Route path="/sos" element={<Sos />} />
      <Route path="/sprays" element={<Sprays />} />
      <Route path="/officer/*" element={<Suspense fallback={<div className="dash">Loading…</div>}><Officer /></Suspense>} />
      <Route path="/passport/:plotId" element={<Passport />} />
      <Route path="*" element={<Home />} />
    </Routes>
  );
}
