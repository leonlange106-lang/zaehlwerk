const numberDE = new Intl.NumberFormat('de-DE', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const currencyDE = new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' });

export function fmtNumber(value: number | null | undefined): string {
  return value == null ? '–' : numberDE.format(value);
}

export function fmtValue(value: number | null | undefined, unit: string): string {
  return value == null ? '–' : `${numberDE.format(value)} ${unit}`;
}

export function fmtCost(value: number | null | undefined): string {
  return value == null ? '–' : currencyDE.format(value);
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '–';
  const d = new Date(iso);
  return isNaN(d.getTime()) ? '–' : d.toLocaleDateString('de-DE');
}

export function fmtBytes(n: number): string {
  if (!n) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.min(units.length - 1, Math.floor(Math.log(n) / Math.log(1024)));
  return `${(n / Math.pow(1024, i)).toFixed(i ? 1 : 0)} ${units[i]}`;
}
