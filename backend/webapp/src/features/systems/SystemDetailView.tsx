import { useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Stack, Group, Title, Card, SimpleGrid, Text, Table, Badge, Button, ActionIcon,
  Skeleton, Alert, Divider, NumberInput, Textarea, Switch, FileButton, Loader,
} from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import {
  IconTrash, IconChevronLeft, IconAlertTriangle, IconCamera, IconArrowsExchange,
} from '@tabler/icons-react';
import dayjs from 'dayjs';
import type { EChartsOption } from 'echarts';
import { useApiData } from '../../api/useApi';
import { api, apiPost, apiUpload, ApiError } from '../../api/client';
import type { ChartData, Reading, SystemRead, SystemStats, OcrResult } from '../../api/types';
import { EChart } from '../../components/EChart';
import { useAuth } from '../../auth/AuthContext';
import { fmtValue, fmtCost, fmtDate, fmtNumber } from '../../util/format';

export function SystemDetailView() {
  const { id = '' } = useParams();
  const { can } = useAuth();
  const canWrite = can('write');

  const system = useApiData<SystemRead>(`/api/systems/${id}`);
  const stats = useApiData<SystemStats>(`/api/systems/${id}/stats`);
  const chart = useApiData<ChartData>(`/api/systems/${id}/chart-data`);
  const readings = useApiData<Reading[]>(`/api/systems/${id}/readings`);

  const unit = system.data?.einheit ?? '';

  function reloadAll() {
    void stats.reload();
    void chart.reload();
    void readings.reload();
  }

  async function remove(r: Reading) {
    if (!confirm(`Ablesung vom ${fmtDate(r.datum)} löschen?`)) return;
    try {
      await api(`/api/readings/${r.id}`, { method: 'DELETE' });
      notifications.show({ message: 'Ablesung gelöscht', color: 'teal' });
      reloadAll();
    } catch (e) {
      notifications.show({ color: 'red', message: e instanceof ApiError ? e.message : 'Fehler' });
    }
  }

  if (system.loading && !system.data) return <Skeleton h={400} radius="sm" />;
  if (system.error) return <Alert color="red" icon={<IconAlertTriangle size={16} />}>{system.error}</Alert>;

  const rows = readings.data ?? [];

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <Group gap="xs">
          <ActionIcon component={Link} to="/readings" variant="subtle" aria-label="Zurück">
            <IconChevronLeft size={18} />
          </ActionIcon>
          <div>
            <Title order={4}>{system.data?.name}</Title>
            <Text size="xs" c="dimmed">{system.data?.typ} · {unit}</Text>
          </div>
        </Group>
      </Group>

      {stats.data && (
        <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="md">
          <Stat label="Gesamtverbrauch" value={fmtValue(stats.data.total_consumption, unit)} />
          <Stat label="Ø pro Tag" value={fmtValue(stats.data.avg_per_day, unit)} />
          <Stat label="Kosten gesamt" value={fmtCost(stats.data.total_cost_tariff ?? stats.data.total_cost)} />
          {stats.data.kwh_factor
            ? <Stat label="Gesamt (kWh)" value={fmtValue(stats.data.total_consumption_kwh, 'kWh')} />
            : <Stat label={`Preis/${unit || 'Einheit'}`} value={fmtCost(stats.data.cost_per_unit)} />}
        </SimpleGrid>
      )}

      {chart.data && <ConsumptionChart chart={chart.data} />}

      {canWrite && (
        <AddReadingForm systemId={id} unit={unit} kwhFactor={stats.data?.kwh_factor ?? null} onSaved={reloadAll} />
      )}

      <Card>
        <Title order={5} mb="sm">Ablesungen</Title>
        {readings.loading && !rows.length ? (
          <Skeleton h={160} />
        ) : rows.length === 0 ? (
          <Text c="dimmed" size="sm">Noch keine Ablesungen erfasst.</Text>
        ) : (
          <Table.ScrollContainer minWidth={560}>
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Datum</Table.Th>
                  <Table.Th ta="right">Stand</Table.Th>
                  <Table.Th ta="right">Verbrauch/Tag</Table.Th>
                  <Table.Th>Herkunft</Table.Th>
                  {canWrite && <Table.Th />}
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {rows.map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>
                      <Group gap={6}>
                        {fmtDate(r.datum)}
                        {r.meter_replaced && (
                          <IconArrowsExchange size={14} color="var(--mantine-color-orange-6)" />
                        )}
                        {r.is_outlier && <Badge size="xs" color="orange" variant="light">Ausreißer</Badge>}
                      </Group>
                    </Table.Td>
                    <Table.Td ta="right">{fmtValue(r.value, unit)}</Table.Td>
                    <Table.Td ta="right">
                      {r.consumption_per_day != null ? `${fmtNumber(r.consumption_per_day)} ${unit}` : '–'}
                      {r.consumption_per_day_kwh != null && (
                        <Text span size="xs" c="dimmed"> ({fmtNumber(r.consumption_per_day_kwh)} kWh)</Text>
                      )}
                    </Table.Td>
                    <Table.Td><Badge size="xs" variant="light" color="gray">{sourceLabel(r.source)}</Badge></Table.Td>
                    {canWrite && (
                      <Table.Td ta="right">
                        <ActionIcon color="red" variant="subtle" onClick={() => void remove(r)} aria-label="Löschen">
                          <IconTrash size={16} />
                        </ActionIcon>
                      </Table.Td>
                    )}
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

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card padding="sm">
      <Text size="xs" c="dimmed">{label}</Text>
      <Text fw={600}>{value}</Text>
    </Card>
  );
}

function sourceLabel(s: string): string {
  return { manual: 'manuell', ha_api: 'HA', mqtt: 'MQTT', import: 'Import' }[s] ?? s;
}

function ConsumptionChart({ chart }: { chart: ChartData }) {
  const points = chart.labels.map((label, i) => ({ label, value: chart.consumption_per_day[i], outlier: chart.outliers[i] }));
  const option: EChartsOption = {
    grid: { top: 16, right: 12, bottom: 28, left: 48 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: points.map((p) => p.label) },
    yAxis: { type: 'value', name: `${chart.unit}/Tag` },
    series: [{
      type: 'line', smooth: true, showSymbol: false,
      data: points.map((p) => p.value),
      lineStyle: { width: 2, color: chart.color },
      itemStyle: { color: chart.color },
      areaStyle: { opacity: 0.12 },
    }],
  };
  return (
    <Card>
      <Title order={5} mb="sm">Verlauf</Title>
      <EChart option={option} height={260} />
    </Card>
  );
}

function AddReadingForm({ systemId, unit, kwhFactor, onSaved }: { systemId: string; unit: string; kwhFactor: number | null; onSaved: () => void }) {
  const [busy, setBusy] = useState(false);
  const [scanning, setScanning] = useState(false);
  const resetRef = useRef<() => void>(null);

  const form = useForm<{
    datum: Date | null; value: number | ''; cost: number | ''; note: string;
    meter_replaced: boolean; meter_start: number | '';
  }>({
    initialValues: { datum: new Date(), value: '', cost: '', note: '', meter_replaced: false, meter_start: '' },
    validate: {
      datum: (v) => (v ? null : 'Datum erforderlich'),
      value: (v) => (v === '' || Number.isNaN(Number(v)) ? 'Zählerstand erforderlich' : null),
      meter_start: (v, values) =>
        values.meter_replaced && v !== '' && Number(v) > Number(values.value)
          ? 'Startstand darf nicht über dem Ablesewert liegen' : null,
    },
  });

  async function scan(file: File | null) {
    if (!file) return;
    setScanning(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await apiUpload<OcrResult>('/api/ocr/scan', fd);
      if (res.value != null) form.setFieldValue('value', res.value);
      if (res.datum) form.setFieldValue('datum', new Date(res.datum));
      notifications.show({
        color: res.value != null ? 'teal' : 'yellow',
        message: res.value != null
          ? `Erkannt: ${fmtNumber(res.value)} ${unit}${res.confidence != null ? ` (${res.confidence}%)` : ''}`
          : 'Kein Zählerstand erkannt',
      });
    } catch (e) {
      notifications.show({ color: 'red', message: e instanceof ApiError ? e.message : 'OCR fehlgeschlagen' });
    } finally {
      setScanning(false);
      resetRef.current?.();
    }
  }

  async function submit(values: typeof form.values) {
    setBusy(true);
    try {
      await apiPost(`/api/systems/${systemId}/readings`, {
        datum: dayjs(values.datum).format('YYYY-MM-DD'),
        value: Number(values.value),
        cost: values.cost === '' ? undefined : Number(values.cost),
        meter_replaced: values.meter_replaced,
        meter_start: values.meter_replaced && values.meter_start !== '' ? Number(values.meter_start) : undefined,
        note: values.note.trim() || undefined,
        source: 'manual',
      });
      notifications.show({ message: 'Ablesung gespeichert', color: 'teal' });
      form.reset();
      onSaved();
    } catch (e) {
      notifications.show({ color: 'red', message: e instanceof ApiError ? e.message : 'Speichern fehlgeschlagen' });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <Group justify="space-between" mb="sm">
        <Title order={5}>Neue Ablesung</Title>
        <FileButton resetRef={resetRef} accept="image/*" onChange={scan}>
          {(props) => (
            <Button {...props} size="xs" variant="light" leftSection={scanning ? <Loader size={14} /> : <IconCamera size={16} />} disabled={scanning}>
              Foto scannen
            </Button>
          )}
        </FileButton>
      </Group>
      <form onSubmit={form.onSubmit(submit)}>
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="sm">
          <DatePickerInput label="Datum" valueFormat="DD.MM.YYYY" {...form.getInputProps('datum')} />
          <NumberInput
            label={`Zählerstand (${unit})`} decimalScale={3} {...form.getInputProps('value')}
            description={kwhFactor && form.values.value !== ''
              ? `≈ ${fmtNumber(Number(form.values.value) * kwhFactor)} kWh`
              : undefined}
          />
          <NumberInput label="Kosten (€)" decimalScale={2} {...form.getInputProps('cost')} />
          <Textarea label="Notiz" autosize minRows={1} {...form.getInputProps('note')} />
        </SimpleGrid>
        <Divider my="sm" />
        <Group align="flex-end">
          <Switch label="Zählertausch" {...form.getInputProps('meter_replaced', { type: 'checkbox' })} />
          {form.values.meter_replaced && (
            <NumberInput label={`Anfangsstand neuer Zähler (${unit})`} decimalScale={3} {...form.getInputProps('meter_start')} />
          )}
          <Button type="submit" loading={busy} ml="auto">Sichern</Button>
        </Group>
      </form>
    </Card>
  );
}
