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
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        duration: 0.6,
        staggerChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { y: 30, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: { duration: 0.5, ease: "easeOut" as Easing },
    },
  };

  return (
    <footer id="contact" className="bg-gradient-to-b from-slate-950 to-slate-900 border-t border-slate-800 py-16 sm:py-20">
      <div className="max-w-6xl mx-auto px-6">
        <motion.div 
          className="flex flex-col items-center justify-center gap-8 sm:gap-12"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.1 }}
          variants={containerVariants}
        >
          {/* Brand */}
          <motion.div variants={itemVariants} className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-gradient-to-br from-cyan-500/10 to-blue-500/10">
              <Network className="w-5 h-5 text-cyan-400" aria-hidden="true" />
            </div>
            <span className="text-base font-bold text-white tracking-tight">Net<span className="text-cyan-400">Trace</span></span>
          </motion.div>

          <motion.div variants={itemVariants} className="text-center">
            <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight mb-2">Contact</h2>
            <p className="text-slate-400 text-sm sm:text-base">Let's connect and build something amazing together</p>
          </motion.div>

          {/* Social buttons */}
          <motion.div 
            variants={itemVariants}
            className="flex items-center justify-center gap-6 sm:gap-8 md:gap-14"
          >
            {socialLinks.map((link, index) => (
              <motion.a
                key={link.name}
                href={link.href}
                target="_blank"
                rel="noopener noreferrer"
                className="flex flex-col items-center gap-3 group"
                aria-label={link.name}
                whileHover={{ scale: 1.08 }}
                whileTap={{ scale: 0.95 }}
                transition={{ type: "spring", stiffness: 400, damping: 17 }}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
              >
                <div
                  className={`w-14 h-14 sm:w-16 sm:h-16 bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl sm:rounded-3xl flex items-center justify-center border border-slate-700 ${link.borderColor} shadow-md group-hover:shadow-lg transition-all duration-300 backdrop-blur-sm`}
                >
                  <span className={`text-slate-400 ${link.color} transition-colors duration-300`}>
                    {link.icon}
                  </span>
                </div>
                <span className="text-xs sm:text-sm font-semibold text-slate-500 group-hover:text-slate-200 transition-colors duration-300">
                  {link.name}
                </span>
              </motion.a>
            ))}
          </motion.div>

          <motion.div 
            variants={itemVariants}
            className="flex flex-col items-center gap-2 text-center"
          >
            <p className="text-xs text-slate-600">
              © {new Date().getFullYear()} Filippo Autiero. All rights reserved.
            </p>
          </motion.div>
        </motion.div>
      </div>
    </footer>
  );
}
