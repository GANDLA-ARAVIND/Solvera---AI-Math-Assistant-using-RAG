import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Calculator, Brain, Zap, BookOpen, ArrowRight, Star } from 'lucide-react';
import useAuthStore from '../store/authStore';

const HomePage = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  const features = [
    {
      icon: Brain,
      title: 'AI-Powered Solutions',
      description: 'Get instant step-by-step solutions to complex math problems using advanced AI'
    },
    {
      icon: Zap,
      title: 'Lightning Fast',
      description: 'Get answers in seconds with our optimized processing engine'
    },
    {
      icon: BookOpen,
      title: 'Learn & Master',
      description: 'Understand concepts deeply with detailed explanations and visual plots'
    },
    {
      icon: Calculator,
      title: 'All Topics Covered',
      description: 'From algebra to calculus, trigonometry to statistics - we handle it all'
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-900/10 to-slate-950">
      {/* Navigation Bar */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-slate-950/80 backdrop-blur-md border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-blue-600/20 rounded-xl flex items-center justify-center">
              <Calculator size={24} className="text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">
                <span className="text-blue-400">Solv</span>era
              </h1>
              <p className="text-xs text-slate-500 mt-0.5">AI Math Assistant</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/login')}
              className="px-6 py-2.5 text-sm font-medium text-slate-300 hover:text-white transition-colors"
            >
              Login
            </button>
            <button
              onClick={() => navigate('/signup')}
              className="px-6 py-2.5 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Sign Up
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="mb-6 inline-block">
            <div className="flex items-center gap-2 bg-blue-600/10 border border-blue-500/30 rounded-full px-4 py-2 text-sm text-blue-300">
              <Star size={16} />
              Your Personal Math Tutor
            </div>
          </div>
          
          <h2 className="text-5xl md:text-6xl font-bold text-white mb-6 leading-tight">
            Master Mathematics with<br />
            <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
              AI-Powered Solutions
            </span>
          </h2>
          
          <p className="text-xl text-slate-400 mb-10 max-w-2xl mx-auto">
            Solve any math problem instantly, understand concepts deeply, and master mathematics with our intelligent math assistant powered by advanced artificial intelligence.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button
              onClick={() => navigate('/signup')}
              className="px-8 py-3.5 text-base font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
            >
              Get Started Free <ArrowRight size={18} />
            </button>
            <button
              onClick={() => navigate('/login')}
              className="px-8 py-3.5 text-base font-medium bg-slate-800 text-white rounded-lg border border-slate-700 hover:bg-slate-700 transition-colors"
            >
              I Already Have an Account
            </button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-6 bg-slate-900/40">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h3 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Why Choose Solvera?
            </h3>
            <p className="text-lg text-slate-400">
              Everything you need to excel in mathematics
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <div
                  key={index}
                  className="p-6 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-blue-500/50 transition-all hover:shadow-lg hover:shadow-blue-500/10"
                >
                  <div className="w-12 h-12 bg-blue-600/20 rounded-lg flex items-center justify-center mb-4">
                    <Icon size={24} className="text-blue-400" />
                  </div>
                  <h4 className="text-lg font-semibold text-white mb-2">
                    {feature.title}
                  </h4>
                  <p className="text-slate-400 text-sm leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <h3 className="text-3xl md:text-4xl font-bold text-white mb-6">
            Ready to Solve Math Problems?
          </h3>
          <p className="text-lg text-slate-400 mb-10">
            Join thousands of students who've already transformed their math skills
          </p>
          <button
            onClick={() => navigate('/signup')}
            className="px-8 py-4 text-lg font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors inline-flex items-center gap-2"
          >
            Start Your Free Trial <ArrowRight size={20} />
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-8 px-6">
        <div className="max-w-6xl mx-auto text-center text-slate-500 text-sm">
          <p>&copy; 2024 Solvera. All rights reserved. AI-Powered Math Solutions.</p>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;
