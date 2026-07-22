import { Placeholder } from '../components/Placeholder';

// Platzhalter-Views der noch zu portierenden Bereiche (Feature-Parität folgt
// Schritt für Schritt aus dem bisherigen Vue-Frontend).

export const TariffsView = () => (
  <Placeholder title="Tarife"
    note="Tarifperioden (Grund-/Arbeitspreis, Gültigkeit) je System – Migration folgt." />
);

export const ReportsView = () => (
  <Placeholder title="Auswertungen"
    note="Verlaufsdiagramme, PDF-/CSV-Berichte und Verbrauchsanalysen – Migration folgt." />
);

export const AuditView = () => (
  <Placeholder title="Audit-Log"
    note="Änderungsprotokoll mit Filtern, Seitenaufteilung und Rollback – Migration folgt." />
);

export const SettingsView = () => (
  <Placeholder title="Einstellungen"
    note="Darstellung, Konto, Zwei-Faktor, Netzwerk, Datenmanagement – Migration folgt." />
);
