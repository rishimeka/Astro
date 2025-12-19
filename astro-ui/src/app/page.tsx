"use client"

import AppHeader from "./components/AppHeader";
import Hero from "./components/Hero";
import FailureScenario from "./components/FailureScenario";
import ProblemSection from "./components/ProblemSection";
import SolutionSection from "./components/SolutionSection";
import WhoThisIsFor from "./components/WhoThisIsFor";
import WhatItEnablesSection from "./components/WhatItEnablesSection";
import WhyItMatters from "./components/WhyItMatters";
import CTA from "./components/CTA";
import Footer from "./components/Footer";

export default function Home() {

  return (
    <div>
      <AppHeader />
      <Hero />
      <ProblemSection />
      <SolutionSection />
      <WhoThisIsFor />
      <WhatItEnablesSection />
      <WhyItMatters />
      <CTA />
      <Footer />
    </div>
  );
}