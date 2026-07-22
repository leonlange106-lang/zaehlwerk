import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Card, Table, Skeleton, Alert, Title, Group, Badge, Text, Anchor, Button, Modal,
  TextInput, ColorInput, SimpleGrid, NumberInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { IconAlertTriangle, IconPlus } from '@tabler/icons-react';
import { useApiData } from '../../api/useApi';
import { apiPost, ApiError } from '../../api/client';
import type { DashboardData } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { fmtValue, fmtDate } from '../../util/format';

// Kompakte Desktop-Tabelle aller Systeme mit aktuellem Stand; Klick öffnet die
// Detailansicht (Ablesungen erfassen/löschen). „System anlegen" via Modal.
export function ReadingsView() {
  const { can } = useAuth();
  const { data, loading, error, reload } = useApiData<DashboardData>('/api/dashboard/data?months=24');
  const [addOpen, setAddOpen] = useState(false);

  const systems = data?.systems ?? [];

  return (
    <Card>
      <Group justify="space-between" mb="sm">
        <Group gap="sm">
          <Title order={5}>Zählerstände</Title>
          <Badge variant="light" color="gray">{systems.length} Systeme</Badge>
        </Group>
        {can('write') && (
          <Button size="xs" leftSection={<IconPlus size={16} />} onClick={() => setAddOpen(true)}>
            System anlegen
          </Button>
        )}
      </Group>

      {error && <Alert color="red" icon={<IconAlertTriangle size={16} />}>{error}</Alert>}
      {loading && !data ? (
        <Skeleton h={280} radius="sm" />
      ) : (
        <Table.ScrollContainer minWidth={640}>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>System</Table.Th>
                <Table.Th>Typ</Table.Th>
                <Table.Th ta="right">Aktueller Stand</Table.Th>
                <Table.Th ta="right">Ø / Tag</Table.Th>
                <Table.Th>Letzte Ablesung</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {systems.map((s) => (
                <Table.Tr key={s.id}>
                  <Table.Td>
                    <Group gap={8} wrap="nowrap">
                      <span style={{ width: 10, height: 10, borderRadius: 5, background: s.farbe, display: 'inline-block' }} />
                      <Anchor component={Link} to={`/readings/${s.id}`} size="sm">{s.name}</Anchor>
                    </Group>
                  </Table.Td>
                  <Table.Td><Text size="sm" c="dimmed">{s.typ}</Text></Table.Td>
                  <Table.Td ta="right">{fmtValue(s.latest, s.einheit)}</Table.Td>
                  <Table.Td ta="right">{fmtValue(s.avg_per_day, s.einheit)}</Table.Td>
                  <Table.Td>{fmtDate(s.latest_datum)}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}

      <AddSystemModal opened={addOpen} onClose={() => setAddOpen(false)} onCreated={() => { setAddOpen(false); void reload(); }} />
    </Card>
  );
}

const PRESETS: Record<string, string> = {
  Strom: 'kWh', Gas: 'kWh', Wasser: 'm³', 'PV-Erzeugung': 'kWh', Wärme: 'kWh', Heizöl: 'l',
};

function AddSystemModal({ opened, onClose, onCreated }: { opened: boolean; onClose: () => void; onCreated: () => void }) {
  const [busy, setBusy] = useState(false);
  const form = useForm<{ name: string; typ: string; einheit: string; farbe: string; brennwert: number | ''; zustandszahl: number | '' }>({
    initialValues: { name: '', typ: 'Strom', einheit: 'kWh', farbe: '#3b82f6', brennwert: '', zustandszahl: '' },
    validate: {
      name: (v) => (v.trim().length < 1 ? 'Name erforderlich' : null),
      typ: (v) => (v.trim().length < 1 ? 'Typ erforderlich' : null),
      einheit: (v) => (v.trim().length < 1 ? 'Einheit erforderlich' : null),
    },
  });

  async function submit(values: typeof form.values) {
    setBusy(true);
    try {
      const zusatzfelder: Record<string, number> = {};
      if (values.brennwert !== '') zusatzfelder.brennwert = Number(values.brennwert);
      if (values.zustandszahl !== '') zusatzfelder.zustandszahl = Number(values.zustandszahl);
      await apiPost('/api/systems', {
        name: values.name.trim(), typ: values.typ.trim(),
        einheit: values.einheit.trim(), farbe: values.farbe,
        ...(Object.keys(zusatzfelder).length ? { zusatzfelder } : {}),
      });
      notifications.show({ message: 'System angelegt', color: 'teal' });
      form.reset();
      onCreated();
    } catch (e) {
      notifications.show({ color: 'red', message: e instanceof ApiError ? e.message : 'Anlegen fehlgeschlagen' });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal opened={opened} onClose={onClose} title="System anlegen" centered>
      <form onSubmit={form.onSubmit(submit)}>
        <SimpleGrid cols={1} spacing="sm">
          <TextInput label="Name" placeholder="z. B. Zähler Keller" {...form.getInputProps('name')} />
          <TextInput
            label="Typ" {...form.getInputProps('typ')}
            onBlur={(e) => {
              const preset = PRESETS[e.currentTarget.value];
              if (preset && !form.values.einheit) form.setFieldValue('einheit', preset);
            }}
          />
          <TextInput label="Einheit" placeholder="kWh, m³ …" {...form.getInputProps('einheit')} />
          {form.values.typ.toLowerCase().includes('gas') && (
            <Group grow>
              <NumberInput label="Brennwert (kWh/m³)" placeholder="11,0" decimalScale={3} {...form.getInputProps('brennwert')} />
              <NumberInput label="Zustandszahl" placeholder="0,95" decimalScale={4} {...form.getInputProps('zustandszahl')} />
            </Group>
          )}
          <ColorInput label="Farbe" {...form.getInputProps('farbe')} />
          <Group justify="flex-end" mt="sm">
            <Button variant="default" onClick={onClose}>Abbrechen</Button>
            <Button type="submit" loading={busy}>Anlegen</Button>
          </Group>
        </SimpleGrid>
      </form>
    </Modal>
  );
}
