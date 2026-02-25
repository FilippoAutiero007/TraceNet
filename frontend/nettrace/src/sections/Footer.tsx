import { Mail, Github, Instagram, Globe } from 'lucide-react';
import { motion } from 'framer-motion';
import { Network } from 'lucide-react';

const socialLinks = [
  {
    name: 'Website',
    icon: <Globe size={26} />,
    href: 'https://autiero-filippo.vercel.app/',
    color: 'group-hover:text-cyan-400',
    borderColor: 'group-hover:border-cyan-400/40',
    shadow: 'group-hover:shadow-cyan-500/10',
  },
  {
    name: 'Email',
    icon: <Mail size={26} />,
    href: 'https://mail.google.com/mail/?view=cm&fs=1&to=filippoautiero07@gmail.com',
    color: 'group-hover:text-red-400',
    borderColor: 'group-hover:border-red-400/40',
    shadow: 'group-hover:shadow-red-500/10',
  },
  {
    name: 'GitHub',
    icon: <Github size={26} />,
    href: 'https://github.com/FilippoAutiero007',
    color: 'group-hover:text-white',
    borderColor: 'group-hover:border-slate-400/40',
    shadow: 'group-hover:shadow-slate-400/10',
  },
  {
    name: 'Instagram',
    icon: <Instagram size={26} />,
    href: 'https://www.instagram.com/filippo_autiero_/',
    color: 'group-hover:text-pink-400',
    borderColor: 'group-hover:border-pink-400/40',
    shadow: 'group-hover:shadow-pink-500/10',
  },
];

export function Footer() {
  return (
    <footer id="contact" className="bg-slate-950 border-t border-slate-800 py-20">
      <div className="max-w-6xl mx-auto px-6">
        <div className="flex flex-col items-center justify-center gap-12">
          {/* Brand */}
          <div className="flex items-center gap-2">
            <Network className="w-5 h-5 text-cyan-400" aria-hidden="true" />
            <span className="text-base font-bold text-white tracking-tight">Net<span className="text-cyan-400">Trace</span></span>
          </div>

          <h2 className="text-3xl font-bold text-white tracking-tight -mt-6">Contact</h2>

          {/* Social buttons */}
          <div className="flex items-center justify-center gap-8 md:gap-14">
            {socialLinks.map((link) => (
              <motion.a
                key={link.name}
                href={link.href}
                target="_blank"
                rel="noopener noreferrer"
                className="flex flex-col items-center gap-3 group"
                aria-label={link.name}
                whileHover={{ scale: 1.08 }}
                whileTap={{ scale: 0.95 }}
                transition={{ type: 'spring', stiffness: 400, damping: 17 }}
              >
                <div
                  className={`w-16 h-16 bg-slate-900 rounded-3xl flex items-center justify-center border border-slate-700 ${link.borderColor} shadow-md ${link.shadow} group-hover:shadow-lg transition-all duration-300`}
                >
                  <span className={`text-slate-400 ${link.color} transition-colors duration-300`}>
                    {link.icon}
                  </span>
                </div>
                <span className="text-xs font-semibold text-slate-500 group-hover:text-slate-200 transition-colors duration-300">
                  {link.name}
                </span>
              </motion.a>
            ))}
          </div>

          <p className="text-xs text-slate-600">
            © {new Date().getFullYear()} Filippo Autiero. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
