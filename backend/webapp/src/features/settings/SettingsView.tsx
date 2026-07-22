import { useEffect, useState } from 'react';
import {
  Stack, Card, Text, Group, Switch, NumberInput, TextInput, Button, Select, Badge,
  Skeleton, Table, Divider, Alert, PasswordInput, Modal, Image, Code, ActionIcon, LoadingOverlay,
  FileInput, List,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconAlertTriangle, IconDownload, IconTrash, IconDatabase, IconWifiOff, IconUpload } from '@tabler/icons-react';
import { useApiData } from '../../api/useApi';
import { api, apiPost, apiUpload, downloadFile, ApiError, ACTIVE_DB_KEY } from '../../api/client';
import type { AppSettings, DatabaseListResponse, BackupInfo } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { fmtBytes } from '../../util/format';

function notifyError(e: unknown) {
  notifications.show({ color: 'red', message: e instanceof ApiError ? e.message : 'Fehler' });
}

export function SettingsView() {
  const { user } = useAuth();
  const settings = useApiData<AppSettings>('/api/settings');
  const [draft, setDraft] = useState<AppSettings | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => { if (settings.data) setDraft(settings.data); }, [settings.data]);

  async function save(patch: Partial<AppSettings>) {
    setSaving(true);
    try {
      const updated = await api<AppSettings>('/api/settings', { method: 'PUT', body: JSON.stringify(patch) });
      setDraft(updated);
      notifications.show({ color: 'teal', message: 'Gespeichert' });
    } catch (e) { notifyError(e); } finally { setSaving(false); }
  }

  return (
    <Stack gap="lg" pos="relative">
      <LoadingOverlay visible={saving} />

      {user && (
        <Card>
          <Text fw={600} mb="sm">Konto</Text>
          <Group gap="xl">
            <Info label="Name" value={user.display_name} />
            <Info label="Benutzername" value={user.username} />
            <Info label="Rolle" value={user.role} />
            <Info label="Zwei-Faktor" value={user.two_factor_enabled ? 'aktiv' : 'inaktiv'} />
          </Group>
        </Card>
      )}

      <DatabaseSection />
      <SecuritySection twoFactorEnabled={!!user?.two_factor_enabled} />

      {settings.loading && !draft ? <Skeleton h={200} /> : draft && (
        <>
          <Card>
            <Group gap="xs" mb="sm"><IconWifiOff size={18} /><Text fw={600}>Netzwerk &amp; Kill-Switch</Text></Group>
            <Switch
              label="Offline-Modus (Kill-Switch): blockiert alle ausgehenden Verbindungen"
              description="Der In-App-Update-Check bleibt als einzige Ausnahme erlaubt."
              checked={draft.offline_mode}
              onChange={(e) => void save({ offline_mode: e.currentTarget.checked })}
            />
            <Divider my="sm" />
            <Group align="flex-end">
              <Switch label="Benachrichtigungen (fällige Ablesungen)" checked={draft.notify_enabled}
                      onChange={(e) => void save({ notify_enabled: e.currentTarget.checked })} />
              <NumberInput label="Intervall (Stunden)" w={160} value={draft.notify_interval_hours}
                           onChange={(v) => setDraft({ ...draft, notify_interval_hours: Number(v) || 6 })}
                           onBlur={() => void save({ notify_interval_hours: draft.notify_interval_hours })} />
            </Group>
          </Card>

          <Card>
            <Text fw={600} mb="sm">Datenmanagement</Text>
            <Group align="flex-end" wrap="wrap">
              <Switch label="Automatische Sicherung" checked={draft.backup_enabled}
                      onChange={(e) => void save({ backup_enabled: e.currentTarget.checked })} />
              <TextInput label="Uhrzeit" w={110} value={draft.backup_time}
                         onChange={(e) => setDraft({ ...draft, backup_time: e.currentTarget.value })}
                         onBlur={() => void save({ backup_time: draft.backup_time })} />
              <NumberInput label="Aufbewahrung (Tage)" w={160} value={draft.backup_keep_days}
                           onChange={(v) => setDraft({ ...draft, backup_keep_days: Number(v) || 7 })}
                           onBlur={() => void save({ backup_keep_days: draft.backup_keep_days })} />
              <NumberInput label="Audit-Log (Tage)" w={150} value={draft.audit_keep_days}
                           onChange={(v) => setDraft({ ...draft, audit_keep_days: Number(v) || 365 })}
                           onBlur={() => void save({ audit_keep_days: draft.audit_keep_days })} />
              <NumberInput label="Telemetrie (Tage, 0=∞)" w={170} value={draft.telemetry_keep_days}
                           onChange={(v) => setDraft({ ...draft, telemetry_keep_days: Number(v) || 0 })}
                           onBlur={() => void save({ telemetry_keep_days: draft.telemetry_keep_days })} />
            </Group>
            <Divider my="sm" />
            <BackupList />
          </Card>

          <ExportImportSection />
        </>
      )}
    </Stack>
  );
}

