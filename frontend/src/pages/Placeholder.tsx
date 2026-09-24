import { Sparkles } from "lucide-react";

export default function Placeholder({ title }: { title: string }) {
  return (
    <div className="ssp-placeholder">
      <div className="ssp-placeholder-icon">
        <Sparkles size={28} />
      </div>
      <h1>{title}</h1>
      <p>This module is ready for implementation.</p>
    </div>
  );
}