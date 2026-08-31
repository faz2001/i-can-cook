import {
  ArrowLeft, ArrowRight, CheckCircle2, Circle, Pause, Play, RotateCcw, Timer, X,
} from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { LivingBackground } from '../components/LivingBackground';
import { ErrorBlock, LoadingBlock } from '../components/StatusBlocks';
import { ApiError, recipesApi } from '../lib/api';
import type { CookSessionOut } from '../lib/types';

function formatQty(q: number): string {
  return Number.isInteger(q) ? String(q) : q.toFixed(2).replace(/0+$/, '').replace(/\.$/, '');
}

function formatClock(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

/** A single timer slot for the whole Kitchen Mode session. Only one timer
 * can run at a time; it's identified by which step it belongs to so it can
 * keep counting down in the background while the user looks at other steps. */
type TimerState = {
  stepNumber: number;
  remaining: number;
  running: boolean;
};

/** Presentational per-step countdown. It no longer owns any ticking state --
 * that lives at the page level so it survives step navigation. This
 * component just reflects whatever remaining/running values it's given and
 * reports taps back up. Cooking is self-paced; the timer informs, it
 * doesn't gate the Next button. */
function StepTimer({
  remaining,
  running,
  onToggle,
  onReset,
}: {
  remaining: number;
  running: boolean;
  onToggle: () => void;
  onReset: () => void;
}) {
  const done = remaining === 0;

  return (
    <div className={`flex items-center gap-4 rounded-3xl px-6 py-4 ${done ? 'bg-tertiary-container/40' : 'bg-surface-container'}`}>
      <span className={`font-display text-4xl tabular-nums ${done ? 'text-tertiary' : 'text-on-surface'}`}>
        {formatClock(remaining)}
      </span>
      <div className="flex items-center gap-2">
        <button
          onClick={onToggle}
          disabled={done}
          aria-label={running ? 'Pause timer' : 'Start timer'}
          className="w-11 h-11 rounded-full bg-primary text-on-primary flex items-center justify-center disabled:opacity-40"
        >
          {running ? <Pause size={18} /> : <Play size={18} />}
        </button>
        <button
          onClick={onReset}
          aria-label="Reset timer"
          className="w-11 h-11 rounded-full bg-surface-container-high text-on-surface-variant flex items-center justify-center"
        >
          <RotateCcw size={16} />
        </button>
      </div>
      {done && <span className="font-ui text-sm font-semibold text-tertiary">Time's up</span>}
    </div>
  );
}

export default function KitchenModePage() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [session, setSession] = useState<CookSessionOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [phase, setPhase] = useState<'prep' | 'cooking' | 'done'>('prep');
  const [checked, setChecked] = useState<Record<number, boolean>>({});
  const [stepIndex, setStepIndex] = useState(0);

  // Single page-level timer slot, independent of which step is on screen.
  const [timer, setTimer] = useState<TimerState | null>(null);
  // When a running timer belongs to a different step than the one the user
  // is trying to start, we ask before silently overwriting it.
  const [pendingTimerStart, setPendingTimerStart] = useState<{ stepNumber: number; seconds: number } | null>(null);

  useEffect(() => {
  if (!id) return;
  const servingsParam = searchParams.get('servings');
  const servings = servingsParam ? Number(servingsParam) : undefined;
  setLoading(true);
  setError(null);
  setPhase('prep');            // add
  setChecked({});              // add
  setStepIndex(0);             // add
  setTimer(null);              // add
  setPendingTimerStart(null);  // add
  recipesApi
    .cookSession(id, servings)
      .then((data) => {
        setSession(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : 'Could not start Kitchen Mode.');
        setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const currentStep = useMemo(() => session?.steps[stepIndex] ?? null, [session, stepIndex]);
  const isLastStep = session ? stepIndex === session.steps.length - 1 : false;

  // Ticks the active timer down once a second, no matter which step is
  // currently displayed -- this is what lets it keep running in the
  // background when the user navigates away from the step it belongs to.
  useEffect(() => {
    if (!timer || !timer.running || timer.remaining <= 0) return;
    const id = setInterval(() => {
      setTimer((t) => (t ? { ...t, remaining: Math.max(0, t.remaining - 1) } : t));
    }, 1000);
    return () => clearInterval(id);
  }, [timer]);

  function startOrToggleTimer(stepNumber: number, seconds: number) {
    setTimer((t) => {
      if (t && t.stepNumber === stepNumber) {
        // Same step: plain pause/resume.
        return { ...t, running: !t.running };
      }
      if (t && t.running) {
        // A different step's timer is actively running -- don't clobber it
        // silently, ask first.
        setPendingTimerStart({ stepNumber, seconds });
        return t;
      }
      // No active timer, or a different step's timer that's already
      // paused -- safe to just take over the slot.
      return { stepNumber, remaining: seconds, running: true };
    });
  }

  function resetTimer(stepNumber: number, seconds: number) {
    setTimer((t) => (t && t.stepNumber === stepNumber ? { stepNumber, remaining: seconds, running: false } : t));
  }

  function confirmTimerSwitch() {
    if (!pendingTimerStart) return;
    setTimer({ stepNumber: pendingTimerStart.stepNumber, remaining: pendingTimerStart.seconds, running: true });
    setPendingTimerStart(null);
  }

  function jumpToTimerStep() {
    if (!timer || !session) return;
    const idx = session.steps.findIndex((s) => s.step_number === timer.stepNumber);
    if (idx >= 0) setStepIndex(idx);
  }

  function exit() {
  navigate(-1);   // was: navigate(`/recipe/${id}`)
}

  if (loading) {
    return (
      <div className="relative min-h-screen">
        <LivingBackground />
        <div className="relative z-10"><LoadingBlock label="Getting the kitchen ready…" /></div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="relative min-h-screen flex items-center justify-center">
        <LivingBackground />
        <div className="relative z-10 max-w-md w-full">
          <ErrorBlock message={error || 'Recipe not found.'} onRetry={exit} />
        </div>
      </div>
    );
  }

  // Is there a running timer parked on a step other than the one we're
  // looking at? If so, surface a small persistent indicator in the header.
  const backgroundTimerActive =
    phase === 'cooking' && !!timer && timer.running && timer.stepNumber !== currentStep?.step_number;

  return (
    <div className="min-h-screen bg-surface flex flex-col">
      {/* Top bar -- always visible so exiting Kitchen Mode is never more than one tap away */}
      <div className="sticky top-0 z-10 bg-surface/95 backdrop-blur-md border-b border-outline-variant/20 px-5 py-4 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="font-heading text-lg text-on-surface leading-tight truncate">{session.name_en}</h1>
          <p className="font-ui text-xs text-on-surface-variant">{session.requested_servings} servings</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {backgroundTimerActive && timer && (
            <button
              onClick={jumpToTimerStep}
              className="flex items-center gap-2 rounded-full bg-tertiary-container/40 px-4 py-2 font-ui text-xs font-semibold text-tertiary"
              aria-label={`Jump to step ${timer.stepNumber}, timer running`}
            >
              <Timer size={14} />
              {formatClock(timer.remaining)} (Step {timer.stepNumber})
            </button>
          )}
          <button
            onClick={exit}
            aria-label="Exit Kitchen Mode"
            className="w-11 h-11 rounded-full bg-surface-container flex items-center justify-center text-on-surface-variant"
          >
            <X size={20} />
          </button>
        </div>
      </div>

      {phase === 'prep' && (
        <div className="flex-1 px-5 py-8 max-w-xl mx-auto w-full">
          <h2 className="font-display text-3xl text-on-surface mb-2">Get everything ready</h2>
          <p className="font-body-md text-on-surface-variant mb-8">
            Check off each item as you set it out — {session.total_active_time_min} active minutes once you start.
          </p>
          <ul className="space-y-2 mb-10">
            {session.prep_checklist.map((item, idx) => {
              const isChecked = !!checked[idx];
              return (
                <li key={idx}>
                  <button
                    onClick={() => setChecked((c) => ({ ...c, [idx]: !c[idx] }))}
                    className={`w-full flex items-center gap-3 rounded-2xl px-4 py-3.5 text-left transition-colors ${
                      isChecked ? 'bg-tertiary-container/30' : 'bg-surface-container'
                    }`}
                  >
                    {isChecked ? (
                      <CheckCircle2 size={20} className="text-tertiary shrink-0" />
                    ) : (
                      <Circle size={20} className="text-on-surface-variant shrink-0" />
                    )}
                    <span className={`font-body-md text-sm ${isChecked ? 'text-on-surface-variant line-through' : 'text-on-surface'}`}>
                      {item.quantity !== null ? `${formatQty(item.quantity)} ${item.unit || ''} ` : ''}
                      {item.name}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
          <button
            onClick={() => setPhase('cooking')}
            className="w-full h-16 rounded-full bg-primary text-on-primary font-ui text-base font-semibold shadow-lg flex items-center justify-center gap-2"
          >
            Start Cooking <ArrowRight size={20} />
          </button>
        </div>
      )}

      {phase === 'cooking' && currentStep && (
        <div className="flex-1 flex flex-col px-5 py-8 max-w-xl mx-auto w-full">
          {/* Progress */}
          <div className="mb-8">
            <div className="flex justify-between font-ui text-xs text-on-surface-variant mb-2">
              <span>Step {currentStep.step_number} of {session.steps.length}</span>
              {currentStep.duration_min !== null && (
                <span className="flex items-center gap-1"><Timer size={12} /> {currentStep.duration_min} min</span>
              )}
            </div>
            <div className="h-2 rounded-full bg-surface-container overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-300"
                style={{ width: `${((stepIndex + 1) / session.steps.length) * 100}%` }}
              />
            </div>
          </div>

          {/* Large step text -- the core hands-free/distance-legible requirement */}
          <div className="flex-1 flex items-center">
            <p className="font-heading text-[28px] md:text-[34px] leading-snug text-on-surface">
              {currentStep.instruction}
            </p>
          </div>

          {currentStep.timer_seconds !== null && (
            <div className="mb-8">
              <StepTimer
                remaining={
                  timer && timer.stepNumber === currentStep.step_number
                    ? timer.remaining
                    : currentStep.timer_seconds
                }
                running={!!timer && timer.stepNumber === currentStep.step_number && timer.running}
                onToggle={() => startOrToggleTimer(currentStep.step_number, currentStep.timer_seconds!)}
                onReset={() => resetTimer(currentStep.step_number, currentStep.timer_seconds!)}
              />
            </div>
          )}

          {/* Navigation */}
          <div className="flex gap-3">
            <button
              onClick={() => setStepIndex((i) => Math.max(0, i - 1))}
              disabled={stepIndex === 0}
              className="w-16 h-16 rounded-full bg-surface-container text-on-surface-variant flex items-center justify-center disabled:opacity-30"
              aria-label="Previous step"
            >
              <ArrowLeft size={22} />
            </button>
            <button
              onClick={() => (isLastStep ? setPhase('done') : setStepIndex((i) => i + 1))}
              className="flex-1 h-16 rounded-full bg-primary text-on-primary font-ui text-base font-semibold shadow-lg flex items-center justify-center gap-2"
            >
              {isLastStep ? 'Finish' : 'Next step'} <ArrowRight size={20} />
            </button>
          </div>
        </div>
      )}

      {phase === 'done' && (
        <div className="flex-1 flex flex-col items-center justify-center px-5 py-8 text-center">
          <div className="w-20 h-20 rounded-full bg-tertiary-container/40 flex items-center justify-center mb-6">
            <CheckCircle2 size={40} className="text-tertiary" />
          </div>
          <h2 className="font-display text-3xl text-on-surface mb-2">Nice work!</h2>
          <p className="font-body-md text-on-surface-variant mb-10 max-w-sm">
            You've stepped through every instruction for {session.name_en}. Enjoy the meal.
          </p>
          <button
            onClick={exit}
            className="h-14 px-10 rounded-full bg-primary text-on-primary font-ui text-sm font-semibold shadow-lg"
          >
            Back to recipe
          </button>
        </div>
      )}

      {/* Confirmation before overwriting a different step's still-running timer */}
      {pendingTimerStart && (
        <div className="fixed inset-0 z-20 flex items-center justify-center bg-black/40 px-5">
          <div className="w-full max-w-sm rounded-3xl bg-surface-container-high p-6 shadow-xl">
            <p className="font-body-md text-on-surface mb-6">
              Stop the Step {timer?.stepNumber} timer and start this one?
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setPendingTimerStart(null)}
                className="flex-1 h-12 rounded-full bg-surface-container text-on-surface-variant font-ui text-sm font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={confirmTimerSwitch}
                className="flex-1 h-12 rounded-full bg-primary text-on-primary font-ui text-sm font-semibold"
              >
                Switch timer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
