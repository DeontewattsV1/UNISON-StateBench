import { Info, LoaderCircle } from 'lucide-react';

export function Button({ children, icon: Icon, variant = 'secondary', loading = false, className = '', ...props }) {
  return <button className={`button button--${variant} ${className}`} aria-busy={loading || undefined} {...props}>
    {loading ? <LoaderCircle size={17} className="spin" aria-hidden="true" /> : Icon && <Icon size={17} aria-hidden="true" />}
    {children}
  </button>;
}

export function Status({ value }) {
  const label = value === 'PASS' ? 'Pass' : value === 'FAIL' ? 'Fail' : value === 'UNKNOWN' ? 'Unknown' : value;
  return <span className={`status status--${String(value || '').toLowerCase()}`}>{label}</span>;
}

export function SafetyNote() {
  return <div className="safety-note"><Info size={19} strokeWidth={1.7} aria-hidden="true" /><span>A model proposal is never an authorization.</span></div>;
}
