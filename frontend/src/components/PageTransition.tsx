import { type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import "./PageTransition.css";

type Variant = "fade" | "slide-right" | "rise" | "scale";

function pickVariant(pathname: string): Variant {
  if (pathname.startsWith("/scheduling")) return "slide-right";
  if (pathname.startsWith("/academics"))  return "rise";
  if (pathname.startsWith("/library"))    return "scale";
  if (pathname.startsWith("/platform"))   return "fade";
  if (pathname.startsWith("/login"))      return "fade";
  return "fade";
}

export default function PageTransition({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  const variant = pickVariant(pathname);
  return (
    <div key={pathname} className={`page-transition pt-${variant}`}>
      {children}
    </div>
  );
}