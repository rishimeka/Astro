'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, ArrowRight, Check } from 'lucide-react';
import { useDirectiveMutations } from '@/hooks/useDirectives';
import { Spinner } from '@/components/Loading';
import Step1Identity, { Step1Data } from './Step1Identity';
import Step2Content, { Step2Data } from './Step2Content';
import Step3Variables, { Step3Data, ExtractedVariable, extractVariables } from './Step3Variables';
import styles from './DirectiveWizard.module.scss';

interface WizardState {
  step1: Step1Data;
  step2: Step2Data;
  step3: Step3Data;
}

const STEPS = [
  { number: 1, label: 'Identity' },
  { number: 2, label: 'Content' },
  { number: 3, label: 'Variables' },
];

function generateId(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    || `directive-${Date.now()}`;
}

export default function DirectiveWizard() {
  const router = useRouter();
  const { createDirective, isSubmitting } = useDirectiveMutations();

  const [currentStep, setCurrentStep] = useState(1);
  const [error, setError] = useState<string | null>(null);

  const [wizardState, setWizardState] = useState<WizardState>({
    step1: { name: '', description: '', tags: [] },
    step2: { content: '' },
    step3: { variables: [] },
  });

  const [errors, setErrors] = useState<{
    step1: Partial<Record<keyof Step1Data, string>>;
    step2: Partial<Record<keyof Step2Data, string>>;
  }>({
    step1: {},
    step2: {},
  });

  const validateStep1 = (): boolean => {
    const newErrors: Partial<Record<keyof Step1Data, string>> = {};
    if (!wizardState.step1.name.trim()) {
      newErrors.name = 'Name is required';
    }
    if (!wizardState.step1.description.trim()) {
      newErrors.description = 'Description is required';
    }
    setErrors((prev) => ({ ...prev, step1: newErrors }));
    return Object.keys(newErrors).length === 0;
  };

  const validateStep2 = (): boolean => {
    const newErrors: Partial<Record<keyof Step2Data, string>> = {};
    if (!wizardState.step2.content.trim()) {
      newErrors.content = 'Content is required';
    }
    setErrors((prev) => ({ ...prev, step2: newErrors }));
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    setError(null);
    if (currentStep === 1 && validateStep1()) {
      setCurrentStep(2);
    } else if (currentStep === 2 && validateStep2()) {
      // Sync variables from content before moving to step 3
      const extractedNames = extractVariables(wizardState.step2.content);
      const syncedVariables: ExtractedVariable[] = extractedNames.map((name) => {
        const existing = wizardState.step3.variables.find((v) => v.name === name);
        return existing || {
          name,
          description: '',
          required: true,
          default: '',
          ui_hint: 'text',
          ui_options: {},
        };
      });
      setWizardState((prev) => ({
        ...prev,
        step3: { variables: syncedVariables },
      }));
      setCurrentStep(3);
    }
  };

  const handleBack = () => {
    setError(null);
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleCreate = async () => {
    setError(null);

    try {
      const id = generateId(wizardState.step1.name);

      await createDirective({
        id,
        name: wizardState.step1.name.trim(),
        description: wizardState.step1.description.trim(),
        content: wizardState.step2.content,
        metadata: {
          tags: wizardState.step1.tags,
          template_variables: wizardState.step3.variables.map((v) => ({
            name: v.name,
            description: v.description,
            required: v.required,
            default: v.default || null,
            ui_hint: v.ui_hint,
            ui_options: v.ui_options,
          })),
        },
      });

      router.push(`/directives/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create directive');
    }
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <Step1Identity
            data={wizardState.step1}
            onChange={(data) => setWizardState((prev) => ({ ...prev, step1: data }))}
            errors={errors.step1}
          />
        );
      case 2:
        return (
          <Step2Content
            data={wizardState.step2}
            onChange={(data) => setWizardState((prev) => ({ ...prev, step2: data }))}
            errors={errors.step2}
          />
        );
      case 3:
        return (
          <Step3Variables
            content={wizardState.step2.content}
            data={wizardState.step3}
            onChange={(data) => setWizardState((prev) => ({ ...prev, step3: data }))}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className={styles.wizard}>
      {/* Progress Indicator */}
      <div className={styles.progressContainer}>
        {STEPS.map((step, index) => (
          <div key={step.number} className={styles.progressStep}>
            {index > 0 && (
              <div
                className={`${styles.stepConnector} ${
                  currentStep > step.number - 1 ? styles.completed : ''
                }`}
              />
            )}
            <div
              className={`${styles.stepCircle} ${
                currentStep === step.number ? styles.active : ''
              } ${currentStep > step.number ? styles.completed : ''}`}
            >
              {currentStep > step.number ? <Check size={16} /> : step.number}
            </div>
            <span
              className={`${styles.stepLabel} ${
                currentStep === step.number ? styles.active : ''
              } ${currentStep > step.number ? styles.completed : ''}`}
            >
              {step.label}
            </span>
          </div>
        ))}
      </div>

      {/* Error Banner */}
      {error && <div className={styles.errorBanner}>{error}</div>}

      {/* Step Content */}
      {renderStepContent()}

      {/* Actions */}
      <div className={styles.actions}>
        <div className={styles.actionsLeft}>
          {currentStep > 1 && (
            <button
              type="button"
              className="btn btn-black-and-white btn-outline"
              onClick={handleBack}
              disabled={isSubmitting}
            >
              <ArrowLeft size={16} />
              Back
            </button>
          )}
        </div>
        <div className={styles.actionsRight}>
          {currentStep < 3 ? (
            <button
              type="button"
              className="btn btn-primary btn-highlight"
              onClick={handleNext}
            >
              Next
              <ArrowRight size={16} />
            </button>
          ) : (
            <button
              type="button"
              className="btn btn-primary btn-highlight"
              onClick={handleCreate}
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <Spinner size="sm" />
                  Creating...
                </>
              ) : (
                <>
                  <Check size={16} />
                  Create Directive
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export { DirectiveWizard };
