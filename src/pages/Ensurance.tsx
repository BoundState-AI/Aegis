/**
 * BoundState Ensurance™ Landing Page
 * 
 * "Insurance prices the risk. Ensurance ensures it doesn't happen."
 * 
 * Marketing landing page matching BoundState.ai brand aesthetic.
 */

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { 
  Shield, 
  Flame, 
  ArrowRight, 
  CheckCircle2, 
  XCircle,
  FlaskConical,
  Scale,
  TrendingUp,
  Zap,
  FileText,
  Building2,
  ExternalLink
} from "lucide-react";

// BoundState brand colors
const BRAND = {
  blue: "#3b82f6",
  dark: "#0a0a0a",
  gray: "#71717a",
  white: "#ffffff",
};

const Ensurance = () => {
  const [scrolled, setScrolled] = useState(false);
  
  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white overflow-x-hidden">
      {/* Neural network background */}
      <div className="fixed inset-0 z-0">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-zinc-800/20 via-zinc-900/40 to-[#0a0a0a]" />
        <svg className="absolute inset-0 w-full h-full opacity-20" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="neural-grid" x="0" y="0" width="100" height="100" patternUnits="userSpaceOnUse">
              <circle cx="50" cy="50" r="1" fill="rgba(255,255,255,0.3)" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#neural-grid)" />
        </svg>
      </div>

      {/* Navigation */}
      <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? 'bg-[#0a0a0a]/95 backdrop-blur-md border-b border-zinc-800' : 'bg-transparent'
      }`}>
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <a href="https://boundstate.ai" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <svg width="32" height="32" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M 25 35 L 25 75 Q 25 80 30 80 L 70 80 Q 75 80 75 75 L 75 55 L 75 50 L 70 45 L 65 40" stroke="#3b82f6" strokeWidth="4" strokeLinecap="square" fill="none"/>
              <line x1="32" y1="70" x2="68" y2="70" stroke="#60a5fa" strokeWidth="3"/>
              <line x1="38" y1="58" x2="62" y2="58" stroke="#93c5fd" strokeWidth="2" opacity="0.7"/>
            </svg>
            <span className="text-lg font-bold tracking-tight">boundstate.ai</span>
          </a>
          <Button 
            className="bg-blue-500 hover:bg-blue-600 text-white rounded-lg px-6"
            onClick={() => window.location.href = 'mailto:joe@boundstate.ai?subject=Ensurance%20Inquiry'}
          >
            Get Started
          </Button>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center pt-20 z-10">
        <div className="container mx-auto px-6">
          <div className="max-w-4xl mx-auto text-center">
            {/* Category Label */}
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/10 border border-blue-500/30 mb-8">
              <Shield className="w-4 h-4 text-blue-400" />
              <span className="text-sm font-medium text-blue-400">A New Category in Chemical Intelligence</span>
            </div>
            
            {/* Main Headline */}
            <h1 className="text-5xl md:text-7xl lg:text-8xl font-black tracking-tight mb-6 leading-[0.9]">
              <span className="text-zinc-600 line-through decoration-red-500/60 decoration-4">In</span>
              <span className="text-white">surance</span>
              <br />
              <span className="text-zinc-500 text-3xl md:text-4xl font-normal">becomes</span>
              <br />
              <span className="text-white">Ensurance</span>
              <span className="text-blue-500">™</span>
            </h1>
            
            {/* Tagline */}
            <p className="text-xl md:text-2xl text-zinc-400 max-w-2xl mx-auto mb-12 leading-relaxed">
              Insurance prices the risk.
              <br />
              <span className="text-white font-medium">Ensurance ensures it doesn't happen.</span>
            </p>
            
            {/* CTA */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button 
                size="lg" 
                className="bg-blue-500 hover:bg-blue-600 text-white px-8 py-6 text-lg rounded-lg shadow-lg shadow-blue-500/20"
                onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })}
              >
                See How It Works
                <ArrowRight className="ml-2 w-5 h-5" />
              </Button>
              <Button 
                variant="ghost" 
                size="lg"
                className="text-zinc-400 hover:text-white hover:bg-zinc-800 px-8 py-6 text-lg"
                onClick={() => window.location.href = 'mailto:joe@boundstate.ai?subject=Ensurance%20Demo%20Request'}
              >
                Schedule a Call
              </Button>
            </div>
          </div>
        </div>
        
        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
          <div className="w-6 h-10 rounded-full border-2 border-zinc-700 flex items-start justify-center p-2">
            <div className="w-1.5 h-2.5 bg-zinc-600 rounded-full" />
          </div>
        </div>
      </section>

      {/* The Problem */}
      <section className="relative py-24 z-10">
        <div className="container mx-auto px-6">
          <div className="max-w-5xl mx-auto">
            <div className="grid md:grid-cols-2 gap-12 items-center">
              <div>
                <p className="text-blue-400 font-medium mb-4">THE PROBLEM</p>
                <h2 className="text-4xl md:text-5xl font-bold mb-6 leading-tight">
                  $175 Billion in PFAS Liability
                </h2>
                <p className="text-xl text-zinc-400 mb-6 leading-relaxed">
                  Water districts alone face an estimated $175B in remediation costs. Chemical manufacturers are next.
                </p>
                <p className="text-lg text-zinc-500">
                  Current tools are reactive. Regulatory trackers wait for restrictions. Insurance actuaries price the inevitable. Remediation companies clean up the mess.
                </p>
              </div>
              <div className="relative">
                <Card className="bg-zinc-900/80 border-zinc-800">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-3 mb-6">
                      <div className="w-10 h-10 rounded-lg bg-red-500/10 flex items-center justify-center">
                        <Flame className="w-5 h-5 text-red-500" />
                      </div>
                      <span className="text-xl font-semibold text-zinc-200">Fire Extinguisher Approach</span>
                    </div>
                    <ul className="space-y-4 text-zinc-400">
                      <li className="flex items-start gap-3">
                        <XCircle className="w-5 h-5 text-red-500/70 mt-0.5 flex-shrink-0" />
                        <span>Wait for contamination to occur</span>
                      </li>
                      <li className="flex items-start gap-3">
                        <XCircle className="w-5 h-5 text-red-500/70 mt-0.5 flex-shrink-0" />
                        <span>React to regulatory action</span>
                      </li>
                      <li className="flex items-start gap-3">
                        <XCircle className="w-5 h-5 text-red-500/70 mt-0.5 flex-shrink-0" />
                        <span>Price the risk, accept the liability</span>
                      </li>
                      <li className="flex items-start gap-3">
                        <XCircle className="w-5 h-5 text-red-500/70 mt-0.5 flex-shrink-0" />
                        <span>Clean up after the lawsuit</span>
                      </li>
                    </ul>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* The Solution */}
      <section id="how-it-works" className="relative py-24 z-10">
        <div className="container mx-auto px-6">
          <div className="max-w-5xl mx-auto">
            <div className="grid md:grid-cols-2 gap-12 items-center">
              <div className="order-2 md:order-1">
                <Card className="bg-zinc-900/80 border-zinc-800">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-3 mb-6">
                      <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                        <Shield className="w-5 h-5 text-blue-500" />
                      </div>
                      <span className="text-xl font-semibold text-zinc-200">Smoke Detector Approach</span>
                    </div>
                    <ul className="space-y-4 text-zinc-400">
                      <li className="flex items-start gap-3">
                        <CheckCircle2 className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
                        <span>Predict which compounds become problems</span>
                      </li>
                      <li className="flex items-start gap-3">
                        <CheckCircle2 className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
                        <span>Track science before it becomes admissible</span>
                      </li>
                      <li className="flex items-start gap-3">
                        <CheckCircle2 className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
                        <span>Engineer the liability out of existence</span>
                      </li>
                      <li className="flex items-start gap-3">
                        <CheckCircle2 className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
                        <span>Change the process before the lawsuit</span>
                      </li>
                    </ul>
                  </CardContent>
                </Card>
              </div>
              <div className="order-1 md:order-2">
                <p className="text-blue-400 font-medium mb-4">THE SOLUTION</p>
                <h2 className="text-4xl md:text-5xl font-bold mb-6 leading-tight">
                  Chemical Foresight
                </h2>
                <p className="text-xl text-zinc-400 mb-6 leading-relaxed">
                  We connect chemistry to courtrooms. Track scientific literature. Map degradation pathways. Predict which molecules become lawsuits—<span className="text-white">before</span> the science is admissible.
                </p>
                <p className="text-lg text-zinc-500">
                  You don't price the risk. You prevent it.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* The Stack */}
      <section className="relative py-24 z-10 border-t border-zinc-800/50">
        <div className="container mx-auto px-6">
          <div className="max-w-4xl mx-auto text-center mb-16">
            <p className="text-blue-400 font-medium mb-4">THE PLATFORM</p>
            <h2 className="text-4xl md:text-5xl font-bold mb-4">Full-Stack Liability Intelligence</h2>
            <p className="text-xl text-zinc-400">
              The only platform connecting chemistry databases to kinetic modeling to litigation prediction.
            </p>
          </div>
          
          <div className="max-w-5xl mx-auto grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                icon: FlaskConical,
                title: "Structure",
                stat: "10,974",
                unit: "compounds",
                description: "Chemical similarity search"
              },
              {
                icon: TrendingUp,
                title: "Fate",
                stat: "732",
                unit: "pathways",
                description: "Degradation evidence from 353 papers"
              },
              {
                icon: Zap,
                title: "Kinetics",
                stat: "Real-time",
                unit: "prediction",
                description: "Rate constants at process conditions"
              },
              {
                icon: Scale,
                title: "Signal",
                stat: "2+ years",
                unit: "early warning",
                description: "Publication dynamics → litigation"
              }
            ].map((item, i) => (
              <Card key={i} className="bg-zinc-900/60 border-zinc-800 hover:border-zinc-700 transition-colors">
                <CardContent className="p-6">
                  <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center mb-4">
                    <item.icon className="w-5 h-5 text-blue-400" />
                  </div>
                  <h3 className="text-lg font-semibold mb-1">{item.title}</h3>
                  <p className="text-2xl font-bold text-white mb-1">{item.stat}</p>
                  <p className="text-sm text-zinc-500 mb-3">{item.unit}</p>
                  <p className="text-sm text-zinc-400">{item.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Comparison Table */}
      <section className="relative py-24 z-10">
        <div className="container mx-auto px-6">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-16">
              <p className="text-blue-400 font-medium mb-4">THE DIFFERENCE</p>
              <h2 className="text-4xl md:text-5xl font-bold">Insurance vs. Ensurance</h2>
            </div>
            
            <div className="grid md:grid-cols-2 gap-8">
              {/* Insurance Column */}
              <div className="space-y-4">
                <div className="text-center pb-4 border-b border-zinc-800">
                  <h3 className="text-2xl font-bold text-zinc-500">Insurance</h3>
                  <p className="text-zinc-600 text-sm">Reactive risk transfer</p>
                </div>
                {[
                  "Prices existing exposure",
                  "Reserves for expected claims",
                  "Serves insurers and actuaries",
                  "Accepts liability as inevitable",
                  "Revenue tied to risk existing"
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-zinc-900/50">
                    <XCircle className="w-5 h-5 text-zinc-600 flex-shrink-0" />
                    <span className="text-zinc-500">{item}</span>
                  </div>
                ))}
              </div>
              
              {/* Ensurance Column */}
              <div className="space-y-4">
                <div className="text-center pb-4 border-b border-zinc-800">
                  <h3 className="text-2xl font-bold text-white">Ensurance<span className="text-blue-500">™</span></h3>
                  <p className="text-zinc-400 text-sm">Proactive liability prevention</p>
                </div>
                {[
                  "Predicts emerging exposure",
                  "Engineers out the cause",
                  "Serves chemical manufacturers",
                  "Makes liability avoidable",
                  "Revenue tied to prevention"
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-blue-500/5 border border-blue-500/10">
                    <CheckCircle2 className="w-5 h-5 text-blue-500 flex-shrink-0" />
                    <span className="text-zinc-300">{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Quote Section */}
      <section className="relative py-24 z-10 border-t border-zinc-800/50">
        <div className="container mx-auto px-6">
          <div className="max-w-3xl mx-auto text-center">
            <blockquote className="text-2xl md:text-4xl font-light text-zinc-300 leading-relaxed mb-8">
              "Insurance is a tax on inevitable harm.
              <br />
              <span className="text-white font-medium">We make the harm not inevitable.</span>"
            </blockquote>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative py-24 z-10">
        <div className="container mx-auto px-6">
          <div className="max-w-4xl mx-auto">
            <Card className="bg-zinc-900/80 border-zinc-800 overflow-hidden relative">
              <CardContent className="p-12 text-center">
                <Building2 className="w-12 h-12 text-blue-400 mx-auto mb-6" />
                <h2 className="text-3xl md:text-4xl font-bold mb-4">Ready to move from insurance to ensurance?</h2>
                <p className="text-xl text-zinc-400 mb-8 max-w-2xl mx-auto">
                  We work with chemical manufacturers who want to know which molecules to stop making before they become the next GenX.
                </p>
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                  <Button 
                    size="lg"
                    className="bg-blue-500 hover:bg-blue-600 text-white px-8 py-6 text-lg rounded-lg"
                    onClick={() => window.location.href = 'mailto:joe@boundstate.ai?subject=Ensurance%20Demo%20Request'}
                  >
                    <FileText className="mr-2 w-5 h-5" />
                    Request a Demo
                  </Button>
                  <Button 
                    variant="outline" 
                    size="lg"
                    className="border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:text-white px-8 py-6 text-lg rounded-lg"
                    onClick={() => window.location.href = 'mailto:joe@boundstate.ai?subject=Ensurance%20Inquiry'}
                  >
                    Schedule a Call
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative py-12 border-t border-zinc-800 z-10">
        <div className="container mx-auto px-6">
          <div className="flex flex-col items-center gap-6">
            {/* Logo */}
            <a href="https://boundstate.ai" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
              <svg width="32" height="32" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M 25 35 L 25 75 Q 25 80 30 80 L 70 80 Q 75 80 75 75 L 75 55 L 75 50 L 70 45 L 65 40" stroke="#3b82f6" strokeWidth="4" strokeLinecap="square" fill="none"/>
                <line x1="32" y1="70" x2="68" y2="70" stroke="#60a5fa" strokeWidth="3"/>
                <line x1="38" y1="58" x2="62" y2="58" stroke="#93c5fd" strokeWidth="2" opacity="0.7"/>
              </svg>
              <span className="text-lg font-bold tracking-tight">boundstate.ai</span>
            </a>
            
            {/* Tagline */}
            <div className="text-center">
              <p className="text-zinc-400 text-sm">
                BoundState™.ai — Purpose-Built AI for Regulated, High-Stakes Engineering
              </p>
              <p className="text-zinc-500 text-sm mt-1">
                Compliant by design. Transparent by necessity.
              </p>
            </div>
            
            {/* Links */}
            <div className="flex items-center gap-6 text-sm">
              <a href="mailto:joe@boundstate.ai" className="text-zinc-500 hover:text-white transition-colors">
                Contact
              </a>
              <a href="https://boundstate.ai" className="text-zinc-500 hover:text-white transition-colors flex items-center gap-1">
                Home <ExternalLink className="w-3 h-3" />
              </a>
            </div>
            
            {/* Copyright */}
            <div className="text-zinc-600 text-xs">
              © 2025 BoundState, Inc. All rights reserved.
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Ensurance;
