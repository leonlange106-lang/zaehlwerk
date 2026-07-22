import { useEffect, useState } from 'react';
import {
  Tabs, Card, Table, Group, Badge, Text, Button, ActionIcon, Skeleton, Alert,
  Stack, Select, Collapse, Divider, Textarea, Code, ScrollArea, TextInput, CopyButton,
  Progress, ThemeIcon,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconAlertTriangle, IconTrash, IconChevronDown, IconChevronUp, IconPlayerPlay,
  IconRefresh, IconCheck, IconX, IconClockHour4, IconLoader2,
} from '@tabler/icons-react';
import { useApiData } from '../../api/useApi';
import { api, apiPost, apiPatch, ApiError } from '../../api/client';
import type {
  AdminUserStatus, AdminSession, AdminDatabase, DatabaseAccessEntry, User,
  LogEntry, QueryResult, UpdateStatus, UpdateStep,
} from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { fmtBytes, fmtDate } from '../../util/format';
import { MqttTab } from './MqttTab';

function relTime(iso: string | null): string {
  if (!iso) return '–';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '–';
  return d.toLocaleString('de-DE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function notifyError(e: unknown) {
  notifications.show({ color: 'red', message: e instanceof ApiError ? e.message : 'Fehler' });
}

export function AdminView() {
  return (
    <Tabs defaultValue="monitoring" keepMounted={false}>
      <Tabs.List mb="md">
        <Tabs.Tab value="monitoring">Monitoring</Tabs.Tab>
        <Tabs.Tab value="databases">Datenbanken</Tabs.Tab>
        <Tabs.Tab value="access">Zugriff</Tabs.Tab>
        <Tabs.Tab value="diagnostics">Diagnose</Tabs.Tab>
        <Tabs.Tab value="query">Abfrage</Tabs.Tab>
        <Tabs.Tab value="logs">Protokoll</Tabs.Tab>
        <Tabs.Tab value="mqtt">MQTT</Tabs.Tab>
        <Tabs.Tab value="update">Update</Tabs.Tab>
      </Tabs.List>
      <Tabs.Panel value="monitoring"><MonitoringTab /></Tabs.Panel>
      <Tabs.Panel value="databases"><DatabasesTab /></Tabs.Panel>
      <Tabs.Panel value="access"><AccessTab /></Tabs.Panel>
      <Tabs.Panel value="diagnostics"><DiagnosticsTab /></Tabs.Panel>
      <Tabs.Panel value="query"><QueryTab /></Tabs.Panel>
      <Tabs.Panel value="logs"><LogsTab /></Tabs.Panel>
      <Tabs.Panel value="mqtt"><MqttTab /></Tabs.Panel>
      <Tabs.Panel value="update"><UpdateTab /></Tabs.Panel>
    </Tabs>
  );
}

// ---------------------------------------------------------------- Monitoring
function MonitoringTab() {
  const users = useApiData<AdminUserStatus[]>('/api/admin/monitoring/users');
  const sessions = useApiData<AdminSession[]>('/api/admin/monitoring/sessions');

  function reload() { void users.reload(); void sessions.reload(); }

  async function terminateAll(u: AdminUserStatus) {
    if (!confirm(`Alle Sitzungen von „${u.display_name}" beenden?`)) return;
    try { await apiPost(`/api/admin/monitoring/users/${u.id}/logout`); reload(); }
    catch (e) { notifyError(e); }
  }
  async function terminate(s: AdminSession) {
    try { await api(`/api/admin/monitoring/sessions/${s.jti}`, { method: 'DELETE' }); reload(); }
    catch (e) { notifyError(e); }
  }

  return (
    <Stack gap="lg">
      <Card>
        <Text fw={600} mb="sm">Konten &amp; Status</Text>
        {users.loading && !users.data ? <Skeleton h={160} /> : (
          <Table.ScrollContainer minWidth={720}>
            <Table>
              <Table.Thead><Table.Tr>
                <Table.Th>Konto</Table.Th><Table.Th>Rolle</Table.Th><Table.Th>2FA</Table.Th>
                <Table.Th>Passwort</Table.Th><Table.Th>Zuletzt</Table.Th>
                <Table.Th ta="right">Sitzungen</Table.Th><Table.Th />
              </Table.Tr></Table.Thead>
              <Table.Tbody>
                {(users.data ?? []).map((u) => (
                  <Table.Tr key={u.id}>
                    <Table.Td>
                      <Group gap={8} wrap="nowrap">
                        <span style={{ width: 9, height: 9, borderRadius: 5, background: u.online ? 'var(--mantine-color-teal-6)' : 'var(--mantine-color-gray-4)' }} />
                        <Text size="sm">{u.display_name}</Text>
                        <Text size="xs" c="dimmed">· {u.username}</Text>
                      </Group>
                    </Table.Td>
                    <Table.Td>{u.role}</Table.Td>
                    <Table.Td><Badge size="xs" variant="light" color={u.two_factor_enabled ? 'teal' : 'orange'}>{u.two_factor_status}</Badge></Table.Td>
                    <Table.Td><Badge size="xs" variant="light" color={u.password_status === 'temporär' ? 'orange' : 'gray'}>{u.password_status}</Badge></Table.Td>
                    <Table.Td><Text size="xs">{relTime(u.last_seen)}</Text></Table.Td>
                    <Table.Td ta="right">{u.active_sessions}</Table.Td>
                    <Table.Td ta="right">
                      <Button size="compact-xs" variant="light" color="red" disabled={!u.active_sessions} onClick={() => void terminateAll(u)}>Abmelden</Button>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}
      </Card>

      <Card>
        <Text fw={600} mb="sm">Aktive Sitzungen</Text>
        {sessions.loading && !sessions.data ? <Skeleton h={120} /> : (
          <Table.ScrollContainer minWidth={620}>
            <Table>
              <Table.Thead><Table.Tr>
                <Table.Th>Konto</Table.Th><Table.Th>Gerät</Table.Th><Table.Th>IP</Table.Th>
                <Table.Th>Zuletzt</Table.Th><Table.Th />
              </Table.Tr></Table.Thead>
              <Table.Tbody>
                {(sessions.data ?? []).map((s) => (
                  <Table.Tr key={s.jti}>
                    <Table.Td><Group gap={6}>{s.username}{s.current && <Badge size="xs" color="teal" variant="light">aktuell</Badge>}</Group></Table.Td>
                    <Table.Td><Text size="xs">{shortAgent(s.user_agent)}</Text></Table.Td>
                    <Table.Td><Text size="xs">{s.ip ?? '–'}</Text></Table.Td>
                    <Table.Td><Text size="xs">{relTime(s.last_seen)}</Text></Table.Td>
                    <Table.Td ta="right"><ActionIcon color="red" variant="subtle" disabled={s.current} onClick={() => void terminate(s)} aria-label="Beenden"><IconTrash size={16} /></ActionIcon></Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}
      </Card>
    </Stack>
  );
}

function shortAgent(ua: string | null): string {
  if (!ua) return 'unbekannt';
  for (const t of ['iPhone', 'iPad', 'Android', 'Macintosh', 'Windows', 'Linux']) if (ua.includes(t)) return t;
  return ua.slice(0, 20);
}

// ---------------------------------------------------------------- Datenbanken
function DatabasesTab() {
  const dbs = useApiData<AdminDatabase[]>('/api/admin/databases');
  const users = useApiData<AdminUserStatus[]>('/api/admin/monitoring/users');
  const [open, setOpen] = useState<string | null>(null);

  return (
    <Card>
      <Text fw={600} mb="sm">Datenbanken</Text>
      {dbs.loading && !dbs.data ? <Skeleton h={160} /> : (
        <Stack gap="xs">
          {(dbs.data ?? []).map((db) => (
            <div key={db.id}>
              <Group justify="space-between" onClick={() => setOpen(open === db.id ? null : db.id)} style={{ cursor: 'pointer' }}>
                <Group gap={8}>
                  <Text size="sm" fw={500}>{db.name}</Text>
                  {db.is_default && <Badge size="xs" variant="light" color="gray">Standard</Badge>}
                  <Text size="xs" c="dimmed">{db.owner_name ?? '–'} · {fmtBytes(db.size_bytes)} · {db.shared_with} geteilt</Text>
                </Group>
                {open === db.id ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
              </Group>
              <Collapse in={open === db.id}>
                <AccessMatrix db={db} users={users.data ?? []} />
              </Collapse>
              <Divider my="xs" />
            </div>
          ))}
        </Stack>
      )}
    </Card>
  );
}

function AccessMatrix({ db, users }: { db: AdminDatabase; users: AdminUserStatus[] }) {
  const access = useApiData<DatabaseAccessEntry[]>(`/api/admin/databases/${db.id}/access`);
  const [userId, setUserId] = useState<string | null>(null);
  const [role, setRole] = useState<string>('read_only');

  const name = (id: string) => users.find((u) => u.id === id)?.display_name ?? id;

  async function grant() {
    if (!userId) return;
    try {
      await apiPost(`/api/admin/databases/${db.id}/access`, { user_id: userId, role });
      setUserId(null);
      void access.reload();
    } catch (e) { notifyError(e); }
  }
  async function revoke(uid: string) {
    try { await api(`/api/admin/databases/${db.id}/access/${uid}`, { method: 'DELETE' }); void access.reload(); }
    catch (e) { notifyError(e); }
  }

  return (
    <Stack gap={6} py="xs" pl="md">
      {(access.data ?? []).map((a) => (
        <Group key={a.user_id} gap="sm">
          <Text size="sm" w={160}>{name(a.user_id)}</Text>
          <Badge size="xs" variant="light" color={a.role === 'owner' ? 'teal' : 'gray'}>{roleLabelDb(a.role)}</Badge>
          {!a.implicit && <Button size="compact-xs" variant="subtle" color="red" onClick={() => void revoke(a.user_id)}>Entziehen</Button>}
        </Group>
      ))}
      <Group gap="sm" align="flex-end">
        <Select placeholder="Konto …" size="xs" data={users.map((u) => ({ value: u.id, label: u.display_name }))} value={userId} onChange={setUserId} searchable w={180} />
        <Select size="xs" data={[{ value: 'read_only', label: 'Lesen' }, { value: 'read_write', label: 'Schreiben' }, { value: 'owner', label: 'Eigentümer' }]} value={role} onChange={(v) => setRole(v ?? 'read_only')} w={130} />
        <Button size="compact-xs" onClick={() => void grant()} disabled={!userId}>Zuweisen</Button>
      </Group>
    </Stack>
  );
}

function roleLabelDb(r: string): string {
  return { owner: 'Eigentümer', read_write: 'Schreiben', read_only: 'Lesen' }[r] ?? r;
}

// ---------------------------------------------------------------- Zugriff
function AccessTab() {
  const { roles } = useAuth();
  const users = useApiData<User[]>('/api/auth/users');
  const [created, setCreated] = useState<{ username: string; temp: string } | null>(null);
  const [nu, setNu] = useState({ username: '', display_name: '', role: 'viewer' });
  const [busy, setBusy] = useState(false);
  const roleData = roles.map((r) => ({ value: r.key, label: r.label }));

  async function setRole(u: User, role: string) {
    try { await apiPatch(`/api/auth/users/${u.id}`, { role }); void users.reload(); }
    catch (e) { notifyError(e); }
  }
  async function create() {
    setBusy(true);
    try {
      const res = await apiPost<{ user: User; temp_password: string }>('/api/admin/users/create',
        { username: nu.username.trim(), display_name: nu.display_name.trim() || null, role: nu.role });
      setCreated({ username: res.user.username, temp: res.temp_password });
      setNu({ username: '', display_name: '', role: 'viewer' });
      void users.reload();
    } catch (e) { notifyError(e); } finally { setBusy(false); }
  }

  return (
    <Stack gap="lg">
      <Card>
        <Text fw={600} mb="sm">Konten &amp; Rollen</Text>
        {users.loading && !users.data ? <Skeleton h={160} /> : (
          <Table>
            <Table.Tbody>
              {(users.data ?? []).map((u) => (
                <Table.Tr key={u.id}>
                  <Table.Td><Text size="sm">{u.display_name}</Text><Text size="xs" c="dimmed">{u.username}{u.source === 'homeassistant' ? ' · HA' : ''}</Text></Table.Td>
                  <Table.Td ta="right" w={200}>
                    <Select size="xs" data={roleData} value={u.role} onChange={(v) => v && void setRole(u, v)} />
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>

      <Card>
        <Text fw={600} mb="sm">Benutzer anlegen</Text>
        <Stack gap="sm">
          <TextInput label="Benutzername" placeholder="z. B. anna.muster" value={nu.username} onChange={(e) => setNu({ ...nu, username: e.currentTarget.value })} />
          <TextInput label="Anzeigename (optional)" value={nu.display_name} onChange={(e) => setNu({ ...nu, display_name: e.currentTarget.value })} />
          <Select label="Rolle" data={roleData} value={nu.role} onChange={(v) => setNu({ ...nu, role: v ?? 'viewer' })} />
          <Group><Button loading={busy} disabled={nu.username.trim().length < 3} onClick={() => void create()}>Anlegen</Button></Group>
          {created && (
            <Alert color="teal" title={`Konto „${created.username}" angelegt`}>
              <Group>
                <Text size="sm">Temporäres Passwort (nur jetzt sichtbar):</Text>
                <Code>{created.temp}</Code>
                <CopyButton value={created.temp}>{({ copied, copy }) => <Button size="compact-xs" variant="light" onClick={copy}>{copied ? 'Kopiert' : 'Kopieren'}</Button>}</CopyButton>
              </Group>
            </Alert>
          )}
        </Stack>
      </Card>
    </Stack>
  );
}

// ---------------------------------------------------------------- Diagnose
interface Diagnostics {
  app_version: string;
  schema_version: number;
  database: { sizes_bytes?: Record<string, number>; journal_mode?: string; integrity_check?: string; fragmentation_pct?: number };
  outbound: { offline_mode?: boolean };
  mqtt: { connected?: boolean; broker?: string | null };
}

function DiagnosticsTab() {
  const { data, loading, error } = useApiData<Diagnostics>('/api/admin/diagnostics');
  if (loading && !data) return <Skeleton h={240} />;
  if (error) return <Alert color="red" icon={<IconAlertTriangle size={16} />}>{error}</Alert>;
  if (!data) return null;
  const dbSize = Object.values(data.database?.sizes_bytes ?? {}).reduce((a, b) => a + b, 0);
  const rows: [string, string][] = [
    ['App-Version', data.app_version],
    ['Schema-Version', String(data.schema_version)],
    ['Datenbankgröße', fmtBytes(dbSize)],
    ['Journal-Modus', data.database?.journal_mode ?? '–'],
    ['Integrität', data.database?.integrity_check ?? '–'],
    ['Fragmentierung', `${data.database?.fragmentation_pct ?? 0} %`],
    ['Offline-Modus', data.outbound?.offline_mode ? 'aktiv' : 'aus'],
    ['MQTT', data.mqtt?.connected ? `verbunden (${data.mqtt.broker ?? ''})` : 'getrennt'],
  ];
  return (
    <Card>
      <Text fw={600} mb="sm">Diagnose</Text>
      <Table>
        <Table.Tbody>
          {rows.map(([k, v]) => (
            <Table.Tr key={k}><Table.Td>{k}</Table.Td><Table.Td ta="right"><Text size="sm" ff="monospace">{v}</Text></Table.Td></Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Card>
  );
}

// ---------------------------------------------------------------- Abfrage
function QueryTab() {
  const [sql, setSql] = useState('SELECT name, typ, einheit FROM systems ORDER BY name');
  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true); setError(null);
    try { setResult(await apiPost<QueryResult>('/api/admin/query', { sql })); }
    catch (e) { setError(e instanceof ApiError ? e.message : 'Fehler'); setResult(null); }
    finally { setBusy(false); }
  }

  return (
    <Card>
      <Text fw={600} mb="sm">Lesende Datenbankabfrage</Text>
      <Textarea value={sql} onChange={(e) => setSql(e.currentTarget.value)} autosize minRows={2} ff="monospace" />
      <Group mt="sm"><Button size="xs" leftSection={<IconPlayerPlay size={14} />} loading={busy} onClick={() => void run()}>Ausführen</Button></Group>
      {error && <Alert color="red" mt="sm" icon={<IconAlertTriangle size={16} />}>{error}</Alert>}
      {result && (
        <ScrollArea mt="sm">
          <Table striped withTableBorder>
            <Table.Thead><Table.Tr>{result.columns.map((c) => <Table.Th key={c}>{c}</Table.Th>)}</Table.Tr></Table.Thead>
            <Table.Tbody>
              {result.rows.map((r, i) => (
                <Table.Tr key={i}>{r.map((v, j) => <Table.Td key={j}><Text size="xs" ff="monospace">{v == null ? '∅' : String(v)}</Text></Table.Td>)}</Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          <Text size="xs" c="dimmed" mt={4}>{result.row_count} Zeilen{result.truncated ? ' (gekürzt)' : ''}</Text>
        </ScrollArea>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------- Protokoll
function LogsTab() {
  const [level, setLevel] = useState('INFO');
  const { data, loading, reload } = useApiData<{ entries: LogEntry[] }>(`/api/admin/logs?lines=200&level=${level}`);
  const color: Record<string, string> = { ERROR: 'red', CRITICAL: 'red', WARNING: 'orange', INFO: 'gray', DEBUG: 'gray' };
  return (
    <Card>
      <Group justify="space-between" mb="sm">
        <Text fw={600}>Anwendungsprotokoll</Text>
        <Group gap="xs">
          <Select size="xs" w={120} data={['DEBUG', 'INFO', 'WARNING', 'ERROR']} value={level} onChange={(v) => setLevel(v ?? 'INFO')} />
          <ActionIcon variant="default" onClick={() => void reload()} aria-label="Aktualisieren"><IconRefresh size={16} /></ActionIcon>
        </Group>
      </Group>
      {loading && !data ? <Skeleton h={200} /> : (
        <ScrollArea h={360}>
          <Stack gap={2}>
            {(data?.entries ?? []).map((e, i) => (
              <Group key={i} gap="xs" wrap="nowrap" align="flex-start">
                <Text size="xs" c="dimmed" ff="monospace" style={{ whiteSpace: 'nowrap' }}>{e.ts.replace('T', ' ')}</Text>
                <Badge size="xs" variant="light" color={color[e.level] ?? 'gray'}>{e.level}</Badge>
                <Text size="xs" ff="monospace">{e.message}</Text>
              </Group>
            ))}
          </Stack>
        </ScrollArea>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------- Update
function UpdateTab() {
  const { data, loading, reload } = useApiData<UpdateStatus>('/api/update/status');
  const [busy, setBusy] = useState(false);

  // Solange ein Vorgang läuft (oder eine Anforderung ansteht), im Takt pollen,
  // damit Ladebalken und Schritt-Log live mitlaufen.
  const running = !!data?.progress?.running || !!data?.pending;
  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => void reload(), 2500);
    return () => clearInterval(t);
  }, [running, reload]);

  async function act(path: string, msg: string) {
    setBusy(true);
    try { await apiPost(path); notifications.show({ color: 'teal', message: msg }); void reload(); }
    catch (e) { notifyError(e); } finally { setBusy(false); }
  }

  if (loading && !data) return <Skeleton h={160} />;
  if (!data?.supported) {
    return <Card><Text c="dimmed" size="sm">Der Selbst-Update-Weg ist in dieser Umgebung nicht eingerichtet.</Text></Card>;
  }

  const progress = data.progress;
  // Schritt-Protokoll: läuft/lief ein Vorgang, dessen Schritte zeigen; sonst die
  // Schritte der letzten Versionsprüfung.
  const steps = progress?.steps?.length ? progress.steps : (data.check_steps ?? []);
  const failed = progress && !progress.running && progress.phase === 'failed';

  return (
    <Card>
      <Text fw={600} mb="sm">Selbst-Update</Text>
      <Table>
        <Table.Tbody>
          <Table.Tr><Table.Td>Installiert</Table.Td><Table.Td ta="right"><Code>{data.current}</Code></Table.Td></Table.Tr>
          <Table.Tr>
            <Table.Td>Verfügbar</Table.Td>
            <Table.Td ta="right">
              <Group gap={6} justify="flex-end">
                <Code>{data.latest ?? '–'}</Code>
                {data.update_available && <Badge size="xs" color="teal" variant="light">neu</Badge>}
              </Group>
            </Table.Td>
          </Table.Tr>
        </Table.Tbody>
      </Table>

      <Group mt="sm">
        <Button size="xs" variant="light" loading={busy} onClick={() => void act('/api/update/check', 'Prüfung ausgelöst')}>Auf Updates prüfen</Button>
        <Button size="xs" loading={busy || !!progress?.running} disabled={!data.update_available || !!progress?.running} onClick={() => void act('/api/update/run', 'Update angefordert')}>Aktualisieren</Button>
        <Button size="xs" variant="default" loading={busy} disabled={!!progress?.running} onClick={() => void act('/api/update/rollback', 'Rollback angefordert')}>Zur Vorversion</Button>
      </Group>

      {data.check_error && !progress && (
        <Alert mt="sm" color="orange" icon={<IconAlertTriangle size={16} />}>
          Versionsprüfung fehlgeschlagen: {data.check_error}
        </Alert>
      )}

      {progress && (
        <Stack gap={6} mt="md">
          <Group justify="space-between">
            <Text size="sm" fw={500}>
              {progress.action === 'rollback' ? 'Rollback' : 'Update'} · {progress.message}
            </Text>
            <Text size="xs" c="dimmed">{progress.percent}%</Text>
          </Group>
          <Progress
            value={progress.percent} animated={progress.running}
            color={failed ? 'red' : progress.running ? 'blue' : 'teal'}
          />
        </Stack>
      )}

      {steps.length > 0 && (
        <Stack gap={4} mt="md">
          <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Protokoll</Text>
          {steps.map((s, i) => <StepRow key={i} step={s} active={!!progress?.running && i === steps.length - 1} />)}
        </Stack>
      )}

      {data.last_action && !progress?.running && (
        <Text size="xs" c="dimmed" mt="sm">
          Letzter Vorgang: {data.last_action.action} · {data.last_action.ok ? 'erfolgreich' : 'fehlgeschlagen'}
          {data.last_action.finished_at ? ` (${fmtDate(data.last_action.finished_at)})` : ''}
        </Text>
      )}
    </Card>
  );
}

function StepRow({ step, active }: { step: UpdateStep; active: boolean }) {
  const { icon, color } = active
    ? { icon: <IconLoader2 size={12} />, color: 'blue' as const }
    : step.ok === true ? { icon: <IconCheck size={12} />, color: 'teal' as const }
      : step.ok === false ? { icon: <IconX size={12} />, color: 'red' as const }
        : { icon: <IconClockHour4 size={12} />, color: 'gray' as const };
  return (
    <Group gap={8} wrap="nowrap" align="center">
      <ThemeIcon size="sm" variant="light" color={color}>{icon}</ThemeIcon>
      <Text size="sm" style={{ wordBreak: 'break-word' }}>{step.message}</Text>
    </Group>
  );
}
