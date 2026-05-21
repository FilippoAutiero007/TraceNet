import { useEffect, useRef } from 'react';

class Particle {
  x!: number;
  y!: number;
  ox!: number;
  oy!: number;
  vx!: number;
  vy!: number;
  r!: number;
  hue!: number;
  alpha!: number;
  width!: () => number;
  height!: () => number;

  constructor(width: () => number, height: () => number) {
    this.width = width;
    this.height = height;
    this.reset();
  }

  reset() {
    this.x = Math.random() * this.width();
    this.y = Math.random() * this.height();
    this.ox = this.x;
    this.oy = this.y;
    this.vx = 0;
    this.vy = 0;
    this.r = Math.random() * 2.5 + 1;
    this.hue = Math.random() * 60 + 200;
    this.alpha = Math.random() * 0.5 + 0.4;
  }

  update(mouse: { x: number; y: number }, repel: number, force: number) {
    const dx = this.x - mouse.x;
    const dy = this.y - mouse.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < repel && dist > 0) {
      const angle = Math.atan2(dy, dx);
      const push = ((repel - dist) / repel) * force;
      this.vx += Math.cos(angle) * push;
      this.vy += Math.sin(angle) * push;
    }
    const homeX = (this.x - this.ox) * 0.05;
    const homeY = (this.y - this.oy) * 0.05;
    this.vx = (this.vx - homeX) * 0.88;
    this.vy = (this.vy - homeY) * 0.88;
    this.x += this.vx;
    this.y += this.vy;
  }
}

export function ParticleEffect() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let W = 0;
    let H = 0;
    let particles: Particle[] = [];
    let animationFrameId = 0;
    const mouse = { x: -999, y: -999 };
    const N = 120, REPEL = 120, FORCE = 6;

    function resize() {
      const r = canvas!.getBoundingClientRect();
      W = canvas!.width = r.width;
      H = canvas!.height = 500;
    }

    function hsl(h: number, s: number, l: number) {
      return `hsl(${h},${s}%,${l}%)`;
    }

    function initParticles() {
      particles = [];
      for (let i = 0; i < N; i++) {
        particles.push(new Particle(() => W, () => H));
      }
    }

    function drawConnections() {
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const d = Math.sqrt(dx * dx + dy * dy);
          if (d < 90) {
            ctx!.beginPath();
            ctx!.moveTo(particles[i].x, particles[i].y);
            ctx!.lineTo(particles[j].x, particles[j].y);
            ctx!.strokeStyle = hsl(220, 70, 70);
            ctx!.globalAlpha = (1 - d / 90) * 0.18;
            ctx!.lineWidth = 0.6;
            ctx!.stroke();
            ctx!.globalAlpha = 1;
          }
        }
      }
    }

    function drawCursor() {
      if (mouse.x < 0) return;
      ctx!.beginPath();
      ctx!.arc(mouse.x, mouse.y, 6, 0, Math.PI * 2);
      ctx!.strokeStyle = 'rgba(180,200,255,0.7)';
      ctx!.lineWidth = 1.5;
      ctx!.stroke();
      ctx!.beginPath();
      ctx!.arc(mouse.x, mouse.y, REPEL, 0, Math.PI * 2);
      ctx!.strokeStyle = 'rgba(150,170,255,0.1)';
      ctx!.lineWidth = 1;
      ctx!.stroke();
    }

    function loop() {
      ctx!.clearRect(0, 0, W, H);
      drawConnections();
      for (const p of particles) {
        p.update(mouse, REPEL, FORCE);
        ctx!.beginPath();
        ctx!.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx!.fillStyle = hsl(p.hue, 80, 70);
        ctx!.globalAlpha = p.alpha;
        ctx!.fill();
        ctx!.globalAlpha = 1;
      }
      drawCursor();
      animationFrameId = requestAnimationFrame(loop);
    }

    const handleMouseMove = (e: MouseEvent) => {
      const r = canvas!.getBoundingClientRect();
      mouse.x = e.clientX - r.left;
      mouse.y = e.clientY - r.top;
    };

    const handleMouseLeave = () => {
      mouse.x = -999;
      mouse.y = -999;
    };

    const handleTouchMove = (e: TouchEvent) => {
      e.preventDefault();
      const r = canvas!.getBoundingClientRect();
      mouse.x = e.touches[0].clientX - r.left;
      mouse.y = e.touches[0].clientY - r.top;
    };

    const handleTouchEnd = () => {
      mouse.x = -999;
      mouse.y = -999;
    };

    const handleWindowResize = () => {
      resize();
      initParticles();
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseleave', handleMouseLeave);
    window.addEventListener('touchmove', handleTouchMove, { passive: false });
    window.addEventListener('touchend', handleTouchEnd);
    window.addEventListener('resize', handleWindowResize);

    resize();
    initParticles();
    loop();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
      window.removeEventListener('touchmove', handleTouchMove);
      window.removeEventListener('touchend', handleTouchEnd);
      window.removeEventListener('resize', handleWindowResize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ height: '500px' }}
    />
  );
}
