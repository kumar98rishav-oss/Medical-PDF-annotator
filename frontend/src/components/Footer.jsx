import React from "react";

export default function Footer() {
  return (
    <footer className="w-full bg-slate-50 border-t border-slate-200 py-1.5 mt-auto">
      <div className="max-w-7xl mx-auto px-4 text-center">
        <p className="text-[10px] text-slate-400 font-medium tracking-wide uppercase">
          &copy; {new Date().getFullYear()} All copyrights reserved
        </p>
      </div>
    </footer>
  );
}
