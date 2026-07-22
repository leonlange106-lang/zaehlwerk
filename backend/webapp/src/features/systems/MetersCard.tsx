import { useState } from 'react';
import {
  Card, Title, Group, Button, Table, Text, Badge, ActionIcon, Modal, TextInput,
  NumberInput, Textarea, SimpleGrid, Autocomplete, Skeleton, Stack,
} from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { IconPlus, IconPencil, IconTrash, IconGauge } from '@tabler/icons-react';
import dayjs from 'dayjs';
import { useApiData } from '../../api/useApi';
import { apiGet, apiPost, apiPatch, apiDelete, ApiError } from '../../api/client';
import type { Meter } from '../../api/types';
import { fmtDate } from '../../util/format';

// Zähler-Metadaten eines Systems (rein dokumentarisch, ohne Einfluss auf die
// Verbrauchslogik). Verwaltung von Hersteller/Modell/Nummer/Eichfrist.
export function MetersCard({ systemId, canWrite }: { systemId: string; canWrite: boolean }) {
  const meters = useApiData<Meter[]>(`/api/systems/${systemId}/meters`);
  const [formOpen, setFormOpen] = useState(false);
  const [editMeter, setEditMeter] = useState<Meter | undefined>();

  const rows = meters.data ?? [];

  function openCreate() { setEditMeter(undefined); setFormOpen(true); }
  async function openEdit(id: string) {
    try {
      setEditMeter(await apiGet<Meter>(`/api/meters/${id}`));
      setFormOpen(true);
    } catch (e) {
      notifications.show({ color: 'red', message: e instanceof ApiError ? e.message : 'Laden fehlgeschlagen' });
    }
  }
  async function remove(m: Meter) {
    if (!confirm(`Zähler ${m.zaehlernummer ?? ''} löschen?`)) return;
    try {
      await apiDelete(`/api/meters/${m.id}`);
      notifications.show({ message: 'Zähler gelöscht', color: 'teal' });
      void meters.reload();
    } catch (e) {
      notifications.show({ color: 'red', message: e instanceof ApiError ? e.message : 'Fehler' });
    }
  }

  return (
    <Card>
      <Group justify="space-between" mb="sm">
        <Group gap="xs">
          <IconGauge size={18} />
          <Title order={5}>Zähler</Title>
          {rows.length > 0 && <Badge variant="light" color="gray">{rows.length}</Badge>}
        </Group>
        {canWrite && (
          <Button size="xs" variant="light" leftSection={<IconPlus size={16} />} onClick={openCreate}>
            Zähler hinzufügen
          </Button>
        )}
      </Group>

      {meters.loading && !meters.data ? (
        <Skeleton h={80} />
      ) : rows.length === 0 ? (
        <Text c="dimmed" size="sm">Noch kein Zähler hinterlegt.</Text>
      ) : (
        <Table.ScrollContainer minWidth={560}>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Zählernummer</Table.Th>
                <Table.Th>Hersteller / Modell</Table.Th>
                <Table.Th>Bauart</Table.Th>
                <Table.Th>Eichfrist</Table.Th>
                {canWrite && <Table.Th />}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {rows.map((m) => (
                <Table.Tr key={m.id}>
                  <Table.Td>
                    <Group gap={6}>
                      <Text size="sm">{m.zaehlernummer ?? '–'}</Text>
                      {!m.aktiv && <Badge size="xs" variant="light" color="gray">ausgebaut</Badge>}
                    </Group>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{[m.hersteller, m.modell].filter(Boolean).join(' · ') || '–'}</Text>
                  </Table.Td>
                  <Table.Td><Text size="sm" c="dimmed">{m.bauart ?? '–'}</Text></Table.Td>
                  <Table.Td><CalibrationBadge meter={m} /></Table.Td>
                  {canWrite && (
                    <Table.Td ta="right">
                      <Group gap={4} justify="flex-end" wrap="nowrap">
                        <ActionIcon variant="subtle" color="gray" aria-label="Bearbeiten" onClick={() => void openEdit(m.id)}>
                          <IconPencil size={16} />
                        </ActionIcon>
                        <ActionIcon variant="subtle" color="red" aria-label="Löschen" onClick={() => void remove(m)}>
                          <IconTrash size={16} />
                        </ActionIcon>
                      </Group>
                    </Table.Td>
                  )}
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}

      <MeterFormModal
        opened={formOpen} systemId={systemId} meter={editMeter}
        onClose={() => setFormOpen(false)}
        onSaved={() => { setFormOpen(false); void meters.reload(); }}
      />
    </Card>
  );
}

function CalibrationBadge({ meter }: { meter: Meter }) {
  if (!meter.eichung_bis) return <Text size="sm" c="dimmed">–</Text>;
  const days = meter.eichung_faellig_in_tagen;
  const color = meter.eichung_abgelaufen ? 'red' : days != null && days <= 90 ? 'orange' : 'gray';
  const label = meter.eichung_abgelaufen
    ? 'abgelaufen'
    : days != null && days <= 90 ? `in ${days} Tagen` : fmtDate(meter.eichung_bis);
  return (
    <Group gap={6}>
      <Text size="sm">{fmtDate(meter.eichung_bis)}</Text>
      {color !== 'gray' && <Badge size="xs" variant="light" color={color}>{label}</Badge>}
    </Group>
  );
}

interface MeterForm {
  hersteller: string; modell: string; zaehlernummer: string; bauart: string;
  baujahr: number | ''; eichung_bis: Date | null; messstellenbetreiber: string;
  stellen_vor: number | ''; stellen_nach: number | ''; eingebaut_am: Date | null;
  ausgebaut_am: Date | null; notiz: string;
}

function toForm(m?: Meter): MeterForm {
  return {
    hersteller: m?.hersteller ?? '', modell: m?.modell ?? '', zaehlernummer: m?.zaehlernummer ?? '',
    bauart: m?.bauart ?? '', baujahr: m?.baujahr ?? '',
    eichung_bis: m?.eichung_bis ? new Date(m.eichung_bis) : null,
    messstellenbetreiber: m?.messstellenbetreiber ?? '',
    stellen_vor: m?.stellen_vor ?? '', stellen_nach: m?.stellen_nach ?? '',
    eingebaut_am: m?.eingebaut_am ? new Date(m.eingebaut_am) : null,
    ausgebaut_am: m?.ausgebaut_am ? new Date(m.ausgebaut_am) : null,
    notiz: m?.notiz ?? '',
  };
}

function MeterFormModal({ opened, systemId, meter, onClose, onSaved }: {
  opened: boolean; systemId: string; meter?: Meter; onClose: () => void; onSaved: () => void;
}) {
  const editing = !!meter;
  const [busy, setBusy] = useState(false);
  const bauarten = useApiData<string[]>('/api/meters/bauarten');
  const form = useForm<MeterForm>({ initialValues: toForm(meter) });

  // Formular bei jedem Öffnen/Wechsel neu befüllen.
  const [seedId, setSeedId] = useState<string | undefined>();
  if (opened && seedId !== (meter?.id ?? 'new')) {
    setSeedId(meter?.id ?? 'new');
    form.setValues(toForm(meter));
  }

  const iso = (d: Date | null) => (d ? dayjs(d).format('YYYY-MM-DD') : null);

  async function submit(v: MeterForm) {
    setBusy(true);
    try {
      const body = {
        hersteller: v.hersteller.trim() || null, modell: v.modell.trim() || null,
        zaehlernummer: v.zaehlernummer.trim() || null, bauart: v.bauart.trim() || null,
        baujahr: v.baujahr === '' ? null : Number(v.baujahr),
        eichung_bis: iso(v.eichung_bis), messstellenbetreiber: v.messstellenbetreiber.trim() || null,
        stellen_vor: v.stellen_vor === '' ? null : Number(v.stellen_vor),
        stellen_nach: v.stellen_nach === '' ? null : Number(v.stellen_nach),
        eingebaut_am: iso(v.eingebaut_am), ausgebaut_am: iso(v.ausgebaut_am),
        notiz: v.notiz.trim() || null,
      };
      if (editing) await apiPatch(`/api/meters/${meter!.id}`, body);
      else await apiPost(`/api/systems/${systemId}/meters`, body);
      notifications.show({ message: editing ? 'Zähler gespeichert' : 'Zähler hinzugefügt', color: 'teal' });
      onSaved();
    } catch (e) {
      notifications.show({ color: 'red', message: e instanceof ApiError ? e.message : 'Speichern fehlgeschlagen' });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal opened={opened} onClose={onClose} title={editing ? 'Zähler bearbeiten' : 'Zähler hinzufügen'} size="lg" centered>
      <form onSubmit={form.onSubmit(submit)}>
        <Stack gap="sm">
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
            <TextInput label="Zählernummer" placeholder="1 ESY 000…" {...form.getInputProps('zaehlernummer')} />
            <Autocomplete label="Bauart" data={bauarten.data ?? []} placeholder="z. B. eHZ, Balgengaszähler" {...form.getInputProps('bauart')} />
            <TextInput label="Hersteller" {...form.getInputProps('hersteller')} />
            <TextInput label="Modell" {...form.getInputProps('modell')} />
            <NumberInput label="Baujahr" min={1900} max={2100} {...form.getInputProps('baujahr')} />
            <DatePickerInput label="Eichung gültig bis" valueFormat="DD.MM.YYYY" clearable {...form.getInputProps('eichung_bis')} />
            <TextInput label="Messstellenbetreiber" {...form.getInputProps('messstellenbetreiber')} />
            <div />
            <NumberInput label="Vorkommastellen" min={1} max={12} {...form.getInputProps('stellen_vor')} />
            <NumberInput label="Nachkommastellen" min={0} max={6} {...form.getInputProps('stellen_nach')} />
            <DatePickerInput label="Eingebaut am" valueFormat="DD.MM.YYYY" clearable {...form.getInputProps('eingebaut_am')} />
            <DatePickerInput label="Ausgebaut am" valueFormat="DD.MM.YYYY" clearable {...form.getInputProps('ausgebaut_am')} />
          </SimpleGrid>
          <Textarea label="Notiz" autosize minRows={1} {...form.getInputProps('notiz')} />
          <Group justify="flex-end" mt="xs">
            <Button variant="default" onClick={onClose}>Abbrechen</Button>
            <Button type="submit" loading={busy}>{editing ? 'Speichern' : 'Hinzufügen'}</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
