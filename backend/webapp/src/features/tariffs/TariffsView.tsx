import { useRef, useState } from 'react';
import {
  Card, Stack, Group, Text, Select, Table, Button, NumberInput, TextInput, ActionIcon,
  Skeleton, Divider, Alert, Badge, Anchor, Loader, Box,
} from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { IconTrash, IconPlus, IconFileText, IconUpload, IconClockExclamation } from '@tabler/icons-react';
import dayjs from 'dayjs';
import { useApiData } from '../../api/useApi';
import { api, apiPost, apiUpload, ApiError } from '../../api/client';
import type { SystemRead, TariffPlan, TariffUploadResult, TariffExpiring } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { fmtCost, fmtDate } from '../../util/format';

function notifyError(e: unknown) {
  notifications.show({ color: 'red', message: e instanceof ApiError ? e.message : 'Fehler' });
}

export function TariffsView() {
  const { can } = useAuth();
  const systems = useApiData<SystemRead[]>('/api/systems');
  const expiring = useApiData<TariffExpiring[]>('/api/tariffs/expiring?within_days=45');
  const [systemId, setSystemId] = useState<string | null>(null);
  const tariffs = useApiData<TariffPlan[]>(systemId ? `/api/systems/${systemId}/tariffs` : null);
  const active = (systems.data ?? []).filter((s) => s.aktiv);
  const canWrite = can('write');

  async function del(id: string) {
    if (!confirm('Tarifperiode löschen?')) return;
    try { await api(`/api/tariffs/${id}`, { method: 'DELETE' }); void tariffs.reload(); void expiring.reload(); }
    catch (e) { notifyError(e); }
  }

  const alerts = expiring.data ?? [];

  return (
    <Stack gap="lg">
      {alerts.length > 0 && (
        <Alert color="orange" icon={<IconClockExclamation size={18} />} title="Kündigungstermine nahen">
          <Stack gap={4}>
            {alerts.map((a) => (
              <Text key={a.tariff_id} size="sm">
                <b>{a.system_name}</b>{a.anbieter ? ` · ${a.anbieter}` : ''}: Vertrag endet {fmtDate(a.gueltig_bis)} –
                {' '}kündbar bis <b>{fmtDate(a.notice_deadline)}</b> (in {a.days_until_deadline} Tagen).
              </Text>
            ))}
          </Stack>
        </Alert>
      )}

      <Card>
        <Group gap="sm" mb="sm">
          <Text fw={600}>Tarife</Text>
          <Select placeholder="System wählen …" w={260}
                  data={active.map((s) => ({ value: s.id, label: s.name }))}
                  value={systemId} onChange={setSystemId} />
        </Group>
        {!systemId ? (
          <Text size="sm" c="dimmed">Wähle ein System, um die Tarifperioden zu sehen.</Text>
        ) : tariffs.loading && !tariffs.data ? <Skeleton h={140} /> : (
          <Table.ScrollContainer minWidth={720}>
            <Table>
              <Table.Thead><Table.Tr>
                <Table.Th>Gültigkeit</Table.Th><Table.Th>Anbieter</Table.Th>
                <Table.Th ta="right">Arbeitspreis</Table.Th><Table.Th ta="right">Grundpreis/Jahr</Table.Th>
                <Table.Th>Kündigung</Table.Th><Table.Th>Vertrag</Table.Th>
                {canWrite && <Table.Th />}
              </Table.Tr></Table.Thead>
              <Table.Tbody>
                {(tariffs.data ?? []).map((t) => (
                  <Table.Tr key={t.id}>
                    <Table.Td>{fmtDate(t.gueltig_ab)} – {t.gueltig_bis ? fmtDate(t.gueltig_bis) : 'offen'}{t.aktiv ? ' · aktiv' : ''}</Table.Td>
                    <Table.Td>{t.anbieter ?? t.name ?? '–'}</Table.Td>
                    <Table.Td ta="right">{fmtCost(t.arbeitspreis)}</Table.Td>
                    <Table.Td ta="right">{fmtCost(t.grundpreis)}</Table.Td>
                    <Table.Td>
                      {t.notice_deadline ? (
                        <Badge size="xs" variant="light" color={t.notice_due_soon ? 'orange' : 'gray'}>
                          bis {fmtDate(t.notice_deadline)}
                        </Badge>
                      ) : <Text size="xs" c="dimmed">–</Text>}
                    </Table.Td>
                    <Table.Td>
                      {t.contract_document_url
                        ? <Anchor href={t.contract_document_url} target="_blank" size="sm"><Group gap={4}><IconFileText size={14} />ansehen</Group></Anchor>
                        : <Text size="xs" c="dimmed">–</Text>}
                    </Table.Td>
                    {canWrite && <Table.Td ta="right"><ActionIcon color="red" variant="subtle" onClick={() => void del(t.id)} aria-label="Löschen"><IconTrash size={16} /></ActionIcon></Table.Td>}
                  </Table.Tr>
                ))}
                {(tariffs.data ?? []).length === 0 && <Table.Tr><Table.Td colSpan={7}><Text size="sm" c="dimmed">Keine Tarifperioden.</Text></Table.Td></Table.Tr>}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}
      </Card>

      {systemId && canWrite && <AddTariff systemId={systemId} onSaved={() => { void tariffs.reload(); void expiring.reload(); }} />}
    </Stack>
  );
}

interface TariffForm {
  gueltig_ab: Date | null; gueltig_bis: Date | null; anbieter: string;
  arbeitspreis: number | ''; grundpreis: number | ''; notice_period_days: number | '';
}

function AddTariff({ systemId, onSaved }: { systemId: string; onSaved: () => void }) {
  const [busy, setBusy] = useState(false);
  const [documentUrl, setDocumentUrl] = useState<string | null>(null);
  const form = useForm<TariffForm>({
    initialValues: { gueltig_ab: new Date(), gueltig_bis: null, anbieter: '', arbeitspreis: '', grundpreis: '', notice_period_days: '' },
    validate: {
      gueltig_ab: (v) => (v ? null : 'Datum erforderlich'),
      arbeitspreis: (v) => (v === '' ? 'Arbeitspreis erforderlich' : null),
    },
  });

  function applySuggestion(res: TariffUploadResult) {
    setDocumentUrl(res.document_url);
    const s = res.suggestion;
    if (s.anbieter) form.setFieldValue('anbieter', s.anbieter);
    if (s.arbeitspreis != null) form.setFieldValue('arbeitspreis', s.arbeitspreis);
    if (s.grundpreis != null) form.setFieldValue('grundpreis', s.grundpreis);
    if (s.notice_period_days != null) form.setFieldValue('notice_period_days', s.notice_period_days);
    if (s.gueltig_ab) form.setFieldValue('gueltig_ab', new Date(s.gueltig_ab));
    if (s.gueltig_bis) form.setFieldValue('gueltig_bis', new Date(s.gueltig_bis));
    const found = [s.anbieter, s.arbeitspreis, s.grundpreis, s.notice_period_days].filter((x) => x != null).length;
    notifications.show({
      color: res.ocr_available ? (found ? 'teal' : 'yellow') : 'yellow',
      message: res.ocr_available
        ? (found ? `Dokument gelesen – ${found} Feld(er) übernommen. Bitte prüfen.` : 'Dokument gespeichert – keine Felder erkannt.')
        : 'Dokument gespeichert (Texterkennung nicht verfügbar).',
    });
  }

  async function submit(values: TariffForm) {
    setBusy(true);
    try {
      await apiPost(`/api/systems/${systemId}/tariffs`, {
        gueltig_ab: dayjs(values.gueltig_ab).format('YYYY-MM-DD'),
        gueltig_bis: values.gueltig_bis ? dayjs(values.gueltig_bis).format('YYYY-MM-DD') : null,
        anbieter: values.anbieter.trim() || null,
        arbeitspreis: Number(values.arbeitspreis),
        grundpreis: values.grundpreis === '' ? 0 : Number(values.grundpreis),
        notice_period_days: values.notice_period_days === '' ? null : Number(values.notice_period_days),
        contract_document_url: documentUrl,
      });
      notifications.show({ color: 'teal', message: 'Tarif gespeichert' });
      form.reset();
      setDocumentUrl(null);
      onSaved();
    } catch (e) { notifyError(e); } finally { setBusy(false); }
  }

  return (
    <Card>
      <Text fw={600} mb="sm">Tarifperiode hinzufügen</Text>
      <UploadZone onUploaded={applySuggestion} />
      {documentUrl && (
        <Text size="xs" c="teal" mt={6}>
          <Group gap={4} component="span"><IconFileText size={14} /> Vertragsunterlage angehängt</Group>
        </Text>
      )}
      <Divider my="sm" label="Manuelle Angaben / Korrektur" labelPosition="left" />
      <form onSubmit={form.onSubmit(submit)}>
        <Group align="flex-end" wrap="wrap">
          <DatePickerInput label="Gültig ab" valueFormat="DD.MM.YYYY" w={150} {...form.getInputProps('gueltig_ab')} />
          <DatePickerInput label="Gültig bis (optional)" valueFormat="DD.MM.YYYY" w={170} clearable {...form.getInputProps('gueltig_bis')} />
          <TextInput label="Anbieter" w={180} {...form.getInputProps('anbieter')} />
          <NumberInput label="Arbeitspreis (€/Einheit)" decimalScale={4} w={180} {...form.getInputProps('arbeitspreis')} />
          <NumberInput label="Grundpreis (€/Jahr)" decimalScale={2} w={170} {...form.getInputProps('grundpreis')} />
          <NumberInput label="Kündigungsfrist (Tage)" w={170} {...form.getInputProps('notice_period_days')} />
          <Button type="submit" loading={busy} leftSection={<IconPlus size={16} />}>Hinzufügen</Button>
        </Group>
      </form>
    </Card>
  );
}

// Drag&Drop-Zone für die Vertragsunterlage (PDF/Bild). Ohne Zusatzabhängigkeit
// über die nativen Drag-Events umgesetzt, im bestehenden Designsystem.
function UploadZone({ onUploaded }: { onUploaded: (r: TariffUploadResult) => void }) {
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File | undefined | null) {
    if (!file) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await apiUpload<TariffUploadResult>('/api/tariffs/upload', fd);
      onUploaded(res);
    } catch (e) { notifyError(e); } finally { setBusy(false); }
  }

  return (
    <Box
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => { e.preventDefault(); setDragOver(false); void handleFile(e.dataTransfer.files?.[0]); }}
      onClick={() => inputRef.current?.click()}
      style={{
        border: `2px dashed var(--mantine-color-${dragOver ? 'teal' : 'gray'}-4)`,
        borderRadius: 'var(--mantine-radius-md)',
        padding: 'var(--mantine-spacing-lg)',
        textAlign: 'center', cursor: 'pointer',
        background: dragOver ? 'var(--mantine-color-teal-light)' : undefined,
      }}
    >
      <input ref={inputRef} type="file" accept=".pdf,image/*" hidden
             onChange={(e) => void handleFile(e.currentTarget.files?.[0])} />
      <Group justify="center" gap="xs">
        {busy ? <Loader size="sm" /> : <IconUpload size={20} />}
        <Text size="sm" c="dimmed">
          {busy ? 'Dokument wird gelesen …' : 'Vertrag (PDF/Foto) hierher ziehen oder klicken – Felder werden automatisch vorgeschlagen'}
        </Text>
      </Group>
    </Box>
  );
}
