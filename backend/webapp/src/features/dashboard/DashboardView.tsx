import { SimpleGrid, Card, Text, Group, Badge, Skeleton, Alert, Stack, Table, Title } from '@mantine/core';
import { IconAlertTriangle } from '@tabler/icons-react';
import type { EChartsOption } from 'echarts';
import { useApiData } from '../../api/useApi';
import type { DashboardData, DashboardSystem } from '../../api/types';
import { EChart } from '../../components/EChart';
import { fmtValue, fmtCost, fmtDate } from '../../util/format';

export function DashboardView() {
  const { data, loading, error } = useApiData<DashboardData>('/api/dashboard/data?months=24');

  if (loading && !data) {
    return (
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
        {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} h={220} radius="sm" />)}
      </SimpleGrid>
    );
  }
  if (error) return <Alert color="red" icon={<IconAlertTriangle size={16} />}>{error}</Alert>;

  const systems = data?.systems ?? [];

  return (
    <Stack gap="lg">
      <SimpleGrid cols={{ base: 1, md: 2, xl: 3 }} spacing="md">
        {systems.map((s) => <SystemCard key={s.id} system={s} />)}
      </SimpleGrid>

      {data?.recent && data.recent.length > 0 && (
        <Card>
          <Title order={5} mb="sm">Zuletzt erfasst</Title>
          <Table.ScrollContainer minWidth={420}>
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>System</Table.Th>
                  <Table.Th>Datum</Table.Th>
                  <Table.Th ta="right">Wert</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {data.recent.map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>{r.system}</Table.Td>
                    <Table.Td>{fmtDate(r.datum)}</Table.Td>
                    <Table.Td ta="right">{fmtValue(r.value, r.einheit)}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        </Card>
      )}
    </Stack>
  );
}

function SystemCard({ system }: { system: DashboardSystem }) {
  const exceeds = system.prognosis?.exceeds_abschlag ?? false;
  const option: EChartsOption = {
    grid: { top: 8, right: 8, bottom: 20, left: 40 },
    xAxis: { type: 'category', data: system.series.map((p) => p.d), show: false },
    yAxis: { type: 'value' },
    tooltip: { trigger: 'axis' },
    series: [{
      type: 'line', smooth: true, showSymbol: false,
      data: system.series.map((p) => p.v),
      areaStyle: { opacity: 0.15 },
      lineStyle: { width: 2, color: system.farbe },
      itemStyle: { color: system.farbe },
    }],
  };

  return (
    <Card>
      <Group justify="space-between" mb="xs">
        <div>
          <Text fw={600}>{system.name}</Text>
          <Text size="xs" c="dimmed">{system.typ}</Text>
        </div>
        <Badge variant="light" color="gray">{system.einheit}</Badge>
      </Group>

      <Group gap="xl" mb="xs">
        <Metric label="Aktuell" value={fmtValue(system.latest, system.einheit)} sub={fmtDate(system.latest_datum)} />
        <Metric label="Verbrauch" value={fmtValue(system.total_consumption, system.einheit)} />
        <Metric label="Kosten" value={fmtCost(system.total_cost_tariff ?? system.total_cost)} />
      </Group>

      {system.series.length > 1 && <EChart option={option} height={120} />}

      {system.prognosis && (
        <Group gap="xs" mt="xs">
          <Badge color={exceeds ? 'orange' : 'gray'} variant="light">
            Prognose {fmtValue(system.prognosis.projected_consumption, system.einheit)} · {fmtCost(system.prognosis.projected_cost)}
          </Badge>
        </Group>
      )}
    </Card>
  );
}

function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <Text size="xs" c="dimmed">{label}</Text>
      <Text fw={600} size="sm">{value}</Text>
      {sub && <Text size="xs" c="dimmed">{sub}</Text>}
    </div>
  );
}
