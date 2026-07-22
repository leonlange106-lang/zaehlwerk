import { useState } from 'react';
import {
  Card, Stack, Group, Text, Select, Table, Button, NumberInput, TextInput, ActionIcon,
  Skeleton, Divider,
} from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { IconTrash, IconPlus } from '@tabler/icons-react';
import dayjs from 'dayjs';
import { useApiData } from '../../api/useApi';
import { api, apiPost, ApiError } from '../../api/client';
import type { SystemRead, TariffPlan } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { fmtCost, fmtDate } from '../../util/format';

function notifyError(e: unknown) {
  notifications.show({ color: 'red', message: e instanceof ApiError ? e.message : 'Fehler' });
}

export function TariffsView() {
  const { can } = useAuth();
  const systems = useApiData<SystemRead[]>('/api/systems');
  const [systemId, setSystemId] = useState<string | null>(null);
  const tariffs = useApiData<TariffPlan[]>(systemId ? `/api/systems/${systemId}/tariffs` : null);
  const active = (systems.data ?? []).filter((s) => s.aktiv);
  const canWrite = can('write');

  async function del(id: string) {
    if (!confirm('Tarifperiode löschen?')) return;
    try { await api(`/api/tariffs/${id}`, { method: 'DELETE' }); void tariffs.reload(); }
    catch (e) { notifyError(e); }
  }

  return (
    <Stack gap="lg">
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
          <Table.ScrollContainer minWidth={640}>
            <Table>
              <Table.Thead><Table.Tr>
                <Table.Th>Gültigkeit</Table.Th><Table.Th>Anbieter</Table.Th>
                <Table.Th ta="right">Arbeitspreis</Table.Th><Table.Th ta="right">Grundpreis/Jahr</Table.Th>
                {canWrite && <Table.Th />}
              </Table.Tr></Table.Thead>
              <Table.Tbody>
                {(tariffs.data ?? []).map((t) => (
                  <Table.Tr key={t.id}>
                    <Table.Td>{fmtDate(t.gueltig_ab)} – {t.gueltig_bis ? fmtDate(t.gueltig_bis) : 'offen'}{t.aktiv ? ' ·  aktiv' : ''}</Table.Td>
                    <Table.Td>{t.anbieter ?? t.name ?? '–'}</Table.Td>
                    <Table.Td ta="right">{fmtCost(t.arbeitspreis)}</Table.Td>
                    <Table.Td ta="right">{fmtCost(t.grundpreis)}</Table.Td>
                    {canWrite && <Table.Td ta="right"><ActionIcon color="red" variant="subtle" onClick={() => void del(t.id)} aria-label="Löschen"><IconTrash size={16} /></ActionIcon></Table.Td>}
                  </Table.Tr>
                ))}
                {(tariffs.data ?? []).length === 0 && <Table.Tr><Table.Td colSpan={5}><Text size="sm" c="dimmed">Keine Tarifperioden.</Text></Table.Td></Table.Tr>}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}
      </Card>

      {systemId && canWrite && <AddTariff systemId={systemId} onSaved={() => void tariffs.reload()} />}
    </Stack>
  );
}

function AddTariff({ systemId, onSaved }: { systemId: string; onSaved: () => void }) {
  const [busy, setBusy] = useState(false);
  const form = useForm<{ gueltig_ab: Date | null; gueltig_bis: Date | null; anbieter: string; arbeitspreis: number | ''; grundpreis: number | '' }>({
    initialValues: { gueltig_ab: new Date(), gueltig_bis: null, anbieter: '', arbeitspreis: '', grundpreis: '' },
    validate: {
      gueltig_ab: (v) => (v ? null : 'Datum erforderlich'),
      arbeitspreis: (v) => (v === '' ? 'Arbeitspreis erforderlich' : null),
    },
  });

  async function submit(values: typeof form.values) {
    setBusy(true);
    try {
      await apiPost(`/api/systems/${systemId}/tariffs`, {
        gueltig_ab: dayjs(values.gueltig_ab).format('YYYY-MM-DD'),
        gueltig_bis: values.gueltig_bis ? dayjs(values.gueltig_bis).format('YYYY-MM-DD') : null,
        anbieter: values.anbieter.trim() || null,
        arbeitspreis: Number(values.arbeitspreis),
        grundpreis: values.grundpreis === '' ? 0 : Number(values.grundpreis),
      });
      notifications.show({ color: 'teal', message: 'Tarif gespeichert' });
      form.reset();
      onSaved();
    } catch (e) { notifyError(e); } finally { setBusy(false); }
  }

  return (
    <Card>
      <Text fw={600} mb="sm">Tarifperiode hinzufügen</Text>
      <form onSubmit={form.onSubmit(submit)}>
        <Group align="flex-end" wrap="wrap">
          <DatePickerInput label="Gültig ab" valueFormat="DD.MM.YYYY" w={150} {...form.getInputProps('gueltig_ab')} />
          <DatePickerInput label="Gültig bis (optional)" valueFormat="DD.MM.YYYY" w={170} clearable {...form.getInputProps('gueltig_bis')} />
          <TextInput label="Anbieter" w={180} {...form.getInputProps('anbieter')} />
          <NumberInput label="Arbeitspreis (€/Einheit)" decimalScale={4} w={180} {...form.getInputProps('arbeitspreis')} />
          <NumberInput label="Grundpreis (€/Jahr)" decimalScale={2} w={170} {...form.getInputProps('grundpreis')} />
          <Button type="submit" loading={busy} leftSection={<IconPlus size={16} />}>Hinzufügen</Button>
        </Group>
      </form>
      <Divider mt="sm" />
    </Card>
  );
}
