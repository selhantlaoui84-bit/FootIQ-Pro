import { useEffect, useState } from 'react';
import { completeOnboarding } from '~/lib/api';
import { useAuth } from '~/lib/auth';

const steps = [
  'Bienvenue sur FootIQ Pro',
  'Comprendre une prédiction',
  'Lire les cotes réelles',
  'Interpréter EV et value bet',
  'Suivre ses paris dans le portefeuille',
  'Lire ses performances',
  'Utiliser l’assistant avec prudence',
  "Rappel responsable : aucun résultat n'est assuré",
];

export function OnboardingModal() {
  const { user, session, platformUser } = useAuth();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (!user) return;
    const localKey = `footiq_onboarding_done_${user.email ?? user.id}`;
    const serverDone = Boolean(platformUser?.metadata?.onboarding_completed);
    const localDone = typeof window !== 'undefined' && window.localStorage.getItem(localKey) === '1';
    setOpen(!serverDone && !localDone);
  }, [platformUser?.metadata?.onboarding_completed, user]);

  async function finish() {
    if (user?.email && typeof window !== 'undefined') {
      window.localStorage.setItem(`footiq_onboarding_done_${user.email}`, '1');
    }
    setOpen(false);
    if (session?.access_token) {
      await completeOnboarding(session.access_token).catch(() => undefined);
    }
  }

  if (!open) return null;

  return (
    <div className="onboardingBackdrop" role="dialog" aria-modal="true" aria-labelledby="onboarding-title">
      <section className="onboardingModal">
        <p className="eyebrow">Onboarding FootIQ Pro</p>
        <h2 id="onboarding-title">{steps[step]}</h2>
        <p>
          FootIQ Pro vous aide à lire les probabilités, les cotes réelles, le risque et votre discipline de pari.
          Les analyses restent statistiques et n'assurent jamais un résultat.
        </p>
        <div className="onboardingSteps">
          {steps.map((item, index) => (
            <span className={index <= step ? 'active' : undefined} key={item} />
          ))}
        </div>
        <div className="inlineActions">
          <button className="button secondary" type="button" onClick={finish}>
            Passer
          </button>
          {step < steps.length - 1 ? (
            <button className="button primary" type="button" onClick={() => setStep((value) => value + 1)}>
              Continuer
            </button>
          ) : (
            <button className="button primary" type="button" onClick={finish}>
              Terminer
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
