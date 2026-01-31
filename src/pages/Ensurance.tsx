/**
 * BoundState Ensurance™ Landing Page
 * 
 * "Insurance prices the risk. Ensurance ensures it doesn't happen."
 * 
 * Light theme matching BoundState.ai brand aesthetic.
 */

import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
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

const Ensurance = () => {
  const { t } = useTranslation();
  const [scrolled, setScrolled] = useState(false);
  
  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="min-h-screen bg-white text-gray-900 overflow-x-hidden">
      {/* Subtle grid background */}
      <div className="fixed inset-0 z-0">
        <div className="absolute inset-0 bg-gradient-to-b from-gray-50 to-white" />
        <div className="absolute inset-0 bg-[radial-gradient(#e5e7eb_1px,transparent_1px)] [background-size:20px_20px] opacity-50" />
      </div>

      {/* Navigation */}
      <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? 'bg-white/95 backdrop-blur-md border-b border-gray-200 shadow-sm' : 'bg-transparent'
      }`}>
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <a href="https://boundstate.ai" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <svg width="32" height="32" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M 25 35 L 25 75 Q 25 80 30 80 L 70 80 Q 75 80 75 75 L 75 55 L 75 50 L 70 45 L 65 40" stroke="#3b82f6" strokeWidth="4" strokeLinecap="square" fill="none"/>
              <line x1="32" y1="70" x2="68" y2="70" stroke="#3b82f6" strokeWidth="3"/>
              <line x1="38" y1="58" x2="62" y2="58" stroke="#60a5fa" strokeWidth="2" opacity="0.7"/>
            </svg>
            <span className="text-lg font-bold tracking-tight text-gray-900">boundstate.ai</span>
          </a>
          <Button
            className="bg-blue-500 hover:bg-blue-600 text-white rounded-lg px-6"
            onClick={() => window.location.href = 'mailto:joe@boundstate.ai?subject=Ensurance%20Inquiry'}
          >
            {t('ensurance.getStarted')}
          </Button>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center pt-20 z-10">
        <div className="container mx-auto px-6">
          <div className="max-w-4xl mx-auto text-center">
            {/* Category Label */}
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-50 border border-blue-200 mb-8">
              <Shield className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-medium text-blue-700">{t('ensurance.newCategory')}</span>
            </div>
            
            {/* Main Headline */}
            <h1 className="text-5xl md:text-7xl lg:text-8xl font-black tracking-tight mb-6 leading-[0.9]">
              <span className="text-gray-400 line-through decoration-red-500/60 decoration-4">In</span>
              <span className="text-gray-900">{t('ensurance.headline1')}</span>
              <br />
              <span className="text-gray-500 text-3xl md:text-4xl font-normal">{t('ensurance.becomes')}</span>
              <br />
              <span className="text-gray-900">Ensurance</span>
              <span className="text-blue-500">™</span>
            </h1>
            
            {/* Tagline */}
            <p className="text-xl md:text-2xl text-gray-600 max-w-2xl mx-auto mb-12 leading-relaxed">
              {t('ensurance.tagline1')}
              <br />
              <span className="text-gray-900 font-medium">{t('ensurance.tagline2')}</span>
            </p>
            
            {/* CTA */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button
                size="lg"
                className="bg-blue-500 hover:bg-blue-600 text-white px-8 py-6 text-lg rounded-lg shadow-lg shadow-blue-500/20"
                onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })}
              >
                {t('ensurance.seeHowItWorks')}
                <ArrowRight className="ml-2 w-5 h-5" />
              </Button>
              <Button
                variant="outline"
                size="lg"
                className="text-gray-600 hover:text-gray-900 border-gray-300 hover:bg-gray-50 px-8 py-6 text-lg"
                onClick={() => window.location.href = 'mailto:joe@boundstate.ai?subject=Ensurance%20Demo%20Request'}
              >
                {t('ensurance.scheduleACall')}
              </Button>
            </div>
          </div>
        </div>
        
        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
          <div className="w-6 h-10 rounded-full border-2 border-gray-300 flex items-start justify-center p-2">
            <div className="w-1.5 h-2.5 bg-gray-400 rounded-full" />
          </div>
        </div>
      </section>

      {/* The Problem */}
      <section className="relative py-24 z-10 bg-gray-50">
        <div className="container mx-auto px-6">
          <div className="max-w-5xl mx-auto">
            <div className="grid md:grid-cols-2 gap-12 items-center">
              <div>
                <p className="text-blue-600 font-semibold mb-4 uppercase tracking-wide text-sm">{t('ensurance.theProblem')}</p>
                <h2 className="text-4xl md:text-5xl font-bold mb-6 leading-tight text-gray-900">
                  {t('ensurance.problemHeadline')}
                </h2>
                <p className="text-xl text-gray-600 mb-6 leading-relaxed">
                  {t('ensurance.problemDescription')}
                </p>
                <p className="text-lg text-gray-500">
                  {t('ensurance.problemDetails')}
                </p>
              </div>
              <div className="relative">
                <Card className="bg-white border-red-200 shadow-lg">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-3 mb-6">
                      <div className="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center">
                        <Flame className="w-5 h-5 text-red-600" />
                      </div>
                      <span className="text-xl font-semibold text-gray-900">{t('ensurance.fireExtinguisherApproach')}</span>
                    </div>
                    <ul className="space-y-4 text-gray-600">
                      <li className="flex items-start gap-3">
                        <XCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                        <span>{t('ensurance.fireExtinguisher.wait')}</span>
                      </li>
                      <li className="flex items-start gap-3">
                        <XCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                        <span>{t('ensurance.fireExtinguisher.react')}</span>
                      </li>
                      <li className="flex items-start gap-3">
                        <XCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                        <span>{t('ensurance.fireExtinguisher.price')}</span>
                      </li>
                      <li className="flex items-start gap-3">
                        <XCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                        <span>{t('ensurance.fireExtinguisher.cleanup')}</span>
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
                <Card className="bg-white border-blue-200 shadow-lg">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-3 mb-6">
                      <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                        <Shield className="w-5 h-5 text-blue-600" />
                      </div>
                      <span className="text-xl font-semibold text-gray-900">{t('ensurance.smokeDetectorApproach')}</span>
                    </div>
                    <ul className="space-y-4 text-gray-600">
                      <li className="flex items-start gap-3">
                        <CheckCircle2 className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
                        <span>{t('ensurance.smokeDetector.predict')}</span>
                      </li>
                      <li className="flex items-start gap-3">
                        <CheckCircle2 className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
                        <span>{t('ensurance.smokeDetector.track')}</span>
                      </li>
                      <li className="flex items-start gap-3">
                        <CheckCircle2 className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
                        <span>{t('ensurance.smokeDetector.engineer')}</span>
                      </li>
                      <li className="flex items-start gap-3">
                        <CheckCircle2 className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
                        <span>{t('ensurance.smokeDetector.change')}</span>
                      </li>
                    </ul>
                  </CardContent>
                </Card>
              </div>
              <div className="order-1 md:order-2">
                <p className="text-blue-600 font-semibold mb-4 uppercase tracking-wide text-sm">{t('ensurance.theSolution')}</p>
                <h2 className="text-4xl md:text-5xl font-bold mb-6 leading-tight text-gray-900">
                  {t('ensurance.solutionHeadline')}
                </h2>
                <p className="text-xl text-gray-600 mb-6 leading-relaxed">
                  {t('ensurance.solutionDescription')}
                </p>
                <p className="text-lg text-gray-500">
                  {t('ensurance.solutionTagline')}
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* The Stack */}
      <section className="relative py-24 z-10 bg-gray-50">
        <div className="container mx-auto px-6">
          <div className="max-w-4xl mx-auto text-center mb-16">
            <p className="text-blue-600 font-semibold mb-4 uppercase tracking-wide text-sm">{t('ensurance.thePlatform')}</p>
            <h2 className="text-4xl md:text-5xl font-bold mb-4 text-gray-900">{t('ensurance.platformHeadline')}</h2>
            <p className="text-xl text-gray-600">
              {t('ensurance.platformDescription')}
            </p>
          </div>
          
          <div className="max-w-5xl mx-auto grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                icon: FlaskConical,
                titleKey: "ensurance.stack.structure.title",
                statKey: "ensurance.stack.structure.stat",
                unitKey: "ensurance.stack.structure.unit",
                descriptionKey: "ensurance.stack.structure.description"
              },
              {
                icon: TrendingUp,
                titleKey: "ensurance.stack.fate.title",
                statKey: "ensurance.stack.fate.stat",
                unitKey: "ensurance.stack.fate.unit",
                descriptionKey: "ensurance.stack.fate.description"
              },
              {
                icon: Zap,
                titleKey: "ensurance.stack.kinetics.title",
                statKey: "ensurance.stack.kinetics.stat",
                unitKey: "ensurance.stack.kinetics.unit",
                descriptionKey: "ensurance.stack.kinetics.description"
              },
              {
                icon: Scale,
                titleKey: "ensurance.stack.signal.title",
                statKey: "ensurance.stack.signal.stat",
                unitKey: "ensurance.stack.signal.unit",
                descriptionKey: "ensurance.stack.signal.description"
              }
            ].map((item, i) => (
              <Card key={i} className="bg-white border-gray-200 shadow-md hover:shadow-lg hover:border-blue-200 transition-all">
                <CardContent className="p-6">
                  <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center mb-4">
                    <item.icon className="w-5 h-5 text-blue-600" />
                  </div>
                  <h3 className="text-lg font-semibold mb-1 text-gray-900">{t(item.titleKey)}</h3>
                  <p className="text-2xl font-bold text-blue-600 mb-1">{t(item.statKey)}</p>
                  <p className="text-sm text-gray-500 mb-3">{t(item.unitKey)}</p>
                  <p className="text-sm text-gray-600">{t(item.descriptionKey)}</p>
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
              <p className="text-blue-600 font-semibold mb-4 uppercase tracking-wide text-sm">{t('ensurance.theDifference')}</p>
              <h2 className="text-4xl md:text-5xl font-bold text-gray-900">{t('ensurance.comparisonHeadline')}</h2>
            </div>
            
            <div className="grid md:grid-cols-2 gap-8">
              {/* Insurance Column */}
              <div className="space-y-4">
                <div className="text-center pb-4 border-b border-gray-200">
                  <h3 className="text-2xl font-bold text-gray-400">{t('ensurance.insurance.title')}</h3>
                  <p className="text-gray-500 text-sm">{t('ensurance.insurance.subtitle')}</p>
                </div>
                {(t('ensurance.insurance.items', { returnObjects: true }) as string[]).map((item, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-gray-50">
                    <XCircle className="w-5 h-5 text-gray-400 flex-shrink-0" />
                    <span className="text-gray-500">{item}</span>
                  </div>
                ))}
              </div>
              
              {/* Ensurance Column */}
              <div className="space-y-4">
                <div className="text-center pb-4 border-b border-blue-200">
                  <h3 className="text-2xl font-bold text-gray-900">{t('ensurance.ensuranceColumn.title')}<span className="text-blue-500">™</span></h3>
                  <p className="text-gray-600 text-sm">{t('ensurance.ensuranceColumn.subtitle')}</p>
                </div>
                {(t('ensurance.ensuranceColumn.items', { returnObjects: true }) as string[]).map((item, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-blue-50 border border-blue-100">
                    <CheckCircle2 className="w-5 h-5 text-blue-500 flex-shrink-0" />
                    <span className="text-gray-700">{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Quote Section */}
      <section className="relative py-24 z-10 bg-gray-900">
        <div className="container mx-auto px-6">
          <div className="max-w-3xl mx-auto text-center">
            <blockquote className="text-2xl md:text-4xl font-light text-gray-300 leading-relaxed mb-8">
              "{t('ensurance.quote1')}
              <br />
              <span className="text-white font-medium">{t('ensurance.quote2')}</span>"
            </blockquote>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative py-24 z-10">
        <div className="container mx-auto px-6">
          <div className="max-w-4xl mx-auto">
            <Card className="bg-gradient-to-br from-blue-50 to-white border-blue-200 shadow-xl overflow-hidden relative">
              <CardContent className="p-12 text-center">
                <Building2 className="w-12 h-12 text-blue-500 mx-auto mb-6" />
                <h2 className="text-3xl md:text-4xl font-bold mb-4 text-gray-900">{t('ensurance.ctaHeadline')}</h2>
                <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
                  {t('ensurance.ctaDescription')}
                </p>
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                  <Button
                    size="lg"
                    className="bg-blue-500 hover:bg-blue-600 text-white px-8 py-6 text-lg rounded-lg"
                    onClick={() => window.location.href = 'mailto:joe@boundstate.ai?subject=Ensurance%20Demo%20Request'}
                  >
                    <FileText className="mr-2 w-5 h-5" />
                    {t('ensurance.requestDemo')}
                  </Button>
                  <Button
                    variant="outline"
                    size="lg"
                    className="border-gray-300 text-gray-700 hover:bg-gray-50 px-8 py-6 text-lg rounded-lg"
                    onClick={() => window.location.href = 'mailto:joe@boundstate.ai?subject=Ensurance%20Inquiry'}
                  >
                    {t('ensurance.scheduleACall')}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative py-12 border-t border-gray-200 z-10 bg-gray-50">
        <div className="container mx-auto px-6">
          <div className="flex flex-col items-center gap-6">
            {/* Logo */}
            <a href="https://boundstate.ai" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
              <svg width="32" height="32" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M 25 35 L 25 75 Q 25 80 30 80 L 70 80 Q 75 80 75 75 L 75 55 L 75 50 L 70 45 L 65 40" stroke="#3b82f6" strokeWidth="4" strokeLinecap="square" fill="none"/>
                <line x1="32" y1="70" x2="68" y2="70" stroke="#3b82f6" strokeWidth="3"/>
                <line x1="38" y1="58" x2="62" y2="58" stroke="#60a5fa" strokeWidth="2" opacity="0.7"/>
              </svg>
              <span className="text-lg font-bold tracking-tight text-gray-900">boundstate.ai</span>
            </a>
            
            {/* Tagline */}
            <div className="text-center">
              <p className="text-gray-600 text-sm">
                {t('ensurance.footerTagline')}
              </p>
              <p className="text-gray-500 text-sm mt-1">
                {t('ensurance.footerSubtag')}
              </p>
            </div>

            {/* Links */}
            <div className="flex items-center gap-6 text-sm">
              <a href="mailto:joe@boundstate.ai" className="text-gray-500 hover:text-gray-900 transition-colors">
                {t('ensurance.contact')}
              </a>
              <a href="https://boundstate.ai" className="text-gray-500 hover:text-gray-900 transition-colors flex items-center gap-1">
                {t('ensurance.home')} <ExternalLink className="w-3 h-3" />
              </a>
            </div>

            {/* Copyright */}
            <div className="text-gray-400 text-xs">
              {t('ensurance.copyright')}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Ensurance;
