import React, { useEffect, useState } from 'react';
import { Shield, FileSearch, Zap, List } from 'lucide-react';

export default function OnboardingModal() {
  const [isVisible, setIsVisible] = useState(false);
  const [isClosing, setIsClosing] = useState(false);

  useEffect(() => {
    const hasSeen = localStorage.getItem('hasSeenOnboarding');
    if (!hasSeen) {
      // Small delay for smooth entry
      const timer = setTimeout(() => setIsVisible(true), 300);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleClose = () => {
    setIsClosing(true);
    localStorage.setItem('hasSeenOnboarding', 'true');
    setTimeout(() => {
      setIsVisible(false);
    }, 400); // Wait for fade out animation
  };

  if (!isVisible) return null;

  return (
    <div 
      className={`fixed inset-0 z-50 flex items-center justify-center p-4 bg-brand-dark/60 backdrop-blur-sm transition-opacity duration-400 ${isClosing ? 'opacity-0' : 'opacity-100 animate-fade-in'}`}
    >
      <div 
        className={`glass-panel w-full max-w-2xl overflow-hidden rounded-2xl shadow-glass transition-transform duration-400 ${isClosing ? 'scale-95' : 'animate-slide-up'}`}
      >
        <div className="bg-brand-dark p-8 md:p-10 text-white relative overflow-hidden">
          {/* Decorative background elements */}
          <div className="absolute top-0 right-0 -translate-y-1/4 translate-x-1/4 w-64 h-64 bg-primary-500/20 rounded-full blur-3xl" />
          <div className="absolute bottom-0 left-0 translate-y-1/4 -translate-x-1/4 w-48 h-48 bg-brand-light/30 rounded-full blur-2xl" />
          
          <div className="relative z-10">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-3">
              Welcome to <span className="text-primary-300">MedAnnotate AI</span>
            </h2>
            <p className="text-slate-300 text-lg max-w-lg leading-relaxed">
              Your intelligent medical document processing and annotation workspace.
            </p>
          </div>
        </div>

        <div className="p-8 md:p-10 bg-white/95">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-10">
            <FeatureItem 
              icon={<Shield className="w-6 h-6 text-primary-600" />}
              title="Automated Segmentation"
              desc="Detects and segments medical visits automatically from complex PDFs."
            />
            <FeatureItem 
              icon={<FileSearch className="w-6 h-6 text-brand-light" />}
              title="Multi-page Tracking"
              desc="Applies intelligent annotations seamlessly across multi-page records."
            />
            <FeatureItem 
              icon={<Zap className="w-6 h-6 text-amber-500" />}
              title="Instant Navigation"
              desc="Jump between patient visits instantly using generated hyperlinks."
            />
            <FeatureItem 
              icon={<List className="w-6 h-6 text-emerald-600" />}
              title="Versatile Processing"
              desc="Handles both scanned OCR documents and native digital PDFs."
            />
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-end gap-4 mt-8 pt-6 border-t border-slate-100">
            <button
              onClick={handleClose}
              className="text-slate-500 hover:text-slate-800 font-medium transition-colors px-4 py-2"
            >
              Don't show again
            </button>
            <button
              onClick={handleClose}
              className="bg-brand-dark hover:bg-brand-blue text-white font-semibold py-3 px-8 rounded-xl shadow-soft hover:shadow-lg transition-all hover:-translate-y-0.5"
            >
              Get Started
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function FeatureItem({ icon, title, desc }) {
  return (
    <div className="flex items-start gap-4">
      <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-slate-50 flex items-center justify-center border border-slate-100 shadow-sm">
        {icon}
      </div>
      <div>
        <h3 className="font-semibold text-slate-800 mb-1">{title}</h3>
        <p className="text-slate-500 text-sm leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}
