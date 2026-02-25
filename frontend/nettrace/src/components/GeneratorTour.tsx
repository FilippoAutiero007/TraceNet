import { useState, useEffect } from 'react';
import Joyride, { type CallBackProps, STATUS } from 'react-joyride';
import { Button } from '@/components/ui/button';
import { HelpCircle } from 'lucide-react';
import { useLanguage } from '@/context/LanguageContext';

const TOUR_STORAGE_KEY = 'nettrace_tour_done';

const joyrideStyles = {
  options: {
    primaryColor: '#06b6d4',
    backgroundColor: '#0f172a',
    arrowColor: '#0f172a',
    textColor: '#cbd5e1',
    overlayColor: 'rgba(0,0,0,0.6)',
  },
};

export function GeneratorTour() {
  const [run, setRun] = useState(false);
  const { t } = useLanguage();

  const steps = [
    { target: '#generator-templates', title: t('tour.step1.title'), content: t('tour.step1.content'), disableBeacon: true, placement: 'bottom' as const },
    { target: '#generator-textarea',  title: t('tour.step2.title'), content: t('tour.step2.content'), placement: 'bottom' as const },
    { target: '#generator-submit',    title: t('tour.step3.title'), content: t('tour.step3.content'), placement: 'top' as const },
    { target: '#generator-result',    title: t('tour.step4.title'), content: t('tour.step4.content'), placement: 'left' as const },
  ];

  useEffect(() => {
    const done = localStorage.getItem(TOUR_STORAGE_KEY);
    if (!done) {
      const timer = setTimeout(() => setRun(true), 600);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleCallback = (data: CallBackProps) => {
    if (data.status === STATUS.FINISHED || data.status === STATUS.SKIPPED) {
      setRun(false);
      localStorage.setItem(TOUR_STORAGE_KEY, '1');
    }
  };

  return (
    <>
      <Joyride
        steps={steps}
        run={run}
        continuous
        showProgress
        showSkipButton
        callback={handleCallback}
        styles={joyrideStyles}
        locale={{
          back: t('tour.back'),
          close: t('tour.close'),
          last: t('tour.last'),
          next: t('tour.next'),
          skip: t('tour.skip'),
        }}
      />
      <Button
        variant="ghost"
        size="sm"
        className="text-slate-400 hover:text-cyan-400 gap-1.5"
        onClick={() => setRun(true)}
        aria-label={t('tour.btn')}
      >
        <HelpCircle className="w-4 h-4" />
        <span className="hidden sm:inline text-xs">{t('tour.btn')}</span>
      </Button>
    </>
  );
}
