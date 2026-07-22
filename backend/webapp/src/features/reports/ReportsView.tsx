import { useState } from 'react';
import { Card, Stack, Group, Text, Button, Select, Skeleton, Alert } from '@mantine/core';
import { IconFileText, IconReportAnalytics, IconAlertTriangle } from '@tabler/icons-react';
import type { EChartsOption } from 'echarts';
import { useApiData } from '../../api/useApi';
import type { SystemRead, ChartData } from '../../api/types';
import { EChart } from '../../components/EChart';

// PDFs werden über einen normalen Link/neuen Tab geöffnet (Sitzungscookie wird
// same-origin mitgesendet). Relative URL -> HA-Ingress-tauglich.
function openPdf(path: string) {
  window.open(path.replace(/^\//, ''), '_blank', 'noopener');
}

export function ReportsView() {
  const systems = useApiData<SystemRead[]>('/api/systems');
  const [systemId, setSystemId] = useState<string | null>(null);
  const chart = useApiData<ChartData>(systemId ? `/api/systems/${systemId}/chart-data` : null);

  const active = (systems.data ?? []).filter((s) => s.aktiv);

  return (
    <Stack gap="lg">
      <Card>
        <Group gap="xs" mb="sm"><IconReportAnalytics size={18} /><Text fw={600}>Berichte (PDF)</Text></Group>
        <Text size="sm" c="dimmed" mb="sm">
          Die Übersicht folgt dem gewohnten Aufbau (Jahresverbrauch, Verbrauch/Kosten pro Tag,
          Kosten pro Einheit, Kosten im Jahr) inklusive Zählertausch-Markierung, Gas-kWh-Umrechnung
          und Auswertungsgrafiken.
        </Text>
        <Group>
          <Button leftSection={<IconFileText size={16} />} onClick={() => openPdf('/api/report/overview.pdf')}>
            Strom/Gas/Wasser-Übersicht
          </Button>
          <Button variant="light" leftSection={<IconFileText size={16} />} onClick={() => openPdf('/api/report.pdf')}>
            Kombinierter Bericht
          </Button>
        </Group>
      </Card>

      <Card>
        <Text fw={600} mb="sm">System-Auswertung</Text>
        <Group align="flex-end" mb="md">
          <Select
            label="System" placeholder="System wählen …" w={260}
            data={active.map((s) => ({ value: s.id, label: s.name }))}
            value={systemId} onChange={setSystemId}
          />
          {systemId && (
            <Button variant="light" leftSection={<IconFileText size={16} />}
                    onClick={() => openPdf(`/api/systems/${systemId}/report.pdf`)}>
              System-Bericht (PDF)
            </Button>
          )}
        </Group>

        {!systemId ? (
          <Text size="sm" c="dimmed">Wähle ein System, um den Verlauf anzuzeigen.</Text>
        ) : chart.loading && !chart.data ? (
          <Skeleton h={280} />
        ) : chart.error ? (
          <Alert color="red" icon={<IconAlertTriangle size={16} />}>{chart.error}</Alert>
        ) : chart.data ? (
          <ConsumptionChart chart={chart.data} />
        ) : null}
      </Card>
    </Stack>
  );
}

function ConsumptionChart({ chart }: { chart: ChartData }) {
  const option: EChartsOption = {
    grid: { top: 20, right: 16, bottom: 30, left: 52 },
    tooltip: { trigger: 'axis' },
    legend: { data: ['Verbrauch/Tag'], top: 0 },
    xAxis: { type: 'category', data: chart.labels },
    yAxis: { type: 'value', name: `${chart.unit}/Tag` },
    series: [{
      name: 'Verbrauch/Tag', type: 'line', smooth: true, showSymbol: false,
      data: chart.consumption_per_day,
      lineStyle: { width: 2, color: chart.color },
      itemStyle: { color: chart.color },
      areaStyle: { opacity: 0.12 },
    }],
  };
  return <EChart option={option} height={320} />;
}