// ---------------------------------------------------------------- Export/Import
function ExportImportSection() {
  const systemsList = useApiData<{ id: string; name: string }[]>('/api/systems');
  const [busy, setBusy] = useState<string | null>(null);
  const [importOpen, setImportOpen] = useState(false);

  async function dl(path: string, filename: string, key: string) {
    setBusy(key);
    try { await downloadFile(path, filename); }
    catch (e) { notifyError(e); } finally { setBusy(null); }
  }

  return (
    <Card>
      <Text fw={600} mb="sm">Export &amp; Import</Text>
      <Group wrap="wrap">
        <Button size="xs" variant="light" leftSection={<IconDownload size={16} />}
                loading={busy === 'zip'} onClick={() => void dl('/api/export.zip', 'zaehlwerk-export.zip', 'zip')}>
          Komplett (ZIP)
        </Button>
        <Button size="xs" variant="light" leftSection={<IconDownload size={16} />}
                loading={busy === 'csv'} onClick={() => void dl('/api/export/data.csv', 'zaehlwerk-ablesungen.csv', 'csv')}>
          Ablesungen (CSV)
        </Button>
        <Button size="xs" variant="light" leftSection={<IconDownload size={16} />}
                loading={busy === 'json'} onClick={() => void dl('/api/export/data.json', 'zaehlwerk-export.json', 'json')}>
          Alles (JSON)
        </Button>
        <Button size="xs" variant="subtle" color="gray"
                loading={busy === 'tpl'} onClick={() => void dl('/api/import/template', 'import-vorlage.csv', 'tpl')}>
          Import-Vorlage
        </Button>
        <Button size="xs" onClick={() => setImportOpen(true)}>CSV importieren …</Button>
      </Group>
      <ImportModal
        opened={importOpen} onClose={() => setImportOpen(false)}
        systems={systemsList.data ?? []}
      />
    </Card>
  );
}

function ImportModal({ opened, onClose, systems }: {
  opened: boolean; onClose: () => void; systems: { id: string; name: string }[];
}) {
  const [systemId, setSystemId] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ imported: number; skipped: number; errors: string[] } | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!systemId || !file) return;
    setBusy(true); setError(null); setResult(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await apiUpload<{ imported: number; skipped: number; errors: string[] }>(`/api/systems/${systemId}/import`, fd);
      setResult(res);
      notifications.show({ color: 'teal', message: `${res.imported} Ablesungen importiert` });
    } catch (e) { setError(e instanceof ApiError ? e.message : 'Import fehlgeschlagen'); } finally { setBusy(false); }
  }

  return (
    <Modal opened={opened} onClose={onClose} title="CSV importieren" centered>
      <Stack>
        {error && <Alert color="red" icon={<IconAlertTriangle size={16} />}>{error}</Alert>}
        <Select label="Zielsystem" placeholder="System wählen …" data={systems.map((s) => ({ value: s.id, label: s.name }))}
                value={systemId} onChange={setSystemId} searchable />
        <FileInput label="CSV-Datei" placeholder="Datei wählen …" accept=".csv,text/csv" value={file} onChange={setFile} leftSection={<IconUpload size={16} />} />
        <Text size="xs" c="dimmed">Spalten: datum, wert, kosten (optional), zaehlertausch (optional), notiz (optional).</Text>
        {result && (
          <Alert color={result.skipped ? 'orange' : 'teal'}>
            {result.imported} importiert, {result.skipped} übersprungen.
            {result.errors.length > 0 && <List size="xs" mt={4}>{result.errors.slice(0, 5).map((e, i) => <List.Item key={i}>{e}</List.Item>)}</List>}
          </Alert>
        )}
        <Group justify="flex-end">
          <Button loading={busy} disabled={!systemId || !file} onClick={() => void submit()}>Importieren</Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return <div><Text size="xs" c="dimmed">{label}</Text><Text size="sm" fw={500}>{value}</Text></div>;
}

