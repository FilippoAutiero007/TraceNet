import React from 'react';
import { Mail, Github, Instagram, Network } from 'lucide-react';
import { motion } from 'framer-motion';

export const Footer: React.FC = () => {
  const socialLinks = [
    {
      name: 'Email',
      icon: <Mail size={28} />,
      href: 'https://mail.google.com/mail/?view=cm&fs=1&to=filippoautiero07@gmail.com',
      color: 'group-hover:text-red-500',
      borderColor: 'group-hover:border-red-500/30',
      label: 'Invia una email a Filippo'
    },
    {
      name: 'GitHub',
      icon: <Github size={28} />,
      href: 'https://github.com/FilippoAutiero007',
      color: 'group-hover:text-[#181717]',
      borderColor: 'group-hover:border-[#181717]/30',
      label: 'Profilo GitHub di Filippo'
    },
    {
      name: 'Instagram',
      icon: <Instagram size={28} />,
      href: 'https://www.instagram.com/filippo_autiero_/',
      color: 'group-hover:text-[#E4405F]',
      borderColor: 'group-hover:border-[#E4405F]/30',
      label: 'Profilo Instagram di Filippo'
    }
  ];

  return (
    <footer id="contact" className="bg-slate-950 border-t border-slate-800 py-20">
      <div className="max-w-6xl mx-auto px-6">
        <div className="flex flex-col items-center justify-center gap-12">
          {/* NetTrace Brand */}
          <div className="flex items-center gap-3 mb-4">
            <Network className="w-10 h-10 text-cyan-400" />
            <span className="text-3xl font-bold text-white">NetTrace</span>
          </div>

          <h2 className="text-4xl font-bold text-white tracking-tight">Contatti</h2>

          <div className="flex items-center justify-center gap-10 md:gap-16">
            {socialLinks.map((link) => (
              <motion.a
                key={link.name}
                href={link.href}
                target="_blank"
                rel="noopener noreferrer"
                className="flex flex-col items-center gap-4 group"
                aria-label={link.label}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                transition={{ type: "spring", stiffness: 400, damping: 17 }}
              >
                <div className={`w-16 h-16 bg-slate-900 rounded-3xl shadow-sm flex items-center justify-center border border-slate-700 ${link.borderColor} group-hover:shadow-lg group-hover:shadow-cyan-500/20 transition-all duration-300`}>
                  <div className={`text-slate-400 ${link.color} transition-colors`}>
                    {link.icon}
                  </div>
                </div>
                <span className="text-sm font-semibold text-slate-400 group-hover:text-white transition-colors">
                  {link.name}
                </span>
              </motion.a>
            ))}
          </div>

          <div className="mt-8 text-center">
            <p className="text-xs text-slate-500">
              © {new Date().getFullYear()} Filippo Autiero. All rights reserved.
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
};