// ---------------------------------------------------------------- Datenbank
function DatabaseSection() {
  const { data, reload } = useApiData<DatabaseListResponse>('/api/databases');
  const dbs = data?.databases ?? [];
  if (dbs.length < 2) return null;

  function switchTo(id: string) {
    localStorage.setItem(ACTIVE_DB_KEY, id);
    notifications.show({ color: 'teal', message: 'Datenbank gewechselt' });
    setTimeout(() => window.location.reload(), 400);
  }

  return (
    <Card>
      <Group gap="xs" mb="sm"><IconDatabase size={18} /><Text fw={600}>Aktive Datenbank</Text></Group>
      <Select
        data={dbs.map((d) => ({ value: d.id, label: `${d.name} (${d.role}, ${fmtBytes(d.size_bytes)})` }))}
        value={data?.active_id ?? null}
        onChange={(v) => { if (v) switchTo(v); }}
        onDropdownOpen={() => void reload()}
      />
    </Card>
  );
}

// ---------------------------------------------------------------- Sicherheit
function SecuritySection({ twoFactorEnabled }: { twoFactorEnabled: boolean }) {
  const { refresh } = useAuth();
  const [pwOpen, setPwOpen] = useState(false);
  const [twoOpen, setTwoOpen] = useState(false);
  const [disableOpen, setDisableOpen] = useState(false);
  return (
    <Card>
      <Text fw={600} mb="sm">Sicherheit</Text>
      <Group>
        <Button variant="light" onClick={() => setPwOpen(true)}>Passwort ändern</Button>
        {!twoFactorEnabled && <Button variant="light" onClick={() => setTwoOpen(true)}>Zwei-Faktor aktivieren</Button>}
        {twoFactorEnabled && (
          <>
            <Badge color="teal" variant="light">Zwei-Faktor aktiv</Badge>
            <Button variant="subtle" color="red" onClick={() => setDisableOpen(true)}>Deaktivieren</Button>
          </>
        )}
      </Group>
      <ChangePasswordModal opened={pwOpen} onClose={() => setPwOpen(false)} />
      <TwoFactorModal opened={twoOpen} onClose={() => setTwoOpen(false)} onDone={() => { setTwoOpen(false); void refresh(); }} />
      <TwoFactorDisableModal opened={disableOpen} onClose={() => setDisableOpen(false)} onDone={() => { setDisableOpen(false); void refresh(); }} />
    </Card>
  );
}

function TwoFactorDisableModal({ opened, onClose, onDone }: { opened: boolean; onClose: () => void; onDone: () => void }) {
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true); setError(null);
    try {
      await apiPost('/api/auth/2fa/disable', { password, code });
      notifications.show({ color: 'teal', message: 'Zwei-Faktor deaktiviert' });
      setPassword(''); setCode(''); onDone();
    } catch (e) { setError(e instanceof ApiError ? e.message : 'Fehler'); } finally { setBusy(false); }
  }

  return (
    <Modal opened={opened} onClose={onClose} title="Zwei-Faktor deaktivieren" centered>
      <Stack>
        {error && <Alert color="red" icon={<IconAlertTriangle size={16} />}>{error}</Alert>}
        <Text size="sm" c="dimmed">Zur Bestätigung Passwort und aktuellen Authenticator-Code eingeben.</Text>
        <PasswordInput label="Passwort" value={password} onChange={(e) => setPassword(e.currentTarget.value)} />
        <TextInput label="6-stelliger Code" value={code} onChange={(e) => setCode(e.currentTarget.value)} inputMode="numeric" maxLength={6} />
        <Group justify="flex-end">
          <Button color="red" loading={busy} disabled={!password || code.length < 6} onClick={() => void submit()}>Deaktivieren</Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function ChangePasswordModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);
    if (next !== confirm) { setError('Die Passwörter stimmen nicht überein.'); return; }
    setBusy(true);
    try {
      await apiPost('/api/auth/change-password', { current_password: current, new_password: next });
      notifications.show({ color: 'teal', message: 'Passwort geändert' });
      onClose();
    } catch (e) { setError(e instanceof ApiError ? e.message : 'Fehler'); } finally { setBusy(false); }
  }

  return (
    <Modal opened={opened} onClose={onClose} title="Passwort ändern" centered>
      <Stack>
        {error && <Alert color="red" icon={<IconAlertTriangle size={16} />}>{error}</Alert>}
        <PasswordInput label="Aktuelles Passwort" value={current} onChange={(e) => setCurrent(e.currentTarget.value)} />
        <PasswordInput label="Neues Passwort" value={next} onChange={(e) => setNext(e.currentTarget.value)} />
        <PasswordInput label="Bestätigen" value={confirm} onChange={(e) => setConfirm(e.currentTarget.value)} />
        <Group justify="flex-end"><Button loading={busy} disabled={!current || !next} onClick={() => void submit()}>Ändern</Button></Group>
      </Stack>
    </Modal>
  );
}

function TwoFactorModal({ opened, onClose, onDone }: { opened: boolean; onClose: () => void; onDone: () => void }) {
  const [setup, setSetup] = useState<{ secret: string; qr_data_uri: string } | null>(null);
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (opened && !setup) {
      apiPost<{ secret: string; qr_data_uri: string }>('/api/auth/2fa/setup').then(setSetup).catch((e) => setError(String(e)));
    }
    if (!opened) { setSetup(null); setCode(''); setError(null); }
  }, [opened, setup]);

  async function activate() {
    setBusy(true); setError(null);
    try { await apiPost('/api/auth/2fa/verify', { code }); notifications.show({ color: 'teal', message: 'Zwei-Faktor aktiv' }); onDone(); }
    catch (e) { setError(e instanceof ApiError ? e.message : 'Code ungültig'); } finally { setBusy(false); }
  }

  return (
    <Modal opened={opened} onClose={onClose} title="Zwei-Faktor aktivieren" centered>
      <Stack>
        {error && <Alert color="red" icon={<IconAlertTriangle size={16} />}>{error}</Alert>}
        {setup && <Image src={setup.qr_data_uri} w={200} mx="auto" alt="QR" />}
        {setup && <Code>{setup.secret}</Code>}
        <TextInput label="6-stelliger Code" value={code} onChange={(e) => setCode(e.currentTarget.value)} inputMode="numeric" />
        <Group justify="flex-end"><Button loading={busy} disabled={!setup || code.length < 6} onClick={() => void activate()}>Aktivieren</Button></Group>
      </Stack>
    </Modal>
  );
}

// ---------------------------------------------------------------- Backups
function BackupList() {
  const { data, loading, reload } = useApiData<{ entries: BackupInfo[]; total_bytes: number }>('/api/backup');
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try { await apiPost('/api/backup/run'); notifications.show({ color: 'teal', message: 'Sicherung erstellt' }); void reload(); }
    catch (e) { notifyError(e); } finally { setBusy(false); }
  }
  async function restore(f: string) {
    if (!confirm(`Sicherung „${f}" wiederherstellen? Die aktuelle Datenbank wird ersetzt.`)) return;
    try { await apiPost(`/api/backup/restore/${encodeURIComponent(f)}`); notifications.show({ color: 'teal', message: 'Wiederhergestellt – bitte neu anmelden' }); setTimeout(() => window.location.reload(), 800); }
    catch (e) { notifyError(e); }
  }
  async function del(f: string) {
    if (!confirm(`Sicherung „${f}" löschen?`)) return;
    try { await api(`/api/backup/${encodeURIComponent(f)}`, { method: 'DELETE' }); void reload(); }
    catch (e) { notifyError(e); }
  }

  return (
    <div>
      <Group justify="space-between" mb="xs">
        <Text size="sm" c="dimmed">Sicherungen{data ? ` · ${fmtBytes(data.total_bytes)}` : ''}</Text>
        <Button size="xs" loading={busy} onClick={() => void run()}>Sicherung jetzt erstellen</Button>
      </Group>
      {loading && !data ? <Skeleton h={80} /> : (data?.entries ?? []).length === 0 ? (
        <Text size="sm" c="dimmed">Keine Sicherungen vorhanden.</Text>
      ) : (
        <Table>
          <Table.Tbody>
            {(data?.entries ?? []).map((b) => (
              <Table.Tr key={b.filename}>
                <Table.Td><Text size="sm" ff="monospace">{b.filename}</Text></Table.Td>
                <Table.Td ta="right">{fmtBytes(b.size_bytes)}</Table.Td>
                <Table.Td ta="right">
                  <Group gap={4} justify="flex-end">
                    <ActionIcon component="a" href={`api/backup/${encodeURIComponent(b.filename)}`} variant="subtle" aria-label="Herunterladen"><IconDownload size={16} /></ActionIcon>
                    <Button size="compact-xs" variant="light" onClick={() => void restore(b.filename)}>Wiederherstellen</Button>
                    <ActionIcon color="red" variant="subtle" onClick={() => void del(b.filename)} aria-label="Löschen"><IconTrash size={16} /></ActionIcon>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </div>
  );
}
